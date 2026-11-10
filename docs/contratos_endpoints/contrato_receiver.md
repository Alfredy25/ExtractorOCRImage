# Receiver

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Rutas montadas en `app/main.py`: colección `POST /receivers/` y `GET /receivers/`, actualización `PATCH /receivers/{receiver_id}`. No hay GET por id ni DELETE.

El alta crea el destinatario y, en la misma petición, su dirección (obligatoria), un contacto y un volante (opcionales) y, si aplica, título y puesto. Esos objetos anidados no se actualizan en el PATCH: el PATCH solo cambia datos del destinatario (`full_name`, `email`, `title`, `position`, `type_entity`).

`type_entity`: `PERSONA` | `GOBIERNO` | `PRIVADA`.

## POST /receivers/

### Descripción

Crear destinatario. Crea el destinatario con su dirección. Contacto y volante son opcionales.

### Request

PERSONA (puesto opcional):

```json
{
  "type_entity": "PERSONA",
  "title": { "abbreviation": "DR.", "meaning": "Doctor" },
  "full_name": "JUAN PEREZ LOPEZ",
  "email": "juan.perez@ejemplo.com",
  "position": {
    "job_role": { "abbreviation": "DIR.", "meaning": "Director" },
    "organization": {
      "name": "CONGRESO DEL ESTADO DE TABASCO",
      "state": "TABASCO"
    }
  },
  "address": {
    "street": "AVENIDA REFORMA",
    "num_street": "120",
    "colony": "CENTRO",
    "municipality": "GUADALAJARA",
    "city": "GUADALAJARA",
    "state": "JALISCO",
    "postal_code": "44100",
    "country": "MEXICO",
    "address_reference": "FRENTE AL PARQUE"
  },
  "contact": { "phone": "3312345678", "ext": "12" },
  "volante": { "name": "VCS-26-131000-00167" }
}
```

PERSONA sin puesto: omitir `position` (o enviarlo `null`). `title` y `full_name` siguen siendo obligatorios.

GOBIERNO o PRIVADA: no enviar `full_name` ni `title`. `position` es obligatorio; `job_role` dentro del puesto puede omitirse.

```json
{
  "type_entity": "GOBIERNO",
  "email": "contacto@congreso.gob.mx",
  "position": {
    "organization": {
      "name": "CONGRESO DEL ESTADO DE TABASCO",
      "state": "TABASCO"
    }
  },
  "address": {
    "street": "AVENIDA REFORMA",
    "num_street": "120",
    "colony": "CENTRO",
    "municipality": "CENTRO",
    "city": "VILLAHERMOSA",
    "state": "TABASCO",
    "postal_code": "86000",
    "country": "MEXICO"
  }
}
```

Header:

- `Authorization`: Bearer 
- `Content-Type`: application/json

### Campos

| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| type_entity | string | sí | — | body. `PERSONA`, `GOBIERNO` o `PRIVADA`. Combo. |
| title | object \| null | condicional | null | body. Obligatorio si `PERSONA`. Prohibido si `GOBIERNO` o `PRIVADA`. Grupo. |
| title.abbreviation | string | sí, si hay title | — | 3–60. Ejemplo `DR.`. Línea de texto. |
| title.meaning | string | sí, si hay title | — | 3–150. Ejemplo `Doctor`. |
| full_name | string \| null | condicional | null | body. Obligatorio si `PERSONA`. Prohibido si `GOBIERNO` o `PRIVADA`. 5–70 sobre el texto enviado. Línea de texto. |
| email | string \| null | no | null | body. Correo, máximo 80. |
| position | object \| null | condicional | null | body. Obligatorio si `GOBIERNO` o `PRIVADA`. Opcional si `PERSONA`. Grupo. |
| position.job_role | object \| null | no | null | Si se omite, el servidor asigna un cargo fijo (ver Validaciones). |
| position.job_role.abbreviation | string | sí, si hay job_role | — | 2–60. Ejemplo `DIR.`. |
| position.job_role.meaning | string | sí, si hay job_role | — | 3–150. Ejemplo `Director`. |
| position.organization | object | sí, si hay position | — | Grupo. |
| position.organization.name | string | sí | — | 3–180. Ejemplo `CONGRESO DEL ESTADO DE TABASCO`. |
| position.organization.state | string | sí | — | Estado de México. Combo. Ejemplo `TABASCO`. |
| address | object | sí | — | body. Una dirección. Grupo. En la respuesta llega dentro de `addresses` (lista). |
| address.street | string | sí | — | 3–80. |
| address.num_street | string | sí | — | 1–15. |
| address.colony | string | sí | — | 3–60. |
| address.municipality | string | sí | — | 3–60. |
| address.city | string | sí | — | 3–60. |
| address.state | string | sí | — | Estado de México. Combo. Ejemplos `JALISCO`, `PUEBLA`. |
| address.postal_code | string | sí | — | 4–5. No exige solo dígitos. |
| address.country | string | sí | — | 3–50. Ejemplo `MEXICO`. |
| address.address_reference | string \| null | no | null | Máximo 50. |
| contact | object \| null | no | null | body. Grupo. En la respuesta llega dentro de `contacts` (lista). |
| contact.phone | string | sí, si hay contact | — | 8–10 dígitos. |
| contact.ext | string \| null | no | null | Hasta 5 dígitos. Vacío se guarda como null. |
| volante | object \| null | no | null | body. Grupo. En la respuesta llega dentro de `volantes` (lista). |
| volante.name | string | sí, si hay volante | — | 18–35. Ejemplo `VCS-26-131000-00167`. |

`created_at`, `updated_at`, `created_by` y `updated_by` no se envían.

### Validaciones

- `type_entity` solo acepta `PERSONA`, `GOBIERNO` o `PRIVADA`.
- PERSONA: `full_name` con texto después de recortar, y `title` presente. Si falta el nombre, el `type` del 422 es `receiver_full_name_required_for_persona`. Si falta el título, `receiver_title_required_for_persona`.
- GOBIERNO o PRIVADA: no enviar `full_name` ni `title` (ni siquiera con valor). Si alguno viene, el `type` es `receiver_name_title_forbidden_for_government_or_private`. `position` es obligatorio; si falta, el `type` es `receiver_position_required`.
- Esos cuatro `type` salen de un validador del objeto completo: en el 422 el `field` queda `body`.
- `full_name` en el alta: 5–70 caracteres sobre el texto tal como se envía. El servidor después recorta y guarda en mayúsculas. Un nombre que solo cumple el mínimo por espacios puede guardarse más corto.
- `email`: correo válido, máximo 80. El servidor recorta y guarda en minúsculas. Omitir o `null` deja el correo vacío.
- Título: se busca por `abbreviation` exacta (no cambia mayúsculas). Si ya existe, se reutiliza y el `meaning` enviado no actualiza el título. Si no existe, se crea.
- Puesto: `organization` es obligatoria cuando hay `position`. `job_role` es opcional.
  - PERSONA con puesto y sin `job_role`: cargo `SIN CARGO` / `Sin cargo especificado`.
  - GOBIERNO sin `job_role`: cargo `INSTITUCIONAL GOBIERNO` / `Destinatario dirigido a institución gubernamental`.
  - PRIVADA sin `job_role`: cargo `INSTITUCIONAL PRIVADO` / `Destinatario dirigido a institución privada`.
  - Si `job_role` viene, se busca por abreviatura ya normalizada. Si existe, se reutiliza y el `meaning` enviado no lo actualiza.
