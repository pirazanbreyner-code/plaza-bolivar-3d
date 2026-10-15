// Genera dist/plaza-bolivar-3d.html: el simulador completo en UN solo archivo (codigo, modelo,
// texturas, cielos y calles incrustados). Se abre con doble clic, sin servidor.
//   npm run standalone
import { readFileSync, writeFileSync, readdirSync, statSync, mkdirSync } from 'node:fs';
import { join, relative } from 'node:path';

const pub = new URL('./public/', import.meta.url).pathname;
const sceneDir = join(pub, 'scene');
const files = [];
(function walk(dir) {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) walk(p);
    else if (f !== 'info.json') files.push(p);
  }
})(sceneDir);

const blocks = files.sort().map((p) => {
  const rel = relative(sceneDir, p);
  let data;
  if (rel.endsWith('.jpg') || rel.endsWith('.png')) data = readFileSync(p).toString('base64');
  else data = readFileSync(p, 'utf8').replaceAll('</', '<\\/');   // texto (json, base64)
  return `<script type="text/plain" data-asset="${rel}">${data}</script>`;
});

const app = readFileSync(join(pub, 'app.js'), 'utf8').replaceAll('</script', '<\\/script');
let html = readFileSync(join(pub, 'local.html'), 'utf8');
const tag = '<script type="module" src="app.js"></script>';
if (!html.includes(tag)) throw new Error('local.html no tiene la etiqueta del script');
html = html.replace(tag, () => `${blocks.join('\n')}\n<script type="module">\n${app}\n</script>`);
mkdirSync(new URL('./dist/', import.meta.url), { recursive: true });
const out = new URL('./dist/plaza-bolivar-3d.html', import.meta.url);
writeFileSync(out, html);
console.log(`dist/plaza-bolivar-3d.html: ${files.length} recursos, ${(html.length / 1e6).toFixed(1)} MB`);
