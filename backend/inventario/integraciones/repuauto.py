"""
Cliente HTTP de la API de RepuAuto (la otra sede).

Se configura en backend/.env con REPUAUTO_URL, REPUAUTO_CORREO y REPUAUTO_CLAVE.
- Inicia sesión en POST {URL}/login y guarda el token en la caché hasta poco antes
  de que venza; si la API lo rechaza (401), pide uno nuevo una sola vez.
- Usa timeouts cortos: si RepuAuto no responde, se lanza AliadoNoDisponible con un
  mensaje claro y el resto del sistema sigue funcionando.
- El navegador nunca llama a RepuAuto: solo este módulo, desde el servidor.
"""

import requests
from django.conf import settings
from django.core.cache import cache

CLAVE_CACHE = "integracion:repuauto:token"


class AliadoNoDisponible(Exception):
    """RepuAuto no está configurado, no responde o devolvió algo inesperado."""


def config():
    return settings.REPUAUTO


def configurado():
    c = config()
    return bool(c["URL"] and c["CORREO"] and c["CLAVE"])


def _url(ruta):
    return f"{config()['URL'].rstrip('/')}/{ruta.lstrip('/')}"


def _mensaje_de_error(respuesta):
    try:
        return respuesta.json().get("error") or f"código {respuesta.status_code}"
    except (ValueError, AttributeError):
        return f"código {respuesta.status_code}"


# ngrok gratis puede responder con una página HTML de aviso en lugar de reenviar la
# petición; este encabezado la salta. En cualquier otro servidor se ignora.
CABECERAS_BASE = {"ngrok-skip-browser-warning": "1", "Accept": "application/json"}


def _pedir(metodo, ruta, headers=None, **kwargs):
    cabeceras = {**CABECERAS_BASE, **(headers or {})}
    try:
        return requests.request(
            metodo, _url(ruta), timeout=config()["TIMEOUT"], headers=cabeceras, **kwargs
        )
    except requests.Timeout:
        raise AliadoNoDisponible("RepuAuto tardó demasiado en responder.")
    except requests.RequestException:
        raise AliadoNoDisponible("No se pudo conectar con RepuAuto. Revisa que su API esté en línea.")


def _token(renovar=False):
    if not renovar:
        guardado = cache.get(CLAVE_CACHE)
        if guardado:
            return guardado
    c = config()
    respuesta = _pedir("POST", "login", json={"correo": c["CORREO"], "clave": c["CLAVE"]})
    if respuesta.status_code != 200:
        raise AliadoNoDisponible(f"RepuAuto rechazó el inicio de sesión: {_mensaje_de_error(respuesta)}")
    try:
        datos = respuesta.json()
        token = datos["token"]
        expira_en = int(datos.get("expira_en", 3600))
    except (ValueError, KeyError, TypeError):
        raise AliadoNoDisponible("RepuAuto respondió el inicio de sesión en un formato inesperado.")
    # Se guarda un minuto menos de lo que dura, para no usar un token a punto de vencer.
    cache.set(CLAVE_CACHE, token, timeout=max(expira_en - 60, 30))
    return token


def facturas(desde, hasta, tipo=None):
    """GET {URL}/facturas de RepuAuto. Devuelve su JSON tal cual, ya validado."""
    if not configurado():
        raise AliadoNoDisponible("La integración con RepuAuto no está configurada en el .env.")

    params = {"desde": desde.isoformat(), "hasta": hasta.isoformat()}
    if tipo:
        params["tipo"] = tipo

    respuesta = None
    for renovar in (False, True):
        cabeceras = {"Authorization": f"Bearer {_token(renovar=renovar)}"}
        respuesta = _pedir("GET", "facturas", params=params, headers=cabeceras)
        if respuesta.status_code != 401:
            break
        cache.delete(CLAVE_CACHE)

    if respuesta.status_code != 200:
        raise AliadoNoDisponible(f"RepuAuto devolvió un error: {_mensaje_de_error(respuesta)}")
    try:
        datos = respuesta.json()
    except ValueError:
        raise AliadoNoDisponible("RepuAuto respondió algo que no es JSON.")
    if not isinstance(datos, dict) or not isinstance(datos.get("facturas"), list):
        raise AliadoNoDisponible("La respuesta de RepuAuto no tiene el formato acordado.")
    return datos
