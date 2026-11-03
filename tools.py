"""
TOOLS COMPARTIDAS + modelo. Las importan los tres casos (caso1_anuncio.py, caso2_highlights.py, caso3_localizacion.py).
Patrón: igual que el lab A2 Strands. Las tools "falsas" devuelven texto fijo; cada una se sustituye
por la llamada real (boto3 / ffmpeg) cambiando solo el cuerpo, no la firma ni el docstring.
Este archivo no se ejecuta solo: no tiene Agent.
"""
import base64
import json
import logging
import os
import subprocess
import tempfile
import time
import boto3
from urllib.parse import urlparse
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
    entrada_tmp = None
    salida_tmp = None
    try:
        # Descargar el objeto de S3 a un archivo temporal
        parsed = urlparse(s3_uri)
        bucket_origen = parsed.netloc
        key_origen = parsed.path.lstrip("/")
        s3 = boto3.client("s3", region_name="eu-north-1")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
            s3.download_fileobj(bucket_origen, key_origen, tmp_in)
            entrada_tmp = tmp_in.name

        # Archivo de salida temporal
        salida_fd, salida_tmp = tempfile.mkstemp(suffix=".mp4")
        os.close(salida_fd)

        # Recortar el clip en vertical 9:16 (1080x1920) con ffmpeg
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", inicio, "-to", fin,
                "-i", entrada_tmp,
                "-vf", "crop=ih*9/16:ih,scale=1080:1920",
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac",
                salida_tmp,
            ],
            check=True,
            capture_output=True,
        )

        # Subir el clip al bucket de destino
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        inicio_safe = inicio.replace(":", "-")
        fin_safe = fin.replace(":", "-")
        bucket_destino = "karem-hackathon-278175638522"
        key_destino = f"clips/clip_{inicio_safe}_{fin_safe}_{timestamp}.mp4"
        s3.upload_file(salida_tmp, bucket_destino, key_destino)

        return f"s3://{bucket_destino}/{key_destino}"
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        return f"[FALLBACK] s3://demo-bucket/clip_{inicio}_{fin}.mp4 - {e} {stderr}"
    except Exception as e:
        return f"[FALLBACK] s3://demo-bucket/clip_{inicio}_{fin}.mp4 - {e}"
    finally:
        for ruta in (entrada_tmp, salida_tmp):
            if ruta and os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    pass

# ---------- MODELO (compartido) ----------

# Región y modelo: en el evento será us-east-1 (perfil "us."). En la cuenta personal
# (plan gratuito) la región casa es eu-north-1 y Nova se usa con el perfil "eu.".
REGION = boto3.Session().region_name or "us-east-1"   # la de `aws configure` o AWS_REGION
PREFIJO = "eu." if REGION.startswith("eu-") else "us."
model = BedrockModel(model_id=f"{PREFIJO}amazon.nova-pro-v1:0", region_name=REGION)
