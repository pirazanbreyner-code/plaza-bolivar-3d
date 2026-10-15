# Plaza de Bolívar (Bogotá): medidas de referencia para el modelo de masas 3D

Investigación del 2026-10-15. Este archivo es una investigación en bruto: cada valor lleva fuente, confianza y notas.

## 0. Método y advertencias (leer antes de usar los números)

- **Geometría (fuente principal):** las huellas de edificios, el polígono de la plaza y los ejes viales vienen de **OpenStreetMap**, leído a través del volcado **Overture Maps, release 2026-09-23.1** (S3 público: `https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-09-23.1/`, temas `buildings`, `base/land_use`, `transportation`). Proyecté las huellas a UTM 18N (EPSG:32618; el factor de escala es 0,99973 y la convergencia 0,07°, así que ambos son despreciables) y medí distancias en un **marco local alineado con la retícula** (sección 0.1). Muchas huellas del centro de Bogotá en OSM provienen de una importación catastral, así que la precisión esperable es de ±1–2 m. Las grandes relaciones (Capitolio, Liévano, Justicia, plaza) las dibujaron mapeadores a mano. Los IDs de OSM se citan para poder verificarlos en openstreetmap.org.
- **Altimetría:** usé el DSM Copernicus GLO-30 (`https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N04_00_W075_00_DEM/...`) y AWS Terrain Tiles (`https://registry.opendata.aws/terrain-tiles/`). Las celdas son de 30 m e incluyen edificios, así que **solo sirven para la pendiente regional**, no para medir desniveles locales.
- **Fuentes web:** desde este contenedor no se pudieron abrir directamente los sitios (wikipedia, eltiempo, idpc, sisbic, etc.). Los valores citados de esas URLs salen de los extractos que devolvió el buscador, no de una lectura completa de la página. Conviene abrir la URL para confirmar antes de dar un número por definitivo.
- **"estimado"** = cálculo propio (pisos × altura típica, proporciones, fotos), no un dato publicado.

### 0.1 Marco local recomendado para Blender

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Origen (0,0) | 4.5981062 N, -74.0760391 W (centroide del polígono OSM de la plaza) | https://www.openstreetmap.org/relation/13663349 | alta | Es el centro de la superficie pavimentada. |
| Rotación de la retícula | Carreras ≈ **31° al este del norte verdadero** (azimut 29,5–32,4° según el elemento); calles ≈ 121° (perpendiculares) | OSM vía Overture (ejes Cra 7, Cra 8, Cl 10, Cl 11 y fachadas) | alta | Fachada Liévano 32,4°, fachada Catedral 32,0°, bordes de la plaza 30,6–31,2°, eje Cra 8 29,5°, eje Cra 7 30,1°, fachadas del Capitolio y de Justicia 120,9–121,1°. |
| Ejes locales | u = "este de retícula" (azimut 121°); v = "norte de retícula" (azimut 31°) | cálculo | alta | E = u·cos31° + v·sin31°; N = −u·sin31° + v·cos31° (metros). lat ≈ 4.5981062 + N/110574; lon ≈ −74.0760391 + E/110962. |
| En Blender (X = Este verdadero, Y = Norte verdadero) | Rotar todo el conjunto alineado a la retícula **−31° en Z** (horario visto desde arriba) | cálculo | alta | Otra opción: modelar en (u,v) con la plaza ortogonal y rotar solo el sol/cielo +31°. |

Todas las coordenadas (u,v) de este informe están en metros en ese marco.

---

