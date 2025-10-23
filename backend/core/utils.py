from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status


def custom_exception_handler(exc, context):
    """Custom exception handler for consistent API error responses."""
    if isinstance(exc, DjangoValidationError):
        exc = APIException(detail={
            'message': 'Validation Error',
            'errors': exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
        })
        exc.status_code = status.HTTP_400_BAD_REQUEST

    elif isinstance(exc, IntegrityError):
        exc = APIException(detail={
            'message': 'Database Integrity Error',
            'errors': str(exc)
        })
        exc.status_code = status.HTTP_400_BAD_REQUEST

    response = exception_handler(exc, context)
    
    if response is not None:
        # Ensure the response has a consistent format
        if isinstance(response.data, dict):
            if 'detail' in response.data and isinstance(response.data['detail'], str):
                response.data = {
                    'message': response.data['detail'],
                    'errors': None
                }
            elif 'detail' in response.data and isinstance(response.data['detail'], dict):
                if 'message' not in response.data['detail']:
                    response.data = {
                        'message': 'Error',
                        'errors': response.data['detail']
                    }
        else:
            response.data = {
                'message': 'Error',
                'errors': response.data
            }

        # Add status code to response
        response.data['status_code'] = response.status_code

    return response
