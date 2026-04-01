# Skill: Seguridad y privacidad

## Principios

- **API keys** solo vía variables de entorno (ver `python-dotenv` en `app/config.py`); archivo `.env` local y no versionado.
- No registrar en logs: claves, tokens, contenido completo de respuestas IA con datos personales.
- Rutas de usuario y exports: validar permisos y evitar path traversal donde haya entrada externa.

## Checklist

- [ ] ¿Nuevo log evita PII y secretos?
- [ ] ¿Errores mostrados al usuario sin stack interno en producción?
- [ ] ¿Exports solo donde indique `EXPORT_DIR` / flujo de export?

## Do / Don’t

| Do | Don’t |
|----|--------|
| Usar `OPENAI_API_KEY` desde env | Pegar claves en issues, commits o capturas |
| Mensajes de error genéricos en UI | `print(api_key)` en cualquier lado |

## Plantillas de prompts cortos

```
Security pass: [archivo] — revisar logs y excepciones; sin secretos; lista hallazgos.
```

```
.env: documentar variables requeridas; nunca subir valores reales.
```

## Referencias en el repo

- `app/config.py` — `OPENAI_API_KEY`, rutas
- `app/core/ai_client.py` — llamadas API
- `app/core/exporters.py` — escritura de archivos
