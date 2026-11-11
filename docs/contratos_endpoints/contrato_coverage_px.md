# CoveragePx

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Cobertura Paquete Express. Prefijo montado en `app/main.py`: `/coverages`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en esta llamada.

Solo hay consulta. No hay alta, edición ni baja por HTTP. `branch` y `place` existen en la tabla y no viajan en la respuesta. Un mismo código postal puede devolver varias filas (una por colonia).

## GET /coverages/

### Descripción
Listar coberturas de un código postal. La respuesta es un arreglo, sin paginación. El parámetro de query se llama `cp`.

### Request

Sin body.

Query:
- `cp`: string, requerido, 4–5 caracteres. Coincide exactamente con `postal_code`. No recorta espacios ni rellena ceros a la izquierda.

Header:
- `Authorization`: Bearer &lt;token&gt;

Ejemplo: `GET /coverages/?cp=98160`

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| cp | string | sí | — | query. `QLineEdit` con `setMaxLength(5)`. |

### Validaciones
- `cp` es obligatorio. Menos de 4 o más de 5 caracteres responde 422.
- No hay patrón: cualquier texto de esa longitud pasa la validación. Si no existe en la tabla, la respuesta es 404.
- La búsqueda es igualdad exacta. `"98160"` y `"9816"` son códigos distintos. `"09816"` no equivale a `"9816"`.

### Respuesta
Status: 200 — lista de `CoveragePxDto`.

```json
[
  {
    "id_delivery": 1,
    "postal_code": "98160",
    "colony": "COLONIA JUAREZ",
    "municipality": "ZACATECAS",
    "city": "ZACATECAS",
    "state": "ZACATECAS",
    "coverage_type": "PAQUETEXPRESS"
  }
]
```

| Campo | Tipo | Notas |
|-------|------|-------|
| id_delivery | int | Identificador de la fila. |
| postal_code | string | El mismo `cp` consultado. |
| colony | string | Colonia o asentamiento. |
| municipality | string | Municipio o delegación. |
| city | string | Ciudad. |
| state | string | Estado. |
| coverage_type | string | Combo cerrado. Ver valores abajo. |

`coverage_type` solo puede ser uno de estos textos, con espacios y mayúsculas tal cual:

- `PAQUETEXPRESS`
- `ZONA PLUS`
- `ZONA PLUS ESPECIAL`

Varias colonias del mismo código postal llegan como varios objetos en el arreglo. Conviene mostrarlas en una tabla o lista.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 404 | ninguna fila con ese `cp` | `{"detail": "no hay cobertura con el cp 98160 en el sistema"}` |
| 422 | `cp` ausente, corto o largo | `{"errors": [{"message": "...", "field": "cp", "type": "..."}]}` |

El 404 incluye el código recibido en el mensaje. El 422 usa el handler global: `field` es `cp`, y `type` es el de Pydantic (`missing`, `string_too_short` o `string_too_long`).
