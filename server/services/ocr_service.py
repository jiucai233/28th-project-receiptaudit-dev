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
import multiprocessing

from core.ocr_engine.paddle_wrapper import PaddleOCRWrapper
from core.ocr_engine.processor import ReceiptProcessor

logger = logging.getLogger(__name__)

def _run_ocr_subprocess(image_path: str, result_queue: multiprocessing.Queue):
    """
    Subprocess worker for PaddleOCR extraction.
    This guarantees that all memory allocated by C++ backends (OpenMP/MKL/MPS)
    is completely reclaimed by the OS when the process exits.
    """
    try:
        wrapper = PaddleOCRWrapper()
        lines = wrapper.extract(image_path)
        result_queue.put({"success": True, "data": lines})
    except Exception as e:
        import traceback
        result_queue.put({"success": False, "error": str(e), "traceback": traceback.format_exc()})


class OCRService:
    _processor = None

    def _get_processor(self):
        if OCRService._processor is None:
            OCRService._processor = ReceiptProcessor()
        return OCRService._processor

    def extract(self, image_path: Path, receipt_id: str) -> dict:
        print(f"\n[OCR] >>> Processing {receipt_id} using Subprocess Engine <<<")
        try:
            processor = self._get_processor()

            # 1. Use Subprocess to extract merged lines (Memory Leak Protection)
            ctx = multiprocessing.get_context("spawn")
            queue = ctx.Queue()
            p = ctx.Process(target=_run_ocr_subprocess, args=(str(image_path), queue))
            p.start()
            p.join(timeout=600) # 60 seconds timeout for OCR
            
            if p.is_alive():
                p.terminate()
                p.join()
                raise TimeoutError("OCR subprocess timed out and was terminated.")

            if queue.empty():
                raise RuntimeError("OCR subprocess exited without returning data.")

            result = queue.get()
            if not result.get("success"):
                raise RuntimeError(f"OCR Subprocess Failed: {result.get('error')}\n{result.get('traceback')}")

            ocr_lines = result["data"]
            print(f"[OCR] Subprocess extracted {len(ocr_lines)} merged lines.")

            # 2. Use the core processor to get structured JSON
            final_result = processor.process(ocr_lines)
            
            # 3. Ensure receipt_id is consistent
            final_result["receipt_id"] = receipt_id
            
            # Logging results for debugging
            print(f"[OCR] Processed Store: {final_result.get('store_name')}")
            print(f"[OCR] Total Items: {len(final_result.get('items', []))}")
            print(f"[OCR] Total Price: {final_result.get('total_price')}")
            
            return final_result

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
