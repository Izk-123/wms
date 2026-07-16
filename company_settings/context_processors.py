from .services import get_company, get_setting

def company_settings(request):
    company = get_company()
    return {
        "company": company,
        "currency_symbol": company.currency_symbol if company else "MK",
        "company_name": company.name if company else "J&N WMS",
        "company_email": company.email if company else "",
        "company_phone": company.phone if company else "",
        "company_logo": company.logo.url if company and company.logo else None,
        "invoice_prefix": get_setting("INVOICE_PREFIX", "INV-"),
        "receipt_prefix": get_setting("RECEIPT_PREFIX", "REC-"),
        "po_prefix": get_setting("PO_PREFIX", "PO-"),
        "payment_terms": get_setting("DEFAULT_PAYMENT_TERMS", "Net 30"),
        "tax_rate": get_setting("DEFAULT_TAX_RATE", 0.0),
    }