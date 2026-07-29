# sales/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Quotation, SalesOrder, SalesOrderItem, Invoice, InvoiceItem
from documents.services.sales_order import SalesOrderPDFService
from documents.services.invoice import InvoicePDFService
from accounts.views import log_activity


@receiver(post_save, sender=Quotation)
def quotation_post_save(sender, instance, created, **kwargs):
    """
    Auto‑convert Quotation → Sales Order when status becomes 'accepted'.
    Then the SalesOrder signal will auto‑create the Invoice.
    """
    if not created and instance.status == 'accepted':
        # Prevent duplicate conversion
        if not instance.sales_orders.exists():
            # 1. Create Sales Order
            order = SalesOrder.objects.create(
                customer=instance.customer,
                quotation=instance,
                status='approved',          # auto‑approved
                discount_amount=instance.discount_amount,
                notes=f"Auto‑converted from quotation {instance.reference}",
                created_by=instance.created_by,
            )

            # 2. Copy items
            for q_item in instance.items.all():
                SalesOrderItem.objects.create(
                    order=order,
                    item=q_item.item,
                    quantity=q_item.quantity,
                    unit_price=q_item.unit_price,
                    notes=q_item.notes,
                )

            # 3. Generate Sales Order PDF and send email
            try:
                service = SalesOrderPDFService(order)
                service.save_to_object()
                if order.customer.email:
                    service.email(
                        recipient=order.customer.email,
                        subject=f"Sales Order {order.reference}",
                        message=(
                            f"Your sales order has been automatically generated "
                            f"from quotation {instance.reference}."
                        )
                    )
            except Exception:
                pass  # Non‑blocking

            # 4. Log activity
            log_activity(
                user=instance.created_by,
                action=f"Auto‑converted quotation {instance.reference} to order {order.reference}",
                module="Sales"
            )


@receiver(post_save, sender=SalesOrder)
def sales_order_post_save(sender, instance, created, **kwargs):
    """
    Auto‑create Invoice when Sales Order status becomes 'approved'.
    Also sends email and updates order status to 'invoiced'.
    """
    if not created and instance.status == 'approved':
        # Prevent duplicate invoices
        if not instance.invoices.exists():
            # 1. Create Invoice
            invoice = Invoice.objects.create(
                customer=instance.customer,
                sales_order=instance,
                due_date=timezone.now().date() + timedelta(days=30),  # default 30 days
                total_amount=instance.total_amount,
                notes=f"Auto‑generated from order {instance.reference}",
                created_by=instance.created_by,
            )

            # 2. Copy items
            for item in instance.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item=item.item,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.total,
                )

            # 3. Update order status to 'invoiced'
            instance.status = 'invoiced'
            instance.save(update_fields=['status'])

            # 4. Generate Invoice PDF and send email
            try:
                service = InvoicePDFService(invoice)
                service.save_to_object()
                if invoice.customer.email:
                    service.email(
                        recipient=invoice.customer.email,
                        subject=f"Invoice {invoice.reference}",
                        message=(
                            f"Your invoice has been automatically generated "
                            f"from order {instance.reference}."
                        )
                    )
            except Exception:
                pass

            # 5. Log activity
            log_activity(
                user=instance.created_by,
                action=f"Auto‑created invoice {invoice.reference} from order {instance.reference}",
                module="Sales"
            )