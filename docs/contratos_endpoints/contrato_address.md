# Address

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Domicilios. Prefijo montado en `app/main.py`: `/addresses`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en cada llamada.

No hay baja. El alta cuelga el domicilio de un destinatario que ya existe: `POST /addresses/{receiver_id}`. El PATCH usa el id del domicilio, no el del destinatario.

El texto se guarda en mayúsculas. En calle y número, además, se abrevian palabras completas y se quitan signos. Colonia, municipio, ciudad, código postal, país y referencia solo se recortan y se pasan a mayúsculas: conservan acentos y no se abrevian.

Si la página pedida se pasa del final, la respuesta trae la última página que sí existe. Sin resultados: `page` 1, `total` 0, `total_pages` 0, `items` [].

## GET /addresses/

### Descripción
Listar domicilios paginados. El texto busca en colonia, calle, ciudad o municipio. `state` filtra por igualdad.

### Request

Sin body.

Query:
- `search`: string, opcional, 2–50. Al menos 2 caracteres después de recortar espacios.
- `state`: string, opcional. Un estado de la lista de abajo. `jalisco` y `JALISCO` valen.
- `page`: int, default 1, >= 1
- `page_size`: int, default 10, 3–50
- `order_by`: `id` | `state`, default `id`
- `direction`: `desc` | `asc`, default `asc`

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| search | string | no | null | query. `QLineEdit`, máximo 50. |
| state | string | no | null | query. `QComboBox` con los estados. |
| page | int | no | 1 | query |
| page_size | int | no | 10 | query. 3–50. |
| order_by | string | no | id | query. Combo `id` o `state`. |
| direction | string | no | asc | query. Combo `asc` o `desc`. |

### Validaciones
- `search` se recorta. Si queda con menos de 2 caracteres, 422 con mensaje `Search debe tener al menos 2 caracteres`. No hay patrón.
- La búsqueda es un fragmento, en mayúsculas, sobre colonia, calle, ciudad y municipio.
- `state` tiene que ser uno de estos valores, ya sin acentos:

`AGUASCALIENTES`, `BAJA CALIFORNIA`, `BAJA CALIFORNIA SUR`, `CAMPECHE`, `CHIAPAS`, `CHIHUAHUA`, `CIUDAD DE MEXICO`, `COAHUILA`, `COLIMA`, `DURANGO`, `ESTADO DE MEXICO`, `GUANAJUATO`, `GUERRERO`, `HIDALGO`, `JALISCO`, `MICHOACAN`, `MORELOS`, `NAYARIT`, `NUEVO LEON`, `OAXACA`, `PUEBLA`, `QUERETARO`, `QUINTANA ROO`, `SAN LUIS POTOSI`, `SINALOA`, `SONORA`, `TABASCO`, `TAMAULIPAS`, `TLAXCALA`, `VERACRUZ`, `YUCATAN`, `ZACATECAS`.

