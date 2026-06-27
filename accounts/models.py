"""
accounts/models.py
User and Role models with auto‑generated employee numbers.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError


def validate_company_email(value):
    """Ensure email ends with @jandn.mw."""
    if not value.endswith("@jandn.mw"):
        raise ValidationError(
            "Only J&N company email addresses (@jandn.mw) are allowed."
        )


class Role(models.Model):
    """User roles (e.g., System Administrator, Warehouse Manager)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom User model.
    - Employee number is auto‑generated if not provided.
    - Password change is forced on first login.
    """
    email = models.EmailField(
        unique=True,
        validators=[validate_company_email]
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='users'
    )
    phone = models.CharField(max_length=20, blank=True)

    # Employee number – auto‑generated as EMP-XXXXX unless manually set
    employee_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Leave blank to auto‑generate (e.g., EMP-00001)."
    )

    # Flags for password management
    must_change_password = models.BooleanField(default=True)
    is_first_login = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("manage_users", "Can manage users"),
            ("manage_roles", "Can manage roles"),
        ]

    def __str__(self):
        return self.get_full_name() or self.username

    @staticmethod
    def generate_employee_number():
        """
        Generate the next employee number in sequence.
        Format: EMP-XXXXX (e.g., EMP-00001, EMP-00042).
        """
        # Fetch all existing employee numbers that match the pattern
        existing = User.objects.filter(
            employee_number__isnull=False,
            employee_number__startswith='EMP-'
        ).values_list('employee_number', flat=True)

        max_num = 0
        for num in existing:
            try:
                # Extract the numeric part after the dash
                val = int(num.split('-')[1])
                if val > max_num:
                    max_num = val
            except (IndexError, ValueError):
                # Ignore malformed numbers
                continue

        next_num = max_num + 1
        return f"EMP-{next_num:05d}"

    def save(self, *args, **kwargs):
        """
        Override save to auto‑generate employee_number for new users
        only if they don't already have one.
        """
        if not self.pk and not self.employee_number:
            self.employee_number = self.generate_employee_number()
        super().save(*args, **kwargs)


class LoginHistory(models.Model):
    """Record of user login attempts."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    login_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-login_time']
        verbose_name_plural = "Login Histories"

    def __str__(self):
        return f"{self.user.username} — {self.login_time}"


class UserActivity(models.Model):
    """Audit log of user actions (e.g., created user, updated item)."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    action = models.CharField(max_length=255)
    module = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "User Activities"

    def __str__(self):
        return f"{self.user.username} — {self.action}"


class UserTutorial(models.Model):
    """Tracks onboarding progress per user."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='tutorial'
    )
    welcome_seen = models.BooleanField(default=False)
    tour_completed = models.BooleanField(default=False)
    tour_completed_at = models.DateTimeField(null=True, blank=True)
    tour_step_reached = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} — tutorial"


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_tutorial(sender, instance, created, **kwargs):
    if created:
        UserTutorial.objects.get_or_create(user=instance)