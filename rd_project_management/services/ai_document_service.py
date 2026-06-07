"""
AI Document Service - Save AI-generated analyses as project documents.
Automatically saves PDFs and Word documents when AI analyses are run.
"""
import os
import uuid
import logging
from datetime import datetime
from io import BytesIO

logger = logging.getLogger(__name__)


def save_ai_analysis_pdf(project, analysis_type, content, user_id=None):
    """
    Save AI analysis result as PDF in project documents.

    Args:
        project: Project model instance
        analysis_type: Type of analysis (risks, report, matching, document_analysis)
        content: Dict or string with analysis content
        user_id: ID of user who ran the analysis

    Returns:
        ProjectDocument instance or None if failed
    """
    from flask import current_app
    from models import db, ProjectDocument

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm

        # Generate PDF content
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=20
        )
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a237e'),
            spaceBefore=15,
            spaceAfter=10
        )

        # Title based on analysis type
        type_titles = {
            'risks': 'Análise de Riscos',
            'report': 'Relatório do Projeto',
            'matching': 'Matching com Editais',
            'document_analysis': 'Análise de Documento'
        }

        title = type_titles.get(analysis_type, 'Análise IA')
        story.append(Paragraph(f"{title} - {project.code}", title_style))
        story.append(Paragraph(f"Projeto: {project.title}", styles['Normal']))
        story.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))

        # Process content based on type
        if analysis_type == 'risks':
            _add_risks_content(story, content, styles, section_style)
        elif analysis_type == 'report':
            _add_report_content(story, content, styles, section_style)
        elif analysis_type == 'matching':
            _add_matching_content(story, content, styles, section_style)
        elif analysis_type == 'document_analysis':
            _add_document_analysis_content(story, content, styles, section_style)

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "<i>Documento gerado automaticamente pelo Orion PMO IA</i>",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=colors.gray)
        ))

        doc.build(story)
        pdf_content = buffer.getvalue()

        # Save to file
        filename = f"{analysis_type}_{project.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        stored_filename = f"{uuid.uuid4().hex}.pdf"

        tenant_folder = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'uploads'),
            str(project.tenant_id or 'global')
        )
        os.makedirs(tenant_folder, exist_ok=True)

        file_path = os.path.join(tenant_folder, stored_filename)
        with open(file_path, 'wb') as f:
            f.write(pdf_content)

        # Create document record
        doc_record = ProjectDocument(
            tenant_id=project.tenant_id,
            project_id=project.id,
            filename=filename,
            stored_filename=stored_filename,
            file_type='pdf',
            file_size=len(pdf_content),
            description=f"{title} gerado por IA em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            uploaded_by_id=user_id
        )

        db.session.add(doc_record)
        db.session.commit()

        logger.info(f"Saved AI analysis PDF: {filename} for project {project.code}")
        return doc_record

    except Exception as e:
        logger.error(f"Error saving AI analysis PDF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def save_proposal_word(project, call, proposal_content, user_id=None):
    """
    Save generated proposal as Word document in project documents.

    Args:
        project: Project model instance
        call: PublicCall model instance
        proposal_content: Markdown/text content of the proposal
        user_id: ID of user who generated the proposal

    Returns:
        ProjectDocument instance or None if failed
    """
    from flask import current_app
    from models import db, ProjectDocument

    try:
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Title
        title = doc.add_heading(f'Proposta - {project.title}', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Metadata
        doc.add_paragraph(f"Projeto: {project.code} - {project.title}")
        doc.add_paragraph(f"Edital: {call.source} - {call.title}")
        doc.add_paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        doc.add_paragraph()

        # Parse markdown content and add to document
        lines = proposal_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Handle headers
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('- ') or line.startswith('* '):
                doc.add_paragraph(line[2:], style='List Bullet')
            elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
                doc.add_paragraph(line[3:], style='List Number')
            else:
                # Regular paragraph - remove markdown bold/italic
                clean_line = line.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                doc.add_paragraph(clean_line)

        # Footer
        doc.add_paragraph()
        footer = doc.add_paragraph("Documento gerado automaticamente pelo Orion PMO IA")
        footer.italic = True

        # Save to bytes
        buffer = BytesIO()
        doc.save(buffer)
        docx_content = buffer.getvalue()

        # Save to file
        filename = f"proposta_{project.code}_{call.source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        stored_filename = f"{uuid.uuid4().hex}.docx"

        tenant_folder = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'uploads'),
            str(project.tenant_id or 'global')
        )
        os.makedirs(tenant_folder, exist_ok=True)

        file_path = os.path.join(tenant_folder, stored_filename)
        with open(file_path, 'wb') as f:
            f.write(docx_content)

        # Create document record
        doc_record = ProjectDocument(
            tenant_id=project.tenant_id,
            project_id=project.id,
            filename=filename,
            stored_filename=stored_filename,
            file_type='docx',
            file_size=len(docx_content),
            description=f"Proposta para {call.source} gerada por IA em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            uploaded_by_id=user_id
        )

        db.session.add(doc_record)
        db.session.commit()

        logger.info(f"Saved proposal Word document: {filename} for project {project.code}")
        return doc_record

    except Exception as e:
        logger.error(f"Error saving proposal Word document: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def _add_risks_content(story, content, styles, section_style):
    """Add risk analysis content to PDF."""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    if isinstance(content, dict):
        # Summary
        if content.get('summary'):
            story.append(Paragraph("Resumo", section_style))
            story.append(Paragraph(content['summary'], styles['Normal']))
            story.append(Spacer(1, 15))

        # Risks
        risks = content.get('risks', [])
        if risks:
            story.append(Paragraph(f"Riscos Identificados ({len(risks)})", section_style))
            for i, risk in enumerate(risks, 1):
                severity_color = '#dc3545' if risk.get('severity') == 'high' else '#ffc107' if risk.get('severity') == 'medium' else '#17a2b8'
                story.append(Paragraph(f"<b>{i}. {risk.get('title', 'Risco')}</b>", styles['Normal']))
                story.append(Paragraph(f"Descrição: {risk.get('description', '')}", styles['Normal']))
                story.append(Paragraph(f"Severidade: <font color='{severity_color}'>{risk.get('severity', 'N/A').upper()}</font>", styles['Normal']))
                if risk.get('mitigation'):
                    story.append(Paragraph(f"Mitigação: {risk.get('mitigation')}", styles['Normal']))
                story.append(Spacer(1, 10))

        # Recommendations
        recommendations = content.get('recommendations', [])
        if recommendations:
            story.append(Paragraph("Recomendações", section_style))
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", styles['Normal']))
    else:
        story.append(Paragraph(str(content), styles['Normal']))


def _add_report_content(story, content, styles, section_style):
    """Add report content to PDF."""
    from reportlab.platypus import Paragraph, Spacer

    if isinstance(content, str):
        # Parse markdown-like content
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 10))
            elif line.startswith('# '):
                story.append(Paragraph(line[2:], section_style))
            elif line.startswith('## '):
                story.append(Paragraph(f"<b>{line[3:]}</b>", styles['Normal']))
            elif line.startswith('- ') or line.startswith('* '):
                story.append(Paragraph(f"• {line[2:]}", styles['Normal']))
            else:
                clean_line = line.replace('**', '').replace('*', '')
                story.append(Paragraph(clean_line, styles['Normal']))
    elif isinstance(content, dict):
        if content.get('report'):
            _add_report_content(story, content['report'], styles, section_style)


