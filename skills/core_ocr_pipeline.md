# Skill: Core OCR / pipeline

## Principios

- **OpenAI** para visión/OCR según `app/core/ai_client.py` y configuración en `app/config.py` (`OPENAI_MODEL`, `TIMEOUT_SECONDS`, `AI_RETRY_COUNT`).
- Respuestas validadas con Pydantic donde exista (`app/core/models.py`, `parsing.py`).
- Recorte e imagen: `crop_tools.py`, `image_io.py` — sin mezclar Qt salvo frontera acordada.

## Checklist

- [ ] ¿Clave API solo vía `python-dotenv` / `os.environ`, nunca hardcode?
- [ ] ¿Reintentos y timeouts alineados con `config.py`?
- [ ] ¿Parsing tolerante pero con errores explícitos hacia la integración/UI?

## Do / Don’t

| Do | Don’t |
|----|--------|
| Mantener prompts y esquema JSON en un solo lugar coherente | Loguear contenido de imágenes o respuestas completas en producción |
| Tests en `tests/unit/test_parsing.py` etc. | Llamadas reales a API en unit tests sin mock |

## Plantillas de prompts cortos

```
Core: ajustar prompt/parsing en [archivo] — mantener modelos Pydantic; pytest test_parsing.
```

```
ai_client: timeout/retry — solo config + ai_client; revisar security_privacy.
```

## Referencias en el repo

- `app/core/ai_client.py`
- `app/core/parsing.py`
- `app/core/models.py`
- `app/core/crop_tools.py`, `app/core/image_io.py`
- `app/config.py` — `OPENAI_*`, `AI_RETRY_COUNT`
- `extraccion_ocr.py` — referencia legacy por lotes
