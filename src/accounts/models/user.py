from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

from core.models import BaseAbstractModel

from .user_manager import MyUserManager

# GitLab rules: letters, digits, "_", "-", "."; must start and end with a letter,
# digit or "_"; must not end in ".git" or ".atom".
username_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_])?$",
    message=(
        "Username can contain only letters, digits, '_', '-' and '.', "
        "and must start and end with a letter, digit or '_'."
    ),
)

# Paths that would clash with top-level routes (/admin, /api, /users/...).
RESERVED_USERNAMES = {
    "admin", "api", "dashboard", "explore", "groups", "help", "login",
    "logout", "profile", "projects", "search", "settings",
    "signup", "static", "media", "users", "-",
}


def validate_username(value):
    lowered = value.lower()
    if lowered in RESERVED_USERNAMES:
        raise ValidationError(f"'{value}' is a reserved name.")
    if lowered.endswith((".git", ".atom")):
        raise ValidationError("Username cannot end with '.git' or '.atom'.")


def avatar_upload_path(instance, filename):
    return f"avatars/users/{instance.id}/{filename}"


class User(BaseAbstractModel, AbstractBaseUser, PermissionsMixin):
    # id, is_active, created_at, updated_at come from BaseAbstractModel.
    # is_active is kept in sync with `state` in save().

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"
        DEACTIVATED = "deactivated", "Deactivated"
        BANNED = "banned", "Banned"

    class UserType(models.TextChoices):
        HUMAN = "human", "Human"
        BOT = "bot", "Bot"
        SERVICE_ACCOUNT = "service_account", "Service account"

    # --- Identity ---
    username = models.CharField(
        max_length=255,
        unique=True,
        validators=[username_validator, validate_username],
        help_text="Unique handle used as the personal namespace, e.g. /<username>/<repo>.",
    )
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)

    # --- Profile ---
    public_email = models.EmailField(blank=True)
    avatar = models.FileField(upload_to=avatar_upload_path, null=True, blank=True)
    bio = models.CharField(max_length=255, blank=True)
    pronouns = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=255, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)
    website_url = models.URLField(blank=True)
    private_profile = models.BooleanField(default=False)

    # --- Account status & type ---
    state = models.CharField(max_length=20, choices=State.choices, default=State.ACTIVE, db_index=True)
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.HUMAN)
    is_staff = models.BooleanField(default=False, help_text="GitLab 'admin': can access the admin area.")
    external = models.BooleanField(
        default=False,
        help_text="External users can only access projects they are explicitly members of.",
    )

    # --- Permissions / limits ---
    can_create_group = models.BooleanField(default=True)
    projects_limit = models.PositiveIntegerField(default=100000)

    # --- Security ---
    confirmed_at = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    password_change_required = models.BooleanField(default=False)
    # Bumped on every sign-in; tokens carrying an older value are rejected.
    token_version = models.PositiveIntegerField(default=0)

    # --- Activity ---
    current_sign_in_at = models.DateTimeField(null=True, blank=True)
    last_activity_on = models.DateField(null=True, blank=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["username", "name"]

    objects = MyUserManager()

    history = AuditlogHistoryField()

    class Meta(BaseAbstractModel.Meta):
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints = [
            # GitLab usernames are unique regardless of case.
            models.UniqueConstraint(Lower("username"), name="accounts_user_username_ci_unique"),
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        self.is_active = self.state == self.State.ACTIVE
        if kwargs.get("update_fields") is not None and "state" in kwargs["update_fields"]:
            kwargs["update_fields"] = {*kwargs["update_fields"], "is_active"}
        super().save(*args, **kwargs)

    @property
    def is_bot(self):
        return self.user_type != self.UserType.HUMAN

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.username


auditlog.register(User)