## 1. La plaza

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Superficie pavimentada de la plaza (plataforma), lado E–O (paralelo a las calles) | **79,4 m** (u = −39,6 → +39,8) | OSM relation 13663349: https://www.openstreetmap.org/relation/13663349 | media-alta | Borde que mapeó OSM como "Plaza de Bolívar" (place=square). No incluye las calzadas/andenes de Cra 7, Cra 8, Cl 10 ni Cl 11. |
| Superficie pavimentada, lado N–S (paralelo a las carreras) | **100,3 m** (v = −50,1 → +50,1) | ídem | media-alta | Esquina NO recortada: escalón de 11,3 × 2,6 m en (u −39,3…−28,0; v 47,5…50,1). |
| Área de la plataforma | 7.677 m² netos (≈ 7.870 m² incluyendo la plataforma de la estatua) | ídem | media-alta | Calculada sobre el polígono OSM. |
| Área "oficial" con calles | **13.903 m²**, capacidad ≈ 55.600 personas (46.212 sin calles) | El Tiempo: https://www.eltiempo.com/archivo/documento/CMS-14179558 ; Archivo de Bogotá: https://archivobogota.secretariageneral.gov.co/noticias/la-plaza-bolivar-0 ; Alcaldía: https://bogota.gov.co/mi-ciudad/cultura-recreacion-y-deporte/lo-que-tu-no-sabias-de-la-plaza-de-bolivar-de-bogota | alta (como dato publicado) | Viene de un estudio de la Universidad de los Andes e incluye calles y las escaleras de la Catedral. Es coherente con el espacio peatonal entre fachadas menos la Cra 8 vehicular (≈ 116,8 × 134,4 − 16 × 134 ≈ 13.550 m²). |
| Distancia entre fachadas E–O (Liévano ↔ Catedral) | **≈ 116 m** (u −55,6 → +60,7) | OSM (relation 7445708, way 24251969) | media | Liévano −57,0 (extremo S) a −54,3 (extremo N); Catedral +60,4/+61,8. |
| Distancia entre fachadas N–S (Capitolio ↔ Palacio de Justicia) | **≈ 134,4 m** (v −67,4 → +67,0) | OSM (relation 7445709, relation 9452213) | media | |
| Orientación de la retícula | Carreras a ~31° E del N verdadero | ver 0.1 | alta | La plaza "mira" al NNE/SSO. Vista desde arriba, la Cra 7 corre de SSO a NNE. |
| Cota del terreno | ≈ 2.606–2.614 m s.n.m. | Copernicus GLO-30 / AWS Terrain Tiles | media | Son DSM de 30 m, ±5 m. En la literatura se citan ~2.600–2.640 m para Bogotá. |
| Pendiente natural del terreno | ≈ 4–4,5 % de descenso hacia el ONO (eje −u). Equivale a **≈ 5 m** entre la Catedral y el Liévano. N–S ≈ 2 %, dentro del ruido. | Transecto de ±400 m en el DSM Copernicus GLO-30 (cálculo propio) | baja-media | Pendiente regional, no la de la superficie actual de la plaza. |
| Desnivel dentro de la plaza | La reforma de 1960 "solucionó el problema de declive", así que la plataforma es **prácticamente horizontal**. Hay **muros sobre la Carrera 8** (lado bajo, occidental) y gradas en el atrio de la Catedral (lado alto, oriental). Estimación: pendiente de la plataforma < 1 %; borde sobre la Cra 8 ≈ 1–2 m sobre la calle en el extremo más bajo (estimado). | Banrep/Credencial: https://www.banrepcultural.org/biblioteca-virtual/credencial-historia/numero-351/un-arquitecto-una-obra-fernando-martinez-sanabria ; Alcaldía 2013 ("muros sobre la carrera octava", "losas del piso"): https://bogota.gov.co/mi-ciudad/cultura-recreacion-y-deporte/la-plaza-y-el-monumento-de-bolivar-seran-restaurados | media (cualitativo) / baja (cifras) | No encontré cotas publicadas. Verificar con fotos o Street View de la Cra 8. |
| Diseño actual | Plaza dura de 1960 (concurso de 1959), de Fernando Martínez Sanabria y Guillermo Avendaño. Sin árboles ni fuentes (se retiraron las fuentes y el parqueo). | Banrep (arriba); Urbipedia: https://www.urbipedia.org/hoja/Fernando_Mart%C3%ADnez_Sanabria | alta | Declarada BIC por el Decreto 1802 de 1995. Hay manual de uso del IDPC de 2024. |
| Pavimento | **Losas de piedra** ("losas del piso", "losas de piedra"). Patrón: retícula ortogonal de losas alineada con la plaza (estimado; no encontré el despiece). | Alcaldía 2013 (arriba); Alcaldía: https://bogota.gov.co/mi-ciudad/cultura-recreacion-y-deporte/asi-reconstruyen-el-emblematico-monumento-al-libertador-en-la-plaza-de | media (material) / baja (patrón) | Color gris-ocre, piedra arenisca local (estimado por fotos). |
| Estatua de Bolívar: posición | Sobre una **plataforma cuadrada de ≈ 14 × 14 m** elevada "a manera de podio". Centro en (u = 6,4; v = −15,3): **desplazada ≈ 15 m hacia el Capitolio (sur) y ≈ 6 m al este** del centroide de la plaza. Coordenadas del centro: 4.5979582, −74.0760606. | OSM (hueco interior del polígono 13663349); Manual IDPC 2024: https://idpc.gov.co/Transparencia/Resoluciones/2024/Manual_de_Uso_Plaza_de_Bolivar.pdf | media | El eje del Capitolio está en u ≈ 3,5, así que la estatua queda ~3 m al este del eje. Las fuentes turísticas dicen "en el centro", pero OSM la sitúa en la mitad sur. |
| Estatua: orientación | Probablemente mira al **norte, hacia el Palacio de Justicia**, de espaldas al Capitolio. | colombia.com: https://www.colombia.com/turismo/sitios-turisticos/bogota/atractivos-turisticos/sdi461/75883/plaza-de-bolivar ; Archivo de Bogotá (en 1876 miraba a la Catedral y en 1880 quedó "enfrentada al Capitolio") | baja | Las fuentes se contradicen. Verificar con una foto. |
| Estatua: figura de bronce | **2,6 m** de alto (Pietro Tenerani, fundida en Múnich por F. von Müller, inaugurada el 20-07-1846) | OEA: http://www.oas.org/children/simon/monumentos.html ; copia de la ficha IDPC: https://ulianamolano.wixsite.com/artepublico-unad/post/obra-4-monumento-a-sim%C3%B3n-bol%C3%ADvar | media | Otra copia de la ficha dice "dimensiones desconocidas". |
| Estatua: pedestal | Peana de bronce, pedestal y basamento de **piedra arenisca** con 4 relieves de bronce. Altura del pedestal **≈ 4–5 m** (estimado); monumento total ≈ 7–8 m sobre la plataforma (estimado). | IDPC, folleto "Adopta un monumento": https://idpc.gov.co/wp-content/uploads/2019/12/Brochure-Monumentos_FINAL_WEB-min.pdf | media (material) / baja (altura) | La altura es una estimación por proporción con la figura de 2,6 m vista en fotos. |
| Plataforma de la estatua: altura | ≈ 0,5–1,0 m con gradas perimetrales (estimado) | Manual IDPC 2024 (plataforma elevada); Alcaldía (gradas de la plataforma destruidas por vandalismo y luego reparadas) | baja | |
| Postes de luz / faroles | Hay "luminarias de la Plaza" (incluidas en la restauración de 2013). OSM solo registra 1 farol (street_lamp) en la esquina Cra 8/Cl 11 (u −48,2; v 57,1). Número y tipo: sin dato. | Alcaldía 2013 (arriba); OSM nodo 12410529194 | baja | También hay un convenio de iluminación permanente de fachadas: https://www.eltiempo.com/politica/congreso/fachadas-de-plaza-de-bolivar-estaran-iluminadas-todo-el-ano-728609 |
| Bolardos, astas, fuente | No hay fuente (se eliminaron en 1960). Sin datos verificables de bolardos ni de astas fijas en la plaza; las banderas cuelgan de los edificios. | Banrep (fuentes eliminadas) | baja | El Manual IDPC prohíbe montajes sobre la estatua, las escalinatas del Capitolio y el atrio de la Catedral, y limita la altura de montajes a 16 m. |
| Otros fijos | Hidrante (pilar) en el andén de la Cra 8, esquina con la Cl 11 (u −45,7; v 55,5). Punto de información turística (u −76, v −78) fuera de la plaza, al SO de la esquina Cra 8/Cl 10. | OSM (Overture `base/infrastructure`) | media | Detalle menor. |

