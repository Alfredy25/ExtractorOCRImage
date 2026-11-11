# Organization

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Organizaciones. Prefijo montado en `app/main.py`: `/organizations`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en cada llamada.

No hay baja. El nombre se guarda en mayúsculas, con abreviaturas de palabras completas y sin algunos signos. El estado se guarda con el valor del catálogo, sin acentos. Una organización se identifica por nombre + estado: el mismo nombre puede existir en otro estado.

Si la página pedida se pasa del final, la respuesta trae la última página que sí existe. Con catálogo vacío: `page` 1, `total` 0, `total_pages` 0, `items` [].

## GET /organizations/

### Descripción
Listar organizaciones paginadas. `search` busca un fragmento del nombre. `state` filtra por igualdad.

### Request

Sin body.

Query:
- `search`: string, opcional, 3–180. Letras, números, punto y espacio, incluyendo `ñ` y `ü`. Al menos 3 caracteres después de recortar espacios.
- `state`: string, opcional. Un estado del catálogo. `tabasco` y `TABASCO` valen.
- `page`: int, default 1, >= 1
- `page_size`: int, default 50, 5–80
- `order_by`: `id` | `name` | `state`, default `id`
- `direction`: `desc` | `asc`, default `asc`

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| search | string | no | null | query. `QLineEdit`, máximo 180. |
| state | string | no | null | query. `QComboBox` con los estados. |
| page | int | no | 1 | query |
| page_size | int | no | 50 | query. 5–80. |
| order_by | string | no | id | query. Combo `id`, `name`, `state`. |
| direction | string | no | asc | query. Combo `asc` o `desc`. |

### Validaciones
- `search` se recorta. Menos de 3 caracteres útiles: 422 con mensaje `Search debe tener al menos 3 caracteres`.
- El fragmento se compara en mayúsculas contra el nombre.
- `state` tiene que ser uno de estos valores:

`AGUASCALIENTES`, `BAJA CALIFORNIA`, `BAJA CALIFORNIA SUR`, `CAMPECHE`, `CHIAPAS`, `CHIHUAHUA`, `CIUDAD DE MEXICO`, `COAHUILA`, `COLIMA`, `DURANGO`, `ESTADO DE MEXICO`, `GUANAJUATO`, `GUERRERO`, `HIDALGO`, `JALISCO`, `MICHOACAN`, `MORELOS`, `NAYARIT`, `NUEVO LEON`, `OAXACA`, `PUEBLA`, `QUERETARO`, `QUINTANA ROO`, `SAN LUIS POTOSI`, `SINALOA`, `SONORA`, `TABASCO`, `TAMAULIPAS`, `TLAXCALA`, `VERACRUZ`, `YUCATAN`, `ZACATECAS`.

### Respuesta
Status: 200 — `PaginatedOrganizations`

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
  "search": "Congreso",
  "state": "TABASCO",
  "items": [
    {
      "id": 1,
      "name": "CONGRESO DEL ESTADO DE TABASCO",
      "state": "TABASCO",
      "created_at": "2026-11-10T23:00:00Z",
      "updated_at": "2026-11-10T23:00:00Z",
      "created_by": 1,
      "updated_by": null
    }
  ]
}
```

`search` en la respuesta conserva las mayúsculas del cliente, ya recortado. `state` sale `null` si no se filtró. La lista va en una tabla.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | query inválido | `{"errors": [{"message": "...", "field": "search", "type": "..."}]}` |

## POST /organizations/

### Descripción
Crear organización. Status 201.

### Request

```json
{
  "name": "Universidad Autonoma de Tabasco",
  "state": "Tabasco"
}
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| name | string | sí | — | body. 3–180, medidos después de normalizar. `QLineEdit` con `setMaxLength(180)`. |
| state | string | sí | — | body. Combo de estados. |

### Validaciones
- El nombre se recorta, se pasa a mayúsculas y luego se abrevian estas frases o palabras completas:

| Texto ya en mayúsculas | Queda |
|------------------------|-------|
| SECRETARIA DE ADMINISTRACION TRIBUTARIA | S.A.T. |
| SECRETARIA DE CONTRALORIA GENERAL | S.C.E. |
| CONTRALORIA GENERAL DEL ESTADO | C.G.E. |
| ORGANO INTERNO DE CONTROL | O.I.C. |
| ORGANO DE CONTROL INTERNO | O.I.C. |
| UNIVERSIDAD | UNI. |
| AUTONOMA | AUT. |
| BAJA CALIFORNIA SUR | B.C.S. |
| SAN LUIS POTOSI | S.L.P. |

- Los acentos no se quitan antes de abreviar. `AUTÓNOMA` no coincide con `AUTONOMA` y se guarda `AUTÓNOMA`. `Universidad Autonoma` sí queda `UNI. AUT.`.
- En el nombre se borran `\ : [ ] # ° " , ! ¿ ¡ “ ”`. El guion `-` pasa a espacio.
- `state` usa el catálogo del GET. `Yucatán` queda `YUCATAN`.
- No puede repetirse la pareja nombre + estado. El mismo nombre en otro estado sí se puede crear.

### Respuesta
Status: 201 — `OrganizationDto`

```json
{
  "id": 2,
  "name": "UNI. AUT. DE TABASCO",
  "state": "TABASCO",
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
| 409 | ya existe ese nombre en ese estado | `{"detail": "La organización ya existe"}` |
| 422 | body inválido | `{"errors": [{"message": "...", "field": "name", "type": "..."}]}` |

## PATCH /organizations/{organization_id}

### Descripción
Actualizar una organización. Solo cambian las claves enviadas. Un cuerpo `{}` responde 200 con la organización actual.

### Request

Path:
- `organization_id`: int >= 1

```json
{ "name": "Congreso del Estado de Tabasco" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| organization_id | int | sí | — | path. >= 1 |
| name | string | no | se omite | body. 3–180 si se envía. Misma normalización del alta. |
| state | string | no | se omite | body. Mismo catálogo. |

### Validaciones
- Omite lo que no cambia.
- `name: null` responde 422 con mensaje `El nombre no puede ser nulo`.
- `state: null` responde 422 con mensaje `El estado no puede ser nulo`.
- El nombre enviado pasa por las mismas abreviaturas y la limpieza de signos del alta.
- La pareja nombre + estado resultante no puede ser la de otra organización. Conservar la pareja propia no choca.

### Respuesta
Status: 200 — `OrganizationDto`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | la organización no existe | `{"detail": "Organización con id 9 no existe"}` |
| 409 | el nombre y el estado ya son de otra organización | `{"detail": "La organización ya existe"}` |
| 422 | path o body inválido, o un campo en null | `{"errors": [{"message": "El nombre no puede ser nulo", "field": "name", "type": "..."}]}` |
