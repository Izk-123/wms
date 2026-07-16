from django.db import transaction
from django.core.cache import cache
from .services import get_setting

def generate_next_number(prefix_key, model, field="reference", padding=6, use_model_cache=True):
    """
    Generate the next sequential number for a given model and prefix.

    Args:
        prefix_key: SystemSetting key (e.g., "INVOICE_PREFIX")
        model: Django model class
        field: field name to check for existing numbers (default: "reference")
        padding: zero-padding width (default: 6)
        use_model_cache: use cache to improve performance (default: True)

    Returns:
        str: formatted number like "INV-000001"
    """
    prefix = get_setting(prefix_key, "DOC-")

    # Use a cache key per model to avoid hitting DB for every number
    cache_key = f"numbering_{model._meta.model_name}_{prefix_key}"

    if use_model_cache:
        next_num = cache.get(cache_key)
        if next_num is not None:
            # Cache hit – increment and return
            new_num = next_num + 1
            cache.set(cache_key, new_num, 60 * 60)  # 1 hour
            return f"{prefix}{new_num:0{padding}d}"

    # Cache miss or disabled – calculate from DB
    with transaction.atomic():
        # Lock the table to avoid race conditions
        # Use select_for_update on the model's table
        last = model.objects.select_for_update().order_by("-id").first()

        if last:
            try:
                # Extract numeric part after the last '-'
                # Handle cases where reference might be "INV-000001" or just "000001"
                if "-" in getattr(last, field):
                    current = int(getattr(last, field).split("-")[-1])
                else:
                    current = int(getattr(last, field))
                next_num = current + 1
            except (ValueError, IndexError, TypeError):
                next_num = 1
        else:
            next_num = 1

        # Cache the next number for subsequent calls
        if use_model_cache:
            cache.set(cache_key, next_num, 60 * 60)

        return f"{prefix}{next_num:0{padding}d}"