---

## 2. Calles perimetrales

Los anchos son de **fachada (o borde de edificio) a borde de la plataforma** medidos en OSM, e incluyen calzada y andenes. No encontré anchos oficiales de calzada.

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Carrera 7 (oriente) | **≈ 20,8 m** de la plataforma a la fachada de la Catedral, incluido el atrio y sus gradas. Eje OSM en u ≈ 47–48,5 frente a la plaza. **Peatonal** ("Avenida Carrera 7", highway=pedestrian). | OSM way 88754482 | media | El atrio de la Catedral mide "110 m de largo" (kiddle/advisor, ver sección 4). Profundidad del atrio ≈ 8–10 m (estimado). |
| Carrera 8 (occidente) | **≈ 16 m** de la plataforma a la fachada del Liévano. Eje en u ≈ −49,5 (S) a −52,6 (N). **Vehicular**: un sentido hacia el sur, máximo 30 km/h frente a la plaza; cerrada a vehículos entre Cl 11 y Cl 12. | OSM ways 1113758882, 937420322, 88754909 | media | Calzada ≈ 7 m más andenes (estimado). En este lado están los muros de contención de la plaza. |
| Calle 10 (sur) | **≈ 17,3 m** de la plataforma a la fachada del Capitolio, incluidas sus escalinatas. Eje en v ≈ −61. **Peatonal** (paving_stones). | OSM ways 679587969, 1057024290, 522249959 | media | |
| Calle 11 (norte) | **≈ 16,9 m** de la plataforma a la fachada de Justicia. Eje en v ≈ 58,5–60,5. **Peatonal** (paving_stones). | OSM way 679587970 | media | Al oriente de la Cra 7, la Calle 11 es vehicular (residential). |
| Separación entre ejes | Cra 8 ↔ Cra 7 ≈ 100–106 m; Cl 10 ↔ Cl 11 ≈ 120–122 m | OSM | media | |

---

