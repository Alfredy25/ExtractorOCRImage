# Skill: UI PySide6

## Principios

- Un hilo GUI: **no** bloquear con red, disco pesado o CPU larga.
- Preferir señales/slots y métodos pequeños; lógica pesada en `app/services/`.
- Temas y colores centralizados en `app/components/theme_manager.py`.

## Checklist

- [ ] ¿Operaciones largas van a worker/hilo con señal de resultado?
- [ ] ¿Widgets con padre correcto para ciclo de vida?
- [ ] ¿Cierre de diálogos y `exec()` usados solo donde corresponde?

## Do / Don’t

| Do | Don’t |
|----|--------|
| Conectar UI a funciones de `app/services/` | SQL o `openai` directo en widgets |
| Reutilizar estilos de `themes.py` | Copiar bloques enormes de CSS/Qt StyleSheet sin necesidad |
| Probar flujo manualmente tras cambios visibles | Cambiar contratos de datos sin coordinar |

## Plantillas de prompts cortos

```
PySide6: [archivo] — [cambio UI]. Sin tocar repository/ai_client.
```

```
MainWindow: nueva acción [menú] → llama [método core]; no bloquear GUI.
```

## Referencias en el repo

- `app/views/main_window.py` — shell principal
- `app/components/theme_manager.py` — tema claro/oscuro
- `app/components/image_viewer.py` — visor/zoom
- `app/components/panels/` — paneles laterales
