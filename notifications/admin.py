from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import NotificationLog, InAppNotification


@admin.register(NotificationLog)
class NotificationLogAdmin(ModelAdmin):
    list_display = (
        'notification_type', 'recipient_email',
        'subject', 'status', 'created_at'
    )
    list_filter = ('notification_type', 'status')
    search_fields = ('recipient_email', 'subject')
    readonly_fields = (
        'notification_type', 'recipient', 'recipient_email',
        'subject', 'status', 'error_message', 'created_at'
    )


@admin.register(InAppNotification)
class InAppNotificationAdmin(ModelAdmin):
    list_display = (
        'recipient', 'title', 'notification_type',
        'level', 'is_read', 'created_at'
    )
    list_filter = ('notification_type', 'level', 'is_read')
    search_fields = ('recipient__username', 'title', 'message')