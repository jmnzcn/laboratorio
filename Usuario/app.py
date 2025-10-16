# Standard Library
import logging
import os
import random
import string
from datetime import datetime, timedelta
import re
import sys

# Third-party Libraries
import requests
from dotenv import load_dotenv
from faker import Faker
from faker_airtravel import AirTravelProvider
from flasgger import Swagger
from marshmallow import Schema, fields, ValidationError, validates, RAISE, INCLUDE


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


## Configuración de Faker
app = Flask(__name__)


## Configuración de Swagger
swagger_template = {
    "info": {
        "title": "Air Travel API: Modulo de Usuario",
        "version": "1.0.0",
        "description": "API for managing airplanes and routes",
        "termsOfService": "https://losvagos.com/terms",
        "Contact": {
            "ResponsibleOrganization": "Los Vagabundos Inc.",
            "ResponsibleDeveloper": "El Vago Principal",
            "email": "",
            "URL": "https://example.com/contact"
        },
    },
    "tags": [
        {
            "name": "Flights routes and seats",
            "description": "Operations related to airplane routes and flights seats data"
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


################################################################################################
################################################################################################
## Inicio de Configuración de Schemas de Marshmallow
################################################################################################
################################################################################################


## Configuracion de Schemas de Airplane
class AirplaneSchema(Schema):
    airplane_id = fields.Int(required=True)
    model = fields.Str(required=True)
    manufacturer = fields.Str(required=True)
    year = fields.Int(required=True)
    capacity = fields.Int(required=True)


## Instancia del esquema
airplane_schema = AirplaneSchema()


################################################################################################


## Configuracion de Schemas de AirplaneRoute
class AirplaneRouteSchema(Schema):
    class Meta:
        unknown = INCLUDE

    airplane_route_id = fields.Int(required=True)
    airplane_id = fields.Int(required=True)
    flight_number = fields.Str(required=True)
    departure = fields.Str(required=True)
    arrival = fields.Str(required=True)
    departure_time = fields.Str(required=True)
    arrival_time = fields.Str(required=True)
    flight_time = fields.Str(required=True)
    price = fields.Float(required=False)
    Moneda = fields.Str(required=False)


## Instancia del esquema
airplane_route_schema = AirplaneRouteSchema()




################################################################################################


## Configuracion de Schemas de AirplaneSeat
class AirplaneSeatSchema(Schema):
    class Meta:
        unknown = RAISE  # Para que falle si hay campos inesperados

    airplane_id = fields.Int(required=True)
    seat_number = fields.Str(required=True)
    status = fields.Str(required=True)

    @validates("status")
    def validate_status(self, value):
        if value not in ["Libre", "Reservado", "Pagado"]:
            raise ValidationError("Estado inválido: debe ser 'Libre', 'Reservado' o 'Pagado'.")


## Instancia del esquema
airplane_seats_schema = AirplaneSeatSchema(many=True)


################################################################################################


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


################################################################################################


# Actualizar el esquema de creación de reservas para usar airplane_route_id
class ReservationCreationSchema(Schema):
    passport_number = fields.Str(required=True)
    full_name = fields.Str(required=True)
    email = fields.Email(required=True)
    phone_number = fields.Str(required=True)
    emergency_contact_name = fields.Str(required=True)
    emergency_contact_phone = fields.Str(required=True)
    airplane_id = fields.Int(required=True)
    airplane_route_id = fields.Int(required=True)
    seat_number = fields.Str(required=True)
    status = fields.Str(required=True, validate=lambda x: x in ["Reservado"])

    class Meta:
        unknown = INCLUDE


################################################################################################


## Configuracion de Schemas de Payment
class PaymentSchema(Schema):
    class Meta:
        unknown = INCLUDE  # Aceptamos campos extra que tal vez no estén explícitamente listados

    # Campos que vienen de la reserva
    reservation_id = fields.Int(required=True)
    reservation_code = fields.Str(required=False)
    passport_number = fields.Str(required=False)
    full_name = fields.Str(required=False)
    email = fields.Str(required=False)
    phone_number = fields.Str(required=False)
    emergency_contact_name = fields.Str(required=False)
    emergency_contact_phone = fields.Str(required=False)
    flight_number = fields.Str(required=False)
    seat_number = fields.Str(required=False)
    airplane_id = fields.Int(required=False)
    airplane_route_id = fields.Int(required=False)
    price = fields.Float(required=False)
    reservation_date = fields.Str(required=False)

    # Campos del pago nuevo
    payment_id = fields.Str(required=True)
    amount = fields.Float(required=True)
    currency = fields.Str(required=True)
    payment_method = fields.Str(required=True)
    status = fields.Str(required=True)
    payment_date = fields.Str(required=True)
    transaction_reference = fields.Str(required=True)

# Instancia para usar en las validaciones
payment_schema = PaymentSchema()


################################################################################################


class PaymentCreationSchema(Schema):
    reservation_id = fields.Int(required=True, strict=True)
    payment_method = fields.Str(required=True, validate=lambda x: x in ["Tarjeta", "PayPal", "Transferencia", "SINPE"])
    currency = fields.Str(load_default="USD", validate=lambda x: x in ["USD", "CRC"])


################################################################################################
################################################################################################
## Fin de Configuración de Schemas de Marshmallow
################################################################################################
################################################################################################


## Configuración de Swagger
swagger = Swagger(app, template=swagger_template)


################################################################################################
################################################################################################
## Inicio de la sección de rutas de vuelo
################################################################################################
################################################################################################


## Obtener todos los asientos de un avión desde el microservicio de gestión de vuelos
## y devolver la respuesta al cliente
@app.route('/get_seats_by_airplane_id/<int:airplane_id>/seats', methods=['GET'])
def get_seats_by_airplane_id(airplane_id):
    """
    Summary: Obtiene los asientos de un avión segun su ID
    Description:
      Recupera y valida la lista de asientos asignados a un avión determinado basado en su airplane_id.
      Se valida el formato del ID, la estructura de la respuesta y se maneja la ausencia de datos o errores de conexión.
    ---
    tags:
      - Flights routes and seats
    produces:
      - application/json
    parameters:
      - name: airplane_id
        in: path
        type: integer
        required: true
        description: ID del avión para consultar sus asientos
        example: 2
    responses:
      200:
        description: Lista de asientos recuperada exitosamente
        examples:
          application/json:
            [
              {
                "seat_number": "1A",
                "status": "Libre"
              },
              {
                "seat_number": "1B",
                "status": "Reservado"
              }
            ]
      400:
        description: El ID del avión no es válido
        examples:
          application/json:
            {
              "message": "Por favor proporciona un ID de avión válido (mayor que cero)."
            }
      404:
        description: No hay asientos registrados para el avión indicado
        examples:
          application/json:
            {
              "message": "No se encontraron asientos para el avión con ID 2."
            }
      500:
        description: Error de conexión o formato inesperado
        examples:
          application/json:
            {
              "message": "Error de validación en los datos de los asientos"
            }
    """
    try:
        if airplane_id <= 0:
            return jsonify({"message": "Por favor proporciona un ID de avión válido (mayor que cero)."}), 400

        asientos = get_seats_by_airplane_id(airplane_id)

        if not isinstance(asientos, list):
            return jsonify({"message": "Error al procesar los datos: formato inválido o sin conexión."}), 500
        if not asientos:
            return jsonify({"message": f"No se encontraron asientos para el avión con ID {airplane_id}."}), 404

        # ✅ Validar con Marshmallow
        try:
            validated = airplane_seats_schema.load(asientos)
        except ValidationError as err:
            app.logger.warning("❌ Validación fallida de asientos.")
            return jsonify({
                "message": "Error de validación en los datos de los asientos",
                "errors": err.messages
            }), 500

        return jsonify(validated), 200

    except Exception:
        app.logger.exception("❌ Error inesperado al obtener asientos del avión")
        return jsonify({"message": "Ocurrió un error inesperado. Intenta nuevamente más tarde."}), 500


################################################################################################


## Obtener todos los aviones junto con sus asientos desde el microservicio de gestión de vuelos
## y devolver la respuesta al cliente
@app.route('/get_all_airplanes_with_seats', methods=['GET'])
def get_all_airplanes_with_seats():
    """
    Summary: Obtiene todos los aviones con sus asientos asociados
    ---
    tags:
      - Flights routes and seats
    produces:
      - application/json
    responses:
      200:
        description: Lista de aviones con sus respectivos asientos validada exitosamente
      404:
        description: No hay aviones o asientos para mostrar
      500:
        description: Error de conexión al microservicio de vuelos o validación
    """
    try:
        gestionvuelos_url = os.getenv("GESTIONVUELOS_SERVICE")

        # 1) Obtener todos los aviones
        resp_planes = requests.get(f"{gestionvuelos_url}/get_airplanes", timeout=20)
        if resp_planes.status_code != 200:
            return jsonify({"error": "No se pudieron obtener los aviones."}), 500

        airplanes = resp_planes.json()
        # 1.a) Validación: lista vacía ⇒ 404
        if not isinstance(airplanes, list) or not airplanes:
            return jsonify({"message": "No hay aviones registrados actualmente."}), 404

        # 2) Obtener todos los asientos agrupados por avión
        resp_seats = requests.get(f"{gestionvuelos_url}/seats/grouped-by-airplane", timeout=20)
        if resp_seats.status_code != 200:
            return jsonify({"error": "No se pudieron obtener los asientos."}), 500

        seats_grouped = resp_seats.json()
        # 2.a) Validación: estructura no dict o vacío ⇒ permitimos, cada avión tendrá lista vacía

        resultado = []
        for avion in airplanes:
            try:
                # 3) Validar datos de avión
                validated_airplane = airplane_schema.load(avion)

                # 4) Recoger sus asientos (puede venir lista vacía)
                airplane_id_str = str(validated_airplane["airplane_id"])
                asientos = seats_grouped.get(airplane_id_str, [])
                # Validar listado de asientos
                validated_seats = airplane_seats_schema.load(asientos)

                resultado.append({
                    **validated_airplane,
                    "seats": validated_seats
                })

            except ValidationError as ve:
                app.logger.warning(f"❌ Error de validación: {ve.messages}")
                return jsonify({
                    "message": "Error de validación en avión o sus asientos",
                    "errors": ve.messages
                }), 500

        # 5) Si tras todo no hay registros (caso borde)
        if not resultado:
            return jsonify({"message": "No hay aviones con asientos para mostrar."}), 404

        return jsonify(resultado), 200

    except requests.RequestException as e:
        app.logger.error("❌ Error de red al consultar el microservicio de vuelos: %s", e)
        return jsonify({"error": "Error al conectar con el microservicio de vuelos."}), 500
    except Exception:
        app.logger.exception("❌ Error interno inesperado")
        return jsonify({"error": "Error interno del servidor"}), 500


################################################################################################


## Función para obtener los asientos de un avión específico mediante el microservicio de gestión de vuelos
## y devolver la respuesta al cliente
def get_seats_by_airplane_id(airplane_id):
    """
    Consulta los asientos de un avión específico mediante el microservicio de gestión de vuelos.

    Valida que el ID sea válido, realiza la solicitud HTTP al microservicio y asegura que la respuesta
    sea una lista JSON con los asientos. Retorna la lista si es válida, o None si ocurre un error.
    """
    # 🔧 Obtener la URL base del microservicio
    gestionvuelos_service = os.getenv("GESTIONVUELOS_SERVICE")
    if not gestionvuelos_service:
        app.logger.error("❌ Falta configurar 'GESTIONVUELOS_SERVICE' en el entorno.")
        return None

    # ✅ Validación del ID
    if not isinstance(airplane_id, int) or airplane_id <= 0:
        app.logger.warning(f"⚠️ ID inválido: {airplane_id}. Debe ser un entero positivo.")
        return None

    url = f"{gestionvuelos_service}/get_airplane_seats/{airplane_id}/seats"
    app.logger.info(f"🔍 Consultando asientos del avión ID {airplane_id} en: {url}")

    try:
        response = requests.get(url, timeout=20)
        app.logger.info("📥 HTTP %d recibido", response.status_code)

        # 🧾 Validación de respuesta JSON esperada
        if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()
            if isinstance(data, list):
                app.logger.info(f"✅ Se recibieron {len(data)} asientos.")
                return data
            app.logger.warning("⚠️ Respuesta recibida no es una lista de asientos.")
        else:
            app.logger.warning(f"⚠️ Error en la respuesta del microservicio: HTTP {response.status_code}")

    except requests.Timeout:
        app.logger.error("⏱️ Tiempo de espera agotado al contactar el microservicio de vuelos.")
    except requests.RequestException as e:
        app.logger.error(f"💥 Fallo en la solicitud al microservicio: {e}")
    except Exception as e:
        app.logger.exception("❌ Error inesperado al procesar la respuesta.")

    return None


#################################################################################################


## Obtener todas las rutas de vuelo desde el microservicio de gestión de vuelos
@app.route('/get_all_airplanes_routes', methods=['GET'])
def get_all_airplanes_routes():
    """
    Summary: Obtiene todas las rutas de vuelo disponibles
    Description:
      Consulta al microservicio de gestión de vuelos para obtener la lista completa de rutas registradas.
      La respuesta se valida para asegurar que tenga el formato correcto. Se notifican errores de conexión,
      estructura inválida o ausencia de datos con los códigos correspondientes.
    ---
    tags:
      - Flights routes and seats
    produces:
      - application/json
    responses:
      200:
        description: Lista de rutas de vuelo obtenida correctamente
        examples:
          application/json:
            [
              {
                "airplane_route_id": 10,
                "flight_number": "LAV101",
                "airplane_id": 3,
                "origin": "SJO",
                "destination": "MIA",
                "departure_time": "Abril 30, 2025 - 08:00:00",
                "arrival_time": "Abril 30, 2025 - 11:30:00",
                "flight_time": "03:30:00",
                "price": 200.0
              }
            ]
      404:
        description: No se encontraron vuelos registrados
        examples:
          application/json:
            {
              "error": "No hay vuelos registrados actualmente en el sistema."
            }
      500:
        description: Error interno del servidor o estructura de datos inválida
        examples:
          application/json:
            {
              "error": "La respuesta del microservicio no tiene el formato correcto (lista esperada)."
            }
    """
    import time
    start = time.time()

    try:
        vuelos = get_all_flights()

        if vuelos is None:
            logging.error("❌ Fallo de conexión con el microservicio de vuelos.")
            return jsonify({"error": "No se pudo establecer conexión con el microservicio de vuelos."}), 500

        if not isinstance(vuelos, list):
            logging.error("❌ Estructura inválida: se esperaba una lista.")
            return jsonify({"error": "La respuesta del microservicio no tiene el formato correcto (lista esperada)."}), 500

        if not vuelos:
            logging.warning("⚠️ La lista de vuelos está vacía.")
            return jsonify({"error": "No hay vuelos registrados actualmente en el sistema."}), 404

        if not all(isinstance(v, dict) and 'airplane_route_id' in v for v in vuelos):
            logging.error("❌ Elementos mal estructurados en la lista de vuelos.")
            return jsonify({"error": "Uno o más vuelos no contienen la estructura esperada ('airplane_route_id' faltante)."}), 500

        elapsed = round(time.time() - start, 2)
        logging.info(f"📡 {len(vuelos)} rutas de vuelo recuperadas en {elapsed}s.")
        return jsonify(vuelos), 200

    except Exception as e:
        logging.exception("❌ Error inesperado al recuperar rutas de vuelo")
        return jsonify({
            "error": "Se produjo un error inesperado al procesar la solicitud. Inténtalo nuevamente más tarde."
        }), 500


## Función para obtener todas las rutas de vuelo desde el microservicio de gestión de vuelos
## y devolver la respuesta al cliente
def get_all_flights():
    """
    Recupera todas las rutas de vuelo disponibles desde el microservicio de gestión de vuelos.

    Realiza una solicitud HTTP al microservicio utilizando la URL configurada en 'GESTIONVUELOS_SERVICE'.
    Valida que la respuesta sea JSON, con formato de lista, y registra información relevante para diagnóstico.

    Returns:
        list | None: Lista de rutas si es exitosa, None si hay error o estructura inválida.
    """
    # 1️⃣ Validación de configuración
    gestionvuelos_service = os.getenv("GESTIONVUELOS_SERVICE")
    if not gestionvuelos_service:
        app.logger.error("❌ Variable de entorno 'GESTIONVUELOS_SERVICE' no definida. Verifica el archivo .env.")
        return None

    url = f"{gestionvuelos_service}/get_all_airplanes_routes"
    app.logger.info("🌐 Consultando rutas de vuelo al microservicio: %s", url)

    try:
        response = requests.get(url, timeout=20)
        status = response.status_code
        content_type = response.headers.get("Content-Type", "")

        app.logger.info("📥 HTTP %d recibido desde microservicio", status)

        # 2️⃣ Validación directa de éxito y formato
        if status != 200:
            app.logger.warning("⚠️ Respuesta no exitosa del microservicio: %d", status)
            return None

        if 'application/json' not in content_type:
            app.logger.warning("⚠️ Se esperaba JSON, pero se recibió: %s", content_type)
            return None

        vuelos = response.json()

        # 3️⃣ Validación estructural
        if isinstance(vuelos, list):
            app.logger.info("✅ %d rutas de vuelo recibidas correctamente.", len(vuelos))
            return vuelos

        app.logger.warning("⚠️ Se esperaba una lista como respuesta, pero se recibió otro tipo.")
        return None

    except requests.Timeout:
        app.logger.error("⏱️ Tiempo de espera agotado al conectar con el microservicio de vuelos.")
    except requests.RequestException as e:
        app.logger.error("💥 Error de conexión con el microservicio: %s", str(e))
    except Exception:
        app.logger.exception("❌ Error inesperado durante la consulta de vuelos.")

    return None


################################################################################################


## Función para notificar el estado de un asiento en un vuelo al microservicio de gestión de vuelos
## y devolver la respuesta al cliente
def notificar_estado_asiento_en_vuelos(airplane_id, seat_number, status):
    """
    Notifica al microservicio de vuelos que se actualice el estado de un asiento específico.

    Args:
        airplane_id (int): ID del avión al que pertenece el asiento.
        seat_number (str): Número del asiento (ej. "1A").
        status (str): Nuevo estado del asiento, por ejemplo "Reservado" o "Libre".

    Returns:
        dict: Resultado del intento con 'ok': True o False y mensaje opcional.
    """
    vuelos_service = os.getenv("GESTIONVUELOS_SERVICE")
    if not vuelos_service:
        app.logger.warning("⚠️ GESTIONVUELOS_SERVICE no está definida.")
        return {"ok": False, "error": "Servicio de vuelos no configurado."}

    # Validación 1: airplane_id positivo
    if not isinstance(airplane_id, int) or airplane_id <= 0:
        app.logger.warning("⚠️ ID de avión inválido: %s", airplane_id)
        return {"ok": False, "error": "ID del avión inválido."}

    # Validación 2: seat_number no vacío y con formato tipo '12A'
    import re
    if not isinstance(seat_number, str) or not seat_number.strip():
        msg = "El número de asiento ('seat_number') debe ser un texto no vacío."
        app.logger.warning(f"⚠️ {msg}")
        return {"ok": False, "error": msg}
    if not re.match(r'^\d{1,2}[A-Z]$', seat_number.strip().upper()):
        msg = f"El número de asiento '{seat_number}' no tiene un formato válido. Se espera algo como '1A'."
        app.logger.warning(f"⚠️ {msg}")
        return {"ok": False, "error": msg}

    url = f"{vuelos_service}/airplanes/{airplane_id}/seats/{seat_number}"
    try:
        response = requests.put(url, json={"status": status}, timeout=20)
        app.logger.info("🪑 Estado del asiento actualizado: %s [%d]", url, response.status_code)
        return {"ok": response.status_code == 200}
    except requests.RequestException as e:
        app.logger.error("❌ Error notificando estado de asiento: %s", str(e))
        return {"ok": False, "error": str(e)}


################################################################################################


## Obtener una ruta de vuelo por su ID desde el microservicio de gestión de vuelos
## y devolver la respuesta al cliente
@app.route('/get_airplane_route_by_id/<int:airplane_route_id>', methods=['GET'])
def get_airplane_route_by_id(airplane_route_id):
    """
    Summary: Obtiene una ruta de vuelo por su ID
    Description:
      Recupera una ruta de vuelo específica desde el microservicio GestiónVuelos utilizando su ID único.
      Se valida que el ID sea un número entero positivo, se verifica la respuesta del microservicio,
      y se valida la estructura con Marshmallow antes de devolver los datos.
    ---
    tags:
      - Flights routes and seats
    produces:
      - application/json
    parameters:
      - name: airplane_route_id
        in: path
        type: integer
        required: true
        description: ID único de la ruta de vuelo
        example: 12
    responses:
      200:
        description: Ruta de vuelo encontrada y validada exitosamente
        examples:
          application/json:
            {
              "airplane_route_id": 12,
              "flight_number": "LAV102",
              "airplane_id": 3,
              "origin": "SJO",
              "destination": "PTY",
              "departure_time": "Abril 30, 2025 - 08:00:00",
              "arrival_time": "Abril 30, 2025 - 10:00:00",
              "flight_time": "02:00:00",
              "price": 145.50
            }
      400:
        description: ID inválido o error de formato
        examples:
          application/json:
            {
              "message": "El ID debe ser un número positivo."
            }
      404:
        description: Ruta no encontrada
        examples:
          application/json:
            {
              "message": "Ruta de vuelo no encontrada"
            }
      500:
        description: Error interno del servidor o de validación
        examples:
          application/json:
            {
              "message": "Error interno del servidor"
            }
    """
    try:
        if airplane_route_id <= 0:
            return jsonify({"message": "El ID debe ser un número positivo."}), 400

        gestion_vuelos_url = os.getenv("GESTIONVUELOS_SERVICE")
        url = f"{gestion_vuelos_url}/get_airplanes_route_by_id/{airplane_route_id}"

        response = requests.get(url, timeout=20)
        status = response.status_code

        if status == 404:
            return jsonify({"message": "Ruta de vuelo no encontrada"}), 404
        if status != 200:
            logging.warning(f"⚠️ Código inesperado del microservicio: {status}")
            return jsonify({"message": "Error al consultar el microservicio GestiónVuelos"}), 500

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            logging.error("❌ La respuesta no es JSON")
            return jsonify({"message": "El microservicio no respondió con JSON válido"}), 500

        data = response.json()

        # Validar estructura con Marshmallow
        validated = airplane_route_schema.load(data)
        return jsonify(validated), 200

    except ValidationError as err:
        logging.warning("❌ Error de validación con Marshmallow")
        return jsonify({"message": "Error de validación", "errors": err.messages}), 500
    except requests.RequestException as e:
        logging.error(f"❌ Error de red al consultar GestiónVuelos: {e}")
        return jsonify({"message": "Error de conexión con el microservicio"}), 500
    except Exception:
        logging.exception("❌ Error inesperado al consultar ruta de vuelo.")
        return jsonify({"message": "Error interno del servidor"}), 500


################################################################################################
################################################################################################
## Fin de la sección de rutas de vuelo
################################################################################################
################################################################################################


################################################################################################
################################################################################################
## Inicio de la sección de Reservas de vuelo
################################################################################################
################################################################################################


## Obtener una reserva por su código único desde el microservicio de gestión de reservas
## y devolver la respuesta al cliente
@app.route('/get_reservation_by_code/<string:reservation_code>', methods=['GET'])
def get_reservation_by_code(reservation_code):
    """
    Summary: Consulta una reserva por su código único
    Description:
      Recupera una reserva desde el microservicio GestiónReservas utilizando el código alfanumérico único (`reservation_code`).
      Valida el formato del código y estructura de la reserva con Marshmallow. Si el código no existe o está mal formado,
      devuelve un error apropiado.

    ---
    tags:
      - Reservations
    produces:
      - application/json
    parameters:
      - name: reservation_code
        in: path
        type: string
        required: true
        description: "Código alfanumérico de la reserva ej. ABC123 "
        example: ABC123
    responses:
      200:
        description: Reserva encontrada y validada correctamente
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
        description: Código inválido o mal formado
        examples:
          application/json:
            {
              "message": "El código de reserva es obligatorio y debe ser texto válido."
            }
      404:
        description: Reserva no encontrada
        examples:
          application/json:
            {
              "message": "Reserva no encontrada en GestiónReservas"
            }
      500:
        description: Error de validación o error interno del servidor
        examples:
          application/json:
            {
              "message": "Error de validación en los datos de la reserva",
              "errors": {
                "email": ["Not a valid email address."]
              }
            }
    """
    try:
        if not isinstance(reservation_code, str) or not reservation_code.strip():
            return jsonify({'message': 'El código de reserva es obligatorio y debe ser texto válido.'}), 400

        gestion_reservas_url = os.getenv("GESTIONRESERVAS_SERVICE")
        url = f"{gestion_reservas_url}/get_reservation_by_code/{reservation_code}"

        response = requests.get(url, timeout=20)

        if response.status_code == 404:
            return jsonify({'message': 'Reserva no encontrada en GestiónReservas'}), 404
        elif response.status_code != 200:
            return jsonify({'message': f'Error consultando reserva. Código: {response.status_code}'}), 500

        data = response.json()

        try:
            validated = ReservationSchema().load(data)
            return jsonify(validated), 200
        except ValidationError as err:
            return jsonify({'message': 'Error de validación en los datos de la reserva', 'errors': err.messages}), 500

    except requests.RequestException as e:
        app.logger.error(f"❌ Error al contactar con GestiónReservas: {e}")
        return jsonify({'message': 'Error de red al conectar con el microservicio'}), 500
    except Exception as e:
        app.logger.exception("❌ Error inesperado al consultar reserva por código desde Usuario")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################


## Obtener una reserva por su ID numérico desde el microservicio de gestión de reservas
## y devolver la respuesta al cliente
@app.route('/get_reservation_by_id/<int:reservation_id>', methods=['GET'])
def consultar_reserva_por_id_usuario(reservation_id):
    """
    Summary: Consulta una reserva por su ID numérico
    Description:
      Este endpoint permite recuperar una reserva específica utilizando su `reservation_id`. La respuesta es validada
      con Marshmallow para asegurar que la estructura sea la correcta. Si el ID es inválido, no existe o ocurre un error,
      se devuelve una respuesta adecuada.
    ---
    tags:
      - Reservations
    produces:
      - application/json
    parameters:
      - name: reservation_id
        in: path
        type: integer
        required: true
        description: ID numérico único de la reserva
        example: 7
    responses:
      200:
        description: Reserva encontrada y validada correctamente
        examples:
          application/json:
            {
              "reservation_id": 7,
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
        description: ID inválido o mal formado
        examples:
          application/json:
            {
              "message": "El ID debe ser un número entero positivo."
            }
      404:
        description: Reserva no encontrada
        examples:
          application/json:
            {
              "message": "Reserva no encontrada en GestiónReservas"
            }
      500:
        description: Error interno o de validación
        examples:
          application/json:
            {
              "message": "Error de validación en los datos de la reserva",
              "errors": {
                "email": ["Not a valid email address."]
              }
            }
    """
    try:
        if reservation_id <= 0:
            return jsonify({'message': 'El ID debe ser un número entero positivo.'}), 400

        gestion_reservas_url = os.getenv("GESTIONRESERVAS_SERVICE")
        url = f"{gestion_reservas_url}/get_reservation_by_id/{reservation_id}"

        response = requests.get(url, timeout=20)

        if response.status_code == 404:
            return jsonify({'message': 'Reserva no encontrada en GestiónReservas'}), 404
        elif response.status_code != 200:
            return jsonify({'message': f'Error consultando reserva. Código: {response.status_code}'}), 500

        data = response.json()

        try:
            validated = ReservationSchema().load(data)
            return jsonify(validated), 200
        except ValidationError as err:
            return jsonify({'message': 'Error de validación en los datos de la reserva', 'errors': err.messages}), 500

    except requests.RequestException as e:
        app.logger.error(f"❌ Error al contactar con GestiónReservas: {e}")
        return jsonify({'message': 'Error de red al conectar con el microservicio'}), 500
    except Exception as e:
        app.logger.exception("❌ Error inesperado al consultar reserva por ID desde Usuario")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################


## Modificar una reserva existente en el microservicio de Gestión de Reservas
## y devolver la respuesta al cliente
@app.route('/update_reservation/<string:reservation_code>', methods=['PUT'])
def usuario_modify_reservation(reservation_code):
    """
    Summary: Modifica una reserva existente desde Usuario
    Description:
      Actualiza sólo seat_number y/o datos de contacto. Body debe incluir
      exactamente: seat_number, email, phone_number, emergency_contact_name,
      emergency_contact_phone. Verifica disponibilidad en GestiónVuelos y
      envía los cambios a GestiónReservas.
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
        description: Código de reserva de 6 caracteres (e.g. ABC123)
      - in: body
        name: body
        required: true
        description: Campos a actualizar (exactamente estos cinco)
        schema:
          type: object
          required:
            - seat_number
            - email
            - phone_number
            - emergency_contact_name
            - emergency_contact_phone
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
        description: Body inválido (faltan o sobran campos) o código mal formado
      404:
        description: Reserva no encontrada en GestiónReservas
      409:
        description: El nuevo asiento no está libre
      503:
        description: No se pudo conectar con GestiónVuelos o GestiónReservas
      504:
        description: Timeout al contactar a algún servicio
      500:
        description: Error interno del servidor
    """
    # 1) Validar formato de código
    code = reservation_code.strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{6}', code):
        return jsonify({'message': 'El código de reserva debe ser 6 caracteres alfanuméricos.'}), 400

    # 2) Leer y validar body
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No se recibió cuerpo JSON.'}), 400

    allowed = {'seat_number', 'email', 'phone_number', 'emergency_contact_name', 'emergency_contact_phone'}
    if set(data.keys()) != allowed:
        return jsonify({
            'message': 'El body debe incluir exactamente estos campos sin extras ni faltantes: '
                       'seat_number, email, phone_number, emergency_contact_name, emergency_contact_phone.'
        }), 400

    gestion_reservas = os.getenv("GESTIONRESERVAS_SERVICE")
    gestion_vuelos   = os.getenv("GESTIONVUELOS_SERVICE")

    # 3) Obtener la reserva actual de GestiónReservas
    try:
        get_resp = requests.get(f"{gestion_reservas}/get_reservation_by_code/{code}", timeout=20)
    except requests.exceptions.ConnectionError:
        return jsonify({'message': 'No se pudo conectar con GestiónReservas.'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'message': 'Timeout al contactar GestiónReservas.'}), 504

    if get_resp.status_code == 404:
        return jsonify({'message': 'Reserva no encontrada en GestiónReservas.'}), 404
    if get_resp.status_code != 200:
        return jsonify({'message': 'Error al obtener reserva de GestiónReservas.'}), get_resp.status_code

    reserva_actual = get_resp.json()

    # 4) Detectar si no hay cambios
    if all(data[field] == reserva_actual.get(field) for field in allowed):
        return jsonify({'message': 'La información es idéntica; no se realizaron cambios.'}), 200

    # 5) Si cambia asiento, verificar disponibilidad
    new_seat = data['seat_number']
    if new_seat != reserva_actual['seat_number']:
        airplane_id = reserva_actual['airplane_id']
        try:
            seats_resp = requests.get(f"{gestion_vuelos}/get_airplane_seats/{airplane_id}/seats", timeout=20)
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos para verificar asiento.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al verificar asiento en GestiónVuelos.'}), 504

        if seats_resp.status_code != 200:
            return jsonify({'message': 'Error al verificar asientos en GestiónVuelos.'}), 500

        seat_info = next((s for s in seats_resp.json() if s['seat_number'] == new_seat), None)
        if not seat_info:
            return jsonify({'message': f"Asiento {new_seat} no existe en el avión."}), 400
        if seat_info['status'] != 'Libre':
            return jsonify({'message': f"El asiento {new_seat} no está libre."}), 409

    # 6) Enviar cambios a GestiónReservas
    try:
        put_resp = requests.put(
            f"{gestion_reservas}/reservations/{code}",
            json=data,
            timeout=20
        )
    except requests.exceptions.ConnectionError:
        return jsonify({'message': 'No se pudo conectar con GestiónReservas.'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'message': 'Timeout al contactar GestiónReservas.'}), 504

    if put_resp.status_code != 200:
        body = put_resp.json() if put_resp.headers.get('Content-Type','').startswith('application/json') else {'message': put_resp.text}
        return jsonify(body), put_resp.status_code

    updated = put_resp.json()

    # 7) Liberar antiguo y reservar nuevo en GestiónVuelos (solo si cambió asiento)
    if new_seat != reserva_actual['seat_number']:
        airplane_id = reserva_actual['airplane_id']
        old_seat    = reserva_actual['seat_number']

        # Liberar
        try:
            free_resp = requests.put(
                f"{gestion_vuelos}/free_seat/{airplane_id}/seats/{old_seat}",
                timeout=20
            )
            if free_resp.status_code != 200:
                logging.warning("No se pudo liberar antiguo asiento en GestiónVuelos.")
        except requests.exceptions.RequestException:
            logging.warning("Error conectando a GestiónVuelos para liberar asiento.")

        # Reservar
        try:
            reserve_resp = requests.put(
                f"{gestion_vuelos}/update_seat_status/{airplane_id}/seats/{new_seat}",
                json={"status": "Reservado"},
                timeout=20
            )
            if reserve_resp.status_code not in (200, 204):
                logging.warning("No se pudo reservar nuevo asiento en GestiónVuelos.")
        except requests.exceptions.RequestException:
            logging.warning("Error conectando a GestiónVuelos para reservar asiento.")

    # 8) Devolver resultado
    return jsonify({
        'message': 'Reserva y datos actualizados exitosamente',
        'reservation': updated
    }), 200


def put_reserva_en_microservicio(codigo, reserva_data):
    gestionreservas_service = os.getenv("GESTIONRESERVAS_SERVICE")

    if not gestionreservas_service:
        return {"ok": False, "error": "Variable de entorno GESTIONRESERVAS_SERVICE no definida"}

    url = f"{gestionreservas_service}/reservations/{codigo}"
    app.logger.info("📝 Enviando PUT al microservicio de reservas: %s", url)

    try:
        response = requests.put(url, json=reserva_data)
        app.logger.info("📥 Código de respuesta: %d", response.status_code)
        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        return {"ok": False, "error": response.json().get("message", "Error desconocido")}
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}


################################################################################################


## Eliminar una reserva existente en el microservicio de Gestión de Reservas
## y devolver la respuesta al cliente
@app.route('/usuario/delete_reservation_by_id/<int:reservation_id>', methods=['DELETE'])
def eliminar_reserva_usuario_por_id(reservation_id):
    """
    Summary: Elimina una reserva por ID desde Usuario
    Description:
      Elimina una reserva mediante su ID consultando al microservicio GestiónReservas, y solicita a GestiónVuelos la liberación del asiento asociado.
    ---
    tags:
      - Reservations
    parameters:
      - name: reservation_id
        in: path
        required: true
        type: integer
        description: ID de la reserva a eliminar
        example: 5
    responses:
      200:
        description: Reserva eliminada con éxito
      404:
        description: Reserva no encontrada
      503:
        description: Error de conexión con GestiónVuelos
      504:
        description: Timeout al liberar el asiento
      500:
        description: Error inesperado
    """
    try:
        if reservation_id <= 0:
            return jsonify({"message": "El ID debe ser un número positivo."}), 400

        # Consultar y eliminar reserva en GestiónReservas
        gestionreservas_url = os.getenv("GESTIONRESERVAS_SERVICE")
        url_delete = f"{gestionreservas_url}/delete_reservation_by_id/{reservation_id}"
        response = requests.delete(url_delete, timeout=20)

        if response.status_code == 404:
            return jsonify({"message": "Reserva no encontrada"}), 404
        elif response.status_code != 200:
            return jsonify({"message": f"Error al eliminar reserva. Código: {response.status_code}"}), 500

        try:
            data = response.json()
        except ValueError:
            return jsonify({"message": "Respuesta inválida del microservicio GestiónReservas"}), 500

        deleted_reservation = data.get("deleted_reservation")
        if not deleted_reservation:
            return jsonify({"message": "Estructura de respuesta inválida"}), 500

        airplane_id = deleted_reservation.get("airplane_id")
        seat_number = deleted_reservation.get("seat_number")

        if not airplane_id or not seat_number:
            return jsonify({"message": "No se encontró información de avión o asiento para liberar"}), 500

        # Liberar asiento en GestiónVuelos
        gestionvuelos_url = os.getenv("GESTIONVUELOS_SERVICE")
        liberar_url = f"{gestionvuelos_url}/free_seat/{airplane_id}/seats/{seat_number}"
        try:
            response_vuelos = requests.put(liberar_url, timeout=20)
            if response_vuelos.status_code != 200:
                return jsonify({
                    "message": "Reserva eliminada, pero no se pudo liberar el asiento",
                    "deleted_reservation": deleted_reservation
                }), 503
        except requests.exceptions.Timeout:
            return jsonify({"message": "Timeout al intentar liberar el asiento en GestiónVuelos"}), 504
        except requests.exceptions.ConnectionError:
            return jsonify({"message": "No se pudo conectar con GestiónVuelos para liberar el asiento"}), 503

        return jsonify({
            "message": data.get("message", "Reserva eliminada exitosamente"),
            "deleted_reservation": deleted_reservation
        }), 200

    except Exception as e:
        app.logger.exception("❌ Error inesperado al eliminar reserva desde Usuario")
        return jsonify({"message": "Error interno del servidor"}), 500


################################################################################################


## Obtener todas las reservas desde el microservicio de gestión de reservas
## y devolver la respuesta al cliente
@app.route('/get_all_reservations', methods=['GET'])
def listar_reservas():
    """
    Summary: Lista todas las reservas existentes
    ---
    tags:
      - Reservations
    produces:
      - application/json
    responses:
      200:
        description: Lista de reservas o mensaje de que no hay reservas
      500:
        description: Error al conectar o validar con GestiónReservas
    """
    try:
        gestion_reservas_url = os.getenv("GESTIONRESERVAS_SERVICE", "http://GestionReservas:5000")
        resp = requests.get(f"{gestion_reservas_url}/get_fake_reservations", timeout=20)

        # Si GestiónReservas devuelve 204, lo convertimos en 200 con mensaje
        if resp.status_code == 204:
            return jsonify({'message': 'No hay reservas registradas.'}), 200

        # Si devuelve 200, parseamos el JSON
        if resp.status_code == 200:
            data = resp.json()
            # Si la lista está vacía, devolvemos mensaje igualmente
            if not isinstance(data, list) or not data:
                return jsonify({'message': 'No hay reservas registradas.'}), 200

            # Validad con Marshmallow
            try:
                validated = reservation_schema.load(data, many=True)
                return jsonify(validated), 200
            except ValidationError as err:
                logging.warning("❌ Error de validación con Marshmallow: %s", err.messages)
                return jsonify({
                    "message": "Error de validación en las reservas",
                    "errors": err.messages
                }), 500

        # Para cualquier otro código, propagamos el error con ese mismo código
        return jsonify({
            'message': f'Error al consultar reservas. Código de respuesta: {resp.status_code}'
        }), resp.status_code

    except requests.exceptions.RequestException:
        logging.exception("❌ Error de conexión con GestiónReservas")
        return jsonify({'message': 'No se pudo conectar con GestiónReservas.'}), 500
    except Exception:
        logging.exception("❌ Error inesperado al consultar reservas")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################


## Crear una reserva de vuelo en el microservicio de Gestión de Reservas
## y devolver la respuesta al cliente
@app.route('/usuario/add_reservation', methods=['POST'])
def usuario_add_reservation():
    """
    Summary: Crea una nueva reserva de vuelo desde el microservicio Usuario
    Description:
      Valida ruta↔avión y disponibilidad del asiento, llama a GestiónReservas
      para crear la reserva, y solo tras el éxito marca el asiento como reservado.
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
        description: Reserva creada exitosamente
      400:
        description: Error de validación o datos inválidos
      409:
        description: Asiento ya reservado
      503:
        description: Servicio no disponible (GestiónVuelos / GestiónReservas)
      504:
        description: Timeout
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No se recibió cuerpo JSON'}), 400

        # 1) Validar payload localmente
        validated = ReservationCreationSchema().load(data)
        airplane_id  = validated['airplane_id']
        route_id     = validated['airplane_route_id']
        seat_number  = validated['seat_number']

        gestion_vuelos   = os.getenv("GESTIONVUELOS_SERVICE")
        gestion_reservas = os.getenv("GESTIONRESERVAS_SERVICE")

        # 2) Validar ruta ↔ avión
        try:
            routes_resp = requests.get(f"{gestion_vuelos}/get_all_airplanes_routes", timeout=20)
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos al obtener rutas.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al obtener rutas en GestiónVuelos.'}), 504

        if routes_resp.status_code != 200:
            return jsonify({'message': 'Error al obtener rutas desde GestiónVuelos.'}), 500

        route = next((r for r in routes_resp.json()
                      if r.get('airplane_route_id') == route_id), None)
        if not route:
            return jsonify({'message': f'Ruta con ID {route_id} no encontrada.'}), 400
        if route.get('airplane_id') != airplane_id:
            return jsonify({'message': f'La ruta {route_id} no está asociada al avión {airplane_id}.'}), 400

        # 3) Validar que el asiento esté Libre
        try:
            seats_resp = requests.get(f"{gestion_vuelos}/get_airplane_seats/{airplane_id}/seats", timeout=20)
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos para verificar asiento.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al verificar asiento en GestiónVuelos.'}), 504

        if seats_resp.status_code != 200:
            return jsonify({'message': 'Error al verificar asientos en GestiónVuelos.'}), 500

        seat = next((s for s in seats_resp.json() if s['seat_number'] == seat_number), None)
        if not seat:
            return jsonify({'message': f'Asiento {seat_number} no existe en el avión {airplane_id}.'}), 400
        if seat['status'] != 'Libre':
            return jsonify({'message': f'El asiento {seat_number} no está libre.'}), 409

        # 4) Llamar primero a GestiónReservas
        try:
            resp = requests.post(
                f"{gestion_reservas}/add_reservation",
                json=validated,
                timeout=20
            )
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónReservas'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al contactar GestiónReservas'}), 504

        # Si fallo en reservas, propagamos el error y **no** tocamos el asiento
        if resp.status_code != 201:
            body = resp.json() if resp.headers.get('Content-Type','').startswith('application/json') else {'message': resp.text}
            return jsonify(body), resp.status_code

        # 5) Solo ahora marcamos el asiento como Reservado
        try:
            book_resp = requests.put(
                f"{gestion_vuelos}/update_seat_status/{airplane_id}/seats/{seat_number}",
                json={'status': 'Reservado'},
                timeout=20
            )
        except requests.exceptions.RequestException:
            # Idealmente aquí podrías hacer rollback de la reserva en GestiónReservas
            return jsonify({
                'message': 'Reserva en GestiónReservas OK, pero fallo al reservar asiento en GestiónVuelos.',
                'reservation': resp.json()
            }), 500

        if book_resp.status_code != 200:
            return jsonify({
                'message': 'Reserva en GestiónReservas OK, pero no se pudo reservar el asiento en GestiónVuelos.',
                'reservation': resp.json()
            }), 500

        # 6) Todo OK: devolvemos el body de GestiónReservas
        return jsonify(resp.json()), 201

    except ValidationError as err:
        return jsonify({'message': 'Error de validación', 'errors': err.messages}), 400
    except Exception:
        logging.exception("❌ Error inesperado en Usuario al crear reserva")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################
################################################################################################
## Transacciones de pago de reservas (Payments)
## desde el microservicio de Gestión de Reservas
## y devolver la respuesta al cliente
#################################################################################################
#################################################################################################

gestion_reservas_url = os.getenv("GESTIONRESERVAS_SERVICE")

@app.route('/cancel_payment_and_reservation/<string:payment_id>', methods=['DELETE'])
def cancel_payment_and_reservation(payment_id):
    """
    Summary: Cancelación de pago y reserva desde el microservicio Usuario
    Description:
      Invoca a GestiónReservas para eliminar un pago, la reserva asociada
      y liberar el asiento en el avión.
    ---
    tags:
      - Payments
    parameters:
      - name: payment_id
        in: path
        type: string
        required: true
        description: ID único del pago (formato PAY123456)
        example: PAY123456
    responses:
      200:
        description: Cancelación exitosa
      400:
        description: Formato de payment_id inválido
      404:
        description: Pago o reserva no encontrada en GestiónReservas
      503:
        description: No se pudo conectar con GestiónReservas
      504:
        description: Timeout al contactar GestiónReservas
      500:
        description: Error interno del servidor
    """
    # 1) Validar formato del payment_id
    pid = payment_id.strip().upper()
    if not re.fullmatch(r'PAY\d{6}', pid):
        return jsonify({'message': 'El formato del payment_id es inválido. Debe ser PAY123456'}), 400

    # 2) Llamar a GestiónReservas
    try:
        resp = requests.delete(
            f"{gestion_reservas_url}/cancel_payment_and_reservation/{pid}",
            timeout=20
        )
    except requests.exceptions.ConnectionError:
        return jsonify({'message': 'No se pudo conectar con GestiónReservas.'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'message': 'Timeout al contactar GestiónReservas.'}), 504

    # 3) Propagar resultado o error
    if resp.status_code == 200:
        return jsonify(resp.json()), 200
    else:
        if resp.headers.get('Content-Type', '').startswith('application/json'):
            return jsonify(resp.json()), resp.status_code
        return jsonify({'message': resp.text}), resp.status_code


################################################################################################


## Obtener todos los pagos generados desde el microservicio de pagos o GestiónReservas
## y devolver la respuesta al cliente
@app.route('/get_all_payments', methods=['GET'])
def get_all_payments():
    """
    Summary: Consulta todos los pagos generados
    Description:
      Consulta al microservicio de GestiónReservas para recuperar todos los pagos generados en memoria.
      Valida que la respuesta sea una lista válida. Si no hay pagos, devuelve un mensaje informativo.
    ---
    tags:
      - Payments
    responses:
      200:
        description: Lista de pagos o mensaje indicando que no hay pagos
        examples:
          application/json:
            [
              {
                "payment_id": "PAY123456",
                "reservation_id": 1,
                "amount": 150.0,
                "currency": "Colones",
                "payment_method": "Tarjeta",
                "status": "Pagado",
                "payment_date": "Abril 30, 2025 - 13:00:00",
                "transaction_reference": "ABC123DEF456"
              }
            ]
          application/json:
            {
              "message": "No hay pagos generados actualmente."
            }
      500:
        description: Error de conexión, validación o estructura inesperada
        examples:
          application/json:
            {
              "message": "Error de validación en los pagos",
              "errors": {
                "_schema": ["Invalid input type."]
              }
            }
    """
    try:
        gestion_reservas_url = os.getenv("GESTIONRESERVAS_SERVICE")
        url = f"{gestion_reservas_url}/get_all_fake_payments"

        response = requests.get(url, timeout=20)

        if response.status_code != 200:
            return jsonify({'message': f'Error al consultar pagos. Código: {response.status_code}'}), response.status_code

        data = response.json()

        if isinstance(data, dict) and "message" in data:
            mensaje = data["message"]
            if "no hay pagos" in mensaje.lower():
                return jsonify({"message": "No hay pagos generados actualmente."}), 200
            return jsonify(data), 200

        if not isinstance(data, list):
            return jsonify({
                "message": "Error de validación: se esperaba una lista de pagos",
                "raw_data": data
            }), 500

        if len(data) == 0:
            return jsonify({"message": "No hay pagos generados actualmente."}), 200

        validated_data = payment_schema.load(data, many=True)
        return jsonify(validated_data), 200

    except ValidationError as err:
        app.logger.warning("❌ Error de validación en los pagos")
        return jsonify({
            "message": "Error de validación en los pagos",
            "errors": err.messages
        }), 500

    except requests.RequestException as e:
        app.logger.error(f"❌ Error al conectar con el microservicio de pagos: {e}")
        return jsonify({'message': 'Error de conexión con el microservicio de pagos'}), 500

    except Exception as e:
        app.logger.exception("❌ Error inesperado al consultar pagos desde Usuario")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################


## Obtener un pago específico por su ID desde el microservicio de pagos o GestiónReservas
## y devolver la respuesta al cliente
@app.route('/get_payment_by_id/<string:payment_id>', methods=['GET'])
def get_payment_by_id(payment_id):
    """
    Summary: Obtiene un pago específico por su ID
    Description:
      Recupera los detalles de un pago usando su identificador único `payment_id` desde el microservicio de pagos (GestiónReservas).
      Valida el formato del identificador. Si el ID es inválido, no existe o hay un error de conexión, devuelve un mensaje apropiado.
    ---
    tags:
      - Payments
    produces:
      - application/json
    parameters:
      - name: payment_id
        in: path
        type: string
        required: true
        description: "ID único del pago formato: PAY123456"
        example: PAY123456
    responses:
      200:
        description: Detalles del pago encontrado
        examples:
          application/json:
            {
              "payment_id": "PAY123456",
              "reservation_id": 1,
              "amount": 150.0,
              "currency": "Dolares",
              "payment_method": "Tarjeta",
              "status": "Pagado",
              "payment_date": "Abril 30, 2025 - 13:00:00",
              "transaction_reference": "ABC123DEF456"
            }
      400:
        description: Formato inválido del ID
        examples:
          application/json:
            {
              "message": "El formato del payment_id es inválido. Debe ser como PAY123456"
            }
      404:
        description: Pago no encontrado
        examples:
          application/json:
            {
              "message": "No se encontró ningún pago con ID: PAY999999"
            }
      500:
        description: Error de conexión o interno
        examples:
          application/json:
            {
              "message": "Error de conexión con el microservicio de pagos"
            }
    """
    try:
        app.logger.info(f"🔍 Buscando pago con ID: {payment_id}")

        if not re.match(r"^PAY\d{6}$", payment_id.strip().upper()):
            return jsonify({'message': 'El formato del payment_id es inválido. Debe ser como PAY123456'}), 400

        gestion_reservas_url = os.getenv("GESTIONRESERVAS_SERVICE")
        url = f"{gestion_reservas_url}/get_payment_by_id/{payment_id}"

        response = requests.get(url, timeout=20)

        if response.status_code == 404:
            return jsonify({'message': f'No se encontró ningún pago con ID: {payment_id}'}), 404
        elif response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            app.logger.error(f"⚠️ Error inesperado al consultar pago. Código: {response.status_code}")
            return jsonify({'message': f'Error consultando pago. Código: {response.status_code}'}), 500

    except requests.RequestException as e:
        app.logger.error(f"❌ Error de red al contactar microservicio: {e}")
        return jsonify({'message': 'Error de conexión con el microservicio de pagos'}), 500
    except Exception as e:
        app.logger.exception("❌ Error inesperado al consultar pago por ID")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################


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


## Crear un nuevo pago para una reserva existente
## en el microservicio de Gestión de Reservas
## y devolver la respuesta al cliente
@app.route('/usuario/create_payment', methods=['POST'])
def usuario_create_payment():
    """
    Summary: Crea un nuevo pago desde el microservicio Usuario
    Description:
      Valida los datos básicos, comprueba que la reserva exista en GestiónReservas,
      delega la creación del pago a GestiónReservas y, si tiene éxito,
      notifica a GestiónVuelos para marcar el asiento como 'Pagado'.
    ---
    tags:
      - Payments
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para registrar el pago
        schema:
          type: object
          required:
            - reservation_id
            - payment_method
          properties:
            reservation_id:
              type: integer
              example: 1
            payment_method:
              type: string
              enum: ["Tarjeta", "PayPal", "Transferencia","SINPE"]
              example: "Tarjeta"
            currency:
              type: string
              enum: ["Dolares", "Colones"]
              example: "Dolares"
    responses:
      201:
        description: Pago registrado exitosamente
      400:
        description: Datos inválidos
      404:
        description: Reserva no encontrada en GestiónReservas
      409:
        description: Pago duplicado para la reserva
      503:
        description: Servicio no disponible (GestiónReservas / GestiónVuelos)
      504:
        description: Timeout
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No se recibió cuerpo JSON'}), 400

        # 1) Validación local
        reservation_id = data.get("reservation_id")
        payment_method = data.get("payment_method")
        currency = data.get("currency", "Dolares")

        if not isinstance(reservation_id, int) or reservation_id <= 0:
            return jsonify({'message': 'El reservation_id debe ser un entero positivo.'}), 400
        if payment_method not in ["Tarjeta", "PayPal", "Transferencia"]:
            return jsonify({'message': 'Método de pago inválido.'}), 400
        if currency not in ["Dolares", "Colones"]:
            return jsonify({'message': 'Moneda no soportada.'}), 400

        gestion_reservas = os.getenv("GESTIONRESERVAS_SERVICE")
        gestion_vuelos   = os.getenv("GESTIONVUELOS_SERVICE")
        timeout          = 20

        # 2) Verificar existencia de la reserva
        try:
            chk = requests.get(
                f"{gestion_reservas}/get_reservation_by_id/{reservation_id}",
                timeout=timeout
            )
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónReservas.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al consultar reserva en GestiónReservas.'}), 504

        if chk.status_code == 404:
            return jsonify({'message': f'Reserva con ID {reservation_id} no encontrada.'}), 404
        if chk.status_code != 200:
            return jsonify({'message': 'Error validando reserva en GestiónReservas.'}), chk.status_code

        reserva = chk.json()
        airplane_id = reserva.get("airplane_id")
        seat_number = reserva.get("seat_number")

        # 3) Delegar la creación del pago a GestiónReservas
        try:
            resp = requests.post(
                f"{gestion_reservas}/create_payment",
                json={
                    'reservation_id': reservation_id,
                    'payment_method': payment_method,
                    'currency': currency
                },
                timeout=timeout
            )
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónReservas al crear el pago.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al crear el pago en GestiónReservas.'}), 504

        if resp.status_code != 201:
            # Propagar error de GestiónReservas (400, 404, 409...)
            body = resp.json() if resp.headers.get('Content-Type','').startswith('application/json') else {'message': resp.text}
            return jsonify(body), resp.status_code

        payment = resp.json().get("payment", {})

        # 4) Notificar a GestiónVuelos para marcar el asiento como 'Pagado'
        try:
            vuelo_resp = requests.put(
                f"{gestion_vuelos}/update_seat_status/{airplane_id}/seats/{seat_number}",
                json={"status": "Pagado"},
                timeout=20
            )
            if vuelo_resp.status_code != 200:
                logging.warning(f"⚠️ GestiónVuelos devolvió {vuelo_resp.status_code} al marcar asiento {seat_number} como Pagado.")
        except requests.exceptions.ConnectionError:
            return jsonify({'message': 'No se pudo conectar con GestiónVuelos.'}), 503
        except requests.exceptions.Timeout:
            return jsonify({'message': 'Timeout al notificar asiento en GestiónVuelos.'}), 504

        return jsonify({
            'message': '✅ Pago registrado y asiento marcado como pagado.',
            'payment': payment
        }), 201

    except Exception:
        logging.exception("❌ Error inesperado en Usuario al crear el pago")
        return jsonify({'message': 'Error interno del servidor'}), 500


################################################################################################


## Editar un pago existente desde el microservicio de pagos o GestiónReservas
## y devolver la respuesta al cliente
@app.route('/usuario/edit_payment/<string:payment_id>', methods=['PUT'])
def usuario_edit_payment(payment_id):
    """
    Summary: Edita un pago existente desde Usuario
    Description:
      Permite modificar método de pago, fecha o referencia de un pago existente
      delegando la operación a GestiónReservas.

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
        description: ID único del pago (formato PAY123456)
      - in: body
        name: body
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
      503:
        description: No se pudo conectar con GestiónReservas
      504:
        description: Timeout al contactar GestiónReservas
      500:
        description: Error interno del servidor
    """
    # 1) Verificar formato del ID
    pid = payment_id.strip().upper()
    if not re.fullmatch(r'PAY\d{6}', pid):
        return jsonify({'message': 'El formato del payment_id es inválido. Debe ser PAY123456'}), 400

    # 2) Validar body
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No se recibió cuerpo JSON'}), 400

    allowed = {'payment_method', 'payment_date', 'transaction_reference'}
    if not set(data.keys()).issubset(allowed):
        return jsonify({'message': 'Solo se pueden actualizar: payment_method, payment_date, transaction_reference'}), 400

    # 3) Reenviar a GestiónReservas
    gestion_reservas = os.getenv("GESTIONRESERVAS_SERVICE")
    timeout = 20

    try:
        resp = requests.put(
            f"{gestion_reservas}/edit_payment/{pid}",
            json=data,
            timeout=timeout
        )
    except requests.exceptions.ConnectionError:
        return jsonify({'message': 'No se pudo conectar con GestiónReservas'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'message': 'Timeout al contactar GestiónReservas'}), 504

    # 4) Propagar respuesta
    if resp.headers.get('Content-Type','').startswith('application/json'):
        body = resp.json()
    else:
        body = {'message': resp.text}

    return jsonify(body), resp.status_code


################################################################################################


# Iniciar la aplicación
if __name__ == '__main__':

    app.run(debug=True, port=5003)
