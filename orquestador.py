"""
Esqueleto del agente orquestador para el hackathon (4 nov 2026).
Patrón: igual que el lab A2 Strands, pero con tools "falsas" que devuelven texto fijo.
El día 4 se sustituye cada tool por la llamada real (boto3 / ComfyUI) una a una.

Ejecutar (necesita credenciales AWS con acceso a Bedrock):
    source .venv/bin/activate
    python hackathon/orquestador.py
"""
import logging
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
    return f"[{idioma_destino}] {texto}"

@tool
def generar_locucion(texto: str, idioma: str) -> str:
    """Convierte texto en voz y devuelve la ruta del mp3 generado.
    Real: Amazon Polly synthesize_speech (Engine='generative')."""
    return f"s3://demo-bucket/locucion_{idioma}.mp3"

@tool
def generar_imagen(prompt: str) -> str:
    """Genera una imagen (key visual) a partir de un prompt y devuelve su ruta.
    Real: Bedrock invoke_model con stability.stable-image-core-v1:1 (us-west-2)."""
    return "s3://demo-bucket/keyvisual.png"

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
        "3) generar_locucion con la traducción. Si te piden material promocional, usa generar_imagen. "
        "Si necesitas un fragmento concreto del vídeo, usa cortar_clip indicando los instantes de inicio y fin. "
        "Explica brevemente cada paso y devuelve las rutas de los archivos generados."
    ),
    tools=[transcribir_video, traducir_texto, generar_locucion, generar_imagen, cortar_clip],
)

if __name__ == "__main__":
    orquestador("Localiza el vídeo s3://demo-bucket/partido.mp4 al inglés y hazme un key visual para la promo")
