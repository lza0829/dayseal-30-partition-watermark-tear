from fastapi import APIRouter
from app.db import connect
from app.repositories import tills as till_repo

router = APIRouter(prefix="/tills", tags=["tills"])


@router.get("")
def list_tills():
    conn = connect()
    try:
        return till_repo.list_tills(conn)
    finally:
        conn.close()