## 3. Capitolio Nacional (lado sur; fachada principal al NNE, azimut ≈ 31°)

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Longitud de la fachada sobre la plaza | **88,6 m** (u −40,8 → +47,8, a lo largo de v = −67,4) | OSM relation 7445709: https://www.openstreetmap.org/relation/7445709 | media-alta | Eje de simetría en u ≈ 3,5. |
| Ancho máximo | 96,1 m (cuerpos laterales salientes hacia atrás, u −44,9 → +51,2) | ídem | media-alta | |
| Fondo | **95,5 m** (v −67,4 → −162,9) | ídem | media-alta | La fachada posterior tiene el cuerpo central retranqueado (Patio Núñez, 23,4 m de ancho × 26,5 m de fondo). |
| Huella | 7.066 m² netos (≈ 7.980 m² brutos con patios). Patio Mosquera, justo detrás del pórtico: 24 × 30 m. Hay 4 patinejos de ≈ 5 × 10 m. | ídem | media | "20.000 m²" en Aleteia/Wikipedia es superficie construida o del predio: https://es.aleteia.org/2020/07/22/capitolio-nacional-una-joya-arquitectonica-colombiana-construida-en-80-anos/ |
| Pisos | 3 pisos + sótano, 4 patios | Wikipedia es: https://es.wikipedia.org/wiki/Capitolio_Nacional_de_Colombia | media | OSM dice 2 (building:levels). |
| Composición de la fachada | Dos cuerpos laterales simétricos y cuerpo central "transparente" a manera de pórtico: **columnata jónica de "seis filas de tres columnas"** (18 columnas) que deja ver el Patio Mosquera. | Wikipedia es (arriba); Structurae: https://structurae.net/fr/ouvrages/capitolio-nacional | media | La disposición exacta (6 de frente × 3 de fondo, o al revés) no está clara. Verificar con foto. Ancho del cuerpo central ≈ 24–30 m (estimado por el ancho del Patio Mosquera). |
| Altura de las columnas | **≈ 14 m**, diámetro ≈ 0,9 m (según un blog) | Di-señas: https://cerayasociados.blogspot.com/2013/11/capitolio-nacional-bogota_16.html | baja | Un jónico de 14 m tendría normalmente ~1,4–1,6 m de diámetro. El dato de 0,9 m es dudoso. |
| Altura a cornisa/parapeto | **≈ 20 m** sobre la plaza (estimado: podio ~2,5 m + columna ~14 m + entablamento ~3,5 m) | estimado | baja | Sobre la cubierta hay 4 grifos (figuras de león-águila): https://www.radionacional.co/cultura/historia-colombiana/trece-curiosidades-que-debe-saber-sobre-el-capitolio-nacional |
| Escalinata / podio | Hay "escalinatas del Capitolio" frente al pórtico; el atrio queda más alto que la plaza. Altura ≈ 2–3 m (estimado). | Manual IDPC 2024 (arriba); blog Di-señas; guía de la colección Lelarge (Archivo de Bogotá): https://archivobogota.secretariageneral.gov.co/sites/default/files/fondo_documental/8.%20Gu%C3%ADa%20colecci%C3%B3n%20Gast%C3%B3n%20Lelarge.pdf | media (existencia) / baja (altura) | Lelarge proyectó "las dos escaleras de entrada principal del lado norte" (1908–1913); puede referirse a escaleras interiores. |
| Material | Piedra de cantería ("piedra rubia" de canteras cercanas) | Radio Nacional (arriba) | alta | Construido entre 1848 y 1926 (Thomas Reed, Cantini, Lelarge, Santamaría y Manrique Martín). |

---

## 4. Catedral Primada, Capilla del Sagrario, Palacio Arzobispal y Colegio de San Bartolomé (lado oriental; fachadas al ONO, azimut ≈ 301°)

