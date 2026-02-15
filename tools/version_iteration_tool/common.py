# 版本迭代工具通用函数。

import os
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Tuple

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env_file() -> None:
    if "LOTRO_ENV_PATH" in os.environ:
        env_path = Path(os.environ["LOTRO_ENV_PATH"]).expanduser().resolve()
        if not env_path.exists():
            raise FileNotFoundError(f"环境文件不存在: {env_path}")
        load_dotenv(env_path, override=False)
        return

    default_path = _project_root() / ".env"
    if default_path.exists():
        load_dotenv(default_path, override=False)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def _require_port(name: str) -> int:
    text = _require_env(name)
    if not text.isdigit():
        raise RuntimeError(f"端口环境变量必须为数字: {name}={text}")
    port = int(text)
    if port <= 0 or port > 65535:
        raise RuntimeError(f"端口环境变量超出范围: {name}={text}")
    return port


def _is_port_listening(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _wait_tunnel_ready(process: subprocess.Popen, local_port: int, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("SSH 隧道进程提前退出，请检查账号权限和网络连通性")
        if _is_port_listening("127.0.0.1", local_port):
            return
        time.sleep(0.1)
    raise RuntimeError(f"SSH 隧道超时未就绪: 127.0.0.1:{local_port}")


@contextmanager
def start_ssh_tunnel_from_env() -> Iterator[None]:
    if shutil.which("ssh") is None:
        raise RuntimeError("未找到 ssh 命令，请先安装 OpenSSH 客户端")

    ssh_host = _require_env("LOTRO_SSH_HOST")
    ssh_user = _require_env("LOTRO_SSH_USER")
    ssh_port = _require_port("LOTRO_SSH_PORT")
    local_port = _require_port("LOTRO_TUNNEL_PORT")
    remote_host = _require_env("LOTRO_REMOTE_DB_HOST")
    remote_port = _require_port("LOTRO_REMOTE_DB_PORT")

    if _is_port_listening("127.0.0.1", local_port):
        print(f"[INFO] 复用已存在 SSH 隧道端口: 127.0.0.1:{local_port}")
        yield
        return

    command = [
        "ssh",
        "-N",
        "-L",
        f"{local_port}:{remote_host}:{remote_port}",
        "-o",
        "ExitOnForwardFailure=yes",
        "-p",
        str(ssh_port),
        f"{ssh_user}@{ssh_host}",
    ]

    process = subprocess.Popen(command)
    tunnel_ready = False
    try:
        _wait_tunnel_ready(process, local_port, timeout_seconds=10.0)
        tunnel_ready = True
        print(f"[INFO] SSH 隧道已建立: 127.0.0.1:{local_port} -> {remote_host}:{remote_port}")
        yield
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3.0)
        if tunnel_ready:
            print("[INFO] SSH 隧道已关闭")


def require_key(data: Dict[str, Any], key: str, path: str) -> Any:
    if key not in data:
        raise ConfigError(f"缺少配置项: {path}{key}")
    return data[key]


def require_type(value: Any, expected_type: type, path: str) -> Any:
    if not isinstance(value, expected_type):
        raise ConfigError(f"配置项类型错误: {path} 期望 {expected_type.__name__}")
    return value


def require_identifier(value: str, path: str) -> str:
    if not value:
        raise ConfigError(f"标识符不能为空: {path}")
    first = value[0]
    if not (first.isalpha() or first == "_"):
        raise ConfigError(f"标识符不合法: {path}={value}")
    for char in value[1:]:
        if not (char.isalnum() or char == "_"):
            raise ConfigError(f"标识符不合法: {path}={value}")
    return value


def require_table_ref(value: str, path: str) -> str:
    parts = value.split(".")
    if len(parts) not in (1, 2):
        raise ConfigError(f"表名格式错误: {path}={value}")
    for idx, part in enumerate(parts):
        require_identifier(part, f"{path}.part{idx}")
    return value


def split_table_ref(table_ref: str) -> Tuple[str, str]:
    parts = table_ref.split(".")
    if len(parts) == 1:
        return "public", parts[0]
    return parts[0], parts[1]


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def quote_table_ref(table_ref: str) -> str:
    schema, table = split_table_ref(table_ref)
    return f"{quote_ident(schema)}.{quote_ident(table)}"


def table_exists(cursor, table_ref: str) -> bool:
    schema, table = split_table_ref(table_ref)
    cursor.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema = %s AND table_name = %s
        ) AS exists
        """,
        (schema, table),
    )
    return bool(cursor.fetchone()["exists"])


def column_exists(cursor, table_ref: str, column_name: str) -> bool:
    schema, table = split_table_ref(table_ref)
    cursor.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.columns
          WHERE table_schema = %s AND table_name = %s AND column_name = %s
        ) AS exists
        """,
        (schema, table, column_name),
    )
    return bool(cursor.fetchone()["exists"])


def constraint_exists(cursor, table_ref: str, constraint_name: str) -> bool:
    schema, table = split_table_ref(table_ref)
    cursor.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.table_constraints
          WHERE table_schema = %s AND table_name = %s AND constraint_name = %s
        ) AS exists
        """,
        (schema, table, constraint_name),
    )
    return bool(cursor.fetchone()["exists"])


def load_yaml_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConfigError("配置文件根对象必须为 YAML 对象")
    return data
