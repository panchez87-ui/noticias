# Bot macro y noticias → Telegram

Reemplaza a las dos versiones anteriores (`Documents/telegram-news-bot`, de palabras clave, y `Downloads/news-digest-bot.zip`), que no se usan.

Requisitos del usuario (2026-10-15):
- Prioridad 1: calendario macro de EE. UU., solo impacto alto, más subsidios y PMI preliminares; aviso 10 minutos antes con el estimado y el anterior.
- Resumen a las 8:00; el lunes incluye el fin de semana.
- Fuera del resumen, solo noticias sumamente importantes; si no hay, silencio.
- Corre cada hora de 7 a 22 h (Ecuador), de lunes a viernes. Costo $0.

Decisiones:
- Investing.com da 403 (bloquea bots), así que se usa el JSON de ForexFactory.
- Las noticias vienen de Google News RSS (`when:1d/3d/3h`) más feeds directos.
- Gemini en tier gratuito: `gemini-3.8-flash` y, como respaldo, `gemini-3.5-flash-lite` (verificado el 2026-10-15).

Python local: `.venv` (3.14). Pruebas: `bot/main.py --dry-run --sin-espera [--modo resumen|urgentes]`.

## Estado
- [x] Código y workflow, probados en dry-run (resumen, urgentes, espera del calendario, Gemini simulado)
- [x] Repo github.com/panchez87-ui/noticias con los 3 secrets; corrida #3 OK el 2026-10-15 (bot @Alertas_wti_bot, renombrado «Noticias»)
- [ ] Primera corrida real y ajuste del criterio de urgentes / del volumen de mensajes
