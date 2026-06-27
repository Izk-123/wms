from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Item, Warehouse, Stock, StockMovement


def get_or_create_stock(item, warehouse):
    """Get stock record or create one with 0 quantity."""
    stock, created = Stock.objects.get_or_create(
        item=item,
        warehouse=warehouse,
        defaults={'quantity': 0}
    )
    return stock


@transaction.atomic
def receive_stock(item, warehouse, quantity, reference="", notes="", user=None):
    """
    Stock IN — goods received into warehouse.
    Used by: Goods Receipt Notes, manual adjustments.
    """
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    stock = get_or_create_stock(item, warehouse)
    stock.quantity += quantity
    stock.save()

    movement = StockMovement.objects.create(
        item=item,
        warehouse=warehouse,
        movement_type="IN",
        quantity=quantity,
        reference=reference,
        notes=notes,
        created_by=user,
    )

    return movement


@transaction.atomic
def issue_stock(item, warehouse, quantity, reference="", notes="", user=None):
    """
    Stock OUT — materials issued to project, department, or production.
    Used by: Material Requisitions, Production Orders.
    """
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    stock = get_or_create_stock(item, warehouse)

    if stock.quantity < quantity:
        raise ValidationError(
            f"Insufficient stock. Available: {stock.quantity} {item.unit.symbol}, "
            f"Requested: {quantity} {item.unit.symbol}."
        )

    stock.quantity -= quantity
    stock.save()

    movement = StockMovement.objects.create(
        item=item,
        warehouse=warehouse,
        movement_type="OUT",
        quantity=quantity,
        reference=reference,
        notes=notes,
        created_by=user,
    )

    return movement


@transaction.atomic
def transfer_stock(item, from_warehouse, to_warehouse, quantity, reference="", notes="", user=None):
    """
    Transfer stock between warehouses.
    Used by: Site-to-site transfers, warehouse reorganization.
    """
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    if from_warehouse == to_warehouse:
        raise ValidationError("Source and destination warehouses must be different.")

    from_stock = get_or_create_stock(item, from_warehouse)

    if from_stock.quantity < quantity:
        raise ValidationError(
            f"Insufficient stock in {from_warehouse.name}. "
            f"Available: {from_stock.quantity} {item.unit.symbol}."
        )

    # Deduct from source
    from_stock.quantity -= quantity
    from_stock.save()

    # Add to destination
    to_stock = get_or_create_stock(item, to_warehouse)
    to_stock.quantity += quantity
    to_stock.save()

    # Record as two linked movements
    out_movement = StockMovement.objects.create(
        item=item,
        warehouse=from_warehouse,
        movement_type="TRANSFER",
        quantity=quantity,
        reference=reference,
        notes=f"Transfer to {to_warehouse.name}. {notes}".strip(),
        created_by=user,
    )

    StockMovement.objects.create(
        item=item,
        warehouse=to_warehouse,
        movement_type="TRANSFER",
        quantity=quantity,
        reference=reference,
        notes=f"Transfer from {from_warehouse.name}. {notes}".strip(),
        created_by=user,
    )

    return out_movement


@transaction.atomic
def adjust_stock(item, warehouse, new_quantity, reason="", user=None):
    """
    Stock adjustment — correct the balance after a physical stock count.
    Records the difference as an IN or OUT movement.
    """
    if new_quantity < 0:
        raise ValidationError("Stock quantity cannot be negative.")

    stock = get_or_create_stock(item, warehouse)
    difference = new_quantity - stock.quantity

    if difference == 0:
        raise ValidationError("New quantity is the same as current quantity. No adjustment needed.")

    stock.quantity = new_quantity
    stock.save()

    movement = StockMovement.objects.create(
        item=item,
        warehouse=warehouse,
        movement_type="ADJUSTMENT",
        quantity=abs(difference),
        reference="STOCK-ADJUSTMENT",
        notes=f"Adjusted {'up' if difference > 0 else 'down'} by {abs(difference)}. Reason: {reason}",
        created_by=user,
    )

    return movement