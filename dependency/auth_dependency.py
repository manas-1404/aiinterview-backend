from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from jose import jwt, JWTError, ExpiredSignatureError
from starlette import status
from datetime import datetime, timedelta

from utils.config import settings

#this module automatically parses the request header containing the Bearer token and the jwt token
http_bearer = HTTPBearer()

def create_jwt_token(data: str) -> str:
    """
    Function to create a JWT token.
    :param data: The data to be encoded in the JWT token.
    :return: A JWT token as a string.
    """

    jwt_payload = {
        "sub": data,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_TOKEN_EXPIRATION_MINUTES),
        "iat": datetime.utcnow()
    }

    return jwt.encode(
        claims=jwt_payload,
        key=settings.JWT_SIGNATURE_SECRET_KEY,
        algorithm=settings.JWT_AUTH_ALGORITHM
    )

def create_jwt_refresh_token(data: str) -> str:
    """
    Function to create a JWT refresh token.
    :param data: The data to be encoded in the JWT refresh token.
    :return: A JWT refresh token as a string.
    """

    jwt_payload = {
        "sub": data,
        "exp": datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRATION_DAYS),
        "iat": datetime.utcnow()
    }

    return jwt.encode(
        claims=jwt_payload,
        key=settings.JWT_SIGNATURE_SECRET_KEY,
        algorithm=settings.JWT_AUTH_ALGORITHM
    )

def authenticate_request(http_credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):

    # retrieve the token by parsing the HTTPAuthorizationCredentials object, it will automatically contain the Bearer prefix and the jwt token
    jwt_token = http_credentials.credentials

    try:
        jwt_payload = jwt.decode(token=jwt_token, algorithms=settings.JWT_AUTH_ALGORITHM, key=settings.JWT_SIGNATURE_SECRET_KEY, options={"verify_signature": True, "verify_exp": True, "verify_sub": False})

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

    return jwt_payload