- Cargo, cuando se envía: `abbreviation` se recorta y pasa a mayúsculas; 2–60; solo letras (incluida Ñ), punto y espacio. `meaning` se recorta y pasa a tipo título; 3–150; solo letras (con acentos y Ñ) y espacio. Los límites y el patrón se miden ya normalizados.
- Organización: `name` se recorta, pasa a mayúsculas, sustituye palabras institucionales y quita signos (`\ : [ ] # ° - " , ! ¿ ¡` y comillas tipográficas; el guion pasa a espacio). Abreviaturas: `UNIVERSIDAD`→`UNI.`, `AUTONOMA`→`AUT.`, `SECRETARIA DE ADMINISTRACION TRIBUTARIA`→`S.A.T.`, `SECRETARIA DE CONTRALORIA GENERAL`→`S.C.E.`, `ORGANO INTERNO DE CONTROL` y `ORGANO DE CONTROL INTERNO`→`O.I.C.`, `CONTRALORIA GENERAL DEL ESTADO`→`C.G.E.`, `BAJA CALIFORNIA SUR`→`B.C.S.`, `SAN LUIS POTOSI`→`S.L.P.`. Después, 3–180. Se reutiliza si ya hay la misma organización (nombre normalizado + estado); no se actualiza.
- `organization.state` y `address.state`: uno de los 32 estados. El texto se recorta, pasa a mayúsculas y se le quitan acentos de vocales (Ñ se conserva) antes de compararlo con el catálogo. Valores: `AGUASCALIENTES`, `BAJA CALIFORNIA`, `BAJA CALIFORNIA SUR`, `CAMPECHE`, `CHIAPAS`, `CHIHUAHUA`, `CIUDAD DE MEXICO`, `COAHUILA`, `COLIMA`, `DURANGO`, `ESTADO DE MEXICO`, `GUANAJUATO`, `GUERRERO`, `HIDALGO`, `JALISCO`, `MICHOACAN`, `MORELOS`, `NAYARIT`, `NUEVO LEON`, `OAXACA`, `PUEBLA`, `QUERETARO`, `QUINTANA ROO`, `SAN LUIS POTOSI`, `SINALOA`, `SONORA`, `TABASCO`, `TAMAULIPAS`, `TLAXCALA`, `VERACRUZ`, `YUCATAN`, `ZACATECAS`.
- Dirección: `street` y `num_street` se recortan, pasan a mayúsculas, abrevian palabras completas y quitan los mismos signos que la organización. Abreviaturas de calle: `CALLE`→`C.`, `AVENIDA`→`AV.`, `BOULEVARD`→`BLVD.`, `CARRETERA`→`CARR.`, `SIN NÚMERO` y `SIN NUMERO`→`SN.`, `S/N`→`SN`, `NUMERO` y `NÚMERO`→`NUM.`, `EDIFICIO`→`EDIF.`, `KILOMETRO`→`KM.`. `colony`, `municipality`, `city`, `postal_code`, `country` y `address_reference` solo se recortan y pasan a mayúsculas. Los mínimos y máximos se miden ya normalizados. `address_reference` vacío no se envía, o se envía `null`.
- Contacto: `phone` se recorta; solo dígitos; 8–10. `ext` se recorta; si queda vacío pasa a `null`; si tiene valor, solo dígitos y máximo 5.
- Volante: `name` de 18 a 35 caracteres. Se guarda en mayúsculas, sin recortar espacios. Si ese nombre en mayúsculas ya existe, se reutiliza el volante.
- Duplicado de destinatario (409), después de normalizar:
  - PERSONA con puesto: mismo `full_name` (sin importar mayúsculas) y el mismo puesto.
  - PERSONA sin puesto: mismo `full_name` y el mismo título, y sin puesto.
  - GOBIERNO o PRIVADA: mismo `type_entity` y el mismo puesto. El nombre no entra en la comparación.

### Respuesta

Status: 201 — `ReceiverDto`

