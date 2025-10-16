# Standard Library
import json
import locale
import logging
import os
import random
import re
import signal
import string
import time
from collections import Counter
from datetime import datetime, timedelta

# Third-party Libraries
import requests
from dateutil import parser  # pip install python-dateutil
from dotenv import load_dotenv
from faker import Faker
from faker_airtravel import AirTravelProvider
from flasgger import Swagger
from marshmallow import Schema, fields, validates, ValidationError, RAISE

# Flask
from flask import Flask, jsonify, request


# Define el tiempo máximo de espera en segundos
MAX_TIMEOUT = 5

## Cargar variables de entorno desde el archivo .env
load_dotenv("config.env")


## Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        # logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)


## Configuración de la aplicación Flask
app = Flask(__name__)


## Configuración de Swagger
swagger_template = {
    "info": {
        "title": "Air Travel API: Módulo Gestión de Vuelos",
        "version": "1.0.0",
        "description": "API para la gestión de reservas de vuelos.",
        "termsOfService": "https://pulseandola.com/terms",
        "Contact": {
            "ResponsibleOrganization": "Un mae random que trata de pulsearla para salir adelante.",
            "ResponsibleDeveloper": "El mismo mae random, le cuesta pero lo intenta.",
            "email": "",
            "URL": "https://pulseandola.com/contact"
        },
    },
    "tags": [
        {
          "name": "Airplanes",
          "description": "Operations related to airplane data"
        },
        {
          "name": "Airplanes Seats",
          "description": "Operations related to airplane seats data"
        },
        {
          "name": "Routes",
          "description": "Operations related to airplane routes"
        },
    ],
    "definitions": {
        "AirplaneSchema": {
            "type": "object",
            "properties": {
                "airplane_id": {
                    "type": "integer",
                    "example": 1
                },
                "model": {
                    "type": "string",
                    "example": "Boeing 737"
                },
                "manufacturer": {
                    "type": "string",
                    "example": "Boeing"
                },
                "year": {
                    "type": "integer",
                    "example": 2019
                },
                "capacity": {
                    "type": "integer",
                    "example": 15
                }
            },
            "required": ["airplane_id", "model", "manufacturer", "year", "capacity"]
        },
        "AirplaneSeatSchema": {
          "type": "object",
          "properties": {
            "seat_number": {
              "type": "string",
              "example": "12A",
              "description": "Número del asiento (ej. 12A)"
            },
            "status": {
              "type": "string",
              "enum": ["Libre", "Reservado"],
              "example": "Libre",
              "description": "Estado actual del asiento"
            }
          },
            "required": ["seat_number", "status"]
        },
        "AirplaneRouteSchema": {
          "type": "object",
          "properties": {
            "airplane_route_id": { "type": "integer", "example": 1 },
            "airplane_id": { "type": "integer", "example": 2 },
            "flight_number": { "type": "string", "example": "AV-1234" },
            "departure": { "type": "string", "example": "Aeropuerto Internacional Juan Santamaría" },
            "departure_time": { "type": "string", "example": "Marzo 30, 2025 - 16:46:19" },
            "arrival": { "type": "string", "example": "Aeropuerto Internacional El Dorado" },
            "arrival_time": { "type": "string", "example": "Marzo 30, 2025 - 19:25:00" },
            "flight_time": {
              "type": "string", "example": "2 horas 39 minutos", "readOnly": True
            },
            "price": { "type": "integer", "example": 98000 },
            "Moneda": {
              "type": "string",
              "enum": ["Colones", "Dolares", "Euros"],
              "example": "Colones"
            }
          },
          "required": [
            "airplane_route_id", "airplane_id", "flight_number",
            "departure", "departure_time", "arrival", "arrival_time", "price", "Moneda"
          ],
          "example": {
            "airplane_route_id": 1,
            "airplane_id": 1,
            "flight_number": "AV-1234",
            "departure": "Aeropuerto Internacional Juan Santamaría",
            "departure_time": "Marzo 30, 2025 - 16:46:19",
            "arrival": "Aeropuerto Internacional El Dorado",
            "arrival_time": "Marzo 30, 2025 - 19:25:00",
            "price": 98000,
            "Moneda": "Colones"
          }
        },
        "ErrorSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "example": "Descripción del error"
                },
                "errors": {
                    "type": "object",
                    "description": "Detalles adicionales del error",
                    "additionalProperties": {
                        "type": "array",
                        "items": { "type": "string" }
                    }
                }
            }
        }
    }
}

## Configuración de Swagger
swagger = Swagger(app, template=swagger_template)


############################################################################################################
############################################################################################################
############################################################################################################
## Aqui inicia Airplanes datos
############################################################################################################
############################################################################################################
############################################################################################################


## Generar datos de aviones falsos
fake_airplane = Faker()
## Añadir el proveedor de AirTravel a Faker
fake_airplane.add_provider(AirTravelProvider)


# Lista de algunos modelos de aviones comunes
airplane_models = [
    'Boeing 737', 'Boeing 777', 'Airbus A320', 'Airbus A380', 'Boeing 787',
    'Embraer E190', 'Airbus A350', 'Boeing 767', 'McDonnell Douglas MD-80',
    'Airbus A330'
]


# Función para generar el número de vuelo en formato alfanumérico (2 letras - 4 números)
def generate_flight_number():
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))  # 2 letras aleatorias
    numbers = random.randint(1000, 9999)  # 4 números aleatorios
    return f"{letters}-{numbers}"


## Lista para almacenar los asientos de todos los aviones
seats = []


## Función para generar asientos para un avión específico
def generar_asientos_para_avion(airplane_id, capacidad=15):
    columnas = ['A', 'B', 'C', 'D', 'E', 'F']
    asientos = []
    total_generados = 0
    fila = 1

    while total_generados < capacidad:
        for letra in columnas:
            if total_generados >= capacidad:
                break
            asiento = {
                'airplane_id': airplane_id,
                'seat_number': f"{fila}{letra}",
                'status': 'Libre'
            }
            asientos.append(asiento)
            total_generados += 1
        fila += 1

    return asientos


airplanes = []


## Generar datos de aviones falsos con sus asientos
for i in range(1, 4):
    year_raw = fake_airplane.year()
    year = int(year_raw) if isinstance(year_raw, str) and year_raw.isdigit() else year_raw
    avion = {
        'airplane_id': i,
        'model': random.choice(airplane_models),
        'manufacturer': fake_airplane.company(),
        'year': year,
        'capacity': 15
    }
    airplanes.append(avion)

    # Generar asientos para este avión y agregarlos a la lista global
    asientos_avion = generar_asientos_para_avion(avion['airplane_id'], capacidad=avion['capacity'])
    seats.extend(asientos_avion)


logging.info(f"\n\nInicio de generador de aviones \n")
# Imprimir los datos generados
for airplane in airplanes:
    logging.info(f"Avión generado: {airplane}")

logging.info(f"✅ Total de aviones generados: {len(airplanes)}\n")


