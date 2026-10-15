// Genera public/local.html: la misma pagina que index.html pero con el encabezado HTML completo
// (al publicar como Artifact, la plataforma lo agrega sola). Sirve para abrir el simulador en el
// computador con un servidor local (ver abrir_simulador.bat / abrir_simulador.command).
import { readFileSync, writeFileSync } from 'node:fs';

const body = readFileSync(new URL('./public/index.html', import.meta.url), 'utf8');
const html = `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
</head>
<body>
${body}
</body>
</html>
`;
writeFileSync(new URL('./public/local.html', import.meta.url), html);
console.log('public/local.html listo');
