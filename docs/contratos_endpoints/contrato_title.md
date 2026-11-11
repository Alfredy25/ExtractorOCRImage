# Title

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Títulos. Prefijo montado en `app/main.py`: `/titles`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en cada llamada.

No hay baja. El alta guarda `abbreviation` y `meaning` tal como llegan, sin pasarlos a mayúsculas ni a título. El PATCH solo cambia las claves enviadas.

Si la página pedida se pasa del final, la respuesta trae la última página que sí existe. Con catálogo vacío: `page` 1, `total` 0, `total_pages` 0, `items` [].

## GET /titles/

### Descripción
Listar títulos paginados. Busca por abreviatura o significado.

### Request

Sin body.

Query:
- `search`: string, opcional. Mínimo 2 caracteres, y al menos 3 útiles después de recortar espacios. Letras, números, punto y espacio. Sin tope de 60: el router declara `maxlength`, y ese nombre no limita la cadena.
- `page`: int, default 1, >= 1
- `page_size`: int, default 50, 5–80
- `order_by`: `id` | `abbrev` | `meaning`, default `id`
- `direction`: `desc` | `asc`, default `asc`

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| search | string | no | null | query. `QLineEdit`. |
| page | int | no | 1 | query. `QSpinBox` mínimo 1. |
| page_size | int | no | 50 | query. 5–80. |
| order_by | string | no | id | query. Combo `id`, `abbrev`, `meaning`. El valor es `abbrev`, no `abbreviation`. |
| direction | string | no | asc | query. Combo `asc` o `desc`. |

### Validaciones
- `search` admite `a-z`, `A-Z`, dígitos, `áéíóúÁÉÍÓÚ`, punto y espacio. No admite `ñ` ni `ü`.
- Se recortan los espacios de los extremos. Si después quedan menos de 3 caracteres, 422 con mensaje `Search debe tener al menos 3 caracteres`.
- La búsqueda es un fragmento. El término se pasa a mayúsculas. La abreviatura se compara tal como está guardada; el significado se compara en mayúsculas. `abg` encuentra un significado que contenga `ABG`. Una abreviatura guardada como `Abg.` no coincide con el término `ABG`.
- `order_by` y `direction` solo aceptan los valores de arriba.

### Respuesta
Status: 200 — `PaginatedTitles`

```json
{
  "page": 1,
  "page_size": 50,
  "total": 1,
  "total_pages": 1,
  "has_prev": false,
  "has_next": false,
  "order_by": "id",
  "direction": "asc",
  "search": "Doctor",
  "items": [
    {
      "id": 1,
      "abbreviation": "DR.",
      "meaning": "Doctor",
      "created_at": "2026-11-10T23:00:00Z",
      "updated_at": "2026-11-10T23:00:00Z",
      "created_by": 1,
      "updated_by": null
    }
  ]
}
```

`search` en la respuesta es el texto ya recortado, con las mayúsculas que envió el cliente. La lista va en una tabla.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | query inválido | `{"errors": [{"message": "...", "field": "search", "type": "..."}]}` |

## POST /titles/

### Descripción
Crear título. Status 201.

### Request

```json
{ "abbreviation": "DR.", "meaning": "Doctor" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| abbreviation | string | sí | — | body. `QLineEdit`, máximo 60. |
| meaning | string | sí | — | body. `QLineEdit`, máximo 150. |

### Validaciones
- `abbreviation`: 3–60 caracteres.
- `meaning`: 3–150 caracteres.
- No hay patrón ni cambio de mayúsculas. Lo que se envía es lo que se guarda.
- La abreviatura no puede repetirse. La comparación usa la abreviatura enviada en mayúsculas contra la abreviatura guardada. `Dr.` choca con un registro cuyo texto guardado sea `DR.`. No choca con uno guardado como `Dr.`.

### Respuesta
Status: 201 — `TitleDto` con `id`, `abbreviation`, `meaning`, `created_at`, `updated_at`, `created_by`, `updated_by`.

```json
{
  "id": 1,
  "abbreviation": "DR.",
  "meaning": "Doctor",
  "created_at": "2026-11-10T23:00:00Z",
  "updated_at": "2026-11-10T23:00:00Z",
  "created_by": 1,
  "updated_by": null
}
```

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 409 | la abreviatura ya existe | `{"detail": "El titulo ya existe"}` |
| 422 | body inválido | `{"errors": [{"message": "...", "field": "abbreviation", "type": "..."}]}` |

## PATCH /titles/{title_id}

### Descripción
Actualizar un título. Solo cambian las claves enviadas. Un cuerpo `{}` responde 200 con el título actual.

### Request

Path:
- `title_id`: int. No hay mínimo declarado en la ruta.

```json
{ "meaning": "Doctora" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| title_id | int | sí | — | path |
| abbreviation | string | no | se omite | body. Máximo 60. Sin mínimo. |
| meaning | string | no | se omite | body. Máximo 150. Sin mínimo. |

### Validaciones
- Omite la clave que no quieras cambiar.
- El schema acepta `null`. Las columnas no aceptan nulo: no uses `null` para borrar. Omite la clave.
- Este PATCH no revisa si la abreviatura ya pertenece a otro título. La columna es única; repetirla falla al guardar.
- El texto se guarda tal como se envía.

### Respuesta
Status: 200 — `TitleDto`, la misma forma que el alta.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | no hay título con ese id | `{"detail": "Titulo con id 9 no existe"}` |
| 422 | path o body inválido | `{"errors": [{"message": "...", "field": "title_id", "type": "..."}]}` |
