from typing import Dict, Optional

import fastapi
from starlette.responses import JSONResponse

app = fastapi.FastAPI(title="Mock service")


@app.post("/api/path/endpoint")
async def some_endpoint(
    item: Dict[str, str],
    limit: Optional[int] = None,
    skip: Optional[int] = None,
):
    if limit:
        item["limit"] = limit
    if skip:
        item["skip"] = skip
    return JSONResponse(item)
