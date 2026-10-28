"""Ajuste de preguntas a los límites de las encuestas tipo quiz de Telegram.

Límites (Bot API, sendPoll): pregunta 1-300 caracteres, opciones 1-100, explicación 0-200.
"""
import csv, re, hashlib

MAX_PREGUNTA, MAX_OPCION, MAX_EXPLICACION = 300, 100, 200
# Margen para la cabecera del tema (emoji + nombre): el enunciado se ajusta a 280.
MARGEN_CABECERA = 20
MAX_ENUNCIADO = MAX_PREGUNTA - MARGEN_CABECERA
COLUMNAS = ["enunciado", "opcion_a", "opcion_b", "opcion_c", "opcion_d", "respuesta_correcta", "explicacion"]

# Abreviaturas que solo se aplican si el texto no cabe, de la más larga a la más corta.
ABREVIATURAS = [
    (r"Convenio Europeo para la [Pp]rotección de los [Dd]erechos [Hh]umanos y de las [Ll]ibertades [Ff]undamentales", "CEDH"),
    (r"Pacto Internacional de Derechos Económicos, Sociales y Culturales", "PIDESC"),
    (r"Pacto Internacional de Derechos Civiles y Políticos", "PIDCP"),
    (r"Declaración Universal de (los )?Derechos Humanos", "DUDH"),
    (r"Ley del Procedimiento Administrativo Común de las Administraciones Públicas", "Ley 39/2015"),
    (r"Ley Orgánica 3/2007,? (de 22 de marzo, )?para la igualdad efectiva de mujeres y hombres", "LO 3/2007"),
    (r"Ley Orgánica 2/1986,? (de 13 de marzo, )?de Fuerzas y Cuerpos de Seguridad", "LO 2/1986"),
    (r"Código de Conducta( del personal de la Guardia Civil)? \(RD 176/2022\)", "RD 176/2022"),
    (r"Tribunal Europeo de Derechos Humanos", "TEDH"),
    (r"Cuerpo Nacional de Policía", "CNP"),
    (r"Juzgado de Violencia sobre la Mujer", "Juzgado de VSM"),
    (r"Audiencia Nacional", "AN"),
    (r"Fuerzas y Cuerpos de Seguridad del Estado", "FCSE"),
    (r"Fuerzas y Cuerpos de Seguridad", "FCS"),
    (r"Ley de Enjuiciamiento Criminal", "LECrim"),
    (r"Carta Social Europea( \((ratificada|revisada)\))?", "CSE"),
    (r"Constitución [Ee]spañola", "CE"),
    (r"Administraciones [Pp]úblicas", "AA. PP."),
    (r"Administración [Pp]ública", "Admón. pública"),
    (r"Comunidades Autónomas", "CC. AA."),
    (r"Comunidad Autónoma", "C. A."),
    (r"Tribunal Constitucional", "TC"),
    (r"Naciones Unidas", "NN. UU."),
    (r"Ley Orgánica", "LO"),
    (r"Real Decreto", "RD"),
    (r"Código Civil", "C. Civil"),
    (r"Código Penal", "C. Penal"),
    (r"Guardia Civil", "GC"),
    (r"\bartículos\b", "arts."),
    (r"\bartículo\b", "art."),
    (r"\bapartado\b", "apdo."),
]

def tlen(t):
    """Longitud tal como la cuenta Telegram (unidades UTF-16: un emoji suele contar 2)."""
    return len(t.encode("utf-16-le")) // 2

def limpiar(t):
    return re.sub(r"\s+", " ", (t or "").replace("\ufeff", "")).strip()

def abreviar(t, limite):
    """Aplica abreviaturas una a una hasta que el texto cabe (o se acaban)."""
    t = limpiar(t)
    for patron, corto in ABREVIATURAS:
        if tlen(t) <= limite:
            break
        t = re.sub(patron, corto, t)
    return t

def _recortar(t, limite):
    """Recorta en el último límite natural (';', ':', ',', espacio) fuera de paréntesis y añade «…»."""
    if tlen(t) <= limite:
        return t
    limite -= tlen(t) - len(t)  # margen si hay emojis
    trozo = t[: limite - 1]
    for sep in ("; ", ": ", ", ", " "):
        k = len(trozo)
        while True:
            k = trozo.rfind(sep, 0, k)
            if k <= limite * 0.45:
                break
            if trozo[:k].count("(") <= trozo[:k].count(")") and not re.search(r"\b(art|arts|apdo|n\.º)\.?$", trozo[:k]):
                return _sin_cola(trozo[:k]) + "…"
    return _sin_cola(trozo) + "…"

