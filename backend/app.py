"""API: register client-side hashes, show matches, let the user confirm them.

There is deliberately no public "query a hash" endpoint: it would be an oracle for
probing who has registered what. Only the worker searches the BK-tree.
"""
import hashlib
import re

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import db

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

HEX64 = re.compile(r"^[0-9a-f]{16}$")


def uid(session: str) -> str:
    if len(session) < 32:
        raise HTTPException(401, "bad session id")
    return hashlib.sha256(session.encode()).hexdigest()  # never store the raw bearer secret


class Register(BaseModel):
    hashes: list[str] = Field(max_length=500)


@app.post("/register")
def register(body: Register, x_session: str = Header()):
    user = uid(x_session)
    for h in body.hashes:
        if not HEX64.match(h):
            raise HTTPException(422, f"bad hash {h!r}")
        # near-uniform images (all 0s / all 1s) match every other flat image -> false takedowns
        if not 8 <= int(h, 16).bit_count() <= 56:
            raise HTTPException(422, "image has too little detail to fingerprint safely")
    with db() as c:
        c.executemany("INSERT OR IGNORE INTO hashes(user, h) VALUES(?,?)", [(user, h) for h in body.hashes])
    return {"registered": len(body.hashes)}


@app.get("/matches")
def matches(x_session: str = Header()):
    with db() as c:
        rows = c.execute("SELECT id, source_url, distance, found_at, status FROM matches WHERE user=? ORDER BY found_at DESC", (uid(x_session),))
        return [dict(r) for r in rows]


class Confirm(BaseModel):
    confirmed: bool  # "yes, this is my content, I did not consent"
    owns_copyright: bool = False  # DMCA is only sent if true (it is a perjury-backed claim)


@app.post("/matches/{match_id}/confirm")
def confirm(match_id: int, body: Confirm, x_session: str = Header()):
    with db() as c:
        cur = c.execute(
            "UPDATE matches SET status=?, owns_copyright=? WHERE id=? AND user=?",
            ("confirmed" if body.confirmed else "rejected", int(body.owns_copyright), match_id, uid(x_session)),
        )
    if not cur.rowcount:
        raise HTTPException(404)
    return {"ok": True}
