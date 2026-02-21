from __future__ import annotations

from io import BytesIO


class ReportService:
    def _fallback_pdf(self, receipt_data: dict, audit_result: dict) -> bytes:
        def esc(s: str) -> str:
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        lines = [
            "Transparent-Audit Report",
            f"Receipt ID: {receipt_data.get('receipt_id', '')}",
            f"Store: {receipt_data.get('store_name', '')}",
            f"Decision: {audit_result.get('audit_decision', '')}",
            f"Score: {audit_result.get('violation_score', 0.0)}",
            f"Reasoning: {audit_result.get('reasoning', '')}",
        ]

        cmd = ["BT", "/F1 12 Tf", "72 780 Td"]
        first = True
        for line in lines:
            if first:
                cmd.append(f"({esc(line)}) Tj")
                first = False
            else:
                cmd.append("0 -16 Td")
                cmd.append(f"({esc(line)}) Tj")
        cmd.append("ET")
        content = "\n".join(cmd).encode("latin-1", errors="replace")

        objs = [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            b"5 0 obj << /Length " + str(len(content)).encode("ascii") + b" >> stream\n" + content + b"\nendstream endobj\n",
        ]

        buf = BytesIO()
        buf.write(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objs:
            offsets.append(buf.tell())
            buf.write(obj)

        start = buf.tell()
        buf.write(f"xref\n0 {len(objs)+1}\n".encode("ascii"))
        buf.write(b"0000000000 65535 f \n")
        for i in range(1, len(objs) + 1):
            buf.write(f"{offsets[i]:010} 00000 n \n".encode("ascii"))
        buf.write(f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\n".encode("ascii"))
        buf.write(f"startxref\n{start}\n%%EOF\n".encode("ascii"))
        return buf.getvalue()

    def build_pdf(self, receipt_data: dict, audit_result: dict) -> bytes:
        try:
            from pathlib import Path

            from core.report_engine.generator import AuditReportGenerator

            path = AuditReportGenerator().generate(receipt_data, audit_result)
            return Path(path).read_bytes()
        except Exception:
            return self._fallback_pdf(receipt_data, audit_result)

    def build_batch_pdf(self, batch_data: list[tuple[dict, dict]]) -> bytes:
        try:
            from pathlib import Path
            from core.report_engine.generator import AuditReportGenerator

            path = AuditReportGenerator().generate_batch(batch_data)
            return Path(path).read_bytes()
        except Exception as e:
            # Fallback to building multiple PDFs and returning the first if batch fails,
            # or ideally combine them. For simplicity, if batch fails we raise exception.
            raise Exception(f"Failed to generate batch PDF: {e}")
