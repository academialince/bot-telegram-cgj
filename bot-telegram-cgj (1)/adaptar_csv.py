#!/usr/bin/env python3
"""Convierte un CSV de la web (enunciado;tipo;opcion_a;…;cursos_aplicables) al formato del bot y lo ajusta a Telegram.

Uso:  python adaptar_csv.py entrada.csv data/ortografia.csv

Quita las columnas que el bot no usa, abrevia lo que no cabe, acorta la explicación a 200 caracteres
y descarta las preguntas con varias respuestas correctas (los quiz de Telegram solo admiten una).
"""
import sys
import formato as F

if len(sys.argv) != 3:
    sys.exit(__doc__)
filas = F.leer_csv(sys.argv[1])
vistas, preguntas = set(), []
for r in filas:
    q = F.ajustar_pregunta(r)
    if F.id_pregunta(q) not in vistas:
        vistas.add(F.id_pregunta(q)); preguntas.append(q)
F.escribir_csv(sys.argv[2], preguntas)
letras = sum(not F.cabe_como_quiz(q) for q in preguntas)
print(f"{len(preguntas)} preguntas guardadas en {sys.argv[2]} "
      f"({len(preguntas) - letras} como quiz normal, {letras} en modo letras por su longitud).")
