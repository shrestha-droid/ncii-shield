// 64-bit dHash: shrink to 9x8 grayscale, bit = left pixel brighter than right neighbour.
// ponytail: plain canvas downscale aliases on huge images and differs slightly per browser;
// tolerance absorbs it. Upgrade to PDQ (256-bit) for production robustness.
self.onmessage = (e: MessageEvent<ImageBitmap>) => {
  const ctx = new OffscreenCanvas(9, 8).getContext("2d", { willReadFrequently: true })!;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(e.data, 0, 0, 9, 8);
  e.data.close();
  const px = ctx.getImageData(0, 0, 9, 8).data;
  const lum = (x: number, y: number) => {
    const i = (y * 9 + x) * 4;
    return 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
  };
  let bits = 0n;
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) bits = (bits << 1n) | (lum(x, y) > lum(x + 1, y) ? 1n : 0n);
  (self as unknown as Worker).postMessage(bits.toString(16).padStart(16, "0"));
};
