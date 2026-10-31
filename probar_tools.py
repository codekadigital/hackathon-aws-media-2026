"""Prueba cada tool directamente, SIN modelo ni credenciales AWS (como agent.tool.calculator en el lab A2)."""
from orquestador import transcribir_video, traducir_texto, generar_locucion, generar_imagen, cortar_clip

# Un @tool de Strands conserva la función original: se puede llamar como función normal.
print(transcribir_video("s3://demo-bucket/partido.mp4"))
print(traducir_texto("Gol en el minuto tres", "en"))
print(generar_locucion("Goal in minute three", "en"))
print(generar_imagen("key visual partido de fútbol, estilo cinematográfico"))
print(cortar_clip("s3://demo-bucket/partido.mp4", "00:00:03", "00:00:10"))
