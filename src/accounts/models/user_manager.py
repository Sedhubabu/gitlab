from django.contrib.auth.base_user import BaseUserManager
from django.db.models import Q


class MyUserManager(BaseUserManager):
    """
    Manager for the email-based custom User model.
    Uses BaseUserManager (not UserManager) because Django's UserManager assumes
    `username` is the login field; here users sign in with email or username.
    """

    use_in_migrations = True

    def get_by_natural_key(self, login):
        # Like GitLab: sign in with either email or username, case-insensitive.
        return self.get(Q(email__iexact=login) | Q(username__iexact=login))

    def _create_user(self, email, username, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set.")
        if not username:
            raise ValueError("The username must be set.")
        email = self.normalize_email(email).lower()
        username = self.model.normalize_username(username)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, username, password, **extra_fields)
