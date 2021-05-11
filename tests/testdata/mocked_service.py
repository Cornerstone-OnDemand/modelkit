from typing import Dict

import fastapi
from starlette.responses import JSONResponse

app = fastapi.FastAPI(title="Mock service")


@app.post("/api/path/endpoint")
async def some_endpoint(item: Dict[str, str]):
    return JSONResponse(item)
