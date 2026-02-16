from __future__ import annotations

import os
# Environment flags are already handled in app.py and paddle_wrapper.py
# but keeping them here for safety if used standalone.
os.environ["PADDLEX_INITIALIZED"] = "True"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import sys
from datetime import datetime
from pathlib import Path
import logging

from core.ocr_engine.paddle_wrapper import PaddleOCRWrapper
from core.ocr_engine.processor import ReceiptProcessor

logger = logging.getLogger(__name__)

class OCRService:
    _ocr_wrapper = None
    _processor = None

    def _get_resources(self):
        if OCRService._ocr_wrapper is None:
            try:
                print("[OCR] Initializing Core OCR Wrapper & Processor...")
                # The wrapper handles PaddleOCR initialization and environment flags
                OCRService._ocr_wrapper = PaddleOCRWrapper()
                OCRService._processor = ReceiptProcessor()
                print("[OCR] Core Resources Initialized.")
            except Exception as e:
                print(f"[OCR] INIT FAILED: {str(e)}")
                import traceback
                traceback.print_exc()
        return OCRService._ocr_wrapper, OCRService._processor

    def extract(self, image_path: Path, receipt_id: str) -> dict:
        print(f"\n[OCR] >>> Processing {receipt_id} using Core Engine <<<")
        try:
            wrapper, processor = self._get_resources()
            if not wrapper:
                return self._fallback(receipt_id, "Engine Init Failed")

            # 1. Use the core wrapper to extract merged lines
            # This handles the complex result structure automatically
            ocr_lines = wrapper.extract(str(image_path))
            print(f"[OCR] Core Wrapper extracted {len(ocr_lines)} merged lines.")

            # 2. Use the core processor to get structured JSON
            result = processor.process(ocr_lines)
            
            # 3. Ensure receipt_id is consistent
            result["receipt_id"] = receipt_id
            
            # Logging results for debugging
            print(f"[OCR] Processed Store: {result.get('store_name')}")
            print(f"[OCR] Total Items: {len(result.get('items', []))}")
            print(f"[OCR] Total Price: {result.get('total_price')}")
            
            return result

        except Exception as e:
            print(f"[OCR] Core Processing Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._fallback(receipt_id, str(e))

    def _fallback(self, receipt_id: str, error_msg: str = "") -> dict:
        return {
            "receipt_id": receipt_id,
            "store_name": "Unknown Store (Error)",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "items": [],
            "total_price": 0,
        }
