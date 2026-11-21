# ARX-94 · pruebas en rojo tras 94c, que se atribuyen en 94f

Medidas al cerrar 94c (punta db20374), fuera de la suite acotada. No se relajan ni se editan: cada una compara valores fijos por semilla o cifras publicadas que cambian con el rediseño (mundo v2 + sensores). La atribución (causa, antes y después, hash nuevo del congelado) se escribe en 94f, con la regeneración única de ev3-d84 A.

| Archivo | Prueba |
|---|---|
| `tests/test_eventos_simultaneos.py` | `test_triple_orden_de_vetos_y_avisos_fijado_semilla_3` |
| `tests/test_eventos_simultaneos.py` | `test_triple_orden_semilla_7_termina_sin_ruta_tras_el_veto` |
| `juego/tests/test_caza_parada_arx79c.py` | `test_caza_parada_termina_con_causa` |
| `juego/tests/test_comparacion_escenarios.py` | `test_regresion_congelado_filas_identicas` |
| `juego/tests/test_fisica_velocidad.py` | `test_resbalon_a_velocidad_alta` |
| `juego/tests/test_fisica_velocidad.py` | `test_resbalon_vuelve_a_la_celda_anterior_y_gasta_bateria` |
| `juego/tests/test_fisica_velocidad.py` | `test_congelado_no_cambia` |
| `juego/tests/test_percepcion_arx90.py` | `test_regresion_semilla_7_exigente_el_hibrido_gana` |
| `juego/tests/test_trazas_divergencia.py` | `test_traza_en_vivo_semilla_4_diverge_en_las_tres_tecnicas` |

Pendiente de verificar en 94f: si alguna ya fallaba con solo 94a y 94b (punta 2fc2daf) o si la causa es 94c. Regla: no se integra nada de ARX-94 con estas pruebas en rojo sin su atribución escrita, y 94c por sí solo no se sube.
