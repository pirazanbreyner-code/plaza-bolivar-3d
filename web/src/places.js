// Lugares del recorrido. Coordenadas del modelo de Blender (metros): u hacia el oriente de la
// reticula (girada 31° respecto al norte), v hacia el norte de la reticula, z sobre la plaza.
// view: desde donde se mira (loc, a la altura de los ojos) y hacia donde (target).
// near: [u, v, radio] para mostrar la ficha al acercarse caminando.
// Fuentes y grado de confianza de cada medida: references/research_raw.md y APROXIMACIONES.md.
export const PLACES = [
  {
    name: 'Plaza de Bolívar',
    kind: 'Plaza',
    text: 'Plaza Mayor de Santafé desde la fundación de la ciudad y Plaza de Bolívar desde 1846, cuando se instaló la estatua del Libertador. Alrededor están los tres poderes: el Congreso (Capitolio), las altas cortes (Palacio de Justicia) y la Alcaldía (Edificio Liévano), además de la Catedral.',
    facts: [['Altitud', '≈ 2.614 m s. n. m.'], ['Losas', '≈ 79 × 100 m'], ['Retícula', 'girada 31° respecto al norte']],
    view: { loc: [-30, -36, 1.62], target: [18.5, 51.5, 14] },
    near: [0, 0, 9],
  },
  {
    name: 'Catedral Primada',
    kind: 'Templo neoclásico',
    text: 'Proyecto de fray Domingo de Petrés, levantada entre 1807 y 1823 sobre el sitio de los templos anteriores. Tiene cinco naves en cruz latina y allí reposan los restos de Gonzalo Jiménez de Quesada, fundador de la ciudad.',
    facts: [['Consagración', '1823'], ['Fachada', '≈ 41 m (en el modelo)'], ['Torres', '42–52 m según la fuente']],
    view: { loc: [22, 22, 1.62], target: [61, 31, 22] },
    near: [50, 30, 14],
  },
  {
    name: 'Capilla del Sagrario',
    kind: 'Barroco colonial',
    text: 'Construida entre 1660 y 1700, junto a la Catedral. Fachada de piedra oscura con portada barroca y dos espadañas; la cúpula roja con nervios blancos se ve desde la plaza.',
    facts: [['Construcción', '1660–1700'], ['Fachada', '≈ 11 × 22 m'], ['Cúpula', '≈ 30 m de altura']],
    view: { loc: [36, -9, 1.62], target: [61, -9, 14] },
    near: [52, -9, 9],
  },
  {
    name: 'Palacio Arzobispal',
    kind: 'Sede arquidiocesana',
    text: 'Edificio de cuatro pisos con enchape de piedra, construido entre 1952 y 1957 después de los incendios del 9 de abril de 1948.',
    facts: [['Construcción', '1952–1957'], ['Pisos', '4'], ['Esquina', 'Cra 7 con Calle 10']],
    view: { loc: [38, -30, 1.62], target: [61.3, -30, 9] },
    near: [52, -32, 10],
  },
  {
    name: 'Palacio de Justicia',
    kind: 'Altas cortes',
    text: 'Obra de Roberto Londoño, terminada en 1999 y ocupada desde 2004; reemplazó al edificio destruido en la toma y retoma de noviembre de 1985. En su fachada se lee la frase de Santander: «Colombianos, las armas os han dado la independencia, las leyes os darán la libertad».',
    facts: [['Terminado', '1999'], ['Fachada', '≈ 83 m de frente'], ['Altura', '≈ 24 m (estimada)']],
    view: { loc: [2, 30, 1.62], target: [2, 67, 14] },
    near: [2, 55, 12],
  },
  {
    name: 'Casa del Florero',
    kind: 'Museo de la Independencia',
    text: 'Casa colonial de la esquina nororiental. El 20 de julio de 1810 el incidente del florero de José González Llorente desató el grito de independencia de Santafé.',
    facts: [['Fecha clave', '20 de julio de 1810'], ['Pisos', '2'], ['Esquina', 'Cra 7 con Calle 11']],
    view: { loc: [52, 44, 1.62], target: [76, 62, 5] },
    near: [68, 54, 9],
  },
  {
    name: 'Edificio Liévano',
    kind: 'Alcaldía Mayor de Bogotá',
    text: 'Proyecto del arquitecto francés Gaston Lelarge, construido entre 1902 y 1910 sobre el sitio de las Galerías Arrubla, que se incendiaron en 1900. Fachada de estilo francés con 32 ejes de ventanas por piso.',
    facts: [['Construcción', '1902–1910'], ['Altura', '≈ 16 m'], ['Frente', '≈ 108 m']],
    view: { loc: [-25, 2, 1.62], target: [-56, 2, 8] },
    near: [-44, 1, 10],
  },
  {
    name: 'Capitolio Nacional',
    kind: 'Congreso de la República',
    text: 'Obra iniciada en 1848 con el proyecto de Thomas Reed y terminada en 1926 tras la intervención de Cantini, Lelarge, Santamaría y otros. Su pórtico de columnas jónicas, en piedra de cantera, deja ver el patio Mosquera.',
    facts: [['Construcción', '1848–1926'], ['Fachada', '≈ 88,6 m'], ['Altura', '≈ 20 m (estimada)']],
    view: { loc: [4, -30, 1.62], target: [3.5, -67.4, 10] },
    near: [4, -52, 12],
  },
  {
    name: 'Estatua de Simón Bolívar',
    kind: 'Monumento en bronce',
    text: 'Obra del escultor italiano Pietro Tenerani, fundida en Múnich e inaugurada el 20 de julio de 1846. Es la primera estatua pública de Bogotá.',
    facts: [['Inauguración', '1846'], ['Figura', '≈ 2,6 m'], ['Autor', 'Pietro Tenerani']],
    view: { loc: [6.4, -2, 1.62], target: [6.4, -15.25, 4.2] },
    near: [6.4, -15.25, 7],
  },
  {
    name: 'Vista a Monserrate',
    kind: 'Cerros Orientales',
    text: 'El santuario de Monserrate (3.152 m) queda a unos 2,3 km al oriente de la plaza, unos 540 m más alto. Al sur está el cerro de Guadalupe, con su virgen en la cumbre. El relieve sale de un modelo de elevación real.',
    facts: [['Monserrate', '3.152 m'], ['Guadalupe', '≈ 3.300 m'], ['Desnivel', '≈ 540 m']],
    view: { loc: [-30, -36, 1.62], target: [1559, 2007, 640] },
  },
  {
    name: 'Vista aérea',
    kind: 'Modo vuelo',
    text: 'Vista desde unos 90 m de altura. En el modo vuelo puedes subir con E o Espacio y bajar con Q o C. Pulsa F para volver a caminar.',
    facts: [['Vuelo', 'F para alternar'], ['Subir / bajar', 'E / Q'], ['Rápido', 'Mayús']],
    view: { loc: [-150, -120, 90], target: [20, 10, 0], fly: true },
  },
];
