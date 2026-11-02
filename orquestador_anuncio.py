"""
Agente de anuncios publicitarios a partir de un brief (caso: marca de deportes).

Una marca de deportes tarda 2 semanas y 15.000 euros en un spot de 15 segundos;
este agente convierte el brief en variantes en una hora. Recibe un brief de
marketing, escribe un guion de 3 escenas con Nova Lite, genera la imagen de cada
escena, monta un vídeo vertical 9:16 con ffmpeg y genera la locución.

Ejecutar (necesita credenciales AWS con acceso a Bedrock + ffmpeg instalado):
    source .venv/bin/activate
    python hackathon/orquestador_anuncio.py
"""
import json
import logging
import os
import subprocess
import tempfile
import time
import boto3
from urllib.parse import urlparse
from strands import Agent, tool

# Se reutilizan tools y modelo del orquestador principal.
from orquestador import generar_imagen, generar_locucion, model

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s")


# ---------- TOOLS NUEVAS ----------

@tool
def escribir_guion(brief: str) -> str:
    """Convierte un brief de marketing en un guion de anuncio en formato JSON.

    Llama a Amazon Nova Lite (eu-north-1) con Bedrock converse pidiendo un guion
    de 3 escenas de 5 segundos para un anuncio vertical 9:16. Cada escena lleva
    un 'prompt_imagen' en inglés estilo cinematográfico y un 'texto_locucion' en
    español de máximo 12 palabras. Devuelve solo JSON. Si la llamada falla,
    devuelve un guion falso de 3 escenas (también en JSON)."""
    try:
        bedrock = boto3.client("bedrock-runtime", region_name="eu-north-1")
        instruccion = (
            "Eres guionista publicitario. A partir del siguiente brief crea un "
            "guion para un anuncio vertical 9:16 de 15 segundos, dividido en 3 "
            "escenas de 5 segundos cada una. Para cada escena devuelve un objeto "
            "JSON con dos claves: 'prompt_imagen', un prompt en inglés, estilo "
            "cinematográfico, para generar el fotograma de esa escena; y "
            "'texto_locucion', el texto de la locución en español con un máximo "
            "de 12 palabras. Responde únicamente con un objeto JSON válido con "
            "la clave 'escenas' que contenga un array de 3 objetos. No incluyas "
            "explicaciones, markdown ni texto fuera del JSON. Brief: " + brief
        )
        respuesta = bedrock.converse(
            modelId="eu.amazon.nova-2-lite-v1:0",
            messages=[
                {"role": "user", "content": [{"text": instruccion}]}
            ],
        )
        texto = respuesta["output"]["message"]["content"][0]["text"]
        # Extraer y validar el JSON devuelto por el modelo (quita fences/texto sobrante)
        estructura = json.loads(_extraer_json(texto))
        return json.dumps(estructura, ensure_ascii=False)
    except Exception as e:
        logging.getLogger(__name__).warning("escribir_guion: usando guion falso - %s", e)
        return json.dumps(_guion_falso(), ensure_ascii=False)


def _extraer_json(texto: str) -> str:
    """Extrae el primer objeto JSON de la respuesta del modelo, eliminando
    fences de markdown y texto sobrante."""
    texto = texto.strip()
    if texto.startswith("```"):
        lineas = texto.splitlines()
        if lineas and lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas and lineas[-1].strip() == "```":
            lineas = lineas[:-1]
        texto = "\n".join(lineas).strip()
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio != -1 and fin != -1 and fin > inicio:
        return texto[inicio:fin + 1]
    return texto


def _guion_falso() -> dict:
    """Guion de respaldo de 3 escenas para el anuncio de zapatillas NovaRun."""
    return {
        "escenas": [
            {
                "prompt_imagen": (
                    "Cinematic wide shot of a young urban runner lacing up "
                    "running shoes on a city bridge at dawn, golden light, "
                    "shallow depth of field, anamorphic lens flare, vertical 9:16"
                ),
                "texto_locucion": "NovaRun, corre tu ciudad",
            },
            {
                "prompt_imagen": (
                    "Cinematic tracking shot of the runner sprinting through "
                    "neon-lit city streets at night, motion blur, dynamic energy, "
                    "low angle hero shot, vertical 9:16"
                ),
                "texto_locucion": "Cada calle es tu pista",
            },
            {
                "prompt_imagen": (
                    "Cinematic close-up of running shoes hitting wet pavement, "
                    "water splash, dramatic rim lighting, logo reveal, vertical 9:16"
                ),
                "texto_locucion": "Corre tu ciudad con NovaRun",
            },
        ]
    }


@tool
def generar_video_ray2(prompt: str) -> str:
    """Genera un clip de vídeo a partir de un prompt y devuelve su ruta S3.

    La versión real usa Bedrock start_async_invoke con el modelo luma.ray-v2:0
    en us-west-2 (no disponible en el plan gratuito). Este placeholder devuelve
    una ruta fija para que el flujo del agente pueda encadenarse."""
    return "s3://demo-bucket/escena.mp4"


