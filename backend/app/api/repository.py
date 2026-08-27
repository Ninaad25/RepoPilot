from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from app.services.sandbox_manager import SandboxManager
from app.services.repository_analyzer import analyze_repository
from app.api.auth import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/api/repository",
    tags=["Repository"],
)

manager = SandboxManager()


class AnalyzeRequest(BaseModel):
    url: HttpUrl


@router.post("/analyze")
def analyze_repo(
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
):

    workspace = None

    try:

        # --------------------------------------------------
        # Create temporary workspace
        # --------------------------------------------------

        sandbox_id, workspace = manager.create_workspace()

        # --------------------------------------------------
        # Clone repository
        # --------------------------------------------------

        manager.clone_repository(
            str(request.url),
            workspace,
        )

        repo_path = Path(workspace) / "repo"

        # --------------------------------------------------
        # Analyze repository
        # --------------------------------------------------

        analysis = analyze_repository(
            repo_path
        )

        return {
            "success": True,
            "analysis": analysis,
        }

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    finally:

        # --------------------------------------------------
        # Always remove temporary clone
        # --------------------------------------------------

        if workspace:

            try:
                manager.cleanup_workspace(
                    workspace
                )
            except Exception:
                pass