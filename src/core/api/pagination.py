from rest_framework.pagination import PageNumberPagination

from .responses import ApiResponse


class StandardPagination(PageNumberPagination):
    """
    Default pagination for every list endpoint.
    Query params: ?page=2&page_size=50
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return ApiResponse.pagination("", self, data)