## AirplaneSchema para validar los datos de los aviones
class AirplaneSchema(Schema):
    class Meta:
        unknown = RAISE  # Lanza error si se envía un campo no definido

    airplane_id = fields.Int(required=True, error_messages={
        "required": "El campo 'airplane_id' es obligatorio.",
        "invalid": "Debe ser un número entero."
    })
    model = fields.Str(required=True, error_messages={
        "required": "El campo 'model' es obligatorio.",
        "invalid": "Debe ser una cadena de texto."
    })
    manufacturer = fields.Str(required=True, error_messages={
        "required": "El campo 'manufacturer' es obligatorio.",
        "invalid": "Debe ser una cadena de texto."
    })
    year = fields.Int(required=True, validate=lambda x: x > 0, error_messages={
        "required": "El campo 'year' es obligatorio.",
        "invalid": "Debe ser un número entero."
    })
    capacity = fields.Int(required=True, validate=lambda x: x > 0, error_messages={
        "required": "El campo 'capacity' es obligatorio.",
        "invalid": "Debe ser un número entero positivo."
    })


## Instanciamos el esquema para usarlo para validar mas adelante
airplane_Schema = AirplaneSchema()


## Función para validar la estructura y los campos de un avión
def validar_avion(avion, current_year):
    """
    Verifica que un diccionario de avión cumpla con todos los requisitos de estructura y tipo.

    Nota: Solo se valida que el campo 'year' sea un número entero positivo (sin límite superior).
    """
    required_fields = ["airplane_id", "model", "manufacturer", "capacity", "year"]

    for campo in required_fields:
        if campo not in avion or avion[campo] in [None, ""]:
            return False, f"El campo '{campo}' está vacío o no está presente."

    if not isinstance(avion["airplane_id"], int) or avion["airplane_id"] <= 0:
        return False, "El 'airplane_id' debe ser un número entero positivo."

    if not isinstance(avion["model"], str) or not avion["model"].strip():
        return False, "El 'model' debe ser una cadena de texto no vacía."

    if not isinstance(avion["manufacturer"], str) or not avion["manufacturer"].strip():
        return False, "El 'manufacturer' debe ser una cadena de texto no vacía."

    if not isinstance(avion["capacity"], int) or avion["capacity"] <= 0:
        return False, "El 'capacity' debe ser un número entero positivo."

    if isinstance(avion["year"], str) and avion["year"].isdigit():
      avion["year"] = int(avion["year"])

    if not isinstance(avion["year"], int) or avion["year"] <= 0:
      return False, "El 'year' debe ser un número entero positivo."

    return True, None


############################################################################################################
## YA REVISADO 4/28 2:08 AM
## Endpoint para obtener la lista completa de aviones
@app.route('/get_airplanes', methods=['GET'])
def get_airplanes():
    """
    Summary: Obtiene la lista completa de aviones
    Description:
      Devuelve la lista completa de aviones disponibles en el sistema.
      Si no hay aviones registrados, devuelve un mensaje indicando que no hay registros.
    ---
    tags:
      - Airplanes
    responses:
      200:
        description: Lista de aviones obtenida correctamente
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/definitions/AirplaneSchema'
      500:
        description: Error interno o estructura de datos inválida
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    import time
    start = time.time()
    try:
        if not isinstance(airplanes, list):
            logging.error("❌ 'airplanes' no es una lista.")
            return jsonify({'message': 'Estructura interna inválida.'}), 500

        if not airplanes:
            logging.info("📭 No hay aviones registrados.")
            return jsonify({'message': 'No hay aviones registrados actualmente.'}), 200

        # Validar duplicados de ID
        seen_ids = set()
        for a in airplanes:
            aid = a.get('airplane_id')
            if aid in seen_ids:
                return jsonify({
                    'message': 'Error de datos: ID de avión duplicado.',
                    'errors': { 'airplane_id': [f'Duplicado: {aid}'] }
                }), 500
            seen_ids.add(aid)

        # Validar con Marshmallow
        schema = AirplaneSchema(many=True)
        errors = schema.validate(airplanes)
        if errors:
            logging.warning("❌ Errores de validación en los datos de aviones.")
            return jsonify({
                'message': 'Errores de validación detectados',
                'errors': errors
            }), 500

        elapsed = round(time.time() - start, 2)
        logging.info(f"✅ Se retornaron {len(airplanes)} aviones en {elapsed} segundos.")
        return jsonify(airplanes), 200

    except Exception:
        logging.exception("❌ Error inesperado al obtener los aviones.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': { 'exception': ['Ocurrió un error inesperado.'] }
        }), 500


############################################################################################################

def find_airplane(airplane_id):
    return next((airplane for airplane in airplanes if airplane['airplane_id'] == airplane_id), None)


############################################################################################################
## REVISADO 4-28 2:44 AM
## Endpoint para obtener un avión por su ID
@app.route('/get_airplane_by_id/<int:airplane_id>', methods=['GET'])
def get_airplane_by_id(airplane_id):
    """
    Summary: Obtiene un avión por su ID
    Description:
      Devuelve un avión específico por su ID.
      Si el parámetro no es válido, devuelve un 400.
      Si no se encuentra el avión, devuelve un 404.
    ---
    tags:
      - Airplanes
    parameters:
      - name: airplane_id
        in: path
        description: ID del avión (debe ser un entero positivo)
        required: true
        schema:
          type: integer
          minimum: 1
    responses:
      200:
        description: Avión encontrado
        content:
          application/json:
            schema:
              $ref: '#/definitions/AirplaneSchema'
      400:
        description: Parámetro inválido
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      404:
        description: Avión no encontrado
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    try:
        # 1) Validación de parámetro
        if airplane_id <= 0:
            return jsonify({
                'message': 'El ID del avión debe ser un entero positivo.',
                'errors': { 'airplane_id': ['Debe ser mayor que cero.'] }
            }), 400

        # 2) Búsqueda en memoria
        airplane = next((a for a in airplanes if a['airplane_id'] == airplane_id), None)
        if not airplane:
            return jsonify({
                'message': f'Avión con ID {airplane_id} no encontrado.',
                'errors': {}
            }), 404

        # 3) (Opcional) última validación con Marshmallow
        schema = AirplaneSchema()
        schema.load(airplane)

        return jsonify(airplane), 200

    except Exception:
        logging.exception("❌ Error inesperado al obtener el avión.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': { 'exception': ['Ocurrió un error inesperado.'] }
        }), 500


############################################################################################################
## Todo el proceso para agregar un avión
## Registrar un nuevo avión - REVISADO
# Función para detectar claves duplicadas en JSON crudo
def detectar_claves_duplicadas(raw_data):
    try:
        claves = []
        def hook(pairs):
            claves.extend(k for k, _ in pairs)
            return dict(pairs)
        json.loads(raw_data, object_pairs_hook=hook)
        duplicadas = [clave for clave, count in Counter(claves).items() if count > 1]
        return duplicadas
    except Exception as e:
        logging.warning("No se pudo analizar duplicados en el JSON: %s", str(e))
        return []

# Función para validar campos extra
def validar_campos_extra(data, expected_fields):
    return list(set(data) - expected_fields)

# Función para validar campos faltantes
def validar_campos_faltantes(data, expected_fields):
    return [campo for campo in expected_fields if campo not in data]


############################################################################################################
## Revisado 4-28 2:55 AM

