---
name: Logistics Technical Suite
colors:
  background: '#10131b'
  surface: '#10131b'
  surface-dim: '#10131b'
  surface-bright: '#363941'
  surface-container-lowest: '#0a0e15'
  surface-container-low: '#181c23'
  surface-container: '#1c2027'
  surface-container-high: '#262a32'
  surface-container-highest: '#31353d'
  surface-variant: '#31353d'
  on-surface: '#e0e2ec'
  on-surface-variant: '#c0c6d6'
  inverse-surface: '#e0e2ec'
  inverse-on-surface: '#2d3038'
  outline: '#8a91a0'
  outline-variant: '#404754'
  primary: '#a9c7ff'
  on-primary: '#003063'
  primary-container: '#3a90ff'
  on-primary-container: '#002957'
  primary-fixed: '#d6e3ff'
  inverse-primary: '#005db6'
  primary-container-hover: '#5aa4ff'
  primary-container-pressed: '#2b7fe6'
  secondary: '#b0c6ff'
  on-secondary: '#002c6f'
  secondary-container: '#578cff'
  on-secondary-container: '#002662'
  secondary-container-hover: '#6f9dff'
  tertiary: '#ffb691'
  on-tertiary: '#552100'
  tertiary-container: '#eb6b13'
  on-tertiary-container: '#4a1c00'
  ocr-selection: '#69b4ff'
  ocr-selection-fill: '#0085ff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  error-container-hover: '#b3141f'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
  headline-md:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
  headline-sm:
    fontFamily: Inter
    fontSize: 17px
    fontWeight: '600'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    letterSpacing: 0.05em
rounded:
  control: 4px
  card: 8px
  pill: 12px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  sidebar: 280px
  inspector: 400px
  topbar: 68px
---

## Brand & Style

Sistema visual de la aplicación de escritorio para extraer destinatarios de etiquetas, armar envíos y consultar coberturas. El operador trabaja muchas horas sobre formularios densos y un visor de imagen, así que la interfaz privilegia lectura, estados claros y poco adorno.

La dirección es **técnica y logística**, en un solo modo oscuro:

- **Capas tonales.** La profundidad se lee por el tono de la superficie, no por sombras. El fondo es azul marino (`background`) y cada panel sube un escalón (`surface-container`, `surface-container-high`).
- **Acento azul contenido.** `primary` y `primary-container` marcan la acción principal, el foco y la selección. El naranja `tertiary` queda para avisos y datos que hay que mirar dos veces.
- **Datos distinguibles del texto.** Inter lleva la interfaz. JetBrains Mono lleva códigos postales, RFC, teléfonos, medidas y etiquetas de sección.
- **Iconos de sistema.** Los glifos son Material Symbols Outlined, empaquetados con la app. Si falta la fuente, el texto cae a Segoe UI y la monoespaciada a Consolas.

La implementación vive en `app/components/theme/`. Los widgets declaran intención (`variant`, `role`, `tone`) y la apariencia sale de la hoja de estilos. El estilo base de Qt es Fusion: el estilo nativo de Windows ignora parte de los bordes y los indicadores.

## Colors

Paleta de un solo tema oscuro. Un color nuevo se agrega en `tokens.py`; los widgets no incrustan hex sueltos.

- **Lienzo.** `background` y `surface` son el mismo azul marino (`#10131b`). `surface-container-lowest` es el pozo del visor de imagen, más oscuro que la ventana.
- **Paneles.** De abajo hacia arriba: `surface-container-low`, `surface-container`, `surface-container-high` y `surface-container-highest`. La barra lateral usa `surface-dim`; la barra superior usa `surface-container`.
- **Texto.** `on-surface` para contenido y títulos. `on-surface-variant` para subtítulos, metadatos y etiquetas de campo. Lo deshabilitado usa `outline`.
- **Bordes.** `outline-variant` separa regiones. `outline` es el borde en reposo de checks y el texto deshabilitado; en hover de botones secundarios el borde pasa a `outline`.
- **Primario.** `primary` (`#a9c7ff`) es texto de acento, enlaces y chips. `primary-container` (`#3a90ff`) es el relleno del botón principal, con texto `on-primary-container`. Hover `#5aa4ff`, pressed `#2b7fe6`.
- **Secundario.** `secondary-container` marca el ítem de navegación activo. El banner de éxito tiñe su borde y su fondo con ese mismo azul, al 55 % y al 10 %.
- **Terciario.** Naranja (`tertiary` `#ffb691`, contenedor `#eb6b13`) para avisos. El chip `warning` usa ese tono con fondo al 12 % y borde al 32 %.
- **OCR.** `ocr-selection` (`#69b4ff`) es el trazo del recorte. `ocr-selection-fill` (`#0085ff`) es el relleno, siempre al 10 % de opacidad.
- **Error.** Texto y bordes en `error` (`#ffb4ab`). El banner de error usa borde al 45 % y fondo al 10 %. El botón `danger` es transparente con borde al 40 % y, en hover, fondo al 12 %.

