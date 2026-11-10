# ShipmentPx

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Envío de Paquete Express. Prefijo montado en `app/main.py`: `/shipments-px`. No hay paginación ni DELETE. El alta no pide folio: el servidor copia `id_shipping` en `id_folio`. El GET por folio usa `id_folio`. El PUT usa `id_shipping`. Después del alta los dos coinciden.

En el alta, el servicio pasa a mayúsculas `name_receiver`, `rfc`, `country`, `state`, `city`, `colony`, `street`, `num_street`, `phone`, `address_reference`, `content` y `comments`. No cambia `postal_code`, `email`, `coverage_type` ni las medidas. El PUT no pasa nada a mayúsculas: guarda el texto tal como se envía.

## GET /shipments-px/

### Descripción
Listar envíos. No está paginado: la respuesta es un arreglo. Orden: `created_at` descendente.

### Request

Sin body.

Query:
- `fecha_inicio`: datetime, opcional. Inclusive (`created_at` >= este valor).
- `fecha_fin`: datetime, opcional. Inclusive (`created_at` <= este valor).
- `my_shipments`: bool, default `false`. Si es `true`, solo envíos del usuario del token.

Header:
- `Authorization`: Bearer &lt;token&gt;

Si se omiten las dos fechas, el rango es hoy a las 00:00:00 hasta la hora actual del servidor. Si solo viene `fecha_fin`, el inicio es ese mismo día a las 00:00:00. Si solo viene `fecha_inicio`, el fin es la hora actual.

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| fecha_inicio | string (datetime) | no | hoy 00:00:00 si ambas faltan | query. Fecha y hora, sin zona. |
| fecha_fin | string (datetime) | no | ahora, si falta | query. Fecha y hora, sin zona. |
| my_shipments | bool | no | false | query. Casilla. |

### Validaciones
- Formato de fecha: ISO 8601 sin zona, por ejemplo `2026-11-09T00:00:00`. Una fecha sola (`2026-11-09`) queda en `00:00:00`. El servidor compara contra su hora local, también sin zona.
- Ninguna de las dos fechas puede ser posterior a ahora. El fin de hoy a las 23:59 falla si esa hora todavía no llega: para “hasta ahora”, omite `fecha_fin`.
- `fecha_inicio` no puede ser mayor que `fecha_fin`.
- `my_shipments` acepta `true` o `false`.

### Respuesta
Status: 200 — lista de `ShippingDto`. Vacía si no hay envíos en el rango.

```json
[
  {
    "id_shipping": 1,
    "id_folio": 1,
    "name_receiver": "DR. PEPE PINEDO PINEDO",
    "rfc": "XAXX-010101-000",
    "country": "MEXICO",
    "state": "ZACATECAS",
    "city": "CIUDAD GOBIERNO",
    "colony": "COLONIA JUAREZ",
    "street": "CTO. CERRO DEL GATO",
    "num_street": "SN",
    "postal_code": "98160",
    "email": "destinatario@example.com",
    "phone": "5555555555",
    "address_reference": "EDIFICIO G, CERCA DE LA ENTRADA PRINCIPAL.",
    "quantity": 1,
    "package_code": 1,
    "content": "DOCUMENTOS LEGALES",
    "weight": 1.0,
    "length": 30.0,
    "width": 20.0,
    "height": 10.0,
    "coverage_type": "PAQUETEXPRESS",
    "comments": "ENTREGAR EN UN HORARIO DE 09:00 A 14:00 HRS.",
    "created_at": "2026-11-09T16:00:00"
  }
]
```

`created_by` no viene en esta respuesta.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 400 | inicio o fin posterior a ahora | `{"detail": "La fecha inicio o fecha fin no puede ser mayor a la fecha actual"}` |
| 400 | inicio mayor que fin | `{"detail": "La fecha inicio no puede ser mayor que la fecha fin"}` |
| 422 | query con formato inválido | `{"errors": [{"message": "...", "field": "fecha_inicio", "type": "..."}]}` |

## POST /shipments-px/

### Descripción
Crear envío. Status 201. El folio de respuesta es el mismo número que `id_shipping`.