_VACIAS = {"de", "del", "la", "las", "el", "los", "lo", "y", "e", "o", "u", "a", "al", "en", "que", "con", "por",
           "para", "un", "una", "unos", "unas", "su", "sus", "se", "sin", "como", "cuando", "si", "ni"}

def _sin_cola(t):
    """Quita palabras vacías y signos colgando al final de un recorte."""
    t = t.rstrip(" ,;:")
    while True:
        partes = t.rsplit(" ", 1)
        if len(partes) == 2 and partes[1].lower() in _VACIAS:
            t = partes[0].rstrip(" ,;:")
        else:
            return t

def ajustar_explicacion(t, limite=MAX_EXPLICACION):
    t = limpiar(t)
    etiqueta = ""
    # Pregunta oficial: «… Pregunta oficial del examen del Colegio de Guardias Jóvenes de 2024 (Modelo A, pregunta n.º 12).»
    m = re.search(r"Pregunta oficial del examen del Colegio de Guardias Jóvenes de (\d{4}) \(Modelo A, (?:pregunta de reserva|pregunta) n\.º (\d+)\)\.?", t)
    if m:
        etiqueta = f"\U0001F4CC Examen oficial CGJ {m.group(1)}, n.º {m.group(2)}."
        t = t[: m.start()].strip()
        t = re.sub(r":\s*respuesta correcta «.*?»\.?$", ".", t)  # la respuesta ya se ve en la encuesta
    m = re.search(r"Preguntado en (?:el )?examen[^:]*:\s*([^.]*)\.?", t)
    if m:
        anos = ", ".join(re.findall(r"20\d\d", m.group(1)))
        if anos:
            etiqueta = f"\U0001F4CC Cayó en CGJ {anos}."
        t = (t[: m.start()] + t[m.end():]).strip()
    disponible = limite - (tlen(etiqueta) + 1 if etiqueta else 0)
    if tlen(t) > disponible:
        t = abreviar(t, disponible)
    if tlen(t) > disponible:
        frases, cuerpo = re.split(r"(?<=[.»])\s+(?=[A-ZÁÉÍÓÚ«(])", t), ""
        for f in frases:
            if tlen(cuerpo) + tlen(f) + 1 <= disponible:
                cuerpo = (cuerpo + " " + f).strip()
            else:
                break
        t = cuerpo or _recortar(frases[0], disponible)
    return (t + " " + etiqueta).strip() if t else etiqueta

def ajustar_pregunta(p):
    """Devuelve la pregunta ajustada. p['modo_letras'] = True si alguna opción sigue sin caber."""
    q = {k: limpiar(p.get(k, "")) for k in COLUMNAS}
    q["respuesta_correcta"] = q["respuesta_correcta"].upper()[:1]
    q["enunciado"] = abreviar(q["enunciado"], MAX_ENUNCIADO)
    for k in ("opcion_a", "opcion_b", "opcion_c", "opcion_d"):
        q[k] = abreviar(q[k], MAX_OPCION)
    q["explicacion"] = ajustar_explicacion(q["explicacion"])
    return q

def cabe_como_quiz(q):
    return tlen(q["enunciado"]) <= MAX_ENUNCIADO and all(
        1 <= tlen(q[k]) <= MAX_OPCION for k in ("opcion_a", "opcion_b", "opcion_c", "opcion_d"))

def id_pregunta(q):
    return hashlib.sha1(q["enunciado"].encode("utf-8")).hexdigest()[:12]

def leer_csv(ruta):
    """Lee un CSV de la web (enunciado;tipo;opcion_a;…) o del bot (enunciado;opcion_a;…). Ignora columnas sobrantes."""
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        muestra = f.read(4096); f.seek(0)
        delim = ";" if muestra.count(";") >= muestra.count(",") else ","
        filas = []
        for r in csv.DictReader(f, delimiter=delim):
            r = {(k or "").strip().lower(): v for k, v in r.items()}
            resp = (r.get("respuesta_correcta") or "").strip().upper()
            if not r.get("enunciado") or resp[:1] not in "ABCD" or len(resp.replace(" ", "")) != 1:
                continue  # vacías o con varias respuestas correctas (los quiz de Telegram admiten solo una)
            filas.append(r)
        return filas

def escribir_csv(ruta, preguntas):
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(COLUMNAS)
        for q in preguntas:
            w.writerow([q[k] for k in COLUMNAS])
