# Bot macro y noticias → Telegram

Corre gratis en GitHub Actions, cada hora de 7:00 a 22:00 (hora de Ecuador), de lunes a viernes.

| Qué | Cuándo |
|---|---|
| ⏰ Aviso de dato macro de EE. UU. (importancia alta + subsidios, PMI preliminares y otros extras), con estimado y anterior | 10 min antes de cada publicación |
| 📊 Dato real publicado, comparado con el estimado (▲ / ▼ / =) | ~3 min después de cada publicación (o en la corrida siguiente) |
| ☀️ Resumen: agenda macro del día + las ~8 noticias más importantes (el lunes incluye el fin de semana) | 8:00 |
| 🚨 Noticia urgente | Solo si es sumamente importante; si no, silencio |

Temas: petróleo, gas natural, centros de datos, IA, oro, maíz, litio, dólar y Fed/tasas.

- **Calendario:** TradingView (gratuito, incluye el dato real publicado); si falla, ForexFactory (sin dato real). Investing.com bloquea los accesos automáticos (error 403).
- **Noticias:** Google News por tema, más feeds de la Fed, OilPrice, CNBC Energía y DatacenterDynamics.
- **Filtro y resúmenes:** Google Gemini, tier gratuito (`gemini-3.8-flash`; si falla, usa `gemini-3.5-flash-lite`).

Todo lo ajustable (temas, búsquedas, indicadores extra, criterio de "urgente", modelos) está en [`bot/config.py`](bot/config.py).

## Puesta en marcha

1. **Clave de Gemini (gratis, sin tarjeta):** entra en https://aistudio.google.com/apikey y crea una API key.
2. **Repositorio:** crea en GitHub un repositorio vacío (por ejemplo, `bot-noticias-macro`) y sube esta carpeta.
3. **Secrets:** en *Settings → Secrets and variables → Actions*, crea `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` y `GEMINI_API_KEY`.
4. **Prueba:** en *Actions → Bot macro y noticias → Run workflow*, con modo `resumen`.

## Minutos de GitHub Actions

Cada corrida dura aproximadamente 1 minuto. Si hay un dato macro antes de la siguiente hora, la corrida se queda esperando hasta el aviso (hasta 75 minutos). Con un repositorio **público**, los minutos son ilimitados. Con uno **privado**, el plan gratuito da 2000 minutos al mes, y en una semana con muchos datos te puedes acercar a ese límite.

## Pruebas locales

```bash
.venv/Scripts/python.exe bot/main.py --dry-run --modo resumen --sin-espera
```

`--dry-run` imprime los mensajes en lugar de enviarlos y no guarda estado. Sin `GEMINI_API_KEY`, el resumen muestra los titulares sin filtrar.

## Correr desde la PC (motor principal)

GitHub retrasa o se salta muchas corridas programadas, así que en horario laboral el bot corre desde la PC con el Programador de tareas de Windows (`bot/local.py`). GitHub queda de respaldo para cuando la PC está apagada: si la PC corrió hace menos de 90 minutos, sus corridas programadas no hacen nada. Las dos comparten `data/state.json` vía git, así que no se repiten mensajes.

Instalación (una sola vez):
1. Completar `.env` en la raíz (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`). No se sube al repo.
2. `powershell -ExecutionPolicy Bypass -File instalar_tarea.ps1`

La tarea corre cada hora de 7:00 a 22:00, al iniciar sesión y al desbloquear la PC; `local.py` sale sin hacer nada los fines de semana, fuera de horario o si ya corrió en esa hora. Registro: `logs/local.log`.

## Limitaciones

- GitHub puede retrasar las corridas programadas o saltárselas. Mientras la PC esté apagada, los avisos dependen de él.
- El calendario de TradingView no es una API oficial: si deja de funcionar, el bot pasa solo a ForexFactory (sin dato real).
- GitHub desactiva los workflows programados tras 60 días sin actividad. Los commits de estado que hace el propio bot cuentan como actividad.
