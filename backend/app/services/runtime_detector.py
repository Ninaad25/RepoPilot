from __future__ import annotations

import json
import re
from pathlib import Path


class RuntimeDetector:

    """
    Detects the runtime and likely application port.

    Supports:
    - Node.js
    - Vite
    - React
    - Next.js
    - Express
    - FastAPI
    - Flask
    - Django
    - Static HTML
    - Nested frontend/backend repositories
    """

    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------

    def detect(
        self,
        repo_path: Path | str,
    ) -> dict:

        repo_path = Path(
            repo_path
        ).resolve()

        package_files = list(
            self._find_files(
                repo_path,
                "package.json",
            )
        )

        requirements_files = list(
            self._find_files(
                repo_path,
                "requirements.txt",
            )
        )

        pyproject_files = list(
            self._find_files(
                repo_path,
                "pyproject.toml",
            )
        )

        # ----------------------------------------------------
        # Node.js
        # ----------------------------------------------------

        if package_files:

            applications = []

            for package_file in package_files:

                package = self._read_json(
                    package_file
                )

                dependencies = {}

                dependencies.update(
                    package.get(
                        "dependencies",
                        {},
                    )
                    or {}
                )

                dependencies.update(
                    package.get(
                        "devDependencies",
                        {},
                    )
                    or {}
                )

                scripts = (
                    package.get(
                        "scripts",
                        {},
                    )
                    or {}
                )

                if "vite" in dependencies:

                    runtime = "Node.js"
                    application_type = "Frontend"
                    port = 5173

                elif "next" in dependencies:

                    runtime = "Node.js"
                    application_type = "Full-stack"
                    port = 3000

                elif (
                    "express" in dependencies
                ):

                    runtime = "Node.js"
                    application_type = "Backend"
                    port = 3000

                else:

                    runtime = "Node.js"
                    application_type = "Node.js"
                    port = 3000

                detected_port = self._detect_port(
                    package_file.parent
                )

                if detected_port:
                    port = detected_port

                applications.append(
                    {
                        "name": package.get(
                            "name"
                        )
                        or package_file.parent.name,

                        "path": str(
                            package_file.parent.relative_to(
                                repo_path
                            )
                        )
                        if package_file.parent != repo_path
                        else ".",

                        "runtime": runtime,

                        "type": application_type,

                        "port": port,

                        "scripts": scripts,

                        "dependencies": sorted(
                            dependencies.keys()
                        ),
                    }
                )

            ports = sorted(
                {
                    app["port"]
                    for app in applications
                    if app.get("port")
                }
            )

            return {
                "runtime": "Node.js",

                "type": (
                    "Multi-app"
                    if len(applications) > 1
                    else applications[0]["type"]
                ),

                "port": (
                    ports[0]
                    if len(ports) == 1
                    else ports
                ),

                "ports": ports,

                "applications": applications,
            }

        # ----------------------------------------------------
        # Python
        # ----------------------------------------------------

        if (
            requirements_files
            or pyproject_files
        ):

            text_parts = []

            for file in (
                requirements_files
                + pyproject_files
            ):

                try:
                    text_parts.append(
                        file.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        ).lower()
                    )
                except Exception:
                    pass

            text = "\n".join(
                text_parts
            )

            if "fastapi" in text:

                return {
                    "runtime": "Python",
                    "type": "FastAPI",
                    "port": 8000,
                    "ports": [8000],
                }

            if "flask" in text:

                return {
                    "runtime": "Python",
                    "type": "Flask",
                    "port": 5000,
                    "ports": [5000],
                }

            if "django" in text:

                return {
                    "runtime": "Python",
                    "type": "Django",
                    "port": 8000,
                    "ports": [8000],
                }

            return {
                "runtime": "Python",
                "type": "Python",
                "port": 8000,
                "ports": [8000],
            }

        # ----------------------------------------------------
        # Static HTML
        # ----------------------------------------------------

        if (
            repo_path / "index.html"
        ).exists():

            return {
                "runtime": "Static",
                "type": "HTML",
                "port": 80,
                "ports": [80],
            }

        # ----------------------------------------------------
        # Unknown
        # ----------------------------------------------------

        return {
            "runtime": "Unknown",
            "type": "Unknown",
            "port": None,
            "ports": [],
        }

    # ========================================================
    # FIND FILES
    # ========================================================

    def _find_files(
        self,
        root: Path,
        filename: str,
    ):

        ignored = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "__pycache__",
        }

        for path in root.rglob(filename):

            if any(
                part in ignored
                for part in path.parts
            ):
                continue

            yield path

    # ========================================================
    # JSON
    # ========================================================

    def _read_json(
        self,
        path: Path,
    ) -> dict:

        try:

            with path.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            if isinstance(
                data,
                dict,
            ):
                return data

        except Exception:
            pass

        return {}

    # ========================================================
    # PORT
    # ========================================================

    def _detect_port(
        self,
        directory: Path,
    ) -> int | None:

        known_ports = {
            3000,
            3001,
            4000,
            4173,
            5000,
            5001,
            5173,
            5174,
            8000,
            8080,
            8081,
        }

        patterns = [
            r"PORT\s*=\s*(\d{2,5})",
            r"port\s*[:=]\s*(\d{2,5})",
            r"localhost:(\d{2,5})",
            r"127\.0\.0\.1:(\d{2,5})",
            r"--port\s+(\d{2,5})",
            r"listen\s*\(\s*(\d{2,5})",
        ]

        for path in self._source_files(
            directory
        ):

            try:

                if path.stat().st_size > 300_000:
                    continue

                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

            except Exception:
                continue

            for pattern in patterns:

                matches = re.findall(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                )

                for match in matches:

                    try:

                        port = int(match)

                        if (
                            1
                            <= port
                            <= 65535
                        ):
                            return port

                    except ValueError:
                        pass

            for port in known_ports:

                if (
                    f":{port}"
                    in text
                ):
                    return port

        return None

    # ========================================================
    # SOURCE FILES
    # ========================================================

    def _source_files(
        self,
        root: Path,
    ):

        extensions = {
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".py",
            ".json",
            ".env",
            ".toml",
        }

        ignored = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "__pycache__",
        }

        for path in root.rglob("*"):

            if not path.is_file():
                continue

            if any(
                part in ignored
                for part in path.parts
            ):
                continue

            if path.suffix.lower() in extensions:

                yield path