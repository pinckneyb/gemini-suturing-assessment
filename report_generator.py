from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from typing import Dict, Any

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for the report"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        # Section header style
        self.section_style = ParagraphStyle(
            'CustomSection',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        )
        
        # Normal text style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Result style
        self.result_style = ParagraphStyle(
            'CustomResult',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leftIndent=20
        )
    
    def generate_report(self, assessment_result: Dict[str, Any], filename: str):
        """Generate a PDF report from assessment results"""
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        
        # Title
        title = Paragraph("Suturing Assessment Report", self.title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Assessment date
        date_text = f"Assessment Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        date_para = Paragraph(date_text, self.normal_style)
        story.append(date_para)
        story.append(Spacer(1, 20))
        
        # Check if this is a VoP Simple Interrupted assessment
        if 'needle_perpendicular' in assessment_result:
            story.extend(self._create_vop_report(assessment_result))
        else:
            story.extend(self._create_generic_report(assessment_result))
        
        # Build PDF
        doc.build(story)
    
    def _create_vop_report(self, assessment_result: Dict[str, Any]):
        """Create VoP Simple Interrupted Suture report"""
        story = []
        
        # VoP Header
        vop_header = Paragraph("VERIFICATION OF PROFICIENCY - SIMPLE INTERRUPTED SUTURE", self.section_style)
        story.append(vop_header)
        story.append(Spacer(1, 15))
        
        # VoP Criteria Table
        table_data = [["Assessment Criteria", "Result"]]
        
        criteria_mapping = {
            "needle_perpendicular": "1. Passes needle perpendicular to skin on both sides of skin",
            "avoids_multiple_grasps": "2. Avoids multiple forceps grasps of skin",
            "square_knots": "3. Instrument ties with square knots",
            "appropriate_tension": "4. Approximates skin with appropriate tension",
            "suture_spacing": "5. Places sutures 0.5 - 1.0 cm apart",
            "skin_eversion": "6. Eversion of the skin edges",
            "economy_of_motion": "7. Economy of Time and Motion",
            "demonstrates_proficiency": "8. Final Rating / Demonstrates Proficiency"
        }
        
        for key, label in criteria_mapping.items():
            value = assessment_result.get(key, "ERROR")
            table_data.append([label, str(value)])
        
        # Create table
        table = Table(table_data, colWidths=[4*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Overall Result
        overall_result = assessment_result.get('demonstrates_proficiency', 'ERROR')
        result_header = Paragraph("OVERALL ASSESSMENT", self.section_style)
        story.append(result_header)
        
        result_text = f"Demonstrates Proficiency: {overall_result}"
        result_para = Paragraph(result_text, self.result_style)
        story.append(result_para)
        story.append(Spacer(1, 20))
        
        # Summative Comments
        summative_comments = assessment_result.get('summative_comments', '')
        if summative_comments:
            comments_header = Paragraph("SUMMATIVE COMMENTS", self.section_style)
            story.append(comments_header)
            
            comments_para = Paragraph(summative_comments, self.normal_style)
            story.append(comments_para)
            story.append(Spacer(1, 20))
        
        return story
    
    def _create_generic_report(self, assessment_result: Dict[str, Any]):
        """Create generic assessment report"""
        story = []
        
        # Overall Assessment
        overall = assessment_result.get('overall_assessment', {})
        pass_fail = overall.get('pass_fail', 'ERROR')
        
        overall_header = Paragraph("OVERALL ASSESSMENT", self.section_style)
        story.append(overall_header)
        
        result_text = f"Result: {pass_fail}"
        result_para = Paragraph(result_text, self.result_style)
        story.append(result_para)
        
        # Improvement areas
        improvement_areas = overall.get('improvement_areas', [])
        if improvement_areas:
            story.append(Spacer(1, 10))
            areas_header = Paragraph("Areas for Improvement:", self.normal_style)
            story.append(areas_header)
            
            for area in improvement_areas:
                area_text = f"• {area}"
                area_para = Paragraph(area_text, self.result_style)
                story.append(area_para)
        
        story.append(Spacer(1, 20))
        
        # Detailed Assessment Categories
        categories = [
            ("PREPARATION", assessment_result.get('preparation', {})),
            ("TECHNIQUE", assessment_result.get('technique', {})),
            ("ECONOMY OF MOTION", assessment_result.get('economy_of_motion', {})),
            ("SAFETY", assessment_result.get('safety', {}))
        ]
        
        for category_name, category_data in categories:
            if category_data:
                story.extend(self._create_category_section(category_name, category_data))
                story.append(Spacer(1, 15))
        
        # Detailed Feedback
        detailed_feedback = overall.get('detailed_feedback', '')
        if detailed_feedback:
            feedback_header = Paragraph("DETAILED FEEDBACK", self.section_style)
            story.append(feedback_header)
            
            feedback_para = Paragraph(detailed_feedback, self.normal_style)
            story.append(feedback_para)
            story.append(Spacer(1, 20))
        
        return story
    
    def _create_category_section(self, category_name: str, category_data: Dict[str, Any]):
        """Create a section for a specific assessment category"""
        elements = []
        
        # Category header
        header = Paragraph(category_name, self.section_style)
        elements.append(header)
        
        # Create table for category items
        table_data = [["Assessment Item", "Result"]]
        
        for key, value in category_data.items():
            if key != "overall_preparation" and key != "overall_technique" and key != "overall_economy" and key != "overall_safety":
                # Format the key for display
                display_key = key.replace('_', ' ').title()
                table_data.append([display_key, str(value)])
        
        # Add overall result
        overall_key = f"overall_{category_name.lower()}"
        if overall_key in category_data:
            table_data.append(["OVERALL", category_data[overall_key]])
        
        # Create table
        if len(table_data) > 1:  # More than just header
            table = Table(table_data, colWidths=[4*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
        
        return elements 