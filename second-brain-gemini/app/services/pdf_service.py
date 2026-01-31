"""
PDF generation service for analysis results.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from typing import Dict, Any
from pathlib import Path
import tempfile
from datetime import datetime
import re

# Import industry-standard BiDi library
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    BIDI_AVAILABLE = True
except ImportError:
    print("⚠️  python-bidi or arabic-reshaper not installed. Hebrew text may not render correctly.")
    BIDI_AVAILABLE = False
    get_display = None
    arabic_reshaper = None


class PDFService:
    """Service for generating PDF reports from analysis results."""
    
    @staticmethod
    def make_rtl(text: str) -> str:
        """
        Convert text to RTL visual order using industry-standard python-bidi library.
        
        This function uses the bidi.algorithm.get_display() function to properly handle
        bidirectional text (Hebrew/English mixed content) for PDF rendering.
        
        Key features:
        - Forces RTL base direction when Hebrew is detected
        - Protects HTML/XML tags from being reversed
        
        Args:
            text: Input text that may contain Hebrew characters and HTML tags
            
        Returns:
            Text converted to visual RTL order, ready for PDF rendering
        """
        if not text:
            return ""
        
        # Convert to string if needed
        text = str(text)
        
        # If bidi library is not available, return text as-is (with warning)
        if not BIDI_AVAILABLE:
            print("⚠️  python-bidi not available, returning text as-is")
            return text
        
        try:
            # Check if text contains Hebrew characters
            has_hebrew = any("\u0590" <= c <= "\u05FF" for c in text)
            
            # If no Hebrew, return as-is (no need for BiDi processing)
            if not has_hebrew:
                return text
            
            # Protect HTML/XML tags from being reversed
            # Strategy: Split text into parts (tags and content), process only content
            import re
            
            # Pattern to match HTML/XML tags
            tag_pattern = re.compile(r'<[^>]+>')
            
            # Split text into parts: tags and content
            parts = []
            last_end = 0
            
            for match in tag_pattern.finditer(text):
                # Add content before tag
                if match.start() > last_end:
                    content_part = text[last_end:match.start()]
                    if content_part:
                        parts.append(('content', content_part))
                
                # Add tag
                parts.append(('tag', match.group(0)))
                last_end = match.end()
            
            # Add remaining content
            if last_end < len(text):
                content_part = text[last_end:]
                if content_part:
                    parts.append(('content', content_part))
            
            # If no tags found, process directly
            if not any(p[0] == 'tag' for p in parts):
                if arabic_reshaper:
                    reshaped_text = arabic_reshaper.reshape(text)
                else:
                    reshaped_text = text
                # Use base_dir='R' to force RTL base direction for Hebrew text
                # This ensures Hebrew words appear in correct order relative to each other
                bidi_text = get_display(reshaped_text, base_dir='R')
                return bidi_text
            
            # Process each part: tags stay as-is, content gets BiDi processing
            result_parts = []
            for part_type, part_text in parts:
                if part_type == 'tag':
                    # Tags stay unchanged
                    result_parts.append(part_text)
                else:
                    # Process content with BiDi
                    if arabic_reshaper:
                        reshaped_content = arabic_reshaper.reshape(part_text)
                    else:
                        reshaped_content = part_text
                    # Use base_dir='R' to force RTL base direction for Hebrew text
                    # This ensures Hebrew words appear in correct order relative to each other
                    bidi_content = get_display(reshaped_content, base_dir='R')
                    result_parts.append(bidi_content)
            
            # Join all parts
            return ''.join(result_parts)
                
        except Exception as e:
            print(f"⚠️  Error in make_rtl: {e}, returning text as-is")
            import traceback
            traceback.print_exc()
            return text
    
    def __init__(self):
        """Initialize PDF service with Hebrew font support."""
        self.hebrew_font = "Helvetica"  # Default fallback
        self.hebrew_font_bold = "Helvetica-Bold"
        self.rtl = True
        
        # Get the base directory
        base_dir = Path(__file__).parent.parent
        
        # Try to find and register a Hebrew-supporting font
        # Priority: 1. Embedded Arial Unicode (always available), 2. System fonts
        hebrew_font_paths = [
            # Embedded font (best option - always available in project)
            (base_dir / "app" / "fonts" / "ArialUnicode.ttf", "ArialUnicode"),
            # macOS system fonts with Hebrew support (fallback)
            (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"), "ArialUnicode"),
            (Path("/Library/Fonts/Arial Unicode.ttf"), "ArialUnicode"),
            (Path("/System/Library/Fonts/SFHebrew.ttf"), "SFHebrew"),
        ]
        
        # Try to register Hebrew fonts
        font_registered = False
        bold_font_registered = False
        
        for font_path, font_name in hebrew_font_paths:
            if font_path.exists():
                try:
                    if "Bold" in str(font_path) or "Bold" in font_name:
                        if not bold_font_registered:
                            pdfmetrics.registerFont(TTFont('HebrewFontBold', str(font_path)))
                            self.hebrew_font_bold = "HebrewFontBold"
                            bold_font_registered = True
                            print(f"✅ Registered Hebrew bold font: {font_path}")
                    else:
                        if not font_registered:
                            pdfmetrics.registerFont(TTFont('HebrewFont', str(font_path)))
                            self.hebrew_font = "HebrewFont"
                            font_registered = True
                            print(f"✅ Registered Hebrew font: {font_path}")
                    
                    if font_registered and bold_font_registered:
                        break
                except Exception as e:
                    print(f"⚠️  Failed to register font {font_path}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        if not font_registered:
            print("⚠️  No Hebrew font found, using Helvetica (Hebrew will NOT display correctly)")
            print("💡 Tip: Noto Sans Hebrew should be downloaded automatically")
        else:
            # If we have regular but not bold, use regular for both
            if not bold_font_registered:
                self.hebrew_font_bold = self.hebrew_font
                print(f"   Using {self.hebrew_font} for both regular and bold")
    
    def create_pdf(self, analysis_data: Dict[str, Any]) -> str:
        """
        Create a PDF report from analysis data.
        
        Args:
            analysis_data: Dictionary containing the analysis results
            
        Returns:
            Path to the generated PDF file
        """
        # Create temporary PDF file
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf.close()
        pdf_path = temp_pdf.name
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Container for the 'Flowable' objects
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Determine font name to use
        font_name = self.hebrew_font if self.hebrew_font != "Helvetica" else 'Helvetica'
        font_name_bold = self.hebrew_font_bold if self.hebrew_font_bold != "Helvetica-Bold" else 'Helvetica-Bold'
        
        print(f"📝 Using font: {font_name} (bold: {font_name_bold}) for PDF generation")
        if font_name == "Helvetica":
            print("⚠️  WARNING: Using Helvetica - Hebrew text will NOT display correctly!")
            print("   Please ensure Arial Unicode MS is installed on your system.")
        
        # Custom styles for Hebrew (RTL)
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor='#667eea',
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=font_name_bold
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor='#764ba2',
            spaceAfter=12,
            spaceBefore=12,
            alignment=TA_RIGHT,
            fontName=font_name_bold
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_RIGHT,
            spaceAfter=12,
            fontName=font_name
        )
        
        # Title
        story.append(Paragraph(self.make_rtl("🧠 Second Brain - סיכום יומי"), title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Date
        date_str = analysis_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        story.append(Paragraph(self.make_rtl(f"תאריך: {date_str}"), normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Summary
        if analysis_data.get('summary'):
            story.append(Paragraph(self.make_rtl("סיכום כללי"), heading_style))
            story.append(Paragraph(self._clean_text(analysis_data['summary']), normal_style))
            story.append(Spacer(1, 0.5*cm))
        
        # Leadership Feedback
        if analysis_data.get('leadership_feedback'):
            story.append(Paragraph(self.make_rtl("💡 מנהיגות (Simon Sinek)"), heading_style))
            lf = analysis_data['leadership_feedback']
            
            if lf.get('the_why'):
                story.append(Paragraph(self.make_rtl(f"<b>הסיבה העמוקה:</b> {self._clean_text(lf['the_why'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if lf.get('circle_of_safety'):
                story.append(Paragraph(self.make_rtl(f"<b>מעגל הביטחון:</b> {self._clean_text(lf['circle_of_safety'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if lf.get('trust_building'):
                story.append(Paragraph(self.make_rtl(f"<b>בניית אמון:</b> {self._clean_text(lf['trust_building'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if lf.get('leadership_moments'):
                story.append(Paragraph(self.make_rtl(f"<b>רגעי מנהיגות:</b> {self._clean_text(lf['leadership_moments'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if lf.get('recommendations'):
                story.append(Paragraph(self.make_rtl(f"<b>המלצות:</b> {self._clean_text(lf['recommendations'])}"), normal_style))
            
            story.append(Spacer(1, 0.5*cm))
        
        # Strategy Feedback
        if analysis_data.get('strategy_feedback'):
            story.append(Paragraph(self.make_rtl("📈 אסטרטגיה"), heading_style))
            sf = analysis_data['strategy_feedback']
            
            if sf.get('operational_efficiency'):
                story.append(Paragraph(self.make_rtl(f"<b>יעילות תפעולית:</b> {self._clean_text(sf['operational_efficiency'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if sf.get('kpis') and isinstance(sf['kpis'], list):
                kpis_text = ", ".join([self._clean_text(kpi) for kpi in sf['kpis']])
                story.append(Paragraph(self.make_rtl(f"<b>מדדי ביצוע:</b> {kpis_text}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if sf.get('action_items') and isinstance(sf['action_items'], list):
                items_text = "<br/>".join([f"• {self._clean_text(item)}" for item in sf['action_items']])
                story.append(Paragraph(self.make_rtl(f"<b>משימות פעולה:</b><br/>{items_text}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if sf.get('strategic_gaps'):
                story.append(Paragraph(self.make_rtl(f"<b>פערים אסטרטגיים:</b> {self._clean_text(sf['strategic_gaps'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if sf.get('resource_allocation'):
                story.append(Paragraph(self.make_rtl(f"<b>הקצאת משאבים:</b> {self._clean_text(sf['resource_allocation'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if sf.get('recommendations'):
                story.append(Paragraph(self.make_rtl(f"<b>המלצות:</b> {self._clean_text(sf['recommendations'])}"), normal_style))
            
            story.append(Spacer(1, 0.5*cm))
        
        # Parenting Feedback
        if analysis_data.get('parenting_feedback'):
            story.append(Paragraph(self.make_rtl("👨‍👩‍👧 הורות (מכון אדלר)"), heading_style))
            pf = analysis_data['parenting_feedback']
            
            if pf.get('encouragement_analysis'):
                story.append(Paragraph(self.make_rtl(f"<b>ניתוח עידוד:</b> {self._clean_text(pf['encouragement_analysis'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if pf.get('atmosphere'):
                story.append(Paragraph(self.make_rtl(f"<b>אקלים:</b> {self._clean_text(pf['atmosphere'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if pf.get('cooperation'):
                story.append(Paragraph(self.make_rtl(f"<b>שיתוף פעולה:</b> {self._clean_text(pf['cooperation'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if pf.get('mutual_respect'):
                story.append(Paragraph(self.make_rtl(f"<b>כבוד הדדי:</b> {self._clean_text(pf['mutual_respect'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if pf.get('problem_solving'):
                story.append(Paragraph(self.make_rtl(f"<b>פתרון בעיות:</b> {self._clean_text(pf['problem_solving'])}"), normal_style))
                story.append(Spacer(1, 0.3*cm))
            
            if pf.get('recommendations'):
                story.append(Paragraph(self.make_rtl(f"<b>המלצות:</b> {self._clean_text(pf['recommendations'])}"), normal_style))
            
            story.append(Spacer(1, 0.5*cm))
        
        # Action Items
        if analysis_data.get('action_items') and isinstance(analysis_data['action_items'], list):
            story.append(Paragraph(self.make_rtl("✅ משימות פעולה"), heading_style))
            for item in analysis_data['action_items']:
                if isinstance(item, dict):
                    title = item.get('title', '')
                    priority = item.get('priority', '')
                    category = item.get('category', '')
                    description = item.get('description', '')
                    due_date = item.get('due_date', '')
                    
                    item_text = f"<b>{self._clean_text(title)}</b>"
                    if priority:
                        item_text += f" [עדיפות: {priority}]"
                    if category:
                        item_text += f" ({category})"
                    if due_date:
                        item_text += f" [תאריך יעד: {due_date}]"
                    if description:
                        item_text += f"<br/>{self._clean_text(description)}"
                    
                    story.append(Paragraph(self.make_rtl(item_text), normal_style))
                    story.append(Spacer(1, 0.2*cm))
                else:
                    story.append(Paragraph(self.make_rtl(f"• {self._clean_text(str(item))}"), normal_style))
                    story.append(Spacer(1, 0.2*cm))
            
            story.append(Spacer(1, 0.5*cm))
        
        # Insights
        if analysis_data.get('insights') and isinstance(analysis_data['insights'], list):
            story.append(Paragraph(self.make_rtl("💡 תובנות"), heading_style))
            for insight in analysis_data['insights']:
                story.append(Paragraph(self.make_rtl(f"• {self._clean_text(str(insight))}"), normal_style))
                story.append(Spacer(1, 0.2*cm))
        
        # Build PDF
        doc.build(story)
        
        return pdf_path
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and escape text for PDF rendering with Hebrew RTL support.
        
        Since ReportLab lacks native BiDi support, we reverse Hebrew characters
        so they appear correctly when rendered with TA_RIGHT alignment.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text safe for PDF with proper Hebrew RTL rendering
        """
        if not text:
            return ""
        
        # Convert to string if needed
        text = str(text)
        
        # Convert to RTL visual order using industry-standard python-bidi library
        # This is necessary because ReportLab doesn't support BiDi natively
        text = self.make_rtl(text)
        
        # Escape special characters for ReportLab
        # ReportLab uses XML-like syntax, so we need to escape &, <, >
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        return text


# Create singleton instance
pdf_service = PDFService()
