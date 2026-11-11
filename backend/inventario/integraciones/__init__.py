"""
Integración entre sedes (PC Stock ↔ RepuAuto).

- facturas.py:    nuestras facturas en el formato acordado (el mismo de RepuAuto).
- repuauto.py:    cliente HTTP de la API de RepuAuto.
- consolidado.py: junta las facturas de las dos sedes.
- views.py:       POST /api/login, GET /api/facturas y GET /api/consolidado/.

El contrato completo está en CONTRATO-INTEGRACION.md, en la raíz del repositorio.
"""
