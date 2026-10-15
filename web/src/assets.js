// Recursos de la escena. Normalmente se leen de scene/ junto a la pagina (Artifact, GitHub o un
// servidor local). En la version de un solo archivo (make_standalone.mjs) vienen dentro del propio
// HTML como bloques <script type="text/plain" data-asset="ruta">base64 o texto</script>, asi la
// pagina abre con doble clic, sin servidor.
export const BASE = 'scene/';
const embedded = new Map();
for (const el of document.querySelectorAll('script[data-asset]')) embedded.set(el.dataset.asset, el);
export const isEmbedded = embedded.size > 0;

const blobUrls = new Map();
function b64ToBytes(s) {
  const bin = atob(s.replace(/\s+/g, ''));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

/** URL para cargar una imagen (archivo o blob creado desde el HTML) */
export function assetUrl(path) {
  const el = embedded.get(path);
  if (!el) return BASE + path;
  if (!blobUrls.has(path)) {
    const type = path.endsWith('.png') ? 'image/png' : 'image/jpeg';
    blobUrls.set(path, URL.createObjectURL(new Blob([b64ToBytes(el.textContent)], { type })));
    el.textContent = '';
  }
  return blobUrls.get(path);
}

export async function assetJSON(path) {
  const el = embedded.get(path);
  if (el) return JSON.parse(el.textContent);
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`no se pudo descargar ${path} (${res.status})`);
  return res.json();
}

/** Texto ASCII de un archivo .b64.txt (como bytes), con progreso de descarga */
export async function assetAscii(path, onProgress) {
  const el = embedded.get(path);
  if (el) {
    const bytes = new TextEncoder().encode(el.textContent);
    el.textContent = '';
    onProgress?.(1);
    return bytes;
  }
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`no se pudo descargar ${path} (${res.status})`);
  const total = Number(res.headers.get('content-length')) || 0;
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length;
    if (total) onProgress?.(Math.min(1, got / total));
  }
  const text = new Uint8Array(got);
  let o = 0;
  for (const c of chunks) { text.set(c, o); o += c.length; }
  return text;
}
