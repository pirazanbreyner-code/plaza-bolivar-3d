#!/bin/sh
# Abre el simulador de la Plaza de Bolivar en el navegador (Mac y Linux; necesita python3).
# Deja esta ventana abierta mientras lo usas; cierrala (o Ctrl+C) para terminar.
cd "$(dirname "$0")/web/public" || exit 1
URL=http://localhost:8765/local.html
(sleep 1; open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null) &
echo "Simulador en $URL  -  cierra esta ventana para detenerlo."
python3 -m http.server 8765 --bind 127.0.0.1
