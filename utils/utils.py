import base64
import pickle
import re

from passlib.context import CryptContext
import time
import uuid
import json
import re
from pydantic import BaseModel
from typing import Any, Dict, Union

crypt_context = CryptContext(schemes=["bcrypt"])

def sanitize_filename_base(name: str) -> str:
    """
    Replace any character that is not a-z, A-Z, 0-9, underscore with '_'.
    This removes spaces, dots, accents, and special characters.
    """
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

def encode_for_cache(obj):
    return base64.b64encode(pickle.dumps(obj)).decode()

def decode_from_cache(data):
    return pickle.loads(base64.b64decode(data.encode()))

def encrypt_string(plain_string: str) -> str:
    """Encrypts a plain string using bcrypt."""
    return crypt_context.hash(plain_string)

def verify_string(plain_string: str, hashed_string: str) -> bool:
    """Verifies a plain string against a hashed string."""
    return crypt_context.verify(plain_string, hashed_string)

def serialize_for_redis(data: Any) -> str:
    """
    Serialize any Python object to a JSON string suitable for storing in Redis.
    Supports dicts, lists, primitives, and Pydantic models.
    """
    if data is None:
        return "null"

    if isinstance(data, str):
        return data

    if isinstance(data, (int, float, bool)):
        return json.dumps(data)

    if isinstance(data, BaseModel):
        return data.model_dump_json()

    if isinstance(data, (list, dict)):
        return json.dumps(data)

    try:
        #if everything fails, then the data is an custom object, so convert it to a dict and return it
        return json.dumps(data.__dict__)
    except (AttributeError, TypeError):
        #data is weird and cannot be serialized, so we return it as a string
        return str(data)
