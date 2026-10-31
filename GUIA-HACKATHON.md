# Guía de preparación — Hackathon AWS Media & Entertainment Agentic AI (4 nov 2026)

Escrita el 24/10/2026. Datos de modelos verificados contra la documentación de Bedrock a fecha de hoy; a 4 de noviembre puede haber cambios menores, pero no estructurales.

Lo que los labs ya te dan: Kiro, agentes Strands con tools, Converse, Knowledge Bases, Guardrails. Esta guía cubre los cinco huecos que ningún lab toca.

---

## 1. Generar vídeo, imagen y audio en AWS

### Qué hay realmente en Bedrock (octubre 2026)

| Modalidad | Modelo | modelId | API | Región | Notas |
|---|---|---|---|---|---|
| **Vídeo (texto/imagen → vídeo)** | Luma **Ray2** | `luma.ray-v2:0` | `start_async_invoke` → S3 | **us-west-2** | 5 s o 9 s, 540p/720p, 16:9 u otros. Prompt máx. 300 tokens. |
| Vídeo | Amazon Nova Reel | — | — | — | **Fin de vida 30/9/2026. Ya no funciona.** Si ves ejemplos con Nova Reel, cámbialos a Ray2. |
| **Imagen (texto → imagen)** | Stability **Stable Image Core** | `stability.stable-image-core-v1:1` | `invoke_model` | us-west-2 | Rápido y barato. |
| Imagen | Stability Stable Image Ultra / SD 3.5 Large | `stability.stable-image-ultra-v1:1`, `stability.sd3-5-large-v1:0` | `invoke_model` | us-west-2 | Más calidad. |
| Edición de imagen | 13 "Stable Image Services" | `stability.stable-image-inpaint-v1:0`, `…-remove-background-v1:0`, `…-outpaint-v1:0`, upscales, style transfer… | `invoke_model` | us-west-2 | Útiles para adaptar creatividades. |
| Imagen | Amazon Nova Canvas | `amazon.nova-canvas-v1:0` | — | — | Legacy, EOL 30/9/2026 en us-east-1. No contar con él. |
| **Voz ↔ voz (conversación)** | Amazon **Nova 2 Sonic** / 2.5 Sonic | `amazon.nova-2-sonic-v1:0` | streaming bidireccional | us-east-1 | Asistente de voz en tiempo real (caso 4 si quieres voz). |
| Audio → texto (LLM) | Mistral Voxtral Mini/Small | `mistral.voxtral-*` | Converse | — | Alternativa a Transcribe cuando quieres razonar sobre el audio. |
| **Vídeo → texto (entender vídeo)** | TwelveLabs **Pegasus 1.5** (8/10/2026) | `us.twelvelabs.pegasus-1-5-v1:0` | `invoke_model` con vídeo en S3 | us-east-1 vía perfil `us.` o `global.` | Resúmenes y **segmentación con timestamps** de todo el vídeo. Es LA pieza del caso 2 (highlights). |
| Vídeo → embeddings (búsqueda) | TwelveLabs Marengo Embed 3.0 / 2.7 | `twelvelabs.marengo-embed-*` | async | — | Búsqueda semántica de escenas. |
| Multimodal (texto+imagen+vídeo → texto) | Nova 2 Lite / Nova Pro | `us.amazon.nova-2-lite-v1:0`, `us.amazon.nova-pro-v1:0` | Converse | us-east-1 | Aceptan vídeo corto como bloque `video`. Baratos para describir clips. |
| Música / efectos | **No hay** modelo de audio generativo en Bedrock hoy | — | — | — | El correo cita "audio generado (Stability AI)": irá por ComfyUI o API externa en la estación GPU. |
| Vídeo Wan 2.2 | **No está en Bedrock** | — | — | — | Es open-weight; correrá en **ComfyUI** sobre la estación con GPU que os dan. |

Conclusión práctica: para el día 4, **vídeo = Ray2 (Bedrock) o Wan 2.2 (ComfyUI)**, **imagen = Stability (Bedrock) o ComfyUI**, **audio generado = ComfyUI/estación GPU**, **voz = Polly** (sección 3) o Nova Sonic, **entender vídeo = Pegasus 1.5 o Nova 2 Lite**.

### Código mínimo

