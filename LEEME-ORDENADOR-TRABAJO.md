# Qué montar en el ordenador del trabajo (antes del 4 nov)

1. **Kiro** (obligatorio): descargar de https://kiro.dev → instalar → iniciar sesión con tu AWS Builder ID
   (el mismo del lab). Si el portátil bloquea instaladores, pide permiso a IT hoy mismo o usa la
   alternativa con GitHub como cuenta. Comprueba que el chat de Kiro responde a un "hola".
2. **Python 3.11+** desde python.org (marcar "Add to PATH") y, en una terminal dentro de esta carpeta:
       python -m venv .venv
       .venv\Scripts\activate          (en PowerShell/CMD)
       pip install -r requirements.txt
       python probar_tools.py          → deben salir 4 líneas de texto
3. **AWS CLI v2** (https://aws.amazon.com/cli/) para configurar las credenciales que os den el día 4:
       aws configure   (o pegar las variables de entorno del portal del evento)
4. **ffmpeg** (https://www.gyan.dev/ffmpeg/builds/, versión "essentials") y añadir su carpeta `bin` al PATH.
   Lo usarás para cortar vídeo, cambiar a 9:16 y mezclar audio.
5. Copia esta carpeta `hackathon/` entera y `GUIA-HACKATHON.md` (están en el zip).

Si algo de 2-4 no se puede instalar por política de la empresa, no pasa nada: el día del evento
os dan una estación en AWS con todo; lo imprescindible es el punto 1.
