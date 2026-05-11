import sys
from pathlib import Path

_BASE = Path(__file__).parent  # semantic_dict/
sys.path.insert(0, str(_BASE))
sys.path.insert(0, str(_BASE / "utils"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from match_engine import search  # noqa: E402

app = FastAPI(title="Semantic Vocabulary API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/match")
def match_endpoint(req: QueryRequest):
    results = search(req.query)
    return {"query": req.query, "count": len(results), "results": results[:50]}