QSS no admite opacidad sobre hex. Los tintes se escriben con `rgba()` a partir de la clave de la paleta.

## Typography

Dos familias, cargadas desde `app/assets/fonts`:

- **Inter** para títulos, cuerpo, botones y campos. Es la fuente de la aplicación, a 14 px (`body-md`).
- **JetBrains Mono** para datos técnicos y para las etiquetas de sección y de campo. Las de sección van en mayúsculas.

Escala en píxeles, tal como la aplica Qt:

| Rol | Familia | Tamaño | Peso | Uso |
|-----|---------|--------|------|-----|
| `headline-lg` | Inter | 28 | 700 | Título de pantalla |
| `headline-md` | Inter | 22 | 600 | Título intermedio |
| `headline-sm` | Inter | 17 | 600 | Título de tarjeta. La marca de la barra lateral usa el mismo tamaño a 700 y en color `primary` |
| `body-lg` | Inter | 16 | 400 | Texto destacado, cabeceras de bloque |
| `body-md` | Inter | 14 | 400 | Cuerpo, campos, diálogos |
| `body-sm` | Inter | 13 | 400 | Subtítulos y texto de apoyo, en `on-surface-variant` |
| `label-md` | JetBrains Mono | 12 | 500 | Etiqueta de sección, en mayúsculas |
| `label-sm` | JetBrains Mono | 11 | 500 | Etiqueta de campo y chips |

Qt no tiene `letter-spacing` en la hoja de estilos. Las etiquetas de sección y los chips aplican un interletraje de `0.05em` por código. Los pesos de interfaz son 400 regular, 500 medium, 600 semibold y 700 bold. El botón secundario va a 500; el primario, a 600.

## Layout & Spacing

La ventana principal es de tres zonas: barra lateral fija, área de trabajo y panel inspector.

- **Barra lateral:** 280 px, fondo `surface-dim`, borde derecho de 1 px en `outline-variant`.
- **Barra superior:** 68 px de alto, fondo `surface-container`, borde inferior de 1 px.
- **Inspector:** 400 px de ancho inicial en el splitter, al lado del contenido.
- **Ritmo:** base de 4 px. Los huecos son 4, 8, 16, 24 y 32 (`xs` a `xl`). El padding habitual de un botón es 8×16; el de un campo, 6×8.
- **Densidad:** formularios y tablas apretados. Los separadores son líneas de 1 px (`outline-variant`, o `surface-variant` si el separador es suave), no bloques vacíos.

## Elevation & Depth

No hay sombras de elevación. Un panel se distingue del fondo porque su tono es más claro y porque lleva un borde de 1 px.

- **Nivel 0.** `background` en la ventana, los diálogos y el área de contenido. El `QWidget` genérico no pinta fondo: así una tarjeta se lee como tarjeta y no como un rectángulo plano encima de otro.
- **Nivel 1.** Tarjeta (`surface-container` + borde `outline-variant`, radio `card`). La cabecera de la tarjeta baja a `surface-container-low`.
- **Nivel 2.** Bloque de campos dentro de la tarjeta (`surface-container-low`, borde `outline-variant` al 60 %).
- **Flotante.** La barra de herramientas del visor usa `surface-container` al 94 % con borde `primary` al 35 % y radio de píldora. QSS no desenfoca el fondo, así que el panel es casi opaco.
- **Foco.** El campo enfocado cambia el borde a `primary-container`. El resalte de selección de texto usa el mismo contenedor, con texto `on-primary-container`.
- **Brillo puntual.** Cuando un control necesita halo, se aplica un `QGraphicsDropShadowEffect` sin desplazamiento, desenfoque de 18 px y `primary-container` con alfa 140. No es la sombra de una tarjeta.

