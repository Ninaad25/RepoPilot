import os
import shutil
import socket
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, HttpUrl


app = FastAPI(
    title="RepoPilot Sandbox Runner",
    version="0.1.0",
)


RUNNER_SECRET = os.getenv("RUNNER_SECRET")

if not RUNNER_SECRET:
    raise RuntimeError("RUNNER_SECRET is not configured")


class LaunchRequest(BaseModel):
    url: HttpUrl


def check_auth(authorization: str | None):
    expected = f"Bearer {RUNNER_SECRET}"

    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid runner authentication.",
        )


def find_available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("0.0.0.0", 0))
        return sock.getsockname()[1]


def run_command(command, timeout=600):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "Command failed."
        )

    return result.stdout.strip()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "RepoPilot Sandbox Runner",
    }


@app.post("/launch")
def launch(
    request: LaunchRequest,
    authorization: str | None = Header(default=None),
):
    check_auth(authorization)

    sandbox_id = str(uuid.uuid4())

    base_dir = Path("/tmp/repopilot")
    workspace = base_dir / sandbox_id

    workspace.mkdir(
        parents=True,
        exist_ok=True,
    )

    repo_path = workspace / "repo"

    image_name = f"repopilot-{sandbox_id}"
    container_name = f"repopilot-{sandbox_id}"

    try:
        # ------------------------------------------
        # Clone
        # ------------------------------------------

        run_command(
            [
                "git",
                "clone",
                "--depth",
                "1",
                str(request.url),
                str(repo_path),
            ],
            timeout=120,
        )

        # ------------------------------------------
        # Find application
        # ------------------------------------------

        app_path = repo_path

        if not (
            (app_path / "package.json").exists()
            or (app_path / "requirements.txt").exists()
            or (app_path / "index.html").exists()
        ):
            candidates = [
                directory
                for directory in repo_path.iterdir()
                if directory.is_dir()
                and directory.name not in {
                    ".git",
                    "node_modules",
                    ".venv",
                    "venv",
                    "dist",
                    "build",
                }
            ]

            found = None

            for directory in candidates:
                if (
                    (directory / "package.json").exists()
                    or (directory / "requirements.txt").exists()
                    or (directory / "index.html").exists()
                ):
                    found = directory
                    break

            if not found:
                raise RuntimeError(
                    "No runnable application found in repository."
                )

            app_path = found

        # ------------------------------------------
        # Dockerfile
        # ------------------------------------------

        dockerfile = app_path / "Dockerfile"

        if not dockerfile.exists():

            if (app_path / "package.json").exists():

                dockerfile.write_text(
                    """FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

EXPOSE 4173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0"]
"""
                )

                container_port = 4173

            elif (app_path / "requirements.txt").exists():

                dockerfile.write_text(
                    """FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
"""
                )

                container_port = 8000

            else:

                dockerfile.write_text(
                    """FROM nginx:alpine

COPY . /usr/share/nginx/html

EXPOSE 80
"""
                )

                container_port = 80

        else:

            import re

            text = dockerfile.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            matches = re.findall(
                r"EXPOSE\s+(\d+)",
                text,
                flags=re.IGNORECASE,
            )

            container_port = (
                int(matches[-1])
                if matches
                else 3000
            )

        # ------------------------------------------
        # Build
        # ------------------------------------------

        run_command(
            [
                "docker",
                "build",
                "-t",
                image_name,
                str(app_path),
            ],
            timeout=600,
        )

        # ------------------------------------------
        # Port
        # ------------------------------------------

        host_port = find_available_port()

        # ------------------------------------------
        # Run
        # ------------------------------------------

        container_id = run_command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--pids-limit",
                "100",
                "--network",
                "bridge",
                "-p",
                f"{host_port}:{container_port}",
                image_name,
            ],
            timeout=60,
        )

        # ------------------------------------------
        # Public URL
        # ------------------------------------------

        public_base_url = os.getenv(
            "RUNNER_PUBLIC_URL",
            "",
        ).rstrip("/")

        if not public_base_url:
            raise RuntimeError(
                "RUNNER_PUBLIC_URL is not configured."
            )

        preview_url = (
            f"{public_base_url}/sandbox/{sandbox_id}"
        )

        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "container_id": container_id,
            "container_name": container_name,
            "image_name": image_name,
            "workspace": str(workspace),
            "host_port": host_port,
            "container_port": container_port,
            "status": "RUNNING",
            "preview_url": preview_url,
        }

    except Exception:

        subprocess.run(
            [
                "docker",
                "rm",
                "-f",
                container_name,
            ],
            capture_output=True,
            text=True,
        )

        subprocess.run(
            [
                "docker",
                "rmi",
                "-f",
                image_name,
            ],
            capture_output=True,
            text=True,
        )

        shutil.rmtree(
            workspace,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=400,
            detail="Sandbox launch failed.",
        )


@app.get("/sandbox/{sandbox_id}")
def sandbox_proxy_info(
    sandbox_id: str,
):
    return {
        "sandbox_id": sandbox_id,
        "message": "Sandbox proxy endpoint.",
    }
