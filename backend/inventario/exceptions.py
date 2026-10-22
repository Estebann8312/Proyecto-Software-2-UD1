from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def manejador_excepciones(exc, context):
    """
    Igual al manejador de DRF, pero convierte ProtectedError (borrar algo que
    tiene registros asociados, p. ej. una pieza con ventas) en un 409 claro
    en lugar de un error 500.
    """
    if isinstance(exc, ProtectedError):
        return Response(
            {"error": "No se puede eliminar porque tiene registros asociados "
                      "(ventas, lotes o piezas)."},
            status=status.HTTP_409_CONFLICT,
        )
    return exception_handler(exc, context)