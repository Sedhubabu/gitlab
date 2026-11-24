import logging

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

from .responses import ApiResponse

logger = logging.getLogger(__name__)


class AppError(APIException):
    """
    Raise from services/views for expected business errors:

        raise AppError("Project limit reached", status_code=403, errors={"projects_limit": 10})
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Request could not be processed."
    default_code = "error"

    def __init__(self, message=None, *, status_code=None, errors=None, code=None):
        super().__init__(detail=message or self.default_detail, code=code)
        if status_code is not None:
            self.status_code = status_code
        self.errors = errors or {}


def _message_from(detail):
    """Pull a readable message out of DRF's `detail` (str, list or dict)."""
    if isinstance(detail, dict):
        if "detail" in detail:
            return str(detail["detail"])
        return "Request failed."
    if isinstance(detail, list):
        return str(detail[0]) if detail else "Request failed."
    return str(detail)


def custom_exception_handler(exc, context):
    """
    Turn every error into the ApiResponse.error shape.
    Registered as REST_FRAMEWORK["EXCEPTION_HANDLER"] in settings.
    """
    response = drf_exception_handler(exc, context)

    # Not an API error DRF knows about → unexpected server error.
    if response is None:
        if settings.DEBUG:
            return None  # let Django show the full debug page in development
        logger.exception("Unhandled API error", exc_info=exc)
        return ApiResponse.error("Internal server error.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if isinstance(exc, AppError):
        message, errors = str(exc.detail), exc.errors
    elif isinstance(exc, ValidationError):
        # Field errors: {"email": ["This field is required."]}
        message = "Validation failed."
        errors = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
    else:
        message = _message_from(response.data)
        errors = {}
        # SimpleJWT puts extra info (token type, reason) next to "detail".
        if isinstance(response.data, dict):
            errors = {k: v for k, v in response.data.items() if k != "detail"}

    error_response = ApiResponse.error(message, errors=errors, status=response.status_code)
    # Keep headers DRF set (WWW-Authenticate for 401, Retry-After for 429).
    for header, value in response.items():
        error_response[header] = value
    return error_response
