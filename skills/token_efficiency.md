# Skill: Eficiencia de tokens (agentes)

## Principios

- **Contexto mínimo**: indicar carpeta o archivo + objetivo en una frase.
- **Skills por nombre**: p. ej. “Aplicar: token_efficiency, ui_pyside6” en lugar de pegar reglas largas.
- **Checklists** antes de párrafos; el agente expande solo lo necesario.

## Checklist

- [ ] ¿El prompt nombra el subagente (`agents/*.agent.md`) si la tarea es grande?
- [ ] ¿Se listan solo archivos a modificar, no el contenido entero?
- [ ] ¿Resultado pedido como diff o lista de cambios, no reescritura del repo?

## Do / Don’t

| Do | Don’t |
|----|--------|
| “Objetivo + archivos + skill” | Pegar README completo en cada mensaje |
| Pedir plan en 5 viñetas antes del código | Pedir “explica todo el proyecto” salvo onboarding |

## Plantillas de prompts cortos

```
Agente: [ui|core|integration|data] — objetivo: [1 línea]. Archivos: [a,b]. Skills: [x,y].
```

```
Solo diff en [archivo]; no tocar [lista excluida]. DoD: pytest + smoke manual.
```

## Referencias en el repo

- `AGENTS.md` — mapa de agentes y skills
- `agents/*.agent.md` — prompts recomendados por rol
