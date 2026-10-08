// All media is decoded and hashed in the browser. Only 16-char hex strings leave this module.
const FRAMES = 8; // keyframes sampled per video

let worker: Worker | undefined;
const hashBitmap = (b: ImageBitmap) =>
  new Promise<string>((resolve) => {
    worker ??= new Worker(new URL("./hash.worker.ts", import.meta.url));
    worker.onmessage = (e) => resolve(e.data);
    worker.postMessage(b, [b]);
  });

async function videoHashes(file: File): Promise<string[]> {
  const v = document.createElement("video");
  v.muted = true;
  v.preload = "auto";
  v.src = URL.createObjectURL(file);
  await new Promise((ok, no) => ((v.onloadedmetadata = ok), (v.onerror = no)));
  const out: string[] = [];
  for (let i = 0; i < FRAMES; i++) {
    v.currentTime = (v.duration * (i + 0.5)) / FRAMES;
    await new Promise((ok) => (v.onseeked = ok));
    out.push(await hashBitmap(await createImageBitmap(v)));
  }
  URL.revokeObjectURL(v.src);
  return out;
}

export async function hashFile(file: File): Promise<string[]> {
  return file.type.startsWith("video/") ? videoHashes(file) : [await hashBitmap(await createImageBitmap(file))];
}
