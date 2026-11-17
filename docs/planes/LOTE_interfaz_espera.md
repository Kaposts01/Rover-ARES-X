# Rama feat/lote-interfaz: en espera de la rama de API

Estado: la rama de interfaz no se integra en `main` todavía.

- `3da523a` ARX-28e: el selector de escenario necesita `/comparacion?escenario=` (ARX-28d, en `servidor.py`).
- `43dc600` ARX-47c: los deslizadores de pesos necesitan que `/ag` acepte `w_*` (ARX-47a, en `servidor.py`).

Hasta que exista la rama de API (28d y 47a), que va detrás de la rama del motor por `servidor.py`, esta rama espera y no pasa a GitOps.