def _add_matching_content(story, content, styles, section_style):
    """Add matching results content to PDF."""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    matches = content.get('matches', []) if isinstance(content, dict) else content

    if matches:
        story.append(Paragraph(f"Editais Compatíveis ({len(matches)})", section_style))

        for i, match in enumerate(matches, 1):
            score = match.get('score', 0)
            score_color = '#28a745' if score >= 80 else '#ffc107' if score >= 60 else '#dc3545'

            story.append(Paragraph(f"<b>{i}. {match.get('call_title', 'Edital')}</b>", styles['Normal']))
            story.append(Paragraph(f"Fonte: {match.get('call_source', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"Compatibilidade: <font color='{score_color}'><b>{score}%</b></font>", styles['Normal']))

            if match.get('reasons'):
                story.append(Paragraph("Motivos:", styles['Normal']))
                for reason in match['reasons']:
                    story.append(Paragraph(f"  • {reason}", styles['Normal']))

            if match.get('call_deadline'):
                story.append(Paragraph(f"Prazo: {match['call_deadline']}", styles['Normal']))

            story.append(Spacer(1, 15))
    else:
        story.append(Paragraph("Nenhum edital compatível encontrado.", styles['Normal']))


def _add_document_analysis_content(story, content, styles, section_style):
    """Add document analysis content to PDF."""
    from reportlab.platypus import Paragraph, Spacer

    if isinstance(content, dict):
        # Summary
        if content.get('summary'):
            story.append(Paragraph("Resumo", section_style))
            story.append(Paragraph(content['summary'], styles['Normal']))
            story.append(Spacer(1, 15))

        # Key points
        if content.get('key_points'):
            story.append(Paragraph("Pontos Principais", section_style))
            for point in content['key_points']:
                story.append(Paragraph(f"• {point}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Requirements
        if content.get('requirements'):
            story.append(Paragraph("Requisitos Identificados", section_style))
            for req in content['requirements']:
                story.append(Paragraph(f"• {req}", styles['Normal']))
            story.append(Spacer(1, 15))

        # Analysis
        if content.get('analysis'):
            story.append(Paragraph("Análise Detalhada", section_style))
            story.append(Paragraph(content['analysis'], styles['Normal']))
    else:
        story.append(Paragraph(str(content), styles['Normal']))
