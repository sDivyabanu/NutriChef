"""Recipe generation endpoints. Generation runs in a background worker; clients poll the job."""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import services
from ..auth import current_user_id
from ..convert import prefs_for_search
from ..nlp.llm import llm_service

router = APIRouter(prefix="/api/nlp", tags=["generation"])
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gen")  # one generation at a time on a laptop CPU
_jobs: dict[str, dict] = {}
MAX_JOBS = 50


class GenerateIn(BaseModel):
    request: str = Field(..., min_length=3, max_length=600)
    use_llm: bool = True
    apply_profile: bool = True


class JobOut(BaseModel):
    id: str
    status: str            # queued | running | done | error
    created_at: float
    elapsed_s: float
    result: dict | None = None
    error: str | None = None


def _run(job_id: str, body: GenerateIn, user_id: str | None) -> None:
    job = _jobs[job_id]
    job["status"] = "running"
    job["started_at"] = time.time()
    try:
        from ..nlp.generate import RecipeGenerator

        prefs = prefs_for_search(user_id, body.apply_profile)
        gen = RecipeGenerator(services.get_engine(), services.ranker)
        job["result"] = asdict(gen.generate(body.request, prefs, use_llm=body.use_llm))
        job["status"] = "done"
    except Exception as exc:
        job["status"] = "error"
        job["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        job["finished_at"] = time.time()


@router.post("/generate", response_model=JobOut, status_code=202)
def generate(body: GenerateIn, request: Request):
    if services.engine is None:
        raise HTTPException(503, "NLP engine is still starting")
    if len(_jobs) >= MAX_JOBS:
        for k in sorted(_jobs, key=lambda k: _jobs[k]["created_at"])[: len(_jobs) - MAX_JOBS + 1]:
            if _jobs[k]["status"] in ("done", "error"):
                _jobs.pop(k, None)
    jid = uuid.uuid4().hex
    _jobs[jid] = {"id": jid, "status": "queued", "created_at": time.time(), "result": None, "error": None}
    _pool.submit(_run, jid, body, current_user_id(request))
    return _job_out(jid)


def _job_out(jid: str) -> JobOut:
    j = _jobs[jid]
    end = j.get("finished_at") or time.time()
    return JobOut(id=jid, status=j["status"], created_at=j["created_at"], elapsed_s=round(end - j["created_at"], 1),
                  result=j["result"], error=j["error"])


@router.get("/jobs/{job_id}", response_model=JobOut)
def job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Unknown job")
    return _job_out(job_id)


@router.get("/llm/status")
def llm_status():
    return llm_service.status()