**Vídeo con Ray2** (asíncrono: lanzas, consultas, recoges de S3):
```python
import boto3, time
br = boto3.client("bedrock-runtime", region_name="us-west-2")
job = br.start_async_invoke(
    modelId="luma.ray-v2:0",
    modelInput={"prompt": "Anuncio de 5 s: zapatillas corriendo por Madrid al amanecer, estilo cinematográfico",
                "duration": "5s", "resolution": "720p", "aspect_ratio": "9:16", "loop": False},
    outputDataConfig={"s3OutputDataConfig": {"s3Uri": "s3://MI-BUCKET/ray2/"}},
)
arn = job["invocationArn"]
while (st := br.get_async_invoke(invocationArn=arn))["status"] == "InProgress":
    time.sleep(15)
print(st["status"], st["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"])  # output.mp4 dentro
```
Para imagen → vídeo, Ray2 admite `keyframes` con una imagen inicial en S3 (ver doc "Luma AI models").

**Imagen con Stability** (síncrono, vuelve en base64):
```python
import boto3, json, base64
br = boto3.client("bedrock-runtime", region_name="us-west-2")
r = br.invoke_model(modelId="stability.stable-image-core-v1:1",
                    body=json.dumps({"prompt": "key visual de una serie de ciencia ficción, neón, 16:9",
                                     "aspect_ratio": "16:9", "output_format": "png"}))
img_b64 = json.loads(r["body"].read())["images"][0]
open("keyvisual.png", "wb").write(base64.b64decode(img_b64))
```

**Entender un vídeo con Pegasus 1.5** (el vídeo debe estar en un bucket de la MISMA región que llamas):
```python
import boto3, json
br = boto3.client("bedrock-runtime", region_name="us-east-1")
r = br.invoke_model(modelId="us.twelvelabs.pegasus-1-5-v1:0", body=json.dumps({
    "inputPrompt": "Lista los 5 momentos más emocionantes con timestamp inicio-fin y un título corto para cada uno. Responde en JSON.",
    "mediaSource": {"s3Location": {"uri": "s3://MI-BUCKET/partido.mp4", "bucketOwner": "123456789012"}},
    "maxOutputTokens": 2048}))
print(json.loads(r["body"].read()))
```

**Describir un clip corto con Nova 2 Lite** (más barato, vídeo como bloque en Converse):
```python
r = br.converse(modelId="us.amazon.nova-2-lite-v1:0", messages=[{"role": "user", "content": [
    {"video": {"format": "mp4", "source": {"s3Location": {"uri": "s3://MI-BUCKET/clip.mp4"}}}},
    {"text": "Describe la escena y sugiere un texto de promo de 15 palabras"}]}])
```

Límites a recordar: los modelos de vídeo son asíncronos y tardan 1-3 min; Ray2 solo en us-west-2 mientras Pegasus/Nova están en us-east-1, así que tendrás **dos clientes boto3 con regiones distintas** y buckets en cada región.

---

## 2. ComfyUI en 1 hora

ComfyUI es un editor de **grafos de nodos** para pipelines de medios generativos. Cada nodo hace una cosa (cargar modelo, codificar prompt, muestrear, decodificar, guardar) y se conectan por cables tipados (MODEL, CLIP, LATENT, IMAGE…). Os dan una estación con GPU y **plantillas listas**; no tienes que montar grafos desde cero.

Lo que necesitas saber hacer:
1. **Abrir la biblioteca de plantillas** (icono Templates en la barra lateral) y cargar la de **Wan 2.2 text-to-video** o **image-to-video**.
2. Identificar los 3 nodos que vas a tocar: el de **prompt positivo** (CLIP Text Encode), el de **prompt negativo**, y el de **parámetros** (ancho/alto, frames/duración, steps, seed, cfg).
3. Pulsar **Queue / Run** y ver el progreso; la salida se guarda en `output/` (nodo Save Video / Save Image).
4. **Exportar el workflow como JSON** (menú Workflow → Export / Save API format). Ese JSON es lo que un agente puede enviar por HTTP a `POST http://<host>:8188/prompt` para automatizar la generación: así conectas ComfyUI con tu agente Strands.
5. Si falla por memoria: baja resolución o número de frames; los modelos de vídeo son pesados.

Patrón de integración agente → ComfyUI (tool de Strands):
```python
import requests, json, time
COMFY = "http://localhost:8188"
def run_comfy(workflow_api_json: dict) -> str:
    pid = requests.post(f"{COMFY}/prompt", json={"prompt": workflow_api_json}).json()["prompt_id"]
    while True:
        h = requests.get(f"{COMFY}/history/{pid}").json()
        if pid in h: return json.dumps(h[pid]["outputs"])   # nombres de archivos generados
        time.sleep(5)
```
Antes de llamar, sustituyes el texto del nodo de prompt en el JSON (`workflow["<id_nodo>"]["inputs"]["text"] = prompt`).

Lectura recomendada (30 min): la guía oficial de inicio de ComfyUI y el tutorial de Wan 2.2 en docs.comfy.org.

