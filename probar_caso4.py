"""Prueba las tools del agente de descubrimiento directamente, SIN el agente
principal (como probar_tools.py y probar_highlights.py).

- perfil_audiencia: lee datos/audiencia.json y devuelve el perfil en JSON.
- buscar_catalogo: lanza un Agent especialista con el catálogo y devuelve los
  3 títulos que mejor encajan.
"""
from caso4_descubrimiento import perfil_audiencia, buscar_catalogo

# perfil_audiencia: lee el perfil del espectador u-1001.
print("=== perfil_audiencia ===")
print(perfil_audiencia("u-1001"))

# buscar_catalogo: el especialista busca los 3 títulos que mejor encajan.
print("=== buscar_catalogo ===")
print(buscar_catalogo("algo ligero para ver en pareja un viernes"))
