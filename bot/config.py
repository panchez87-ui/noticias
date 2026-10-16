"""
Configuración del bot. Todo lo que se ajusta a mano vive aquí; main.py no
debería necesitar cambios para cambiar temas, fuentes, horarios o modelos.
"""

from datetime import timedelta, timezone

# Ecuador es UTC-5 todo el año (sin horario de verano).
ZONA_LOCAL = timezone(timedelta(hours=-5))

# ---------------------------------------------------------------------------
# Horario (hora de Ecuador). El cron del workflow lo arranca cada hora de
# 7 a 22, de lunes a viernes; aquí se decide qué hace cada corrida.
# ---------------------------------------------------------------------------
HORA_RESUMEN = 8  # la primera corrida desde las 8:00 manda el resumen del día
# Si la PC (bot/local.py) corrió hace menos de esto, las corridas programadas
# de GitHub no hacen nada: la PC es el motor principal y GitHub el respaldo.
MINUTOS_PC_ACTIVA = 90

# ---------------------------------------------------------------------------
# Calendario económico. Fuente principal: TradingView (trae el dato real
# publicado). Respaldo: ForexFactory (sin dato real). Investing.com bloquea
# a los bots.
# ---------------------------------------------------------------------------
CALENDARIO_URL = "https://economic-calendar.tradingview.com/events"
CALENDARIO_PAIS = "US"
CALENDARIO_IMPORTANCIA_MIN = 1  # TradingView: 1 = alta, 0 = media, -1 = baja
# Eventos que se avisan aunque no sean de importancia alta (título exacto de TradingView).
CALENDARIO_EXTRA = [
    "Initial Jobless Claims",
    "S&P Global Manufacturing PMI Flash",
    "S&P Global Services PMI Flash",
    "Core PPI MoM",
    "Retail Sales Ex Autos MoM",
    "Average Hourly Earnings MoM",
    # "EIA Crude Oil Stocks Change",
]

CALENDARIO_RESPALDO_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CALENDARIO_RESPALDO_EXTRA = ["Unemployment Claims", "Flash Manufacturing PMI", "Flash Services PMI"]
MINUTOS_ANTES = 10
MINUTOS_DESPUES = 3  # margen para que TradingView cargue el dato real antes de enviarlo
# Cuánto mira hacia adelante cada corrida. Algo más de 60 min para cubrir los
# retrasos de GitHub Actions; los avisos ya enviados no se repiten.
HORIZONTE_MINUTOS = 75

