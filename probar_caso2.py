"""Prueba las tools del agente de highlights directamente, SIN modelo ni agente (como probar_tools.py)."""
from caso2_highlights import entender_video
from tools import cortar_clip

# entender_video: llama a Bedrock Nova Lite con el vídeo de S3.
print(entender_video("s3://karem-hackathon-278175638522/entrada/prueba12s.mp4"))

# cortar_clip: recorta un tramo del vídeo entre dos marcas de tiempo.
print(cortar_clip("s3://karem-hackathon-278175638522/entrada/prueba12s.mp4", "00:00:03", "00:00:06"))
