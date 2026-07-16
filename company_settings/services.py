from datetime import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from .models import ApprovalRule, ApprovalRequest
from accounts.models import User, Role
from .models import Company, PaymentMethod, SystemSetting
from django.core.cache import cache

def get_company():
    """Return the single Company instance (cached)."""
    cache_key = "company_profile"
    company = cache.get(cache_key)
    if not company:
        try:
            company = Company.objects.first()
            cache.set(cache_key, company, 60 * 60)  # 1 hour
        except Company.DoesNotExist:
            company = None
    return company

def get_setting(key, default=None):
    """Get a system setting by key, return typed value."""
    cache_key = f"settings_{key}"
    value = cache.get(cache_key)
    if value is not None:
        return value

    try:
        setting = SystemSetting.objects.get(key=key)
        value = setting.typed_value
    except SystemSetting.DoesNotExist:
        value = default

    cache.set(cache_key, value, 60 * 60)  # 1 hour
    return value

def get_payment_methods():
    """Return list of active payment methods."""
    cache_key = "active_payment_methods"
    methods = cache.get(cache_key)
    if methods is None:
        methods = list(PaymentMethod.objects.filter(is_active=True).values("code", "name"))
        cache.set(cache_key, methods, 60 * 60)
    return methods


def get_approval_required(action, amount):
    """
    Returns the Role required to approve the given action/amount,
    or None if no approval is needed.
    """
    rule = ApprovalRule.objects.filter(
        action=action,
        min_amount__lte=amount,
        is_active=True
    ).order_by('-min_amount').first()

    if rule and (rule.max_amount is None or amount <= rule.max_amount):
        return rule.required_role
    return None

def user_can_approve(user, action, amount):
    """
    Check if the user's role is sufficient to approve the action/amount.
    Uses role level hierarchy (higher level = more authority).
    """
    required_role = get_approval_required(action, amount)
    if not required_role:
        return True  # no approval needed
    if not user.role:
        return False
    # Role level: higher = more authority
    return user.role.level >= required_role.level

def create_approval_request(user, action, amount, reference="", notes="", content_object=None):
    """
    Create a pending approval request.
    Returns the ApprovalRequest object.
    """
    if not get_approval_required(action, amount):
        raise ValidationError("This action does not require approval.")

    request = ApprovalRequest.objects.create(
        action=action,
        reference=reference,
        amount=amount,
        requested_by=user,
        notes=notes,
        status='pending'
    )

    if content_object:
        ct = ContentType.objects.get_for_model(content_object)
        request.content_type = ct
        request.object_id = content_object.pk
        request.save()

    # Notify approvers
    required_role = get_approval_required(action, amount)
    if required_role:
        notify_approvers(request, required_role)

    return request

def notify_approvers(approval_request, required_role):
    """
    Send notification to all users with the required role.
    """
    from notifications.sender import notify_users
    approvers = User.objects.filter(role=required_role, is_active=True)
    if approvers:
        notify_users(
            users=approvers,
            title=f"Approval Needed: {approval_request.action}",
            message=f"{approval_request.reference} – Amount: MWK {approval_request.amount} requires your approval.",
            notification_type='approval_required',
            level='warning',
            url=f"/settings/approvals/{approval_request.pk}/",
        )

def approve_request(approval_request, approver, note=""):
    """
    Approve a pending request.
    """
    if approval_request.status != 'pending':
        raise ValidationError("This request is no longer pending.")
    if not user_can_approve(approver, approval_request.action, approval_request.amount):
        raise ValidationError("You do not have permission to approve this request.")
    approval_request.status = 'approved'
    approval_request.approved_by = approver
    approval_request.approved_at = timezone.now()
    if note:
        approval_request.notes += f"\nApproved: {note}"
    approval_request.save()
    return approval_request

def reject_request(approval_request, approver, reason):
    """
    Reject a pending request with a reason.
    """
    if approval_request.status != 'pending':
        raise ValidationError("This request is no longer pending.")
    if not user_can_approve(approver, approval_request.action, approval_request.amount):
        raise ValidationError("You do not have permission to reject this request.")
    if not reason:
        raise ValidationError("A rejection reason is required.")
    approval_request.status = 'rejected'
    approval_request.approved_by = approver
    approval_request.approved_at = timezone.now()
    approval_request.rejection_reason = reason
    approval_request.save()
    return approval_request