# ARX-79 · Calibración de la garantía en el mapa grande

Plan: `docs/planes/ARX-79_garantia_grande.md` (worktree de interfaz). Rama `feat/arx-79-garantia`, base `22dc129` (con ARX-90, ARX-91 y ARX-28c integrados).

## 79a · Medición base (garantía actual, `garantia=True`)

Estado: **pendiente de medición (79a, con turno)**.

Condiciones: sin eventos, modo automático por la API (`TestClient`, sin servidores), semillas 1 a 20 por nivel, tope de 500 pasos, código de la rama sin cambios en `juego/partida.py`. Las mismas 20 semillas en ambos tamaños.

Columnas: **Éxito** = victorias/20; **Pasos** = media y mediana solo de las victorias; **Causa de la derrota** = una de: batería 0 con sitios pendientes · batería insuficiente para los sitios restantes · sitios 0/n (sin ruta real a sitios) · caza sin batería · caza sin ruta · caza parada (sin terminar en el tope) · SIN_RUTA · otra (con el aviso). Se anotan las semillas perdidas.

### Mapa grande (40×60)

| Nivel | Éxito | Pasos (media) | Pasos (mediana) | Causa de la derrota (semillas) |
|---|---|---|---|---|
| 1 Muy fácil | pendiente | pendiente | pendiente | pendiente |
| 2 Fácil | pendiente | pendiente | pendiente | pendiente |
| 3 Medio | pendiente | pendiente | pendiente | pendiente |
| 4 Difícil | pendiente | pendiente | pendiente | pendiente |
| 5 Hardcore | pendiente | pendiente | pendiente | pendiente |

### Mapa pequeño (20×30), control

| Nivel | Éxito | Pasos (media) | Pasos (mediana) | Causa de la derrota (semillas) |
|---|---|---|---|---|
| 1 Muy fácil | pendiente | pendiente | pendiente | pendiente |
| 2 Fácil | pendiente | pendiente | pendiente | pendiente |
| 3 Medio | pendiente | pendiente | pendiente | pendiente |
| 4 Difícil | pendiente | pendiente | pendiente | pendiente |
| 5 Hardcore | pendiente | pendiente | pendiente | pendiente |

Referencias previas (no son esta medición): QA 17/11 en `ab46b4a`: Muy fácil grande pierde las semillas 8, 9 y 12; Medio grande las 1 a 4. ARX-58: Muy fácil grande 80 % con mediana 77 pasos.

## 79d · Medición final

Pendiente (tras 79b y 79c). Criterio: Muy fácil y Fácil grande ≥ 95 %; Medio ≥ 85 %; pequeño sin empeorar.
