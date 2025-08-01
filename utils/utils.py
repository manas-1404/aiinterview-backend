import base64
import pickle
import re


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