### Respuesta
Status: 200 — `PaginatedAddresses`

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
  "search": "Reforma",
  "state": null,
  "items": [
    {
      "id": 1,
      "street": "AV. REFORMA",
      "num_street": "120",
      "colony": "CENTRO",
      "municipality": "GUADALAJARA",
      "city": "GUADALAJARA",
      "state": "JALISCO",
      "postal_code": "44100",
      "country": "MEXICO",
      "address_reference": null,
      "receiver_id": 4,
      "created_at": "2026-11-10T23:00:00Z",
      "updated_at": "2026-11-10T23:00:00Z",
      "created_by": 1,
      "updated_by": null
    }
  ]
}
```

`search` en la respuesta conserva las mayúsculas que envió el cliente, ya recortado. `state` sale con el valor del catálogo, o `null` si no se filtró. La lista va en una tabla.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | query inválido | `{"errors": [{"message": "...", "field": "state", "type": "..."}]}` |

## POST /addresses/{receiver_id}

### Descripción
Crear un domicilio para un destinatario que ya existe. Status 201.

### Request

Path:
- `receiver_id`: int >= 1

```json
{
  "street": "Avenida Reforma",
  "num_street": "120",
  "colony": "Centro",
  "municipality": "Guadalajara",
  "city": "Guadalajara",
  "state": "Jalisco",
  "postal_code": "44100",
  "country": "Mexico",
  "address_reference": "Edificio norte"
}
```

`address_reference` se puede omitir.

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| receiver_id | int | sí | — | path. >= 1 |
| street | string | sí | — | body. 3–80. `QLineEdit`. |
| num_street | string | sí | — | body. 1–15. `QLineEdit`. |
| colony | string | sí | — | body. 3–60. |
| municipality | string | sí | — | body. 3–60. |
| city | string | sí | — | body. 3–60. |
| state | string | sí | — | body. Combo de estados. |
| postal_code | string | sí | — | body. 4–5. `QLineEdit` con `setMaxLength(5)`. No exige solo dígitos. |
| country | string | sí | — | body. 3–50. Ejemplo `MEXICO`. |
| address_reference | string | no | null | body. Máximo 50. Sin mínimo. |

### Validaciones
- Todo el texto se recorta y se guarda en mayúsculas. Colonia, municipio, ciudad, código postal, país y referencia conservan acentos.
- Calle y número, después de las mayúsculas, sustituyen estas palabras completas:

| Texto | Queda |
|-------|-------|
| CALLE | C. |
| AVENIDA | AV. |
| BOULEVARD | BLVD. |
| CARRETERA | CARR. |
| SIN NÚMERO / SIN NUMERO | SN. |
| S/N | SN |
| NUMERO / NÚMERO | NUM. |
| EDIFICIO | EDIF. |
| KILOMETRO | KM. |

- En calle y número se borran `\ : [ ] # ° " , ! ¿ ¡ “ ”`. El guion `-` pasa a espacio. `Avenida Reforma` se guarda como `AV. REFORMA`.
- `state` usa el mismo catálogo del GET. `Michoacán` queda `MICHOACAN`. `Ciudad de México` queda `CIUDAD DE MEXICO`.
- Dos domicilios del mismo destinatario son el mismo si coinciden calle, colonia, código postal, municipio, ciudad, estado y país. El número y la referencia no cuentan. Esa comparación ignora acentos y mayúsculas. El segundo alta responde 409 e incluye el `address_id` del que ya existe.

### Respuesta
Status: 201 — `AddressDto`. Misma forma que un elemento de `items`, con el texto ya normalizado.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | el destinatario no existe | `{"detail": "Destinatario con id 4 no existe"}` |
| 409 | ya tiene un domicilio equivalente | `{"detail": {"msg": "El destinatario ya tiene un domicilio equivalente", "address_id": 1}}` |
| 422 | path o body inválido | `{"errors": [{"message": "...", "field": "postal_code", "type": "..."}]}` |

## PATCH /addresses/{address_id}

### Descripción
Actualizar un domicilio. Solo cambian las claves enviadas. Un cuerpo `{}` responde 200 con el domicilio actual.

### Request

Path:
- `address_id`: int >= 1

```json
{ "num_street": "122", "address_reference": "Planta baja" }
```

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| address_id | int | sí | — | path. >= 1 |
| street | string | no | se omite | body. 3–80 si se envía |
| num_street | string | no | se omite | body. 1–15 si se envía |
| colony | string | no | se omite | body. 3–60 si se envía |
| municipality | string | no | se omite | body. 3–60 si se envía |
| city | string | no | se omite | body. 3–60 si se envía |
| state | string | no | se omite | body. Mismo catálogo |
| postal_code | string | no | se omite | body. 4–5 si se envía |
| country | string | no | se omite | body. 3–50 si se envía |
| address_reference | string | no | se omite | body. Máximo 50. `null` borra la referencia. |

### Validaciones
- Las claves enviadas pasan por las mismas reglas del alta: mayúsculas, abreviaturas de calle y número, catálogo de estado.
- Omite lo que no cambia.
- `address_reference` en `null` deja la referencia vacía.
- No mandes `null` en calle ni número: el normalizador no lo acepta. Tampoco en colonia, municipio, ciudad, estado, código postal o país: esas columnas no aceptan nulo.
- Si el resultado queda equivalente a otro domicilio del mismo destinatario, 409 con el `address_id` de ese otro. El propio domicilio no choca consigo mismo.

### Respuesta
Status: 200 — `AddressDto`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin token, token inválido o usuario inactivo | `{"detail": "Not authenticated"}`, `{"detail": "Token inválido o expirado"}` o `{"detail": "Usuario no válido o inactivo"}` |
| 404 | el domicilio no existe | `{"detail": "Domicilio con id 9 no existe"}` |
| 409 | quedaría igual a otro domicilio del mismo destinatario | `{"detail": {"msg": "El destinatario ya tiene un domicilio equivalente", "address_id": 1}}` |
| 422 | path o body inválido | `{"errors": [{"message": "...", "field": "street", "type": "..."}]}` |
