from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


# ============================================================
# CONSTANTS
# ============================================================

IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".gitlab",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    "coverage",
    ".parcel-cache",
    ".vite",
}

IGNORED_FILES = {
    ".DS_Store",
}

PACKAGE_MANAGER_FILES = {
    "package-lock.json": "npm",
    "yarn.lock": "Yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lock": "Bun",
    "bun.lockb": "Bun",
}

LANGUAGE_BY_EXTENSION = {
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".py": "Python",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

ENTRY_POINT_NAMES = {
    "main.js",
    "main.jsx",
    "main.ts",
    "main.tsx",
    "index.js",
    "index.jsx",
    "index.ts",
    "index.tsx",
    "server.js",
    "server.ts",
    "app.js",
    "app.ts",
    "app.py",
    "main.py",
    "manage.py",
}

FRAMEWORK_DEPENDENCIES = {
    "react": "React",
    "react-dom": "React",
    "next": "Next.js",
    "vite": "Vite",
    "@vitejs/plugin-react": "Vite + React",
    "@vitejs/plugin-react-swc": "Vite + React",
    "express": "Express",
    "fastify": "Fastify",
    "@nestjs/core": "NestJS",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "@angular/core": "Angular",
    "svelte": "Svelte",
    "@sveltejs/kit": "SvelteKit",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "django": "Django",
    "prisma": "Prisma",
    "@prisma/client": "Prisma",
    "tailwindcss": "Tailwind CSS",
}

KNOWN_PORTS = {
    80,
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
    8888,
}


# ============================================================
# BASIC HELPERS
# ============================================================

def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _walk_files(root: Path) -> list[Path]:
    files: list[Path] = []

    if not root.exists():
        return files

    for current_root, directories, filenames in os.walk(root):

        directories[:] = [
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
        ]

        current_path = Path(current_root)

        for filename in filenames:

            if filename in IGNORED_FILES:
                continue

            files.append(current_path / filename)

    return files


# ============================================================
# PACKAGE.JSON DISCOVERY
# ============================================================

def _find_package_files(root: Path) -> list[Path]:
    packages = []

    for path in _walk_files(root):

        if path.name == "package.json":
            packages.append(path)

    return sorted(
        packages,
        key=lambda path: (
            len(path.relative_to(root).parts),
            str(path),
        ),
    )


def _package_info(
    package_path: Path,
    root: Path,
) -> dict[str, Any]:

    package = _read_json(package_path)

    dependencies = {}

    for dependency_group in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        values = package.get(dependency_group) or {}

        if isinstance(values, dict):
            dependencies.update(values)

    scripts = package.get("scripts") or {}

    if not isinstance(scripts, dict):
        scripts = {}

    relative_path = _relative(package_path, root)

    package_directory = package_path.parent

    relative_directory = _relative(
        package_directory,
        root,
    )

    return {
        "path": relative_path,
        "directory": relative_directory,
        "name": package.get("name"),
        "version": package.get("version"),
        "private": package.get("private"),
        "dependencies": dependencies,
        "scripts": scripts,
    }


# ============================================================
# PACKAGE MANAGER
# ============================================================

def _detect_package_manager(
    root: Path,
    package_files: list[Path],
) -> str:

    managers = []

    # Root lockfile.
    for lock_file, manager in PACKAGE_MANAGER_FILES.items():

        if (root / lock_file).exists():
            managers.append(manager)

    # Nested lockfiles.
    for package_file in package_files:

        directory = package_file.parent

        for lock_file, manager in PACKAGE_MANAGER_FILES.items():

            if (directory / lock_file).exists():
                managers.append(manager)

    managers = list(dict.fromkeys(managers))

    if not managers and package_files:
        return "npm"

    if len(managers) == 1:
        return managers[0]

    if managers:
        return " + ".join(managers)

    return "Unknown"


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def _detect_languages(files: list[Path]) -> list[str]:

    counts: dict[str, int] = {}

    for path in files:

        language = LANGUAGE_BY_EXTENSION.get(
            path.suffix.lower()
        )

        if not language:
            continue

        counts[language] = counts.get(language, 0) + 1

    ordered = sorted(
        counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    return [language for language, _ in ordered]


# ============================================================
# DEPENDENCY COLLECTION
# ============================================================

def _all_dependencies(
    package_infos: list[dict[str, Any]],
) -> set[str]:

    dependencies: set[str] = set()

    for package in package_infos:

        for dependency in package.get(
            "dependencies",
            {},
        ).keys():

            dependencies.add(dependency)

    return dependencies


# ============================================================
# FRAMEWORK DETECTION
# ============================================================

def _detect_frameworks(
    root: Path,
    files: list[Path],
    package_infos: list[dict[str, Any]],
) -> list[str]:

    dependencies = _all_dependencies(package_infos)

    frameworks: list[str] = []

    def add(name: str):
        if name not in frameworks:
            frameworks.append(name)

    # --------------------------------------------------------
    # JavaScript / TypeScript
    # --------------------------------------------------------

    if "react" in dependencies:
        add("React")

    if "react-dom" in dependencies:
        add("React")

    if "vite" in dependencies:
        add("Vite")

    if "@vitejs/plugin-react" in dependencies:
        add("Vite + React")

    if "@vitejs/plugin-react-swc" in dependencies:
        add("Vite + React")

    if "next" in dependencies:
        add("Next.js")

    if "express" in dependencies:
        add("Express")

    if "fastify" in dependencies:
        add("Fastify")

    if "@nestjs/core" in dependencies:
        add("NestJS")

    if "vue" in dependencies:
        add("Vue")

    if "nuxt" in dependencies:
        add("Nuxt")

    if "@angular/core" in dependencies:
        add("Angular")

    if "svelte" in dependencies:
        add("Svelte")

    if "@sveltejs/kit" in dependencies:
        add("SvelteKit")

    if "prisma" in dependencies:
        add("Prisma")

    if "@prisma/client" in dependencies:
        add("Prisma")

    if "tailwindcss" in dependencies:
        add("Tailwind CSS")

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    requirements_files = [
        path
        for path in files
        if path.name.lower() == "requirements.txt"
    ]

    for requirements_file in requirements_files:

        try:

            text = requirements_file.read_text(
                encoding="utf-8",
                errors="ignore",
            ).lower()

            if "fastapi" in text:
                add("FastAPI")

            if "flask" in text:
                add("Flask")

            if "django" in text:
                add("Django")

        except Exception:
            pass

    # pyproject.toml
    pyproject_files = [
        path
        for path in files
        if path.name == "pyproject.toml"
    ]

    for pyproject in pyproject_files:

        try:

            text = pyproject.read_text(
                encoding="utf-8",
                errors="ignore",
            ).lower()

            if "fastapi" in text:
                add("FastAPI")

            if "flask" in text:
                add("Flask")

            if "django" in text:
                add("Django")

        except Exception:
            pass

    # --------------------------------------------------------
    # Prisma files
    # --------------------------------------------------------

    if any(
        path.suffix.lower() == ".prisma"
        for path in files
    ):
        add("Prisma")

    if any(
        path.name == "prisma.config.ts"
        for path in files
    ):
        add("Prisma")

    return frameworks


# ============================================================
# APPLICATION DETECTION
# ============================================================

def _detect_applications(
    root: Path,
    package_infos: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    applications = []

    for package in package_infos:

        directory = root / package["directory"]

        dependencies = set(
            package.get("dependencies", {}).keys()
        )

        scripts = package.get("scripts", {})

        frameworks = []

        if "react" in dependencies:
            frameworks.append("React")

        if "vite" in dependencies:
            frameworks.append("Vite")

        if "next" in dependencies:
            frameworks.append("Next.js")

        if "express" in dependencies:
            frameworks.append("Express")

        if "fastify" in dependencies:
            frameworks.append("Fastify")

        if "vue" in dependencies:
            frameworks.append("Vue")

        if "prisma" in dependencies or "@prisma/client" in dependencies:
            frameworks.append("Prisma")

        # Determine application type.
        if "vite" in dependencies:
            app_type = "Frontend"

        elif "react" in dependencies and "express" not in dependencies:
            app_type = "Frontend"

        elif "next" in dependencies:
            app_type = "Full-stack"

        elif "express" in dependencies or "fastify" in dependencies:
            app_type = "Backend"

        else:
            app_type = "Node.js"

        # Port.
        if "vite" in dependencies:
            port = 5173

        elif "next" in dependencies:
            port = 3000

        elif "express" in dependencies:
            port = 3000

        else:
            port = None

        # Commands.
        build_command = None
        start_command = None

        if "build" in scripts:
            build_command = "npm run build"

        if "start" in scripts:
            start_command = "npm start"

        elif "dev" in scripts:
            start_command = "npm run dev"

        applications.append(
            {
                "name": package.get("name")
                or directory.name
                or root.name,

                "path": package["directory"],

                "type": app_type,

                "framework": (
                    " + ".join(
                        dict.fromkeys(frameworks)
                    )
                    if frameworks
                    else "Node.js"
                ),

                "runtime": "Node.js",

                "port": port,

                "package_manager": "npm",

                "build_command": build_command,

                "start_command": start_command,

                "dependencies": sorted(
                    package.get(
                        "dependencies",
                        {},
                    ).keys()
                ),

                "scripts": scripts,
            }
        )

    return applications


# ============================================================
# RUNTIME
# ============================================================

def _detect_runtime(
    package_infos: list[dict[str, Any]],
    languages: list[str],
    frameworks: list[str],
) -> str:

    if package_infos:
        return "Node.js"

    if (
        "FastAPI" in frameworks
        or "Flask" in frameworks
        or "Django" in frameworks
    ):
        return "Python"

    if "Python" in languages:
        return "Python"

    if "Java" in languages:
        return "Java"

    if "Go" in languages:
        return "Go"

    if "Rust" in languages:
        return "Rust"

    return "Unknown"


# ============================================================
# PORT DETECTION
# ============================================================

def _detect_ports_from_text(
    text: str,
) -> set[int]:

    ports: set[int] = set()

    patterns = [
        r"PORT\s*=\s*(\d{2,5})",
        r"port\s*[:=]\s*(\d{2,5})",
        r"listen\s*\(\s*(\d{2,5})",
        r"localhost:(\d{2,5})",
        r"127\.0\.0\.1:(\d{2,5})",
        r"--port\s+(\d{2,5})",
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for match in matches:

            try:
                port = int(match)

                if 1 <= port <= 65535:
                    ports.add(port)

            except ValueError:
                pass

    # Known ports that may appear without obvious syntax.
    for port in KNOWN_PORTS:

        if (
            f":{port}" in text
            or f" {port}" in text
        ):
            ports.add(port)

    return ports


def _detect_ports(
    files: list[Path],
    applications: list[dict[str, Any]],
) -> list[int]:

    ports: set[int] = set()

    # Application-level detection first.
    for application in applications:

        port = application.get("port")

        if isinstance(port, int):
            ports.add(port)

    relevant_extensions = {
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".py",
        ".json",
        ".toml",
        ".env",
        ".yaml",
        ".yml",
    }

    for path in files:

        if path.suffix.lower() not in relevant_extensions:
            continue

        try:

            if path.stat().st_size > 300_000:
                continue

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            ports.update(
                _detect_ports_from_text(text)
            )

        except Exception:
            continue

    return sorted(ports)


# ============================================================
# SCRIPTS
# ============================================================

def _detect_scripts(
    package_infos: list[dict[str, Any]],
) -> dict[str, str]:

    scripts: dict[str, str] = {}

    multiple_packages = len(package_infos) > 1

    for package in package_infos:

        location = package["directory"]

        for name, command in package.get(
            "scripts",
            {},
        ).items():

            if multiple_packages and location != ".":

                key = f"{location}:{name}"

            else:

                key = name

            scripts[key] = command

    return scripts


# ============================================================
# ENTRY POINTS
# ============================================================

def _detect_entry_points(
    root: Path,
    files: list[Path],
    package_infos: list[dict[str, Any]],
) -> list[str]:

    entry_points: list[str] = []

    # package.json main fields.
    for package in package_infos:

        package_file = root / package["path"]

        package_data = _read_json(package_file)

        main = package_data.get("main")

        if main:

            entry = _relative(
                package_file.parent / main,
                root,
            )

            if entry not in entry_points:
                entry_points.append(entry)

    # Common entry files.
    for path in files:

        if path.name not in ENTRY_POINT_NAMES:
            continue

        relative = _relative(
            path,
            root,
        )

        if relative not in entry_points:
            entry_points.append(relative)

    return sorted(entry_points)


# ============================================================
# DEPENDENCIES
# ============================================================

def _collect_dependencies(
    package_infos: list[dict[str, Any]],
) -> list[str]:

    dependencies: set[str] = set()

    for package in package_infos:

        dependencies.update(
            package.get(
                "dependencies",
                {},
            ).keys()
        )

    return sorted(dependencies)


# ============================================================
# STRUCTURE
# ============================================================

def _build_structure(
    root: Path,
    files: list[Path],
) -> dict[str, list[str]]:

    structure_files: list[str] = []
    structure_directories: set[str] = set()

    for path in files:

        relative = _relative(
            path,
            root,
        )

        structure_files.append(relative)

        parent = path.parent

        while parent != root:

            try:

                relative_parent = parent.relative_to(root)

            except ValueError:
                break

            structure_directories.add(
                str(relative_parent)
            )

            parent = parent.parent

    return {
        "files": sorted(
            structure_files
        ),
        "directories": sorted(
            structure_directories
        ),
    }


# ============================================================
# FILE EXTENSIONS
# ============================================================

def _detect_extensions(
    files: list[Path],
) -> dict[str, int]:

    extensions: dict[str, int] = {}

    for path in files:

        extension = path.suffix.lower()

        if not extension:
            continue

        extensions[extension] = (
            extensions.get(
                extension,
                0,
            )
            + 1
        )

    return dict(
        sorted(
            extensions.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


# ============================================================
# FRAMEWORK LABEL
# ============================================================

def _framework_label(
    frameworks: list[str],
) -> str:

    if not frameworks:
        return "Unknown"

    # Most useful labels first.
    if (
        "React" in frameworks
        and "Vite" in frameworks
    ):
        frontend = "React + Vite"

    elif "Vite + React" in frameworks:
        frontend = "Vite + React"

    elif "Express" in frameworks:
        frontend = "Express"

    elif "Next.js" in frameworks:
        frontend = "Next.js"

    elif "FastAPI" in frameworks:
        frontend = "FastAPI"

    elif "Django" in frameworks:
        frontend = "Django"

    elif "Flask" in frameworks:
        frontend = "Flask"

    else:
        frontend = frameworks[0]

    # Add important backend/database technology.
    extras = []

    if (
        "Express" in frameworks
        and frontend != "Express"
    ):
        extras.append("Express")

    if (
        "Prisma" in frameworks
        and "Prisma" not in frontend
    ):
        extras.append("Prisma")

    if (
        "Tailwind CSS" in frameworks
        and "Tailwind CSS" not in frontend
    ):
        extras.append("Tailwind CSS")

    if extras:
        return " + ".join(
            [frontend] + extras
        )

    return frontend


# ============================================================
# MAIN ANALYZER
# ============================================================

class RepositoryAnalyzer:

    def analyze(
        self,
        repo_path: str | Path,
    ) -> dict[str, Any]:

        root = Path(repo_path).resolve()

        if not root.exists():
            raise FileNotFoundError(
                f"Repository path does not exist: {root}"
            )

        if not root.is_dir():
            raise ValueError(
                f"Repository path is not a directory: {root}"
            )

        # ----------------------------------------------------
        # Scan
        # ----------------------------------------------------

        files = _walk_files(root)

        package_files = _find_package_files(root)

        package_infos = [
            _package_info(
                package_file,
                root,
            )
            for package_file in package_files
        ]

        # ----------------------------------------------------
        # Detect
        # ----------------------------------------------------

        languages = _detect_languages(files)

        frameworks = _detect_frameworks(
            root,
            files,
            package_infos,
        )

        runtime = _detect_runtime(
            package_infos,
            languages,
            frameworks,
        )

        package_manager = _detect_package_manager(
            root,
            package_files,
        )

        applications = _detect_applications(
            root,
            package_infos,
        )

        ports = _detect_ports(
            files,
            applications,
        )

        scripts = _detect_scripts(
            package_infos,
        )

        entry_points = _detect_entry_points(
            root,
            files,
            package_infos,
        )

        dependencies = _collect_dependencies(
            package_infos,
        )

        structure = _build_structure(
            root,
            files,
        )

        extensions = _detect_extensions(files)

        # ----------------------------------------------------
        # Labels
        # ----------------------------------------------------

        framework = _framework_label(
            frameworks
        )

        language = (
            " + ".join(
                languages[:3]
            )
            if languages
            else "Unknown"
        )

        port = (
            " / ".join(
                str(value)
                for value in ports
            )
            if ports
            else "Unknown"
        )

        # ----------------------------------------------------
        # Commands
        # ----------------------------------------------------

        build_commands = []

        start_commands = []

        for application in applications:

            path = application["path"]

            prefix = ""

            if path != ".":
                prefix = f"cd {path} && "

            if application.get(
                "build_command"
            ):
                build_commands.append(
                    prefix
                    + application["build_command"]
                )

            if application.get(
                "start_command"
            ):
                start_commands.append(
                    prefix
                    + application["start_command"]
                )

        build_commands = list(
            dict.fromkeys(
                build_commands
            )
        )

        start_commands = list(
            dict.fromkeys(
                start_commands
            )
        )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        result = {
            "repository": {
                "name": root.name,
                "version": (
                    package_infos[0].get(
                        "version"
                    )
                    if package_infos
                    else None
                ),
                "path": str(root),
            },

            "runtime": runtime,

            "framework": framework,

            "frameworks": frameworks,

            "language": language,

            "languages": languages,

            "package_manager": package_manager,

            "port": port,

            "ports": ports,

            "build_command": (
                " | ".join(
                    build_commands
                )
                if build_commands
                else "Not detected"
            ),

            "start_command": (
                " | ".join(
                    start_commands
                )
                if start_commands
                else "Not detected"
            ),

            "files": {
                "total": len(files),
                "directories": len(
                    structure[
                        "directories"
                    ]
                ),
                "extensions": extensions,
            },

            "entry_points": entry_points,

            "dependencies": dependencies,

            "scripts": scripts,

            "packages": package_infos,

            "applications": applications,

            "structure": structure,

            "summary": {
                "runtime": runtime,
                "framework": framework,
                "language": language,
                "total_files": len(files),
                "total_directories": len(
                    structure[
                        "directories"
                    ]
                ),
                "dependency_count": len(
                    dependencies
                ),
                "package_count": len(
                    package_infos
                ),
                "application_count": len(
                    applications
                ),
            },
        }

        return result


# ============================================================
# FUNCTION API
# ============================================================

def analyze_repository(
    repo_path: str | Path,
) -> dict[str, Any]:

    analyzer = RepositoryAnalyzer()

    return analyzer.analyze(
        repo_path
    )