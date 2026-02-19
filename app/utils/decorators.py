from flask import request, jsonify
from functools import wraps
from config import Config

def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing bearer token"}), 401

        token = auth_header.replace("Bearer ", "").strip()

        if Config.INTEGRATIONS_TOKEN != token:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated