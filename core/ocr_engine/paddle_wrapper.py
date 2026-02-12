import os

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from paddleocr import PaddleOCR


class PaddleOCRWrapper:
    """PaddleOCR 기반 영수증 텍스트 추출 래퍼 (PaddleOCR 3.x API)"""

    def __init__(self, lang: str = "korean", min_confidence: float = 0.5):
        """
        Args:
            lang: OCR 언어 설정
            min_confidence: 최소 신뢰도 (이 값 미만인 텍스트는 제거)
        """
        self.ocr = PaddleOCR(lang=lang)
        self.min_confidence = min_confidence

    def extract(self, image_path: str) -> list[dict]:
        """이미지에서 텍스트를 추출하여 줄 단위로 반환

        Args:
            image_path: 영수증 이미지 경로

        Returns:
            줄 단위 OCR 결과 리스트
            [{"text": str, "confidence": float, "bbox": list}, ...]
        """
        result = self.ocr.predict(image_path)

        if not result:
            return []

        r = result[0]
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
