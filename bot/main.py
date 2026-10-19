#!/usr/bin/env python3
"""
Bot de calendario macro y noticias -> Telegram.

Cada corrida (cada hora, 7 a 22 h de Ecuador, lunes a viernes):
  1. Noticias:
     - la primera corrida desde las 8:00 manda el resumen del día (agenda macro
       + noticias más importantes; el lunes incluye el fin de semana);
     - las demás solo avisan si hay algo sumamente importante (si no, silencio).
  2. Calendario: si algún dato macro sale antes de la próxima corrida, espera y
     avisa 10 minutos antes, con el estimado y el dato anterior.

Variables de entorno: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY.

Pruebas locales:
    python bot/main.py --dry-run                  # no envía nada, no guarda estado
    python bot/main.py --dry-run --modo resumen   # fuerza el resumen
    python bot/main.py --dry-run --sin-espera     # no espera a los avisos del calendario
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_ESTADO = RAIZ / "data" / "state.json"
UA = "Mozilla/5.0 (compatible; BotNoticiasMacro/1.0)"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def log(msg):
    print(f"[{datetime.now(config.ZONA_LOCAL):%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def ahora():
    return datetime.now(config.ZONA_LOCAL)


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# Estado persistente (data/state.json, se guarda en el repositorio)
# ---------------------------------------------------------------------------

def cargar_estado():
    estado = {}
    if ARCHIVO_ESTADO.exists():
        try:
            estado = json.loads(ARCHIVO_ESTADO.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"AVISO: no se pudo leer el estado ({e}); se empieza de cero.")
    estado.setdefault("vistos", {})        # noticias ya procesadas: clave -> fecha
    estado.setdefault("avisados", {})      # eventos del calendario ya avisados
    estado.setdefault("publicados", {})    # eventos cuyo dato real ya se envió
    estado.setdefault("urgentes", [])      # titulares enviados como urgentes
    estado.setdefault("ultimo_resumen", None)
    return estado


def pc_activa(estado):
    """La PC corrió hace poco (bot/local.py): GitHub queda solo de respaldo."""
    ultima = estado.get("ultima_corrida_pc")
    return bool(ultima) and ahora() - datetime.fromisoformat(ultima) < timedelta(minutes=config.MINUTOS_PC_ACTIVA)


def guardar_estado(estado, dry_run):
    if dry_run:
        return
    limite = (ahora() - timedelta(days=config.DIAS_MEMORIA)).isoformat()
    estado["vistos"] = {k: v for k, v in estado["vistos"].items() if v >= limite}
    estado["avisados"] = {k: v for k, v in estado["avisados"].items() if v >= limite}
    estado["publicados"] = {k: v for k, v in estado["publicados"].items() if v >= limite}
    estado["urgentes"] = [u for u in estado["urgentes"] if u["fecha"] >= limite]
    ARCHIVO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True),
                              encoding="utf-8")


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def enviar_telegram(texto, dry_run):
    if dry_run:
        print("\n----- MENSAJE (dry-run) -----\n" + texto + "\n-----------------------------\n")
        return
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    # Telegram admite hasta 4096 caracteres por mensaje; se parte por líneas.
    trozos, actual = [], ""
    for linea in texto.split("\n"):
        if len(actual) + len(linea) + 1 > 4000:
            trozos.append(actual)
            actual = ""
        actual += linea + "\n"
    trozos.append(actual)
    for trozo in trozos:
        datos = urllib.parse.urlencode({
            "chat_id": os.environ["TELEGRAM_CHAT_ID"],
            "text": trozo,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode("utf-8")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=datos), timeout=30) as r:
                r.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Telegram respondió {e.code}: {e.read().decode('utf-8', 'replace')}") from e
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Calendario económico
# ---------------------------------------------------------------------------

def nombre_evento(titulo):
    nombre = config.NOMBRES_INDICADORES.get(titulo, titulo)
    for sufijo in (" Speaks", " Speech"):
        if nombre.endswith(sufijo):
            nombre = "Discurso: " + nombre[:-len(sufijo)]
    return nombre


def valor_tv(e, campo):
    """Formatea un valor de TradingView con su escala y unidad (p. ej. 199K, 1.3%)."""
    v = e.get(campo)
    if v is None:
        return None
    texto = f"{v:g}" + (e.get("scale") or "")
    unidad = (e.get("unit") or "").strip()
    if unidad == "%":
        texto += "%"
    elif unidad:
        texto += f" {unidad}"
    return texto


def leer_calendario_tradingview():
    hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    params = urllib.parse.urlencode({
        "from": (hoy - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "to": (hoy + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "countries": config.CALENDARIO_PAIS,
    })
    req = urllib.request.Request(f"{config.CALENDARIO_URL}?{params}", headers={
        "User-Agent": "Mozilla/5.0", "Origin": "https://www.tradingview.com"})
    with urllib.request.urlopen(req, timeout=20) as r:
        datos = json.loads(r.read())["result"]
    eventos = []
    for e in datos:
        if (e.get("importance") or -1) < config.CALENDARIO_IMPORTANCIA_MIN and e.get("title") not in config.CALENDARIO_EXTRA:
            continue
        eventos.append({
            "fecha": datetime.fromisoformat(e["date"].replace("Z", "+00:00")).astimezone(config.ZONA_LOCAL),
            "titulo": e["title"],
            "nombre": nombre_evento(e["title"]),
            "real": valor_tv(e, "actual"),
            "real_num": e.get("actual"),
            "est_num": e.get("forecast"),
            "estimado": valor_tv(e, "forecast") or "—",
            "anterior": valor_tv(e, "previous") or "—",
        })
    return eventos


def leer_calendario_forexfactory():
    eventos = []
    for e in json.loads(http_get(config.CALENDARIO_RESPALDO_URL)):
        if e.get("country") != "USD":
            continue
        if e.get("impact") != "High" and e.get("title") not in config.CALENDARIO_RESPALDO_EXTRA:
            continue
        eventos.append({
            "fecha": datetime.fromisoformat(e["date"]).astimezone(config.ZONA_LOCAL),
            "titulo": e["title"],
            "nombre": nombre_evento(e["title"]),
            "real": None,  # ForexFactory no publica el dato real en su JSON
            "estimado": e.get("forecast") or "—",
            "anterior": e.get("previous") or "—",
        })
    return eventos


def leer_calendario():
    """Eventos relevantes, con la hora convertida a Ecuador."""
    try:
        eventos = leer_calendario_tradingview()
    except Exception as e:
        log(f"AVISO: falló el calendario de TradingView ({e}); se usa ForexFactory (sin dato real).")
        eventos = leer_calendario_forexfactory()
    return sorted(eventos, key=lambda x: x["fecha"])


def agrupar_por_hora(eventos):
    grupos = {}
    for e in eventos:
        grupos.setdefault(e["fecha"], []).append(e)
    return sorted(grupos.items())


def linea_evento(e):
    real = f"real: <b>{html.escape(e['real'])}</b> | " if e.get("real") else ""
    return (f"• <b>{html.escape(e['nombre'])}</b> — {real}est: {html.escape(e['estimado'])}"
            f" | ant: {html.escape(e['anterior'])}")


def mensaje_aviso(fecha, eventos):
    lineas = [f"⏰ <b>En {config.MINUTOS_ANTES} min — dato macro EE. UU. a las {fecha:%H:%M}</b>", ""]
    lineas += [linea_evento(e) for e in eventos]
    return "\n".join(lineas)


def comparacion(e):
    real, estimado = e.get("real_num"), e.get("est_num")
    if real is None or estimado is None:
        return ""
    if real > estimado:
        return " ▲ sobre lo estimado"
    if real < estimado:
        return " ▼ bajo lo estimado"
    return " = en línea"


def mensaje_publicado(fecha, eventos):
    lineas = [f"📊 <b>Publicado — dato macro EE. UU. de las {fecha:%H:%M}</b>", ""]
    lineas += [linea_evento(e) + comparacion(e) for e in eventos if e.get("real")]
    return "\n".join(lineas)


def es_discurso(grupo):
    # Los discursos y conferencias no tienen cifras: no hay dato real que esperar.
    return all(e["anterior"] == "—" and e["estimado"] == "—" for e in grupo)


def procesar_calendario(eventos, estado, args):
    """Avisa 10 min antes de cada dato y manda el dato real apenas se publica.

    Cubre lo que pasa antes de la próxima corrida, esperando si hace falta, más
    los datos publicados desde la corrida anterior cuyo valor real aún no se envió.
    """
    horizonte = ahora() + timedelta(minutes=config.HORIZONTE_MINUTOS)
    tareas = []
    for fecha, grupo in agrupar_por_hora(eventos):
        clave = fecha.isoformat()
        aviso = fecha - timedelta(minutes=config.MINUTOS_ANTES)
        if fecha > ahora() and aviso <= horizonte:
            if clave not in estado["avisados"]:
                tareas.append((aviso, "aviso", fecha, grupo))
            if clave not in estado["publicados"] and not es_discurso(grupo):
                tareas.append((fecha + timedelta(minutes=config.MINUTOS_DESPUES), "publicado", fecha, grupo))
        elif (ahora() - timedelta(minutes=90) <= fecha <= ahora() and clave not in estado["publicados"]
              and not es_discurso(grupo)):
            tareas.append((ahora(), "publicado", fecha, grupo))

    if not tareas:
        log("Calendario: no hay datos macro antes de la próxima corrida.")
        return

    for momento, tipo, fecha, grupo in sorted(tareas, key=lambda t: t[0]):
        espera = (momento - ahora()).total_seconds()
        if espera > 0:
            if args.sin_espera:
                log(f"Calendario: (sin espera) el mensaje '{tipo}' saldría a las {momento:%H:%M}.")
            else:
                log(f"Calendario: esperando hasta las {momento:%H:%M} ({tipo} del dato de las {fecha:%H:%M})...")
                time.sleep(espera)
                if tipo == "publicado":
                    try:  # se vuelve a leer el calendario para traer el dato recién publicado
                        grupo = [e for e in leer_calendario() if e["fecha"] == fecha] or grupo
                    except Exception as e:
                        log(f"AVISO: no se pudo releer el calendario ({e}).")

        if tipo == "aviso":
            enviar_telegram(mensaje_aviso(fecha, grupo), args.dry_run)
            estado["avisados"][fecha.isoformat()] = ahora().isoformat()
            log(f"Calendario: aviso enviado ({len(grupo)} indicador/es de las {fecha:%H:%M}).")
        elif any(e.get("real") for e in grupo):
            enviar_telegram(mensaje_publicado(fecha, grupo), args.dry_run)
            estado["publicados"][fecha.isoformat()] = ahora().isoformat()
            log(f"Calendario: dato real enviado (indicadores de las {fecha:%H:%M}).")
        else:
            log(f"Calendario: el dato de las {fecha:%H:%M} aún no aparece; se reintenta en la próxima corrida.")
        guardar_estado(estado, args.dry_run)


def agenda_de_hoy(eventos):
    hoy = ahora().date()
    grupos = [(f, g) for f, g in agrupar_por_hora(eventos) if f.date() == hoy]
    if not grupos:
        return "📅 <b>Agenda macro EE. UU.</b>\nSin datos de alto impacto hoy."
    lineas = ["📅 <b>Agenda macro EE. UU. (hora Ecuador)</b>"]
    for fecha, grupo in grupos:
        marca = " ✅ publicado" if fecha <= ahora() else ""
        lineas.append(f"\n<b>{fecha:%H:%M}</b>{marca}")
        lineas += [linea_evento(e) for e in grupo]
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Noticias
# ---------------------------------------------------------------------------

def clave_titular(titulo):
    # Google News agrega " - Fuente" al final; se quita para detectar repetidos entre fuentes.
    base = re.sub(r"\s+-\s+[^-]+$", "", titulo).lower()
    base = re.sub(r"[^a-z0-9 ]", "", base)
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def url_google_news(busqueda, ventana):
    consulta = f"({busqueda})"
    if config.MEDIOS_CONFIABLES:
        consulta += " (" + " OR ".join(f"site:{m}" for m in config.MEDIOS_CONFIABLES) + ")"
    q = urllib.parse.quote(f"{consulta} when:{ventana}")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def leer_feed(url, nombre):
    try:
        return feedparser.parse(http_get(url)).entries
    except Exception as e:
        log(f"AVISO: no se pudo leer '{nombre}' -> {e}")
        return []


def recolectar_noticias(desde, ventana_google):
    """Titulares publicados desde `desde`, sin repetidos, agrupados por tema."""
    fuentes = [(tema, None, url_google_news(cfg["busqueda"], ventana_google))
               for tema, cfg in config.TEMAS.items()]
    fuentes += [(f["tema"], f["fuente"], f["url"]) for f in config.FEEDS_DIRECTOS]

    por_tema = {tema: [] for tema in config.TEMAS}
    claves = set()
    for tema, fuente, url in fuentes:
        for entrada in leer_feed(url, fuente or f"Google News / {tema}"):
            titulo = (entrada.get("title") or "").strip()
            link = entrada.get("link") or ""
            if not titulo or not link:
                continue
            fecha = None
            if entrada.get("published_parsed"):
                fecha = datetime(*entrada.published_parsed[:6], tzinfo=timezone.utc)
                if fecha < desde:
                    continue
            clave = clave_titular(titulo)
            if clave in claves:
                continue
            claves.add(clave)
            por_tema[tema].append({
                "clave": clave,
                "titulo": titulo,
                "link": link,
                "fuente": (entrada.get("source") or {}).get("title") or fuente or "Google News",
                "fecha": fecha,
                "tema": tema,
            })
    for tema in por_tema:
        por_tema[tema].sort(key=lambda n: n["fecha"] or desde, reverse=True)
        por_tema[tema] = por_tema[tema][:config.MAX_TITULARES_POR_TEMA]
    return por_tema


def lista_numerada(noticias):
    lineas = []
    for i, n in enumerate(noticias):
        cuando = n["fecha"].astimezone(config.ZONA_LOCAL).strftime("%d/%m %H:%M") if n["fecha"] else "?"
        lineas.append(f"[{i}] {n['titulo']} — {cuando}")
    return "\n".join(lineas)


def temas_para_prompt():
    return ", ".join(f'"{k}" ({v["etiqueta"].split(" ", 1)[1]})' for k, v in config.TEMAS.items())


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

def preguntar_gemini(prompt):
    """Devuelve la respuesta JSON de Gemini ya parseada, probando los modelos en orden."""
    clave = os.environ.get("GEMINI_API_KEY", "")
    if not clave:
        raise RuntimeError("falta GEMINI_API_KEY")
    cuerpo = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }).encode("utf-8")
    ultimo_error = None
    for modelo in config.MODELOS_GEMINI:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
        req = urllib.request.Request(url, data=cuerpo, headers={
            "Content-Type": "application/json", "x-goog-api-key": clave})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                respuesta = json.loads(r.read())
            texto = "".join(p.get("text", "") for p in respuesta["candidates"][0]["content"]["parts"])
            log(f"Gemini respondió con {modelo}.")
            return json.loads(texto)
        except urllib.error.HTTPError as e:
            ultimo_error = f"{modelo}: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}"
        except Exception as e:
            ultimo_error = f"{modelo}: {e}"
        log(f"AVISO: falló {ultimo_error}; probando el siguiente modelo.")
    raise RuntimeError(f"ningún modelo de Gemini respondió ({ultimo_error})")


def elegidas(respuesta, noticias):
    """Valida la lista que devuelve la IA y la cruza con las noticias originales."""
    resultado = []
    for item in respuesta.get("noticias", []):
        try:
            n = noticias[int(item["id"])]
        except (KeyError, ValueError, IndexError, TypeError):
            continue
        # El tema lo decide la IA leyendo el titular; si no da uno válido, queda el de la búsqueda.
        tema = item.get("tema") if item.get("tema") in config.TEMAS else n["tema"]
        resultado.append((n, str(item.get("resumen", "")).strip(), str(item.get("por_que", "")).strip(), tema))
    return resultado


def bloques_por_tema(seleccion):
    """Agrupa las noticias elegidas por tema, en el orden de config.TEMAS."""
    bloques = []
    for tema, cfg in config.TEMAS.items():
        lineas = []
        for n, resumen, _, t in seleccion:
            if t != tema:
                continue
            enlace = f'<a href="{html.escape(n["link"], quote=True)}">{html.escape(n["fuente"])}</a>'
            lineas.append(f"• {html.escape(resumen)} ({enlace})")
        if lineas:
            bloques.append(f"<b>{cfg['etiqueta']}</b>\n" + "\n\n".join(lineas))
    return "\n\n".join(bloques)


def limitar_por_tema(seleccion):
    """Deja como máximo NOTICIAS_POR_TEMA_MAX noticias en cada bloque."""
    cuenta, resultado = {}, []
    for item in seleccion:
        cuenta[item[3]] = cuenta.get(item[3], 0) + 1
        if cuenta[item[3]] <= config.NOTICIAS_POR_TEMA_MAX:
            resultado.append(item)
    return resultado


def recolectar_tendencias(desde):
    """Titulares de MEDIOS_TENDENCIAS publicados desde `desde`, sin filtro de tema.

    Se pide cada medio día por día: Google News devuelve como máximo 100
    titulares por búsqueda, y así el conteo no depende de la ventana."""
    ruido = re.compile(config.RUIDO_TENDENCIAS, re.I)
    titulares, claves = [], set()
    dia, hasta = desde.astimezone(config.ZONA_LOCAL).date(), ahora().date()
    while dia <= hasta:
        for medio in config.MEDIOS_TENDENCIAS:
            q = urllib.parse.quote(f"site:{medio} after:{dia} before:{dia + timedelta(days=1)}")
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            for entrada in leer_feed(url, f"Google News / {medio}"):
                titulo = (entrada.get("title") or "").strip()
                link = entrada.get("link") or ""
                if not titulo or not link or ruido.search(titulo):
                    continue
                if entrada.get("published_parsed"):
                    if datetime(*entrada.published_parsed[:6], tzinfo=timezone.utc) < desde:
                        continue
                clave = clave_titular(titulo)
                if clave in claves:
                    continue
                claves.add(clave)
                titulares.append({"titulo": titulo, "link": link, "medio": medio,
                                  "fuente": (entrada.get("source") or {}).get("title") or medio})
        dia += timedelta(days=1)
    log(f"Lo más comentado: {len(titulares)} titulares de medios generales.")
    return titulares


def lo_mas_comentado(titulares):
    """Las historias con fondo económico más repetidas que no caen en un bloque de TEMAS."""
    if not titulares:
        return ""
    lista = "\n".join(f"[{i}] {n['titulo']}" for i, n in enumerate(titulares))
    prompt = f"""Eres analista de mercados. Abajo hay {len(titulares)} titulares de medios grandes,
