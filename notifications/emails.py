from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone

from .models import NotificationLog


def _send_email(
    recipient_user,
    recipient_email,
    subject,
    template_name,
    context,
    notification_type,
):
    """
    Central email sending function.
    Renders an HTML template, sends the email,
    and logs the result in NotificationLog.
    """
    # Add shared context variables
    context['subject'] = subject
    context['year'] = timezone.now().year
    context['site_name'] = 'J&N WMS'

    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    log = NotificationLog.objects.create(
        notification_type=notification_type,
        recipient=recipient_user,
        recipient_email=recipient_email,
        subject=subject,
        status='pending',
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        log.status = 'sent'
        log.save()

    except Exception as e:
        log.status = 'failed'
        log.error_message = str(e)
        log.save()


# ─────────────────────────────────────────
# PUBLIC EMAIL FUNCTIONS
# ─────────────────────────────────────────

def send_low_stock_alert(low_stock_items, recipients):
    """
    Send low stock alert to Warehouse Managers.
    recipients: list of User objects.
    low_stock_items: queryset of Stock objects.
    """
    if not low_stock_items:
        return

    from django.conf import settings
    dashboard_url = getattr(
        settings, 'SITE_URL', 'http://127.0.0.1:8000'
    ) + '/inventory/stock/?low_stock=1'

    for user in recipients:
        _send_email(
            recipient_user=user,
            recipient_email=user.email,
            subject=f"⚠ Low Stock Alert — {len(list(low_stock_items))} items need attention",
            template_name='notifications/email/low_stock.html',
            context={
                'recipient_name': user.get_full_name() or user.username,
                'low_stock_items': low_stock_items,
                'dashboard_url': dashboard_url,
            },
            notification_type='low_stock',
        )


def send_purchase_request_approval_needed(purchase_request, approvers):
    """
    Notify approvers when a PR is submitted.
    approvers: list of User objects with approve_purchaserequest permission.
    """
    from django.conf import settings
    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    pr_url = f"{base_url}/procurement/requests/{purchase_request.pk}/"

    for user in approvers:
        _send_email(
            recipient_user=user,
            recipient_email=user.email,
            subject=f"Action Required: Purchase Request {purchase_request.reference} awaits approval",
            template_name='notifications/email/pr_approval_required.html',
            context={
                'recipient_name': user.get_full_name() or user.username,
                'pr': purchase_request,
                'pr_url': pr_url,
            },
            notification_type='approval_required',
        )


def send_purchase_request_decision(purchase_request):
    """
    Notify the requester when their PR is approved or rejected.
    """
    from django.conf import settings
    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    pr_url = f"{base_url}/procurement/requests/{purchase_request.pk}/"

    requester = purchase_request.requested_by
    status = purchase_request.status  # 'approved' or 'rejected'

    _send_email(
        recipient_user=requester,
        recipient_email=requester.email,
        subject=f"Your Purchase Request {purchase_request.reference} has been {status}",
        template_name='notifications/email/request_status.html',
        context={
            'recipient_name': requester.get_full_name() or requester.username,
            'request_type': 'Purchase Request',
            'reference': purchase_request.reference,
            'status': status,
            'actioned_by': purchase_request.approved_by.get_full_name()
                           if purchase_request.approved_by else 'System',
            'actioned_at': purchase_request.approved_at,
            'reason': purchase_request.rejection_reason,
            'detail_url': pr_url,
        },
        notification_type='approved' if status == 'approved' else 'rejected',
    )


def send_material_request_approval_needed(material_request, approvers):
    """
    Notify approvers when a Material Request is submitted.
    """
    from django.conf import settings
    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    mr_url = f"{base_url}/operations/requests/{material_request.pk}/"

    for user in approvers:
        _send_email(
            recipient_user=user,
            recipient_email=user.email,
            subject=f"Action Required: Material Request {material_request.reference} awaits approval",
            template_name='notifications/email/mr_approval_required.html',
            context={
                'recipient_name': user.get_full_name() or user.username,
                'mr': material_request,
                'mr_url': mr_url,
            },
            notification_type='approval_required',
        )


def send_material_request_decision(material_request):
    """
    Notify the requester when their MR is approved or rejected.
    """
    from django.conf import settings
    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    mr_url = f"{base_url}/operations/requests/{material_request.pk}/"

    requester = material_request.requested_by
    status = material_request.status

    _send_email(
        recipient_user=requester,
        recipient_email=requester.email,
        subject=f"Your Material Request {material_request.reference} has been {status}",
        template_name='notifications/email/request_status.html',
        context={
            'recipient_name': requester.get_full_name() or requester.username,
            'request_type': 'Material Request',
            'reference': material_request.reference,
            'status': status,
            'actioned_by': material_request.approved_by.get_full_name()
                           if material_request.approved_by else 'System',
            'actioned_at': material_request.approved_at,
            'reason': material_request.rejection_reason,
            'detail_url': mr_url,
        },
        notification_type='approved' if status == 'approved' else 'rejected',
    )


def send_goods_received_notification(goods_receipt, recipients):
    """
    Notify Warehouse Manager and Procurement Officer when a GRN is confirmed.
    """
    from django.conf import settings
    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    grn_url = f"{base_url}/procurement/grn/{goods_receipt.pk}/"

    for user in recipients:
        _send_email(
            recipient_user=user,
            recipient_email=user.email,
            subject=f"Goods Received: {goods_receipt.reference} — {goods_receipt.purchase_order.supplier.name}",
            template_name='notifications/email/goods_received.html',
            context={
                'recipient_name': user.get_full_name() or user.username,
                'grn': goods_receipt,
                'grn_url': grn_url,
            },
            notification_type='goods_received',
        )