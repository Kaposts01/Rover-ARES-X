# Auditoría del 22/11: nuestro ARES-X frente al ARES-X de ejemplo

Comparación de este repositorio con la implementación de referencia en Jupyter (carpeta `Downloads\ARES-X_proyecto_2026-11-10\ares-x`).

Método:
- Se leyó el código de ambos proyectos.
- Se midió en el navegador qué devuelve cada fuente del panel paso a paso (semilla 77, nivel 4, Marte, 12 pasos).

## 1. Por qué los gráficos del panel no cambiaban (corregido)

El panel derecho no mostraba la decisión del paso. Volvía a calcular un laboratorio:

| Pestaña | Qué mostraba | Qué usó de verdad el motor |
|---|---|---|
| Difuso | `GET /difuso`: inclinación 0 y temperatura 0 fijas, distancia topada en 20. Mostró «velocidad 0,85» en los 12 pasos | velocidades de 0,50 a 0,85 (reglas R4/R6) e inclinación de 0,2° a 14,4° |
| RNA | `GET /rna`: volvía a leer los sensores desde la celda nueva y decidía con velocidad 0,5 | en el paso 11 el panel dijo «barranco 100 %» y el motor decidió con «libre 100 %» |
| Genético | `GET /ag`: volvía a correr el AG del laboratorio desde la posición actual con los pesos del laboratorio, solo cada 8 pasos o al cambiar la firma | otro AG, el del plan en juego. El panel mostraba «ruta no viable» y AG-FALLBACK-GARANTIA de un AG que no era el que jugaba |

El ejemplo lo resuelve con «seguir la misión en vivo»: recarga los controles con la lectura real del paso (`vista3d_ui.js:429-446`, `app.py:330-339`).

**Corrección:**
- `Mision.paso_mision` guarda `ultima_ia`, solo como registro (sin azar ni efecto en las decisiones): rasgos de la RNA, probabilidades usadas, distancia, batería, inclinación y temperatura del difuso.
- `GET /ia/paso` recalcula activaciones, curvas y reglas con esas mismas entradas. Son deterministas, así que coinciden con la decisión; lo verifica `test_ia_del_paso_muestra_lo_que_la_ia_uso_en_ese_paso`.
- El AG que devuelve es el del plan en juego (`mision._optimizar_ag.ultimo`): historial por generación, ruta, orden y replanteos.
- El panel usa una sola petición por paso, muestra la cabecera «Paso N · celda → rumbo · acción» y un historial de los últimos 40 pasos en cada pestaña: p(barranco) y confianza, velocidad, y celdas que faltan, con marca en los replanteos.

## 2. Defectos encontrados en el motor

| # | Defecto | Estado |
|---|---|---|
| 1 | Panel de la RNA con datos re-muestreados y acción recalculada a velocidad 0,5 | corregido (`/ia/paso`) |
| 2 | Panel del difuso con inclinación y temperatura en 0 | corregido (`/ia/paso`) |
| 3 | El aviso de aborto térmico del laboratorio difuso usaba la tolerancia general, no la del planeta (`servidor.py`, `_difuso_datos`) | corregido |
| 4 | `/ag` recalculaba el AG del laboratorio y su caché nunca acertaba, porque la clave incluye la posición del rover | el panel ya no lo usa; el laboratorio lo sigue usando a propósito |
| 5 | Modo «Solo difuso» con el perfil v2: la inclinación salía del rasgo 2, que en v2 es el contraste óptico (`conduccion.py`) | corregido: usa `inclinacion_de_rasgos`, como el modo híbrido |
| 6 | `/paneles`: tras un paso las reglas llegan solo como id y sin pasos como tuplas, así que la columna izquierda pierde la fuerza de cada regla | pendiente |
| 7 | `_paneles` llama a `sugerencia()` en cada refresco, y eso incluye un AG de evaluación: cómputo de sobra | pendiente |
| 8 | `partida.py`: la rama `"meteorito" in EVENTOS_GRAVES` nunca se cumple (documentado así) | pendiente: decidir si se elimina |
| 9 | `app.js`: un comentario dice que `/serie` no trae `p_libre` ni `p_obstaculo`, y sí los trae | pendiente (menor) |
| 10 | `_sensores` devuelve las claves `borde` y `gradiente` también en v2, y el frontend lo compensa | pendiente (menor) |

## 3. Funciones del ejemplo que aquí faltan o son más pobres

Lo que tenemos igual: evolución del AG en 3D, hologramas, cine y postproceso, logros y mapa de incertidumbre. Lo que tenemos mejor: combate y drones (el ejemplo no tiene).

| Función | En el ejemplo | Aquí |
|---|---|---|
| Laboratorios que siguen la misión en vivo | sí | el panel ya sigue el paso; el laboratorio modal todavía no |
| Modos de cámara (seguir, persecución, primera persona, cenital) | 5 modos | órbita más director de cine |
| Eventos | 19 (géiser, erupción, desprendimiento, ráfaga, corrosión, restauración de sensores, forzar día…) | 9 |
| Dron compañero | sí | falta |
| Defensa oral guiada | sí | falta |
| Reporte HTML descargable y narrador de pasos | sí | solo `/historial.csv` |
| Sonido | sí | falta |
| Maqueta 3D en miniatura | sí | falta |
| Comparar políticas en vivo | sí | desde JSON precalculado |
| Reejecutar con la misma semilla (determinismo) | sí | falta |
| Telemetría con rangos físicos | sí | parcial |

Sugerencia de prioridad para la defensa del trabajo:

1. Que el laboratorio modal también siga la misión en vivo, reutilizando `/ia/paso`.
2. Reporte descargable de la misión.
3. Modos de cámara de seguimiento y primera persona.
4. El resto es decorativo.