---

## 3. Servicios de media de AWS (casos 2 y 3)

| Servicio | Para qué | Llamada básica | Devuelve |
|---|---|---|---|
| **Amazon Transcribe** | audio/vídeo → texto con timestamps por palabra, hablantes, idioma | `start_transcription_job` (asíncrono, entrada en S3) | JSON con `results.transcripts` y `results.items` (palabra, start_time, end_time); subtítulos SRT/VTT si lo pides |
| **Amazon Translate** | texto → otro idioma | `translate_text` (síncrono) | `TranslatedText` |
| **Amazon Polly** | texto → voz (mp3/ogg), voces neurales y generativas en muchos idiomas | `synthesize_speech` | stream de audio; con `SpeechMarkTypes` te da timestamps para sincronizar |
| **Amazon Rekognition Video** | detección de escenas/planos, personas famosas, etiquetas, moderación | `start_segment_detection`, `start_label_detection` (asíncrono) | segmentos con timestamps; alternativa barata a Pegasus para cortar por planos |
| **AWS Elemental MediaConvert** | recortar, re-encodear, apilar vertical 9:16, quemar subtítulos | `create_job` con JSON de settings | archivo en S3 |
| **ffmpeg** (en la estación) | lo mismo que MediaConvert pero inmediato | subprocess | archivo local |

### Pipeline del caso 3 (localización y doblaje)
```
vídeo.mp4 → Transcribe (es-ES) → Translate (en-US) → Polly (voz en inglés, speech marks)
          → ffmpeg: reemplazar/mezclar pista de audio + subtítulos VTT → vídeo_en.mp4
```
```python
import boto3, time, json, urllib.request
tr = boto3.client("transcribe", region_name="us-east-1")
tr.start_transcription_job(TranscriptionJobName="job1", Media={"MediaFileUri": "s3://MI-BUCKET/video.mp4"},
                           IdentifyLanguage=True, Subtitles={"Formats": ["vtt"]})
while (j := tr.get_transcription_job(TranscriptionJobName="job1"))["TranscriptionJob"]["TranscriptionJobStatus"] == "IN_PROGRESS":
    time.sleep(10)
text = json.load(urllib.request.urlopen(j["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]))["results"]["transcripts"][0]["transcript"]

tl = boto3.client("translate", region_name="us-east-1")
en = tl.translate_text(Text=text, SourceLanguageCode="auto", TargetLanguageCode="en")["TranslatedText"]

polly = boto3.client("polly", region_name="us-east-1")
audio = polly.synthesize_speech(Text=en, VoiceId="Matthew", Engine="generative", OutputFormat="mp3")
open("dub_en.mp3", "wb").write(audio["AudioStream"].read())
```
```bash
# mezclar la nueva voz y quemar subtítulos
ffmpeg -i video.mp4 -i dub_en.mp3 -map 0:v -map 1:a -c:v copy -shortest video_en.mp4
```

### Pipeline del caso 2 (highlights y promos)
```
vídeo largo → Pegasus 1.5 (o Rekognition segments + Transcribe) → lista de momentos [inicio, fin, título]
            → ffmpeg: cortar cada momento, reencuadrar a 9:16, añadir música (pista libre o generada en ComfyUI)
            → Nova 2 Lite: escribir caption y hashtags por clip → publicar/mostrar
```
```bash
ffmpeg -ss 00:12:03 -to 00:12:18 -i partido.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" -i musica.mp3 -map 0:v -map 1:a -shortest clip1.mp4
```

Con esto los casos 2 y 3 se convierten en "un agente que llama a 4 tools en orden". Lo nuevo no es la IA, es saber qué servicio hace cada paso.

---

## 4. Patrones multi-agente con Strands (caso 4 y orquestación en general)

Strands ofrece cuatro patrones. Para un hackathon de un día, usa los dos primeros.

| Patrón | Cuándo | Cómo se ve |
|---|---|---|
| **Agents as tools** (orquestador + especialistas) | Casi siempre. Un agente "jefe" decide a qué especialista llamar. Predecible, fácil de depurar. | `@tool` que envuelve un `Agent` |
| **Swarm** | Los agentes se pasan el control entre sí sin orden fijo. Más creativo, menos controlable. | `Swarm([...], entry_point=..., max_handoffs=20)` |
| **Graph** | Flujo con pasos y condiciones conocidas (pipeline). | `GraphBuilder` con nodos y aristas condicionales |
| **Workflow** | Tareas con dependencias, solo como tool de `strands-agents-tools`. | — |

### Lo que ya sabes del lab A2 Strands (hecho 26 oct) y cómo escala al hackathon

