from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sandbox import Sandbox
from app.models.user import User
from app.services.sandbox_manager import SandboxManager
from app.api.auth import get_current_user


router = APIRouter(
    prefix="/api/sandbox",
    tags=["Sandbox"],
)

manager = SandboxManager()


class LaunchRequest(BaseModel):
    url: HttpUrl


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

        app_path = manager.find_application(repo_path)

        # ------------------------------------------
        # Dockerfile + container port
        # ------------------------------------------

        dockerfile = app_path / "Dockerfile"

        if dockerfile.exists():
            container_port = manager.detect_dockerfile_port(
                dockerfile
            )
        else:
            _, container_port = manager.generate_dockerfile(
                app_path
            )

        # ------------------------------------------
        # Build Docker image
        # ------------------------------------------

        image_name, container_port = manager.build_image(
            workspace,
            sandbox_id,
        )

        # ------------------------------------------
        # Start container
        # ------------------------------------------

        container = manager.start_container(
            image_name,
            sandbox_id,
            container_port,
        )

        container_name = container["container_name"]

        # ------------------------------------------
        # Save sandbox to database
        # ------------------------------------------

        sandbox = Sandbox(
            sandbox_id=sandbox_id,
            user_id=current_user.id,
            repo_url=str(request.url),
            container_id=container["container_id"],
            container_name=container_name,
            image_name=image_name,
            workspace=str(workspace),
            host_port=container["host_port"],
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
            "preview_url": (
                f"http://localhost:{sandbox.host_port}"
            ),
            "status": sandbox.status,
        }

    except Exception as error:

        # ------------------------------------------
        # Cleanup everything created by this launch
        # ------------------------------------------

        if (
            sandbox_id
            or container_name
            or workspace
            or image_name
        ):
            manager.delete_sandbox(
                sandbox_id=sandbox_id or "",
                container_name=container_name or "",
                workspace=workspace,
                image_name=image_name,
            )

        # ------------------------------------------
        # Rollback database
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
        "preview_url": (
            f"http://localhost:"
            f"{sandbox.host_port}"
        ),
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

    if status in {"STOPPED", "DEAD", "NOT_FOUND"}:

        # Save status before cleanup
        sandbox.status = status
        db.commit()

        # Remove Docker container, image and workspace
        manager.delete_sandbox(
            sandbox_id=sandbox.sandbox_id,
            container_name=sandbox.container_name,
            workspace=(
                Path(sandbox.workspace)
                if sandbox.workspace
                else None
            ),
            image_name=sandbox.image_name,
        )

        # Remove database record
        db.delete(sandbox)
        db.commit()

        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "status": status,
            "cleaned_up": True,
            "message": "Sandbox stopped and cleaned up",
        }

    # ------------------------------------------
    # Keep database status synchronized
    # ------------------------------------------

    if sandbox.status != status:
        sandbox.status = status
        db.commit()
        db.refresh(sandbox)

    response = {
        "success": True,
        "sandbox_id": sandbox.sandbox_id,
        "status": status,
        "container_name": sandbox.container_name,
        "container_id": sandbox.container_id,
        "cleaned_up": False,
    }

    if sandbox.host_port:
        response["preview_url"] = (
            f"http://localhost:"
            f"{sandbox.host_port}"
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

    try:
        # ------------------------------------------
        # Stop container
        # Remove image
        # Remove workspace
        # ------------------------------------------

        manager.delete_sandbox(
            sandbox_id=sandbox.sandbox_id,
            container_name=sandbox.container_name,
            workspace=(
                Path(sandbox.workspace)
                if sandbox.workspace
                else None
            ),
            image_name=sandbox.image_name,
        )

        # ------------------------------------------
        # Remove database record
        # ------------------------------------------

        db.delete(sandbox)
        db.commit()

        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "message": "Sandbox deleted successfully",
        }

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
