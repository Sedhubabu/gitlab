import uuid

from django.db import models


class BaseAbstractModel(models.Model):
    """Common fields shared by every model in the project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        get_latest_by = "created_at"