El handle del splitter es transparente y, al pasar el cursor, se tiñe con `primary-container` al 25 %.

## Shapes

El lenguaje es de esquinas cortas. Nada es píldora salvo lo que es un control compacto o una barra flotante.

- **Controles:** radio de 4 px en botones, campos, chips, tablas, tooltips y casillas.
- **Tarjetas:** radio de 8 px en tarjetas, banners, grupos y la marca de la barra lateral. La cabecera solo redondea las esquinas superiores.
- **Píldoras:** radio de 12 px en la barra del visor y en los botones cuadrados de solo icono (32×32, o 30×30 si van en el visor).
- **Casillas y radios.** La casilla usa el radio de control (4 px). El radio del indicador circular es 10 px. Ambos miden 16 px, con borde de 2 px.
- **Recorte OCR.** Esquinas rectas. El rectángulo de selección no se redondea: el borde tiene que coincidir con el píxel del recorte.
- **Barras.** El progreso mide 6 px de alto con radio de 3 px. La barra de desplazamiento mide 10 px, con el pulgar a radio 5 px.

## Components

Los componentes no llevan hoja de estilos propia. Declaran `variant`, `role` o `tone`.

- **Botones.**
  - **Secundario (por defecto):** fondo `surface-container-high`, texto `on-surface`, borde `outline-variant`, padding 8×16, peso 500. En hover el fondo sube a `surface-variant` y el borde a `outline`.
  - **Primario** (`variant="primary"`): fondo y borde `primary-container`, texto `on-primary-container`, peso 600.
  - **Ghost:** fondo transparente, texto `on-surface-variant`, borde `outline-variant`. En hover, fondo `surface-variant` y texto `on-surface`.
  - **Peligro:** fondo transparente, texto `error`, borde `error` al 40 %.
  - **Enlace:** sin borde ni fondo, texto `primary`. En hover pasa a `primary-fixed`.
  - **Navegación:** transparente, texto a la izquierda. El ítem marcado usa fondo `secondary-container` y texto `on-secondary-container`. La salida lleva `tone="danger"`.
  - **Solo icono:** 32×32, transparente, radio de píldora. No se le fija tamaño de fuente en la hoja de estilos, para no deformar el glifo.
- **Campos.** Fondo `surface-dim`, borde `outline-variant`, radio 4 px, texto Inter a 14 px. Al foco, el borde pasa a `primary-container`. Si el valor es inválido, el borde es `error`. CP, RFC y teléfonos usan `role="mono"` (JetBrains Mono a 13 px).
- **Tarjetas.** `Card` con cabecera opcional (icono + título). El icono de cabecera va en `primary-container`. Dentro, `SectionBox` agrupa campos un tono por debajo de la tarjeta.
- **Banners.** Misma base que la tarjeta. `tone="success"` tiñe con `secondary-container`; `tone="error"`, con `error`.
- **Chips.** Monoespaciada a 11 px, padding 3×8, radio 4 px. El tono primario usa texto `primary`, fondo al 10 % y borde al 24 %. `neutral` es superficie alta con borde `outline-variant`. `warning` usa `tertiary`.
- **Etiquetas de sección.** JetBrains Mono a 12 px, mayúsculas, color `on-surface-variant`, interletraje `0.05em`.
- **Casillas.** Indicador de 16 px sobre `surface-dim`, borde `outline`. Marcada: fondo y borde `primary-container`. En hover el borde pasa a `primary`.
- **Visor.** Lienzo `surface-container-lowest` con borde `outline-variant`. Encima, la barra flotante en píldora. El recorte (`QRubberBand`) lleva relleno `ocr-selection-fill` al 10 % y trazo de 1 px en `ocr-selection`, con esquinas rectas.
- **Tablas.** Fondo `surface-container`, borde `outline-variant`, radio 4 px. La cabecera de columna va en monoespaciada, 11 px, peso 700.
- **Progreso.** Canal `surface-container-high` de 6 px; el avance es `primary-container`.
- **Desplazamiento.** Canal transparente. Pulgar `outline-variant`, radio 5 px; en hover, `outline`.
- **Tooltips.** Fondo `surface-container-highest`, borde `outline-variant`, radio 4 px, padding 4×8.
