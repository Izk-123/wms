from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect


class WMSPermissionMixin(PermissionRequiredMixin):
    """
    Shared permission mixin for all WMS views.
    Shows a friendly error instead of a 403 page.
    """
    def handle_no_permission(self):
        messages.error(
            self.request,
            "You do not have permission to perform that action."
        )
        return redirect('reports:dashboard')