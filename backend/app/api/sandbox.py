
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.sandbox import Sandbox
from app.models.user import User
from app.services.sandbox_manager import SandboxManager


router = APIRouter(
    prefix="/api/sandbox",
    tags=["Sandbox"],
)

manager = SandboxManager()


class LaunchRequest(BaseModel):
    url: HttpUrl


# ==================================================
# RUNNER URL
# ==================================================

SANDBOX_RUNNER_URL = os.getenv(
    "SANDBOX_RUNNER_URL",
    "",
).rstrip("/")


def get_preview_url(
    sandbox_id: str,
    runner_preview_url: str | None = None,
) -> str | None:
    """
    Return the externally accessible preview URL.

    Priority:
    1. URL returned by the remote runner
    2. SANDBOX_RUNNER_URL + /preview/<sandbox_id>/
    3. None
    """

    # If the runner explicitly returned a preview URL,
    # use that first.
    if runner_preview_url:
        return runner_preview_url.rstrip("/")

    # Otherwise construct the URL from the configured
    # remote sandbox runner.
    if SANDBOX_RUNNER_URL:
        return (
            f"{SANDBOX_RUNNER_URL}"
            f"/preview/"
            f"{sandbox_id}/"
        )

    return None


# ==================================================
# LAUNCH
# ==================================================

