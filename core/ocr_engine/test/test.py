"""test/receipts 폴더의 영수증 이미지를 OCR + processor로 처리하여 result.json 생성"""
import json
import os
import sys
import glob

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from paddle_wrapper import PaddleOCRWrapper
from processor import ReceiptProcessor

TEST_DIR = os.path.dirname(__file__)
RECEIPTS_DIR = os.path.join(TEST_DIR, "receipts")
OUTPUT_PATH = os.path.join(TEST_DIR, "result.json")


def main():
    # 영수증 이미지 파일 목록 (png, jpg, jpeg)
    image_files = sorted(
        glob.glob(os.path.join(RECEIPTS_DIR, "*.*")),
        key=lambda x: os.path.basename(x),
    )
    image_files = [
        f for f in image_files
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    if not image_files:
        print("receipts 폴더에 이미지가 없습니다.")
        return

    print(f"총 {len(image_files)}개 영수증 이미지 발견\n")

    wrapper = PaddleOCRWrapper()
    processor = ReceiptProcessor()
    results = []

    for i, image_path in enumerate(image_files):
        filename = os.path.basename(image_path)
        print(f"[{i+1}/{len(image_files)}] {filename}")

        try:
            ocr_lines = wrapper.extract(image_path)
            print(f"  OCR 추출: {len(ocr_lines)}줄")

            result = processor.process(ocr_lines)
            results.append(result)

            print(f"  가게: {result['store_name']}")
            print(f"  날짜: {result['date']}")
            print(f"  품목: {len(result['items'])}개")
            print(f"  총액: {result['total_price']:,}원")
        except Exception as e:
            print(f"  오류: {e}")
            results.append({
                "receipt_id": "",
                "store_name": "",
                "date": "",
                "items": [],
                "total_price": 0,
            })
        print()

    # result.json 저장
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"결과 저장 완료: {OUTPUT_PATH}")
    print(f"처리된 영수증: {len(results)}개")


if __name__ == "__main__":
    main()