## Endpoint para agregar un nuevo avión
@app.route('/add_airplane', methods=['POST'])
def add_airplane():
    """
    Summary: Agrega un nuevo avión
    Description:
      Recibe un JSON con los datos de un avión y lo registra en el sistema,
      generando automáticamente sus asientos.
      - Detecta claves duplicadas en el JSON bruto.
      - Valida campos extra y faltantes.
      - Valida con Marshmallow.
      - Comprueba unicidad POR CONTENIDO (modelo, fabricante, año, capacidad).
      - Genera asientos según la capacidad indicada.
    ---
    tags:
      - Airplanes
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/AirplaneSchema'
    responses:
      201:
        description: Avión agregado con éxito
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Avión y asientos agregados con éxito"
      400:
        description: Datos inválidos
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    try:
        # 1) Detectar claves duplicadas en el JSON bruto
        raw_json = request.data.decode('utf-8')
        duplicadas = detectar_claves_duplicadas(raw_json)
        if duplicadas:
            return jsonify({
                'message': f"Se detectaron campos duplicados: {', '.join(duplicadas)}",
                'errors': {'json': [f'Duplicada(s): {", ".join(duplicadas)}']}
            }), 400

        # 2) Parsear y validar presencia de cuerpo
        data = request.get_json()
        if not data:
            return jsonify({
                'message': 'No se recibió ningún cuerpo JSON.',
                'errors': {'body': ['Body vacío o mal formado']}
            }), 400

        expected = {"airplane_id", "model", "manufacturer", "year", "capacity"}
        extras = set(data) - expected
        faltantes = expected - set(data)

        if extras:
            return jsonify({
                'message': 'Campos no válidos detectados.',
                'errors': {'extras': list(extras)}
            }), 400
        if faltantes:
            return jsonify({
                'message': 'Faltan campos obligatorios.',
                'errors': {'faltantes': list(faltantes)}
            }), 400

        # 3) Validación de tipos/límites básicos
        if not isinstance(data['year'], int) or data['year'] <= 0:
            return jsonify({
                'message': "El campo 'year' debe ser un entero positivo.",
                'errors': {'year': ['Debe ser entero > 0']}
            }), 400

        # 4) Validación completa con Marshmallow
        errors = airplane_Schema.validate(data)
        if errors:
            return jsonify({
                'message': 'Errores de validación.',
                'errors': errors
            }), 400

        # 5) Verificar unicidad de ID
        if any(a['airplane_id'] == data['airplane_id'] for a in airplanes):
            return jsonify({
                'message': 'Ya existe un avión con ese ID.',
                'errors': {'airplane_id': ['Duplicado']}
            }), 400

        # 5.1) Verificar unicidad POR CONTENIDO (modelo+fabricante+año+capacidad)
        existente = next((
            a for a in airplanes
            if a['model'] == data['model']
            and a['manufacturer'] == data['manufacturer']
            and a['year'] == data['year']
            and a['capacity'] == data['capacity']
        ), None)
        if existente:
            return jsonify({
                'message': f"Ya existe un avión con los mismos datos (modelo, fabricante, año, capacidad) con ID {existente['airplane_id']}.",
                'errors': {'duplicate': [f"ID existente: {existente['airplane_id']}"]}
            }), 400

        # 6) Guardar y generar asientos
        nuevo = airplane_Schema.load(data)
        airplanes.append(nuevo)

        nuevos_asientos = generar_asientos_para_avion(
            nuevo['airplane_id'],
            capacidad=nuevo['capacity']
        )
        seats.extend(nuevos_asientos)

        logging.info(f"✈️ Avión agregado: {nuevo}")
        return jsonify({'message': 'Avión y asientos agregados con éxito'}), 201

    except Exception:
        logging.exception("❌ Error inesperado al agregar avión.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################
## REVISADO

def detectar_claves_duplicadas(raw_data):
    claves = []
    def hook(pairs):
        claves.extend(k for k, _ in pairs)
        return dict(pairs)
    try:
        json.loads(raw_data, object_pairs_hook=hook)
        return [k for k, v in Counter(claves).items() if v > 1]
    except Exception:
        return []


############################################################################################################
## REVISADO 4-28 3:08 AM

## Actualizar un avión existente por su ID
@app.route('/update_airplane/<int:airplane_id>', methods=['PUT'])
def update_airplane(airplane_id):
    """
    Summary: Actualiza un avión existente por su ID
    Description:
      Actualiza los datos (model, manufacturer, year, capacity) de un avión existente.
      - Valida que el ID sea un entero positivo.
      - Detecta claves duplicadas en el JSON bruto.
      - Valida campos extra y faltantes.
      - Valida con Marshmallow.
      - Verifica que haya cambios reales antes de actualizar.
    ---
    tags:
      - Airplanes
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: airplane_id
        in: path
        type: integer
        format: int64
        required: true
        description: ID del avión (entero positivo)
        minimum: 1
      - name: body
        in: body
        required: true
        description: Objeto con los campos a actualizar
        schema:
          type: object
          properties:
            model:
              type: string
              example: "Boeing 737"
            manufacturer:
              type: string
              example: "Boeing"
            year:
              type: integer
              example: 2019
            capacity:
              type: integer
              example: 150
          required:
            - model
            - manufacturer
            - year
            - capacity
    responses:
      200:
        description: Avión actualizado con éxito
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Avión actualizado con éxito"
      400:
        description: Parámetro inválido o datos incorrectos
        schema:
          $ref: '#/definitions/ErrorSchema'
      404:
        description: Avión no encontrado
        schema:
          $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        schema:
          $ref: '#/definitions/ErrorSchema'
    """
    try:
        # 1) Validar ID
        if airplane_id <= 0:
            return jsonify({
                'message': 'El ID del avión debe ser un entero positivo.',
                'errors': {'airplane_id': ['Debe ser mayor que cero.']}
            }), 400

        # 2) Detectar claves duplicadas en el JSON bruto
        raw_json = request.data.decode('utf-8')
        duplicadas = detectar_claves_duplicadas(raw_json)
        if duplicadas:
            return jsonify({
                'message': f'Se detectaron campos duplicados: {", ".join(duplicadas)}',
                'errors': {'json': [f'Duplicada(s): {", ".join(duplicadas)}']}
            }), 400

        # 3) Parsear body
        data = request.get_json()
        if not data:
            return jsonify({
                'message': 'No se recibió cuerpo JSON.',
                'errors': {'body': ['Body vacío o mal formado']}
            }), 400

        # 4) Validar campos extra y faltantes
        expected = {'model', 'manufacturer', 'year', 'capacity'}
        extras = set(data) - expected
        faltantes = expected - set(data)
        if extras:
            return jsonify({
                'message': 'Se encontraron campos no válidos.',
                'errors': {'extras': list(extras)}
            }), 400
        if faltantes:
            return jsonify({
                'message': 'Faltan campos obligatorios.',
                'errors': {'faltantes': list(faltantes)}
            }), 400

        # 5) Verificar existencia del avión
        airplane = find_airplane(airplane_id)
        if not airplane:
            return jsonify({
                'message': f'Avión con ID {airplane_id} no encontrado.',
                'errors': {}
            }), 404

        # 6) Validar con Marshmallow
        full = {'airplane_id': airplane_id, **data}
        errors = airplane_Schema.validate(full)
        if errors:
            return jsonify({
                'message': 'Errores de validación.',
                'errors': errors
            }), 400

        # 7) Sin cambios reales
        if all(airplane.get(k) == data.get(k) for k in expected):
            return jsonify({
                'message': 'No se realizaron cambios porque los datos son idénticos.'
            }), 200

        # 8) Actualizar y responder
        airplane.update(data)
        logging.info(f'✏️ Avión con ID={airplane_id} actualizado correctamente.')
        return jsonify({'message': 'Avión actualizado con éxito'}), 200

    except Exception:
        logging.exception('❌ Error inesperado al actualizar el avión.')
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################


# Manejador para cortar la ejecución si se excede el tiempo
def timeout_handler(signum, frame):
    raise TimeoutError("⏱️ Tiempo de espera agotado en la operación.")


@app.route('/delete_airplane_by_id/<int:airplane_id>', methods=['DELETE'])
def delete_airplane_by_id(airplane_id):
    """
    Summary: Elimina un avión y sus asientos asociados
    Description:
      Elimina el avión identificado por `airplane_id` junto con todos sus asientos registrados.
      - Valida que el ID sea un entero positivo.
      - Verifica que exista el avión.
      - Cuenta y elimina los asientos asociados.
      - Devuelve el número de asientos eliminados.
    ---
    tags:
      - Airplanes
    produces:
      - application/json
    parameters:
      - name: airplane_id
        in: path
        type: integer
        format: int64
        required: true
        description: ID del avión a eliminar (entero positivo)
        minimum: 1
    responses:
      200:
        description: Avión y asientos eliminados correctamente
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Avión con ID 3 eliminado exitosamente."
            asientos_eliminados:
              type: integer
              example: 15
      400:
        description: Parámetro inválido
        schema:
          $ref: '#/definitions/ErrorSchema'
      404:
        description: Avión no encontrado
        schema:
          $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        schema:
          $ref: '#/definitions/ErrorSchema'
    """
    try:
        # 1) Validar parámetro
        if airplane_id <= 0:
            return jsonify({
                'message': 'El ID del avión debe ser un entero positivo.',
                'errors': {'airplane_id': ['Debe ser mayor que cero.']}
            }), 400

        # 2) Validar estructuras internas
        if not isinstance(airplanes, list) or not isinstance(seats, list):
            return jsonify({
                'message': 'Estructura interna inválida.',
                'errors': {}
            }), 500

        # 3) Verificar existencia de aviones
        if not airplanes:
            return jsonify({
                'message': 'No hay aviones registrados en el sistema.',
                'errors': {}
            }), 404

        # 4) Buscar el avión
        airplane = next((a for a in airplanes if a.get('airplane_id') == airplane_id), None)
        if not airplane:
            return jsonify({
                'message': f'Avión con ID {airplane_id} no encontrado.',
                'errors': {}
            }), 404

        # 5) Contar y eliminar asientos asociados
        count = sum(1 for s in seats if s.get('airplane_id') == airplane_id)
        seats[:] = [s for s in seats if s.get('airplane_id') != airplane_id]

        # 6) Eliminar el avión
        airplanes.remove(airplane)
        logging.info(f"🗑️ Avión eliminado: ID={airplane_id}, Asientos eliminados={count}")

        return jsonify({
            'message': f'Avión con ID {airplane_id} eliminado exitosamente.',
            'asientos_eliminados': count
        }), 200

    except Exception:
        logging.exception("❌ Error inesperado al eliminar el avión.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################
############################################################################################################
############################################################################################################
### Aqui termina Airplanes datos
############################################################################################################
############################################################################################################
############################################################################################################


############################################################################################################
############################################################################################################
############################################################################################################
### Aqui empieza Airplane seats datos
############################################################################################################
############################################################################################################
############################################################################################################


## Definición del esquema para validar los datos de los asientos de aviones
class AirplaneSeatSchema(Schema):
    airplane_id = fields.Int(required=True, validate=lambda x: x > 0, error_messages={
        "required": "El campo 'airplane_id' es obligatorio.",
        "invalid": "Debe ser un número entero positivo."
    })

    seat_number = fields.Str(required=True, error_messages={
        "required": "El campo 'seat_number' es obligatorio.",
        "invalid": "Debe ser una cadena de texto no vacía."
    })

    status = fields.Str(required=True, validate=lambda x: x in ["Libre", "Reservado", "Pagado"], error_messages={
        "required": "El campo 'status' es obligatorio.",
        "invalid": "Debe ser 'Libre', 'Reservado', 'Pagado'."
    })

    class Meta:
        unknown = RAISE


## Instanciamos el esquema para usarlo para validar mas adelante
airplane_seat_schema = AirplaneSeatSchema(many=True)
airplane_seats_schema = AirplaneSeatSchema(many=True)


## Obtener todos los asientos de un avión específico
@app.route('/get_airplane_seats/<int:airplane_id>/seats', methods=['GET'])
def get_airplane_seats(airplane_id):
    """
    Summary: Obtiene todos los asientos de un avión específico
    Description:
      Recupera la lista de asientos para el avión identificado por `airplane_id`.
      - Valida que el ID sea un entero positivo.
      - Verifica que exista el avión.
      - Devuelve 404 si no hay asientos para ese avión.
    ---
    tags:
      - Airplanes Seats
    produces:
      - application/json
    parameters:
      - name: airplane_id
        in: path
        type: integer
        format: int64
        required: true
        description: ID del avión (entero positivo)
        minimum: 1
    responses:
      200:
        description: Lista de asientos del avión
        schema:
          type: array
          items:
            $ref: '#/definitions/AirplaneSeatSchema'
      400:
        description: Parámetro inválido
        schema:
          $ref: '#/definitions/ErrorSchema'
      404:
        description: Avión no encontrado o sin asientos
        schema:
          $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        schema:
          $ref: '#/definitions/ErrorSchema'
    """
    try:
        # Validar parámetro
        if airplane_id <= 0:
            return jsonify({
                'message': 'El ID del avión debe ser un entero positivo.',
                'errors': {'airplane_id': ['Debe ser mayor que cero.']}
            }), 400

        # Estructuras internas
        if not isinstance(airplanes, list) or not isinstance(seats, list):
            return jsonify({
                'message': 'Estructura interna inválida.',
                'errors': {}
            }), 500

        # Verificar existencia del avión
        if not any(a.get('airplane_id') == airplane_id for a in airplanes):
            return jsonify({
                'message': f'Avión con ID {airplane_id} no encontrado.',
                'errors': {}
            }), 404

        # Filtrar asientos
        lista = [s for s in seats if s.get('airplane_id') == airplane_id]
        if not lista:
            return jsonify({
                'message': f'No hay asientos registrados para el avión {airplane_id}.',
                'errors': {}
            }), 404

        # Validación con Marshmallow
        errors = airplane_seats_schema.validate(lista)
        if errors:
            return jsonify({
                'message': 'Error en los datos de los asientos.',
                'errors': errors
            }), 500

        return jsonify(lista), 200

    except Exception:
        logging.exception("❌ Error inesperado al obtener los asientos del avión.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################


## Obtener todos los asientos agrupados por avión
@app.route('/seats/grouped-by-airplane', methods=['GET'])
def get_seats_grouped_by_airplane():
    """
    Summary: Obtiene todos los asientos agrupados por avión
    Description:
      Recupera todos los asientos y los agrupa por `airplane_id`.
      - Verifica que la lista de asientos exista y no esté vacía.
      - Agrupa y valida cada grupo con Marshmallow.
    ---
    tags:
      - Airplanes Seats
    produces:
      - application/json
    responses:
      200:
        description: Asientos agrupados por avión
        schema:
          type: object
          additionalProperties:
            type: array
            items:
              $ref: '#/definitions/AirplaneSeatSchema'
      500:
        description: Error interno del servidor
        schema:
          $ref: '#/definitions/ErrorSchema'
    """
    try:
        # Validar lista de asientos
        if not isinstance(seats, list):
            return jsonify({
                'message': 'Estructura interna de asientos inválida.',
                'errors': {}
            }), 500

        if not seats:
            return jsonify({
                'message': 'No hay asientos registrados en el sistema.',
                'errors': {}
            }), 200

        # Agrupar
        grouped = {}
        for s in seats:
            aid = s.get('airplane_id')
            if not isinstance(aid, int) or aid <= 0:
                continue
            grouped.setdefault(aid, []).append({
                'airplane_id': aid,
                'seat_number': s.get('seat_number'),
                'status': s.get('status')
            })

        # Validar cada grupo
        for aid, group in grouped.items():
            errors = airplane_seats_schema.validate(group)
            if errors:
                return jsonify({
                    'message': f'Error en los datos de los asientos del avión {aid}.',
                    'errors': errors
                }), 500

        return jsonify(grouped), 200

    except Exception:
        logging.exception("❌ Error inesperado al agrupar los asientos.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################
############################################################################################################
############################################################################################################
### Aqui termina Airplane seats datos
############################################################################################################
############################################################################################################
############################################################################################################


############################################################################################################
############################################################################################################
############################################################################################################
### Aqui inicia Airplanes Routes datos
############################################################################################################
############################################################################################################
############################################################################################################


## Definición del esquema para validar los datos de las rutas de aviones
class AirplaneRouteSchema(Schema):
    class Meta:
        unknown = RAISE  # Error si hay campos no definidos

    airplane_route_id = fields.Int(required=True)
    airplane_id = fields.Int(required=True)
    flight_number = fields.Str(required=True)
    departure = fields.Str(required=True)
    departure_time = fields.Str(required=True)
    arrival = fields.Str(required=True)
    arrival_time = fields.Str(required=True)
    flight_time = fields.Str(dump_only=True)  # Se calcula, no se espera en entrada
    price = fields.Int(required=True)
    Moneda = fields.Str(required=True)

    VALID_MONEDAS = {'Dolares', 'Euros', 'Colones'}

    @validates("flight_number")
    def validar_flight_number(self, value):
        if not re.match(r"^[A-Z]{2}-\d{4}$", value):
            raise ValidationError("El número de vuelo debe tener el formato 'AA-1234'.")

    @validates("Moneda")
    def validar_moneda(self, value):
        if value not in self.VALID_MONEDAS:
            raise ValidationError(f"Moneda no válida. Use: {', '.join(self.VALID_MONEDAS)}")

    @validates("airplane_route_id")
    @validates("airplane_id")
    @validates("price")
    def validar_enteros_positivos(self, value):
        if not isinstance(value, int) or value <= 0:
            raise ValidationError("Debe ser un número entero positivo.")

    @validates("departure")
    @validates("arrival")
    def validar_no_vacios(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Este campo no puede estar vacío.")

    @validates("departure_time")
    @validates("arrival_time")
    def validar_fecha_formato_espanol(self, value):
        traducido = traducir_mes_espanol_a_ingles(value)
        try:
            parser.parse(traducido)
        except Exception:
            raise ValidationError("Formato de fecha inválido. Usa formato como: 'Marzo 30, 2025 - 16:46:19'")


############################################################################################################


airplane_route_schema = AirplaneRouteSchema()


# Definir los meses en español
meses_es = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


print()  # Salto de línea
print()  # Salto de línea

# Generar datos de rutas de aviones
airplanes_routes = []
used_airplane_ids = set()

# Lista de aviones disponibles
available_airplanes = [a['airplane_id'] for a in airplanes]  # ✅ dinámica según los datos actuales

random.shuffle(available_airplanes)  # Para que los airplane_id se asignen aleatoriamente

## Cantidad de rutas a generar (1 a 10) seria de 9 rutas, el 10 no se cuenta
for i in range(1, 4):  # Hasta 10 rutas como máximo si no se repite airplane_id
    if not available_airplanes:
        break  # No quedan aviones disponibles sin repetir

    airplane_id = available_airplanes.pop()  # Extraer uno único

    departure_time = fake_airplane.date_time_this_year()
    arrival_time = departure_time + timedelta(hours=random.randint(1, 12), minutes=random.randint(0, 59))

    def formatear_fecha(fecha):
        mes = meses_es[fecha.month]
        return f"{mes} {fecha.day}, {fecha.year} - {fecha.strftime('%H:%M:%S')}"

    duracion = arrival_time - departure_time
    horas, resto = divmod(duracion.total_seconds(), 3600)
    minutos = resto // 60
    flight_time = f"{int(horas)} horas {int(minutos)} minutos"

    airplanes_routes.append({
        'airplane_route_id': i,
        'airplane_id': airplane_id,
        'flight_number': generate_flight_number(),
        'departure': fake_airplane.airport_name(),
        'departure_time': formatear_fecha(departure_time),
        'arrival': fake_airplane.airport_name(),
        'arrival_time': formatear_fecha(arrival_time),
        'flight_time': flight_time,
        'price': fake_airplane.random_int(min=60000, max=150000),
        'Moneda': 'Colones'
    })


# Imprimir los datos generados
for route in airplanes_routes:
    print(route)


## REVISADO
############################################################################################################


# Configurar locale para formato español
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "es_ES")
    except locale.Error:
        locale.setlocale(locale.LC_TIME, "")


# Diccionario para traducir meses en español a inglés para parser
MESES_ES_A_EN = {
    "enero": "january", "febrero": "february", "marzo": "march",
    "abril": "april", "mayo": "may", "junio": "june",
    "julio": "july", "agosto": "august", "septiembre": "september",
    "octubre": "october", "noviembre": "november", "diciembre": "december"
}


# Función para traducir fecha con mes en español a inglés
def traducir_mes_espanol_a_ingles(fecha_str: str) -> str:
    for mes_es, mes_en in MESES_ES_A_EN.items():
        if mes_es in fecha_str.lower():
            return re.sub(mes_es, mes_en, fecha_str, flags=re.IGNORECASE)
    return fecha_str

def formatear_fecha(fecha: datetime) -> str:
    return fecha.strftime("%B %d, %Y - %H:%M:%S").capitalize()

def calcular_duracion(departure: datetime, arrival: datetime) -> str:
    duracion = arrival - departure
    horas, resto = divmod(duracion.total_seconds(), 3600)
    minutos = resto // 60
    return f"{int(horas)} horas {int(minutos)} minutos"

VALID_MONEDAS = {'Dolares', 'Euros', 'Colones'}

def validar_campos_vacios(data, campos):
    return [f for f in campos if not isinstance(data.get(f), str) or not data[f].strip()]


## Revisado 4-28 3:08 AM
## Agregar una nueva ruta de avión
@app.route('/add_airplane_route', methods=['POST'])
def add_airplane_route():
    """
    Summary: Agrega una nueva ruta de avión
    Description:
      Crea una nueva ruta de avión con los datos proporcionados.
      - Valida claves duplicadas en el JSON crudo.
      - Verifica que el avión exista.
      - Impide rutas duplicadas por ID, por número de vuelo o por todos los campos idénticos.
      - Comprueba que la hora de llegada sea posterior a la de salida.
      - Formatea las fechas y calcula la duración del vuelo.
    ---
    tags:
      - Routes
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        description: Objeto con los datos de la nueva ruta
        required: true
        schema:
          $ref: '#/definitions/AirplaneRouteSchema'
    responses:
      201:
        description: Ruta agregada con éxito
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: Ruta agregada con éxito
                route:
                  $ref: '#/definitions/AirplaneRouteSchema'
      400:
        description: Datos inválidos o duplicados
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    try:
        raw = request.data.decode('utf-8')
        # 1) Duplicados de clave JSON
        dup = detectar_claves_duplicadas(raw)
        if dup:
            return jsonify({
                'message': f"Se detectaron campos duplicados: {', '.join(dup)}",
                'errors': {}
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                'message': 'No se recibió ningún cuerpo JSON.',
                'errors': {}
            }), 400

        # 2) Deserializar y validar esquema
        route = airplane_route_schema.load(data)

        # 3) Verificar existencia de avión
        if not any(a['airplane_id'] == route['airplane_id'] for a in airplanes):
            return jsonify({
                'message': 'El avión especificado no existe.',
                'errors': {'airplane_id': [f"No existe avión con ID {route['airplane_id']}"]}
            }), 400

        # 4) Duplicados por ID o número de vuelo
        if any(r['airplane_route_id'] == route['airplane_route_id'] for r in airplanes_routes):
            return jsonify({
                'message': f"Ya existe una ruta con ID {route['airplane_route_id']}.",
                'errors': {'airplane_route_id': [f"Duplicado: {route['airplane_route_id']}"]}
            }), 400
        if any(r['flight_number'] == route['flight_number'] and r['airplane_id'] == route['airplane_id']
               for r in airplanes_routes):
            return jsonify({
                'message': f"Ya existe la ruta {route['flight_number']} para el avión {route['airplane_id']}.",
                'errors': {'flight_number': [f"Duplicado: {route['flight_number']}"]}
            }), 400
        if any(all(r.get(k) == route.get(k) for k in route) for r in airplanes_routes):
            existing = next(r for r in airplanes_routes if all(r.get(k) == route.get(k) for k in route))
            return jsonify({
                'message': 'Ya existe una ruta con todos los mismos datos.',
                'errors': {'airplane_route_id': [f"Ya registrada con ID {existing['airplane_route_id']}"]}
            }), 400

        # 5) Validar orden de fechas
        dep_str = traducir_mes_espanol_a_ingles(route['departure_time'])
        arr_str = traducir_mes_espanol_a_ingles(route['arrival_time'])
        dt_dep = parser.parse(dep_str)
        dt_arr = parser.parse(arr_str)
        if dt_arr <= dt_dep:
            return jsonify({
                'message': 'La hora de llegada debe ser posterior a la de salida.',
                'errors': {'arrival_time': ['<= departure_time']}
            }), 400

        # 6) Formatear fechas y duración
        route['departure_time'] = formatear_fecha(dt_dep)
        route['arrival_time'] = formatear_fecha(dt_arr)
        route['flight_time'] = calcular_duracion(dt_dep, dt_arr)

        # 7) Registrar y responder con mensaje de éxito
        airplanes_routes.append(route)
        logging.info(f"🛬 Ruta agregada: ID={route['airplane_route_id']}, Vuelo={route['flight_number']}, Avión={route['airplane_id']}")
        return jsonify({
            'message': 'Ruta agregada con éxito',
            'route': route
        }), 201

    except ValidationError as ve:
        return jsonify({
            'message': 'Error de validación',
            'errors': ve.messages
        }), 400

    except Exception:
        logging.exception("❌ Error inesperado al agregar ruta de avión.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################

## Revisado 4-28 3:08 AM
## Obtener todas las rutas de avión
@app.route('/get_all_airplanes_routes', methods=['GET'])
def get_airplanes_routes():
    """
    Summary: Obtiene todas las rutas de avión
    Description:
      Devuelve la lista de rutas de avión registradas en el sistema.
      Si no hay rutas registradas, devuelve un mensaje indicando que no hay registros.
    ---
    tags:
      - Routes
    responses:
      200:
        description: Lista de rutas obtenida correctamente
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/definitions/AirplaneRouteSchema'
      200:
        description: No hay rutas registradas actualmente
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: No hay rutas registradas actualmente.
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    try:
        # Verificar estructura de datos
        if not isinstance(airplanes_routes, list):
            logging.error("❌ 'airplanes_routes' no es una lista.")
            return jsonify({
                'message': 'Error interno: estructura de datos inválida.',
                'errors': {'airplanes_routes': ['Debe ser una lista.']}
            }), 500

        # Si no hay rutas registradas
        if not airplanes_routes:
            logging.info("📭 No hay rutas registradas actualmente.")
            return jsonify({'message': 'No hay rutas registradas actualmente.'}), 200

        # Validar y serializar usando Marshmallow
        schema = AirplaneRouteSchema(many=True)
        serialized = schema.dump(airplanes_routes)

        logging.info(f"📦 Se retornaron {len(serialized)} rutas de avión.")
        return jsonify(serialized), 200

    except Exception:
        logging.exception("❌ Error inesperado al obtener las rutas de avión.")
        return jsonify({
            'message': 'Error interno del servidor al obtener las rutas.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################
## Revisado 4-28 3:08 AM


## Obtener una ruta de avión por ID
@app.route('/get_airplanes_route_by_id/<int:airplane_route_id>', methods=['GET'])
def get_airplanes_route_by_id(airplane_route_id):
    """
    Summary: Obtiene una ruta de avión por su ID
    Description:
      Devuelve la ruta de avión identificada por `airplane_route_id`.
      - Si el ID es menor o igual a 0, devuelve un 400.
      - Si no se encuentra la ruta, devuelve un 404.
    ---
    tags:
      - Routes
    parameters:
      - name: airplane_route_id
        in: path
        description: ID único de la ruta de avión (entero positivo)
        required: true
        schema:
          type: integer
          minimum: 1
    responses:
      200:
        description: Ruta encontrada
        content:
          application/json:
            schema:
              $ref: '#/definitions/AirplaneRouteSchema'
      400:
        description: Parámetro inválido
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      404:
        description: Ruta no encontrada
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    try:
        # 1) Validar parámetro
        if airplane_route_id <= 0:
            return jsonify({
                'message': 'El ID de la ruta debe ser un entero positivo.',
                'errors': {'airplane_route_id': ['Debe ser mayor que cero.']}
            }), 400

        # 2) Verificar la estructura en memoria
        if not isinstance(airplanes_routes, list):
            logging.error("❌ 'airplanes_routes' no es una lista.")
            return jsonify({
                'message': 'Error interno: estructura de datos inválida.',
                'errors': {'airplanes_routes': ['Debe ser una lista.']}
            }), 500

        # 3) Búsqueda de la ruta
        route = next((r for r in airplanes_routes if r.get('airplane_route_id') == airplane_route_id), None)
        if not route:
            return jsonify({
                'message': f'Ruta con ID {airplane_route_id} no encontrada.',
                'errors': {}
            }), 404

        # 4) Serializar con Marshmallow
        serialized = AirplaneRouteSchema().dump(route)

        return jsonify(serialized), 200

    except ValidationError as err:
        # Aunque no debería ocurrir en dump, lo cubrimos por si acaso
        return jsonify({
            'message': 'Error al serializar la ruta.',
            'errors': err.messages
        }), 500

    except Exception:
        logging.exception("❌ Error inesperado al obtener la ruta de avión.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################
## Revisado 4-28 3:08 AM

## Actualizar una ruta de avión por airplane_route_id
@app.route('/update_airplane_route_by_id/<int:airplane_route_id>', methods=['PUT'])
def update_airplane_route_by_id(airplane_route_id):
    """
    Summary: Actualiza una ruta de avión existente
    Description:
      Modifica todos los datos de la ruta de avión identificada por `airplane_route_id`.
      - Si el ID no es un entero positivo, devuelve 400.
      - Si no se encuentra la ruta, devuelve 404.
      - No se permite cambiar `airplane_route_id` en el body.
      - Si el JSON contiene campos duplicados o extraños, devuelve 400.
      - Verifica que la hora de llegada sea posterior a la de salida.
      - Si no hay cambios reales, devuelve 200 sin modificar nada.
      - Devuelve la ruta actualizada en el cuerpo de la respuesta.
    ---
    tags:
      - Routes
    parameters:
      - name: airplane_route_id
        in: path
        type: integer
        required: true
        description: ID único de la ruta de avión (entero positivo)
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/AirplaneRouteSchema'
    responses:
      200:
        description: Ruta actualizada con éxito o sin cambios
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Ruta actualizada con éxito"
                route:
                  $ref: '#/definitions/AirplaneRouteSchema'
      400:
        description: Datos inválidos o parámetro erróneo
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      404:
        description: Ruta no encontrada
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    try:
        # 1) Validar parámetro
        if airplane_route_id <= 0:
            return jsonify({
                'message': 'El ID de la ruta debe ser un entero positivo.',
                'errors': {'airplane_route_id': ['Debe ser mayor que cero.']}
            }), 400

        # 2) Validar estructura en memoria
        if not isinstance(airplanes_routes, list):
            logging.error("❌ 'airplanes_routes' no es una lista.")
            return jsonify({
                'message': 'Error interno: estructura de datos inválida.',
                'errors': {'airplanes_routes': ['Debe ser una lista.']}
            }), 500

        # 3) Buscar la ruta a actualizar
        route = next((r for r in airplanes_routes if r.get('airplane_route_id') == airplane_route_id), None)
        if not route:
            return jsonify({
                'message': f'Ruta con ID {airplane_route_id} no encontrada.',
                'errors': {}
            }), 404

        # 4) Detectar claves duplicadas
        raw = request.data.decode('utf-8')
        dup = detectar_claves_duplicadas(raw)
        if dup:
            return jsonify({
                'message': f'Se detectaron campos duplicados en el JSON: {", ".join(dup)}',
                'errors': {k: ['Duplicado'] for k in dup}
            }), 400

        # 5) Parsear body
        data = request.get_json()
        if not data:
            return jsonify({
                'message': 'No se recibió ningún cuerpo JSON.',
                'errors': {}
            }), 400

        # 5a) Impedir cambio de ID en payload
        if 'airplane_route_id' in data and data['airplane_route_id'] != airplane_route_id:
            return jsonify({
                'message': 'No está permitido cambiar `airplane_route_id`.',
                'errors': {'airplane_route_id': ['Debe coincidir con el parámetro de ruta.']}
            }), 400

        # 6) Validar y deserializar con Marshmallow
        updated = AirplaneRouteSchema().load(data)

        # 7) Validar fecha y calcular duración
        dep_str = traducir_mes_espanol_a_ingles(updated['departure_time'])
        arr_str = traducir_mes_espanol_a_ingles(updated['arrival_time'])
        dt_dep = parser.parse(dep_str)
        dt_arr = parser.parse(arr_str)
        if dt_arr <= dt_dep:
            return jsonify({
                'message': 'La hora de llegada debe ser posterior a la de salida.',
                'errors': {'arrival_time': ['Debe ser posterior a departure_time.']}
            }), 400

        updated['departure_time'] = formatear_fecha(dt_dep)
        updated['arrival_time']   = formatear_fecha(dt_arr)
        updated['flight_time']    = calcular_duracion(dt_dep, dt_arr)

        # 8) Comprobar si no hay cambios reales
        keys_to_compare = [
            'airplane_id', 'flight_number', 'departure',
            'departure_time', 'arrival', 'arrival_time',
            'price', 'Moneda', 'flight_time'
        ]
        if all(route.get(k) == updated.get(k) for k in keys_to_compare):
            return jsonify({
                'message': 'No se realizaron cambios porque los datos son idénticos.',
                'route': AirplaneRouteSchema().dump(route)
            }), 200

        # 9) Aplicar cambios en memoria
        route.update(updated)
        logging.info(f"✏️ Ruta actualizada: ID={airplane_route_id}")

        # 10) Serializar para la respuesta
        result = AirplaneRouteSchema().dump(route)
        return jsonify({
            'message': 'Ruta actualizada con éxito',
            'route': result
        }), 200

    except ValidationError as err:
        return jsonify({
            'message': 'Error de validación de datos.',
            'errors': err.messages
        }), 400

    except Exception:
        logging.exception("❌ Error inesperado al actualizar la ruta de avión.")
        return jsonify({
            'message': 'Error interno del servidor.',
            'errors': {'exception': ['Ocurrió un error inesperado.']}
        }), 500


############################################################################################################


## Eliminar una ruta de avión por airplane_route_id
@app.route('/delete_airplane_route_by_id/<int:airplane_route_id>', methods=['DELETE'])
def delete_airplane_route_by_id(airplane_route_id):
    """
    Summary: Elimina una ruta de avión
    Description:
      Borra la ruta de avión identificada por `airplane_route_id`.
      - Si el ID no es un entero positivo, devuelve 400.
      - Si la ruta no existe, devuelve 404.
      - Si ocurre un error interno, devuelve 500.
    ---
    tags:
      - Routes
    parameters:
      - name: airplane_route_id
        in: path
        required: true
        description: ID único de la ruta de avión a eliminar (entero positivo)
        schema:
          type: integer
          minimum: 1
    responses:
      200:
        description: Ruta eliminada con éxito
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Ruta eliminada con éxito"
      400:
        description: Parámetro inválido
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      404:
        description: Ruta no encontrada
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
      500:
        description: Error interno del servidor
        content:
          application/json:
            schema:
              $ref: '#/definitions/ErrorSchema'
    """
    try:
        # 1) Validar que sea un entero positivo
        if airplane_route_id <= 0:
            return jsonify({
                "message": "El ID de la ruta debe ser un entero positivo.",
                "errors": {"airplane_route_id": ["Debe ser mayor que cero."]}
            }), 400

        # 2) Validar estructura interna
        if not isinstance(airplanes_routes, list):
            logging.error("❌ 'airplanes_routes' no es una lista.")
            return jsonify({
                "message": "Error interno: estructura de rutas inválida.",
                "errors": {"airplanes_routes": ["Debe ser una lista."]}
            }), 500

        # 3) Buscar la ruta
        route = next((r for r in airplanes_routes if r.get("airplane_route_id") == airplane_route_id), None)
        if not route:
            return jsonify({
                "message": f"Ruta con ID {airplane_route_id} no encontrada.",
                "errors": {}
            }), 404

        # 4) Eliminar
        airplanes_routes.remove(route)
        logging.info(f"🗑️ Ruta eliminada: ID={airplane_route_id}")

        # 5) Responder éxito
        return jsonify({"message": "Ruta eliminada con éxito"}), 200

    except Exception:
        logging.exception("❌ Error al eliminar la ruta de avión.")
        return jsonify({
            "message": "Error interno del servidor.",
            "errors": {"exception": ["Ocurrió un error inesperado."]}
        }), 500


############################################################################################################


####################################
####################################
### Aqui termina Airplanes Routes datos
####################################
####################################


## Actualizar el estado de un asiento específico
@app.route('/update_seat_status/<int:airplane_id>/seats/<string:seat_number>', methods=['PUT'])
def update_seat_status(airplane_id, seat_number):
    """
    Actualiza el estado de un asiento específico
    ---
    tags:
      - Airplanes Seats
    parameters:
      - name: airplane_id
        in: path
        type: integer
        required: true
        description: ID del avión
      - name: seat_number
        in: path
        type: string
        required: true
        description: "Número del asiento (ej: 12A)"
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [Libre, Reservado, Pagado]
              example: Reservado
    responses:
      200:
        description: Estado del asiento actualizado con éxito
      400:
        description: Solicitud inválida
      404:
        description: Asiento o avión no encontrado
    """
    try:
        # Validar que la lista de asientos sea válida
        if not isinstance(seats, list):
            return jsonify({"message": "Error interno: estructura de asientos inválida."}), 500

        # Validar que el avión exista
        if not any(a['airplane_id'] == airplane_id for a in airplanes):
            return jsonify({"message": f"Avión con ID {airplane_id} no existe."}), 404

        # Validar longitud del número de asiento
        if len(seat_number) > 5:
            return jsonify({"message": "El número de asiento es demasiado largo."}), 400

        # Prevenir keywords inválidas como ALL o *
        if seat_number.upper() in ["ALL", "*"]:
            return jsonify({"message": "No está permitido modificar todos los asientos en una sola solicitud."}), 400

        # Validar formato del número de asiento
        if not re.match(r"^\d+[A-F]$", seat_number.upper()):
            return jsonify({"message": "Formato de número de asiento inválido. Debe ser como '12A'."}), 400

        data = request.get_json()
        if not data:
            return jsonify({"message": "No se recibió cuerpo JSON."}), 400

        nuevo_estado = data.get("status")
        if nuevo_estado not in ["Libre", "Reservado", "Pagado"]:
            return jsonify({"message": "Estado inválido. Debe ser 'Libre', 'Reservado', 'Pagado'."}), 400

        # Buscar el asiento específico
        asiento = next(
            (s for s in seats if s["airplane_id"] == airplane_id and s["seat_number"] == seat_number.upper()),
            None
        )

        if not asiento:
            return jsonify({"message": f"Asiento {seat_number} no encontrado en el avión {airplane_id}."}), 404

        if asiento["status"] == nuevo_estado:
            return jsonify({"message": f"El asiento {seat_number} ya tenía el estado '{nuevo_estado}'."}), 200

        # Actualizar estado
        asiento["status"] = nuevo_estado

        # Log para auditoría
        logging.info(f"Estado del asiento {seat_number} en avión {airplane_id} actualizado a {nuevo_estado}")

        return jsonify({
            "message": f"Estado del asiento {seat_number} actualizado a {nuevo_estado}.",
            "asiento": asiento
        }), 200

    except Exception as e:
        logging.exception("Error al actualizar el estado del asiento.")
        return jsonify({"message": "Error interno del servidor"}), 500



def get_random_free_seat(airplane_id):
    """
    Devuelve un asiento libre aleatorio para el avión dado.
    Si no hay asientos disponibles, retorna un mensaje de advertencia.
    """
    try:
        if not isinstance(seats, list):
            logging.error("❌ La estructura de datos 'seats' no es válida (no es lista).")
            return None

        for seat in seats:
            if seat["airplane_id"] == airplane_id and seat["status"] == "Libre":
                logging.info(f"✅ Asiento libre encontrado: {seat['seat_number']} para avión {airplane_id}")
                return seat

        logging.info(f"⚠️ No hay asientos disponibles para el avión con ID {airplane_id}")
        return None

    except Exception as e:
        logging.exception("❌ Error al buscar asiento libre para el avión.")
        return None


@app.route('/get_random_free_seat/<int:airplane_id>', methods=['GET'])
def get_random_free_seat_endpoint(airplane_id):
    seat = get_random_free_seat(airplane_id)
    if seat:
        return jsonify(seat), 200
    return jsonify({'message': 'No hay asientos libres'}), 404


@app.route('/free_seat/<int:airplane_id>/seats/<string:seat_number>', methods=['PUT'])
def liberar_asiento(airplane_id, seat_number):
    try:
        # Validar estructuras de datos
        if not isinstance(seats, list):
            return jsonify({'message': 'Estructura de asientos inválida.'}), 500

        if not isinstance(airplanes, list):
            return jsonify({'message': 'Estructura de aviones inválida.'}), 500

        # Validar ID positivo
        if airplane_id <= 0:
            return jsonify({'message': 'El ID del avión debe ser positivo.'}), 400

        # Validar existencia del avión
        if not any(a['airplane_id'] == airplane_id for a in airplanes):
            return jsonify({'message': f"Avión con ID {airplane_id} no encontrado."}), 404

        # Buscar el asiento
        asiento = next((s for s in seats if s['airplane_id'] == airplane_id and s['seat_number'] == seat_number.upper()), None)
        if not asiento:
            return jsonify({'message': f"Asiento {seat_number} no encontrado en el avión {airplane_id}."}), 404

        # Si ya está libre
        if asiento["status"] == "Libre":
            return jsonify({'message': f"El asiento {seat_number} ya estaba libre."}), 200

        # Liberar asiento
        asiento["status"] = "Libre"
        logging.info(f"🟢 Asiento {seat_number} del avión {airplane_id} liberado exitosamente.")
        return jsonify({
            'message': f"Asiento {seat_number} en avión {airplane_id} fue liberado con éxito.",
            'asiento': asiento
        }), 200

    except Exception as e:
        logging.exception("❌ Error al liberar el asiento.")
        return jsonify({'message': 'Error interno del servidor'}), 500


# -----------------------------
# Manejadores globales de errores
# -----------------------------

@app.errorhandler(404)
def handle_not_found(e):
    """
    Manejador global para 404: rutas no encontradas.
    Devuelve JSON en lugar de la página HTML por defecto de Flask.
    """
    response = {
        'message': 'Endpoint no encontrado.',
        'errors': {}
    }
    return jsonify(response), 404


@app.errorhandler(405)
def handle_method_not_allowed(e):
    """
    Manejador global para 405: método no permitido.
    """
    response = {
        'message': 'Método HTTP no permitido para este endpoint.',
        'errors': {}
    }
    return jsonify(response), 405


# Iniciar la aplicación
if __name__ == '__main__':
    # Solo se ejecuta al correr el script directamente, no en recarga automática
    app.run(debug=True, port=5001)
