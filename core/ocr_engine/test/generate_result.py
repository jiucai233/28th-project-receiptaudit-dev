"""50장 영수증에 대해 OCR 실행 → result.json 생성"""

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from core.ocr_engine.paddle_wrapper import PaddleOCRWrapper
from core.ocr_engine.processor import ReceiptProcessor

TEST_DIR = Path(__file__).parent
RECEIPTS_DIR = TEST_DIR / "receipts"
RESULT_PATH = TEST_DIR / "result.json"


def main():
    images = sorted(
        list(RECEIPTS_DIR.glob("receipt*.png")) + list(RECEIPTS_DIR.glob("receipt*.jpg"))
    )
    print(f"총 {len(images)}장 영수증 OCR 시작")

    wrapper = PaddleOCRWrapper()
    processor = ReceiptProcessor()

    results = []
    start = time.time()

    for i, img_path in enumerate(images, 1):
        lines = wrapper.extract(str(img_path))
        result = processor.process(lines)
        results.append(result)

        if i % 5 == 0 or i == len(images):
            elapsed = time.time() - start
            print(f"  {i}/{len(images)} 완료 ({elapsed:.0f}s)")

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    print(f"\nresult.json 저장 완료 ({len(results)}장, {elapsed:.0f}s)")
    print(f"경로: {RESULT_PATH}")


if __name__ == "__main__":
    main()
