# Standard Library
import logging
import os
import random
import string
from datetime import datetime, timedelta
import re
import random
import string
from werkzeug.exceptions import BadRequest

# Third-party Libraries
import requests
from dotenv import load_dotenv
from faker import Faker
from faker_airtravel import AirTravelProvider
from flasgger import Swagger
from marshmallow import Schema, fields, ValidationError, RAISE

# Flask
from flask import Flask, jsonify, request


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
        "title": "Air Travel API: Módulo Gestión de Reservas",
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
            "name": "Reservations",
            "description": "Operaciones relacionadas con reservas de vuelos."
        },
        {
            "name": "Payments",
            "description": "Operaciones relacionadas con pagos de reservas."
        }
    ],
    "definitions": {
        "ReservationSchema": {
            "type": "object",
            "properties": {
                "passport_number": {
                    "type": "string",
                    "example": "A12345678"
                },
                "full_name": {
                    "type": "string",
                    "example": "Luis Gómez"
                },
                "email": {
                    "type": "string",
                    "example": "luis@example.com"
                },
                "phone_number": {
                    "type": "string",
                    "example": "+50688889999"
                },
                "emergency_contact_name": {
                    "type": "string",
                    "example": "Carlos Jiménez"
                },
                "emergency_contact_phone": {
                    "type": "string",
                    "example": "+50677778888"
                },
                "airplane_id": {
                    "type": "integer",
                    "example": 1
                },
                "airplane_route_id": {
                    "type": "integer",
                    "example": 10
                },
                "seat_number": {
                    "type": "string",
                    "example": "1A"
                },
                "status": {
                    "type": "string",
                    "enum": ["Reservado", "Pagado"],
                    "example": "Reservado"
                }
            },
            "required": [
                "passport_number",
                "full_name",
                "email",
                "phone_number",
                "emergency_contact_name",
                "emergency_contact_phone",
                "airplane_id",
                "airplane_route_id",
                "seat_number",
                "status"
            ]
        }
    }
}


## Configuración de Swagger
swagger = Swagger(app, template=swagger_template)


fake = Faker()
payments = []


####################################
####################################
## Aqui inicia Airplanes datos
####################################
####################################


## Generar datos de aviones falsos
fake_airplane = Faker()
## Añadir el proveedor de AirTravel a Faker
fake_airplane.add_provider(AirTravelProvider)


## Generar datos de reservaciones falsos
def generate_fake_reservations(n=3):
    generated = []
    existing_ids = set()

    gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE")
    rutas_url = f"{gestion_vuelos_url}/get_all_airplanes_routes"

    logging.info("🔄 Iniciando generación de reservas...")

    try:
        response = requests.get(rutas_url)
        if response.status_code != 200:
            logging.error(f"❌ No se pudo obtener rutas desde GestiónVuelos. Código: {response.status_code}")
            return generated

        routes = response.json()

        if not isinstance(routes, list):
            logging.error("❌ Formato inválido: se esperaba una lista de rutas, pero se recibió otro tipo.")
            return generated

        logging.info(f"✅ Se recibieron {len(routes)} rutas desde GestiónVuelos.")
    except Exception as e:
        logging.exception("❌ Conexión con GestiónVuelos fallida al obtener rutas.")
        return generated

    if not routes:
        logging.warning("⚠️ No hay rutas disponibles para generar reservas.")
        return generated

    random.shuffle(routes)

    while len(generated) < n and routes:
        route = routes.pop()
        airplane_id = route['airplane_id']
        flight_number = route['flight_number']
        airplane_route_id = route['airplane_route_id']
        route_id = route.get('route_id')  # ✅ Se toma el route_id si está presente
        price = route.get('price', 0.0)  # ✅ Se toma el precio si viene, o 0.0 por defecto
        logging.info(f"➡️ Procesando ruta para avión id {airplane_id} con código de vuelo {flight_number}")

        seat_url = f"{gestion_vuelos_url}/get_random_free_seat/{airplane_id}"
        try:
            seat_response = requests.get(seat_url)
            if seat_response.status_code != 200:
                logging.warning(f"⚠️ No se encontró asiento libre para avión id {airplane_id}")
                continue

            seat = seat_response.json()
            logging.info(f"🪑 Asiento libre encontrado: {seat['seat_number']} en avión id {airplane_id}")
        except Exception as e:
            logging.exception("❌ Error al obtener asiento libre desde GestiónVuelos.")
            continue

        update_seat_url = f"{gestion_vuelos_url}/update_seat_status/{airplane_id}/seats/{seat['seat_number']}"
        try:
            update_response = requests.put(update_seat_url, json={"status": "Reservado"})
            if update_response.status_code != 200:
                logging.warning(f"⚠️ No se pudo reservar el asiento {seat['seat_number']} en avión id {airplane_id}")
                continue
            logging.info(f"✅ Asiento {seat['seat_number']} marcado como 'Reservado'")
        except Exception as e:
            logging.exception("❌ Error al actualizar estado del asiento a 'Reservado'")
            continue

        reservation = {
            'reservation_id': len(generated) + 1,
            'reservation_code': generate_reservation_code(),
            'passport_number': generate_passport_number(),
            'full_name': fake.name(),
            'email': fake.email(),
            'phone_number': fake.phone_number(),
            'emergency_contact_name': fake.name(),
            'emergency_contact_phone': fake.phone_number(),
            'airplane_id': airplane_id,
            'flight_number': flight_number,
            'airplane_route_id': airplane_route_id,
            'seat_number': seat['seat_number'],
            'reservation_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': "Reservado",
            'price': price
        }

        generated.append(reservation)
        logging.info(f"✅ Reserva generada: ID {reservation['reservation_id']} para asiento {reservation['seat_number']} reservación {reservation['reservation_code']}")

    logging.info(f"🎉 Finalizada generación de reservas. Total generadas: {len(generated)}")
    return generated


## airplanes_reservations = []

