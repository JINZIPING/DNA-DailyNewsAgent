from __future__ import annotations

from contextlib import contextmanager
import os
import subprocess
import time
from urllib import error, request


DEFAULT_RSSHUB_IMAGE = "diygod/rsshub:chromium-bundled"
DEFAULT_RSSHUB_PORT = 1200


def rsshub_route_url(route: str, *, base_url: str) -> str:
    normalized_route = route.strip()
    if normalized_route.startswith("rsshub://"):
        normalized_route = "/" + normalized_route.removeprefix("rsshub://")
    if not normalized_route.startswith("/"):
        normalized_route = "/" + normalized_route
    return base_url.rstrip("/") + normalized_route


@contextmanager
def temporary_rsshub(
    *,
    image: str = DEFAULT_RSSHUB_IMAGE,
    port: int = DEFAULT_RSSHUB_PORT,
):
    container_name = f"dna-rsshub-{os.getpid()}"
    env_args, docker_env = _rsshub_env()
    _run_docker(
        [
            "run",
            "--rm",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{port}:1200",
            "-e",
            "NODE_ENV=production",
            *env_args,
            image,
        ],
        env=docker_env,
    )
    try:
        _wait_for_rsshub(port)
        yield f"http://127.0.0.1:{port}"
    finally:
        subprocess.run(
            ["docker", "stop", container_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _run_docker(args: list[str], *, env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(
            ["docker", *args],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Docker is required for one-time RSSHub fetches.") from exc
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() if exc.stderr else "no Docker error output"
        raise RuntimeError(f"Failed to start temporary RSSHub container: {details}") from exc


def _rsshub_env() -> tuple[list[str], dict[str, str]]:
    docker_env = os.environ.copy()
    github_token = os.getenv("RSSHUB_GITHUB_ACCESS_TOKEN")
    if not github_token:
        return [], docker_env
    docker_env["GITHUB_ACCESS_TOKEN"] = github_token
    return ["-e", "GITHUB_ACCESS_TOKEN"], docker_env


def _wait_for_rsshub(port: int) -> None:
    health_url = f"http://127.0.0.1:{port}/healthz"
    deadline = time.time() + 60
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with request.urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, error.URLError) as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"RSSHub did not become ready in time: {last_error}")
