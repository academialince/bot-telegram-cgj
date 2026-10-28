#!/usr/bin/env python3
"""Publica UNA pregunta tipo quiz en Telegram y avanza la rotación de temas.

GitHub Actions lo ejecuta dos veces al día (ver .github/workflows/publicar.yml).

Uso:
  python publicar.py              publica la siguiente pregunta (necesita TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID)
  python publicar.py --prueba     muestra lo que publicaría, sin enviar nada ni tocar estado.json
"""
import html, json, os, random, sys, urllib.request, urllib.error
from datetime import datetime, timezone
import formato as F

BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG = os.path.join(BASE, "config.json")
RUTA_ESTADO = os.path.join(BASE, "estado.json")
LETRAS = "ABCD"


def cargar_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defecto


def guardar_estado(estado):
    with open(RUTA_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
        f.write("\n")


def telegram(metodo, datos):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{metodo}",
        data=json.dumps(datos).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Telegram rechazó {metodo}: {e.read().decode('utf-8', 'replace')}")
    if not resp.get("ok"):
        raise SystemExit(f"Telegram rechazó {metodo}: {resp}")
    return resp["result"]


def elegir(config, estado):
    """Siguiente tema de la rotación con preguntas disponibles y una pregunta aún no publicada de ese tema."""
    rot = config["rotacion"]
    for salto in range(len(rot)):
        i = (estado.get("indice", 0) + salto) % len(rot)
        tema = rot[i]
        ruta = os.path.join(BASE, tema["archivo"])
        if not os.path.exists(ruta):
            continue  # aún no se ha subido ese CSV: se salta
        preguntas = [F.ajustar_pregunta(p) for p in F.leer_csv(ruta)]
        if not preguntas:
            continue
        usadas = set(estado.setdefault("usadas", {}).get(tema["archivo"], []))
        libres = [q for q in preguntas if F.id_pregunta(q) not in usadas]
        if not libres:  # tema agotado: vuelve a empezar
            estado["usadas"][tema["archivo"]] = []
            libres = preguntas
        return i, tema, random.choice(libres)
    raise SystemExit("No hay ningún CSV con preguntas en la carpeta data/.")


def publicar(chat_id, tema, q, anonima, prueba=False):
    cabecera = f"{tema['emoji']} {tema['nombre']}"
    opciones = [q[f"opcion_{l.lower()}"] for l in LETRAS]
    correcta = LETRAS.index(q["respuesta_correcta"])
    encuesta = {"chat_id": chat_id, "type": "quiz", "is_anonymous": anonima,
                "correct_option_id": correcta, "explanation": q["explicacion"]}
    mensajes = []
    if F.cabe_como_quiz(q):
        pregunta = f"{cabecera}\n\n{q['enunciado']}"
        encuesta["question"] = pregunta if F.tlen(pregunta) <= F.MAX_PREGUNTA else q["enunciado"]
        encuesta["options"] = [{"text": o} for o in opciones]
    else:
        # Modo letras: el texto completo va en un mensaje y la encuesta solo lleva A, B, C, D.
        texto = (f"<b>{html.escape(cabecera)}</b>\n\n{html.escape(q['enunciado'])}\n\n"
                 + "\n".join(f"<b>{l})</b> {html.escape(o)}" for l, o in zip(LETRAS, opciones)))
        mensajes.append({"chat_id": chat_id, "text": texto, "parse_mode": "HTML"})
        encuesta["question"] = "👆 ¿Cuál es la respuesta correcta?"
        encuesta["options"] = [{"text": l} for l in LETRAS]
    if not encuesta["explanation"]:
        del encuesta["explanation"]
    if prueba:
        for m in mensajes:
            print("MENSAJE:\n" + m["text"] + "\n")
        print("ENCUESTA:", json.dumps({k: v for k, v in encuesta.items() if k != "chat_id"}, ensure_ascii=False, indent=1))
        return
    for m in mensajes:
        telegram("sendMessage", m)
    telegram("sendPoll", encuesta)


def main():
    prueba = "--prueba" in sys.argv
    config = cargar_json(RUTA_CONFIG, None)
    estado = cargar_json(RUTA_ESTADO, {"indice": 0, "usadas": {}, "historial": []})
    i, tema, q = elegir(config, estado)
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not prueba and not chat_id:
        raise SystemExit("Falta la variable TELEGRAM_CHAT_ID.")
    publicar(chat_id, tema, q, config.get("encuesta_anonima", True), prueba)
    if prueba:
        return
    pid = F.id_pregunta(q)
    estado["usadas"].setdefault(tema["archivo"], []).append(pid)
    estado["indice"] = (i + 1) % len(config["rotacion"])
    estado.setdefault("historial", []).append(
        {"fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "tema": tema["nombre"], "id": pid})
    estado["historial"] = estado["historial"][-60:]
    guardar_estado(estado)
    print(f"Publicada: {tema['nombre']} · {q['enunciado'][:80]}")


if __name__ == "__main__":
    main()
