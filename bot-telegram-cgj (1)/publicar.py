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
    m = re.search(r"Pregunta oficial del examen del Colegio de Guardias Jóvenes de (\d{4}) \(Modelo A, (?:pregunta de reserva|pregunta) n\.º (\d+)\)\.?", t)
    if m:
        etiqueta = f"📌 Examen oficial CGJ
