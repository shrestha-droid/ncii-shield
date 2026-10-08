"use client";
import { useEffect, useState } from "react";
import { hashFile } from "../lib/hash";

const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";
type Match = { id: number; source_url: string; distance: number; status: string };

export default function Home() {
  const [session, setSession] = useState("");
  const [msg, setMsg] = useState("");
  const [matches, setMatches] = useState<Match[]>([]);

  const call = (path: string, init: RequestInit = {}) =>
    fetch(API + path, { ...init, headers: { "X-Session": session, "Content-Type": "application/json" } });

  useEffect(() => {
    // anonymous identity = random secret kept only in this browser
    let s = localStorage.getItem("session");
    if (!s) localStorage.setItem("session", (s = crypto.randomUUID() + crypto.randomUUID()));
    setSession(s);
  }, []);

  const refresh = async () => session && setMatches(await (await call("/matches")).json());
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [session]);

  async function onFiles(files: FileList | null) {
    if (!files) return;
    setMsg("Hashing locally…");
    const hashes = (await Promise.all([...files].map(hashFile))).flat();
    const r = await call("/register", { method: "POST", body: JSON.stringify({ hashes }) });
    setMsg(r.ok ? `Registered ${hashes.length} fingerprints. Your files never left this device.` : (await r.json()).detail);
  }

  const confirm = async (id: number, confirmed: boolean) => {
    const owns = confirmed && window.confirm("Are you the copyright owner (e.g. you took the photo)? OK = also send a DMCA notice.");
    await call(`/matches/${id}/confirm`, { method: "POST", body: JSON.stringify({ confirmed, owns_copyright: owns }) });
    refresh();
  };

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>Protect my images</h1>
      <input type="file" multiple accept="image/*,video/*" onChange={(e) => onFiles(e.target.files)} />
      <p>{msg}</p>
      <h2>Matches</h2>
      {matches.map((m) => (
        <div key={m.id}>
          <a href={m.source_url} rel="noreferrer noopener">{m.source_url}</a> (distance {m.distance}) — {m.status}{" "}
          {m.status === "pending" && (
            <>
              <button onClick={() => confirm(m.id, true)}>That's my content — send takedown</button>{" "}
              <button onClick={() => confirm(m.id, false)}>Not mine</button>
            </>
          )}
        </div>
      ))}
    </main>
  );
}
