from fastapi import APIRouter, Body
from app.services import line_service as svc

router = APIRouter(prefix="/lines", tags=["lines"])


@router.get("")
def list_lines(business_day: str | None = None):
    return svc.list_lines(business_day)


@router.post("")
def create_line(body: dict = Body(...)):
    return svc.create_line(body)


@router.patch("/{line_id}")
def patch_line(line_id: int, body: dict = Body(...)):
    return svc.patch_line(line_id, body)


@router.delete("/{line_id}")
def delete_line(line_id: int):
    return svc.remove_line(line_id)
