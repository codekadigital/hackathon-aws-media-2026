"""Prueba las tools del agente de anuncios directamente, SIN modelo ni agente
(como probar_tools.py y probar_highlights.py).

- escribir_guion: llama a Bedrock Nova Lite y devuelve el guion en JSON.
- montar_anuncio: usa dos imágenes que ya existen en el bucket bajo generadas/
  (lista las keys con boto3 y coge las dos primeras) y textos de ejemplo.
"""
import boto3
from orquestador_anuncio import escribir_guion, montar_anuncio

# Brief del encargo.
brief = (
    "Brief: zapatillas de running NovaRun, público 25-40 años urbano, "
    "mensaje 'corre tu ciudad', tono enérgico"
)

# escribir_guion: llama a Bedrock Nova Lite (eu-north-1) y devuelve el guion en JSON.
print("=== escribir_guion ===")
guion = escribir_guion(brief)
print(guion)

# montar_anuncio: dos imágenes que ya existen en el bucket bajo generadas/.
bucket = "karem-hackathon-278175638522"
s3 = boto3.client("s3", region_name="eu-north-1")
resp = s3.list_objects_v2(Bucket=bucket, Prefix="generadas/")
claves = [
    obj["Key"]
    for obj in resp.get("Contents", [])
    if obj["Key"].lower().endswith((".png", ".jpg", ".jpeg"))
]

if len(claves) >= 2:
    imagenes = [f"s3://{bucket}/{claves[0]}", f"s3://{bucket}/{claves[1]}"]
else:
    # Si no hay dos imágenes en generadas/, avisa y usa rutas de demo.
    print("Aviso: no hay dos imágenes en generadas/; usando rutas de demo.")
    imagenes = ["s3://demo-bucket/escena1.png", "s3://demo-bucket/escena2.png"]

# Textos de ejemplo para la locución de las dos escenas.
textos = ["NovaRun, corre tu ciudad", "Cada calle es tu pista"]

print("=== montar_anuncio ===")
print("Imágenes:", imagenes)
print(montar_anuncio(imagenes, textos))