```json
{
  "id": 1,
  "type_entity": "PERSONA",
  "title": {
    "id": 3,
    "abbreviation": "DR.",
    "meaning": "Doctor",
    "created_at": "2026-11-09T16:00:00",
    "updated_at": "2026-11-09T16:00:00",
    "created_by": 1,
    "updated_by": null
  },
  "full_name": "JUAN PEREZ LOPEZ",
  "email": "juan.perez@ejemplo.com",
  "position": {
    "id": 8,
    "job_role": {
      "id": 2,
      "abbreviation": "DIR.",
      "meaning": "Director",
      "created_at": "2026-11-09T16:00:00",
      "updated_at": "2026-11-09T16:00:00",
      "created_by": 1,
      "updated_by": null
    },
    "organization": {
      "id": 4,
      "name": "CONGRESO DEL ESTADO DE TABASCO",
      "state": "TABASCO",
      "created_at": "2026-11-09T16:00:00",
      "updated_at": "2026-11-09T16:00:00",
      "created_by": 1,
      "updated_by": null
    },
    "created_at": "2026-11-09T16:00:00",
    "updated_at": "2026-11-09T16:00:00",
    "created_by": 1,
    "updated_by": null
  },
  "addresses": [
    {
      "id": 10,
      "street": "AV. REFORMA",
      "num_street": "120",
      "colony": "CENTRO",
      "municipality": "GUADALAJARA",
      "city": "GUADALAJARA",
      "state": "JALISCO",
      "postal_code": "44100",
      "country": "MEXICO",
      "address_reference": "FRENTE AL PARQUE",
      "receiver_id": 1,
      "created_at": "2026-11-09T16:00:00",
      "updated_at": "2026-11-09T16:00:00",
      "created_by": 1,
      "updated_by": null
    }
  ],
  "contacts": [
    {
      "id": 6,
      "phone": "3312345678",
      "ext": "12",
      "id_destinatario": 1,
      "created_at": "2026-11-09T16:00:00",
      "updated_at": "2026-11-09T16:00:00",
      "created_by": 1,
      "updated_by": null
    }
  ],
  "volantes": [
    {
      "id": 5,
      "name": "VCS-26-131000-00167",
      "created_at": "2026-11-09T16:00:00",
      "updated_at": "2026-11-09T16:00:00",
      "created_by": 1,
      "updated_by": null
    }
  ],
  "created_at": "2026-11-09T16:00:00",
  "updated_at": "2026-11-09T16:00:00",
  "created_by": 1,
  "updated_by": null
}
```

En GOBIERNO y PRIVADA, `title` y `full_name` vienen `null`. Si no hubo puesto, contacto o volante, `position` es `null` y `contacts` o `volantes` vienen `[]`. La calle de la respuesta ya está abreviada (`AVENIDA` → `AV.`).

### Errores

| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 409 | destinatario duplicado | `{"detail": {"msg": "El destinatario ya existe", "receiver_id": 1}}` |
| 422 | body inválido o regla de tipo | `{"errors": [{"message": "...", "field": "body", "type": "receiver_full_name_required_for_persona"}]}` |
| 422 | campo requerido, formato o longitud | `{"errors": [{"message": "...", "field": "full_name", "type": "missing"}]}` |

`type` de las reglas de negocio del alta: `receiver_full_name_required_for_persona`, `receiver_title_required_for_persona`, `receiver_name_title_forbidden_for_government_or_private`, `receiver_position_required`. El `message` es el texto de esa regla (`full_name es requerido para PERSONA`, `title es requerido para PERSONA`, `full_name y title no son permitidos para GOBIERNO o PRIVADA`, `El puesto es requerido para GOBIERNO o PRIVADA`).

Reutilizar título, cargo, organización o volante que ya existen no responde 409: el alta sigue y enlaza el registro existente.

## GET /receivers/

### Descripción

Listar destinatarios paginados. Busca por nombre de la persona y por nombre de la organización del puesto. Puede filtrar por tipo y por estado de alguna dirección.

### Request

Sin body.

Query:

- `search`: string, opcional. Máximo 40. Letras (con acentos y Ñ), dígitos, espacio, punto y guion. Ejemplo: `S.A. de C.V.`
- `page`: int, default 1, mínimo 1
- `page_size`: int, default 50, mínimo 5, máximo 100. El texto de la ruta dice «5-50»; el límite que aplica es 100.
- `order_by`: `id` | `full_name` | `name_org` | `created_at`, default `id`
- `direction`: `desc` | `asc`, default `asc`
- `type_entity`: `PERSONA` | `GOBIERNO` | `PRIVADA`, opcional
- `state`: string, opcional. Estado de una dirección del destinatario.

