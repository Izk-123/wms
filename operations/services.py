from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.services import issue_stock, receive_stock
from .models import (
    MaterialRequest, MaterialRequestItem,
    MaterialReturn, MaterialReturnItem
)


@transaction.atomic
def submit_material_request(material_request, user):
    if material_request.status != "draft":
        raise ValidationError("Only draft requests can be submitted.")

    material_request.status = "submitted"
    material_request.save()

    # Email
    try:
        from notifications.emails import send_material_request_approval_needed
        from notifications.utils import get_material_request_approvers
        approvers = get_material_request_approvers()
        if approvers:
            send_material_request_approval_needed(material_request, approvers)
    except Exception:
        pass

    # ── Real-time ────────────────────────────────────────
    try:
        from notifications.sender import notify_users
        from notifications.utils import get_material_request_approvers
        project_name = (
            material_request.project.name
            if material_request.project else "General"
        )
        notify_users(
            users=get_material_request_approvers(),
            title="Material Request Awaits Approval",
            message=(
                f"{material_request.reference} submitted by "
                f"{material_request.requested_by.get_full_name()} "
                f"for {project_name}."
            ),
            notification_type="approval_required",
            level="warning",
            url=f"/operations/requests/{material_request.pk}/",
        )
    except Exception:
        pass
    # ────────────────────────────────────────────────────


@transaction.atomic
def approve_material_request(material_request, user):
    if material_request.status != "submitted":
        raise ValidationError("Only submitted requests can be approved.")

    material_request.status = "approved"
    material_request.approved_by = user
    material_request.approved_at = timezone.now()
    material_request.save()

    # Email
    try:
        from notifications.emails import send_material_request_decision
        send_material_request_decision(material_request)
    except Exception:
        pass

    # ── Real-time ────────────────────────────────────────
    try:
        from notifications.sender import notify_user
        notify_user(
            user=material_request.requested_by,
            title="Material Request Approved",
            message=(
                f"Your request {material_request.reference} has been "
                f"approved by {user.get_full_name()}. "
                f"Materials will be issued shortly."
            ),
            notification_type="approved",
            level="success",
            url=f"/operations/requests/{material_request.pk}/",
        )
    except Exception:
        pass
    # ────────────────────────────────────────────────────


@transaction.atomic
def reject_material_request(material_request, user, reason):
    if material_request.status != "submitted":
        raise ValidationError("Only submitted requests can be rejected.")
    if not reason:
        raise ValidationError("A rejection reason is required.")

    material_request.status = "rejected"
    material_request.approved_by = user
    material_request.approved_at = timezone.now()
    material_request.rejection_reason = reason
    material_request.save()

    # Email
    try:
        from notifications.emails import send_material_request_decision
        send_material_request_decision(material_request)
    except Exception:
        pass

    # ── Real-time ────────────────────────────────────────
    try:
        from notifications.sender import notify_user
        notify_user(
            user=material_request.requested_by,
            title="Material Request Rejected",
            message=(
                f"Your request {material_request.reference} was rejected. "
                f"Reason: {reason}"
            ),
            notification_type="rejected",
            level="danger",
            url=f"/operations/requests/{material_request.pk}/",
        )
    except Exception:
        pass
    # ────────────────────────────────────────────────────

@transaction.atomic
def issue_materials(material_request, user):
    """
    Issue all approved items from the warehouse.
    Handles partial issuance when stock is insufficient.
    """
    if material_request.status not in ("approved", "partially_issued"):
        raise ValidationError("Only approved requests can be issued.")

    warehouse = material_request.warehouse
    issued_count = 0
    partial = False

    for req_item in material_request.items.select_related('item'):
        pending = req_item.quantity_pending
        if pending <= 0:
            continue

        try:
            issue_stock(
                item=req_item.item,
                warehouse=warehouse,
                quantity=pending,
                reference=material_request.reference,
                notes=(
                    f"Issued for {material_request.project or 'general use'}"
                ),
                user=user,
            )
            req_item.quantity_issued += pending
            req_item.save()
            issued_count += 1

        except ValidationError:
            # Not enough stock for this item — skip and mark partial
            partial = True
            continue

    if issued_count == 0:
        raise ValidationError(
            "No items could be issued. Check stock levels."
        )

    # Update request status
    all_issued = all(
        i.is_fully_issued for i in material_request.items.all()
    )
    material_request.status = "issued" if all_issued else "partially_issued"
    material_request.save()


@transaction.atomic
def process_material_return(material_return, user):
    """
    Return unused materials back to the warehouse.
    Each returned item triggers a stock IN movement.
    """
    warehouse = material_return.warehouse

    for return_item in material_return.items.select_related('item'):
        if return_item.quantity_returned <= 0:
            continue

        receive_stock(
            item=return_item.item,
            warehouse=warehouse,
            quantity=return_item.quantity_returned,
            reference=material_return.reference,
            notes=(
                f"Return from {material_return.material_request.reference}"
            ),
            user=user,
        )