numerados. Agrupa los que cuentan la MISMA historia (el mismo hecho o el mismo conflicto en
desarrollo, p. ej. "protestas en Francia" o "resultados de los bancos de EE. UU."). Devuelve
las 20 historias con MÁS titulares, de cualquier ámbito (empresas, geopolítica, guerras,
política, sociedad...). Para cada una:
- "ids": la lista COMPLETA de los números de sus titulares;
- "tema": si la historia trata directamente de uno de estos temas, su clave:
  {temas_para_prompt()}; si no, "otro";
- "fondo_economico": true solo si tiene un efecto económico claro (mueve mercados, divisas,
  bonos, empresas concretas, commodities, comercio o finanzas públicas); false para sucesos
  políticos, sociales o humanos sin ese efecto;
- "resumen": en español, 1 o 2 frases: qué está pasando y por qué importa en lo económico.
No des recomendaciones de inversión.

Responde solo con JSON: {{"historias": [{{"ids": [<números>], "tema": "<clave u otro>", "fondo_economico": true, "resumen": "<texto>"}}]}}

Titulares:
{lista}"""
    historias = []
    for h in preguntar_gemini(prompt).get("historias", []):
        ids = set()
        for i in h.get("ids", []):
            try:
                if 0 <= int(i) < len(titulares):
                    ids.add(int(i))
            except (ValueError, TypeError):
                continue
        medios = {titulares[i]["medio"] for i in ids}
        if (h.get("fondo_economico") is not True or h.get("tema") in config.TEMAS
                or len(ids) < config.TENDENCIAS_MIN_TITULARES or len(medios) < config.TENDENCIAS_MIN_MEDIOS):
            continue
        historias.append((len(ids), len(medios), str(h.get("resumen", "")).strip(), titulares[min(ids)]))
    historias.sort(key=lambda x: x[0], reverse=True)
    lineas = []
    for n_titulares, n_medios, resumen, n in historias[:config.MAX_TENDENCIAS]:
        enlace = f'<a href="{html.escape(n["link"], quote=True)}">{html.escape(n["fuente"])}</a>'
        lineas.append(f"• {html.escape(resumen)} <i>({n_titulares} titulares en {n_medios} medios)</i> ({enlace})")
    log(f"Lo más comentado: {len(historias)} historias pasan el umbral; se muestran {len(lineas)}.")
    return "\n\n".join(lineas)


def hacer_resumen(estado, eventos, error_calendario, args):
    es_lunes = ahora().weekday() == 0
    horas = config.HORAS_RESUMEN_LUNES if es_lunes else config.HORAS_RESUMEN
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    por_tema = recolectar_noticias(desde, "3d" if es_lunes else "1d")
    noticias = [n for lista in por_tema.values() for n in lista]
    log(f"Resumen: {len(noticias)} titulares de las últimas {horas} h.")

    hoy = ahora()
    partes = [f"☀️ <b>Resumen del {DIAS[hoy.weekday()]} {hoy.day} {MESES[hoy.month - 1]}</b>"]
    if es_lunes:
        partes[0] += "\n<i>Incluye el fin de semana</i>"
    partes.append(f"📅 <b>Agenda macro</b>\n⚠️ No se pudo leer el calendario ({html.escape(error_calendario)})."
                  if error_calendario else agenda_de_hoy(eventos))
    # Los datos reales que ya van en la agenda no se repiten en un mensaje aparte.
    for fecha, grupo in agrupar_por_hora(eventos):
        if fecha <= ahora() and any(e.get("real") for e in grupo):
            estado["publicados"][fecha.isoformat()] = ahora().isoformat()

    seleccion = []
    if noticias:
        prompt = f"""Eres el editor de un analista junior de commodities y macro en Ecuador. Abajo
