# Registro de aproximaciones

Qué partes del modelo son exactas, cuáles aproximadas y cómo verificarlas.
Fuentes completas en [`references/research_raw.md`](references/research_raw.md).
Todos los valores numéricos viven en [`scripts/plaza/config.py`](scripts/plaza/config.py).

## Datos con base medida (confianza media-alta)

| Elemento | Fuente | Precisión |
|---|---|---|
| Planta de la plaza (79,4 × 100,3 m) y plataforma de la estatua (14 × 14 m, desplazada 15 m al sur) | OpenStreetMap (r13663349) vía Overture Maps 2026-09-23.1 | ±1–2 m |
| Líneas y longitudes de fachada: Capitolio 88,6 m, Liévano 108,1 m (con su desvío de 1,4°), Justicia 83,2 m, Catedral + Sagrario 65,8 m | OSM | ±1–2 m |
| Rotación de la retícula: 31° al este del norte. Afecta la orientación del sol | OSM (ejes y fachadas, entre 29,5° y 32,4°) | ±1,5° |
| Relieve de los Cerros Orientales: Monserrate, Guadalupe y la cadena completa, unos 12 × 14,5 km | AWS Terrain Tiles z13 (unos 19 m/píxel, SRTM). Validado: plaza 2.614 m, Monserrate 3.136 m en la coordenada del santuario (dato publicado: 3.152 m), cumbre de Guadalupe 3.297 m (dato publicado: unos 3.317 m) | ±10–20 m en altura y unos 20 m en planta; las crestas finas se suavizan |
| Ciudad de fondo: 1.474 huellas reales de edificios en unos 700 m a la redonda | OSM vía Overture | Planta ±1–2 m; la **altura es estimada** (ver abajo) |
| Posición del sol según fecha y hora | Algoritmo NOAA, verificado (mediodía de octubre a 76° de elevación) | ±0,5° |

## Aproximaciones (estimadas, verificar con fotos)

| Elemento | Valor usado | Cómo se estimó | Cómo verificar |
|---|---|---|---|
| Altura del Capitolio | 20 m a la cornisa (podio 2,5 + columnas 14 + entablamento 3,5) | Blog (columnas de 14 m, confianza baja) + proporción | Foto frontal con escala (puertas, personas) |
| Columnata del Capitolio | Pórtico central de 6 × 3 columnas jónicas, 30 m de ancho, r = 0,70 m | "Seis filas de tres columnas" (Wikipedia, Reed) | Foto o plano. No se sabe si el frente tiene 6 o 3 columnas |
| Cuerpos laterales del Capitolio | 5 ejes de ventanas en 2 niveles, pilastras de orden gigante | Composición neoclásica genérica | Foto de la fachada norte |
| Catedral: ancho de fachada | 41,3 m (v 9,5 → 50,8) | Quiebre de la huella OSM, coherente con el ancho de 40 m de las naves | Plano o levantamiento |
| Catedral: alturas | Cornisa unos 25 m, frontón unos 30 m, torres de 3 cuerpos con cupulín y cruz unos 50 m | 52 m (Wikipedia) frente a 42 m (otras fuentes); se usa unos 50 m con la cruz | Foto con escala o dato oficial |
| Catedral: ornamento | Columnas toscanas/jónicas adosadas, 3 puertas en arco, hornacinas | Descripción genérica (dórico/jónico) | Foto frontal |
| Cuerpo entre la Catedral y el Sagrario | 13,1 m de frente, 13 m de alto, 2 pisos | Tramo de la huella OSM sin identificar | Foto |
| Capilla del Sagrario | Cuerpo de 17 m + espadaña hasta unos 22,5 m; cúpula unos 30 m | Fachada 11 × 22 m (Viajandox), cúpula unos 30 m | Foto |
| Palacio Arzobispal | Volumen principal retranqueado unos 15 m tras un jardín con muro; 4 pisos, 17,5 m; volumen de esquina de 3 pisos | OSM (posición) + SISBIC (4 pisos); altura = pisos × 4,4 m | **Dudoso**: SISBIC habla de fachada sobre la Cra 7. Verificar en Street View |
| Palacio de Justicia | 22 m, pórtico de pilares de 7 m, 4 pisos de ventanas cuadradas, inscripción de Santander | 5 pisos (SISBIC) × 4,4 m; composición aproximada | Foto frontal. El ritmo de vanos es aproximado |
| Edificio Liévano | 16 m a la cornisa, arcada de 5,6 m, 2 pisos, 32 ejes, mansardas solo en las esquinas, frontón central | Manual IDPC (16 m, indirecto) + EcuRed (32 vanos, mansardas de esquina) | Foto. El color (crema) es estimado |
| Estatua de Bolívar | Pedestal 4,6 m + figura 2,6 m, mirando al norte | Figura 2,6 m (media); pedestal por proporción (baja); la orientación tiene fuentes contradictorias | Foto. **La figura es una escultura simplificada, no un retrato** |
| Plataforma de la estatua | 0,55 m de alto, 3 gradas | Estimado (fuentes: "a manera de podio") | Foto |
| Atrio de la Catedral | 1,2 m de alto, unos 9 m de fondo, gradas de 15 cm a lo largo de v −15 → 50,8 | Estimado (atrio de 1–1,5 m) | Foto o Street View |
| Desnivel de la plaza | Plaza horizontal; calles 12 cm más bajas; Cra 8 con calzada 15 cm más baja | La reforma de 1960 niveló la plataforma; **no se modelaron** los muros de contención sobre la Cra 8 (1–2 m) | Street View de la Cra 8 |
| Pavimento | Losas de 0,80 × 0,80 m de piedra gris ocre | Sin despiece publicado | Foto cenital |
| Alturas de la ciudad de fondo | Según pisos de OSM cuando existen (20 de 1.474); si no, entre 1 y 12 pisos según superficie y zona (más altos al norte y occidente) | Aleatorio con semilla fija (reproducible) | No aplica: son edificios de contexto |
| Terreno cerca de la plaza | Plano hasta 380 m y fundido con el modelo de elevación hasta 900 m | La pendiente real (unos 4,5 % hacia el ONO) se ignora en el entorno inmediato | — |
| Cobertura de los cerros | Barrios por debajo de unos 2.760 m, bosque hasta 3.150 m, páramo por encima, roca en pendientes fuertes | Estimado por altitud (sin mapa de coberturas) | Imagen satelital |
| Santuarios de Monserrate y Guadalupe | Volúmenes simples en la cumbre más cercana del modelo de elevación | Coordenadas aproximadas | — |
| Mobiliario urbano (faroles, bolardos, bancas) | **No modelado** | Sin datos verificables | Street View |
| Personas, palomas, vehículos | **No modelados** | — | — |

## Simplificaciones técnicas

- Las texturas son procedurales (sin fotos): no reproducen manchas, letreros ni reparaciones reales.
- Los relieves, las esculturas de las fachadas y los capiteles corintios son geometría simplificada.
- Bruma atmosférica: mezcla exponencial por distancia (14 km) con el color del propio modelo de cielo. No es un volumen físico.
