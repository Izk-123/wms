# notifications/views.py
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from .models import InAppNotification


class NotificationListView(LoginRequiredMixin, ListView):
    model = InAppNotification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        return InAppNotification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')


class NotificationCountView(LoginRequiredMixin, View):
    """HTMX endpoint – returns the bell icon with unread count."""
    def get(self, request):
        count = InAppNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()

        html = render_to_string(
            'notifications/partials/bell.html',
            {'unread_count': count},
            request=request
        )
        return HttpResponse(html)


class NotificationDropdownView(LoginRequiredMixin, View):
    """HTMX endpoint – returns the dropdown panel content."""
    def get(self, request):
        notifications = InAppNotification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:10]

        unread_count = InAppNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()

        html = render_to_string(
            'notifications/partials/dropdown.html',
            {
                'notifications': notifications,
                'unread_count': unread_count,
            },
            request=request
        )
        return HttpResponse(html)


class MarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(
            InAppNotification, pk=pk, recipient=request.user
        )
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'ok'})


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        InAppNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        return JsonResponse({'status': 'ok', 'count': 0})