# Volante

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Volantes. Prefijo montado en `app/main.py`: `/volante`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en cada llamada.

No hay baja ni consulta por id. El nombre se guarda recortado y en mayúsculas. El alta y el PATCH exigen el nombre completo: 18 a 35 caracteres.

Si la página pedida se pasa del final y no supera 100, la respuesta trae la última página que sí existe. Con catálogo vacío: `page` 1, `total` 0, `total_pages` 0, `items` [].

## GET /volante/

### Descripción
Listar volantes paginados. `search` busca un fragmento del nombre.

### Request

Sin body.

Query:
- `search`: string, opcional, 3–50. Letras, dígitos y guion.
- `page`: int, default 1, 1–100
- `page_size`: int, default 50, 5–100
- `order_by`: `id` | `name`, default `id`
- `direction`: `desc` | `asc`, default `asc`

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| search | string | no | null | query. `QLineEdit`, máximo 50. Validador de letras, dígitos y `-`. |
| page | int | no | 1 | query. 1–100. |
| page_size | int | no | 50 | query. 5–100. |
| order_by | string | no | id | query. Combo `id` o `name`. |
| direction | string | no | asc | query. Combo `asc` o `desc`. |

### Validaciones
- `search` solo admite `A-Z`, `a-z`, dígitos y `-`. No admite espacios.
- El término se recorta y se pasa a mayúsculas. La búsqueda es un fragmento del nombre. `131000` encuentra `VCS-26-131000-00167`.
- `page` mayor que 100 responde 422. Una página que existe en el rango pero ya no tiene filas regresa la última página con datos.

### Respuesta
Status: 200 — `PaginatedVolantes`

La respuesta no devuelve `order_by` ni `direction`. `search` vuelve en mayúsculas, o `null` si no se envió.

```json
{
  "search": "131000",
  "page": 1,
  "page_size": 50,
  "total": 1,
  "total_pages": 1,
  "has_prev": false,
  "has_next": false,
  "items": [
    {
      "id": 1,
      "name": "VCS-26-131000-00167",
      "created_at": "2026-11-10T23:00:00Z",
      "updated_at": "2026-11-10T23:00:00Z",
      "created_by": 1,
      "updated_by": null
    }
  ]
}
```

La lista va en una tabla.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | query inválido | `{"errors": [{"message": "...", "field": "search", "type": "..."}]}` |

## POST /volante/

### Descripción
Crear volante. Status 201.

### Request

```json
{ "name": "VCS-26-131000-00167" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| name | string | sí | — | body. 18–35. `QLineEdit` con `setMaxLength(35)`. |

### Validaciones
- Largo 18–35. No hay patrón de caracteres en el alta: el guion y las letras se aceptan por el largo, no por una expresión.
- Se recorta y se guarda en mayúsculas. `vcs-26-131000-00167` queda `VCS-26-131000-00167`.
- El nombre no puede repetirse. La comparación es en mayúsculas.

### Respuesta
Status: 201 — `VolanteDto`

```json
{
  "id": 1,
  "name": "VCS-26-131000-00167",
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
| 409 | el nombre ya existe | `{"detail": "Volante ya existe"}` |
| 422 | body inválido | `{"errors": [{"message": "...", "field": "name", "type": "..."}]}` |

## PATCH /volante/{volante_id}

### Descripción
Actualizar el nombre de un volante. `name` es obligatorio en este body: no es un cambio parcial de claves opcionales.

### Request

Path:
- `volante_id`: int >= 1

```json
{ "name": "VCS-26-131000-00168" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| volante_id | int | sí | — | path. >= 1 |
| name | string | sí | — | body. 18–35. |

### Validaciones
- Mismas reglas de largo que el alta. Un cuerpo `{}` responde 422.
- El nombre se recorta y se guarda en mayúsculas.
- Si ese nombre ya pertenece a otro volante, 409. Conservar el nombre del propio volante no choca.

### Respuesta
Status: 200 — `VolanteDto`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | el volante no existe | `{"detail": "Volante no existe"}` |
| 409 | el nombre ya es de otro volante | `{"detail": "name de volante ya existe"}` |
| 422 | path o body inválido | `{"errors": [{"message": "...", "field": "name", "type": "..."}]}` |
