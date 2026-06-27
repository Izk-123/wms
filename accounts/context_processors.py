from .models import UserTutorial


def tutorial_context(request):
    """
    Injects tutorial state into every template.
    Used by base.html to decide whether to show
    the welcome modal or start the tour automatically.
    """
    if not request.user.is_authenticated:
        return {}

    tutorial, _ = UserTutorial.objects.get_or_create(
        user=request.user
    )

    return {
        'tutorial_welcome_seen': tutorial.welcome_seen,
        'tutorial_completed': tutorial.tour_completed,
        'show_welcome_modal': not tutorial.welcome_seen,
        'show_tour': tutorial.welcome_seen and not tutorial.tour_completed,
    }