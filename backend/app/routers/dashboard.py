from fastapi import APIRouter
from app.services import catalog_service as svc

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard():
    return svc.dashboard()

@router.get("/dashboard/extended")
def dashboard_extended():
    if hasattr(svc, "dashboard_extended"):
        return svc.dashboard_extended()
    return svc.dashboard()

@router.get("/dashboard/fence")
def dashboard_fence():
    if hasattr(svc, "fence_snapshot"):
        return svc.fence_snapshot()
    if hasattr(svc, "dashboard_fenced"):
        return svc.dashboard_fenced()
    return svc.dashboard()