hay titulares de las últimas {horas} horas, numerados. Para CADA tema (petróleo, gas natural,
centros de datos, IA, oro, maíz, litio, dólar y tasas de la Fed) elige entre
{config.NOTICIAS_POR_TEMA_MIN} y {config.NOTICIAS_POR_TEMA_MAX} noticias, las más importantes para
ese mercado; si un tema no tiene suficientes noticias relevantes, elige solo las que haya:
es mejor un bloque corto que uno con relleno (páginas de cotizaciones o titulares sin un hecho
concreto no cuentan). Prioriza hechos (decisiones, datos, acuerdos, conflictos, cifras) sobre
análisis u opinión.
Si varias noticias tratan el mismo hecho, elige solo una.

Para cada una indica el "tema" según de qué trata REALMENTE el titular (no adivines por la
fuente), usando una de estas claves: {temas_para_prompt()}. Si un titular no encaja en
ninguno de esos temas, no lo elijas. Escribe también en español un "resumen" de 1 o 2
frases: qué pasó y por qué importa para el mercado. No des recomendaciones de inversión.

Responde solo con JSON: {{"noticias": [{{"id": <número>, "tema": "<clave>", "resumen": "<texto>"}}]}}

Titulares:
{lista_numerada(noticias)}"""
        if args.dry_run and not os.environ.get("GEMINI_API_KEY"):
            log("Sin GEMINI_API_KEY en dry-run: se muestran los primeros titulares sin filtrar.")
            seleccion = limitar_por_tema([(n, n["titulo"], "", n["tema"]) for n in noticias])
        else:
            try:
                seleccion = limitar_por_tema(elegidas(preguntar_gemini(prompt), noticias))
            except Exception as e:
                # La agenda macro llega igual aunque la IA falle.
                log(f"ERROR con Gemini: {e}")
                partes.append("⚠️ <i>No se pudo usar Gemini para elegir las noticias; revisa GEMINI_API_KEY "
                              "o los logs en Actions.</i>")

    if seleccion:
        partes.append("📰 <b>Lo más importante</b>\n\n" + bloques_por_tema(seleccion))
    else:
        partes.append("📰 Sin noticias destacadas.")

    if args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        log("Sin GEMINI_API_KEY en dry-run: no se calcula «Lo más comentado».")
    else:
        try:
            comentado = lo_mas_comentado(recolectar_tendencias(desde))
            if comentado:
                partes.append("🔥 <b>Lo más comentado</b>\n\n" + comentado)
        except Exception as e:
            # Es un extra: si falla, el resumen sale igual.
            log(f"ERROR en «Lo más comentado»: {e}")

    enviar_telegram("\n\n".join(partes), args.dry_run)
    marca = ahora().isoformat()
    for n in noticias:
        estado["vistos"][n["clave"]] = marca
    estado["ultimo_resumen"] = hoy.date().isoformat()


def revisar_urgentes(estado, args):
    desde = datetime.now(timezone.utc) - timedelta(hours=3)
    por_tema = recolectar_noticias(desde, "3h")
    nuevas = [n for lista in por_tema.values() for n in lista if n["clave"] not in estado["vistos"]]
    log(f"Urgentes: {len(nuevas)} titulares nuevos desde la última corrida.")
    if not nuevas:
        return

    ya_enviadas = "\n".join(f"- {u['titulo']}" for u in estado["urgentes"]) or "(ninguna)"
    prompt = f"""Filtras alertas para un analista de commodities y macro. Abajo hay titulares
