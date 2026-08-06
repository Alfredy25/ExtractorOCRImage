# Implementación de Módulo de Envíos Paquetexpress

## Contexto del Proyecto

La aplicación actual es un cliente de escritorio desarrollado en Python + PySide6.

Actualmente la aplicación permite:

1. Iniciar sesión mediante JWT contra backend FastAPI.
2. Cargar imágenes de sobres.
3. Recortar la zona del destinatario.
4. Extraer datos mediante OCR utilizando OpenAI.
5. Editar los campos extraídos.
6. Crear registros de destinatarios.
7. Exportar registros a Excel o CSV.

La aplicación NO utiliza base de datos local.

Toda la persistencia ocurre mediante llamadas REST al backend.

---

# Objetivo

Agregar una nueva funcionalidad para generar envíos mediante Paquetexpress utilizando:

- datos obtenidos por OCR
- consulta de cobertura
- creación de envío

Esta funcionalidad debe integrarse al flujo existente sin afectar el comportamiento actual.

---

# IMPORTANTE

Antes de modificar cualquier archivo:

1. Analizar el código existente.
2. Identificar los lugares afectados.
3. Identificar servicios, formularios, modelos y validaciones relacionados.
4. Localizar la pantalla principal donde se realiza actualmente:
   - carga de imagen
   - recorte
   - OCR
   - creación de registros
5. Implementar los cambios necesarios.
6. Al finalizar entregar resumen de impacto.

Si existe alguna duda o alguna parte de este requerimiento no es clara:

DETENERSE ANTES DE IMPLEMENTAR

y solicitar aclaración.

---

# Flujo General

```text
Pantalla Principal OCR
        │
        ▼
Consultar Cobertura
        │
        ▼
GET /coverages/{cp}
        │
 ┌──────┴──────┐
 │             │
 │             │
 ▼             ▼
404         Cobertura
Sin          Encontrada
Cobertura
 │             │
 ▼             ▼
Modal      Abrir Nueva Ventana
Error            │
 │               ▼
 ▼       Seleccionar Cobertura
Regresar         │
                 ▼
       Completar Datos Envío
                 │
                 ▼
       Validación Acumulativa
                 │
                 ▼
         POST /shipments-px/
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
      Error            Éxito
        │                 │
        ▼                 ▼
 Mostrar Errores      Cerrar Ventana
                         │
                         ▼
             Regresar Pantalla OCR
```

---

# Nuevo Botón

Agregar botón:

```text
Consultar Cobertura
```

en la pantalla principal.

El código postal utilizado será el extraído previamente por OCR.

---

# Endpoint Cobertura

## Request

```http
GET /coverages/{cp}
```

Ejemplo:

```http
GET /coverages/cp=55010
```

Autenticación:

```http
Authorization: Bearer <token>
```

utilizando el token obtenido durante el login.

---

## Caso A - Sin cobertura

Respuesta:

```json
{
  "detail": "no hay cobertura con el cp 55010 en el sistema"
}
```

Comportamiento esperado:

- Mostrar modal de ERROR.
- No mostrar warnings ni mensajes informativos.
- Indicar claramente que no existe cobertura para el código postal.
- Permanecer en la pantalla actual.

---

## Caso B - Cobertura encontrada

Respuesta:

```json
[
  {
    "postal_code": "01030",
    "colony": "FLORIDA",
    "municipality": "ALVARO OBREGON",
    "city": "CIUDAD DE MEXICO",
    "state": "CIUDAD DE MEXICO",
    "coverage_type": "PAQUETEXPRESS"
  }
]
```

o múltiples registros.

En este caso abrir una NUEVA VENTANA.

No utilizar modal.

---

# Diseño de la Nueva Ventana

La ventana tendrá dos formularios principales.

```text
┌─────────────────────────────┬──────────────────────────────┐
│ COBERTURA PAQUETEXPRESS     │ DATOS DEL ENVÍO             │
│                             │                              │
│ Código Postal              │ Destinatario                │
│ Colonia                    │ RFC                         │
│ Ciudad                     │ País                        │
│ Estado                     │ Calle                       │
│ Tipo Cobertura             │ Número                      │
│                            │ Teléfono                    │
│                            │ Email                       │
│                            │ Referencia                  │
│                            │ Cantidad                    │
│                            │ Código Paquete              │
│                            │ Contenido                   │
│                            │ Peso                        │
│                            │ Largo                       │
│                            │ Ancho                       │
│                            │ Alto                        │
└─────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ DATOS OCR DE REFERENCIA                             │
└─────────────────────────────────────────────────────┘
```

aqui utilizar como referencia el estilo de pantalla que te dejo en la carpeta stylo/ventana_envio.html

---

# Formulario Cobertura

Mostrar:

- Código Postal
- Colonia (ComboBox)
- Ciudad
- Estado
- Tipo Cobertura

Si existen varias coberturas:

```text
FLORIDA
AXOTLA
...
```

mostrar las colonias en un ComboBox.

La primera opción debe quedar seleccionada por defecto.

Al cambiar colonia actualizar automáticamente:

- city
- state
- coverage_type

con los datos asociados al registro seleccionado.

---

# Datos OCR de Referencia

Esta sección es únicamente visual.

NO se envía al backend.

Mostrar:

- Estado OCR
- Ciudad OCR
- Colonia OCR
- Código Postal OCR

Estos datos permiten al operador comparar la información obtenida por OCR con la cobertura devuelta por Paquetexpress para seleccionar la colonia correcta.

---

# Formulario de Envío

## name_receiver

Prioridad de llenado:

1. nombre_titulo
2. cargo_dependencia
3. vacío