### Request

```json
{
  "name_receiver": "DR. PEPE PINEDO PINEDO",
  "rfc": "XAXX-010101-000",
  "country": "MEXICO",
  "state": "ZACATECAS",
  "city": "CIUDAD GOBIERNO",
  "colony": "COLONIA JUAREZ",
  "street": "CTO. CERRO DEL GATO",
  "num_street": "SN",
  "postal_code": "98160",
  "email": "destinatario@example.com",
  "phone": "5555555555",
  "address_reference": "Edificio G, cerca de la entrada principal.",
  "quantity": 1,
  "package_code": 1,
  "content": "Documentos Legales",
  "weight": 1.0,
  "length": 30.0,
  "width": 20.0,
  "height": 10.0,
  "coverage_type": "PAQUETEXPRESS",
  "comments": "ENTREGAR EN UN HORARIO DE 09:00 A 14:00 HRS."
}
```

Header:
- `Authorization`: Bearer &lt;token&gt;
- `Content-Type`: application/json

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| name_receiver | string | sí | — | body. 4–80. Se guarda en mayúsculas. |
| rfc | string | sí | — | body. 12–15. Se guarda en mayúsculas. Ejemplo `XAXX-010101-000`. |
| country | string | sí | — | body. 3–50. Mayúsculas. Ejemplo `MEXICO`. |
| state | string | sí | — | body. 5–50. Mayúsculas. Ejemplo `ZACATECAS`. Texto libre, no es el catálogo de estados del destinatario. |
| city | string | sí | — | body. 3–60. Mayúsculas. |
| colony | string | sí | — | body. 3–60. Mayúsculas. |
| street | string | sí | — | body. 3–80. Mayúsculas. No abrevia calle. |
| num_street | string | sí | — | body. 1–15. Mayúsculas. Ejemplos `SN`, `123`. |
| postal_code | string | sí | — | body. 4–5, solo dígitos. |
| email | string \| null | no | null | body. Correo, máximo 80. Se guarda tal cual. |
| phone | string \| null | no | null | body. 10–20 si se envía. Mayúsculas. |
| address_reference | string \| null | no | null | body. Máximo 50. Mayúsculas. |
| quantity | int | sí | — | body. Mínimo 1. Sin máximo en el schema. Spin. |
| package_code | int | sí | — | body. 1–63. Spin. |
| content | string | sí | — | body. 10–100. Mayúsculas. Ejemplo `Documentos Legales`. |
| weight | number | sí | — | body. Mayor que 0, hasta 8 dígitos y 2 decimales. |
| length | number | sí | — | body. Igual que `weight`. Ejemplo `30.00`. |
| width | number | sí | — | body. Igual que `weight`. Ejemplo `20.00`. |
| height | number | sí | — | body. Igual que `weight`. Ejemplo `10.00`. |
| coverage_type | string \| null | no | null | body. Si se envía, 4–60. No se pasa a mayúsculas. Ejemplo `PAQUETEXPRESS`. El PUT no puede cambiarlo. |
| comments | string | sí en la práctica | null en el schema | body. 5–80. Mayúsculas. El schema permite omitirlo, pero el servicio llama `.upper()`: hay que enviarlo siempre. |

No se envían `id_shipping`, `id_folio`, `created_at` ni `created_by`.

### Validaciones
- Los mínimos y máximos se miden sobre el texto enviado, antes de pasarlo a mayúsculas.
- `postal_code`: patrón `^[0-9]+$`, longitud 4 o 5.
- `email`: correo válido, máximo 80. Omitir o `null` lo deja vacío.
- `phone` y `address_reference`: omitir o `null` los deja vacíos. Si vienen, respetan su mínimo y máximo.
- `quantity` ≥ 1. `package_code` de 1 a 63.
- `weight`, `length`, `width` y `height`: número mayor que 0, como máximo 8 dígitos en total y 2 decimales. `0` y los negativos fallan. Sirve `1` o `1.5`; `1.555` no.
- `coverage_type`: omitirlo lo guarda null. Si se envía, 4–60 y se conserva el texto (no hay catálogo cerrado).
- `comments`: envíalo siempre, de 5 a 80 caracteres. Se guarda en mayúsculas.