Orden de norte a sur sobre la Cra 7: **Catedral** (esquina Calle 11) → **Capilla del Sagrario** → **Palacio Arzobispal** (esquina Calle 10) → [Calle 10] → **San Bartolomé / San Ignacio**.

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Conjunto Catedral + Sagrario: frente sobre la Cra 7 | **65,8 m** (v −15,0 → +50,8, a lo largo de u ≈ 60,5–61,8) | OSM way 24251969: https://www.openstreetmap.org/way/24251969 | media-alta | OSM agrupa los dos templos en un solo polígono. |
| Fachada de la Catedral (ancho) | **≈ 54 m** (v ≈ −3,6 → +50,8), derivado de restar al conjunto los 11 m del Sagrario. Puede ser ≈ 41 m si el quiebre en v ≈ 9,5 marca el borde de la torre sur. | derivado de OSM + Viajandox | baja-media | No encontré un ancho de fachada publicado. |
| Fondo / huella | 108 m de fondo (Cra 7 → Cra 6). Huella OSM de 6.021 m² (con Sagrario); Wikipedia da ≈ 5.300 m² para la Catedral sola, de 5 naves en cruz latina. | OSM; Wikipedia es: https://es.wikipedia.org/wiki/Catedral_primada_de_Colombia | media | |
| Altura de las torres | **52 m** (Wikipedia/Wikidata, "reforma de 1943") frente a **42 m** (Viajandox, advisor.travel) | Wikidata: https://www.wikidata.org/wiki/Q2942872 ; Anexo de edificios altos: https://es.wikipedia.org/wiki/Anexo:Edificios_m%C3%A1s_altos_de_Colombia ; https://viajandox.com.co/bogota/catedral-primada-de-colombia-A2654 ; https://es.advisor.travel/poi/Catedral-Primada-de-Colombia-8341 | media (52) / baja (42) | Dos torres de tres cuerpos: la sur (Santa Bárbara) y la norte (San Emigdio, con reloj). Primer cuerpo dórico; segundo cuerpo y torres jónicos. |
| Cuerpo principal de la fachada (sin torres) | ≈ 22–25 m (estimado: 2 cuerpos superpuestos, torres ≈ 2× esa altura) | estimado | baja | |
| Nave central | ≈ 20–24 m a la clave (estimado). Bóvedas de cañón sobre columnas; cúpula sobre tambor en el crucero. | estimado; Wikipedia es (descripción) | baja | No encontré la cifra. |
| Puertas | Principal 7,20 × 3,60 m; laterales 5,60 × 2,80 m | advisor.travel (arriba); Kiddle: https://kids.kiddle.co/Primatial_Cathedral_of_Bogot%C3%A1 | media | Útiles para dar escala a la fachada. |
| Atrio y gradas | Atrio de **≈ 110 m de largo** a lo largo de la Cra 7, con escaleras donde se sienta la gente. Altura ≈ 1–1,5 m (≈ 6–9 gradas) y profundidad ≈ 8–10 m (estimado). | Kiddle/advisor (110 m); Manual IDPC ("atrio de la Catedral") | media (largo) / baja (alto) | Absorbe parte del desnivel natural (el lado oriental es el alto). |
| Capilla del Sagrario (al sur de la Catedral) | Fachada de **11 m de ancho × 22 m de alto**; cúpula sobre el crucero de **≈ 30 m**. Construida entre 1660 y 1700. | Viajandox: https://viajandox.com.co/bogota/capilla-del-sagrario-de-la-catedral-de-bogota-A2667 ; Flickr: https://www.flickr.com/photos/pris63/52915178087 ; Wikipedia: https://es.wikipedia.org/wiki/Capilla_del_Sagrario_de_Bogot%C3%A1 | media | En OSM corresponde al tramo v −15,0 → −3,6 (11,4 m), coherente con el dato. Tiene un campanario propio. |
| Palacio Arzobispal (Cra 7 n.º 10-20, esquina Calle 10) | **4 pisos**, fachadas sobre la Cra 7 y la Calle 10 con zócalo y enchape de piedra y portada central de piedra de 2 pisos. Construido entre 1952 y 1957 (Esguerra, Sáenz, Urdaneta y Suárez). Frente sobre la Cra 7 ≈ 39 m (v −15 → −54,6). Altura ≈ 16–18 m (estimado: 4 × 4–4,5 m). | SISBIC: https://sisbic.idpc.gov.co/inmueble/1495 ; Wikiwand: https://www.wikiwand.com/es/articles/Palacio_arzobispal_de_Bogot%C3%A1 ; Gaudium Press: https://es.gaudiumpress.org/content/14374-una-visita-al-palacio-arzobispal-en-bogota/ | media (pisos) / baja (altura) | En OSM el volumen principal ("Palacio Cardenalicio", way 24457222, 24 × 25 m) está retranqueado ~15 m tras un jardín con muro (u 65–76), con un volumen de 3 pisos en la esquina (way 663354104, 11,7 × 11,4 m). Verificar con foto: SISBIC habla de fachada sobre la Cra 7. |
| Colegio Mayor de San Bartolomé (Cra 7 n.º 9-96, al sur de la Calle 10) | Huella OSM de 4.061 m², con frente sobre la Cra 7 de **≈ 68 m** (v −100,4 → −168,1) y sobre la Calle 9 de ≈ 103 m. **3 pisos**; altura ≈ 13–15 m (estimado). | OSM way 28289653: https://www.openstreetmap.org/way/28289653 ; Wikipedia: https://es.wikipedia.org/wiki/Edificio_del_Colegio_Mayor_de_San_Bartolom%C3%A9_(Bogot%C3%A1) | media (huella) / baja (altura) | En OSM la esquina exacta Cra 7/Cl 10 (u 69–102, v −100…−64) es un espacio cercado sin edificio, y la Iglesia de San Ignacio da a la Calle 10 en u 102–139. Reforma de 1919–1937. Monumento Nacional (Decreto 1584 de 1975). |

---