nuevos, numerados. La regla es casi nunca molestar: elige un titular SOLO si cumple este
criterio:

{config.CRITERIO_URGENTE}

Tampoco elijas nada que repita un hecho ya alertado hoy:
{ya_enviadas}

Lo normal es que la lista quede vacía. Si eliges alguno, indica su "tema" según de qué trata
realmente, con una de estas claves: {temas_para_prompt()}; y escribe en español un "resumen"
(qué pasó, 1 frase) y "por_que" (por qué mueve el mercado, 1 frase). Máximo 3. No des
recomendaciones de inversión.

Responde solo con JSON: {{"noticias": [{{"id": <número>, "tema": "<clave>", "resumen": "<texto>", "por_que": "<texto>"}}]}}

Titulares:
{lista_numerada(nuevas)}"""

    if args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        log("Sin GEMINI_API_KEY en dry-run: no se evalúan urgentes.")
        seleccion = []
    else:
        seleccion = elegidas(preguntar_gemini(prompt), nuevas)[:3]

    for n, resumen, por_que, tema in seleccion:
        texto = (f"🚨 <b>Urgente — {config.TEMAS[tema]['etiqueta']}</b>\n\n{html.escape(resumen)}\n\n"
                 f"<i>Por qué importa:</i> {html.escape(por_que)}\n\n"
                 f'<a href="{html.escape(n["link"], quote=True)}">{html.escape(n["fuente"])}</a>')
        enviar_telegram(texto, args.dry_run)
        estado["urgentes"].append({"titulo": n["titulo"], "fecha": ahora().isoformat()})
    if not seleccion:
        log("Urgentes: nada sumamente importante; no se envía nada.")

    marca = ahora().isoformat()
    for n in nuevas:
        estado["vistos"][n["clave"]] = marca


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modo", choices=["auto", "resumen", "urgentes", "calendario"], default="auto")
    p.add_argument("--dry-run", action="store_true", help="Imprime los mensajes en vez de enviarlos y no guarda estado.")
    p.add_argument("--sin-espera", action="store_true", help="No espera a la hora de los avisos del calendario.")
    args = p.parse_args()

    if not args.dry_run:
        faltan = [v for v in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY") if not os.environ.get(v)]
        if faltan:
            log(f"ERROR: faltan variables de entorno: {', '.join(faltan)}")
            sys.exit(1)

    estado = cargar_estado()
    hoy = ahora().date().isoformat()

    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and pc_activa(estado):
        log("La PC está corriendo el bot; esta corrida de GitHub no hace nada.")
        return

    eventos, error_calendario = [], None
    try:
        eventos = leer_calendario()
        log(f"Calendario: {len(eventos)} eventos relevantes entre ayer y los próximos 3 días.")
    except Exception as e:
        error_calendario = str(e)
        log(f"ERROR leyendo el calendario: {e}")

    modo = args.modo
    if modo == "auto":
        if ahora().hour >= config.HORA_RESUMEN and estado["ultimo_resumen"] != hoy:
            modo = "resumen"
        elif estado["ultimo_resumen"] == hoy:
            modo = "urgentes"
        else:
            modo = "calendario"  # antes del resumen: solo avisos del calendario
    log(f"Modo: {modo}")

    fallo = False
    try:
        if modo == "resumen":
            hacer_resumen(estado, eventos, error_calendario, args)
        elif modo == "urgentes":
            revisar_urgentes(estado, args)
    except Exception as e:
        # Un fallo en las noticias no debe impedir los avisos del calendario.
        log(f"ERROR en noticias: {e}")
        fallo = True
    guardar_estado(estado, args.dry_run)

    if eventos:
        procesar_calendario(eventos, estado, args)
    guardar_estado(estado, args.dry_run)
    if fallo:
        sys.exit(1)


if __name__ == "__main__":
    main()
