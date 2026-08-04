# Skill: Core OCR / pipeline

## Principios

- **OpenAI** para visión/OCR según `app/services/ocr_service.py` y `app/config/`.
- Respuestas validadas con Pydantic en `app/models/extraction.py` y `app/services/parsing_service.py`.
- Recorte e imagen: `app/utils/crop_tools.py`, `app/utils/image_io.py`.

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

- `app/services/ocr_service.py`, `app/services/parsing_service.py`
- `app/models/extraction.py`
- `app/utils/crop_tools.py`, `app/utils/image_io.py`
- `app/config/` — `OPENAI_*`, `AI_RETRY_COUNT`
- `extraccion_ocr.py` — referencia legacy por lotes
