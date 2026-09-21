from typing import TYPE_CHECKING

from query_counter.middleware import DjangoQueryCounterMiddleware

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class QueryCounterMiddleware(DjangoQueryCounterMiddleware):
    """Считать SQL прикладных запросов, пропуская админку Django."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Передать запросы админки дальше без сбора и вывода статистики."""
        if request.path_info == "/admin" or request.path_info.startswith("/admin/"):
            return self.get_response(request)
        return super().__call__(request)
