"""HTTP contract for the camera and the guard's dashboard."""
import os
import re
from datetime import datetime, timezone

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from storage import ParkingStore

PLATE = re.compile(r'[A-Z0-9-]{3,12}', re.ASCII)


def normalize_plate(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value.isascii():
        return None
    value = value.upper()
    return value if PLATE.fullmatch(value) else None


def create_app(store=None, capacity=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 4096
    capacity = int(capacity if capacity is not None else os.getenv('PARKING_CAPACITY', '5'))
    if capacity < 1:
        raise ValueError('PARKING_CAPACITY must be positive')
    if store is None:
        client = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), decode_responses=True,
                             socket_connect_timeout=2, socket_timeout=2,
                             retry=Retry(NoBackoff(), 0))
        store = ParkingStore(client)

    @app.errorhandler(redis.exceptions.RedisError)
    def storage_error(error):
        app.logger.warning('Redis unavailable: %s', type(error).__name__)
        return jsonify(error='Parking data is temporarily unavailable. Please try again.'), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.get('/api/health')
    def health():
        store.ping()
        return jsonify(status='ok')

    @app.get('/api/parking')
    def parking():
        snapshot = store.snapshot()
        count = len(snapshot['vehicles'])
        return jsonify(**snapshot, count=count, capacity=capacity, full=count >= capacity)

    @app.post('/api/entries')
    def entry():
        body = request.get_json(silent=True)
        plate = normalize_plate(body.get('plate')) if isinstance(body, dict) else None
        if plate is None:
            return jsonify(error='Enter a plate with 3–12 letters, digits, or hyphens.'), 400
        entered_at = datetime.now(timezone.utc).isoformat()
        result = store.admit(plate, entered_at, capacity)
        if result != 'created':
            message = 'This car is already parked.' if result == 'duplicate' else 'Parking lot is full. Release a car first.'
            return jsonify(error=message, code=result), 409
        return jsonify(plate=plate, entered_at=entered_at), 201

    @app.delete('/api/vehicles/<plate>')
    def release(plate):
        plate = normalize_plate(plate)
        if plate is None:
            return jsonify(error='Invalid plate.'), 400
        if not store.release(plate):
            return jsonify(error='This car is no longer parked.'), 404
        return '', 204

    return app
