import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Each logged-in user gets their own private channel group:
        notification_user_{user_id}

    When a notification is sent to that group,
    it is pushed instantly to the user's browser.
    """

    async def connect(self):
        user = self.scope['user']

        # Reject unauthenticated connections
        if user.is_anonymous:
            await self.close()
            return

        # Each user has their own group
        self.group_name = f'notification_user_{user.pk}'

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send unread count on connect so the bell updates immediately
        unread_count = await self.get_unread_count(user)
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle messages from the browser."""
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'mark_read':
            notification_id = data.get('id')
            if notification_id:
                await self.mark_notification_read(notification_id)
                unread_count = await self.get_unread_count(self.scope['user'])
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': unread_count,
                }))

        elif action == 'mark_all_read':
            await self.mark_all_read(self.scope['user'])
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': 0,
            }))

    # ── Handlers for messages sent from the server ──────

    async def notification_message(self, event):
        """
        Called when channel_layer.group_send() is called
        with type='notification.message'.
        Django Channels converts dots to underscores.
        """
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification'],
        }))

    # ── Database helpers (sync → async) ─────────────────

    @database_sync_to_async
    def get_unread_count(self, user):
        from notifications.models import InAppNotification
        return InAppNotification.objects.filter(
            recipient=user,
            is_read=False
        ).count()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        from notifications.models import InAppNotification
        InAppNotification.objects.filter(
            pk=notification_id,
            recipient=self.scope['user']
        ).update(is_read=True)

    @database_sync_to_async
    def mark_all_read(self, user):
        from notifications.models import InAppNotification
        InAppNotification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True)