import contextlib
from dataclasses import (
    asdict,
    dataclass,
    field
)
from django.http.response import JsonResponse
from django.core.paginator import (
    EmptyPage,
    Paginator
)
from django.db.models import (
    Model,
    QuerySet
)
from rest_framework.serializers import (
    ListSerializer,
    Serializer
)
from djutils_rest import logger
from http import HTTPStatus as Status


@dataclass
class ApiResponse():
    data: any                        = field(default=None)
    message: str | None              = field(default=None)
    serializer: Serializer | None    = field(default=None)
    status_code: int                 = Status.OK
    
    meta: dict[str, any] | None      = field(init=False, default=None)
    error: any                       = field(init=False, default=None)
    __headers: dict[str, any] | None = field(init=False, default=None)

    def headers(self, values: dict[str, any]) -> "ApiResponse":
        self.__headers = values
        return self
    
    def exception(self, error: Exception | list[Exception]) -> "ApiResponse":
        self.error = error
        if isinstance(error, Exception):
            self.error = str(error)
        elif isinstance(error, list):
            self.error = [str(e) for e in error]

        return self

    def paginate(self, page_number: int, page_size: int) -> "ApiResponse":
        try:
            if isinstance(self.data, QuerySet):
                return self._paginate_queryset(page_number, page_size)
            
            return self._paginate_list(page_number, page_size)
        except Exception as err:
            logger.exception('ApiResponse.paginate Exception: <%s>', str(err), exc_info=True)
            return self
    
    def _paginate_list(self, page_number: int, page_size: int) -> "ApiResponse":
        total_row = len(self.data)
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        self.data = self.data[start_index:end_index]

        total_pages = (total_row + page_size - 1) // page_size

        next_page_number = page_number + 1 if page_number < total_pages else None

        self.meta = {
            'length': len(self.data),
            'total_pages': total_pages,
            'next_page_number': next_page_number,
        }
        return self

    def _paginate_queryset(self, page_number: int, page_size: int) -> "ApiResponse":
        if not self.data.ordered:
            self.data = self.data.order_by('pk')

        total_pages = (self.data.count() + page_size - 1)
        with contextlib.suppress(EmptyPage):
            paginator = Paginator(self.data, page_size)
            page = paginator.page(page_number)

            self.data = page.object_list
            self.meta = {
                'length': page.object_list.count(),
                'total_pages': total_pages,
                'next_page_number': page_number + 1 if page.has_next() else None,
            }
            return self

        self.meta = {
            'length': page.object_list.count(),
            'total_pages': total_pages,
            'next_page_number': None,
        }
        self.data = []
        return self

    def _json(self) -> JsonResponse:
        self.meta = self.meta or None

        self._serialize_response_data()

        result = asdict(self)
        result = { key: result[key] for key in ('message', 'data', 'error', 'meta') }

        result['message'] = result['message'] or self._message()
        if result['data'] is None:
            del result['data']

        if not result['meta']:
            del result['meta']

        if not result['error']:
            del result['error']

        response = JsonResponse(
            data=result,
            status=self.status_code
        )

        if headers := self.__headers:
            for header in headers:
                response[header] = headers[header]

        return response
    
    def _message(self) -> str:
        if self.status_code >= Status.OK and self.status_code <= Status.PARTIAL_CONTENT:
            return 'Request was successful'
        
        return 'A request error occurred'

    def _serialize_response_data(self) -> any:
        if isinstance(self.data, (QuerySet, list)):
            if serializer := self.serializer:
                self.data = list(serializer(instance=self.data, many=True).data)
        elif isinstance(self.data, Model):
            if serializer := self.serializer:
                self.data = dict(serializer(instance=self.data).data)
        elif isinstance(self.data, Serializer):
            self.data = dict(self.data.data)
        elif isinstance(self.data, ListSerializer):
            self.data = list(self.data.data)