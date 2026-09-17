import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.sandbox import Sandbox
from app.models.user import User
from app.services.sandbox_client import SandboxRunnerClient


router = APIRouter(
    prefix="/api/sandbox",
    tags=["Sandbox"],
)


class LaunchRequest(BaseModel):
    url: HttpUrl


# ==================================================
# RUNNER
# ==================================================

def get_runner() -> SandboxRunnerClient:
    return SandboxRunnerClient()


def get_preview_url(
    sandbox_id: str,
    runner_preview_url: str | None = None,
) -> str | None:
    """
    Return the externally accessible preview URL.

    Priority:
    1. URL returned by the remote runner
    2. RUNNER_PUBLIC_URL + /preview/<sandbox_id>/
    3. None
    """

    if runner_preview_url:
        return runner_preview_url.rstrip("/")

    runner_public_url = os.getenv(
        "RUNNER_PUBLIC_URL",
        "",
    ).rstrip("/")

    if runner_public_url:
        return (
            f"{runner_public_url}"
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

    try:
        # ------------------------------------------
        # Create sandbox ID
        # ------------------------------------------

        import uuid

        sandbox_id = str(uuid.uuid4())

        # ------------------------------------------
        # Call remote sandbox runner
        # ------------------------------------------

        runner = get_runner()

        result = runner.launch(
            sandbox_id=sandbox_id,
            repo_url=str(request.url),
            container_port=3000,
        )

        # ------------------------------------------
        # Runner response
        # ------------------------------------------

        container_id = result.get(
            "container_id"
        )

        container_name = result.get(
            "container_name"
        )

        image_name = result.get(
            "image_name"
        )

        workspace = result.get(
            "workspace"
        )

        host_port = result.get(
            "host_port"
        )

        container_port = result.get(
            "container_port",
            3000,
        )

        preview_url = get_preview_url(
            sandbox_id,
            result.get("preview_url"),
        )

        # ------------------------------------------
        # Save sandbox
        # ------------------------------------------

        sandbox = Sandbox(
            sandbox_id=sandbox_id,
            user_id=current_user.id,
            repo_url=str(request.url),
            container_id=container_id,
            container_name=container_name,
            image_name=image_name,
            workspace=workspace,
            host_port=host_port,
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
        "sandbox_id": sandbox.sandbox_id,
        "repo_url": sandbox.repo_url,
        "container_id": sandbox.container_id,
        "container_name": sandbox.container_name,
        "status": sandbox.status,
        "preview_url": preview_url,
    }


# ==================================================
# STOP
# ==================================================

@router.post("/{sandbox_id}/stop")
def stop_sandbox(
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
        runner = get_runner()

        runner.stop(
            sandbox_id=sandbox.sandbox_id,
            container_name=sandbox.container_name,
        )

        sandbox.status = "STOPPED"

        db.commit()

        return {
            "success": True,
            "sandbox_id": sandbox.sandbox_id,
            "status": sandbox.status,
        }

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )