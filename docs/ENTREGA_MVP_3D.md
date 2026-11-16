# ARES-X · Entrega del MVP 3D (cierre ARX-09, con ARX-11 a ARX-13)

Documento de cierre del MVP 3D: qué se entrega, cómo se ejecuta, qué criterio de aceptación cubre cada parte y qué limitaciones quedan. Las limitaciones completas están en `INFORME_TECNICO.md` §6; aquí solo se resumen.

## 1. Qué se entrega

| Componente | Ubicación | Estado |
|---|---|---|
| Motor de simulación (mapa, rover, sensores, física) | `simulador.py` (congelado, ev3-d08) | Entregado |
| RNA (MLP 32-16, scikit-learn) | `rna.py` | Entregado; macro-F1 0,928 en prueba |
| Lógica difusa (Mamdani, centroide) | `difuso.py` | Entregado; 9 reglas documentadas |
| Algoritmo genético (K puntos de paso) | `genetico.py` | Entregado; 100 % de éxito en 20 semillas |
| Integración y supervisor (códigos de motivo) | `integracion.py` | Entregado; gancho de intervención (ARX-10) |
| Experimentos y prueba causal | `intervencion.py` | Entregado |
| API REST (FastAPI) | `api/servidor.py` | Entregado: `/`, `/mapa`, `/estado`, `/partida`, `/mover`, `/paso`, `/modo`, `/disparo`, `/evento`, `/paneles`, `/explicacion`, `/intervencion` |
| Escena 3D en navegador (Three.js r160 local) | `api/static/` | Entregado |
| Combate: disparo, munición, drones | `juego/combate.py` | Entregado |
| Modos que conducen solos (rna, difuso, ag) con interruptor de veto | `juego/conduccion.py` | Entregado (ARX-11); tabla de 20 semillas en `docs/TABLA_MODOS.md` |
| Juego de escritorio (pygame) | `juego/` | Entregado como versión alternativa |
| Notebook de registro del pipeline | `ARES_X_ejecutado.ipynb` | 24 celdas sin errores; no se ejecuta en Colab (ver §4) |
| Informe técnico | `INFORME_TECNICO.md` | Borrador; §7 y §8 para revisión del estudiante |
| README e instalación local | `README.md` | Entregado |
| Guion del video (sobre el MVP 3D) | `juego/GUION_VIDEO.md` | Rehecho (ARX-13, ev3-d34 A); lo graba el estudiante |

## 2. Cómo se ejecuta

Desde la carpeta `ares_x/`, con las dependencias de `requirements.txt` instaladas (sin Colab, sin GPU y sin claves):

```bash
# API y escena 3D en el navegador
uvicorn api.servidor:app --reload
# luego abrir http://127.0.0.1:8765

# Juego de escritorio (pygame)
python -m juego

# Ejecución headless reproducible con exportación
python -m juego --headless --semilla 11 --pasos 300 --salida <carpeta>

# Suite de pruebas completa (289 pruebas al cierre de ARX-13; unos 5 min en CPU)
python -m pytest -q
```

## 3. Criterios de aceptación del MVP 3D (`docs/SPEC_MVP_3D.md`, sección 7)

| # | Criterio | Cubierto por |
|---|---|---|
| 1 | `POST /partida` con semilla 11 deja al rover en el inicio con batería 100 | `api/tests/test_api.py::test_estado_inicial_en_el_inicio_con_bateria_completa` |
| 2 | Modo `automatico` con semilla 11 llega a `EXITO` sin colisiones ni barrancos | `test_criterio_2_automatico_llega_a_exito_sin_colisiones` |
| 3 | Diagonal bloqueada devuelve `movido: false` con motivo legible | `test_criterio_3_diagonal_bloqueada_devuelve_motivo` |
| 4 | El cooldown de disparo impide dos disparos sin turno intermedio (409) | `test_disparo_respeta_cooldown_y_municion`; `juego/tests/test_combate.py::test_dos_disparos_seguidos_sin_turno_solo_produce_uno` |
| 5 | Dron pasa de patrulla a persecución a 6 celdas y a ataque a 1 celda | `juego/tests/test_combate.py::test_patrulla_pasa_a_alerta_a_seis_celdas`, `test_persecucion_se_acerca_y_pasa_a_ataque_a_una_celda` |
| 6 | `GET /paneles` devuelve entradas y salidas de cada técnica | `test_paneles_devuelven_entradas_y_salidas` |
| 8 | Todas las rutas tienen pruebas y ninguna devuelve traceback | `test_ningun_error_expone_traceback`; pruebas de cada ruta en `test_api.py` |
| 9 | Con la intervención activa, la decisión cambia | `test_intervencion_rna_se_aplica_a_la_mision`; prueba causal en `intervencion.py` (INFORME §4.1) |

