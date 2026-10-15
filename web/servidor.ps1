# Servidor local minimo para el simulador (Windows, sin instalar nada).
# Lo usa abrir_simulador.bat: sirve web/public en http://localhost:8765 y abre el navegador.
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'public'))
$port = 8765
$types = @{
  '.html' = 'text/html; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'
  '.json' = 'application/json; charset=utf-8'; '.txt' = 'text/plain; charset=utf-8'
  '.jpg' = 'image/jpeg'; '.png' = 'image/png'; '.css' = 'text/css'
}
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")
try { $listener.Start() } catch {
  Write-Host "No se pudo abrir el puerto $port (puede que el simulador ya este abierto)."
  Start-Process "http://localhost:$port/local.html"
  exit
}
Write-Host "Simulador en http://localhost:$port/local.html  -  cierra esta ventana para detenerlo."
Start-Process "http://localhost:$port/local.html"
while ($listener.IsListening) {
  $ctx = $listener.GetContext()
  try {
    $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
    if ($rel -eq '') { $rel = 'local.html' }
    $file = [IO.Path]::GetFullPath((Join-Path $root $rel))
    if ($file.StartsWith($root) -and (Test-Path -LiteralPath $file -PathType Leaf)) {
      $bytes = [IO.File]::ReadAllBytes($file)
      $ext = [IO.Path]::GetExtension($file).ToLower()
      $ctx.Response.ContentType = if ($types.ContainsKey($ext)) { $types[$ext] } else { 'application/octet-stream' }
      $ctx.Response.ContentLength64 = $bytes.Length
      $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $ctx.Response.StatusCode = 404
    }
  } catch {
    $ctx.Response.StatusCode = 500
  } finally {
    $ctx.Response.Close()
  }
}
