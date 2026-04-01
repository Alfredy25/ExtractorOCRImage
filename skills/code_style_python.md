# Skill: Estilo de código Python

## Principios

- **Python 3.11+**; tipado donde ayude (`list[str]`, `Optional[...]` según ya use el archivo).
- Imports: stdlib, terceros, locales (`app.*`) en bloques claros como en el archivo vecino.
- Nombres descriptivos en español o inglés **consistentes con el archivo** que se edita.

## Checklist

- [ ] ¿El cambio sigue el estilo del módulo (comillas, longitud de línea)?
- [ ] ¿Funciones nuevas con responsabilidad única?
- [ ] ¿Sin dead code ni prints de depuración olvidados?

## Do / Don’t

| Do | Don’t |
|----|--------|
| Pequeños refactors solo si desbloquean el objetivo | Reformatear archivos enteros sin pedido |
| Docstrings donde el módulo ya los usa | Comentarios que repiten el nombre de la función |

## Plantillas de prompts cortos

```
Estilo: match [archivo referencia]; cambio mínimo en [objetivo].
```

```
Refactor local en [función] — sin cambiar API pública.
```

## Referencias en el repo

- `app/main.py` — entrada
- `app/core/*.py` — estilo dominio
- `app/ui/*.py` — estilo Qt