### Respuesta
Status: 201 — `ShippingDto`, la misma forma que cada elemento del GET. `id_folio` sale igual a `id_shipping`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 422 | campo requerido, longitud, patrón o decimal | `{"errors": [{"message": "...", "field": "postal_code", "type": "..."}]}` |

## GET /shipments-px/{folio}

### Descripción
Obtener un envío por `id_folio`.

### Request

Sin body.

Path:
- `folio`: int. Es `id_folio`, no un tipo aparte. Tras el alta coincide con `id_shipping`.

Header:
- `Authorization`: Bearer &lt;token&gt;

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| folio | int | sí | — | path. |

### Validaciones
- Tiene que ser un entero. El router no declara mínimo.

### Respuesta
Status: 200 — un `ShippingDto`, la misma forma que el elemento del listado.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 404 | no hay envío con ese folio | `{"detail": "Envío no encontrado"}` |
| 422 | `folio` no es entero | `{"errors": [{"message": "...", "field": "folio", "type": "..."}]}` |

## PUT /shipments-px/{id_shipping}

### Descripción
Actualizar un envío por `id_shipping`. Aunque el método es PUT, solo cambia las claves enviadas. No se puede cambiar `id_shipping`, `id_folio`, `coverage_type` ni `created_at`.

### Request

```json
{
  "phone": "3331234567",
  "comments": "ENTREGAR EN RECEPCION"
}
```

Path:
- `id_shipping`: int. Llave primaria. Tras el alta es el mismo número que `id_folio`.

Header:
- `Authorization`: Bearer &lt;token&gt;

Para no tocar un campo, omítelo. `null` vacía `email`, `phone`, `address_reference` o `comments`. No envíes `null` en el resto: el schema lo acepta, pero esas columnas no admiten null y esta ruta no lo convierte en un 422.

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| id_shipping | int | sí | — | path. |
| name_receiver | string \| null | no | omitido | body. Sin min/max en este schema. No se pasa a mayúsculas. |
| rfc | string \| null | no | omitido | body. Igual. |
| country | string \| null | no | omitido | body. |
| state | string \| null | no | omitido | body. |
| city | string \| null | no | omitido | body. |
| colony | string \| null | no | omitido | body. |
| street | string \| null | no | omitido | body. |
| num_street | string \| null | no | omitido | body. |
| postal_code | string \| null | no | omitido | body. Este schema no repite el patrón de dígitos. |
| email | string \| null | no | omitido | body. Si viene texto, tiene que ser correo. `null` lo vacía. |
| phone | string \| null | no | omitido | body. `null` lo vacía. |
| address_reference | string \| null | no | omitido | body. `null` lo vacía. |
| quantity | int \| null | no | omitido | body. |
| package_code | int \| null | no | omitido | body. |
| content | string \| null | no | omitido | body. |
| weight | number \| null | no | omitido | body. |
| length | number \| null | no | omitido | body. |
| width | number \| null | no | omitido | body. |
| height | number \| null | no | omitido | body. |
| comments | string \| null | no | omitido | body. `null` lo vacía. No se pasa a mayúsculas. |

`coverage_type` no está en este body.

### Validaciones
- Cuerpo `{}` es válido y devuelve el envío sin cambiar sus datos de negocio. Aun así, el servicio reescribe `created_by` con el usuario del token. Ese id no sale en `ShippingDto`.
- El PUT no declara mínimos, máximos ni patrón. El escritorio puede seguir los límites del alta para no guardar valores que el alta rechazaría.
- `email`, si se envía como texto, tiene que ser un correo. `null` lo borra.
- El texto se guarda como llega, sin mayúsculas.

### Respuesta
Status: 200 — `ShippingDto`.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 404 | no existe ese `id_shipping` | `{"detail": "Envio no encontrado"}` |
| 422 | `id_shipping` no es entero, o `email` inválido | `{"errors": [{"message": "...", "field": "email", "type": "..."}]}` |

El 404 de esta ruta dice `Envio` sin acento. El 404 del GET por folio dice `Envío` con acento.
