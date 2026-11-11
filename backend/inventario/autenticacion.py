from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

# Marca de los tokens que se entregan a la otra sede en POST /api/login.
ALCANCE_INTEGRACION = "integracion"


class JWTSinIntegracion(JWTAuthentication):
    """
    Autenticación JWT por defecto de la API. Rechaza los tokens de integración:
    esos duran horas y solo deben servir para leer facturas (GET /api/facturas),
    no para administrar la tienda con los permisos de un administrador.
    """

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if token.get("alcance") == ALCANCE_INTEGRACION:
            raise InvalidToken("Este token solo sirve para la integración entre sedes.")
        return token
