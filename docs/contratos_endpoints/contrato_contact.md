# Contact

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Contactos telefónicos. Prefijo montado en `app/main.py`: `/contacts`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en cada llamada.

No hay baja. El alta cuelga el contacto de un destinatario que ya existe: `POST /contacts/{receiver_id}`. El PATCH usa el id del contacto. En la respuesta el destinatario se llama `id_destinatario`.

Si la página pedida se pasa del final, la respuesta trae la última página que sí existe. Sin resultados: `page` 1, `total` 0, `total_pages` 0, `items` [].

## GET /contacts/

### Descripción
Listar contactos paginados. `search` busca un fragmento del teléfono.

### Request

Sin body.

Query:
- `search`: string, opcional, 2–10. Al menos 2 caracteres después de recortar espacios.
- `page`: int, default 1, >= 1
- `page_size`: int, default 10, 3–50
- `order_by`: `id` | `phone`, default `id`
- `direction`: `desc` | `asc`, default `asc`

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| search | string | no | null | query. `QLineEdit`, máximo 10. |
| page | int | no | 1 | query |
| page_size | int | no | 10 | query. 3–50. |
| order_by | string | no | id | query. Combo `id` o `phone`. |
| direction | string | no | asc | query. Combo `asc` o `desc`. |

### Validaciones
- `search` se recorta. Si queda con menos de 2 caracteres, 422 con mensaje `Search debe tener al menos 2 caracteres`.
- No exige solo dígitos. El filtro es un fragmento del teléfono guardado, sin pasar a mayúsculas. `8444` encuentra `8444160470`.

### Respuesta
Status: 200 — `PaginatedContacts`

```json
{
  "page": 1,
  "page_size": 10,
  "total": 1,
  "total_pages": 1,
  "has_prev": false,
  "has_next": false,
  "order_by": "id",
  "direction": "asc",
  "search": "8444",
  "items": [
    {
      "id": 1,
      "phone": "8444160470",
      "ext": "12",
      "id_destinatario": 4,
      "created_at": "2026-11-10T23:00:00Z",
      "updated_at": "2026-11-10T23:00:00Z",
      "created_by": 1,
      "updated_by": null
    }
  ]
}
```

`ext` puede venir `null`. La lista va en una tabla.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | query inválido | `{"errors": [{"message": "...", "field": "search", "type": "..."}]}` |

## POST /contacts/{receiver_id}

### Descripción
Crear un contacto para un destinatario que ya existe. Status 201.

### Request

Path:
- `receiver_id`: int >= 1

```json
{ "phone": "8444160470", "ext": "12" }
```

`ext` se puede omitir.

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| receiver_id | int | sí | — | path. >= 1 |
| phone | string | sí | — | body. 8–10 dígitos. `QLineEdit` con validador numérico y `setMaxLength(10)`. |
| ext | string | no | null | body. Hasta 5 dígitos. `QLineEdit` con `setMaxLength(5)`. |

### Validaciones
- Se recortan espacios. Un `ext` vacío o solo espacios se guarda como `null`.
- `phone` y `ext` solo aceptan dígitos. `phone` no admite `null`.
- El mismo destinatario no puede repetir la pareja teléfono + extensión. Sin extensión, la pareja es el teléfono y extensión vacía.

### Respuesta
Status: 201 — `ContactDto`. Misma forma que un elemento de `items`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | el destinatario no existe | `{"detail": "Destinatario con id 4 no existe"}` |
| 409 | ya tiene ese teléfono y esa extensión | `{"detail": "El destinatario ya tiene un contacto con ese teléfono y extensión"}` |
| 422 | path o body inválido | `{"errors": [{"message": "...", "field": "phone", "type": "..."}]}` |

## PATCH /contacts/{contact_id}

### Descripción
Actualizar un contacto. Solo cambian las claves enviadas. Un cuerpo `{}` responde 200 con el contacto actual.

### Request

Path:
- `contact_id`: int >= 1

```json
{ "ext": "15" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| contact_id | int | sí | — | path. >= 1 |
| phone | string | no | se omite | body. 8–10 si se envía. |
| ext | string | no | se omite | body. Máximo 5. `null` o `""` borra la extensión. |

### Validaciones
- Omite lo que no cambia.
- `phone` en `null` responde 422 con mensaje `El teléfono no puede ser nulo`.
- En el PATCH, `phone` y `ext` no exigen el patrón de solo dígitos. `phone` sí exige 8–10 caracteres después de recortar. `ext` exige como máximo 5.
- `ext` vacío se guarda `null`.
- La pareja teléfono + extensión no puede quedar igual a la de otro contacto del mismo destinatario.

### Respuesta
Status: 200 — `ContactDto`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | el contacto no existe | `{"detail": "Contacto con id 9 no existe"}` |
| 409 | otro contacto del mismo destinatario ya tiene ese teléfono y esa extensión | `{"detail": "El destinatario ya tiene un contacto con ese teléfono y extensión"}` |
| 422 | path o body inválido, o teléfono nulo | `{"errors": [{"message": "El teléfono no puede ser nulo", "field": "phone", "type": "..."}]}` |
