# Bot macro y noticias → Telegram

Repo público: github.com/panchez87-ui/noticias. Bot de Telegram: @Alertas_wti_bot (renombrado «Noticias»), chat_id 1554570836. Es el único bot de noticias vigente.

Requisitos del usuario (2026-10-15):
- Prioridad 1: calendario macro de EE. UU. (importancia alta + extras). Extras desde el 2026-10-21: inventarios EIA de crudo, gasolina y gas natural, y subastas del Tesoro a 10, 20 y 30 años (en TradingView tienen importancia media/baja y no salían). Aviso 10 minutos antes con estimado y anterior, y mensaje con el dato real unos 3 minutos después de publicado (▲/▼/= frente al estimado).
- Resumen a las 8:00 con la agenda del día (incluye el dato real de lo ya publicado); el lunes incluye el fin de semana.
- Noticias agrupadas en bloques en el orden de `TEMAS`: Fed → petróleo → gas → dólar → oro → maíz → litio → centros de datos → IA.
- «Muy comentado ahora» (2026-10-29): el usuario notó que no llegó nada cuando Alphabet (28-oct) y Amazon (29-oct) reportaron y cayeron. Su idea: si una noticia se repite mucho, avisar. «Lo más comentado» solo corría a las 8:00 y además excluía las historias con tema (Alphabet salía como «ia»). Ahora `revisar_comentados` corre en cada corrida de urgentes: barre `MEDIOS_TENDENCIAS` de las últimas `HORAS_COMENTADO` (6) y avisa las historias con ≥ `COMENTADO_MIN_TITULARES` (8) en ≥ `COMENTADO_MIN_MEDIOS` (3), aunque caigan en un tema. Cada historia se avisa una vez al día (`estado["comentados"]`, incluye lo del resumen; Gemini decide si repite). Resultados de empresas y movimientos de bolsa cuentan como tema «otro». También se agregaron al criterio de urgentes los resultados sorpresivos de las 7 magníficas y las caídas o subidas fuertes del S&P 500 y el Nasdaq. Se probó primero un bloque de tema «acciones», pero se quitó: el usuario quiere que esto llegue por repetición.
- Cada bloque lleva 1 noticia; una 2.ª solo si es otro hecho importante (2026-10-19; probó 2-3 por bloque y le pareció demasiado: ~27 noticias). Si un tema no tiene nada relevante, el bloque no sale.
- «Lo más comentado» (2026-10-19): al final del resumen, siempre las 3 historias más repetidas de cualquier ámbito con fondo económico que NO caen en un bloque ni repiten una noticia ya elegida en el resumen. Sin umbral mínimo (antes ≥15 titulares y ≥5 medios; el usuario pidió que sean siempre 3); se muestra el conteo de titulares y medios. Pueden repetirse cada día aunque no haya información nueva. Se barre `MEDIOS_TENDENCIAS` día por día y Gemini agrupa por historia; el conteo lo hace el código. El resultado varía algo entre corridas de Gemini.
- Fuera del resumen, solo noticias sumamente importantes; si no hay, silencio.
- Corre cada hora de 7 a 22 h (Ecuador), de lunes a viernes. Costo $0.

Decisiones:
- Investing.com da 403 (bloquea bots). Calendario: TradingView (economic-calendar.tradingview.com, con dato real; requiere header Origin) y ForexFactory como respaldo (sin dato real).
- Subastas del Tesoro (2026-10-21): TradingView no cargó el resultado de la de 20 años ni 2 h después, así que el aviso salió pero el dato no. El resultado se toma de TreasuryDirect (`completar_subastas`, API pública TA_WS): rendimiento adjudicado + cobertura (bid-to-cover), y ▲/▼ frente a la subasta anterior porque no hay estimado.
- Noticias: Google News RSS limitado a `MEDIOS_CONFIABLES` (site:), más feeds directos.
- GitHub se saltó la mayoría de las corridas programadas del 15 y 16-oct (cron en :00). Desde el 2026-10-16 el motor principal es la PC del usuario (encendida en horario laboral): tarea «Bot noticias macro» del Programador de tareas → `.venv\Scripts\pythonw.exe bot\local.py` cada hora 7-22, al iniciar sesión y al desbloquear. GitHub (cron en :07) queda de respaldo: no hace nada si `ultima_corrida_pc` en state.json tiene menos de `MINUTOS_PC_ACTIVA` (90). El estado se comparte vía git (local.py hace pull/push). Secretos locales en `.env` (gitignored); registro en `logs/local.log`. El usuario descartó cron-job.org, Cloudflare y Supabase.
- Crear la tarea con Register-ScheduledTask lo bloquea el clasificador de permisos: la registra el usuario con `instalar.ps1` (también crea `.venv` y `.env` desde `.env.example`).
- Varias PC: el push de la marca `ultima_corrida_pc` hace de candado (`tomar_turno` en local.py); si otra PC subió antes en esa hora, esta no corre.
- Gemini asigna el tema de cada noticia leyendo el titular; la búsqueda que la encontró a veces no coincide.
- Gemini en tier gratuito: `gemini-3.8-flash`, luego `gemini-3.5-flash-lite` y `gemini-3.5-flash` (`gemini-2.5-flash` da 404). Si Gemini falla, el resumen se envía igual con la agenda macro.
- Saturación de Gemini (2026-10-22): desde el 21-oct `3.8-flash` da HTTP 503 «high demand» a menudo, y el 22-oct a las 8:00 fallaron ambos modelos, así que el resumen salió sin noticias. Por pedido del usuario, `preguntar_gemini` vuelve a probar la lista cada 3 min (`MINUTOS_REINTENTO_GEMINI`) si el error es 429/500/503 o timeout, hasta 40 min (`MINUTOS_MAX_GEMINI`) o hasta 1 min antes del próximo aviso/dato del calendario (`limite_gemini`, lo fija `main`), porque los datos macro tienen prioridad. Con un error de clave no reintenta; con `--sin-espera`, un solo intento. Ese día el resumen se reenvió a mano llamando a `hacer_resumen` (correr `main.py --sin-espera` sin dry-run enviaría los avisos del calendario antes de tiempo). El aviso en Telegram distingue saturación de un problema con la clave.

Python local: `.venv` (3.14). Pruebas: `bot/main.py --dry-run --sin-espera [--modo resumen|urgentes|calendario]`.
Los archivos usan CRLF en Windows (core.autocrlf=true): editar con la herramienta Edit, no con scripts que comparen texto con LF.

## Estado
- [x] Código y workflow probados en dry-run y en Actions (corridas #3 a #5 OK el 2026-10-15)
- [x] Medios confiables, bloques por tema, dato real del calendario y mensaje de dato publicado
- [x] Cron movido a :07 (2026-10-16)
- [x] `bot/local.py` + respaldo de GitHub + instalador (2026-10-16)
- [ ] Instalar en la PC personal del usuario
- [x] Tarea instalada y primera corrida desde la PC OK (resumen enviado el 2026-10-16 9:51)
- [ ] Ver el primer aviso y el primer dato real en un día con datos (la semana del 19-oct)
- [x] 1 (o 2) noticias por bloque + «Lo más comentado» con 3 historias (probado en dry-run el 2026-10-19)
- [ ] Revisar «Lo más comentado» tras unos días (umbral, calidad del fondo económico)
- [ ] Ajustar el criterio de urgentes y el volumen de mensajes tras una semana de uso
