# Hackathon AWS Media & Entertainment Agentic AI — 4 nov 2026

Kit de preparación y esqueleto de agente (Strands + Bedrock) para el hackathon de Madrid (Torre Foster, 09:00–18:30).

## Qué hay aquí (un archivo por caso de uso)
| Archivo | Para qué |
|---|---|
| `tools.py` | Las tools compartidas (transcribir, traducir, locutar, imagen, cortar clip) y el modelo. No se ejecuta solo. |
| `caso1_anuncio.py` + `probar_caso1.py` | Caso 1: anuncio desde un brief (guion con Nova, imágenes verticales con Stability, montaje con ffmpeg, Ray2 placeholder). |
| `caso2_highlights.py` + `probar_caso2.py` | Caso 2: highlights para redes (Nova 2 Lite entiende el vídeo, ffmpeg corta en 9:16). |
| `caso4_descubrimiento.py` + `probar_caso4.py` + `datos/` | Caso 4: descubrimiento conversacional (perfil del espectador + agente especialista de catálogo como tool; catálogo y audiencia de ejemplo en `datos/`). |
| `caso3_localizacion.py` + `probar_caso3.py` | Caso 3: localización y doblaje a EN/FR/DE (traducción real con Nova; Transcribe y Polly en fallback hasta el evento). |
| `requirements.txt` | strands-agents, strands-agents-tools, boto3, requests. |
| `GUIA-HACKATHON.md` | Guía larga: modelos de Bedrock, ComfyUI, Transcribe/Translate/Polly, patrones multiagente, pitch. |
| `LEEME-ORDENADOR-TRABAJO.md` | Pasos de instalación en un portátil nuevo. |

Cada `probar_casoN.py` llama a las tools de ese caso una a una, sin modelo: primero las piezas, luego el agente (`python casoN_*.py`).

## Arranque en 2 minutos (Windows, PowerShell)
```powershell
py install 3.12                      # si no tienes Python; el 3.15 falla con pyyaml
py -V:3.12 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # solo la primera vez
.venv\Scripts\activate
pip install -r requirements.txt
python probar_caso3.py               # 5 líneas = OK
```
Linux/Mac: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

## El día del evento
1. Clonar este repo en la estación o en Kiro del navegador: `git clone https://github.com/codekadigital/hackathon-aws-media-2026.git`
2. Decidir caso de uso a las 10:00 y no cambiarlo. Recortar alcance a las 12:30.
3. Sustituir tools falsas por reales de una en una; si una falla, volver al placeholder.
4. Grabar la demo en cuanto funcione la primera vez.
5. **Antes de irse: `git push`.** La cuenta AWS del evento se borra al terminar.

## Cuenta personal de AWS (plan gratuito) — lo aprendido el 31 oct
- El plan gratuito bloquea Translate, Polly, Transcribe y Rekognition (política SCP). Bedrock y S3 sí funcionan.
- S3 solo deja crear buckets en la región "casa" de la cuenta: **eu-north-1**. El bucket de pruebas está ahí (nombre en la chuleta privada).
- Nova en Europa se llama con el perfil `eu.` (`eu.amazon.nova-pro-v1:0`) en `eu-north-1`. `orquestador.py` elige el prefijo según la región configurada con `aws configure`.
- En el evento la cuenta será de pago en `us-east-1` con todo habilitado: no hace falta cambiar código, solo la región.
