from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


class OCRService:
    def _fallback(self, receipt_id: str) -> dict:
        return {
            "receipt_id": receipt_id,
            "store_name": "Unknown Store",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "items": [{"id": 1, "name": "식비", "unit_price": 10000, "count": 1, "price": 10000}],
            "total_price": 10000,
        }

    def _parse_line(self, line: str, idx: int) -> dict | None:
        nums = re.findall(r"\d{1,3}(?:,\d{3})+|\d+", line)
        if not nums:
            return None
        name = re.sub(r"\d", "", line).strip(" -:\t")
        if len(name) < 2:
            return None
        price = int(nums[-1].replace(",", ""))
        return {"id": idx, "name": name[:40], "unit_price": price, "count": 1, "price": price}

    def extract(self, image_path: Path, receipt_id: str) -> dict:
        try:
            from paddleocr import PaddleOCR  # type: ignore

            ocr = PaddleOCR(use_angle_cls=True, lang="korean")
            raw = ocr.ocr(str(image_path), cls=True)
            lines = []
            for page in raw:
                if not page:
                    continue
                for chunk in page:
                    text = chunk[1][0] if len(chunk) > 1 else ""
                    text = (text or "").strip()
                    if text:
                        lines.append(text)

            if not lines:
                return self._fallback(receipt_id)

            items = []
            idx = 1
            for line in lines:
                parsed = self._parse_line(line, idx)
                if parsed:
                    items.append(parsed)
                    idx += 1

            if not items:
                return self._fallback(receipt_id)

            return {
                "receipt_id": receipt_id,
                "store_name": lines[0][:60],
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "items": items,
                "total_price": sum(x["price"] for x in items),
            }
        except Exception:
            return self._fallback(receipt_id)
