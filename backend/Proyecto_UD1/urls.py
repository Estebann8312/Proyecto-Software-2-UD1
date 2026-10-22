"""
URL configuration for Proyecto_UD1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    # Panel administrativo de Django
    path("admin/", admin.site.urls),

    # Rutas de la aplicación inventario:
    # /api/auth/login/     (JWT + rol, con límite de intentos)
    # /api/auth/register/
    # /api/auth/me/
    # /api/auth/register/
    # /api/categorias/
    # /api/piezas/
    # /api/proveedores/
    # /api/lotes/
    # /api/ventas/
    path("api/", include("inventario.urls")),


    # Renovar token JWT
    path(
        "api/auth/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # ---> Login por sesión para la API navegable de DRF <---
    path("api-auth/", include("rest_framework.urls")),
]