El lab te dio el 80 % del patrón. Lo que cambia el día 4 es solo la **escala**: más tools, un orquestador y tools que llamen a servicios reales.

| Lab A2 (ya hecho) | Hackathon (misma idea, más grande) |
|---|---|
| `@tool def calculator(expression)` | `@tool def transcribe_video(s3_uri)`, `@tool def generate_image(prompt)`, `@tool def search_catalog(query)` |
| `Agent(model="amazon.nova-lite-v1:0", tools=[calculator, weather])` | Orquestador con `BedrockModel(model_id="us.amazon.nova-pro-v1:0")` o Claude, y 3 a 5 tools |
| `weather()` devolvía siempre "Sunny" (placeholder) | Haz lo mismo al principio: tools "fake" que devuelven texto fijo, y sustitúyelas por las reales una a una |
| `agent.tool.calculator(expression="2+3*4")` | Prueba cada tool directamente antes de dejar que el agente la elija |
| `logging.getLogger("strands").setLevel(INFO)` | Enseña ese log en la demo: se ve qué tool elige y por qué |
| `websearch` con `ddgs` | Tool que llama a `boto3` (Transcribe, Bedrock, Rekognition) o a ComfyUI por HTTP |
| Una tool que envuelve una búsqueda | Una tool que envuelve **otro Agent** (agents as tools, abajo) |

**¿Tendré que programar los agentes?** Sí, en Python con Strands (o Kiro te genera el esqueleto). Pero "programar un agente" es exactamente lo del lab: funciones con `@tool` + docstring claro + un `Agent` con system prompt. La lógica de decidir qué tool usar la pone el modelo, no tú. Lo que de verdad lleva tiempo es escribir las tools (llamadas a servicios) y el prompt del orquestador.

**Receta de arranque para el día 4 (primeros 60 min):**
1. Crea el orquestador con 3 tools placeholder que devuelvan texto fijo (como `weather()`).
2. Comprueba que el agente las encadena bien con 2 o 3 preguntas de ejemplo.
3. Sustituye una tool por la real (p. ej. Transcribe o la Knowledge Base). Vuelve a probar.
4. Repite con las demás. Si una tool real falla, vuelve al placeholder y sigue; la demo no se para.

### Agents as tools (el que recomiendo para el caso 4)
```python
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

model = BedrockModel(model_id="us.amazon.nova-pro-v1:0")   # o un Claude vía us.anthropic.…

@tool
def catalog_search(query: str) -> str:
    """Busca títulos en el catálogo (Knowledge Base) a partir de una descripción o estado de ánimo."""
    kb = Agent(model=model, system_prompt="Eres el buscador del catálogo. Usa retrieve sobre la KB y devuelve 5 títulos con sinopsis.",
               tools=[kb_retrieve_tool], callback_handler=None)
    return str(kb(query))

@tool
def audience_profile(user_id: str) -> str:
    """Devuelve el perfil Audience 360 del espectador (géneros, horario, dispositivos, histórico)."""
    return lookup_audience360(user_id)      # lectura del dataset sintético que os dan

@tool
def trailer_promo(title: str) -> str:
    """Genera una promo corta (texto + imagen key visual) para un título."""
    ...

orchestrator = Agent(
    model=model,
    system_prompt=("Eres el asistente de descubrimiento de contenido de una plataforma de streaming. "
                   "Primero consulta audience_profile, luego catalog_search, y propone 3 opciones explicando por qué encajan. "
                   "Responde en el idioma del usuario."),
    tools=[audience_profile, catalog_search, trailer_promo],
)
print(orchestrator("Soy el usuario u-1042, quiero algo ligero para ver con mi pareja esta noche"))
```

### Swarm (si queréis enseñar "varios agentes colaborando")
```python
from strands import Agent
from strands.multiagent import Swarm
researcher = Agent(name="researcher", system_prompt="Investigas tendencias y datos de audiencia…")
writer     = Agent(name="writer",     system_prompt="Escribes briefs de promo…")
reviewer   = Agent(name="reviewer",   system_prompt="Revisas tono de marca y cumplimiento…")
swarm = Swarm([researcher, writer, reviewer], entry_point=researcher, max_handoffs=10, max_iterations=15)
result = swarm("Crea el brief de una promo para la final de la liga dirigida a jóvenes 18-25")
print(result.status, [n.node_id for n in result.node_history])
```
Pon siempre `max_handoffs`: sin límite, los agentes pueden pasarse la pelota indefinidamente.

