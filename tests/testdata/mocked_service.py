from typing import Dict, List, Optional, Union

import fastapi
from starlette.responses import JSONResponse

app = fastapi.FastAPI(title="Mock service")


@app.post("/api/path/endpoint")
async def some_endpoint(
    item: Dict[str, Union[str, int]],
    limit: Optional[int] = None,
    skip: Optional[int] = None,
):
    if limit:
        item["limit"] = limit
    if skip:
        item["skip"] = skip
    return JSONResponse(item)


@app.post("/api/path/endpoint/batch")
async def some_endpoint_batch(
    items: List[Dict[str, Union[str, int]]],
    limit: Optional[int] = None,
    skip: Optional[int] = None,
):
    for item in items:
        if limit:
            item["limit"] = limit
        if skip:
            item["skip"] = skip
    return JSONResponse(items)
