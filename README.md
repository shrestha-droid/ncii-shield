# NCII Shield

    cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/uvicorn app:app        # API :8000
    .venv/bin/python worker.py       # simulated ingest + matcher + dry-run notice dispatch
    .venv/bin/python bktree.py       # self-check
    cd frontend && npm install && npm run dev   # :3000

Flow: browser dHashes files locally (worker + canvas; video = 8 sampled frames) -> `POST /register` (hex only)
-> worker matches ingested hashes via BK-tree (Hamming <= 10) -> match shows on dashboard as `pending`
-> **registered user confirms** -> worker drafts IT Rules 3(2)(b) notice (+ DMCA only if they claim copyright) -> dry-run send.