Header:

- `Authorization`: Bearer 

### Campos

| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| search | string | no | null | query. Línea de texto, máximo 40. |
| page | int | no | 1 | query. Spin, mínimo 1. |
| page_size | int | no | 50 | query. Spin, 5–100. |
| order_by | string | no | `id` | query. Combo: `id`, `full_name`, `name_org`, `created_at`. |
| direction | string | no | `asc` | query. Combo: `asc`, `desc`. |
| type_entity | string | no | null | query. Combo: `PERSONA`, `GOBIERNO`, `PRIVADA`. |
| state | string | no | null | query. Combo con los 32 estados. |

### Validaciones

- `search`, si viene: debe cumplir el patrón antes de recortar. Después se recortan los extremos y deben quedar al menos 3 caracteres. Si no, 422 con mensaje `Search debe tener al menos 3 caracteres`. La búsqueda usa ese texto en mayúsculas y hace coincidencia parcial contra `full_name` y contra el nombre de la organización del puesto.
- `page` ≥ 1. `page_size` de 5 a 100.
- `order_by` y `direction` solo los literales de arriba. `name_org` ordena por el nombre de la organización del puesto. Si el orden no es `id`, el `id` se usa como desempate en la misma dirección.
- `type_entity`, si viene, solo `PERSONA`, `GOBIERNO` o `PRIVADA`.
- `state`, si viene, se recorta y pasa a mayúsculas. No se le quitan acentos. Se compara igual al `state` guardado en alguna dirección. Esos estados están sin acento (`MICHOACAN`, `QUERETARO`, `NUEVO LEON`, `CIUDAD DE MEXICO`, …). Enviar `Michoacán` queda `MICHOACÁN` y no coincide.
- Si la página pedida pasa de la última, la respuesta devuelve la última página existente. Con cero resultados, `page` es 1, `total_pages` es 0, `has_prev` y `has_next` son false.
- `search` en la respuesta es el texto ya recortado y en mayúsculas, o `null` si no se buscó.

### Respuesta

