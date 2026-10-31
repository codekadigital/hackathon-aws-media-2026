# Hackathon AWS Media & Entertainment Agentic AI — 4 nov 2026

Kit de preparación y esqueleto de agente (Strands + Bedrock) para el hackathon de Madrid (Torre Foster, 09:00–18:30).

## Qué hay aquí
| Archivo | Para qué |
|---|---|
| `orquestador.py` | Agente orquestador Strands con 5 tools placeholder (transcribir, traducir, locutar, imagen, cortar clip). Se sustituyen una a una por las reales el día del evento. |
| `probar_tools.py` | Prueba las tools sin modelo ni credenciales. Debe imprimir 5 líneas. |
| `requirements.txt` | strands-agents, strands-agents-tools, boto3, requests. |
| `GUIA-HACKATHON.md` | Guía larga: modelos de Bedrock (Ray2, Stability, Pegasus), ComfyUI, Transcribe/Translate/Polly, patrones multiagente, pitch. |
| `LEEME-ORDENADOR-TRABAJO.md` | Pasos de instalación en un portátil nuevo. |
| `chuleta.html` | Chuleta consultable desde el móvil (publicada como artifact en claude.ai). |

## Arranque en 2 minutos (Windows, PowerShell)
```powershell
py install 3.12                      # si no tienes Python; el 3.15 falla con pyyaml
py -V:3.12 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # solo la primera vez
.venv\Scripts\activate
pip install -r requirements.txt
python probar_tools.py               # 5 líneas = OK
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
- S3 solo deja crear buckets en la región "casa" de la cuenta: **eu-north-1**. Bucket: `s3://karem-hackathon-278175638522/`.
- Nova en Europa se llama con el perfil `eu.` (`eu.amazon.nova-pro-v1:0`) en `eu-north-1`. `orquestador.py` elige el prefijo según `AWS_REGION`.
- En el evento la cuenta será de pago en `us-east-1` con todo habilitado: no hace falta cambiar código, solo la región.