# Nombres en español de los indicadores más comunes (títulos de TradingView y,
# más abajo, de ForexFactory). Lo que no esté aquí se muestra con el título original.
NOMBRES_INDICADORES = {
    "Inflation Rate MoM": "IPC (inflación general) m/m",
    "Inflation Rate YoY": "IPC (inflación general) a/a",
    "Core Inflation Rate MoM": "IPC subyacente m/m",
    "Core Inflation Rate YoY": "IPC subyacente a/a",
    "PPI MoM": "IPP (precios al productor) m/m",
    "Core PPI MoM": "IPP subyacente m/m",
    "Core PCE Price Index MoM": "PCE subyacente m/m",
    "Core PCE Price Index YoY": "PCE subyacente a/a",
    "Personal Income MoM": "Ingreso personal m/m",
    "Personal Spending MoM": "Gasto personal m/m",
    "Non Farm Payrolls": "Nóminas no agrícolas (NFP)",
    "Average Hourly Earnings MoM": "Salario medio por hora m/m",
    "JOLTs Job Openings": "Vacantes laborales JOLTS",
    "Initial Jobless Claims": "Subsidios por desempleo",
    "S&P Global Manufacturing PMI Flash": "PMI manufacturero S&P (preliminar)",
    "S&P Global Services PMI Flash": "PMI de servicios S&P (preliminar)",
    "Retail Sales MoM": "Ventas minoristas m/m",
    "Retail Sales Ex Autos MoM": "Ventas minoristas sin autos m/m",
    "GDP Growth Rate QoQ Adv": "PIB (avance) t/t",
    "GDP Growth Rate QoQ 2nd Est": "PIB (2.ª estimación) t/t",
    "GDP Growth Rate QoQ Final": "PIB (final) t/t",
    "Fed Interest Rate Decision": "Decisión de tasas de la Fed",
    "Fed Press Conference": "Conferencia de prensa de la Fed",
    "FOMC Minutes": "Actas del FOMC",
    "FOMC Economic Projections": "Proyecciones económicas del FOMC",
    "Michigan Consumer Sentiment Prel": "Sentimiento del consumidor U. Michigan (prelim.)",
    "Michigan Consumer Sentiment Final": "Sentimiento del consumidor U. Michigan (final)",
    "Durable Goods Orders MoM": "Pedidos de bienes duraderos m/m",
    "Building Permits Prel": "Permisos de construcción (prelim.)",
    "Housing Starts": "Inicios de vivienda",
    "Existing Home Sales": "Ventas de viviendas usadas",
    "EIA Crude Oil Stocks Change": "Inventarios de crudo (EIA)",
    # ForexFactory (respaldo)
    "CPI m/m": "IPC (inflación general) m/m",
    "CPI y/y": "IPC (inflación general) a/a",
    "Core CPI m/m": "IPC subyacente m/m",
    "Core CPI y/y": "IPC subyacente a/a",
    "PPI m/m": "IPP (precios al productor) m/m",
    "Core PPI m/m": "IPP subyacente m/m",
    "Core PCE Price Index m/m": "PCE subyacente m/m",
    "Core PCE Price Index y/y": "PCE subyacente a/a",
    "Non-Farm Employment Change": "Nóminas no agrícolas (NFP)",
    "Unemployment Rate": "Tasa de desempleo",
    "Average Hourly Earnings m/m": "Salario medio por hora m/m",
    "ADP Non-Farm Employment Change": "Empleo privado ADP",
    "JOLTS Job Openings": "Vacantes laborales JOLTS",
    "Unemployment Claims": "Subsidios por desempleo",
    "ISM Manufacturing PMI": "PMI manufacturero ISM",
    "ISM Services PMI": "PMI de servicios ISM",
    "Flash Manufacturing PMI": "PMI manufacturero S&P (preliminar)",
    "Flash Services PMI": "PMI de servicios S&P (preliminar)",
    "Retail Sales m/m": "Ventas minoristas m/m",
    "Core Retail Sales m/m": "Ventas minoristas subyacentes m/m",
    "Advance GDP q/q": "PIB (avance) t/t",
    "Prelim GDP q/q": "PIB (preliminar) t/t",
    "Final GDP q/q": "PIB (final) t/t",
    "Federal Funds Rate": "Decisión de tasas de la Fed",
    "FOMC Statement": "Comunicado del FOMC",
    "FOMC Press Conference": "Conferencia de prensa del FOMC",
    "FOMC Meeting Minutes": "Actas del FOMC",
    "CB Consumer Confidence": "Confianza del consumidor (Conference Board)",
    "Prelim UoM Consumer Sentiment": "Sentimiento del consumidor U. Michigan (prelim.)",
    "Durable Goods Orders m/m": "Pedidos de bienes duraderos m/m",
    "Core Durable Goods Orders m/m": "Pedidos de bienes duraderos subyacentes m/m",
    "Philly Fed Manufacturing Index": "Índice manufacturero Fed de Filadelfia",
    "Empire State Manufacturing Index": "Índice manufacturero Empire State",
    "Crude Oil Inventories": "Inventarios de crudo (EIA)",
    "Natural Gas Storage": "Almacenamiento de gas natural (EIA)",
}