@router.post("/launch")
def launch_repository(
    request: LaunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sandbox_id = None
    workspace = None
    image_name = None
    container_name = None

    try:
        # ------------------------------------------
        # Create workspace
        # ------------------------------------------

        sandbox_id, workspace = manager.create_workspace()

        # ------------------------------------------
        # Clone repository
        # ------------------------------------------

        manager.clone_repository(
            str(request.url),
            workspace,
        )

        repo_path = workspace / "repo"

        # ------------------------------------------
        # Find application
        # ------------------------------------------

        app_path = manager.find_application(
            repo_path
        )

        # ------------------------------------------
        # Dockerfile + container port
        # ------------------------------------------

        dockerfile = app_path / "Dockerfile"

        if dockerfile.exists():
            container_port = (
                manager.detect_dockerfile_port(
                    dockerfile
                )
            )
        else:
            _, container_port = (
                manager.generate_dockerfile(
                    app_path
                )
            )

        # ------------------------------------------
        # Build Docker image
        # ------------------------------------------

        image_name, container_port = (
            manager.build_image(
                workspace,
                sandbox_id,
            )
        )

        # ------------------------------------------
        # Start container
        # ------------------------------------------

        container = manager.start_container(
            image_name,
            sandbox_id,
            container_port,
        )

        container_name = container[
            "container_name"
        ]

        # ------------------------------------------
        # Runner preview URL
        # ------------------------------------------

        preview_url = get_preview_url(
            sandbox_id,
            container.get("preview_url"),
        )

        # ------------------------------------------
        # Save sandbox
        # ------------------------------------------

        sandbox = Sandbox(
            sandbox_id=sandbox_id,
            user_id=current_user.id,
            repo_url=str(request.url),
            container_id=container[
                "container_id"
            ],
            container_name=container_name,
            image_name=image_name,
            workspace=str(workspace),
            host_port=container.get(
                "host_port"
            ),
            container_port=container_port,
            status="RUNNING",
        )

        db.add(sandbox)
        db.commit()
        db.refresh(sandbox)

        # ------------------------------------------
        # Response
        # ------------------------------------------

        return {
            "success": True,
            "sandbox_id": sandbox.sandbox_id,
            "container_id": sandbox.container_id,
            "preview_url": preview_url,
            "status": sandbox.status,
        }

    except Exception as error:

        # ------------------------------------------
        # Cleanup
        # ------------------------------------------

        if (
            sandbox_id
            or container_name
            or workspace
            or image_name
        ):
            manager.delete_sandbox(
                sandbox_id=sandbox_id or "",
                container_name=(
                    container_name or ""
                ),
                workspace=workspace,
                image_name=image_name,
            )

        # ------------------------------------------
        # Database rollback
        # ------------------------------------------

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ==================================================
# GET SANDBOX
# ==================================================

@router.get("/{sandbox_id}")
def get_sandbox(
    sandbox_id: str,
    db: Session = Depends(get_db),
):
    sandbox = (
        db.query(Sandbox)
        .filter(
            Sandbox.sandbox_id == sandbox_id
        )
        .first()
    )

    if not sandbox:
        raise HTTPException(
            status_code=404,
            detail="Sandbox not found",
        )

    preview_url = get_preview_url(
        sandbox.sandbox_id
    )

    return {
        "success": True,
        "sandbox": {
            "sandbox_id": sandbox.sandbox_id,
            "repo_url": sandbox.repo_url,
            "container_id": sandbox.container_id,
            "container_name": sandbox.container_name,
            "image_name": sandbox.image_name,
            "host_port": sandbox.host_port,
            "container_port": sandbox.container_port,
            "status": sandbox.status,
            "created_at": sandbox.created_at,
        },
        "preview_url": preview_url,
    }


# ==================================================
# SANDBOX STATUS
# ==================================================

@router.get("/{sandbox_id}/status")
def sandbox_status(
    sandbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sandbox = (
        db.query(Sandbox)
        .filter(
            Sandbox.sandbox_id == sandbox_id,
            Sandbox.user_id == current_user.id,
        )
        .first()
    )

    if not sandbox:
        raise HTTPException(
            status_code=404,
            detail="Sandbox not found",
        )

    status = manager.get_container_status(
        sandbox.container_name
    )

    # ------------------------------------------
    # Automatic cleanup
    # ------------------------------------------

    if status in {
        "STOPPED",
        "DEAD",
        "NOT_FOUND",
    }:

        sandbox.status = status
        db.commit()

        manager.delete_sandbox(
            sandbox_id=sandbox.sandbox_id,
            container_name=(
                sandbox.container_name
            ),
            workspace=(
                Path(sandbox.workspace)
                if sandbox.workspace
                else None
            ),
            image_name=sandbox.image_name,
        )

        db.delete(sandbox)
        db.commit()

        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "status": status,
            "cleaned_up": True,
            "message": (
                "Sandbox stopped and cleaned up"
            ),
        }

    # ------------------------------------------
    # Synchronize status
    # ------------------------------------------

    if sandbox.status != status:

        sandbox.status = status

        db.commit()
        db.refresh(sandbox)

    # ------------------------------------------
    # Build response
    # ------------------------------------------

    response = {
        "success": True,
        "sandbox_id": sandbox.sandbox_id,
        "status": status,
        "container_name": (
            sandbox.container_name
        ),
        "container_id": sandbox.container_id,
        "cleaned_up": False,
    }

    # ------------------------------------------
    # Production preview URL
    # ------------------------------------------

    runner_url = os.getenv(
        "SANDBOX_RUNNER_URL",
        "",
    ).rstrip("/")

    if runner_url:
        response["preview_url"] = (
            f"{runner_url}"
            f"/preview/"
            f"{sandbox.sandbox_id}/"
        )

    return response


# ==================================================
# DELETE SANDBOX
# ==================================================

@router.delete("/{sandbox_id}")
def delete_sandbox(
    sandbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sandbox = (
        db.query(Sandbox)
        .filter(
            Sandbox.sandbox_id == sandbox_id,
            Sandbox.user_id == current_user.id,
        )
        .first()
    )

    if not sandbox:
        raise HTTPException(
            status_code=404,
            detail="Sandbox not found",
        )

    manager.delete_sandbox(
        sandbox_id=sandbox.sandbox_id,
        container_name=(
            sandbox.container_name
            or ""
        ),
        workspace=(
            Path(sandbox.workspace)
            if sandbox.workspace
            else None
        ),
        image_name=sandbox.image_name,
    )

    db.delete(sandbox)
    db.commit()

    return {
        "success": True,
        "sandbox_id": sandbox_id,
        "message": "Sandbox deleted",
    }
