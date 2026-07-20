from django.db import models
from accounts.models import User


class NotificationLog(models.Model):
    """
    Records every email sent by the system.
    Useful for auditing and debugging.
    """

    NOTIFICATION_TYPES = (
        ("low_stock",           "Low Stock Alert"),
        ("approval_required",   "Approval Required"),
        ("approved",            "Request Approved"),
        ("rejected",            "Request Rejected"),
        ("goods_received",      "Goods Received"),
        ("password_reset",      "Password Reset"),
        ("welcome",             "Welcome Email"),
    )

    STATUS_CHOICES = (
        ("sent",    "Sent"),
        ("failed",  "Failed"),
        ("pending", "Pending"),
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='notifications_received'
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} → {self.recipient_email}"
    
class InAppNotification(models.Model):
    """
    Real-time in-app notifications shown in the bell icon.
    Delivered via WebSocket. Persisted so users see them
    even if they were offline when the event happened.
    """

    LEVEL_CHOICES = (
        ("info",    "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("danger",  "Danger"),
    )

    TYPE_CHOICES = (
        ("low_stock",         "Low Stock"),
        ("approval_required", "Approval Required"),
        ("approved",          "Approved"),
        ("rejected",          "Rejected"),
        ("goods_received",    "Goods Received"),
        ("general",           "General"),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='in_app_notifications'
    )
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default="general"
    )
    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        default="info"
    )
    url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional URL to link to from the notification"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} — {self.title}"

    def to_dict(self):
        """Serialise to dict for WebSocket transmission."""
        return {
            'id': self.pk,
            'title': self.title,
            'message': self.message,
            'type': self.notification_type,
            'level': self.level,
            'url': self.url,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%d %b %Y %H:%M'),
        }