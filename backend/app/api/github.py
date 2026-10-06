from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import current_user
from app.schemas.github import GitHubInspectRequest, GitHubRepositoryEvidence
from app.services.github_inspector import inspect_public_repository


router = APIRouter(prefix="/api/v1/github", tags=["github"])


@router.post("/inspect", response_model=GitHubRepositoryEvidence)
def inspect_repo(
    payload: GitHubInspectRequest,
    u=Depends(current_user),
):
    try:
        return inspect_public_repository(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub inspection failed: {exc}",
        ) from exc
