# 认证与权限服务。
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

from ..config import ConfigError, get_config
from ..db import db_cursor


class AuthError(Exception):
    pass


def _get_auth_config() -> Dict[str, Any]:
    config = get_config()
    auth_config = config["auth"]
    algorithm = auth_config["hash_algorithm"]
    if algorithm not in {"sha256", "sha512"}:
        raise ConfigError("auth.hash_algorithm 仅支持 sha256/sha512")
    return auth_config


def _hash_password(password: str, salt_hex: str, algorithm: str) -> str:
    try:
        salt_bytes = bytes.fromhex(salt_hex)
    except ValueError as exc:
        raise AuthError("passwordSalt 必须为 hex 编码") from exc

    hasher = hashlib.new(algorithm)
    hasher.update(salt_bytes)
    hasher.update(password.encode("utf-8"))
    return hasher.hexdigest()


def verify_password(password: str, passwordHash: str, passwordSalt: str) -> bool:
    auth_config = _get_auth_config()
    algorithm = auth_config["hash_algorithm"]
    computed = _hash_password(password, passwordSalt, algorithm)
    return hmac.compare_digest(computed, passwordHash)


def _encode_part(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode_part(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def issue_token(payload: Dict[str, Any]) -> str:
    auth_config = _get_auth_config()
    secret = auth_config["token_secret"].encode("utf-8")
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = hmac.new(secret, data, hashlib.sha256).digest()
    return f"{_encode_part(data)}.{_encode_part(signature)}"


def verify_token(token: str) -> Dict[str, Any]:
    auth_config = _get_auth_config()
    secret = auth_config["token_secret"].encode("utf-8")

    parts = token.split(".")
    if len(parts) != 2:
        raise AuthError("token 格式错误")

    data = _decode_part(parts[0])
    signature = _decode_part(parts[1])
    expected = hmac.new(secret, data, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise AuthError("token 签名无效")

    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise AuthError("token payload 非对象")

    now = int(time.time())
    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise AuthError("token exp 无效")
    if now >= exp:
        raise AuthError("token 已过期")

    return payload


def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    with db_cursor() as cursor:
        cursor.execute(
            'SELECT id, username, "passwordHash", "passwordSalt", "isGuest" FROM users WHERE username = %s',
            (username,),
        )
        user = cursor.fetchone()

        if user is None:
            raise AuthError("用户名或密码错误")

        if not verify_password(password, user["passwordHash"], user["passwordSalt"]):
            raise AuthError("用户名或密码错误")

        cursor.execute(
            """
            SELECT roles.name
            FROM roles
            JOIN user_roles ON user_roles."roleId" = roles.id
            WHERE user_roles."userId" = %s
            """,
            (user["id"],),
        )
        roles = [row["name"] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT permissions."permKey"
            FROM permissions
            JOIN role_permissions ON role_permissions."permId" = permissions.id
            JOIN user_roles ON user_roles."roleId" = role_permissions."roleId"
            WHERE user_roles."userId" = %s
            """,
            (user["id"],),
        )
        permissions = [row["permKey"] for row in cursor.fetchall()]

    return {
        "id": user["id"],
        "username": user["username"],
        "isGuest": user["isGuest"],
        "roles": roles,
        "permissions": permissions,
    }


def get_user_by_id(userId: int) -> Optional[Dict[str, Any]]:
    with db_cursor() as cursor:
        cursor.execute('SELECT id, username, "isGuest" FROM users WHERE id = %s', (userId,))
        user = cursor.fetchone()
        if user is None:
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "isGuest": user["isGuest"],
        }


def issue_login_response(username: str, password: str) -> Dict[str, Any]:
    auth_config = _get_auth_config()
    user = authenticate_user(username, password)
    now = int(time.time())
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "roles": user["roles"],
        "iat": now,
        "exp": now + auth_config["token_ttl_seconds"],
    }
    token = issue_token(payload)
    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "isGuest": user["isGuest"],
        },
        "roles": user["roles"],
        "permissions": user["permissions"],
        "token": token,
    }
