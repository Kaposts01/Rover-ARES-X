# R23: dificultad real, mecánicas por planeta y correcciones del motor

Ronda de correcciones pedida por el evaluador (22/11/2026). Todo vale solo para la partida jugable (`garantia=True`); el
escenario `congelado` y las evaluaciones no cambian.

## Qué cambió

- `juego/dificultad.py`: batería inicial por nivel, intensidad de las mecánicas y compensación por planeta.
- `juego/planetas.py`: perfil por planeta (gravedad, viento con ráfagas, hielo, pendiente, arrastre, polvo) y su efecto en el motor.
- `juego/termico.py`: modelo térmico frío (Marte y gigantes). Antes la temperatura interna de Neptuno quedaba fija en 20 °C.
- `Partida`: recarga solo si hace falta (y parcial), batería del difuso en %, resbalón por pendiente encendido, garantía redefinida.
- `juego/conduccion.py`: los modos Solo RNA, Solo difuso y Solo AG guardan `mision.ultima_ia` (el panel de IA y `/ia/paso`).

## Garantía (redefinida)

Antes: «con la batería inicial hay una ruta completa sin recargar»; en la práctica la gente la leía como «se gana siempre».
Ahora: «existe una ruta ganadora» con las bases de recarga que habrá y la mitad del sobrecoste medio del planeta. No promete
ganar: viento, hielo, eventos y la conducción de la IA pueden hacerla fallar. Interruptor: `dificultad.GARANTIA_CON_BASES_Y_PLANETA`.

## Cómo reproducir las cifras

```
python scripts/medir_dificultad.py --tamano pequeno --planetas Marte,Tierra --semillas 20 --politica hibrido
python scripts/medir_dificultad.py --tamano pequeno --planetas Marte --semillas 20 --niveles 3,4,5 --politica sin_ag
```
Políticas: `hibrido`, `sin_rna`, `sin_difuso`, `sin_ag`. Mapa pequeño, semillas 1 a 20, modo automático por la API en proceso.

## Valores (supuestos de simulación)

Batería del nivel 1 a 5 (pequeño): 100, 94, 88, 80, 70, más la compensación del planeta. Intensidad de las mecánicas:
0,4; 0,6; 0,75; 0,9; 1,1. Calibrados en Marte; el resto de planetas se compensa con
`(sobrecoste_planeta − sobrecoste_Marte) · intensidad · 70` unidades de batería.

## Resultados (híbrido, modo automático, 20 semillas, mapa pequeño)

Antes (main): Marte y Tierra idénticos, 100 % en los cinco niveles, batería sobrante de las ganadas 54, 48, 38, 31 y 37 %.

| Planeta | N1 | N2 | N3 | N4 | N5 |
|---|---|---|---|---|---|
| Marte | 100 % | 100 % | 90 % | 70 % | 40 % |
| Tierra | 100 % | 100 % | 100 % | 80 % | 65 % |

Batería sobrante de las ganadas: 45 a 47 % (N1), 37 % (N2), 22 a 26 % (N3), 19 a 22 % (N4), 15 a 27 % (N5).
Mapa grande (8 semillas, Marte): N3 88 %, N4 62 %, N5 50 %.

Ablaciones en Marte (N3, N4, N5): híbrido 90, 70, 40 (esta pasada) frente a sin AG 75, 70, 55; sin difuso 90, 70, 50; sin RNA 90, 80, 65
(pasada previa con el mismo código salvo el generador de polvo). Con 20 semillas el error es de ±10 puntos: el AG y el difuso aportan algo
pequeño y la RNA no se distingue de cero.


## Recalibración tras el AG con restricciones (22/11, segunda parte de R23)

Con 8 a 12 sitios, ventanas, recarga obligatoria, opcionales, difuso evolucionado y RNA con anticipación (ver `R23_ag.md`) la partida jugable es otra:
las cifras de arriba (3 a 4 sitios) ya no valen. No se tocó la batería por nivel (`dificultad.BATERIA_POR_NIVEL`): el problema nuevo, con 3 a 4 bases, ya
deja a Marte dentro de las metas. Híbrido, modo automático por la API (con drones desde Medio), mapa pequeño, semillas 1 a 20, difuso evolucionado de Marte:

| Nivel | Sitios | Meta | Marte | Tierra (difuso de defecto) |
|---|---|---|---|---|
| 1 Muy fácil | 8 | ≥ 95 % | 100 % (20/20) | 100 % |
| 2 Fácil | 8 | ≥ 95 % | 100 % (20/20) | 95 % |
| 3 Medio | 9 | 85–95 % | 85 % (17/20) | 100 % |
| 4 Difícil | 10 | 65–85 % | 85 % (17/20) | 90 % |
| 5 Hardcore | 11 | 40–65 % | 65 % (13/20) | 80 % |

Batería sobrante de las ganadas en Marte: 56, 58, 53, 52 y 61 %. Pasos de las ganadas: 90, 93, 146, 147, 171 (antes, con 3 a 4 sitios, 45 a 55). Con 20 semillas
el error es de ±10 a ±15 puntos: Marte está en la banda en los cinco niveles (N3, N4 y N5 en su borde superior); **Tierra queda por encima de la meta en N3 a N5** (la
compensación por planeta de la primera parte la hace más fácil con el problema nuevo; no se recalibró). Derrotas: casi todas por batería agotada (tormentas, viento o
un plan que se queda corto), una por drones sin batería para cazarlos, y 1 a 2 partidas de cada 100 que no terminan en 500 pasos (un bucle de espera cerca del refugio que
no se resolvió).

Con el difuso de defecto (sin evolucionar) la misma medición en Marte dio 100, 100, 90, 80 y 60 % (antes de los últimos retoques de robustez, 100, 100, 90, 80, 60).

Cómo reproducir: `python scripts/medir_dificultad.py --tamano pequeno --planetas Marte,Tierra --semillas 20 --politica hibrido`.