# Imprimirlas para ver que estén correctas
# print("\n>> Reservas generadas:")
# for r in airplanes_reservations:
#  print(r)


## Otener todas las reservas generadas
@app.route('/get_fake_reservations', methods=['GET'])
def get_fake_reservations():
    """
    Summary: Obtiene todas las reservas generadas
    Description:
      Recupera todas las reservas de vuelo generadas en memoria.
      Si no hay reservas disponibles, retorna un estado 204 sin contenido.
    ---
    tags:
      - Reservations
    produces:
      - application/json
    responses:
      200:
        description: Lista completa de reservas generadas
        examples:
          application/json:
            [
              {
                "reservation_id": 1,
                "reservation_code": "ABC123",
                "passport_number": "A12345678",
                "full_name": "Luis Gómez",
                "email": "luis@example.com",
                "phone_number": "+50688889999",
                "emergency_contact_name": "Carlos Jiménez",
                "emergency_contact_phone": "+50677778888",
                "airplane_id": 1,
                "seat_number": "1A",
                "status": "Reservado",
                "issued_at": "Abril 9, 2025 - 16:55:12"
              }
            ]
      204:
        description: No hay reservas generadas actualmente
        examples:
          application/json:
            {
              "message": "No hay reservas generadas actualmente."
            }
    """
    if not reservations:
        return jsonify({'message': 'No hay reservas generadas actualmente.'}), 204

    return jsonify(reservations), 200


####################################
####################################
### Aqui termina Airplanes datos
####################################
####################################


class ReservationSchema(Schema):
    class Meta:
        unknown = RAISE

    reservation_id = fields.Int()
    airplane_id = fields.Int(required=True)
    airplane_route_id = fields.Int(required=True)
    flight_number = fields.Str()
    reservation_date = fields.Str()
    price = fields.Float()

    passport_number = fields.Str(required=True)
    full_name = fields.Str(required=True)
    email = fields.Email(required=True)
    phone_number = fields.Str(required=True)
    emergency_contact_name = fields.Str(required=True)
    emergency_contact_phone = fields.Str(required=True)
    seat_number = fields.Str(required=True)

    status = fields.Str(required=True, validate=lambda s: s in ["Reservado", "Pagado"])

    issued_at = fields.Str()
    reservation_code = fields.Str()  # ya no required


## Instancia del esquema de validación
reservation_schema = ReservationSchema()

# Lista en memoria
reservations = []


def generate_reservation_code():
    """Genera un código de reserva estilo ABC123"""
    letters = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=3))
    digits = ''.join(random.choices('23456789', k=3))
    return f"{letters}{digits}"


def generate_passport_number():
    """Genera un número de pasaporte simulado (ej. A12345678)"""
    letter = random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')
    numbers = ''.join(random.choices('0123456789', k=8))
    return f"{letter}{numbers}"


# Diccionario de meses en español
meses_es = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def formatear_fecha_espanol(fecha):
    """Devuelve la fecha en formato: Enero 13, 2025 - 19:00:00"""
    mes = meses_es[fecha.month]
    return f"{mes} {fecha.day}, {fecha.year} - {fecha.strftime('%H:%M:%S')}"


################################################################################################################
################################################################################################################
### Aqui empieza Reservations datos
################################################################################################################
################################################################################################################


## Obtener reservas por codigo de reserva y devolver la información de la reserva
@app.route('/get_reservation_by_code/<reservation_code>', methods=['GET'])
def get_reservation_by_code(reservation_code):
    """
    Summary: Obtiene una reserva por su código único
    Description:
      Recupera una reserva existente utilizando su reservation_code único.
      El código debe ser una cadena alfanumérica de 6 caracteres (ej. ABC123).
      También valida la estructura de la reserva usando Marshmallow.
    ---
    tags:
      - Reservations
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: reservation_code
        in: path
        type: string
        required: true
        description: Código único de la reserva (6 caracteres alfanuméricos)
        example: "ABC123"
    responses:
      200:
        description: Reserva encontrada y validada exitosamente
        examples:
          application/json:
            {
              "reservation_id": 1,
              "reservation_code": "ABC123",
              "passport_number": "A12345678",
              "full_name": "Luis Gómez",
              "email": "luis@example.com",
              "phone_number": "+50688889999",
              "emergency_contact_name": "Carlos Jiménez",
              "emergency_contact_phone": "+50677778888",
              "airplane_id": 1,
              "seat_number": "1A",
              "status": "Reservado",
              "issued_at": "Abril 9, 2025 - 16:55:12"
            }
      400:
        description: Código de reserva inválido
        examples:
          application/json:
            {
              "message": "El código de reserva debe ser un string alfanumérico de 6 caracteres."
            }
      404:
        description: Reserva no encontrada
        examples:
          application/json:
            {
              "message": "Reserva no encontrada"
            }
      500:
        description: Error interno del servidor o error de validación
        examples:
          application/json:
            {
              "message": "Error interno del servidor"
            }
    """
    try:
        logging.info(f"🔍 Solicitando reserva con código: {reservation_code}")

        # Validar que sea un string alfanumérico de 6 caracteres
        if not isinstance(reservation_code, str) or not re.match(r'^[A-Z0-9]{6}$', reservation_code.upper()):
            logging.warning("⚠️ Código de reserva inválido recibido.")
            return jsonify({'message': 'El código de reserva debe ser un string alfanumérico de 6 caracteres.'}), 400

        reservation = next((r for r in reservations if r.get('reservation_code') == reservation_code.upper()), None)
        if not reservation:
            return jsonify({'message': 'Reserva no encontrada'}), 404

        validated_reservation = reservation_schema.load(reservation)

        return jsonify(validated_reservation), 200

    except ValidationError as err:
        return jsonify({'message': 'Error de validación', 'errors': err.messages}), 500
    except Exception as e:
        logging.exception("❌ Error inesperado al validar la reserva por código.")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################################


