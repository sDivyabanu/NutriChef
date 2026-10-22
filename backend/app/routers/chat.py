"""Conversational assistant endpoint. State is structured and round-tripped by the client (no server memory)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import services
from ..auth import current_user_id
from ..convert import hits_to_schema, parsed_from_understanding, prefs_for_search, understanding_from_parsed
from ..schemas_nlp import QueryUnderstanding, SearchHit

router = APIRouter(prefix="/api/nlp", tags=["assistant"])


class ChatState(BaseModel):
    understanding: QueryUnderstanding | None = None
    shown_ids: list[int] = Field(default_factory=list, max_length=50)
    focus_recipe_id: int | None = None
    turns: int = 0


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    state: ChatState | None = None
    apply_profile: bool = True


class ChatOut(BaseModel):
    reply: str
    action: str
    state: ChatState
    results: list[SearchHit] = []
    total: int | None = None
    focus_recipe_id: int | None = None
    suggestions: list[str] = []


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, request: Request):
    eng = services.engine
    if eng is None:
        raise HTTPException(503, "NLP engine is still starting")
    from ..nlp.chat import ChatAssistant

    st = body.state or ChatState()
    state = {"pq": st.understanding, "shown_ids": st.shown_ids, "focus_recipe_id": st.focus_recipe_id, "turns": st.turns}
    prefs = prefs_for_search(current_user_id(request), body.apply_profile)
    turn = ChatAssistant(eng, services.ranker).turn(
        body.message, state, prefs, lambda u: parsed_from_understanding(u) if u is not None else None
    )
    pq = turn.state.get("pq")
    out_state = ChatState(
        understanding=understanding_from_parsed(pq) if pq is not None and not isinstance(pq, QueryUnderstanding) else pq,
        shown_ids=turn.state.get("shown_ids") or [], focus_recipe_id=turn.state.get("focus_recipe_id"),
        turns=turn.state.get("turns", 0),
    )
    return ChatOut(reply=turn.reply, action=turn.action, state=out_state,
                   results=hits_to_schema(turn.results.hits) if turn.results else [],
                   total=turn.results.total if turn.results else None,
                   focus_recipe_id=turn.focus_recipe_id, suggestions=turn.suggestions)