## 5. Palacio de Justicia (lado norte; fachada al SSO, azimut ≈ 211°)

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Longitud de la fachada sobre la plaza | **83,2 m** según la huella OSM (u −39,5 → +43,7). El lote mide **99,62 m por la Calle 11** según SISBIC. | OSM relation 9452213: https://www.openstreetmap.org/relation/9452213 ; ficha SISBIC: https://sisbic.idpc.gov.co/Fichas_CH/FV_003110013001.pdf | media | Discrepancia sin resolver. 99,6 m dejaría solo ~7 m entre los ejes OSM de la Cra 7 y la Cra 8, así que para el modelo recomiendo 83–84 m. |
| Fondo | 93,7 m (OSM); 95,95 m (SISBIC) | ídem | media-alta | Ocupa toda la manzana 13 del barrio La Catedral. Patio interior de 31,4 × 38,7 m. |
| Pisos | Varios volúmenes: **5 pisos** en los volúmenes delanteros y **máximo 10** en el tercer volumen (posterior). Otra fuente habla de 2 torres de 3 pisos unidas y de un cuerpo de 7. | SISBIC: https://sisbic.idpc.gov.co/inmueble/802 ; El Tiempo: https://www.eltiempo.com/archivo/documento/MAM-829827 | media (SISBIC) | OSM dice 3 pisos (poco fiable). |
| Altura | Fachada a la plaza ≈ 20–24 m (5 pisos × 4–4,5 m, estimado). Volumen más alto ≈ 35–38 m (10 pisos, estimado). | estimado | baja | Fachada sobria de piedra blanca con la frase de Santander. Concreto reforzado (SISBIC). Obra de Roberto Londoño terminada en 1999 y ocupada desde 2004. |

---

## 6. Edificio Liévano / Alcaldía Mayor (lado occidental; fachada al ESE, azimut ≈ 121°)

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Longitud de la fachada sobre la Cra 8 | **108,1 m** (v −52,9 → +55,2) | OSM relation 7445708: https://www.openstreetmap.org/relation/7445708 | media-alta | Coincide con el **"frente 108,3 m"** de la ficha SISBIC del predio Calle 11 n.º 9-50 (manzana 3): https://sisbic.idpc.gov.co/Fichas_CH/FV_003110003009.pdf |
| Fondo / manzana | OSM cubre toda la manzana: ≈ 111 × 112 m (10.421 m² netos). SISBIC da un fondo de 99,0 m. | ídem | media | El predio tiene 3 inmuebles; el más alto es de 9 pisos (Edificio Bicentenario de 2011, detrás). Patio interior ajardinado de 1.547 m². |
| Profundidad del ala sobre la plaza | ≈ 20 m (de la fachada al patio, derivado de OSM) | OSM | baja-media | |
| Niveles | Basamento en **arcada de piedra** (portal) + **2 niveles** con **32 vanos de ventana por nivel**, es decir 3 niveles. Fachada de tres cuerpos con pilastras y frontón triangular; **mansardas en las dos esquinas** (la central se suprimió en 1974). | EcuRed: https://www.ecured.cu/Palacio_Li%C3%A9vano ; Wikipedia es: https://es.wikipedia.org/wiki/Alcald%C3%ADa_Mayor_de_Bogot%C3%A1 ; Alcaldía: https://bogota.gov.co/asi-vamos/obras/restauracion-de-la-facha-lievano-y-el-palacio-municipal | media-alta | Ritmo de vanos ≈ 108/32 ≈ 3,4 m (derivado). Fachadas sobre la Cl 10, la Cl 11 y la Cra 8. |
| Altura a cornisa | **≈ 16 m** | Manual IDPC 2024 ("altura máxima de montajes 16 m tomando como referencia el Edificio Liévano"): https://idpc.gov.co/Transparencia/Resoluciones/2024/Manual_de_Uso_Plaza_de_Bolivar.pdf | media | Dato indirecto. Equivale a ≈ 5,3 m por nivel. Mansardas de esquina ≈ +4–5 m (estimado). |
| Arcada | Pórtico en planta baja a lo largo de la Cra 8 (andén cubierto). Profundidad ≈ 4–5 m (estimado). | EcuRed (arcada en piedra) | media (existencia) / baja (medida) | No sé si la huella OSM incluye el pórtico. |
| Contexto | Arquitecto Gaston Lelarge; obra entre 1902 y 1910, sobre el sitio de las Galerías Arrubla (53 m de frente, incendiadas en 1900). | Wikipedia en: https://en.wikipedia.org/wiki/Palacio_Li%C3%A9vano | media | |

---