## Obtener reservas por ID numérico y devolver la información de la reserva
@app.route('/get_reservation_by_id/<reservation_id>', methods=['GET'])
def get_reservation_by_id(reservation_id):
    """
    Summary: Obtiene una reserva por su ID numérico
    Description:
      Recupera una reserva existente utilizando su reservation_id único.
      Valida que el ID sea un número entero positivo mayor a cero.
      También valida la estructura de la reserva usando Marshmallow.
    ---
    tags:
      - Reservations
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: reservation_id
        in: path
        type: integer
        required: true
        description: ID numérico único de la reserva (debe ser mayor a cero)
        example: 7
    responses:
      200:
        description: Reserva encontrada y validada exitosamente
        examples:
          application/json:
            {
              "reservation_id": 7,
              "reservation_code": "DEF456",
              "passport_number": "B98765432",
              "full_name": "Ana Martínez",
              "email": "ana@example.com",
              "phone_number": "+50677776666",
              "emergency_contact_name": "Luis Pérez",
              "emergency_contact_phone": "+50666667777",
              "airplane_id": 2,
              "seat_number": "2B",
              "status": "Reservado",
              "issued_at": "Abril 15, 2025 - 12:30:00"
            }
      400:
        description: ID inválido proporcionado
        examples:
          application/json:
            {
              "message": "El ID de reserva debe ser un número entero positivo mayor que cero."
            }
      404:
        description: Reserva no encontrada
        examples:
          application/json:
            {
              "message": "Reserva no encontrada"
            }
      500:
        description: Error interno del servidor o error de validación
        examples:
          application/json:
            {
              "message": "Error interno del servidor"
            }
    """
    try:
        logging.info(f"🔍 Solicitando reserva con ID: {reservation_id}")

        # Validar si reservation_id es realmente un entero
        try:
            reservation_id = int(reservation_id)
        except (ValueError, TypeError):
            logging.warning("⚠️ Se recibió un reservation_id no numérico.")
            return jsonify({'message': 'El ID de reserva debe ser un número entero positivo.'}), 400

        if reservation_id <= 0:
            logging.warning("⚠️ ID de reserva inválido (negativo o cero).")
            return jsonify({'message': 'El ID de reserva debe ser un número positivo mayor que cero.'}), 400

        reservation = next((r for r in reservations if r.get('reservation_id') == reservation_id), None)
        if not reservation:
            return jsonify({'message': 'Reserva no encontrada'}), 404

        validated_reservation = reservation_schema.load(reservation)

        return jsonify(validated_reservation), 200

    except ValidationError as err:
        return jsonify({'message': 'Error de validación', 'errors': err.messages}), 500
    except Exception as e:
        logging.exception("❌ Error inesperado al validar la reserva.")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################################


