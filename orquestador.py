"""
Esqueleto del agente orquestador para el hackathon (4 nov 2026).
Patrón: igual que el lab A2 Strands, pero con tools "falsas" que devuelven texto fijo.
El día 4 se sustituye cada tool por la llamada real (boto3 / ComfyUI) una a una.

Ejecutar (necesita credenciales AWS con acceso a Bedrock):
    source .venv/bin/activate
    python hackathon/orquestador.py
"""
import base64
import json
import logging
import time
import boto3
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s")

# ---------- TOOLS (placeholders; cambia el cuerpo, no la firma ni el docstring) ----------

@tool
def transcribir_video(s3_uri: str) -> str:
    """Transcribe el audio de un vídeo en S3 y devuelve el texto con marcas de tiempo.
    Real: Amazon Transcribe start_transcription_job + polling."""
    return "[00:00-00:05] Bienvenidos al partido de hoy. [00:05-00:12] Gol en el minuto tres."

@tool
def traducir_texto(texto: str, idioma_destino: str) -> str:
    """Traduce un texto al idioma destino (código ISO, p. ej. 'en', 'fr').
    Real: Amazon Translate translate_text."""
    try:
        bedrock = boto3.client("bedrock-runtime", region_name="eu-north-1")
        instruccion = (
            f"Traduce el siguiente texto al idioma cuyo código ISO es '{idioma_destino}' "
            f"(por ejemplo en = inglés, fr = francés, de = alemán). Responde únicamente "
            f"con la traducción, sin comillas, sin negritas ni explicaciones. Texto: {texto}."
        )
        respuesta = bedrock.converse(
            modelId="eu.amazon.nova-2-lite-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": instruccion}],
                }
            ],
        )
        return respuesta["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return "[FALLBACK] " + f"[{idioma_destino}] {texto}" + f" - {e}"

@tool
def generar_locucion(texto: str, idioma: str) -> str:
    """Convierte texto en voz y devuelve la ruta del mp3 generado.
    Real: Amazon Polly synthesize_speech (Engine='generative')."""
    return f"s3://demo-bucket/locucion_{idioma}.mp3"

@tool
def generar_imagen(prompt: str) -> str:
    """Genera una imagen (key visual) a partir de un prompt y devuelve su ruta.
    El prompt debe escribirse en inglés: el filtro de Stability rechaza prompts en otros idiomas.
    Real: Bedrock invoke_model con stability.stable-image-core-v1:1 (us-west-2)."""
    try:
        # 1) Generar imagen con Bedrock (Stability, us-west-2)
        bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
        cuerpo = json.dumps(
            {"prompt": prompt, "aspect_ratio": "16:9", "output_format": "png"}
        )
        respuesta = bedrock.invoke_model(
            modelId="stability.stable-image-core-v1:1",
            body=cuerpo,
        )
        resultado = json.loads(respuesta["body"].read())
        if "images" not in resultado or not resultado["images"]:
            return f"[FALLBACK] s3://demo-bucket/keyvisual.png - {resultado.get('finish_reasons')}"
        imagen_b64 = resultado["images"][0]
        imagen_bytes = base64.b64decode(imagen_b64)

        # 2) Subir a S3 (eu-north-1)
        s3 = boto3.client("s3", region_name="eu-north-1")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        bucket = "karem-hackathon-278175638522"
        key = f"generadas/keyvisual_{timestamp}.png"
        s3.put_object(
            Bucket=bucket, Key=key, Body=imagen_bytes, ContentType="image/png"
        )
        return f"s3://{bucket}/{key}"
    except Exception as e:
        return f"[FALLBACK] s3://demo-bucket/keyvisual.png - {e}"

@tool
def cortar_clip(s3_uri: str, inicio: str, fin: str) -> str:
    """Recorta un fragmento del vídeo entre los instantes inicio y fin (formato HH:MM:SS) y devuelve la ruta S3 del clip recortado.
    Real: ffmpeg con selección de tramos por marcas de tiempo (-ss / -to)."""
    return f"s3://demo-bucket/clip_{inicio}_{fin}.mp4"

# ---------- ORQUESTADOR ----------

# Región y modelo: en el evento será us-east-1 (perfil "us."). En la cuenta personal
# (plan gratuito) la región casa es eu-north-1 y Nova se usa con el perfil "eu.".
REGION = boto3.Session().region_name or "us-east-1"   # la de `aws configure` o AWS_REGION
PREFIJO = "eu." if REGION.startswith("eu-") else "us."
model = BedrockModel(model_id=f"{PREFIJO}amazon.nova-pro-v1:0", region_name=REGION)

orquestador = Agent(
    model=model,
    system_prompt=(
        "Eres el agente de localización de contenidos de una plataforma de streaming. "
        "Para localizar un vídeo: 1) transcribir_video, 2) traducir_texto al idioma pedido, "
        "3) generar_locucion con la traducción. Si te piden material promocional, usa generar_imagen (el prompt debe ir en inglés, porque el filtro de Stability rechaza prompts en otros idiomas). "
        "Si necesitas un fragmento concreto del vídeo, usa cortar_clip indicando los instantes de inicio y fin. "
        "Explica brevemente cada paso y devuelve las rutas de los archivos generados."
    ),
    tools=[transcribir_video, traducir_texto, generar_locucion, generar_imagen, cortar_clip],
)

if __name__ == "__main__":
    orquestador("Localiza el vídeo s3://demo-bucket/partido.mp4 al inglés y hazme un key visual para la promo")
