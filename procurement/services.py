from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.services import receive_stock
from .models import (
    PurchaseRequest, PurchaseOrder,
    GoodsReceipt, GoodsReceiptItem
)


@transaction.atomic
def submit_purchase_request(purchase_request, user):
    if purchase_request.status != "draft":
        raise ValidationError("Only draft requests can be submitted.")

    purchase_request.status = "submitted"
    purchase_request.save()

    # Email
    try:
        from notifications.emails import send_purchase_request_approval_needed
        from notifications.utils import get_warehouse_managers
        approvers = get_warehouse_managers()
        if approvers:
            send_purchase_request_approval_needed(purchase_request, approvers)
    except Exception:
        pass

    # ── Real-time in-app notification ───────────────────
    try:
        from notifications.sender import notify_users
        from notifications.utils import get_warehouse_managers
        notify_users(
            users=get_warehouse_managers(),
            title="Purchase Request Awaits Approval",
            message=(
                f"{purchase_request.reference} submitted by "
                f"{purchase_request.requested_by.get_full_name()}. "
                f"{purchase_request.items.count()} item(s) requested."
            ),
            notification_type="approval_required",
            level="warning",
            url=f"/procurement/requests/{purchase_request.pk}/",
        )
    except Exception:
        pass
    # ───────────────────────────────────────────────────


@transaction.atomic
def approve_purchase_request(purchase_request, user):
    if purchase_request.status != "submitted":
        raise ValidationError("Only submitted requests can be approved.")

    purchase_request.status = "approved"
    purchase_request.approved_by = user
    purchase_request.approved_at = timezone.now()
    purchase_request.save()

    # Email
    try:
        from notifications.emails import send_purchase_request_decision
        send_purchase_request_decision(purchase_request)
    except Exception:
        pass

    # ── Real-time ────────────────────────────────────────
    try:
        from notifications.sender import notify_user
        notify_user(
            user=purchase_request.requested_by,
            title="Purchase Request Approved",
            message=(
                f"Your request {purchase_request.reference} has been "
                f"approved by {user.get_full_name()}."
            ),
            notification_type="approved",
            level="success",
            url=f"/procurement/requests/{purchase_request.pk}/",
        )
    except Exception:
        pass
    # ────────────────────────────────────────────────────


@transaction.atomic
def reject_purchase_request(purchase_request, user, reason):
    if purchase_request.status != "submitted":
        raise ValidationError("Only submitted requests can be rejected.")
    if not reason:
        raise ValidationError("A rejection reason is required.")

    purchase_request.status = "rejected"
    purchase_request.approved_by = user
    purchase_request.approved_at = timezone.now()
    purchase_request.rejection_reason = reason
    purchase_request.save()

    # Email
    try:
        from notifications.emails import send_purchase_request_decision
        send_purchase_request_decision(purchase_request)
    except Exception:
        pass

    # ── Real-time ────────────────────────────────────────
    try:
        from notifications.sender import notify_user
        notify_user(
            user=purchase_request.requested_by,
            title="Purchase Request Rejected",
            message=(
                f"Your request {purchase_request.reference} was rejected. "
                f"Reason: {reason}"
            ),
            notification_type="rejected",
            level="danger",
            url=f"/procurement/requests/{purchase_request.pk}/",
        )
    except Exception:
        pass
    # ────────────────────────────────────────────────────


@transaction.atomic
def confirm_goods_receipt(goods_receipt, user):
    if goods_receipt.status == "confirmed":
        raise ValidationError("This GRN has already been confirmed.")

    po = goods_receipt.purchase_order
    warehouse = po.delivery_warehouse

    for grn_item in goods_receipt.items.select_related(
        'purchase_order_item__item'
    ):
        item = grn_item.purchase_order_item.item
        qty = grn_item.quantity_received
        if qty <= 0:
            continue
        receive_stock(
            item=item,
            warehouse=warehouse,
            quantity=qty,
            reference=goods_receipt.reference,
            notes=f"Received via {goods_receipt.reference} from PO {po.reference}",
            user=user,
        )
        po_item = grn_item.purchase_order_item
        po_item.quantity_received += qty
        po_item.save()

    goods_receipt.status = "confirmed"
    goods_receipt.save()

    all_items = po.items.all()
    fully_received = all(
        i.quantity_received >= i.quantity_ordered for i in all_items
    )
    po.status = "received" if fully_received else "partial"
    po.save()

    # Email
    try:
        from notifications.emails import send_goods_received_notification
        from notifications.utils import (
            get_warehouse_managers, get_procurement_officers
        )
        recipients = list(set(
            get_warehouse_managers() + get_procurement_officers()
        ))
        if recipients:
            send_goods_received_notification(goods_receipt, recipients)
    except Exception:
        pass

    # ── Real-time ────────────────────────────────────────
    try:
        from notifications.sender import notify_users
        from notifications.utils import (
            get_warehouse_managers, get_procurement_officers
        )
        recipients = list(set(
            get_warehouse_managers() + get_procurement_officers()
        ))
        notify_users(
            users=recipients,
            title="Goods Received",
            message=(
                f"{goods_receipt.reference} confirmed — "
                f"{goods_receipt.purchase_order.supplier.name}. "
                f"Stock updated in {warehouse.name}."
            ),
            notification_type="goods_received",
            level="success",
            url=f"/procurement/grn/{goods_receipt.pk}/",
        )
    except Exception:
        pass
    # ────────────────────────────────────────────────────