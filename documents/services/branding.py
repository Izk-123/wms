# documents/services/branding.py
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from company_settings.services import get_company

def get_company_data():
    company = get_company()
    return {
        'name': company.name if company else "J&N WMS",
        'address': company.physical_address or '',
        'phone': company.phone or '',
        'email': company.email or '',
        'currency': company.currency_symbol if company else "MK",
        'logo_path': company.logo.path if company and company.logo else None,
    }

def get_document_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CompanyTitle',
        parent=styles['Title'],
        fontSize=16,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='CompanyHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='RightAlign',
        parent=styles['Normal'],
        alignment=2,
    ))
    styles.add(ParagraphStyle(
        name='CenterAlign',
        parent=styles['Normal'],
        alignment=1,
    ))
    return styles