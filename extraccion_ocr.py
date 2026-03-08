import os
import base64
from datetime import date
import pandas as pd
from openai import OpenAI
from pathlib import Path
import json
from dotenv import load_dotenv
from PIL import Image
import re


def json_fallback():
    """JSON estándar si el modelo no devuelve algo parseable."""
    return {
        "destinatario_raw": None,
        "campos": {
            "nombre_o_titulo": None,
            "cargo_dependencia": None,
            "direccion": None,
            "colonia": None,
            "municipio_o_alcaldia": None,
            "estado": None,
            "codigo_postal": None,
            "extras": None,
            "contacto": None,
            "indicaciones": None
        },
        "observaciones_ia": "No se pudo obtener un JSON válido del modelo."
    }

def image_to_base64(path: Path) -> str:
    """Convierte imagen a base64 (JPEG)."""
    with Image.open(path) as img:
        img = img.convert("RGB")
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def main():
    # --- FECHA (sin depender de locale del sistema) ---
    meses_es = [
        "Enero","Febrero","Marzo","Abril","Mayo","Junio",
        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
    ]

    fecha_hoy = date.today()
    anio = fecha_hoy.year
    dia = fecha_hoy.day
    mes = meses_es[fecha_hoy.month - 1]  # <- evita problemas de locale

    # Nombre archivo salida
    fecha_archivo = fecha_hoy.strftime("%d-%m-%Y")
    nombre_excel = f"procesados_{fecha_archivo}.xlsx"

    # Orden de columnas deseado en el Excel
    columns = [
        "fecha",
        "indicaciones",
        "nombre_o_titulo",
        "cargo_dependencia",
        "direccion",
        "colonia",
        "municipio_o_alcaldia",
        "estado",
        "codigo_postal",
        "contacto",
        "extras",
        "observaciones_ia",
        "imagen",
        "destinatario_raw",
    ]

    # Carpetas RECORTES
    # # Carpeta con imágenes Ajusco
    carpeta_recortes_ajusco = Path(Path.home(),f"OneDrive - FGC\\Archivos de Stefano Mendoza - EVIDENCIAS-OCR\\{anio}\\{mes}\\{dia}\\Ajusco\\RECORTES")
    print(carpeta_recortes_ajusco)

    # # Carpeta con imágenes Coyoacan
    carpeta_recortes_coyoacan = Path(Path.home(),f"OneDrive - FGC\\Archivos de Stefano Mendoza - EVIDENCIAS-OCR\\{anio}\\{mes}\\{dia}\\Coyoacan\\RECORTES")
    print(carpeta_recortes_coyoacan)

    carpetas = []
    if carpeta_recortes_ajusco.exists():
        carpetas.append(carpeta_recortes_ajusco)
    if carpeta_recortes_coyoacan.exists():
        carpetas.append(carpeta_recortes_coyoacan)

    # Extensiones válidas
    extensiones = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")

    resultados = []

    load_dotenv()  # carga el archivo .env
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    system_prompt = """
    === INSTRUCCIONES ===
    Eres un asistente especializado en OCR para sobres.
    
    TAREA:
    A partir de la imagen proporcionada, extrae únicamente el texto del DESTINATARIO que aparece en la etiqueta blanca del sobre y estructura la información en el JSON indicado
    
    REGLAS GENERALES:
    - Copia el texto exactamente como aparece.
    - Respeta mayúsculas, minúsculas, acentos, saltos de línea y puntuación.
    - No corrijas, no completes, no inventes información.
    - No uses información ni contexto externo al texto visible en la etiqueta.
    - Si alguna parte del texto es ilegible, escribe: "ilegible" en el campo correspondiente.
    - Si un campo NO existe en el texto, escribe: null.
    - Si detectas algún número pero es ilegible, marca el campo como "ilegible" y describe brevemente en "observaciones_ia" qué número o dato no se puede leer.
    
    ALCANCE DEL TEXTO:
    - Considera como parte del DESTINATARIO el nombre, cargo, dirección, colonia, municipio/alcaldía, estado, código postal, teléfonos, horarios y referencias de entrega.
    - El texto bajo secciones como "PARA:", "DOMICILIO:", "TEL.", "Horario de recepción", etc., forma parte del destinatario.
    - El texto bajo "CON COPIA AL" se debe incluir completo en el campo "extras".
    - El texto bajo "CONTENIDO", "ASUNTO" u otros similares también se debe incluir en "extras".

    Formato de salida (OBLIGATORIO):
    - Devuelve únicamente el JSON.
    - No uses bloques de código (no uses ```).
    - No incluyas la palabra "json" en la salida final ni ningún otro texto adicional.
    - La salida debe comenzar con '{' y terminar con '}'.
    - Sin comentarios, sin explicaciones.
    
    REGLAS DE CAMPOS:
    - Para todos los campos de "campos":
      - Si el dato es legible: escribe el texto tal cual aparece.
      - Si el dato es ilegible: escribe "ilegible".
      - Si el dato no existe en la etiqueta: escribe null.
    - Campo "direccion": debe contener solamente calle y número (y piso, interior, torre, etc. si se menciona). La colonia va en "colonia".
    - Campo "contacto": incluye teléfonos, extensiones y cualquier otro medio de contacto visible.
    - Campo "indicaciones": incluye referencias de ubicación (entre calles, horarios de recepción, puntos de referencia, instrucciones de acceso, etc.).
    
    Devuelve SOLO este JSON:
    
    {
      "destinatario_raw": "",
      "campos": {
        "nombre_o_titulo": "",
        "cargo_dependencia": "",
        "direccion": "",
        "colonia": "",
        "municipio_o_alcaldia": "",
        "estado": "",
        "codigo_postal": "",
        "extras": "",
        "contacto": "",
        "indicaciones": ""
      },
      "observaciones_ia": ""
    }

    "destinatario_raw":
    - Debe contener TODO el texto del destinatario tal cual aparece en la etiqueta (incluyendo nombre, cargo, dirección, teléfonos, horarios, copias, contenido, etc.), en un solo string, respetando saltos de línea.
    
    "observaciones_ia":
    - Escribe observaciones breves sobre:
      - Partes cortadas.
      - Teléfonos u otros números ilegibles.
      - Reflejos, inclinación, baja resolución u otros problemas de lectura.
      - O, si todo es perfectamente legible, escribe: "Sin observaciones."
    
    === FIN INSTRUCCIONES ===
    
    A continuación tienes dos ejemplos de cómo se espera la respuesta en formato JSON (son solo ejemplos):

    ===== Ejemplo1=====
    {
      "destinatario_raw": "MTRO. BRUNO MANUEL IBARRA REYES. TITULAR DE LA ADMINISTRACIÓN DESCONCENTRADA DE RECAUDACIÓN MÉXICO “2” CON SEDE EN MÉXICO DEL SERVICIO DE ADMINISTRACIÓN TRIBUTARIA. AV. SOR JUANA INÉS DE LA CRUZ NO. 22 ENTRE AV BUGAMBILIAS Y GUSTAVO A MADERO, TLALNEPANTLA DE BAZ, ESTADO DE MÉXICO, C.P. 54000 TEL OFICINA 312-313-0513 EXT 312 JUAN MANUEL LOPEZ CELULAR 55 8404 8609, Horario de recepción: 9:00am a 14:00 horas de lunes a viernes entrada por caseta 3, OFICIO 1513, ASUNTO: ENTREGA INFORMACION",
      "campos": {
        "nombre_o_titulo": "MTRO. BRUNO MANUEL IBARRA REYES.",
        "cargo_dependencia": "TITULAR DE LA ADMINISTRACIÓN DESCONCENTRADA DE RECAUDACIÓN MÉXICO “2” CON SEDE EN MÉXICO DEL SERVICIO DE ADMINISTRACIÓN TRIBUTARIA.",
        "direccion": "AV. SOR JUANA INÉS DE LA CRUZ NO. 22, PISO 2",
        "colonia": "COLONIA VILLA DE SERIS",
        "municipio_o_alcaldia": "TLALNEPANTLA DE BAZ",
        "estado": "ESTADO DE MÉXICO",
        "codigo_postal": "54000",
        "extras": "OFICIO 1513 ASUNTO: ENTREGA INFORMACION JUAN MANUEL LOPEZ",
        "contacto": "TEL OFICINA 312-313-0513 EXT 312 CELULAR 55 8404 8609",
        "indicaciones": "ENTRE AV BUGAMBILIAS Y GUSTAVO A MADERO, Horario de recepción: 9:00am a 14:00 horas de lunes a viernes entrada por caseta 3"
      },
      "observaciones_ia": "imagen algo borrosa hay un número que no se alcanza a visualizar revisar para llenar el número de forma correcta."
    }
    ====== FIN EJEMPLO1 ======
    ====== EJEMPLO 2 ======
    {
      "destinatario_raw": "TITULAR DEL MUNICIPIO DE JERÉCUARO , GUANAJUATO PRESIDENCIA MUNICIPAL FRAY ANGEL JUAREZ # 32, CENTRO JERECUARO, GTO. CP. 38540 Horario de recepción: 9:00am a 14:00 horas de lunes a viernes TEL: 812020 2455 INFORMES SOBRE ENVIO, COMUNICARSE AL TELÉFONO 5200-1500, EXT. 10559, 10191 O 10306. ASUNTO: SE REMITE INFORMACIÓN RELATIVA AL CONTRIBUYENTE: TEÓFILO MANUEL GARCÍA CORPUS.",
      "campos": {
        "nombre_o_titulo": "TITULAR DEL MUNICIPIO DE JERÉCUARO",
        "cargo_dependencia": "GUANAJUATO PRESIDENCIA MUNICIPAL",
        "direccion": "FRAY ANGEL JUAREZ # 32",
        "colonia": "CENTRO",
        "municipio_o_alcaldia": "JERECUARO",
        "estado": "GTO",
        "codigo_postal": "38540",
        "extras": "ASUNTO: SE REMITE INFORMACIÓN RELATIVA AL CONTRIBUYENTE: TEÓFILO MANUEL GARCÍA CORPUS.",
        "contacto": "TEL: 812020 2455",
        "indicaciones": "Horario de recepción: 9:00am a 14:00 horas de lunes a viernes INFORMES SOBRE ENVIO, COMUNICARSE AL TELÉFONO 5200-1500, EXT. 10559, 10191 O 10306"
      },
      "observaciones_ia": "imagen algo borrosa hay un número que no se alcanza a visualizar revisar para llenar el número de forma correcta."
    }
    ======FIN EJEMPLO 2 ======
    """

    user_prompt = "Devuelve únicamente el JSON requerido, sin ningún texto adicional, sin ``` y sin la palabra json."

    for carpeta in carpetas:
        print(f"carpeta:\t{carpeta}")
        rows = []

        for archivo in os.listdir(carpeta):
            print(archivo)
            if archivo.endswith(extensiones):
                ruta = Path(carpeta,archivo)
                print(f"Procesando: {archivo}")

                # imagen_base64 = encode_image(ruta)
                data_url = image_to_base64(ruta)
                print("Se convirtio la imagen a base 64")
                print("Obteniendo respuesta...")
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        temperature=0,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system",
                             "content": system_prompt
                             },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": user_prompt},
                                    {"type": "image_url", "image_url": {"url": data_url}},
                                ]
                            }
                        ],
                        max_tokens=1200
                    )
                except Exception as e:
                    print(f"ha ocurrido un error\n{e}\n con la imagen: {archivo}")
                    continue

                contenido = response.choices[0].message.content
                print("Se obtubo el contenido")
                try:
                    json_result = json.loads(contenido)
                    print(f"contenido sin limpiar:\n{contenido}")

                except json.JSONDecodeError as e:
                    print(f"ha ocurrido un error\n{e}")
                    contenido_limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", contenido.strip(), flags=re.IGNORECASE | re.MULTILINE)
                    contenido_limpio = contenido_limpio.strip()
                    # Intenta convertir texto en JSON plano
                    json_result = json.loads(contenido_limpio)
                    print(contenido_limpio)
                except Exception as e:
                    print(f"ha ocurrido un error\n{e}")
                    json_result = None

                if json_result is None:
                    json_result = json_fallback()

                # Aplanar al esquema requerido (sin columnas de "confianza")
                campos = json_result.get("campos", {}) or {}
                row = {
                    "imagen": archivo,
                    "fecha": fecha_archivo,
                    "destinatario_raw": json_result.get("destinatario_raw").upper() if json_result.get("destinatario_raw") is not None else "null",
                    "observaciones_ia": json_result.get("observaciones_ia").upper() if json_result.get("observaciones_ia") is not None else "null",
                    "nombre_o_titulo": campos.get("nombre_o_titulo").upper() if campos.get("nombre_o_titulo") is not None else "null",
                    "cargo_dependencia": campos.get("cargo_dependencia").upper() if campos.get("cargo_dependencia") is not None else "null",
                    "direccion": campos.get("direccion").upper() if campos.get("direccion") is not None else "null",
                    "colonia": campos.get("colonia").upper() if campos.get("colonia") is not None else "null",
                    "municipio_o_alcaldia": campos.get("municipio_o_alcaldia").upper() if campos.get("municipio_o_alcaldia") is not None else "null",
                    "estado": campos.get("estado").upper() if campos.get("estado") is not None else "null",
                    "codigo_postal": campos.get("codigo_postal").upper() if campos.get("codigo_postal") is not None else "null",
                    "extras": campos.get("extras").upper() if campos.get("extras") is not None else "null",
                    "contacto": campos.get("contacto").upper() if campos.get("contacto") is not None else "null",
                    "indicaciones": campos.get("indicaciones").upper() if campos.get("indicaciones") is not None else "null",
                }

                # Asegurar orden y columnas faltantes
                for col in columns:
                    row.setdefault(col, None)

                rows.append(row)
        # Guardar Excel
        if rows:
            df = pd.DataFrame(rows, columns=columns)
            carpeta_salida = carpeta.parent # <- una carpeta antes de RECORTES
            ruta_excel = carpeta_salida / nombre_excel
            df.to_excel(ruta_excel, index=False)
            print(f"\nProceso terminado em carpeta: {carpeta}")
            print(f"Archivo generado: {nombre_excel}")

if __name__ == "__main__":
    try:
        main()
        input("\nPresione dos veces enter para salir: \n")
    except KeyboardInterrupt:
        input("\nProceso terminado por el usuario presione dos veces entes para salir: \n")
    except Exception as ex:
        print(ex)
        input("\nRevise la exepción y presione enter para salir: ")

