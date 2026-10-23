"""Register an EduMate service account and API key with the existing RAG service.

The RAG project is never modified: this script only calls its public HTTP API.

Usage::

    python scripts/register_rag_key.py
    python scripts/register_rag_key.py --base-url http://127.0.0.1:18000 --force

The plaintext API key is written to the local ``.env`` only (git-ignored).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"

DEFAULT_USERNAME = "edumate_service"
DEFAULT_PASSWORD = "EduMateRag@2026"
DEFAULT_KEY_NAME = "edumate_service"


def _read_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def _write_env_value(path: Path, key: str, value: str) -> None:
    if not path.exists():
        path = ENV_FILE
        if ENV_EXAMPLE.exists():
            path.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    lines = path.read_text(encoding="utf-8").splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[index] = f"{key}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return str(body["error"].get("message") or body["error"])
    if isinstance(body, dict) and body.get("detail"):
        return str(body["detail"])
    return response.text[:200]


def _verify_key(client: httpx.Client, key: str) -> bool:
    response = client.get("/v1/kb/groups", headers={"X-API-Key": key})
    return response.status_code == 200


def main() -> int:
    parser = argparse.ArgumentParser(description="Register an EduMate RAG service API key")
    parser.add_argument(
        "--base-url",
        default=os.getenv("RAG_BASE_URL", "http://127.0.0.1:18000"),
        help="RAG service base URL (default: %(default)s)",
    )
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--key-name", default=DEFAULT_KEY_NAME)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Create a new key even if the existing .env key is still valid",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    with httpx.Client(base_url=base_url, timeout=30) as client:
        health = client.get("/healthz")
        if health.status_code != 200:
            print(f"RAG service is not reachable at {base_url}: HTTP {health.status_code}")
            return 1

        existing_key = _read_env_value(ENV_FILE, "RAG_API_KEY")
        if existing_key and not args.force and _verify_key(client, existing_key):
            print(f"Existing RAG_API_KEY is valid (prefix {existing_key[:10]}...); nothing to do.")
            return 0

        register = client.post(
            "/auth/register",
            json={"username": args.username, "password": args.password},
        )
        if register.status_code == 201:
            print(f"Registered RAG service account: {args.username}")
        elif register.status_code in {400, 409}:
            print(f"RAG service account already exists: {args.username}")
        else:
            print(f"Failed to register RAG account: HTTP {register.status_code} {_error(register)}")
            return 1

        login = client.post(
            "/auth/login",
            json={"username": args.username, "password": args.password},
        )
        if login.status_code != 200:
            print(
                "Failed to login to the RAG service. If the account already exists with "
                f"another password, pass --password. HTTP {login.status_code} {_error(login)}"
            )
            return 1
        token = login.json()["access_token"]

        created = client.post(
            "/api-keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": args.key_name},
        )
        if created.status_code != 201:
            print(f"Failed to create API key: HTTP {created.status_code} {_error(created)}")
            return 1

        payload = created.json()
        key = payload["key"]
        if not _verify_key(client, key):
            print("The new API key could not access /v1/kb/groups; aborting.")
            return 1

        _write_env_value(ENV_FILE, "RAG_API_KEY", key)
        _write_env_value(ENV_FILE, "RAG_BASE_URL", base_url)
        print(
            f"Created API key '{payload['name']}' (prefix {payload['key_prefix']}); "
            f"written to {ENV_FILE} (git-ignored)."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
