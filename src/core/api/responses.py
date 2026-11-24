from rest_framework.response import Response


class ApiResponse:
    """
    The one response shape for the whole API. Every response has the same keys:

        {
            "success": bool,
            "status": int,        # same as the HTTP status code
            "message": str,
            "data": any | null,
            "errors": dict | null,
            "metadata": dict | null
        }

    Paginated responses add a "pagination" object.
    """

    @staticmethod
    def _body(*, success, status, message, data=None, errors=None, metadata=None):
        return {
            "success": success,
            "status": status,
            "message": message,
            "data": data,
            "errors": errors,
            "metadata": metadata,
        }

    @staticmethod
    def success(message="", data=None, status=200, metadata=None):
        return Response(
            ApiResponse._body(success=True, status=status, message=message, data=data, metadata=metadata),
            status=status,
        )

    @staticmethod
    def error(message, errors=None, status=400, metadata=None):
        return Response(
            ApiResponse._body(success=False, status=status, message=message, errors=errors or {}, metadata=metadata),
            status=status,
        )

    @staticmethod
    def pagination(message, paginator, data, status=200, metadata=None):
        """`paginator` is a PageNumberPagination after paginate_queryset() has run."""
        page = paginator.page
        body = ApiResponse._body(success=True, status=status, message=message, data=data, metadata=metadata)
        body["pagination"] = {
            "count": page.paginator.count,
            "page_size": page.paginator.per_page,
            "total_pages": page.paginator.num_pages,
            "current_page": page.number,
            "next_page": paginator.get_next_link(),
            "previous_page": paginator.get_previous_link(),
        }
        return Response(body, status=status)
