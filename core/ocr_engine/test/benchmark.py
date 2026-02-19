"""OCR Performance Benchmark — 조건별 정확도 측정

사용법:
    # 전체 벤치마크 (원본 + 6개 augmentation)
    python -m core.ocr_engine.test.benchmark

    # 특정 조건만
    python -m core.ocr_engine.test.benchmark --condition original bright_up rotate_10
"""

import argparse
import json
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from core.ocr_engine.paddle_wrapper import PaddleOCRWrapper
from core.ocr_engine.processor import ReceiptProcessor

TEST_DIR = Path(__file__).parent
ANSWER_PATH = TEST_DIR / "answer.json"
RECEIPTS_DIR = TEST_DIR / "receipts"
AUG_DIR = TEST_DIR / "augmented"
REPORT_PATH = TEST_DIR / "benchmark_report_augmented.json"
REPORT_NO_SKEW_PATH = TEST_DIR / "benchmark_report_no_skew.json"

ALL_CONDITIONS = [
    "original",
    "bright_up",
    "bright_down",
    "low_res",
    "rotate_15",
    "rotate_30",
    "rotate_45",
]

CONDITION_LABELS = {
    "original": "원본 (Baseline)",
    "bright_up": "밝기 +50%",
    "bright_down": "밝기 -50%",
    "low_res": "해상도 50% 축소",
    "rotate_15": "15° 회전",
    "rotate_30": "30° 회전",
    "rotate_45": "45° 회전",
}

# 고정 샘플 20장 (seed=42로 뽑은 결과를 하드코딩)
# receipt 번호 → answer 인덱스: receiptXX → answers[int(XX)-1]
SAMPLED_STEMS = [
    "receipt02", "receipt03", "receipt06", "receipt07", "receipt08",
    "receipt09", "receipt14", "receipt15", "receipt16", "receipt18",
    "receipt28", "receipt33", "receipt35", "receipt37", "receipt38",
    "receipt41", "receipt45", "receipt47", "receipt48", "receipt50",
]


def stem_to_answer_idx(stem: str) -> int:
    """receiptXX → answers 배열 인덱스 (0-based)"""
    num = int(stem.replace("receipt", ""))
    return num - 1


