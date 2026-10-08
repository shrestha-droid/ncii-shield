"""Worker: simulated ingestion -> BK-tree match -> alert; plus notice dispatch for confirmed matches.

Run: python worker.py   (separate process from the API; they share the SQLite file)
"""
import queue
import random
import threading
import time

from bktree import BKTree
from db import db

TOL = 10  # max Hamming distance of 64 bits. Tune against real data before trusting it.
q: queue.Queue = queue.Queue()
tree, seen = BKTree(), 0
lock = threading.Lock()


def ingest():
    """Simulated scraper. Real one: poll file hosts / public channels, hash thumbnails with the
    SAME dHash as frontend/lib/hash.ts (Pillow: resize 9x8, luma, compare neighbours)."""
    while True:
        time.sleep(3)
        with db() as c:
            rows = c.execute("SELECT h FROM hashes").fetchall()
        if rows and random.random() < 0.5:  # re-upload: registered hash with a few bits flipped
            h = int(random.choice(rows)["h"], 16)
            for b in random.sample(range(64), random.randint(0, 6)):
                h ^= 1 << b
        else:
            h = random.getrandbits(64)
        q.put((f"https://example-filehost.test/{random.getrandbits(32):08x}", h))


def sync_tree():
    global seen
    with db() as c:
        rows = c.execute("SELECT id, h FROM hashes WHERE id > ? ORDER BY id", (seen,)).fetchall()
    with lock:
        for r in rows:
            tree.add(int(r["h"], 16), r["id"])
            seen = r["id"]


def match():
    while True:
        url, h = q.get()
        sync_tree()
        with lock:
            hits = tree.search(h, TOL)
        with db() as c:
            for hash_id, dist in hits:
                user = c.execute("SELECT user FROM hashes WHERE id=?", (hash_id,)).fetchone()["user"]
                cur = c.execute("INSERT OR IGNORE INTO matches(hash_id, user, source_url, distance, found_at) VALUES(?,?,?,?,?)",
                                (hash_id, user, url, dist, time.time()))
                if cur.rowcount:
                    notify(user, url, dist)


def notify(user: str, url: str, dist: int):
    # Dashboard (GET /matches) is the alert channel. Email: SMTP. Webhook: needs SSRF validation first.
    print(f"[alert] user {user[:8]} match d={dist} at {url}")


IT_RULES = """To the Grievance Officer / Abuse Desk,

Under Rule 3(2)(b) of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021, I request removal within 24 hours of content exposing a private area / showing nudity or a sexual act, published without my consent, at:
{url}
This complaint is made by the depicted individual (or on their behalf)."""

DMCA = """To the Designated Copyright Agent,

I request removal of material infringing my copyright at:
{url}
I have a good-faith belief the use is not authorised by the copyright owner, its agent, or the law. The information in this notice is accurate, and under penalty of perjury I am the owner of the exclusive right allegedly infringed."""


def abuse_contact(url: str) -> str:
    # ponytail: guess. Real: RDAP lookup of host/registrar abuse contact + a table of platform grievance officers.
    return "abuse@" + url.split("/")[2]


def send(to: str, body: str) -> str:
    # ponytail: dry run only. Wire SMTP here, and only after a human has reviewed a few dry runs.
    print(f"[notice:dry-run] to {to}\n{body}\n")
    return "dry_run"


def dispatch():
    while True:
        time.sleep(3)
        with db() as c:
            rows = c.execute("SELECT id, source_url, owns_copyright FROM matches WHERE status='confirmed'").fetchall()
            for m in rows:  # only matches the registered user confirmed get a notice
                kinds = [("IT_RULES_3_2_b", IT_RULES)] + ([("DMCA", DMCA)] if m["owns_copyright"] else [])
                for kind, tpl in kinds:
                    to, body = abuse_contact(m["source_url"]), tpl.format(url=m["source_url"])
                    if not c.execute("SELECT 1 FROM notices WHERE match_id=? AND kind=?", (m["id"], kind)).fetchone():
                        c.execute("INSERT INTO notices VALUES(NULL,?,?,?,?,?,?)", (m["id"], kind, to, body, send(to, body), time.time()))


if __name__ == "__main__":
    for f in (ingest, match, dispatch):
        threading.Thread(target=f, daemon=True).start()
    threading.Event().wait()
