"""
Agente de highlights para redes sociales (caso: club de fútbol).

Un club tarda 6 horas en sacar los clips verticales del partido; este agente
los publica a los 10 minutos del pitido final. Recibe un vídeo en S3, detecta
los 3 momentos más destacados con Nova Lite (entender_video), recorta cada
uno con cortar_clip y, si hace falta, genera una miniatura con generar_imagen.

Ejecutar (necesita credenciales AWS con acceso a Bedrock):
    source .venv/bin/activate
    python hackathon/caso2_highlights.py
"""
import json
import logging
import boto3
from strands import Agent, tool

# Se reutilizan tools y modelo del orquestador principal.
from tools import cortar_clip, generar_imagen, model

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s")


# ---------- TOOL NUEVA ----------

@tool
def entender_video(s3_uri: str) -> str:
    """Analiza un vídeo almacenado en S3 y devuelve los 3 momentos más destacados
    en formato JSON con título, inicio y fin (HH:MM:SS).

    Usa Amazon Nova Lite (eu-north-1) a través de Bedrock converse, enviando el
    vídeo como bloque de contenido junto con la instrucción de texto.
    Si la llamada falla, devuelve un JSON de respaldo con dos momentos ficticios
    y el mensaje de error, precedido por el prefijo [FALLBACK]."""
    try:
        bedrock = boto3.client("bedrock-runtime", region_name="eu-north-1")
        respuesta = bedrock.converse(
            modelId="eu.amazon.nova-2-lite-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "video": {
                                "format": "mp4",
                                "source": {
                                    "s3Location": {"uri": s3_uri}
                                },
                            }
                        },
                        {
                            "text": (
                                "Eres editor de redes de un club de fútbol. "
                                "Busca momentos con potencial viral: goles, paradas, "
                                "regates, celebraciones, polémicas, reacciones del "
                                "público o del banquillo, momentos graciosos. "
                                "Para cada uno da inicio y fin en HH:MM:SS (entre 5 "
                                "y 20 segundos), un título corto y una puntuación de "
                                "1 a 10 según emoción, sorpresa y claridad visual. "
                                "Devuelve solo JSON con los momentos que pasen de 7, "
                                "ordenados de mayor a menor puntuación."
                            )
                        },
                    ],
                }
            ],
        )
        return respuesta["output"]["message"]["content"][0]["text"]
    except Exception as e:
        fallback = json.dumps(
            [
                {"titulo": "Momento 1", "inicio": "00:00:01", "fin": "00:00:04"},
                {"titulo": "Momento 2", "inicio": "00:00:05", "fin": "00:00:08"},
            ],
            ensure_ascii=False,
        )
        return f"[FALLBACK] {fallback} - {e}"


# ---------- AGENTE HIGHLIGHTS ----------

agente_highlights = Agent(
    model=model,
    tools=[entender_video, cortar_clip, generar_imagen],
    system_prompt=(
        "Eres el agente de highlights para redes sociales de un club de fútbol. "
        "Recibe un vídeo en S3, llama a entender_video para obtener los 3 momentos "
        "más destacados en JSON. Para cada momento, llama a cortar_clip pasando el "
        "inicio y el fin (formato HH:MM:SS) y la ruta del vídeo original. "
        "Al final, devuelve las rutas S3 de los clips recortados."
    ),
)


if __name__ == "__main__":
    agente_highlights(
        "Saca los mejores momentos de "
        "s3://karem-hackathon-278175638522/entrada/prueba12s.mp4 en vertical para Instagram"
    )