# ---------------------------------------------------------------------------
# Noticias. Cada tema se busca en Google News (agrega Reuters, WSJ, CNBC,
# Bloomberg, etc.); además hay algunos feeds directos asignados a un tema.
# El orden de esta lista es el orden de los bloques en el resumen. El tema
# final de cada noticia lo asigna Gemini leyendo el titular (la búsqueda que
# la encontró a veces no coincide con su contenido).
# ---------------------------------------------------------------------------
TEMAS = {
    "fed": {"etiqueta": "🏦 Fed y tasas", "busqueda": '"Federal Reserve" OR FOMC OR "Fed chair"'},
    "petroleo": {"etiqueta": "🛢 Petróleo", "busqueda": 'crude oil OR OPEC OR Brent OR WTI'},
    "gas": {"etiqueta": "🔥 Gas natural", "busqueda": '"natural gas" OR LNG OR "Henry Hub"'},
    "dolar": {"etiqueta": "💵 Dólar", "busqueda": '"dollar index" OR "U.S. dollar" OR DXY'},
    "oro": {"etiqueta": "🥇 Oro", "busqueda": '"gold price" OR "gold prices" OR bullion'},
    "maiz": {"etiqueta": "🌽 Maíz", "busqueda": 'corn futures OR "corn prices" OR WASDE OR "USDA corn"'},
    "litio": {"etiqueta": "🔋 Litio", "busqueda": 'lithium'},
    "datacenters": {"etiqueta": "🏢 Centros de datos", "busqueda": '"data center" OR "data centers" OR hyperscaler'},
    "ia": {"etiqueta": "🤖 Inteligencia artificial", "busqueda": '"artificial intelligence" OR OpenAI OR Nvidia OR Anthropic'},
}

# Las búsquedas de Google News se limitan a estos medios (sin esta lista
# entraban ~190 medios, muchos locales, de brókers o irrelevantes).
# Lista vacía = cualquier medio.
MEDIOS_CONFIABLES = [
    "reuters.com", "bloomberg.com", "cnbc.com", "wsj.com", "ft.com",
    "marketwatch.com", "finance.yahoo.com", "kitco.com", "oilprice.com",
    "naturalgasintel.com", "spglobal.com", "argusmedia.com",
    "dtnpf.com", "profarmer.com", "agweb.com", "mining.com",
]

FEEDS_DIRECTOS = [
    {"tema": "fed", "fuente": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/press_monetary.xml"},
    {"tema": "petroleo", "fuente": "OilPrice.com", "url": "https://oilprice.com/rss/main"},
    {"tema": "petroleo", "fuente": "CNBC Energía", "url": "https://www.cnbc.com/id/19836768/device/rss/rss.html"},
    {"tema": "datacenters", "fuente": "DatacenterDynamics", "url": "https://www.datacenterdynamics.com/en/rss/"},
]

MAX_TITULARES_POR_TEMA = 30   # para el resumen de la mañana
MAX_NOTICIAS_RESUMEN = 8      # cuántas noticias como máximo entran al resumen
HORAS_RESUMEN = 24            # ventana del resumen (martes a viernes)
HORAS_RESUMEN_LUNES = 72      # el lunes incluye el fin de semana
DIAS_MEMORIA = 5              # cuántos días se recuerdan noticias y avisos enviados

# ---------------------------------------------------------------------------
# IA (Google Gemini, tier gratuito). Si el primer modelo falla o agota su
# cuota, se prueba el siguiente. Verifica de vez en cuando que sigan vigentes:
# https://ai.google.dev/gemini-api/docs/models
# ---------------------------------------------------------------------------
MODELOS_GEMINI = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

# Criterio para las alertas fuera del resumen. Mientras más estricto, menos mensajes.
CRITERIO_URGENTE = """Solo hechos que un analista de commodities necesita saber YA porque
pueden mover fuerte el mercado hoy. Ejemplos: decisión sorpresiva de la OPEP+, ataque o
cierre de infraestructura energética (oleoductos, refinerías, Estrecho de Ormuz), sanciones
o prohibiciones de exportación nuevas, acción de emergencia o giro inesperado de la Fed,
dato macro muy por fuera de lo esperado, quiebra o fusión gigante en el sector, anuncio de
inversión en IA o centros de datos de decenas de miles de millones, informe del USDA que
sorprende fuertemente al mercado del maíz. NO son urgentes: análisis, opiniones,
previsiones de bancos, movimientos de precio normales, notas repetidas de algo ya conocido."""