Verificaciones de navegador con Playwright (consola limpia y capturas en `docs/capturas/`): `api/verificar_frontend.py`, `verificar_automatico.py`, `verificar_combate.py` y `verificar_modos.py`, y `verificar_menu.py` para el menú y el historial.

Tabla de 20 semillas por modo: `python scripts/tabla_modos.py` (genera `docs/TABLA_MODOS.md`).

## 4. Diferencias respecto de la pauta original

- **Google Colab (RF-16 y §15 de la pauta):** no se usa. Por decisión registrada en la Bandeja (ev3-d30) el proyecto corre en local. Las decisiones originales para Colab (ev3-d03 y ev3-d04) quedaron reemplazadas. El notebook se conserva como registro del pipeline completo.
- **Alcance planetario (§3):** la simulación se centra en Marte. Los perfiles de los otros cuerpos existen en `simulador.py` como supuestos, pero no se validó en la interfaz el bloqueo de Júpiter con ruedas (CA-07).
- **Video (§15):** lo graba el estudiante con el guion de `juego/GUION_VIDEO.md`, ya rehecho sobre el MVP 3D (ev3-d34 A).
- **Aportes individuales y declaración de uso de IA (§15 y §17):** quedan como borrador en `INFORME_TECNICO.md` §7 y §8, para revisión del estudiante.

## 5. Limitaciones

Lista completa en `INFORME_TECNICO.md` §6. Resumen:

- El supervisor congelado no conoce a los drones; la capa de combate vive en la API (`_decidir_combate_automatico`).
- Los modos `rna`, `difuso` y `ag` conducen solos con el veto encendido o apagado (ARX-11). No reaccionan a los drones más allá del daño de batería; la decisión de combate solo la usan `automatico` y `generativo`.
- Qwen2.5-0.5B se probó y se descartó por decisión del estudiante (ev3-d37): no forma parte del entregable.
- Los drones evitan solo la celda exacta; no hay predicción de su movimiento.
- Puede aparecer `SIN_RUTA` por falsos positivos del sensor.
- Los valores de energía, daño y alcance son supuestos de simulación, no especificaciones reales.

## 6. Registro de cambios de cierre (ARX-09)

- Revisión estática (pyflakes) de los módulos del MVP 3D. Hallazgos corregidos: 5 imports sin uso (`api/servidor.py`, `juego/partida.py`, `juego/ui.py`, `juego/visual.py`) y 1 en `api/tests/test_api.py`.
- Error corregido: el impacto de un disparo no llegaba en `eventos_combate` porque `tick()` vaciaba la lista antes de responder. Se reinyectan los eventos del disparo en `_turno` y se agregó la prueba `test_impacto_del_disparo_llega_en_la_respuesta`.
- Notas de INFORME_TECNICO §2 (líneas 27 y 28) y §7 (línea 111) actualizadas: las decisiones de Colab quedaron reemplazadas por ev3-d30.

### ARX-11 · modos que conducen solos

- `juego/conduccion.py`: rna elige el vecino de mayor p_libre que acerca al objetivo; difuso avanza por BFS con su velocidad y espera o rodea si es baja; ag sigue su ruta y replanifica solo si queda bloqueada.
- Interruptor de veto de seguridad (encendido por defecto): `POST /modo` acepta `veto`; la interfaz tiene la casilla.
- Corregido durante la implementación: el indicador de borde de barranco no era específico de la celda de enfrente (el veto se disparaba en celdas libres); ahora se usa el LIDAR por celda. Y lo que el veto ve como peligroso pasa a riesgo, para que el replanteo lo rodee.
- Tabla de 20 semillas en `docs/TABLA_MODOS.md` (capa de juego). Arnés distinto del notebook: las cifras no se mezclan.
- Pruebas: `juego/tests/test_conduccion.py`; API del veto y de `/paso` por modo.

### ARX-12 · Qwen (cancelado)

Cancelado por decisión del estudiante (ev3-d37). Qwen y el modo generativo se retiran del entregable.

### ARX-13 · guion del video (ev3-d34 A)

- `juego/GUION_VIDEO.md` rehecho sobre el MVP 3D: escenas por modo, veto, intervención en vivo, combate. Checklist sin teclas de pygame.
- Cifras: las del notebook (experimento y prueba causal) y las de `docs/TABLA_MODOS.md`, cada una citada con su arnés.

### Cierre de ARX-09 (con ARX-11 a ARX-13)

- Suite completa: **289 pruebas en verde**, código de salida 0.
- Pyflakes sobre los módulos tocados: sin hallazgos.
