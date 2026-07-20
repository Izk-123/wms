from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import InAppNotification


def notify_user(
    user,
    title,
    message,
    notification_type="general",
    level="info",
    url="",
):
    """
    Send a real-time in-app notification to a specific user.

    1. Saves it to the database (persists if user is offline).
    2. Pushes it via WebSocket (instant if user is online).

    Usage:
        from notifications.sender import notify_user
        notify_user(
            user=request.user,
            title="Stock Received",
            message="100 bags of Portland Cement received into Main Warehouse.",
            level="success",
            url="/inventory/stock/",
        )
    """
    # Save to database
    notification = InAppNotification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        level=level,
        url=url,
    )

    # Push via WebSocket
    channel_layer = get_channel_layer()
    group_name = f'notification_user_{user.pk}'

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification.message',
                'notification': notification.to_dict(),
            }
        )
    except Exception:
        # WebSocket push failed — notification still saved to DB
        pass

    return notification


def notify_users(users, title, message, notification_type="general",
                 level="info", url=""):
    """Send the same notification to multiple users."""
    for user in users:
        notify_user(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            level=level,
            url=url,
        )