Reglas:

- Si nombre_titulo tiene valor → usar nombre_titulo.
- Si nombre_titulo está vacío → usar cargo_dependencia.
- Si ambos están vacíos → dejar vacío.

Campo editable.

---

## rfc

Valor inicial:

```text
XAXX010101000
```

Editable.

---

## country

Valor inicial:

```text
MEXICO
```

No editable.

---

## Campos provenientes de Cobertura

Estos valores SI se envían al backend:

- state
- city
- colony
- postal_code
- coverage_type

Deben obtenerse exclusivamente del formulario de cobertura.

Nunca de los datos OCR.

---

## street

Llenar con:

```text
direccion
```

extraída por OCR.

Editable.

---

## num_street

Captura manual.

---

## phone

Llenar con:

```text
contacto
```

extraído por OCR.

Editable.

---

## email

Captura manual.

---

## address_reference

Llenar con:

```text
indicaciones
```

extraídas por OCR.

Editable.

---

# Valores Iniciales

Todos editables.

```text
quantity = 1
package_code = 1
content = DOCUMENTOS LEGALES
weight = 1
length = 30
width = 20
height = 1
```

---

# Endpoint Crear Envío

## URL

```http
POST /shipments-px/
```

Autenticación:

```http
Authorization: Bearer <token>
```

utilizando el token obtenido durante el login.

---

# Fuente de Verdad para Validaciones

Utilizar exactamente las validaciones definidas por el modelo Pydantic:

```python
# ShippingRequest:
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ShippingRequest(BaseModel):
    name_receiver: str = Field(..., min_length=4, max_length=80,
        examples=["DR. PEPE PINEDO PINEDO"])

    rfc: str = Field(..., min_length=12, max_length=15,
        examples=["XAXX-010101-000"])

    country: str = Field(..., min_length=3,max_length=50,
        examples=["MEXICO"])

    state: str = Field(..., min_length=5, max_length=50,
        examples=["ZACATECAS"])

    city: str = Field(..., min_length=3, max_length=60,
        examples=["CIUDAD GOBIERNO"])

    colony: str = Field(..., min_length=3, max_length=60,
        examples=["COLONIA JUAREZ"])

    street: str = Field(..., min_length=3, max_length=80,
        examples=["CTO. CERRO DEL GATO"])

    num_street: str = Field(..., min_length=1, max_length=15,
        examples=["SN", "123"])

    postal_code: str = Field(..., min_length=4, max_length=5,
        pattern=r"^[0-9]+$", examples=["98160"])

    email: Optional[EmailStr] = Field(default=None,
        max_length=80, examples=["destinatario@example.com"])

    phone: Optional[str] = Field(default=None, min_length=10, max_length=20,
        examples=["5555555555"])

    address_reference: Optional[str] = Field(default=None, max_length=50,
        examples=["Edificio G, cerca de la entrada principal."])

    quantity: int = Field(..., ge=1, examples=[1])

    package_code: int = Field(..., ge=1, le=63, examples=[1])

    content: str = Field(..., min_length=10, max_length=100,
        examples=["Documentos Legales"])

    weight: Decimal = Field(..., gt=0, max_digits=8,
        decimal_places=2, examples=["1.00"])

    length: Decimal = Field(..., gt=0, max_digits=8,
        decimal_places=2, examples=["30.00"])

    width: Decimal = Field(..., gt=0, max_digits=8,
        decimal_places=2, examples=["20.00"])

    height: Decimal = Field(..., gt=0, max_digits=8,
        decimal_places=2, examples=["10.00"])

    coverage_type: str = Field(default=None, min_length=4, max_length=60)
```

Respetar:

- min_length
- max_length
- pattern
- ge
- le
- gt
- Optional
- EmailStr

---

# Validación Acumulativa

NO detenerse en el primer error.

Implementar validación acumulativa.

Proceso:

1. Validar todos los campos.
2. Acumular todos los errores.
3. Mostrar todos los errores encontrados.

Ejemplo:

```text
Se encontraron los siguientes errores:

• name_receiver debe tener entre 4 y 80 caracteres.

• email no tiene un formato válido.

• phone debe contener al menos 10 caracteres.

• postal_code debe contener únicamente números.
```

---

# Errores

Mostrar mediante modal de ERROR.

No usar:

- warnings
- tooltips
- mensajes informativos

Debe utilizarse el componente de error utilizado actualmente en la aplicación.

---

# Éxito

Si el envío es creado correctamente:

1. Mostrar mensaje de éxito.
2. Cerrar la ventana de envíos.
3. Regresar automáticamente a la pantalla principal.
4. Mantener visible:
   - imagen
   - recorte
   - formulario OCR
   - información previamente capturada

---

# Cancelar

Agregar botón:

```text
Cancelar
```

Comportamiento:

1. Cerrar ventana de envíos.
2. Regresar a la pantalla principal.
3. No perder información existente.

---

# Testing

Crear o actualizar pruebas para:

## Cobertura

- cobertura encontrada
- cobertura no encontrada
- selección de colonia
- actualización automática de datos

## Validaciones

- validación exitosa
- múltiples errores simultáneos
- validación acumulativa

## Envío

- creación exitosa
- error de backend
- serialización correcta del request

## UI

- apertura de ventana
- regreso mediante cancelar
- regreso después de envío exitoso

---

# Entregable

Al finalizar proporcionar:

1. Archivos modificados.
2. Resumen de cambios.
3. Nuevos formularios agregados.
4. Nuevos servicios agregados.
5. Validaciones implementadas.
6. Tests creados o actualizados.
7. Riesgos detectados.
8. Suposiciones realizadas durante la implementación.