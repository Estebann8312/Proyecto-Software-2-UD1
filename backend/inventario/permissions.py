from rest_framework import permissions

from .models import Usuario


ROLES_EMPLEADO = ("vendedor", "administrador")


def get_empleado(user):
    """
    Devuelve el registro Usuario (empleado) vinculado al User autenticado,
    o None si es anónimo o un cliente.

    El rol se resuelve SOLO por el vínculo OneToOne Usuario.user. Nunca por
    email: comparar emails permitía que alguien se registrara con el correo
    de un empleado y heredara su rol.
    """
    if not user or not user.is_authenticated:
        return None
    try:
        return user.empleado
    except Usuario.DoesNotExist:
        return None


def get_rol(user):
    empleado = get_empleado(user)
    return empleado.rol if empleado else None


class IsAdministrador(permissions.BasePermission):
    """Solo usuarios con rol 'administrador'."""

    message = "Solo un administrador puede realizar esta acción."

    def has_permission(self, request, view):
        return get_rol(request.user) == "administrador"


class IsVendedorOrAdmin(permissions.BasePermission):
    """Vendedores y administradores."""

    message = "Solo empleados (vendedor o administrador) pueden acceder."

    def has_permission(self, request, view):
        return get_rol(request.user) in ROLES_EMPLEADO


class LecturaEmpleadoEscrituraAdmin(permissions.BasePermission):
    """Empleados pueden consultar; solo el administrador crea, edita o borra."""

    message = "Solo un administrador puede modificar este recurso."

    def has_permission(self, request, view):
        rol = get_rol(request.user)
        if request.method in permissions.SAFE_METHODS:
            return rol in ROLES_EMPLEADO
        return rol == "administrador"