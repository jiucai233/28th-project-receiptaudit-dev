# -*- coding: utf-8 -*-
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class AuditReportGenerator:
    """
    Premium PDF report generator using ReportLab and NanumSquare fonts.
    Supports complex Korean characters and professional layouts.
    """
    
    def __init__(self) -> None:
        """
        Initializes the report generator and registers NanumSquare fonts.
        """
        self.styles = getSampleStyleSheet()
        
        # Resolve project root and font directory
        self.project_root = Path(__file__).parent.absolute().parent.parent
        font_dir = self.project_root / "nanum-square"
        
        # Font variant mapping
        self.font_family = "NanumSquare"
        font_variants = {
            "Regular": "NanumSquareR.ttf",
            "Bold": "NanumSquareB.ttf",
            "ExtraBold": "NanumSquareEB.ttf",
            "Light": "NanumSquareL.ttf"
        }
        
        # Register fonts
        for name, filename in font_variants.items():
            font_path = font_dir / filename
            if not font_path.exists():
                font_path = font_dir / filename.replace("NanumSquare", "NanumSquare_ac")
            
            if font_path.exists():
                pdfmetrics.registerFont(TTFont(f"{self.font_family}-{name}", font_path))
            else:
                print(f"Warning: Font {filename} not found in {font_dir}")

        # Create custom styles
        self._create_styles()

    def _create_styles(self) -> None:
        """Defines custom ParagraphStyles for the report."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontName=f'{self.font_family}-ExtraBold',
            fontSize=24,
            textColor=HexColor("#1f77b4"),
            alignment=1,
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontName=f'{self.font_family}-Bold',
            fontSize=14,
            backColor=HexColor("#f5f7f9"),
            leftIndent=5,
            padding=5,
            spaceBefore=15,
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='NormalKorean',
            fontName=f'{self.font_family}-Regular',
            fontSize=10,
            leading=14
        ))

    def generate(self, receipt_data: Dict[str, Any], audit_result: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Generates a professionally styled PDF report.

        Args:
            receipt_data: Dictionary with receipt details.
            audit_result: Dictionary with AI audit findings.
            output_path: File path to save the PDF. If None, saves to web/cache.

        Returns:
            Absolute path to the generated PDF.
        """
        # Default path to web/cache if not provided
        if output_path is None:
            cache_dir = self.project_root / "web" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_report_{receipt_data.get('receipt_id', 'unknown')}_{timestamp}.pdf"
            output_path = str(cache_dir / filename)

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        elements = []

        # 1. Header
        elements.append(Paragraph("감사 결과 보고서", self.styles['ReportTitle']))
        elements.append(Paragraph("Transparent-Audit: Smart Receipt Audit System", 
                                 ParagraphStyle('Sub', fontName=f'{self.font_family}-Light', fontSize=10, alignment=1, textColor=colors.grey)))
        elements.append(Paragraph(f"보고서 생성일: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                 ParagraphStyle('Date', fontName=f'{self.font_family}-Regular', fontSize=9, alignment=2)))
        elements.append(Spacer(1, 10))

        # 2. Summary Section
        elements.append(Paragraph("1. 감사 요약 (Summary)", self.styles['SectionHeader']))
        
        summary_data = [
            ["영수증 ID", receipt_data.get('receipt_id', 'N/A')],
            ["가맹점명", receipt_data.get('store_name', 'N/A')],
            ["총 결제 금액", f"{receipt_data.get('total_price', 0):,} 원"],
            ["감사 판정", audit_result.get("audit_decision", "Unknown")]
        ]
        
        summary_table = Table(summary_data, colWidths=[100, 350])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), f'{self.font_family}-Regular'),
            ('FONTNAME', (0,0), (0,-1), f'{self.font_family}-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(summary_table)

        # 3. Item Details Section
        elements.append(Paragraph("2. 품목 명세 (Item Details)", self.styles['SectionHeader']))
        
        item_data = [["품목명", "단가", "수량", "금액"]]
        for item in receipt_data.get("items", []):
            item_data.append([
                item.get('name', ''),
                f"{item.get('unit_price', 0):,}",
                str(item.get('count', 0)),
                f"{item.get('price', 0):,}"
            ])
            
        item_table = Table(item_data, colWidths=[200, 80, 50, 100])
        item_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), f'{self.font_family}-Regular'),
            ('FONTNAME', (0,0), (-1,0), f'{self.font_family}-Bold'),
            ('BACKGROUND', (0,0), (-1,0), HexColor("#e6ebf0")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ]))
        elements.append(item_table)

        # 4. AI Reasoning Section
        elements.append(Paragraph("3. AI 상세 감사 의견 (AI Reasoning)", self.styles['SectionHeader']))
        elements.append(Paragraph(audit_result.get("reasoning", "의견 없음"), self.styles['NormalKorean']))

        # Build PDF
        doc.build(elements)
        return str(Path(output_path).absolute())

if __name__ == "__main__":
    # Test generation into web/cache
    try:
        gen = AuditReportGenerator()
        res_path = gen.generate(
            {"receipt_id": "RCPT-WEB-CACHE", "store_name": "Cache Test Store", "total_price": 15000, "items": [{"name": "Sample Item", "unit_price": 15000, "count": 1, "price": 15000}]},
            {"audit_decision": "Pass", "reasoning": "This is a cached generation test."},
        )
        print(f"PDF generated successfully at: {res_path}")
    except Exception as e:
        print(f"Error during report generation: {e}")