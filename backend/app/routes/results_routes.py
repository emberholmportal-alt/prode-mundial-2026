from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..limiter import limiter
from ..models import OfficialResult
from ..schemas import OfficialResultOut

router = APIRouter(tags=["results"])


@router.get("/results", response_model=list[OfficialResultOut])
@limiter.limit("120/minute")
def list_results(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(OfficialResult)).all()
    return [OfficialResultOut.model_validate(r) for r in rows]
