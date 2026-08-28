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
    version="1.0.0",
)


RUNNER_API_KEY = os.getenv("RUNNER_API_KEY")

BASE_DIR = Path(
    os.getenv(
        "RUNNER_WORKSPACE",
        "/tmp/repopilot",
    )
)

BASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==================================================
# AUTH
# ==================================================

def verify_runner_key(
    authorization: str | None,
):
    if not RUNNER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="RUNNER_API_KEY is not configured",
        )

    expected = f"Bearer {RUNNER_API_KEY}"

    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid runner authentication",
        )


# ==================================================
# REQUEST MODELS
# ==================================================

class LaunchRequest(BaseModel):
    sandbox_id: str
    repo_url: HttpUrl
    container_port: int = 3000


class StopRequest(BaseModel):
    sandbox_id: str
    container_name: str


# ==================================================
# HELPERS
# ==================================================

def run_command(
    command: list[str],
    timeout: int = 600,
):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Command failed"
        )

    return result.stdout.strip()


def find_available_port():
    """
    Find a free TCP port on the runner.
    """

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as sock:

        sock.bind(
            ("0.0.0.0", 0)
        )

        return sock.getsockname()[1]


def detect_dockerfile_port(
    dockerfile: Path,
):
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

    if matches:
        return int(matches[-1])

    return 3000


def generate_dockerfile(
    repo_path: Path,
):
    package_json = (
        repo_path / "package.json"
    )

    if package_json.exists():

        import json

        package_data = json.loads(
            package_json.read_text()
        )

        dependencies = {
            **package_data.get(
                "dependencies",
                {},
            ),
            **package_data.get(
                "devDependencies",
                {},
            ),
        }

        scripts = package_data.get(
            "scripts",
            {},
        )

        # ------------------------------------------
        # NEXT.JS
        # ------------------------------------------

        if "next" in dependencies:

            dockerfile = """
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
"""

            port = 3000

        # ------------------------------------------
        # VITE
        # ------------------------------------------

        elif "vite" in dependencies:

            dockerfile = """
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

EXPOSE 4173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0"]
"""

            port = 4173

        # ------------------------------------------
        # EXPRESS
        # ------------------------------------------

        elif "express" in dependencies:

            if "start" in scripts:

                command = [
                    "npm",
                    "start",
                ]

            else:

                command = [
                    "node",
                    "server.js",
                ]

            dockerfile = f"""
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD {json.dumps(command)}
"""

            port = 3000

        # ------------------------------------------
        # GENERIC NODE
        # ------------------------------------------

        else:

            if "start" in scripts:

                command = [
                    "npm",
                    "start",
                ]

            else:

                command = [
                    "node",
                    "server.js",
                ]

            dockerfile = f"""
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD {json.dumps(command)}
"""

            port = 3000

        dockerfile_path = (
            repo_path / "Dockerfile"
        )

        dockerfile_path.write_text(
            dockerfile.strip()
        )

        return (
            dockerfile_path,
            port,
        )

    # ------------------------------------------
    # PYTHON
    # ------------------------------------------

    requirements = (
        repo_path / "requirements.txt"
    )

    if requirements.exists():

        dockerfile = """
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
"""

        dockerfile_path = (
            repo_path / "Dockerfile"
        )

        dockerfile_path.write_text(
            dockerfile.strip()
        )

        return (
            dockerfile_path,
            8000,
        )

    # ------------------------------------------
    # STATIC
    # ------------------------------------------

    if (
        repo_path / "index.html"
    ).exists():

        dockerfile = """
FROM nginx:alpine

COPY . /usr/share/nginx/html

EXPOSE 80
"""

        dockerfile_path = (
            repo_path / "Dockerfile"
        )

        dockerfile_path.write_text(
            dockerfile.strip()
        )

        return (
            dockerfile_path,
            80,
        )

    raise RuntimeError(
        "Unable to determine project runtime."
    )


# ==================================================
# HEALTH
# ==================================================

