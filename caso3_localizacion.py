r"""
CASO 3 · Localización y doblaje (plataforma de streaming, episodios a EN/FR/DE).
Tools: transcribir_video (Transcribe; falsa en plan gratuito), traducir_texto (Nova 2 Lite, real),
generar_locucion (Polly; falsa en plan gratuito), generar_imagen (Stability, real), cortar_clip (ffmpeg, real).

Ejecutar:  .venv\Scripts\activate  →  python caso3_localizacion.py
Probar las tools sueltas:  python probar_caso3.py
"""
import logging
from strands import Agent
from tools import transcribir_video, traducir_texto, generar_locucion, generar_imagen, cortar_clip, model

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s")

orquestador = Agent(
    model=model,
    system_prompt=(
        "Eres el agente de localización y doblaje de una plataforma de streaming. "
        "Localizas episodios de series a inglés, francés y alemán. "
        "Para cada episodio sigue este orden: 1) llama a transcribir_video una sola vez para obtener la transcripción del audio; "
        "2) para cada idioma destino (inglés, francés, alemán, en ese orden) llama a traducir_texto con la transcripción y el idioma, "
        "y luego llama a generar_locucion con la traducción y el idioma. "
        "Al terminar, devuelve las rutas S3 de cada resultado (transcripción, traducción y locución) agrupadas por idioma."
    ),
    tools=[transcribir_video, traducir_texto, generar_locucion, generar_imagen, cortar_clip],
)

if __name__ == "__main__":
    orquestador("Localiza el episodio s3://demo-bucket/episodio1.mp4 a inglés, francés y alemán")
