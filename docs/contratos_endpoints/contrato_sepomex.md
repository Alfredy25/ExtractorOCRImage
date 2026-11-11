# Sepomex

Auth: Bearer token. Header `Authorization: Bearer <access_token>`.

Token: `POST /auth/login` con `{ "email", "password" }` → `{ "access_token", "token_type": "bearer" }`.

Catálogo SEPOMEX. Prefijo montado en `app/main.py`: `/sepomex`. Un `QNetworkAccessManager` (o equivalente) debe adjuntar el Bearer en esta llamada.

Solo hay consulta por código postal. No hay listado general, alta, edición ni baja. Un código postal puede devolver varios asentamientos, ordenados por nombre de asentamiento.

## GET /sepomex/{postal_code}

### Descripción
Consultar los asentamientos de un código postal.

### Request

Sin body.

Path:
- `postal_code`: string de exactamente 5 dígitos. Ejemplo `97000`.

Header:
- `Authorization`: Bearer &lt;token&gt;

Ejemplo: `GET /sepomex/97000`

### Campos
| Campo | Tipo | Requerido | Default | Notas |
|-------|------|-----------|---------|-------|
| postal_code | string | sí | — | path. `QLineEdit` con `setMaxLength(5)` y validador de 5 dígitos. |

### Validaciones
- Exactamente 5 dígitos: `^\d{5}$`. `9700` y `970000` responden 422. `01234` es un código válido de longitud.
- La búsqueda es igualdad exacta. No recorta espacios: un código con espacio no cumple el patrón.

### Respuesta
Status: 200 — lista de `SepomexDto`.

```json
[
  {
    "id": 1,
    "postal_code": "97000",
    "settlement": "CENTRO",
    "settlement_type": "Colonia",
    "municipality": "Mérida",
    "city": "Mérida",
    "state": "YUCATAN",
    "state_code": "31",
    "zone": "Urbano"
  }
]
```

| Campo | Tipo | Notas |
|-------|------|-------|
| id | int | Identificador de la fila del catálogo. |
| postal_code | string | 5 caracteres. El mismo código consultado. |
| settlement | string | Asentamiento. |
| settlement_type | string | Texto del catálogo. No es un combo cerrado del API. |
| municipality | string | Municipio. |
| city | string \| null | Ciudad. Puede venir `null`. |
| state | string | Estado del catálogo de la república, sin acentos. Los mismos valores que domicilio y organización: `YUCATAN`, `CIUDAD DE MEXICO`, `NUEVO LEON`, y el resto. |
| state_code | string | Clave de 2 caracteres del catálogo. |
| zone | string | Texto del catálogo. No es un combo cerrado del API. |

Varios asentamientos del mismo código llegan como varios objetos. Conviene mostrarlos en una tabla. `city` vacío se muestra como celda en blanco.

### Errores
| Status | Cuándo | Cuerpo |
|--------|--------|--------|
| 401 | sin header Authorization | `{"detail": "Not authenticated"}` |
| 401 | token inválido o expirado | `{"detail": "Token inválido o expirado"}` |
| 401 | usuario inexistente o inactivo | `{"detail": "Usuario no válido o inactivo"}` |
| 404 | el código no está en el catálogo | `{"detail": "Código postal 97000 no existe en el catálogo"}` |
| 422 | el path no son 5 dígitos | `{"errors": [{"message": "...", "field": "postal_code", "type": "..."}]}` |

El 404 incluye en el mensaje el código recibido.
