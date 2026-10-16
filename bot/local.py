#!/usr/bin/env python3
"""
Corre el bot desde la PC (Programador de tareas de Windows, tarea «Bot noticias macro»).

La PC es el motor principal mientras está encendida; GitHub Actions queda de
respaldo y no hace nada si la PC corrió hace poco (ver `pc_activa` en main.py).
Las dos comparten data/state.json a través del repositorio, así que no se
repiten mensajes.

Cada corrida:
  1. Sale sin hacer nada si es fin de semana, fuera de 7-22 h, o si la PC ya
     corrió en esta misma hora (la tarea se dispara también al iniciar sesión
     y al desbloquear la PC).
  2. Trae el estado del repositorio (git pull).
  3. Sale si hay una corrida de GitHub en curso (evita avisos duplicados).
  4. Marca la corrida en el estado y la sube, para que GitHub se quede quieto.
  5. Corre bot/main.py y sube el estado final.

Secretos: archivo .env en la raíz del proyecto (no se sube a GitHub).
Registro: logs/local.log.
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_ESTADO = RAIZ / "data" / "state.json"
ARCHIVO_LOG = RAIZ / "logs" / "local.log"
API_CORRIDAS = "https://api.github.com/repos/panchez87-ui/noticias/actions/runs?per_page=10"


def log(msg):
    ARCHIVO_LOG.parent.mkdir(exist_ok=True)
    with ARCHIVO_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(config.ZONA_LOCAL):%Y-%m-%d %H:%M:%S}] [PC] {msg}\n")


def git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def subir_estado(mensaje):
    git("add", "data/state.json")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=RAIZ,
                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode == 0:
        return
    git("commit", "-m", f"{mensaje} [skip ci]")
    try:
        git("push", "-q")
    except RuntimeError:
        # GitHub subió su propio estado entretanto: se reaplica el nuestro encima.
        git("pull", "-q", "--rebase", "-X", "theirs")
        git("push", "-q")


def cargar_env():
    archivo = RAIZ / ".env"
    if not archivo.exists():
        raise RuntimeError("falta el archivo .env con los secretos")
    for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ[clave.strip()] = valor.strip().strip('"')
    faltan = [v for v in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY") if not os.environ.get(v)]
    if faltan:
        raise RuntimeError(f"faltan en .env: {', '.join(faltan)}")


def github_corriendo():
    req = urllib.request.Request(API_CORRIDAS, headers={"User-Agent": "BotNoticiasMacro-PC"})
    with urllib.request.urlopen(req, timeout=20) as r:
        corridas = json.load(r)["workflow_runs"]
    return any(c["status"] in ("queued", "in_progress", "waiting", "pending") for c in corridas)


def main():
    ahora = datetime.now(config.ZONA_LOCAL)
    if ahora.weekday() >= 5 or not 7 <= ahora.hour <= 22:
        return

    cargar_env()
    git("pull", "-q", "--rebase", "--autostash")
    estado = json.loads(ARCHIVO_ESTADO.read_text(encoding="utf-8")) if ARCHIVO_ESTADO.exists() else {}
    ultima = estado.get("ultima_corrida_pc")
    if ultima and datetime.fromisoformat(ultima).strftime("%Y-%m-%d %H") == ahora.strftime("%Y-%m-%d %H"):
        return  # ya corrió en esta hora

    try:
        if github_corriendo():
            log("Hay una corrida de GitHub en curso; esta vez no hace nada.")
            return
    except Exception as e:
        log(f"AVISO: no se pudo consultar GitHub ({e}); se sigue.")

    estado["ultima_corrida_pc"] = ahora.isoformat()
    ARCHIVO_ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    subir_estado("estado del bot (PC)")

    log("Corriendo bot/main.py")
    python = Path(sys.executable).with_name("python.exe")  # pythonw no tiene consola para la salida
    with ARCHIVO_LOG.open("a", encoding="utf-8") as f:
        r = subprocess.run([str(python), str(RAIZ / "bot" / "main.py")], cwd=RAIZ, stdout=f,
                           stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    log(f"main.py terminó con código {r.returncode}")
    subir_estado("estado del bot (PC)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)
