#!/usr/bin/env python3
import argparse
import secrets
import sys
from getpass import getpass

from server.config import ConfigError, get_config
from server.services.auth import _hash_password, _get_auth_config, AuthError


def _read_password(arg_password: str | None) -> str:
    if arg_password:
        return arg_password
    value = getpass("请输入明文密码: ").strip()
    if not value:
        raise ValueError("密码不能为空")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="生成用户密码哈希与盐（与服务端一致）")
    parser.add_argument("--password", help="明文密码（不建议在命令行明文传入）")
    parser.add_argument("--username", help="可选：用户名，用于生成 SQL 片段")
    parser.add_argument("--db", help="可选：数据库名，用于生成 SQL 片段")
    args = parser.parse_args()

    try:
        _ = get_config()
        auth_config = _get_auth_config()
    except (ConfigError, FileNotFoundError) as exc:
        print(f"配置加载失败: {exc}", file=sys.stderr)
        return 1

    password = _read_password(args.password)
    salt_bytes = auth_config["salt_bytes"]
    salt_hex = secrets.token_bytes(salt_bytes).hex()
    algorithm = auth_config["hash_algorithm"]

    try:
        password_hash = _hash_password(password, salt_hex, algorithm)
    except AuthError as exc:
        print(f"生成哈希失败: {exc}", file=sys.stderr)
        return 1

    print("hash_algorithm:", algorithm)
    print("passwordSalt:", salt_hex)
    print("passwordHash:", password_hash)

    if args.username:
        db_name = args.db or "<database>"
        print()
        print("SQL 示例(请按实际字段补齐):")
        print(
            'INSERT INTO users (username, "passwordHash", "passwordSalt", "isGuest", "crtTime", "uptTime")\n'
            f"VALUES ('{args.username}', '{password_hash}', '{salt_hex}', FALSE, NOW(), NOW());"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
