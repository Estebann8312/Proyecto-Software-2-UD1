from rest_framework import permissions
from .models import Usuario, Cliente

class IsAdministrador(permissions.BasePermission):
    """Permite el acceso solo a los usuarios con rol 'administrador'."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            empleado = Usuario.objects.get(email=request.user.email)
            return empleado.rol == 'administrador'
        except Usuario.DoesNotExist:
            return False

class IsVendedorOrAdmin(permissions.BasePermission):
    """Permite el acceso a vendedores y administradores."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            empleado = Usuario.objects.get(email=request.user.email)
            return empleado.rol in ['vendedor', 'administrador']
        except Usuario.DoesNotExist:
            return False

class IsClienteOwner(permissions.BasePermission):
    """
    Permite a los clientes acceder, pero solo a sus propios registros.
    Los administradores y vendedores pueden ver los registros de todos.
    """
    def has_object_permission(self, request, view, obj):
        try:
            empleado = Usuario.objects.get(email=request.user.email)
            if empleado.rol in ['vendedor', 'administrador']:
                return True
        except Usuario.DoesNotExist:
            pass

        # Si no es empleado, verificamos si es el cliente dueño del objeto (ej. su propia Venta)
        try:
            cliente = Cliente.objects.get(email=request.user.email)
            # Asume que el objeto (como Venta) tiene un campo id_cliente
            return obj.id_cliente == cliente
        except Cliente.DoesNotExist:
            return False