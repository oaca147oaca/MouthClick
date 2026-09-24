"""Launch without a visible console; keep diagnostics for the latest session."""
import os
from pathlib import Path
import runpy
import sys
import traceback


def main():
    from mouthclick_instance import acquire
    if not acquire():
        return
    folder = Path(__file__).resolve().parent
    logs = Path(os.environ.get("LOCALAPPDATA", str(folder))) / "MouthClick" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / "ultima-sesion.log"
    os.chdir(folder)
    with log_path.open("w", encoding="utf-8", buffering=1) as log:
        original = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = log
        try:
            runpy.run_path(str(folder / "mouthclick_mvp_opticalflow.py"), run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                traceback.print_exc()
                show_error(log_path)
        except Exception:
            traceback.print_exc()
            show_error(log_path)
        finally:
            sys.stdout, sys.stderr = original


def show_error(log_path):
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, f"No se pudo ejecutar MouthClick.\nRegistro: {log_path}", "MouthClick", 0x10)


if __name__ == "__main__":
    main()
