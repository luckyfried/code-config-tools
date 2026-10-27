// Draws the XYZ tiles that cover the extent into one square canvas, whatever zoom the tiles come at.

export function loadImage(url, timeoutMs = 9000) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.decoding = "async";
    const timer = setTimeout(() => {
      img.src = "";
      reject(new Error("timeout"));
    }, timeoutMs);
    img.onload = () => {
      clearTimeout(timer);
      resolve(img);
    };
    img.onerror = () => {
      clearTimeout(timer);
      reject(new Error("load"));
    };
    img.src = url;
  });
}

// template: a URL with {z}, {x}, {y}. ext: the extent in tiles at ext.z. Returns { canvas, loaded, failed }.
export async function mosaic(template, zoom, ext, size) {
  const scale = 2 ** (zoom - ext.z);
  const x0 = ext.x0 * scale;
  const y0 = ext.y0 * scale;
  const span = (ext.x1 - ext.x0) * scale;
  const n = 2 ** zoom;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  const px = size / span;
  const jobs = [];
  for (let ty = Math.floor(y0); ty < y0 + span; ty++) {
    if (ty < 0 || ty >= n) continue;
    for (let tx = Math.floor(x0); tx < x0 + span; tx++) {
      const wx = ((tx % n) + n) % n;
      const url = template.replace("{z}", zoom).replace("{x}", wx).replace("{y}", ty);
      jobs.push(
        loadImage(url).then((img) => {
          ctx.drawImage(img, (tx - x0) * px, (ty - y0) * px, px + 0.5, px + 0.5);
          return true;
        }),
      );
    }
  }
  const results = await Promise.allSettled(jobs);
  const loaded = results.filter((r) => r.status === "fulfilled").length;
  return { canvas, loaded, failed: results.length - loaded };
}
