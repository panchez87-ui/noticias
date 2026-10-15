# Bot macro y noticias → Telegram

Repo público: github.com/panchez87-ui/noticias. Bot de Telegram: @Alertas_wti_bot (renombrado «Noticias»), chat_id 1554570836. Es el único bot de noticias vigente.

Requisitos del usuario (2026-10-15):
- Prioridad 1: calendario macro de EE. UU. (importancia alta + extras). Aviso 10 minutos antes con estimado y anterior, y mensaje con el dato real unos 3 minutos después de publicado (▲/▼/= frente al estimado).
- Resumen a las 8:00 con la agenda del día (incluye el dato real de lo ya publicado); el lunes incluye el fin de semana.
- Noticias agrupadas en bloques en el orden de `TEMAS`: Fed → petróleo → gas → dólar → oro → maíz → litio → centros de datos → IA.
- Fuera del resumen, solo noticias sumamente importantes; si no hay, silencio.
- Corre cada hora de 7 a 22 h (Ecuador), de lunes a viernes. Costo $0.

Decisiones:
- Investing.com da 403 (bloquea bots). Calendario: TradingView (economic-calendar.tradingview.com, con dato real; requiere header Origin) y ForexFactory como respaldo (sin dato real).
- Noticias: Google News RSS limitado a `MEDIOS_CONFIABLES` (site:), más feeds directos.
- Gemini asigna el tema de cada noticia leyendo el titular; la búsqueda que la encontró a veces no coincide.
- Gemini en tier gratuito: `gemini-3.8-flash` y, como respaldo, `gemini-3.5-flash-lite` (verificado el 2026-10-15). Si Gemini falla, el resumen se envía igual con la agenda macro.

Python local: `.venv` (3.14). Pruebas: `bot/main.py --dry-run --sin-espera [--modo resumen|urgentes|calendario]`.
Los archivos usan CRLF en Windows (core.autocrlf=true): editar con la herramienta Edit, no con scripts que comparen texto con LF.

## Estado
- [x] Código y workflow probados en dry-run y en Actions (corridas #3 a #5 OK el 2026-10-15)
- [x] Medios confiables, bloques por tema, dato real del calendario y mensaje de dato publicado
- [ ] Ver el primer aviso y el primer dato real en un día con datos (la semana del 19-oct)
- [ ] Ajustar el criterio de urgentes y el volumen de mensajes tras una semana de uso