@tool
def montar_anuncio(imagenes_s3: list[str], textos: list[str]) -> str:
    """Monta un anuncio vertical 1080x1920 a partir de imágenes de S3 y devuelve
    su ruta S3.

    Descarga cada imagen de S3 (eu-north-1), genera con ffmpeg un clip de 5
    segundos por imagen con un zoom lento (filtro zoompan, 125 frames a 25 fps),
    escala y recorta cada fotograma a 1080x1920, concatena los clips sin audio y
    sube el resultado al bucket 'karem-hackathon-278175638522' con la key
    'anuncios/anuncio_{timestamp}.mp4'. Si falla, devuelve una ruta de respaldo
    junto con el error.

    'textos' no se usa en el montaje (el vídeo se genera sin audio); se recibe
    para mantener la firma y el orden del flujo del agente, que usa los textos
    por separado en generar_locucion."""
    temporales = []  # rutas temporales a limpiar al final
    try:
        s3 = boto3.client("s3", region_name="eu-north-1")
        bucket = "karem-hackathon-278175638522"

        # 1) Descargar cada imagen a un archivo temporal
        imagenes_loc = []
        for uri in imagenes_s3:
            parsed = urlparse(uri)
            bucket_origen = parsed.netloc
            key = parsed.path.lstrip("/")
            _, ext = os.path.splitext(key)
            suffix = ext if ext else ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                s3.download_fileobj(bucket_origen, key, tmp)
                imagenes_loc.append(tmp.name)
                temporales.append(tmp.name)

        # 2) Clip de 5 s con zoompan por cada imagen (125 frames a 25 fps)
        clips = []
        for img_path in imagenes_loc:
            clip_fd, clip_path = tempfile.mkstemp(suffix=".mp4")
            os.close(clip_fd)
            clips.append(clip_path)
            temporales.append(clip_path)
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", img_path,
                    "-vf",
                    (
                        "scale=2160:3840:force_original_aspect_ratio=increase,"
                        "crop=2160:3840,"
                        "zoompan=z='min(zoom+0.0015,1.5)':d=125:s=1080x1920:fps=25,"
                        "format=yuv420p"
                    ),
                    "-frames:v", "125",
                    "-an",
                    clip_path,
                ],
                check=True,
                capture_output=True,
            )

        # 3) Concatenar los clips en un único vídeo vertical sin audio
        salida_fd, salida_tmp = tempfile.mkstemp(suffix=".mp4")
        os.close(salida_fd)
        temporales.append(salida_tmp)
        entradas = []
        for clip in clips:
            entradas.extend(["-i", clip])
        n = len(clips)
        concat = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
        subprocess.run(
            [
                "ffmpeg", "-y",
                *entradas,
                "-filter_complex", concat,
                "-map", "[v]",
                "-c:v", "libx264", "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-an",
                salida_tmp,
            ],
            check=True,
            capture_output=True,
        )

        # 4) Subir el resultado a S3
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        key_destino = f"anuncios/anuncio_{timestamp}.mp4"
        s3.upload_file(salida_tmp, bucket, key_destino)
        return f"s3://{bucket}/{key_destino}"
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        return f"[FALLBACK] s3://demo-bucket/anuncio.mp4 - {e} {stderr}"
    except Exception as e:
        return f"[FALLBACK] s3://demo-bucket/anuncio.mp4 - {e}"
    finally:
        for ruta in temporales:
            if ruta and os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    pass


# ---------- AGENTE DE ANUNCIOS ----------

agente_anuncio = Agent(
    model=model,
    tools=[escribir_guion, generar_imagen, generar_video_ray2, montar_anuncio, generar_locucion],
    system_prompt=(
        "Eres el agente de creación de anuncios publicitarios a partir de un brief. "
        "Recibes un brief de marketing. Sigue este orden: "
        "1) llama a escribir_guion con el brief para obtener un guion en JSON con 3 escenas, "
        "cada una con 'prompt_imagen' (en inglés) y 'texto_locucion' (en español); "
        "2) para cada escena, llama a generar_imagen pasando su 'prompt_imagen' en inglés; "
        "guarda cada ruta S3 devuelta en una lista, en el mismo orden que las escenas; "
        "3) llama a montar_anuncio pasando la lista de rutas S3 de las imágenes y la lista "
        "de textos de locución en el mismo orden; "
        "4) llama a generar_locucion pasando como 'texto' todos los textos de locución unidos "
        "por espacios y como 'idioma' 'es'; "
        "5) devuelve las rutas S3 del anuncio de vídeo y de la locución."
    ),
)


if __name__ == "__main__":
    agente_anuncio(
        "Brief: zapatillas de running NovaRun, público 25-40 años urbano, "
        "mensaje 'corre tu ciudad', tono enérgico"
    )
