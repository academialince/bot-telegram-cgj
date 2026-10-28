# Bot de Telegram · Pregunta del día (Prolince · CGJ)

Publica **dos preguntas al día** en un canal o grupo de Telegram como encuesta tipo *quiz*, rotando la temática. Funciona solo con **GitHub Actions**, así que no hace falta servidor.

## Cómo funciona

- Cada tema es un CSV en `data/`. El nombre que se muestra («⚖️ Derecho Constitucional») sale de `config.json`, por eso los CSV no llevan columna de tema.
- Cada publicación toma el **siguiente tema** de `rotacion` (en `config.json`) y una pregunta **al azar que aún no se haya publicado**. Cuando se agota un tema, vuelve a empezar por ese tema.
- El progreso se guarda en `estado.json`. El propio workflow lo actualiza en el repositorio tras cada publicación.
- Si en `config.json` aparece un CSV que todavía no está en `data/` (ortografía, gramática, inglés…), se salta hasta que lo subas.

### Límites de Telegram

| Campo | Máximo |
|---|---|
| Pregunta | 300 caracteres |
| Cada opción | 100 caracteres |
| Explicación (bombilla 💡) | 200 caracteres |

- Las explicaciones ya vienen recortadas a 200 caracteres, y el año en que la pregunta cayó en examen se indica con 📌.
- Cuando una opción no cabe ni abreviando, el bot usa el **modo letras**: envía un mensaje con la pregunta y las cuatro opciones completas, y debajo la encuesta solo con A, B, C y D.
- Las preguntas con varias respuestas correctas, por ejemplo «A,D», se descartan, porque un quiz de Telegram solo admite una respuesta correcta.

## Puesta en marcha (una sola vez)

1. **Crear el bot.** En Telegram, abre @BotFather, envía `/newbot` y guarda el **token** que te da.
2. **Añadirlo al canal.** Mete el bot en tu canal o grupo como **administrador**, con permiso para publicar mensajes.
3. **Averiguar el chat_id.**
   - Canal público: es su `@nombre`, por ejemplo `@prolince_cgj`.
   - Canal privado o grupo: publica un mensaje y abre `https://api.telegram.org/bot<TOKEN>/getUpdates`. El número que empieza por `-100…` es el chat_id.
4. **Subir este repositorio a GitHub.** Puede ser privado.
5. **Añadir los secretos.** Ve a *Settings → Secrets and variables → Actions → New repository secret* y crea:
   - `TELEGRAM_BOT_TOKEN`: el token de BotFather.
   - `TELEGRAM_CHAT_ID`: el `@canal` o el número `-100…`.
6. **Dar permiso de escritura al workflow.** En *Settings → Actions → General → Workflow permissions*, marca **Read and write permissions**.
7. **Probarlo.** En la pestaña *Actions*, abre «Pregunta del día» y pulsa **Run workflow**. Debería publicarse una pregunta en el canal.

## Horario

El horario se define en `.github/workflows/publicar.yml` y está en **UTC**:

```yaml
- cron: "0 8 * * *"    # 09:00 en invierno / 10:00 en verano (hora peninsular)
- cron: "0 19 * * *"   # 20:00 en invierno / 21:00 en verano
```

GitHub puede retrasar las ejecuciones programadas unos minutos en horas de mucha carga.

## Añadir tus CSV de ortografía, gramática e inglés

Puedes subirlos directamente a `data/` con el formato de la web (`enunciado;tipo;opcion_a;…;cursos_aplicables`). El bot ignora las columnas que no usa y los ajusta al publicar.

Los nombres de archivo deben coincidir con los de `config.json`:

- `data/ortografia.csv`
- `data/gramatica.csv`
- `data/ingles.csv`

Si prefieres dejarlos limpios y comprobar antes cuántas preguntas caben, conviértelos primero:

```bash
python adaptar_csv.py ortografia_web.csv data/ortografia.csv
```

## Cambiar la rotación

Edita la lista `rotacion` de `config.json`. Puedes reordenar los temas, quitarlos o repetirlos; por ejemplo, poner Constitucional dos veces le da el doble de frecuencia. Cada entrada lleva:

- `archivo`: la ruta del CSV.
- `nombre`: el texto que se muestra en la publicación.
- `emoji`: el icono que acompaña al nombre.

## Probar en local sin publicar

```bash
python publicar.py --prueba
```

Muestra lo que se enviaría, sin enviar nada y sin tocar `estado.json`. No necesita dependencias, solo Python 3.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `publicar.py` | Elige y publica una pregunta, y actualiza `estado.json` |
| `formato.py` | Ajuste a los límites de Telegram y lectura y escritura de los CSV |
| `adaptar_csv.py` | Convierte un CSV de la web al formato del bot |
| `config.json` | Rotación de temas: archivo, nombre y emoji |
| `estado.json` | Preguntas ya publicadas y siguiente tema; lo actualiza el workflow |
| `data/*.csv` | Bancos de preguntas: `enunciado;opcion_a;opcion_b;opcion_c;opcion_d;respuesta_correcta;explicacion` |
| `.github/workflows/publicar.yml` | Programación diaria en GitHub Actions |