@app.get("/health")
def health():
    docker_available = shutil.which(
        "docker"
    )

    if not docker_available:
        return {
            "status": "degraded",
            "docker": False,
        }

    try:

        run_command(
            [
                "docker",
                "info",
            ],
            timeout=20,
        )

        return {
            "status": "healthy",
            "docker": True,
        }

    except Exception as error:

        return {
            "status": "degraded",
            "docker": False,
            "error": str(error),
        }


# ==================================================
# LAUNCH
# ==================================================

@app.post("/runner/launch")
def launch(
    request: LaunchRequest,
    authorization: str | None = Header(
        default=None
    ),
):
    verify_runner_key(
        authorization
    )

    sandbox_id = request.sandbox_id

    workspace = (
        BASE_DIR / sandbox_id
    )

    container_name = (
        f"repopilot-{sandbox_id}"
    )

    image_name = (
        f"repopilot-{sandbox_id}"
    )

    try:

        # ------------------------------------------
        # Clean previous workspace
        # ------------------------------------------

        if workspace.exists():
            shutil.rmtree(
                workspace,
                ignore_errors=True,
            )

        workspace.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ------------------------------------------
        # Clone
        # ------------------------------------------

        repo_path = (
            workspace / "repo"
        )

        run_command(
            [
                "git",
                "clone",
                "--depth",
                "1",
                str(request.repo_url),
                str(repo_path),
            ],
            timeout=120,
        )

        # ------------------------------------------
        # Detect application
        # ------------------------------------------

        application_path = repo_path

        if not (
            (application_path / "package.json").exists()
            or (
                application_path / "requirements.txt"
            ).exists()
            or (
                application_path / "index.html"
            ).exists()
        ):

            candidates = [
                item
                for item in repo_path.iterdir()
                if item.is_dir()
                and item.name
                not in {
                    ".git",
                    "node_modules",
                    ".venv",
                    "venv",
                    "dist",
                    "build",
                }
            ]

            for candidate in candidates:

                if (
                    (candidate / "package.json").exists()
                    or (
                        candidate / "requirements.txt"
                    ).exists()
                    or (
                        candidate / "index.html"
                    ).exists()
                ):

                    application_path = candidate
                    break

        # ------------------------------------------
        # Dockerfile
        # ------------------------------------------

        dockerfile = (
            application_path / "Dockerfile"
        )

        if dockerfile.exists():

            container_port = (
                detect_dockerfile_port(
                    dockerfile
                )
            )

        else:

            _, container_port = (
                generate_dockerfile(
                    application_path
                )
            )

        # ------------------------------------------
        # Docker build
        # ------------------------------------------

        run_command(
            [
                "docker",
                "build",
                "-t",
                image_name,
                str(application_path),
            ],
            timeout=600,
        )

        # ------------------------------------------
        # Public runner port
        # ------------------------------------------

        host_port = find_available_port()

        # ------------------------------------------
        # Start container
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
        # Public preview URL
        # ------------------------------------------

        public_url = os.getenv(
            "RUNNER_PUBLIC_URL",
            "",
        ).rstrip("/")

        preview_url = (
            f"{public_url}/preview/"
            f"{sandbox_id}/"
            if public_url
            else None
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
            "preview_url": preview_url,
            "status": "RUNNING",
        }

    except Exception as error:

        # ------------------------------------------
        # Cleanup container
        # ------------------------------------------

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

        # ------------------------------------------
        # Cleanup image
        # ------------------------------------------

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

        # ------------------------------------------
        # Cleanup workspace
        # ------------------------------------------

        shutil.rmtree(
            workspace,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ==================================================
# STOP
# ==================================================

@app.post("/runner/stop")
def stop(
    request: StopRequest,
    authorization: str | None = Header(
        default=None
    ),
):
    verify_runner_key(
        authorization
    )

    subprocess.run(
        [
            "docker",
            "rm",
            "-f",
            request.container_name,
        ],
        capture_output=True,
        text=True,
    )

    image_name = (
        f"repopilot-{request.sandbox_id}"
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

    workspace = (
        BASE_DIR / request.sandbox_id
    )

    shutil.rmtree(
        workspace,
        ignore_errors=True,
    )

    return {
        "success": True,
        "sandbox_id": request.sandbox_id,
        "status": "STOPPED",
    }