from auditlog.mixins import AuditlogHistoryAdminMixin
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import format_html

from accounts.models import User


class UserCreationAdminForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "username", "name")

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data.get("email")).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email


class UserChangeAdminForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data.get("email")).lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with that username already exists.")
        return username


@admin.register(User)
class UserAdmin(AuditlogHistoryAdminMixin, DjangoUserAdmin):
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm
    show_auditlog_history_link = True

    list_display = (
        "username",
        "email",
        "name",
        "state_badge",
        "user_type",
        "is_staff",
        "external",
        "two_factor_enabled",
        "last_activity_on",
        "created_at",
    )
    list_display_links = ("username", "email")
    list_filter = (
        "state",
        "user_type",
        "is_staff",
        "is_superuser",
        "external",
        "two_factor_enabled",
        "private_profile",
        "can_create_group",
        "created_at",
    )
    search_fields = ("username", "email", "name", "public_email", "organization")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    filter_horizontal = ("groups", "user_permissions")

    readonly_fields = (
        "id",
        "is_active",
        "token_version",
        "last_login",
        "current_sign_in_at",
        "last_activity_on",
        "created_at",
        "updated_at",
        "avatar_preview",
    )

    fieldsets = (
        (None, {"fields": ("id", "username", "email", "name", "password")}),
        ("Profile", {
            "fields": (
                "avatar", "avatar_preview", "public_email", "bio", "pronouns",
                "location", "organization", "job_title", "website_url", "private_profile",
            ),
        }),
        ("Account", {
            "fields": ("state", "is_active", "user_type", "external"),
            "description": "'is_active' follows 'state': only active users can sign in.",
        }),
        ("Access level", {
            "fields": ("is_staff", "is_superuser", "can_create_group", "projects_limit"),
        }),
        ("Security", {
            "fields": ("confirmed_at", "two_factor_enabled", "password_change_required", "token_version"),
        }),
        ("Permissions", {
            "classes": ("collapse",),
            "fields": ("groups", "user_permissions"),
        }),
        ("Activity", {
            "fields": ("last_login", "current_sign_in_at", "last_activity_on", "created_at", "updated_at"),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "name", "usable_password", "password1", "password2"),
        }),
    )

    actions = (
        "activate_users",
        "block_users",
        "deactivate_users",
        "ban_users",
        "confirm_users",
        "force_sign_out",
    )

    # --- Display helpers ---

    STATE_COLORS = {
        User.State.ACTIVE: "#108548",
        User.State.BLOCKED: "#c17d10",
        User.State.DEACTIVATED: "#737278",
        User.State.BANNED: "#dd2b0e",
    }

    @admin.display(description="State", ordering="state")
    def state_badge(self, obj):
        return format_html(
            '<span style="color:#fff;background:{};padding:2px 8px;border-radius:10px">{}</span>',
            self.STATE_COLORS.get(obj.state, "#737278"),
            obj.get_state_display(),
        )

    @admin.display(description="Avatar preview")
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" style="height:64px;border-radius:50%">', obj.avatar.url)
        return "—"

    # --- Safety ---

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        # Only superusers may grant superuser / admin rights.
        if not request.user.is_superuser:
            readonly += ["is_superuser", "is_staff", "groups", "user_permissions"]
        return readonly

    # --- Bulk actions ---

    def _set_state(self, request, queryset, state):
        # Never let an admin lock themselves out.
        queryset = queryset.exclude(pk=request.user.pk)
        count = 0
        for user in queryset:
            user.state = state
            if state != User.State.ACTIVE:
                user.token_version += 1  # invalidate existing JWTs
            user.save(update_fields=["state", "token_version", "updated_at"])
            count += 1
        self.message_user(request, f"{count} user(s) set to {User.State(state).label}.", messages.SUCCESS)

    @admin.action(description="Activate / unblock selected users")
    def activate_users(self, request, queryset):
        self._set_state(request, queryset, User.State.ACTIVE)

    @admin.action(description="Block selected users")
    def block_users(self, request, queryset):
        self._set_state(request, queryset, User.State.BLOCKED)

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        self._set_state(request, queryset, User.State.DEACTIVATED)

    @admin.action(description="Ban selected users")
    def ban_users(self, request, queryset):
        self._set_state(request, queryset, User.State.BANNED)

    @admin.action(description="Confirm email of selected users")
    def confirm_users(self, request, queryset):
        count = queryset.filter(confirmed_at__isnull=True).update(confirmed_at=timezone.now())
        self.message_user(request, f"{count} user(s) confirmed.", messages.SUCCESS)

    @admin.action(description="Force sign-out (revoke tokens)")
    def force_sign_out(self, request, queryset):
        for user in queryset:
            user.token_version += 1
            user.save(update_fields=["token_version", "updated_at"])
        self.message_user(request, f"Signed out {queryset.count()} user(s).", messages.SUCCESS)
