"""Cliente OpenAI para extracción de campos del destinatario."""
import base64
import io
import logging
import time

import cv2
import numpy as np
from openai import OpenAI

from app.config import AI_RETRY_COUNT, OPENAI_API_KEY, OPENAI_MODEL, TIMEOUT_SECONDS
from app.core.models import ExtraccionDestinatario
from app.core.parsing import parse_extraccion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres un asistente especializado en leer la etiqueta blanca del DESTINATARIO en sobres enviados en México.
Tu tarea es extraer el contenido del destinatario y devolver EXCLUSIVAMENTE un JSON VÁLIDO que cumpla el esquema indicado.
Reglas ESENCIALES:
- Fidelidad: copia el texto tal cual aparece (mayúsculas, acentos, signos, saltos de línea).
- No inventes ni completes datos. No uses conocimiento externo.
- Si un dato NO existe en la etiqueta, usa "" (cadena vacía).
- Si un dato es ilegible/borroso, usa "ilegible".
- No corrijas ortografía ni expandas acrónimos; sólo remueve artefactos OCR evidentes (espacios dobles).
- No agregues comentarios, markdown ni texto fuera del JSON.
- La salida debe comenzar con '{' y terminar con '}'.
Contexto operativo:
- Imágenes: recortes de la zona del destinatario; otras zonas del sobre NO deben considerarse.
- País: México.
- Devuelve claves exactamente como se especifican y en español.
"""

USER_PROMPT_TEMPLATE = '''
Instrucciones de extracción:

1) Analiza ÚNICAMENTE la etiqueta blanca del DESTINATARIO en la imagen adjunta.
2) Devuelve EXACTAMENTE este JSON (sin código, sin ``` y sin la palabra json):

{{
  "destinatario_raw": "",
  "campos": {{
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
  }},
  "observaciones_ia": ""
}}

Definiciones y criterios:
- "destinatario_raw": TODO el texto del destinatario tal cual aparece en la etiqueta, respetando saltos de línea. Incluye: nombre/título, cargo/dependencia, calle y número, colonia, municipio o alcaldía, estado, código postal, teléfonos, horarios, referencias, "con copia al", "asunto", etc. (si están visibles en la etiqueta del destinatario).
- "direccion": SOLO calle y número (y piso/interior/torre si se menciona). No incluyas colonia aquí.
- "colonia": nombre de la colonia o barrio, si aparece.
- "municipio_o_alcaldia": el municipio o la alcaldía.
- "estado": tal como aparezca (puede ser abreviado).
- "codigo_postal": tal como aparezca (no inventar).
- "extras": usa para "ASUNTO", "CON COPIA AL", "OFICIO", "CONTENIDO" u otros campos que no encajan en categorías anteriores, siempre que estén en la etiqueta del destinatario.
- "contacto": teléfonos, extensiones u otros medios de contacto visibles.
- "indicaciones": referencias, entre calles, horarios, instrucciones de acceso, puntos de referencia, etc., si aparecen en la etiqueta.
- Si un campo NO aparece en el texto visible, usa "" (cadena vacía).
- Si un campo aparece pero es ilegible, usa "ilegible".
- No reordenes ni reinterpretes: respeta el texto.

Contexto adicional:
- SEDE seleccionada: "{SEDE}".
  * Este dato es SOLO contexto; no lo infieras en los campos ni lo agregues al JSON si no aparece en la etiqueta.

Calidad:
- Si hay partes cortadas, reflejos, inclinación, baja resolución o números dudosos, descríbelos en "observaciones_ia".
- Si todo es legible, escribe: "Sin observaciones."

Responde EXCLUSIVAMENTE con el JSON válido.
'''


def _image_to_data_url(image_np: np.ndarray) -> str:
    """Convierte imagen numpy a data URL PNG/JPEG base64."""
    is_success, buf = cv2.imencode(".png", image_np)
    if not is_success:
        is_success, buf = cv2.imencode(".jpg", image_np)
        mime = "image/jpeg"
    else:
        mime = "image/png"
    if not is_success:
        raise ValueError("No se pudo codificar la imagen")
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def extract_fields(image_np: np.ndarray, sede: str) -> dict:
    """
    Envía el recorte a OpenAI y devuelve el dict de extracción.
    Con reintentos y fallback si el JSON es inválido.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)
    data_url = _image_to_data_url(image_np)
    user_content = USER_PROMPT_TEMPLATE.format(SEDE=sede.strip().upper())

    last_error = None
    for attempt in range(AI_RETRY_COUNT + 1):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_content},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                max_tokens=1200,
                timeout=TIMEOUT_SECONDS,
            )
            raw = response.choices[0].message.content
            parsed = parse_extraccion(raw)
            return parsed.model_dump()
        except Exception as e:
            last_error = e
            logger.warning("Intento %d falló: %s", attempt + 1, e)
            if attempt < AI_RETRY_COUNT:
                time.sleep(2 ** attempt)
            continue

    logger.error("Todos los reintentos fallaron: %s", last_error)
    fallback = {
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
            "indicaciones": "",
        },
        "observaciones_ia": "No se obtuvo JSON válido del modelo."
        + (f" Error: {last_error}" if last_error else ""),
    }
    return fallback