## 7. Coordenadas (WGS84)

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Centro de la plaza (centroide de la plataforma) | **4.5981062, −74.0760391** | OSM relation 13663349 | alta | Centro del marco de fachadas: 4.5980916, −74.0760184 (2,6 m de diferencia). |
| Esquina plataforma SO de retícula (Cra 8 / Cl 10), la más occidental | 4.5979030, −74.0765779 | OSM | media-alta | |
| Esquina plataforma SE (Cra 7 / Cl 10), la más austral | 4.5975315, −74.0759653 | OSM | media-alta | |
| Esquina plataforma NE (Cra 7 / Cl 11), la más oriental | 4.5982936, −74.0755140 | OSM | media-alta | Con un pequeño chaflán a 4.5983239, −74.0755234. |
| Esquina plataforma NO (Cra 8 / Cl 11), la más septentrional | 4.5986577, −74.0761215 | OSM | media-alta | |
| Cruces de ejes viales | Cra 8 × Cl 10: 4.5978551, −74.0767119 · Cra 7 × Cl 10: 4.5973507, −74.0758445 · Cra 7 × Cl 11: 4.5983181, −74.0753677 · Cra 8 × Cl 11: 4.5988213, −74.0761632 | OSM (ejes) | media | |
| Esquinas del marco de fachadas | SO 4.5978497, −74.0767920 · SE 4.5973007, −74.0758840 · NE 4.5983368, −74.0752502 · NO 4.5988788, −74.0761466 | derivado de OSM | media | Intersecciones de las líneas de fachada Liévano/Capitolio/Catedral/Justicia. |
| Centro de la plataforma de la estatua | 4.5979582, −74.0760606 | OSM | media | |

---

## 8. Luz y cielo

| Elemento | Valor | Fuente (URL) | Confianza | Notas |
|---|---|---|---|---|
| Nubosidad | Cielo **cubierto o mayormente nublado entre el ~70 % (agosto) y el ~90 % (abril)** del tiempo. La época más nublada va de finales de septiembre a principios de junio. Luz típica: difusa, suave, gris-blanca, con claros breves. | WeatherSpark: https://weatherspark.com/y/23324/Average-Weather-in-Bogot%C3%A1-Colombia-Year-Round | media-alta | Lluvias en marzo–mayo y octubre–noviembre. La radiación en el centro es ≈ 4–4,5 kWh/m²·día (IDEAM vía https://construible.es/comunicaciones/comunicacion-integracion-energias-renovables-viviendas-bogota-colombia). |
| Geometría solar (lat 4,6° N) | Elevación del sol al mediodía: **85° en los equinoccios (al sur), 71° en junio (al norte), 62° en diciembre (al sur)**; cenital a mediados de abril y a finales de agosto. Día de 11,9–12,4 h; salida ≈ 5:40–6:15 y puesta ≈ 17:45–18:20 (UTC−5). | cálculo astronómico; WeatherSpark (duración del día) | alta | Por la rotación de 31°: la Catedral (fachada al ONO) recibe el sol de la tarde, el Liévano (al ESE) el de la mañana, Justicia (al SSO) la mayor parte del año, y el Capitolio (al NNE) queda en sombra salvo de mediados de abril a finales de agosto (cuando el sol pasa al norte). |
| Recomendación de render | Cielo nublado (HDRI overcast) o sol de 2.600 m (aire limpio, UV alto) con nubes cúmulo; temperatura de color ≈ 6.500–7.500 K en días nublados. | estimado | — | |

---

## Apéndice A: huellas simplificadas en el marco local (u,v) en metros

Origen en 4.5981062, −74.0760391; v hacia el azimut 31°. Simplificadas con tolerancia de 0,4 m a partir de OSM vía Overture 2026-09-23.1. Úsalas como perfil para extruir.

