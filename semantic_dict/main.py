import importlib.util
import sys
from pathlib import Path

_BASE = Path(__file__).parent  # semantic_dict/
sys.path.insert(0, str(_BASE))
sys.path.insert(0, str(_BASE / "utils"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Файл называется 07_match_engine.py — имя начинается с цифры, importlib обязателен
_spec = importlib.util.spec_from_file_location("match_engine", _BASE / "07_match_engine.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
search = _mod.search

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
