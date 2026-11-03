"""
Agente de descubrimiento conversacional de contenido (caso 4).

Un espectador tarda 8 minutos en decidir qué ver y uno de cada cinco abandona;
este asistente lo resuelve en 30 segundos de conversación. El espectador se
presenta con su id; el asistente consulta su perfil de audiencia, busca en el
catálogo los 3 títulos que mejor encajan y propone opciones explicando por qué.
Si se le pide, genera una carátula promocional con generar_imagen.

Patrón: agents-as-tools (un @tool que envuelve un Agent especialista).

Ejecutar (necesita credenciales AWS con acceso a Bedrock):
    source .venv/bin/activate
    python hackathon/caso4_descubrimiento.py
"""
import json
import logging
import os

from strands import Agent, tool

# Se reutilizan el modelo y la tool de imagen del orquestador principal.
from tools import generar_imagen, model

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s")

# Directorio base del script: resuelve datos/*.json sin importar desde dónde
# se ejecute el comando.
_BASE = os.path.dirname(os.path.abspath(__file__))


# ---------- TOOLS ----------

@tool
def perfil_audiencia(user_id: str) -> str:
    """Devuelve el perfil del espectador identificado por user_id como JSON.
    Lee datos/audiencia.json; si el usuario no existe, devuelve
    '[FALLBACK] perfil desconocido'."""
    ruta = os.path.join(_BASE, "datos", "audiencia.json")
    with open(ruta, encoding="utf-8") as f:
        audiencia = json.load(f)
    for espectador in audiencia:
        if espectador["id"] == user_id:
            return json.dumps(espectador, ensure_ascii=False)
    return "[FALLBACK] perfil desconocido"


@tool
def buscar_catalogo(consulta: str) -> str:
    """Busca en el catálogo los 3 títulos que mejor encajan con la consulta
    (género, estado de ánimo, contexto).

    Patrón agents-as-tools: crea dentro un Agent especialista que tiene el
    catálogo completo en su system_prompt. El especialista devuelve id, titulo
    y una frase de por qué encaja cada título."""
    ruta = os.path.join(_BASE, "datos", "catalogo.json")
    with open(ruta, encoding="utf-8") as f:
        catalogo = f.read()
    especialista = Agent(
        model=model,
        callback_handler=None,
        system_prompt=(
            "Eres el buscador del catálogo de una plataforma de streaming "
            "española. A continuación tienes el catálogo completo en JSON:\n\n"
            + catalogo
            + "\n\nEl usuario te da una consulta (género, estado de ánimo, "
            "contexto). Devuelve los 3 títulos del catálogo que mejor encajen "
            "con la consulta. Para cada uno indica su id, su titulo y una "
            "frase breve explicando por qué encaja. Responde en español."
        ),
    )
    resultado = especialista(consulta)
    return str(resultado)


# ---------- AGENTE DE DESCUBRIMIENTO ----------

asistente = Agent(
    model=model,
    system_prompt=(
        "Eres el asistente de descubrimiento de una plataforma de streaming "
        "española. Cuando el espectador se presente con su id (empieza por "
        "'u-'), llama a perfil_audiencia para obtener su perfil. Luego llama a "
        "buscar_catalogo con una consulta que combine lo que pide el espectador "
        "con su perfil (géneros favoritos, tono, horario, idioma). Propón 3 "
        "opciones explicando en una frase por qué encajan con él. Responde en "
        "el idioma del espectador que aparezca en su perfil y pregunta si "
        "quiere afinar la búsqueda. Si el espectador te pide una carátula o "
        "imagen promocional de algún título, llama a generar_imagen con un "
        "prompt en inglés que describa la carátula."
    ),
    tools=[perfil_audiencia, buscar_catalogo, generar_imagen],
)


if __name__ == "__main__":
    print("Asistente de descubrimiento. Escribe 'salir' para terminar.")
    while True:
        mensaje = input("Tú: ")
        if mensaje.strip().lower() == "salir":
            break
        asistente(mensaje)
