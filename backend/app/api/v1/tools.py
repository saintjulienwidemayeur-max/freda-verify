from fastapi import APIRouter, Depends

from app.core.deps import Principal, get_principal
from app.core.errors import AppError
from app.schemas import MrzIn
from app.services.mrz import MrzError, parse_mrz

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/mrz/check")
def mrz_check(body: MrzIn, _: Principal = Depends(get_principal)):
    """Validates an MRZ you already extracted (OCR). Checks layout, ICAO check digits and dates. Not proof that the document is genuine."""
    try:
        return parse_mrz(body.lines, fix_ocr=body.fix_ocr).to_dict()
    except MrzError as e:
        raise AppError(422, "invalid_mrz", str(e)) from e
