from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from jwt import ExpiredSignatureError
from app.utils.messages import INVALID_TOKEN_NO_SUBJECT
from app.utils.methods import create_exception_response

SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=20))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        device_id: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        if device_id is None:
            return create_exception_response(400, INVALID_TOKEN_NO_SUBJECT)
        return device_id, user_id
    except ExpiredSignatureError:
        return create_exception_response(401, "Token has expired")
    except JWTError:
        return create_exception_response(401, "Invalid token")