Status: 200 — `PaginatedReceiver`

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
  "search": "JUAN",
  "items": []
}
```

Cada elemento de `items` es un `ReceiverDto` con la misma forma que la respuesta 201.

### Errores

| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | query inválido | `{"errors": [{"message": "Search debe tener al menos 3 caracteres", "field": "search", "type": "value_error"}]}` |

## PATCH /receivers/{receiver_id}

### Descripción

Actualizar el destinatario. Solo se aplican los campos enviados. No modifica direcciones, contactos ni volantes.

### Request

```json
{
  "full_name": "JUAN PEREZ GARCIA",
  "email": "juan.garcia@ejemplo.com"
}
```

Path:

- `receiver_id`: int ≥ 1. Ejemplo `1`.

Header:

- `Authorization`: Bearer 

Para quitar el correo de una persona o institución, enviar `"email": null`.

Para quitar el puesto de una PERSONA, enviar `"position": null`.

No enviar `null` en `full_name`, `title` ni `type_entity`: el servidor lo rechaza. Para no cambiar un campo, omitirlo.

Pasar de GOBIERNO o PRIVADA a PERSONA exige los dos campos en la misma petición:

```json
{
  "type_entity": "PERSONA",
  "full_name": "ANA LOPEZ RUIZ",
  "title": { "abbreviation": "LIC.", "meaning": "Licenciado" }
}
```

### Campos

| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| receiver_id | int | sí | — | path. ≥ 1. |
| full_name | string | no | omitido | body. 5–70 ya recortado y en mayúsculas. No enviar `null`. |
| email | string \| null | no | omitido | body. Correo, máximo 80. `null` borra el correo. |
| title | object | no | omitido | body. Misma forma que en el alta (`abbreviation`, `meaning`). No enviar `null`. |
| position | object \| null | no | omitido | body. Misma forma que en el alta. `null` solo es válido en PERSONA y quita el puesto. |
| type_entity | string | no | omitido | body. `PERSONA`, `GOBIERNO` o `PRIVADA`. No enviar `null`. |

### Validaciones

- Se actualizan solo las claves presentes. Un cuerpo `{}` es válido y devuelve el destinatario sin cambiar sus datos de negocio.
- `full_name`, si se envía: no puede ser `null`; se recorta y pasa a mayúsculas antes de medir 5–70. Mensaje si viene `null`: `El nombre no puede ser nulo`.
- `email`, si se envía: `null` lo deja vacío; si es texto, se recorta, pasa a minúsculas y debe ser un correo de hasta 80.
- `title`, si se envía: no puede ser `null` (`El título no puede ser nulo`). El objeto trae `abbreviation` (3–60) y `meaning` (3–150). Se reutiliza por abreviatura exacta, igual que en el alta.
- `type_entity`, si se envía: no puede ser `null` (`El tipo no puede ser nulo`) y solo acepta los tres valores.
- Cambio de tipo:
  - Omitirlo, o enviar el mismo tipo, deja el tipo actual.
  - De GOBIERNO o PRIVADA a PERSONA: el body debe incluir `full_name` y `title`. Si falta uno, 422 con `detail` `Para pasar a PERSONA se requieren full_name y title`.
  - De PERSONA a GOBIERNO o PRIVADA: 422, `Una persona no puede cambiar a GOBIERNO o PRIVADA`.
  - Entre GOBIERNO y PRIVADA: 422, `No se puede cambiar entre GOBIERNO y PRIVADA`.
- Si el tipo resultante no es PERSONA, enviar `full_name` o `title` responde 422: `full_name y title no son permitidos para GOBIERNO o PRIVADA`.
- `position`:
  - PERSONA, clave omitida: el puesto no cambia.
  - PERSONA, `null`: se quita el puesto.
  - PERSONA, objeto sin `job_role`: cargo `SIN CARGO`.
  - GOBIERNO o PRIVADA, `null` o cualquier envío de puesto vacío: 422, `El puesto es requerido para GOBIERNO o PRIVADA`.
  - GOBIERNO o PRIVADA, objeto sin `job_role`: el cargo fijo del tipo (`INSTITUCIONAL GOBIERNO` o `INSTITUCIONAL PRIVADO`).
  - Con `job_role` y `organization`, mismas reglas de formato y reutilización que en el alta.
- Después del cambio se vuelve a comprobar el duplicado, sin contar al propio destinatario. La clave es la misma que en el alta. Si choca con otro, 409.

### Respuesta

Status: 200 — `ReceiverDto`, la misma forma que el 201.

### Errores

| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 404 | no existe ese id | `{"detail": "Destinatario con id 1 no existe"}` |
| 409 | el resultado duplica a otro destinatario | `{"detail": {"msg": "El destinatario ya existe", "receiver_id": 2}}` |
| 422 | `null` o formato en un campo | `{"errors": [{"message": "Value error, El nombre no puede ser nulo", "field": "full_name", "type": "value_error"}]}` |
| 422 | cambio de tipo no permitido, o campos de persona en una institución | `{"detail": "Una persona no puede cambiar a GOBIERNO o PRIVADA"}` |
| 422 | falta identidad al pasar a PERSONA | `{"detail": "Para pasar a PERSONA se requieren full_name y title"}` |
| 422 | `full_name` o `title` con tipo institucional | `{"detail": "full_name y title no son permitidos para GOBIERNO o PRIVADA"}` |
| 422 | puesto vacío en GOBIERNO o PRIVADA | `{"detail": "El puesto es requerido para GOBIERNO o PRIVADA"}` |
| 422 | `receiver_id` menor que 1 | `{"errors": [{"message": "...", "field": "receiver_id", "type": "..."}]}` |

Los 422 que lanza el servicio usan `detail` (texto). Los 422 de validación del body o del path usan `errors`.