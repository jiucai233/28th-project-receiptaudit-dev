from __future__ import annotations
import os

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"
os.environ['FLAGS_allocator_strategy'] = 'naive_best_fit' 
os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0.2' 
os.environ['FLAGS_eager_delete_tensor_gb'] = '0.0'
import cv2
import numpy as np
from paddleocr import PaddleOCR


class PaddleOCRWrapper:
    """PaddleOCR 기반 영수증 텍스트 추출 래퍼 (PaddleOCR 3.x API)"""

    CONFIDENCE_RETRY_THRESHOLD = 0.6
    SKEW_ANGLE_THRESHOLD = 3.0  # 이 각도 이하는 보정 안 함
    def __init__(
        self,
        lang: str = "korean",
        min_confidence: float = 0.5,
        use_skew_correction: bool = True,
    ):
        """
        Args:
            lang: OCR 언어 설정
            min_confidence: 최소 신뢰도 (이 값 미만인 텍스트는 제거)
            use_skew_correction: 기울기 보정 전처리 사용 여부
        """
        self.ocr = PaddleOCR(
            lang=lang, 
            use_doc_orientation_classify=False,
            device="cpu",          # 강제로 CPU 전용 사용 (GPU/MPS 메모리 누수 방지)
            enable_mkldnn=False,   # mkldnn 비활성화 (메모리 팽창 방지)
            cpu_threads=4          # Medium 인스턴스(2vCPU) 및 로컬 환경 고려 (스레드 제한)
        )
        self.min_confidence = min_confidence
        self.use_skew_correction = use_skew_correction

    def _avg_confidence(self, r: dict) -> float:
        """OCR 결과의 평균 신뢰도 계산"""
        scores = r["rec_scores"]
        return sum(scores) / len(scores) if scores else 0.0

    def extract(self, image_path: str) -> list[dict]:
        """이미지에서 텍스트를 추출하여 줄 단위로 반환

        방향 분류를 비활성화하고, 평균 신뢰도가 낮으면
        180도 회전 후 재시도하여 더 나은 결과를 채택한다.

        Args:
            image_path: 영수증 이미지 경로

        Returns:
            줄 단위 OCR 결과 리스트
            [{"text": str, "confidence": float, "bbox": list}, ...]
        """
        with open(image_path, "rb") as f:
            data = f.read()
        img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return []

        if self.use_skew_correction:
            img = self._correct_skew(img)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        result = self.ocr.predict(img_rgb)

        if not result:
            return []

        r = result[0]

        # 평균 신뢰도가 낮으면 180도 회전 후 재시도
        if self._avg_confidence(r) < self.CONFIDENCE_RETRY_THRESHOLD:
            img_rotated = np.rot90(img_rgb, 2)  # 180도 회전

            result2 = self.ocr.predict(img_rotated)
            if result2 and self._avg_confidence(result2[0]) > self._avg_confidence(r):
                r = result2[0]

        texts = r["rec_texts"]
        scores = r["rec_scores"]
        polys = r["dt_polys"]

        detections = []
        for text, score, poly in zip(texts, scores, polys):
            if float(score) < self.min_confidence:
                continue
            bbox = poly.tolist()
            y_center = (bbox[0][1] + bbox[2][1]) / 2
            x_center = (bbox[0][0] + bbox[2][0]) / 2
            detections.append({
                "text": text.strip(),
                "confidence": float(score),
                "bbox": bbox,
                "y_center": y_center,
                "x_center": x_center,
            })

        lines = self._merge_lines(detections)
        return lines

    MIN_CONTOUR_AREA_RATIO = 0.05  # 컨투어가 이미지의 5% 미만이면 신뢰 불가

    def _detect_skew_angle(self, img: np.ndarray) -> float:
        """문서 기울기 감지 (컨투어 기반 + Hough 라인 대체)

        흰 배경 위 영수증의 외곽을 찾아 회전 각도를 계산한다.
        컨투어가 너무 작으면 Hough 라인 기반으로 대체한다.

        Returns:
            기울기 각도 (도). 양수 = 반시계 방향.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return 0.0

        largest = max(contours, key=cv2.contourArea)
        img_area = img.shape[0] * img.shape[1]
        area_ratio = cv2.contourArea(largest) / img_area

        # 영수증이 이미지 대부분(90%+)을 차지 → 회전 없음
        if area_ratio > 0.9:
            return 0.0

        # 컨투어가 너무 작으면 노이즈일 가능성 → Hough 라인으로 대체
        if area_ratio < self.MIN_CONTOUR_AREA_RATIO:
            return self._detect_skew_hough(gray)

        rect = cv2.minAreaRect(largest)
        angle = rect[2]  # [0, 90) in OpenCV 4.5+

        w, h = rect[1]

        # OpenCV minAreaRect는 [0, 90) 범위의 각도를 반환하므로
        # angle과 angle-90 두 해석이 가능.
        angle_alt = angle - 90

        if abs(angle_alt) < abs(angle):
            # 명확히 작은 쪽 선택 (15°, 30° 등)
            angle = angle_alt
        elif abs(angle_alt) == abs(angle):
            # 45° 동점: w > h이면 가로가 긴 것 → 90° 보정
            if w > h:
                angle = angle_alt

        return angle

    HOUGH_MIN_LINES = 10  # 최소 라인 수 (신뢰도 확보)
    HOUGH_MAX_STD = 5.0   # 각도 표준편차 한계 (이상이면 신뢰 불가)

    def _detect_skew_hough(self, gray: np.ndarray) -> float:
        """Hough 라인 기반 기울기 감지 (컨투어 감지 실패 시 대체)

        텍스트 라인의 기울기를 직접 측정하여 문서 회전 각도를 추정한다.
        라인 수가 적거나 각도 분산이 크면 신뢰할 수 없으므로 0을 반환.
        """
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=80, minLineLength=50, maxLineGap=10,
        )
        if lines is None:
            return 0.0

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            if abs(dx) < 1:
                continue
            a = np.degrees(np.arctan2(y2 - y1, dx))
            # 수평에 가까운 라인만 사용 (텍스트 라인)
            if abs(a) < 45:
                angles.append(a)

        if len(angles) < self.HOUGH_MIN_LINES:
            return 0.0

        # 각도 분산이 크면 노이즈 → 신뢰 불가
        if float(np.std(angles)) > self.HOUGH_MAX_STD:
            return 0.0

        return float(np.median(angles))

    def _correct_skew(self, img: np.ndarray) -> np.ndarray:
        """기울어진 영수증 이미지를 자동 보정"""
        angle = self._detect_skew_angle(img)
        if abs(angle) <= self.SKEW_ANGLE_THRESHOLD:
            return img

        (h, w) = img.shape[:2]
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # 회전 후 잘리지 않도록 캔버스 확장
        cos = abs(M[0, 0])
        sin = abs(M[0, 1])
        new_w = int(h * sin + w * cos)
        new_h = int(h * cos + w * sin)
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2

        rotated = cv2.warpAffine(
            img, M, (new_w, new_h),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

        return self._crop_to_content(rotated)

    def _crop_to_content(self, img: np.ndarray) -> np.ndarray:
        """흰 배경을 제거하고 영수증 영역만 크롭"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return img

        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)

        # 약간의 패딩 추가
        pad = 10
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img.shape[1] - x, w + 2 * pad)
        h = min(img.shape[0] - y, h + 2 * pad)

        return img[y:y + h, x:x + w]

    def _merge_lines(
        self, detections: list[dict], y_threshold: float | None = None
    ) -> list[dict]:
        """Y좌표가 가까운 텍스트를 같은 줄로 병합

        영수증 OCR에서 같은 행의 품목명과 가격이 별도 감지되는 경우가 많으므로,
        Y좌표 차이가 threshold 이내인 텍스트를 하나의 줄로 합침.

        y_threshold가 None이면 텍스트 높이 기반으로 자동 계산.
        """
        if not detections:
            return []

        # 자동 threshold: 텍스트 박스 평균 높이의 60%
        if y_threshold is None:
            heights = []
            for d in detections:
                bbox = d["bbox"]
                h = abs(bbox[2][1] - bbox[0][1])
                if h > 0:
                    heights.append(h)
            if heights:
                y_threshold = max(sum(heights) / len(heights) * 0.6, 10.0)
            else:
                y_threshold = 15.0

        detections.sort(key=lambda d: d["y_center"])

        merged = []
        current_group = [detections[0]]

        for det in detections[1:]:
            if abs(det["y_center"] - current_group[0]["y_center"]) <= y_threshold:
                current_group.append(det)
            else:
                merged.append(self._merge_group(current_group))
                current_group = [det]

        if current_group:
            merged.append(self._merge_group(current_group))

        return merged

    def _merge_group(self, group: list[dict]) -> dict:
        """같은 줄의 텍스트들을 X좌표 순서로 합침"""
        group.sort(key=lambda d: d["x_center"])

        merged_text = " ".join(d["text"] for d in group)
        avg_confidence = sum(d["confidence"] for d in group) / len(group)

        all_x = [p[0] for d in group for p in d["bbox"]]
        all_y = [p[1] for d in group for p in d["bbox"]]
        merged_bbox = [
            [min(all_x), min(all_y)],
            [max(all_x), min(all_y)],
            [max(all_x), max(all_y)],
            [min(all_x), max(all_y)],
        ]

        return {
            "text": merged_text,
            "confidence": avg_confidence,
            "bbox": merged_bbox,
        }