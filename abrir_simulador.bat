@echo off
rem Abre el simulador de la Plaza de Bolivar en el navegador (Windows).
rem Deja esta ventana abierta mientras lo usas; cierrala para terminar.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web\servidor.ps1"
