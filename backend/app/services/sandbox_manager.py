import json
import shutil
import socket
import subprocess
import tempfile
import uuid

from pathlib import Path

DOCKER = shutil.which("docker") or "docker"

class SandboxManager:

    def __init__(self):
        self.base_dir = (
            Path(tempfile.gettempdir()) / "repopilot"
        )

        self.base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ==================================================
    # WORKSPACE
    # ==================================================

    def create_workspace(self):

        sandbox_id = str(uuid.uuid4())

        workspace = (
            self.base_dir / sandbox_id
        )

        workspace.mkdir(
            parents=True,
            exist_ok=True,
        )

        return sandbox_id, workspace

    # ==================================================
    # CLONE
    # ==================================================

    def clone_repository(
        self,
        repo_url: str,
        workspace: Path,
    ):

        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                repo_url,
                str(workspace / "repo"),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:

            raise RuntimeError(
                result.stderr.strip()
                or "Failed to clone repository"
            )

    # ==================================================
    # FIND APPLICATION
    # ==================================================

    def find_application(
        self,
        repo_path: Path,
    ):

        # ----------------------------------------------
        # Root application
        # ----------------------------------------------

        if (
            (repo_path / "package.json").exists()
            or (repo_path / "requirements.txt").exists()
            or (repo_path / "index.html").exists()
        ):

            return repo_path

        # ----------------------------------------------
        # Immediate subdirectories
        # ----------------------------------------------

        ignored = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            "dist",
            "build",
        }

        for directory in repo_path.iterdir():

            if not directory.is_dir():
                continue

            if directory.name in ignored:
                continue

            if (
                (directory / "package.json").exists()
                or (
                    directory / "requirements.txt"
                ).exists()
                or (
                    directory / "index.html"
                ).exists()
            ):

                return directory

        raise RuntimeError(
            "No runnable application found in repository."
        )

    # ==================================================
    # DOCKERFILE GENERATOR
    # ==================================================

    def generate_dockerfile(
        self,
        repo_path: Path,
    ):

        # ----------------------------------------------
        # NODE
        # ----------------------------------------------

        package_json = (
            repo_path / "package.json"
        )

        if package_json.exists():

            try:

                package_data = json.loads(
                    package_json.read_text()
                )

            except Exception:

                raise RuntimeError(
                    "Unable to read package.json."
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

        # ----------------------------------------------
        # PYTHON
        # ----------------------------------------------

        requirements = (
            repo_path / "requirements.txt"
        )

        if requirements.exists():

            if (
                repo_path / "manage.py"
            ).exists():

                dockerfile = """
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
"""

                port = 8000

            else:

                dockerfile = """
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
"""

                port = 8000

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

        # ----------------------------------------------
        # STATIC
        # ----------------------------------------------

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
    # BUILD
    # ==================================================

    def build_image(
        self,
        workspace: Path,
        sandbox_id: str,
    ):

        repo_path = self.find_application(
            workspace / "repo"
        )

        image_name = (
            f"repopilot-{sandbox_id}"
        )

        result = subprocess.run(
            [
                DOCKER,
                "build",
                "-t",
                image_name,
                str(repo_path),
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:

            raise RuntimeError(
                result.stderr.strip()
                or "Docker build failed"
            )

        return image_name

    # ==================================================
    # PORT
    # ==================================================

    def find_available_port(self):

        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        ) as sock:

            sock.bind(
                ("127.0.0.1", 0)
            )

            return sock.getsockname()[1]

    # ==================================================
    # START
    # ==================================================

    def start_container(
        self,
        image_name: str,
        sandbox_id: str,
        container_port: int = 3000,
    ):

        host_port = (
            self.find_available_port()
        )

        container_name = (
            f"repopilot-{sandbox_id}"
        )

        result = subprocess.run(
            [
                DOCKER,
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
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:

            raise RuntimeError(
                result.stderr.strip()
                or "Failed to start container"
            )

        return {
            "container_id": result.stdout.strip(),
            "container_name": container_name,
            "host_port": host_port,
            "container_port": container_port,
        }

        # ==================================================
    # STATUS
    # ==================================================

    def get_container_status(
        self,
        container_name: str,
    ):
        result = subprocess.run(
            [
                DOCKER,
                "inspect",
                "-f",
                "{{.State.Status}}",
                container_name,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return "NOT_FOUND"

        status = result.stdout.strip().lower()

        if status == "running":
            return "RUNNING"

        if status == "exited":
            return "STOPPED"

        if status == "created":
            return "CREATED"

        if status == "paused":
            return "PAUSED"

        if status == "restarting":
            return "RESTARTING"

        if status == "dead":
            return "DEAD"

        return status.upper()

    # ==================================================
    # STOP
    # ==================================================

    def stop_container(
        self,
        container_name: str,
    ):

        subprocess.run(
            [
                DOCKER,
                "rm",
                "-f",
                container_name,
            ],
            capture_output=True,
            text=True,
        )

    # ==================================================
    # CLEANUP
    # ==================================================

    def cleanup_workspace(
        self,
        workspace: Path,
    ):

        shutil.rmtree(
            workspace,
            ignore_errors=True,
        )

        # ==================================================
    # DELETE SANDBOX
    # ==================================================

    def delete_sandbox(
        self,
        sandbox_id: str,
        container_name: str,
        workspace: Path | None = None,
        image_name: str | None = None,
    ):
        # Stop and remove container
        self.stop_container(container_name)

        # Remove Docker image
        if image_name:
            subprocess.run(
                [
                    DOCKER,
                    "rmi",
                    "-f",
                    image_name,
                ],
                capture_output=True,
                text=True,
            )

        # Remove workspace
        if workspace:
            self.cleanup_workspace(workspace)