### Bedrock AgentCore (solo para saber qué es)
Servicio gestionado para **desplegar** agentes: *Runtime* (tu agente en un contenedor con endpoint invoke), *Memory* (memoria corta y larga entre sesiones), *Gateway* (convierte APIs y Lambdas en tools MCP), *Observability*. Se despliega con `agentcore configure` y `agentcore launch` desde el starter toolkit. En el hackathon probablemente no te dé tiempo a desplegar; menciónalo en la arquitectura como "siguiente paso a producción" y los SAs lo valorarán.

### Observabilidad rápida (para la demo)
Activa *Model invocation logging* en Bedrock; cada pregunta del agente genera varias líneas con `stopReason = tool_use … end_turn`. Enseñar ese log en la presentación demuestra que el agente razona y actúa.

---

## 5. Presentar la solución (17:00, ante el panel)

Tienes unos 5 minutos. Estructura que funciona:
1. **Problema (30 s)**: un cliente de M&E concreto y su dolor en números ("tarda 3 días en localizar un episodio").
2. **Solución (30 s)**: una frase. "Un agente que dobla un episodio a 5 idiomas en 20 minutos".
3. **Arquitectura (1 min)**: un diagrama con cajas: Usuario → Kiro/UI → Agente orquestador (Strands) → tools (Transcribe, Translate, Polly, Pegasus, Ray2/ComfyUI, KB) → S3 → salida. Marca qué es gestionado por AWS.
4. **Demo (2 min)**: vídeo grabado de la demo, nunca en vivo. Graba en cuanto funcione la primera vez.
5. **Valor y siguiente paso (30 s)**: ahorro, nuevos ingresos, cómo pasa a producción (AgentCore, Guardrails, coste por minuto de vídeo).
6. **Equipo y reparto**: quién hizo qué, en una línea.

Consejos:
- Decidid el caso de uso a las 10:00 y no lo cambiéis. Recortad alcance a las 12:30 si vais tarde.
- Repartid: 1 persona agente/orquestación, 1-2 tools de media (Transcribe/Polly/ffmpeg), 1 ComfyUI/vídeo, 1 datos Audience 360 + KB, 1 slides y demo.
- Preparad un plan B sin GPU: si ComfyUI falla, Ray2 o imagen estática + Polly siguen contando una historia.
- Guardad todo en S3 con nombres claros; el jurado pregunta "¿esto es real?" y enseñar el bucket responde.

---

## Dónde encaja cada caso de uso

| Caso | Entender | Generar | Agentes | Dato extra |
|---|---|---|---|---|
| 1 Vídeo publicitario | Nova 2 Lite lee el brief | Ray2 o Wan 2.2 (vídeo), Stability (key visual), ComfyUI (audio), Polly (locución) | 1 orquestador + tool por medio | Audience 360 para variantes por segmento |
| 2 Highlights y promos | **Pegasus 1.5** (timestamps) o Rekognition segments + Transcribe | ffmpeg 9:16 + música + Nova caption | orquestador + tool "cortar" + tool "caption" | Audience 360 para elegir qué momentos a quién |
| 3 Localización y doblaje | Transcribe | Translate + Polly + ffmpeg | pipeline lineal (Graph o tools en orden) | Guardrails para tono/marca |
| 4 Descubrimiento conversacional | Converse / Nova Sonic (voz) | Stability para carátulas | **agents as tools**: perfil + catálogo (KB) + promo | Audience 360 es el núcleo |

---

## Plan de estudio de esta guía (encaja en PLAN-LABS.md)
- **Jue 30, mañana (2 h)**: sección 1 y 3. Ejecuta mentalmente los 4 snippets; si tienes cuenta propia, prueba Stability y Polly (céntimos).
- **Dom 2 (2 h)**: sección 2 y 4. Tutorial de ComfyUI 30 min; monta el orquestador de 3 tools de la sección 4 con tools falsas que devuelvan strings; eso ya es tu esqueleto para el día 4.
- **Lun 3 (1 h)**: sección 5. Elige caso con el equipo, dibuja la arquitectura, reparte roles.

## Fuentes consultadas (24/10/2026)
- Bedrock "Models at a glance": https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html
- Nova Reel (EOL 30/9/2026): https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-reel.html
- Luma Ray2: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-luma-ai-ray2.html
- TwelveLabs Pegasus 1.5: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-twelvelabs-pegasus-v1-5.html
- Stable Image Core: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-stability-ai-stable-image-core-1-0.html
- Strands agents-as-tools: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/
- Strands Swarm: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/
- AgentCore getting started: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-toolkit.html
- Catálogo Bedrock 2026 (tercero): https://hidekazu-konishi.com/entry/amazon_bedrock_model_catalog_2026.html
