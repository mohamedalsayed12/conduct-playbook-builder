"""Static rollout dashboard page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(tags=["dashboard"])

_DASHBOARD_HTML = Path(__file__).resolve().parents[1] / "static" / "dashboard.html"


@router.get("/dashboard", include_in_schema=False)
def get_dashboard() -> FileResponse:
    """Serve the strategist rollout dashboard HTML."""
    return FileResponse(_DASHBOARD_HTML, media_type="text/html; charset=utf-8")


@router.get("/", include_in_schema=False)
def redirect_root_to_dashboard() -> RedirectResponse:
    """Send visitors of the bare service URL to the dashboard."""
    return RedirectResponse(url="/dashboard", status_code=307)