```
Plaza de Bolívar (OSM r13663349), área 7677 m²
 ext: (-39.6,-50.1) (39.8,-50.2) (39.2,47.8) (36.6,50.1) (-28.0,49.8) (-28.0,47.5) (-39.3,47.5)
 hueco = plataforma de la estatua (196 m²): (13.3,-22.3) (-0.7,-22.2) (-0.5,-8.2) (13.5,-8.3)

Capitolio Nacional (OSM r7445709), 7066 m²; 3 pisos + sótano
 ext: (-40.8,-67.4) (-41.0,-99.5) (-44.7,-99.5) (-44.9,-128.2) (-40.7,-128.2) (-40.9,-161.9) (-6.1,-162.2) (-6.0,-136.1) (17.3,-136.0) (17.1,-162.5) (46.5,-162.9) (46.7,-127.8) (51.1,-127.8) (51.2,-99.1) (47.6,-99.1) (47.8,-67.3)
 Patio Mosquera (709 m²): (14.7,-74.3) (14.3,-104.4) (-9.3,-104.2) (-8.9,-74.1)
 patinejos (51 m² c/u): (29.0,-122.3)(28.8,-112.7)(34.1,-112.6)(34.3,-122.1) | (29.3,-96.2)(29.1,-86.7)(34.3,-86.5)(34.6,-96.1) | (-28.1,-112.6)(-22.8,-112.5)(-22.6,-122.1)(-27.8,-122.2) | (-21.8,-95.2)(-27.1,-95.4)(-27.3,-85.8)(-22.0,-85.6)

Catedral Primada + Capilla del Sagrario (OSM w24251969), 6021 m²
 ext: (61.8,50.8) (61.0,50.0) (61.4,45.7) (60.9,45.2) (60.4,9.7) (61.2,9.4) (60.7,-15.0) (88.9,-15.2) (88.9,-21.7) (108.7,-21.8) (109.5,-5.5) (132.8,-5.7) (133.0,9.1) (168.2,8.8) (168.8,49.1) (69.0,50.0) (68.5,50.8) (63.2,50.3) (63.2,50.8)
 (Sagrario ≈ tramo de fachada v -15.0 → -3.6)

Palacio Cardenalicio / Arzobispal, volumen principal (OSM w24457222), 600 m², 4 pisos
 ext: (76.2,-23.3) (75.9,-48.4) (99.7,-48.6) (100.0,-23.4)
Volumen de esquina Cra 7/Cl 10 (OSM w663354104), 133 m², 3 pisos
 ext: (63.6,-54.6) (75.3,-54.5) (75.2,-43.1) (63.5,-43.2)

Palacio de Justicia (OSM r9452213), 6583 m²
 ext: (-39.5,67.1) (43.7,66.9) (44.4,160.6) (-38.8,160.8)
 patio (1210 m²): (19.2,86.6) (-12.1,86.6) (-11.9,125.3) (19.4,125.3)

Palacio Liévano, manzana completa (OSM r7445708), 10421 m²
 ext: (-57.0,-52.9) (-54.3,55.2) (-165.9,59.8) (-165.3,-50.7)
 patio ajardinado (1547 m²): (-80.2,14.5) (-75.9,14.4) (-76.4,-14.7) (-94.2,-14.5) (-94.3,-20.2) (-110.9,-20.0) (-110.0,29.9) (-80.0,29.5)
 patinejo (50 m²): (-76.7,-27.9) (-76.6,-39.4) (-81.0,-39.4) (-81.1,-28.0)

Casa del Florero / Museo de la Independencia (OSM w58868730), 611 m², esquina NE (Cra 7 × Cl 11), 2 pisos (estimado ≈ 9 m)
 ext: (65.1,59.6) (86.3,59.6) (86.3,68.1) (90.0,68.1) (90.0,84.8) (86.0,84.8) (86.1,90.4) (64.9,90.3) (64.9,81.0) (78.6,81.0) (78.6,73.4) (65.1,73.4)

Colegio Mayor de San Bartolomé (OSM w28289653), 4061 m², 3 pisos
 ext: (69.2,-100.4) (69.3,-168.1) (171.9,-167.4) (171.8,-140.9) (139.3,-141.2) (102.0,-141.4) (102.0,-100.2)
Iglesia de San Ignacio (OSM w24457192), bbox u 101.9→139.3, v -141.4→-63.7 (fachada sobre la Calle 10)
```

---

## Mayores incertidumbres

1. **Alturas de casi todos los edificios.** Solo hay datos publicados para las torres de la Catedral (52 m, o 42 m según otras fuentes), la fachada del Sagrario (22 m), la figura de Bolívar (2,6 m) y, de forma indirecta, el Liévano (≈ 16 m). Las alturas del Capitolio (≈ 20 m), Justicia (≈ 20–24 m), Palacio Arzobispal, San Bartolomé, la nave de la Catedral y el pedestal de la estatua son **estimadas**.
2. **Ancho de la fachada del Palacio de Justicia:** 83 m (OSM) frente a un lote de 99,6 m (SISBIC).
3. **Desnivel real de la plaza:** consta que es una plataforma nivelada en 1960 con muros sobre la Cra 8 y gradas en el atrio de la Catedral, pero no hay cotas publicadas. La pendiente natural (~4–4,5 %, ~5 m en 116 m) sale de un DSM de 30 m.
4. **Columnata del Capitolio:** número y disposición de columnas ("seis filas de tres"), altura (14 m según un blog) y ancho del cuerpo central.
5. **Reparto del frente oriental entre Catedral, Sagrario y Palacio Arzobispal** (OSM agrupa Catedral y Sagrario; el Palacio Arzobispal aparece retranqueado tras un jardín), y orientación actual de la estatua.
6. **Mobiliario urbano** (faroles, bolardos, astas) y despiece del pavimento: sin datos verificables. Hay que relevarlo con fotos o Street View.
7. Los valores web se tomaron de extractos del buscador sin abrir las páginas, porque el contenedor no tiene acceso. Hay que verificar contra la fuente original antes de un uso formal.