## Eliminar una reserva por su ID y liberar el asiento asociado llamando a GESTIONVUELOS
## y devolver la información de la reserva eliminada
@app.route('/delete_reservation_by_id/<int:reservation_id>', methods=['DELETE'])
def delete_reservation_by_id(reservation_id):
    """
    Summary: Elimina o cancela una reserva existente
    Description:
      Elimina una reserva por su ID y libera automáticamente el asiento asociado llamando al microservicio GestiónVuelos.
      Si el ID no existe, la estructura es inválida, o el asiento no se puede liberar, se devuelve el error correspondiente.
    ---
    tags:
      - Reservations
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: reservation_id
        in: path
        description: ID numérico de la reserva que se desea eliminar
        required: true
        type: integer
        minimum: 1
        example: 5
    responses:
      200:
        description: Reserva eliminada con éxito y asiento liberado
        examples:
          application/json:
            {
              "message": "Reserva eliminada exitosamente",
              "deleted_reservation": {
                "reservation_id": 5,
                "reservation_code": "DEF456",
                "passport_number": "B98765432",
                "full_name": "Carlos López",
                "email": "carlos@example.com",
                "phone_number": "+50611112222",
                "emergency_contact_name": "María Fernández",
                "emergency_contact_phone": "+50633334444",
                "airplane_id": 2,
                "seat_number": "2B",
                "status": "Reservado",
                "issued_at": "Abril 10, 2025 - 12:00:00"
              }
            }
      400:
        description: ID inválido o estructura incorrecta
        examples:
          application/json:
            {
              "message": "El ID de reserva debe ser un número positivo."
            }
      404:
        description: Reserva no encontrada
        examples:
          application/json:
            {
              "message": "Reserva no encontrada"
            }
      503:
        description: Servicio de GestiónVuelos no disponible
        examples:
          application/json:
            {
              "message": "No se pudo conectar con GestiónVuelos para liberar el asiento."
            }
      504:
        description: Timeout al contactar GestiónVuelos
        examples:
          application/json:
            {
              "message": "Timeout al intentar liberar el asiento en GestiónVuelos."
            }
      500:
        description: Error interno del servidor
        examples:
          application/json:
            {
              "message": "Error interno del servidor"
            }
    """
    try:
        logging.info(f"🔄 Solicitud para eliminar reserva ID: {reservation_id}")

        if not isinstance(reservation_id, int) or reservation_id <= 0:
            return jsonify({'message': 'El ID de reserva debe ser un número positivo.'}), 400

        if not isinstance(reservations, list):
            return jsonify({'message': 'Estructura de datos inválida para reservas.'}), 500

        reservation = next((r for r in reservations if r['reservation_id'] == reservation_id), None)
        if not reservation:
            return jsonify({'message': 'Reserva no encontrada'}), 404

        # Validar la estructura básica con Marshmallow
        try:
            reservation_schema.load(reservation, partial=True)
        except ValidationError as err:
            return jsonify({'message': 'Error de validación', 'errors': err.messages}), 500

        airplane_id = reservation['airplane_id']
        seat_number = reservation['seat_number']

        # Eliminar la reserva de memoria
        reservations.remove(reservation)
        logging.info(f"✅ Reserva con ID {reservation_id} eliminada correctamente.")

        # Llamar al microservicio GestiónVuelos para liberar el asiento
        gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE")
        liberar_url = f"{gestion_vuelos_url}/free_seat/{airplane_id}/seats/{seat_number}"

        try:
            response = requests.put(liberar_url, timeout=5)
            if response.status_code == 200:
                logging.info(f"🪑 Asiento {seat_number} del avión {airplane_id} liberado exitosamente en GestiónVuelos.")
            else:
                logging.warning(f"⚠️ GestiónVuelos devolvió error al liberar asiento {seat_number}: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            logging.error("❌ No se pudo conectar con GestiónVuelos al liberar asiento.")
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos para liberar el asiento.'}), 503
        except requests.exceptions.Timeout:
            logging.error("⏰ Timeout al intentar liberar asiento en GestiónVuelos.")
            return jsonify({'message': 'Timeout al intentar liberar el asiento en GestiónVuelos.'}), 504

        return jsonify({
            'message': 'Reserva eliminada exitosamente',
            'deleted_reservation': reservation
        }), 200

    except Exception as e:
        logging.exception("❌ Error inesperado al eliminar la reserva.")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################################


## Crear una nueva reserva de vuelo
@app.route('/add_reservation', methods=['POST'])
def add_reservation():
    """
    Summary: Crea una nueva reserva de vuelo
    Description:
      Crea una nueva reserva de vuelo y marca el asiento como reservado.
      Valida que la ruta (airplane_route_id) exista y esté asociada al airplane_id.
      El reservation_code, issued_at y reservation_id se generan automáticamente.
      Falla si la ruta no existe o no coincide con el avión, el asiento ya está
      reservado o si hay problemas de conexión/timeout con GestiónVuelos.
    ---
    tags:
      - Reservations
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Datos de la nueva reserva
        required: true
        schema:
          $ref: '#/definitions/ReservationSchema'
    responses:
      201:
        description: Reserva creada con éxito
      400:
        description: Datos inválidos, ruta/avión no coinciden o asiento inexistente
      409:
        description: Asiento ya reservado
      503:
        description: Servicio de GestiónVuelos no disponible
      504:
        description: Timeout al contactar GestiónVuelos
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No se recibió cuerpo JSON'}), 400

        # 1) Validar payload contra el schema
        validated = reservation_schema.load(data)
        airplane_id       = validated['airplane_id']
        route_id          = validated['airplane_route_id']
        seat_number       = validated['seat_number']

        gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE", "http://localhost:5001")
        logging.info(f"🔗 Conectando a GestiónVuelos en: {gestion_vuelos_url}")

        # 2) Validar que la ruta exista y esté asociada al avión
        try:
            routes_resp = requests.get(
                f"{gestion_vuelos_url}/get_all_airplanes_routes",
                timeout=20
            )
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos al obtener rutas.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al obtener rutas en GestiónVuelos.'}), 504

        if routes_resp.status_code != 200:
            return jsonify({'message': 'Error al obtener rutas desde GestiónVuelos.'}), 500

        routes = routes_resp.json()
        route = next((r for r in routes if r.get('airplane_route_id') == route_id), None)
        if not route:
            return jsonify({'message': f'Ruta con ID {route_id} no encontrada.'}), 400
        if route.get('airplane_id') != airplane_id:
            return jsonify({
                'message': f'La ruta {route_id} no está asociada al avión {airplane_id}.'
            }), 400

        # 3) Comprobar que el asiento exista y esté libre
        try:
            seats_resp = requests.get(
                f"{gestion_vuelos_url}/get_airplane_seats/{airplane_id}/seats",
                timeout=20
            )
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos para verificar asiento.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al verificar asiento en GestiónVuelos.'}), 504

        if seats_resp.status_code != 200:
            return jsonify({'message': 'Error al verificar estado de asientos.'}), 500

        seats = seats_resp.json()
        asiento = next((s for s in seats if s['seat_number'] == seat_number), None)
        if not asiento:
            return jsonify({'message': 'El asiento especificado no existe para ese avión.'}), 400
        if asiento['status'] != 'Libre':
            return jsonify({'message': f"El asiento {seat_number} no está disponible."}), 409

        # 4) Generar reservation_code, issued_at, reservation_id
        validated['reservation_code'] = generar_codigo_reserva_unico()
        validated['issued_at']        = formatear_fecha_espanol(datetime.now())
        validated['reservation_id']   = len(reservations) + 1

        # 5) Marcar asiento como "Reservado"
        try:
            reserve_resp = requests.put(
                f"{gestion_vuelos_url}/update_seat_status/{airplane_id}/seats/{seat_number}",
                json={"status": "Reservado"},
                timeout=20
            )
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos al reservar asiento.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al reservar asiento en GestiónVuelos.'}), 504

        if reserve_resp.status_code != 200:
            return jsonify({'message': f"No se pudo reservar el asiento {seat_number}."}), 500

        # 6) Guardar la reserva en memoria
        reservations.append(validated)
        logging.info(f"✅ Reserva creada exitosamente: {validated}")

        return jsonify({
            "message": "Reserva creada exitosamente",
            "reservation": validated
        }), 201

    except ValidationError as err:
        logging.error(f"❌ Error de validación: {err.messages}")
        return jsonify({'message': 'Error de validación', 'errors': err.messages}), 400
    except Exception:
        logging.exception("❌ Error inesperado al crear reserva.")
        return jsonify({'message': 'Error interno del servidor'}), 500


def generar_codigo_reserva_unico():
    while True:
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not any(r['reservation_code'] == codigo for r in reservations):
            return codigo


######################################################################################################


@app.route('/reservations/<string:reservation_code>', methods=['PUT'])
def edit_reservation(reservation_code):
    """
    Summary: Modifica una reserva existente
    Description:
      Permite actualizar el asiento (si está libre) y/o datos de contacto de una reserva ya creada.
      Valida que el código de reserva exista y que los datos entrantes sean válidos.
      Si se cambia el asiento, se libera el anterior y se reserva el nuevo únicamente si su estado es 'Libre'.
      El body debe contener exactamente estos cinco campos: seat_number, email, phone_number,
      emergency_contact_name y emergency_contact_phone.
    ---
    tags:
      - Reservations
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: reservation_code
        in: path
        type: string
        required: true
        description: Código alfanumérico de 6 caracteres de la reserva (ej. ABC123)
      - in: body
        name: body
        required: true
        description: Debe incluir exactamente estos campos para actualizar la reserva
        schema:
          type: object
          properties:
            seat_number:
              type: string
              example: "2C"
            email:
              type: string
              example: "nuevo@example.com"
            phone_number:
              type: string
              example: "+50612345678"
            emergency_contact_name:
              type: string
              example: "Nuevo Contacto"
            emergency_contact_phone:
              type: string
              example: "+50687654321"
    responses:
      200:
        description: Reserva y datos actualizados exitosamente o sin cambios
      400:
        description: Código inválido o body inválido (faltan o sobran campos)
      404:
        description: Reserva no encontrada
      409:
        description: El nuevo asiento no está libre
      503:
        description: No se pudo conectar con GestiónVuelos
      504:
        description: Timeout al contactar a GestiónVuelos
      500:
        description: Error interno del servidor
    """
    # 1) Normalizar y validar el código
    code = reservation_code.strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{6}', code):
        return jsonify({'message': 'El código de reserva debe ser 6 caracteres alfanuméricos.'}), 400

    # 2) Buscar la reserva
    reservation = next((r for r in reservations if r['reservation_code'] == code), None)
    if not reservation:
        return jsonify({'message': 'Reserva no encontrada'}), 404

    # 3) Obtener y validar el body
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No se recibió cuerpo JSON.'}), 400

    allowed = {'seat_number', 'email', 'phone_number', 'emergency_contact_name', 'emergency_contact_phone'}
    received = set(data.keys())

    # 4) Asegurar que no falte ni sobre ningún campo
    if received != allowed:
        return jsonify({
            'message': 'El body debe incluir exactamente estos campos sin extras ni faltantes: '
                       'seat_number, email, phone_number, emergency_contact_name, emergency_contact_phone.'
        }), 400

    # 5) Comprobar si la información es idéntica
    identical = all(data[field] == reservation.get(field) for field in allowed)
    if identical:
        return jsonify({'message': 'La información es idéntica; no se realizaron cambios.'}), 200

    gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE")

    # 6) Si cambian de asiento, gestionar liberación y reserva del nuevo
    new_seat = data['seat_number']
    if new_seat != reservation['seat_number']:
        airplane_id = reservation['airplane_id']

        # 6.a) Consultar disponibilidad del nuevo asiento
        try:
            status_resp = requests.get(
                f"{gestion_vuelos_url}/get_airplane_seats/{airplane_id}/seats",
                timeout=5
            )
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos para verificar asiento.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al verificar asiento en GestiónVuelos.'}), 504

        if status_resp.status_code != 200:
            return jsonify({'message': 'Error verificando estado de los asientos.'}), 500

        seats = status_resp.json()
        seat_info = next((s for s in seats if s['seat_number'] == new_seat), None)
        if not seat_info:
            return jsonify({'message': f"Asiento {new_seat} no existe en el avión."}), 400
        if seat_info['status'] != 'Libre':
            return jsonify({'message': f"El asiento {new_seat} no está libre."}), 409

        # 6.b) Liberar asiento anterior
        old_seat = reservation['seat_number']
        try:
            free_resp = requests.put(
                f"{gestion_vuelos_url}/free_seat/{airplane_id}/seats/{old_seat}",
                timeout=5
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return jsonify({'message': 'Error liberando el asiento anterior en GestiónVuelos.'}), 503

        if free_resp.status_code != 200:
            return jsonify({'message': 'No se pudo liberar el asiento anterior.'}), 500

        # 6.c) Reservar el nuevo asiento
        try:
            reserve_resp = requests.put(
                f"{gestion_vuelos_url}/update_seat_status/{airplane_id}/seats/{new_seat}",
                json={"status": "Reservado"},
                timeout=5
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return jsonify({'message': 'Error reservando el nuevo asiento en GestiónVuelos.'}), 503

        if reserve_resp.status_code not in (200, 204):
            return jsonify({'message': f"No se pudo reservar el nuevo asiento {new_seat}."}), 500

        reservation['seat_number'] = new_seat

    # 7) Actualizar los demás campos de contacto
    for field in ['email', 'phone_number', 'emergency_contact_name', 'emergency_contact_phone']:
        reservation[field] = data[field]

    # 8) Validar con Marshmallow
    try:
        validated = reservation_schema.load(reservation)
    except ValidationError as err:
        return jsonify({'message': 'Error de validación', 'errors': err.messages}), 400

    # 9) Respuesta de éxito
    return jsonify({
        'message': 'Reserva y datos actualizados exitosamente',
        'reservation': validated
    }), 200


############################################################################################################
############################################################################################################
############################################################################################################
### Aqui termina Reservations datos
############################################################################################################
############################################################################################################
############################################################################################################


############################################################################################################
############################################################################################################
############################################################################################################
### Aqui Inicia Pagos datos
############################################################################################################
############################################################################################################
############################################################################################################


def generate_fake_payments(max_pagados=None):
    """
    Genera pagos falsos únicos para algunas o todas las reservas existentes,
    actualiza el estado de la reserva a 'Pagado' y llama a GESTIONVUELOS
    para cambiar el estado del asiento a 'Pagado'.
    """
    if not isinstance(reservations, list) or not reservations:
        logging.warning("⚠️ No hay reservas disponibles para generar pagos.")
        return []

    total_reservas = len(reservations)
    cantidad = max_pagados if isinstance(max_pagados, int) and 0 < max_pagados <= total_reservas else total_reservas

    reservas_seleccionadas = random.sample(reservations, cantidad)
    fake_payments = []
    used_ids = set()
    gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE")

    for reserva in reservas_seleccionadas:
        reservation_id = reserva.get("reservation_id")
        price = reserva.get("price", 0.0)
        airplane_id = reserva.get("airplane_id")
        seat_number = reserva.get("seat_number")

        # Generar ID único de pago
        while True:
            payment_id = f"PAY{random.randint(100000, 999999)}"
            if payment_id not in used_ids:
                used_ids.add(payment_id)
                break

        # ✅ Actualizar estado de la reserva
        reserva["status"] = "Pagado"

        # ✅ Llamar al microservicio para actualizar el estado del asiento
        try:
            update_url = f"{gestion_vuelos_url}/update_seat_status/{airplane_id}/seats/{seat_number}"
            update_response = requests.put(update_url, json={"status": "Pagado"})
            if update_response.status_code == 200:
                logging.info(f"🛫 Asiento {seat_number} del avión {airplane_id} marcado como 'Pagado' en GESTIONVUELOS.")
            else:
                logging.warning(f"⚠️ No se pudo actualizar asiento {seat_number} en avión {airplane_id}: {update_response.status_code}")
        except Exception as e:
            logging.exception(f"❌ Error al llamar al microservicio GESTIONVUELOS para el asiento {seat_number}")

        payment_info = {
            "payment_id": payment_id,
            "reservation_id": reservation_id,
            "amount": price,
            "currency": random.choice(["USD", "CRC"]),
            "payment_method": random.choice(["Tarjeta", "PayPal", "Transferencia"]),
            "status": "Pagado",
            "payment_date": formatear_fecha_espanol(datetime.now()),
            "transaction_reference": ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        }

        full_payment_record = {**payment_info, **reserva}
        fake_payments.append(full_payment_record)

    logging.info(f"💳 Se generaron {len(fake_payments)} pagos con actualización remota de asiento.")
    return fake_payments


#####################################################################################################


## Lista en memoria para pagos falsos
@app.route('/get_all_fake_payments', methods=['GET'])
def get_all_fake_payments():
    """
    Summary: Lista todos los pagos generados falsamente
    Description:
      Devuelve una lista de pagos simulados almacenados en memoria, útiles para pruebas o demostraciones.
      Si no hay pagos generados, se devuelve un mensaje indicando la ausencia de registros.
    ---
    tags:
      - Payments
    produces:
      - application/json
    responses:
      200:
        description: Lista de pagos en memoria o mensaje de que no hay pagos
        examples:
          application/json:
            [
              {
                "payment_id": "PAY123456",
                "reservation_id": 1,
                "amount": 385.25,
                "currency": "USD",
                "payment_method": "Tarjeta",
                "status": "Pagado",
                "payment_date": "Abril 16, 2025 - 15:22:00",
                "transaction_reference": "X8GJ9KL23RT7"
              }
            ]
          application/json:
            {
              "message": "No hay pagos generados actualmente."
            }
    """
    if not payments:
        return jsonify({'message': 'No hay pagos generados actualmente.'}), 200
    return jsonify(payments), 200


#####################################################################################################


## Obtener un pago específico por su payment_id y devolver la información del pago
## y el pago en sí
@app.route('/get_payment_by_id/<string:payment_id>', methods=['GET'])
def get_payment_by_id(payment_id):
    """
    Summary: Obtiene un pago específico por su ID
    Description:
      Recupera los detalles de un pago utilizando el payment_id proporcionado.
      Valida que el ID cumpla con el formato 'PAY' seguido de 6 dígitos (ej: PAY123456).
      Si el pago no existe o la estructura de datos es inválida, se devuelve el error correspondiente.
    ---
    tags:
      - Payments
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: payment_id
        in: path
        type: string
        required: true
        description: ID único del pago, en el formato 'PAY123456'
        example: PAY123456
    responses:
      200:
        description: Pago encontrado exitosamente
        examples:
          application/json:
            {
              "payment_id": "PAY123456",
              "reservation_id": 1,
              "amount": 150.0,
              "currency": "Dolares",
              "payment_method": "Tarjeta",
              "status": "Pagado",
              "payment_date": "Abril 29, 2025 - 13:00:00",
              "transaction_reference": "X1Y2Z3A4B5C6"
            }
      400:
        description: Formato de payment_id inválido
        examples:
          application/json:
            {
              "message": "El formato del payment_id es inválido. Debe ser como PAY123456"
            }
      404:
        description: No se encontró el pago
        examples:
          application/json:
            {
              "message": "No se encontró ningún pago con ID: PAY654321"
            }
      500:
        description: Error interno del servidor o estructura inválida
        examples:
          application/json:
            {
              "message": "Estructura de pagos inválida."
            }
    """
    logging.info(f"🔍 Buscando pago con ID: {payment_id}")

    # Validación 1: Formato correcto del payment_id
    if not re.match(r"^PAY\d{6}$", payment_id.strip().upper()):
        return jsonify({'message': 'El formato del payment_id es inválido. Debe ser como PAY123456'}), 400

    # Validación 2: Asegurar que payments sea una lista
    if not isinstance(payments, list):
        logging.error("❌ Estructura de pagos inválida: no es una lista.")
        return jsonify({'message': 'Estructura de pagos inválida.'}), 500

    # Validación 4: Si no hay pagos aún
    if not payments:
        logging.warning("⚠️ No hay pagos generados en memoria.")
        return jsonify({'message': 'No hay pagos generados aún.'}), 404

    # Buscar el pago
    payment = next((p for p in payments if p['payment_id'] == payment_id), None)

    if payment:
        return jsonify(payment), 200

    return jsonify({'message': f'No se encontró ningún pago con ID: {payment_id}'}), 404


#####################################################################################################


## Eliminar un pago específico por su payment_id y devolver la información de la reserva asociada
@app.route('/delete_payment_by_id/<string:payment_id>', methods=['DELETE'])
def delete_payment_by_id(payment_id):
    """
    Elimina un pago específico por su payment_id
    ---
    tags:
      - Payments
    parameters:
      - name: payment_id
        in: path
        type: string
        required: true
        description: ID único del pago
    responses:
      200:
        description: Pago eliminado con éxito
      400:
        description: Formato inválido o estructura incorrecta
      404:
        description: Pago no encontrado
      500:
        description: Error interno del servidor
    """

    logging.info(f"🗑️ Solicitud para eliminar el pago con ID: {payment_id}")

    # Validación 1: Formato correcto
    if not re.match(r"^PAY\d{6}$", payment_id.strip().upper()):
        return jsonify({'message': 'El formato del payment_id es inválido. Debe ser como PAY123456'}), 400

    # Validación 2: Estructura correcta de datos
    if not isinstance(payments, list):
        logging.error("❌ Estructura de datos de pagos inválida.")
        return jsonify({'message': 'Estructura de pagos inválida.'}), 500

    # Validación 3: Buscar el pago
    payment = next((p for p in payments if p['payment_id'] == payment_id), None)
    if not payment:
        logging.warning(f"⚠️ No se encontró ningún pago con ID: {payment_id}")
        return jsonify({'message': f'No se encontró ningún pago con ID: {payment_id}'}), 404

    # Eliminar
    payments.remove(payment)
    logging.info(f"✅ Pago con ID {payment_id} eliminado correctamente.")

    return jsonify({'message': f'El pago con ID {payment_id} fue eliminado con éxito.'}), 200


#####################################################################################################


## Crear un nuevo pago para una reserva existente y actualizar el estado de la reserva a 'Pagado'
## y notificar a GESTIONVUELOS para marcar el asiento como 'Pagado'
@app.route('/create_payment', methods=['POST'])
def create_payment():
    """
    Summary: Crea un nuevo pago para una reserva existente
    Description:
      Registra un pago asociado a una reserva existente en el sistema.
      Verifica que la reserva exista, que no tenga ya un pago registrado,
      y genera automáticamente un ID único de pago y la referencia de transacción.
      Actualiza el estado de la reserva a 'Pagado' y notifica a GestiónVuelos
      para que también marque el asiento como 'Pagado'.
      El pago se almacena en memoria.
    ---
    tags:
      - Payments
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        description: Datos requeridos para registrar el pago
        schema:
          type: object
          required:
            - reservation_id
            - payment_method
          properties:
            reservation_id:
              type: integer
              example: 1
              description: ID único de la reserva a pagar
            payment_method:
              type: string
              enum: ["Tarjeta", "PayPal", "Transferencia"]
              example: "Tarjeta"
              description: Método utilizado para efectuar el pago
            currency:
              type: string
              enum: ["Dolares", "Colones"]
              example: "Dolares"
              description: Moneda utilizada para el pago

    responses:
      201:
        description: Pago registrado exitosamente
      400:
        description: Datos inválidos proporcionados
      404:
        description: Reserva no encontrada
      409:
        description: Pago duplicado para la misma reserva
      503:
        description: Servicio de GestiónVuelos no disponible
      504:
        description: Timeout al contactar GestiónVuelos
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()
        reservation_id = data.get("reservation_id")
        payment_method = data.get("payment_method")
        currency = data.get("currency", "USD")

        # Validación básica
        if not isinstance(reservation_id, int) or reservation_id <= 0:
            return jsonify({'message': 'El reservation_id debe ser un número entero positivo.'}), 400

        if payment_method not in ["Tarjeta", "PayPal", "Transferencia"]:
            return jsonify({'message': 'Método de pago inválido.'}), 400

        if currency not in ["Dolares", "Colones"]:
            return jsonify({'message': 'Moneda no soportada.'}), 400

        # Validar existencia de reserva
        reserva = next((r for r in reservations if r['reservation_id'] == reservation_id), None)
        if not reserva:
            return jsonify({'message': f'Reserva con ID {reservation_id} no encontrada.'}), 404

        # Validar que no haya pago duplicado para esta reserva
        if any(p.get("reservation_id") == reservation_id for p in payments):
            return jsonify({'message': 'Esta reserva ya tiene un pago registrado.'}), 409

        # Generar ID único de pago
        while True:
            payment_id = f"PAY{random.randint(100000, 999999)}"
            if not any(p.get("payment_id") == payment_id for p in payments):
                break

        # 1) Actualizar estado de la reserva a 'Pagado'
        reserva['status'] = "Pagado"

        # 2) Notificar a GestiónVuelos para marcar el asiento como 'Pagado'
        gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE")
        airplane_id = reserva['airplane_id']
        seat_number = reserva['seat_number']
        try:
            vuelo_resp = requests.put(
                f"{gestion_vuelos_url}/update_seat_status/{airplane_id}/seats/{seat_number}",
                json={"status": "Pagado"},
                timeout=5
            )
            if vuelo_resp.status_code != 200:
                logging.warning(f"⚠️ GestiónVuelos devolvió {vuelo_resp.status_code} al marcar asiento {seat_number} como Pagado.")
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos para actualizar estado del asiento.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al actualizar asiento en GestiónVuelos.'}), 504

        # 3) Crear el pago, incluyendo la reserva ya actualizada
        payment = {
            **reserva,
            "payment_id": payment_id,
            "reservation_id": reservation_id,
            "amount": reserva.get("price", 0.0),
            "currency": currency,
            "payment_method": payment_method,
            "status": "Pagado",
            "payment_date": formatear_fecha_espanol(datetime.now()),
            "transaction_reference": ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        }
        payments.append(payment)

        return jsonify({
            "message": "✅ Pago registrado correctamente.",
            "payment": payment
        }), 201

    except Exception:
        logging.exception("❌ Error al crear el pago.")
        return jsonify({'message': 'Error interno del servidor'}), 500


############################################################################################################


## Eliminar un pago y liberar el asiento asociado y devolver la información de la reserva asociada
## y el pago en sí
@app.route('/cancel_payment_and_reservation/<string:payment_id>', methods=['DELETE'])
def cancel_payment_and_reservation(payment_id):
    """
    Cancelación activa por parte del cliente: elimina el pago, la reserva asociada
    y libera el asiento en el avión.
    ---
    tags:
      - Payments
    parameters:
      - name: payment_id
        in: path
        type: string
        required: true
        description: ID único del pago (formato PAY123456)
    responses:
      200:
        description: "Cancelación exitosa. Se eliminó el pago y la reserva. El asiento fue liberado."
        schema:
          type: object
          properties:
            message:
              type: string
            deleted_payment:
              type: object
            deleted_reservation:
              type: object
      400:
        description: "Formato inválido"
      404:
        description: "Pago no encontrado o datos incompletos"
      500:
        description: "Error interno al liberar el asiento o procesar la cancelación"
    """

    logging.info(f"🚨 Solicitud de cancelación completa recibida para el pago: {payment_id}")

    # Validación del formato
    if not re.match(r"^PAY\d{6}$", payment_id.strip().upper()):
        return jsonify({'message': 'El formato del payment_id es inválido. Debe ser como PAY123456'}), 400

    # Buscar el pago
    payment = next((p for p in payments if p['payment_id'] == payment_id), None)
    if not payment:
        return jsonify({'message': f'No se encontró el pago con ID: {payment_id}'}), 404

    reservation_id = payment.get("reservation_id")
    airplane_id = payment.get("airplane_id")
    seat_number = payment.get("seat_number")

    if not reservation_id or not airplane_id or not seat_number:
        return jsonify({'message': 'El pago no tiene los datos completos para liberar la reserva'}), 404

    # 🔄 Primero liberar el asiento
    try:
        gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE")
        liberar_url = f"{gestion_vuelos_url}/free_seat/{airplane_id}/seats/{seat_number}"
        response = requests.put(liberar_url)

        if response.status_code != 200:
            logging.warning(f"⚠️ No se pudo liberar el asiento {seat_number}. Código: {response.status_code}")
            return jsonify({'message': 'No se pudo liberar el asiento en GestiónVuelos.'}), 500

        logging.info(f"🪑 Asiento {seat_number} del avión {airplane_id} fue liberado exitosamente.")

    except Exception as e:
        logging.exception("❌ Error al intentar liberar el asiento en GestiónVuelos.")
        return jsonify({'message': 'Error interno al liberar el asiento'}), 500

    # ✅ Luego eliminar el pago
    payments.remove(payment)
    logging.info(f"💸 Pago con ID {payment_id} eliminado correctamente.")

    # ✅ Luego eliminar la reserva asociada
    reserva = next((r for r in reservations if r["reservation_id"] == reservation_id), None)
    if reserva:
        reservations.remove(reserva)
        logging.info(f"🗑️ Reserva con ID {reservation_id} eliminada correctamente.")
    else:
        reserva = {}

    return jsonify({
        'message': 'Cancelación exitosa: pago y reserva eliminados, asiento liberado.',
        'deleted_payment': payment,
        'deleted_reservation': reserva
    }), 200


############################################################################################################


## Editar un pago existente y devolver la información de la reserva asociada
@app.route('/edit_payment/<string:payment_id>', methods=['PUT'])
def edit_payment(payment_id):
    """
    Summary: Edita un pago existente -> método de pago, fecha o referencia
    Description:
      Edita un pago existente -> método de pago, fecha o referencia

    ---
    tags:
      - Payments
    parameters:
      - name: payment_id
        in: path
        type: string
        required: true
        description: ID único del pago (formato PAY123456)
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            payment_method:
              type: string
              enum: ["Tarjeta", "PayPal", "Transferencia", "Efectivo", "SINPE"]
              example: "Tarjeta"
            payment_date:
              type: string
              example: "Abril 25, 2025 - 17:00:00"
            transaction_reference:
              type: string
              example: "XYZ123ABC456"
    responses:
      200:
        description: Pago actualizado correctamente
      400:
        description: Datos inválidos o formato incorrecto
      404:
        description: Pago no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        logging.info(f"✏️ Solicitud para editar el pago con ID: {payment_id}")

        if not re.match(r"^PAY\d{6}$", payment_id.strip().upper()):
            return jsonify({'message': 'El formato del payment_id es inválido. Debe ser como PAY123456'}), 400

        payment = next((p for p in payments if p['payment_id'] == payment_id), None)
        if not payment:
            return jsonify({'message': f'No se encontró el pago con ID: {payment_id}'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'message': 'No se recibió cuerpo JSON'}), 400

        # Editar payment_method
        if 'payment_method' in data:
            if data['payment_method'] not in ["Tarjeta", "PayPal", "Transferencia", "Efectivo", "SINPE"]:
                return jsonify({'message': 'Método de pago inválido'}), 400
            payment['payment_method'] = data['payment_method']

        # Editar payment_date
        if 'payment_date' in data:
            payment['payment_date'] = data['payment_date']

        # Editar transaction_reference
        if 'transaction_reference' in data:
            payment['transaction_reference'] = data['transaction_reference']

        logging.info(f"✅ Pago actualizado: {payment}")
        return jsonify({
            'message': 'Pago actualizado correctamente.',
            'payment': payment
        }), 200

    except Exception as e:
        logging.exception("❌ Error al editar el pago.")
        return jsonify({'message': 'Error interno del servidor'}), 500


############################################################################################################


# Iniciar la aplicación
if __name__ == '__main__':

  # Generar las reservas una sola vez al arrancar el servidor
  reservations.extend(generate_fake_reservations(3))

  ## Generar los pagos una sola vez al arrancar el servidor
  payments = generate_fake_payments(1)

  # Ejecutar la app sin recargador para evitar duplicación
  app.run(debug=True, use_reloader=False, port=5002)
