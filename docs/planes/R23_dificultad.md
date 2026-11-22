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