def load_answers() -> list[dict]:
    with open(ANSWER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_image_path(condition: str, stem: str) -> Path | None:
    """조건 + stem으로 이미지 경로 반환 (png/jpg 자동 탐색)"""
    base_dir = RECEIPTS_DIR if condition == "original" else AUG_DIR / condition
    for ext in (".png", ".jpg"):
        p = base_dir / (stem + ext)
        if p.exists():
            return p
    return None


def _normalize(text: str) -> str:
    """공백 제거"""
    return text.replace(" ", "")


def _score_store_name(result: str, answer: str) -> float:
    """가게명 유사도 (0.0~1.0)

    - 완전 일치 → 1.0
    - 공백 제거 후 일치 → 1.0
    - 한쪽이 다른 쪽에 포함 → 비율 기반 (최소 0.8)
    - 그 외 → SequenceMatcher ratio
    """
    if not answer:
        return 1.0 if not result else 0.0
    if not result:
        return 0.0
    if result == answer:
        return 1.0
    r, a = _normalize(result), _normalize(answer)
    if r == a:
        return 1.0
    if a in r or r in a:
        return max(len(min(r, a, key=len)) / len(max(r, a, key=len)), 0.8)
    return SequenceMatcher(None, r, a).ratio()


def _score_date(result: str, answer: str) -> float:
    """날짜 점수: 날짜 맞으면 0.5, 시간까지 맞으면 1.0"""
    if not answer:
        return 1.0 if not result else 0.0
    if not result:
        return 0.0
    if result == answer:
        return 1.0
    r_parts = result.split()
    a_parts = answer.split()
    r_date = r_parts[0] if r_parts else ""
    a_date = a_parts[0] if a_parts else ""
    if r_date != a_date:
        return 0.0
    # 날짜 일치, 정답에 시간이 없으면 1.0
    a_time = a_parts[1] if len(a_parts) > 1 else ""
    if not a_time:
        return 1.0
    return 0.5  # 날짜는 맞지만 시간 불일치


def _score_item(r_item: dict, a_item: dict) -> float:
    """개별 품목 매칭 점수 (이름 50% + 가격 50%)"""
    r_name = _normalize(r_item["name"])
    a_name = _normalize(a_item["name"])
    name_sim = SequenceMatcher(None, r_name, a_name).ratio()
    if name_sim < 0.4:
        return 0.0
    price_match = 1.0 if r_item["price"] == a_item["price"] else 0.0
    return name_sim * 0.5 + price_match * 0.5


def _score_items(result_items: list, answer_items: list) -> float:
    """품목 전체 매칭 점수 (greedy matching)

    각 정답 품목에 대해 가장 유사한 결과 품목을 매칭.
    점수 = 매칭 점수 합 / max(결과수, 정답수)
    """
    if not answer_items:
        return 1.0 if not result_items else 0.0
    if not result_items:
        return 0.0

    used = set()
    total_score = 0.0

    for a_item in answer_items:
        best_score = 0.0
        best_idx = -1
        for i, r_item in enumerate(result_items):
            if i in used:
                continue
            score = _score_item(r_item, a_item)
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx >= 0 and best_score > 0:
            used.add(best_idx)
        total_score += best_score

    max_items = max(len(result_items), len(answer_items))
    return total_score / max_items


def _score_total_price(result: int, answer: int) -> float:
    """총액 점수: 완전 일치만 인정"""
    if answer == 0:
        return 1.0 if result == 0 else 0.0
    return 1.0 if result == answer else 0.0


def calc_accuracy(pairs: list[tuple[dict, dict]]) -> dict:
    """(result, answer) 쌍 목록으로 필드별 유사도 기반 정확도 계산"""
    n = len(pairs)
    fields = {"store_name": 0.0, "date": 0.0, "items": 0.0, "total_price": 0.0}
    perfect = 0

    for r, a in pairs:
        s_store = _score_store_name(r["store_name"], a["store_name"])
        s_date = _score_date(r["date"], a["date"])
        s_items = _score_items(r["items"], a["items"])
        s_total = _score_total_price(r["total_price"], a["total_price"])

        fields["store_name"] += s_store
        fields["date"] += s_date
        fields["items"] += s_items
        fields["total_price"] += s_total

        if s_store == 1.0 and s_date == 1.0 and s_items == 1.0 and s_total == 1.0:
            perfect += 1

    field_acc = {k: round(v / n * 100, 1) for k, v in fields.items()}
    overall = round(sum(fields.values()) / (n * 4) * 100, 1)

    return {
        "field_accuracy": field_acc,
        "receipt_accuracy": round(perfect / n * 100, 1),
        "overall_field_accuracy": overall,
        "perfect_count": perfect,
        "total_count": n,
    }


def run_condition(
    wrapper: PaddleOCRWrapper,
    processor: ReceiptProcessor,
    condition: str,
    answers: list[dict],
) -> dict:
    """하나의 조건에 대해 OCR 실행 + 정확도 계산"""
    label = CONDITION_LABELS.get(condition, condition)
    print(f"\n{'='*60}")
    print(f"  [{condition}] {label}  ({len(SAMPLED_STEMS)}장)")
    print(f"{'='*60}")

    start = time.time()
    pairs = []
    for i, stem in enumerate(SAMPLED_STEMS, 1):
        img_path = get_image_path(condition, stem)
        if img_path is None:
            print(f"  SKIP: {stem} (이미지 없음)")
            continue

        lines = wrapper.extract(str(img_path))
        result = processor.process(lines)
        answer = answers[stem_to_answer_idx(stem)]
        pairs.append((result, answer))

        if i % 5 == 0 or i == len(SAMPLED_STEMS):
            elapsed = time.time() - start
            print(f"  {i}/{len(SAMPLED_STEMS)} 완료 ({elapsed:.0f}s)")

    elapsed = time.time() - start
    acc = calc_accuracy(pairs)

    print(f"\n  Field Accuracy:")
    print(f"    store_name:  {acc['field_accuracy']['store_name']:5.1f}%")
    print(f"    date:        {acc['field_accuracy']['date']:5.1f}%")
    print(f"    items:       {acc['field_accuracy']['items']:5.1f}%")
    print(f"    total_price: {acc['field_accuracy']['total_price']:5.1f}%")
    print(f"  Overall Field Accuracy: {acc['overall_field_accuracy']:.1f}%")
    print(f"  Receipt Accuracy (PERFECT): {acc['perfect_count']}/{acc['total_count']} ({acc['receipt_accuracy']:.1f}%)")
    print(f"  Time: {elapsed:.1f}s")

    return {
        "condition": condition,
        "label": label,
        **acc,
        "time_seconds": round(elapsed, 1),
    }


def print_summary(report: list[dict]):
    """최종 요약 테이블 출력"""
    print(f"\n{'='*80}")
    print(f"  OCR Performance Benchmark Report")
    print(f"{'='*80}")
    print(f"{'조건':<20} {'가게명':>7} {'날짜':>7} {'품목':>7} {'총액':>7} │ {'Overall':>8} {'PERFECT':>8}")
    print(f"{'-'*20} {'-'*7} {'-'*7} {'-'*7} {'-'*7} ┼ {'-'*8} {'-'*8}")

    for r in report:
        fa = r["field_accuracy"]
        label = r["label"][:18]
        print(
            f"{label:<20} {fa['store_name']:>6.1f}% {fa['date']:>6.1f}% "
            f"{fa['items']:>6.1f}% {fa['total_price']:>6.1f}% │ "
            f"{r['overall_field_accuracy']:>6.1f}%  "
            f"{r['perfect_count']:>2}/{r['total_count']}"
        )

    print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="OCR Performance Benchmark")
    parser.add_argument(
        "--condition",
        nargs="*",
        default=None,
        help="실행할 조건 (미지정 시 전체)",
    )
    parser.add_argument(
        "--no-skew",
        action="store_true",
        help="기울기 보정 전처리 비활성화",
    )
    args = parser.parse_args()

    conditions = args.condition if args.condition else ALL_CONDITIONS
    report_path = REPORT_NO_SKEW_PATH if args.no_skew else REPORT_PATH

    # 유효성 검사
    for c in conditions:
        base_dir = RECEIPTS_DIR if c == "original" else AUG_DIR / c
        if not base_dir.exists():
            print(f"ERROR: {base_dir} 폴더가 없습니다. augment.py를 먼저 실행하세요.")
            sys.exit(1)

    answers = load_answers()
    wrapper = PaddleOCRWrapper(use_skew_correction=not args.no_skew)
    processor = ReceiptProcessor()

    skew_label = "OFF" if args.no_skew else "ON"
    print(f"\n  기울기 보정: {skew_label}")

    # 기존 리포트 로드 (--condition 사용 시 병합용)
    existing = {}
    if args.condition and report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            for entry in json.load(f):
                # items_count → items 호환
                fa = entry.get("field_accuracy", {})
                if "items_count" in fa and "items" not in fa:
                    fa["items"] = fa.pop("items_count")
                existing[entry["condition"]] = entry

    report = []
    total_start = time.time()

    for cond in conditions:
        result = run_condition(wrapper, processor, cond, answers)
        report.append(result)
        existing[cond] = result  # 새 결과로 갱신

    total_elapsed = time.time() - total_start

    # --condition 사용 시 기존 결과와 병합하여 저장
    if args.condition:
        merged = [existing[c] for c in ALL_CONDITIONS if c in existing]
        print_summary(merged)
    else:
        merged = report
        print_summary(report)

    print(f"\n  Total time: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"  Report saved: {report_path}")


if __name__ == "__main__":
    main()
