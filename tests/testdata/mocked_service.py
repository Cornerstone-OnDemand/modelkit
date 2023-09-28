from typing import Dict, List, Optional, Union

import fastapi
from starlette.responses import JSONResponse
from typing_extensions import Annotated

app = fastapi.FastAPI(title="Mock service")


@app.post("/api/path/endpoint")
async def some_endpoint(
    item: Dict[str, Union[str, int]],
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    x_correlation_id: Annotated[Union[str, None], fastapi.Header()] = None,
):
    if x_correlation_id:
        item["x_correlation_id"] = x_correlation_id
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
    x_correlation_id: Annotated[Union[str, None], fastapi.Header()] = None,
):
    for item in items:
        if x_correlation_id:
            item["x_correlation_id"] = x_correlation_id
        if limit:
            item["limit"] = limit
        if skip:
            item["skip"] = skip
    return JSONResponse(items)
