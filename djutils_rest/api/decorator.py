from functools import wraps
from urllib.request import Request
from rest_framework.serializers import Serializer

def validate_schema(validator: Serializer, parse_from: str = 'default') -> callable[..., any]:
    def decorator(view_func: callable[..., any]) -> callable[..., any]:
        @wraps(view_func)
        def wrapper(cls, request: Request, *args, **kwargs) -> any:
            attr_name = parse_from

            if not attr_name or attr_name == 'default':
                if request.method.upper() in ('GET', 'DELETE'):
                    validate_data = request.query_params
                    attr_name = 'query_params'
                elif request.method.upper() in ('POST', 'PUT', 'PATCH'):
                    validate_data = request.data
                    attr_name = 'data'
            elif attr_name in {'query_params', 'data'}:
                validate_data = getattr(request, attr_name)

            if 'validate_data' not in locals():
                raise Exception('validate_schema parse_from value only default, data or query_params')

            validation = validator(data=validate_data)
            not validation.is_valid(raise_exception=True)

            setattr(request, f'validated_{attr_name}', validation.validated_data)            
            return view_func(cls, request, *args, **kwargs)

        return wrapper

    return decorator
