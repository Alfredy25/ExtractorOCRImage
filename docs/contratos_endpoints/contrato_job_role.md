# JobRole

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Cargos. Prefijo montado en `app/main.py`: `/job-roles`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en cada llamada.

No hay baja. La abreviatura se guarda en mayúsculas. El significado se guarda con la primera letra de cada palabra en mayúscula: `director general` queda `Director General`.

Si la página pedida se pasa del final, la respuesta trae la última página que sí existe. Con catálogo vacío: `page` 1, `total` 0, `total_pages` 0, `items` [].

## GET /job-roles/

### Descripción
Listar cargos paginados. Busca por abreviatura o significado.

### Request

Sin body.

Query:
- `search`: string, opcional, 3–60. Letras, números, punto y espacio, incluyendo `ñ` y `ü`. Al menos 3 caracteres después de recortar espacios.
- `page`: int, default 1, >= 1
- `page_size`: int, default 50, 5–80
- `order_by`: `id` | `abbreviation` | `meaning`, default `id`
- `direction`: `desc` | `asc`, default `asc`

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| search | string | no | null | query. `QLineEdit`, máximo 60. |
| page | int | no | 1 | query |
| page_size | int | no | 50 | query. 5–80. |
| order_by | string | no | id | query. Combo `id`, `abbreviation`, `meaning`. |
| direction | string | no | asc | query. Combo `asc` o `desc`. |

### Validaciones
- Patrón de `search`: letras (con acentos, `ñ` y `ü`), dígitos, punto y espacio.
- Se recortan los extremos. Menos de 3 caracteres útiles: 422 con mensaje `Search debe tener al menos 3 caracteres`.
- La búsqueda es un fragmento. El término y las dos columnas se comparan en mayúsculas. `dir` encuentra `DIR.` y `Director`.

### Respuesta
Status: 200 — `PaginatedJobs`

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
  "search": "director",
  "items": [
    {
      "id": 1,
      "abbreviation": "DIR.",
      "meaning": "Director",
      "created_at": "2026-11-10T23:00:00Z",
      "updated_at": "2026-11-10T23:00:00Z",
      "created_by": 1,
      "updated_by": null
    }
  ]
}
```

`search` en la respuesta es el texto recortado, con las mayúsculas del cliente. La lista va en una tabla.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | query inválido | `{"errors": [{"message": "...", "field": "search", "type": "..."}]}` |

## GET /job-roles/{job_id}

### Descripción
Obtener un cargo por id.

### Request

Sin body.

Path:
- `job_id`: int. La ruta no declara un mínimo.

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| job_id | int | sí | — | path |

### Validaciones
- `job_id` tiene que ser un entero. Un texto en el path responde 422.

### Respuesta
Status: 200 — `JobDto`

```json
{
  "id": 1,
  "abbreviation": "DIR.",
  "meaning": "Director",
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
| 422 | `job_id` no es un entero | `{"errors": [{"message": "...", "field": "job_id", "type": "..."}]}` |

Un id que no existe no está traducido a 404.

## POST /job-roles/

### Descripción
Crear cargo. Status 201.

### Request

```json
{ "abbreviation": "dir.", "meaning": "director" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| abbreviation | string | sí | — | body. 2–60. `QLineEdit` con `setMaxLength(60)`. |
| meaning | string | sí | — | body. 3–150. `QLineEdit` con `setMaxLength(150)`. |

### Validaciones
- `abbreviation`: letras (incluida `ñ`), punto y espacio. Sin dígitos y sin acentos. Se guarda en mayúsculas. `dir.` queda `DIR.`.
- `meaning`: letras con acentos, `ñ` y espacio. Sin dígitos y sin punto. Se guarda en forma de título. `director general` queda `Director General`.
- La abreviatura no puede repetirse. La comparación es en mayúsculas.

### Respuesta
Status: 201 — `JobDto` con el texto ya normalizado.

```json
{
  "id": 1,
  "abbreviation": "DIR.",
  "meaning": "Director",
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
| 409 | la abreviatura ya existe | `{"detail": "El cargo ya existe"}` |
| 422 | body inválido | `{"errors": [{"message": "...", "field": "abbreviation", "type": "..."}]}` |

## PATCH /job-roles/{job_id}

### Descripción
Actualizar un cargo. Solo cambian las claves enviadas. Un cuerpo `{}` responde 200 con el cargo actual.

### Request

Path:
- `job_id`: int >= 1

```json
{ "meaning": "director general" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| job_id | int | sí | — | path. >= 1 |
| abbreviation | string | no | se omite | body. 2–60 y el mismo patrón del alta, si se envía. |
| meaning | string | no | se omite | body. 3–150 y el mismo patrón del alta, si se envía. |

### Validaciones
- Omite la clave que no cambia.
- `null` no borra. Si envías `abbreviation: null`, 422 con mensaje `La abreviatura no puede ser nula`. Si envías `meaning: null`, 422 con mensaje `El significado no puede ser nulo`.
- La abreviatura enviada se pasa a mayúsculas y el significado a forma de título, igual que en el alta.
- Si la abreviatura nueva ya pertenece a otro cargo, 409. Conservar la misma abreviatura del propio cargo no choca.

### Respuesta
Status: 200 — `JobDto`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | el cargo no existe | `{"detail": "Cargo con id 9 no existe"}` |
| 409 | la abreviatura ya es de otro cargo | `{"detail": "El cargo ya existe"}` |
| 422 | path o body inválido, o un campo en null | `{"errors": [{"message": "La abreviatura no puede ser nula", "field": "abbreviation", "type": "..."}]}` |
