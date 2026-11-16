# Capturas finales de ARES-X (ARX-49)

Regeneración: con el servidor en marcha (`python -m uvicorn api.servidor:app --port 8765`), desde ares_x/ ejecuta
`python docs/capturas/capturas_finales.py`. Salen en `docs/capturas/finales/`. Tarda unos minutos (la vista del AG espera la corrida).

| Archivo | Vista | Qué muestra |
|---|---|---|
| 01_asistente_marte.png | Asistente (menú de inicio) | Planeta y mapa, modo de IA con veto, escenario e «Iniciar misión» |
| 02_partida_marte_1366.png | Partida en Marte, 1366×768 | HUD con estado, escena con relieve y horizonte, rover y ruta punteada |
| 03_partida_marte_1920.png | Partida en Marte, 1920×1080 | Misma vista en pantalla grande |
| 04_decision_ia_rna.png | Decisión de la IA en modo RNA | Columna con las cuatro técnicas resumidas y el panel de controles |
| 05_laboratorio_genetico.png | Laboratorio · genético | Curva de fitness, población de la generación y desglose de los candidatos (CA-04) |
| 06_laboratorio_difuso_barrido.png | Laboratorio · difuso | Pertenencia, salida de velocidad y barrido de 10 a 1 m (CA-05) |
| 07_laboratorio_rna.png | Laboratorio · RNA | Rasgos editables, probabilidades y matriz de confusión con recall (CA-06) |
| 08_comparacion_politicas.png | Laboratorio · políticas | Híbrido frente a ablaciones con media ± desviación, y tabla (contrato §7) |
| 09_jupiter_sonda.png | Júpiter en modo sonda | Mar de nubes en bandas, vórtices y la sonda con su sombra (ev3-d39) |
| 10_mercurio.png | Mercurio | Suelo gris con cráteres, rocas grises y cielo oscuro |
| 11_automatico_continuo.png | Automático continuo | Bloque de misiones, éxitos, fracasos y medianas; señal biológica con su cautela |
| 12_estados_demo.png | Indicador de estado (demo) | Estado del rover en el HUD (ÉXITO y el resto con ?demo=estados) |
| 13_modo_cine.png | Modo cine (tecla H) | La escena sin paneles |
| 14_movil.png | Móvil, 375×812 | Columnas apiladas sin solapes |
| 15_tablet.png | Tablet, 768×1024 | Diseño intermedio |

Notas: los datos de móviles, escenarios y planetas son de prueba (adaptador.js, USAR_MOTOR = false) hasta que el motor publique
/moviles, /escenarios y /planetas. El rendimiento de estas capturas es de render por software; la medición con GPU real es
abrir la app con `?fps=1`.
