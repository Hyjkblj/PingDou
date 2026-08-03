from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def envelope(
    request: Request,
    data: Any,
    *,
    status_code: int = 200,
    meta: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {"requestId": request.state.request_id, "data": data, "meta": meta}
        ),
    )

