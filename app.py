import re
import threading
import time
from flask import Flask, render_template, request, redirect, send_file
import yt_dlp
import os
from pathlib import Path

# cookies_content = os.getenv("COOKIES_CONTENT")
# if cookies_content:
#     with open("cookies.txt", "w", encoding="utf-8") as f:
#         f.write(cookies_content)

app = Flask(__name__)

# Ruta para el formulario principal
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            return redirect(f"/formatos?url={url}")
    return render_template('index.html')

# Ruta para mostrar los formatos disponibles
@app.route('/formatos')
def formatos():
    url = request.args.get('url')
    if not url:
        return redirect('/')
    
    opciones = {
        'quiet': True,
        'skip_download': True,
        'forcejson': True,
        'extract_flat': False,
        'cookies': 'cookies.txt',  # <- Ruta a las cookies
        'cookiefile': 'cookies.txt',
    }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=False)
            formatos = info.get('formats', [])
            titulo = info.get('title', 'Sin título')
            duracion = info.get("duration") or 0
            thumbnail = info.get('thumbnail', '')

        print("Duración cruda:", duracion)
        print("Tipo de duración:", type(duracion))
        # Duracion en hh:mm:ss
        duracion = time.strftime('%H:%M:%S', time.gmtime(duracion))

        # Filtrar formatos que puedan descargarse directamente
        formatos_filtrados = []
        for f in formatos:
            try:
                if f.get('filesize') or f.get('filesize_approx'):
                    tamanio = f.get('filesize', f.get('filesize_approx'))
                    formatos_filtrados.append({
                        'format_id': f.get('format_id', 'N/A'),
                        'ext': f.get('ext', 'N/A'),
                        'resolution': f.get('resolution') or f.get('abr', 'N/A'),
                        'tamanio': round(tamanio / (1024 * 1024), 2),
                        'tipo': 'audio' if f.get('vcodec') == 'none' else 'video',
                    })
            except Exception as err:
                print("❌ Error procesando un formato:", err)
                continue

        print("formatos filtrados", formatos_filtrados)
        # print("formatos", formatos)

        return render_template("results.html",
            titulo=info.get("title"),
            thumbnail=info.get("thumbnail"),
            duracion=duracion,
            formatos=formatos_filtrados,
            url=url
        )
    
    except Exception as e:
        return f"Error al analizar el video: {str(e)}"

# Función para eliminar el archivo después de que se haya enviado
def eliminar_archivo(ruta_archivo):
    # Asegurarse de que el archivo se elimine en un hilo separado
    try:
        # Esperar un pequeño tiempo antes de eliminar para asegurarnos de que el archivo ya no esté siendo utilizado
        time.sleep(1)
        os.remove(ruta_archivo)
        print(f"Archivo eliminado: {ruta_archivo}")  # Depuración
    except Exception as e:
        print(f"Error al eliminar el archivo: {str(e)}")  # Depuración

# Función para limpiar caracteres no válidos en nombres de archivos
def limpiar_titulo(titulo):
    # Reemplazar solo los dos puntos por guion bajo
    titulo= titulo.replace(":", "_")
    titulo = titulo.replace("|", "｜")  # Reemplazar "｜" por "|"
    return titulo

# Ruta para descargar el formato elegido
@app.route('/descargar')
def descargar():
    audio_mp3 = request.args.get('audio') == '1'
    url = request.args.get('url')
    format_id = request.args.get('format_id')
    if not url or not format_id:
        return redirect('/')

    # Ruta absoluta para guardar el archivo en el directorio de tu proyecto
    carpeta_descarga = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
    output_path = os.path.join(carpeta_descarga, '%(title)s.%(ext)s')

    print(f"Ruta de descarga configurada: {output_path}")  # Depuración

    opciones = {
        'format': format_id,
        'outtmpl': output_path,
        'postprocessors': [],
        'quiet': True,
    }

    if audio_mp3:
        opciones['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        })

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = info_dict.get('title', 'audio')
            final_ext = 'mp3' if audio_mp3 else info_dict.get('ext', 'mp4')

            # Limpiar el nombre del archivo, reemplazando los dos puntos por guion bajo
            nombre_archivo = f"{limpiar_titulo(title)}.{final_ext}"

            # Ruta completa del archivo descargado
            ruta_archivo = os.path.join(carpeta_descarga, nombre_archivo)
            print(f"Buscando archivo en: {ruta_archivo}")  # Depuración

            # Verificar si el archivo existe en la carpeta de descargas
            if os.path.exists(ruta_archivo):
                print(f"Archivo encontrado: {ruta_archivo}")  # Depuración
                response = send_file(ruta_archivo, as_attachment=True)

                # Crear un hilo para eliminar el archivo después de enviarlo
                threading.Thread(target=eliminar_archivo, args=(ruta_archivo,)).start()

                return response
            else:
                print(f"Archivo no encontrado: {ruta_archivo}")  # Depuración
                return "Archivo no encontrado después de la descarga."

    except Exception as e:
        return f"Error al descargar: {str(e)}"
    
# if __name__ == '__main__':
#     app.run(
#         debug=True,
#         host='0.0.0.0',
#         port=5000
#         )
