"""X11 package smoke test: require a mapped app window and a clean close."""

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from Xlib import X, display, protocol


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", help="Packaged executable to test instead of source")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    command = (
        [str(Path(args.executable).resolve())]
        if args.executable
        else [sys.executable, str(root / "main.py")]
    )
    with tempfile.TemporaryDirectory() as temporary:
        connection = display.Display()
        process = subprocess.Popen(
            command + ["--config", str(Path(temporary) / "settings.json")], cwd=root
        )
        try:
            deadline = time.monotonic() + 45
            window = None
            while time.monotonic() < deadline and process.poll() is None:
                for child in connection.screen().root.query_tree().children:
                    if child.get_attributes().map_state == X.IsViewable and "HandGhost" in (
                        child.get_wm_name() or ""
                    ):
                        window = child
                        break
                if window is not None:
                    break
                time.sleep(0.1)
            if window is None:
                raise RuntimeError(f"HandGhost did not map a window (exit={process.poll()})")
            delete = connection.intern_atom("WM_DELETE_WINDOW")
            protocols = connection.intern_atom("WM_PROTOCOLS")
            window.send_event(
                protocol.event.ClientMessage(
                    window=window,
                    client_type=protocols,
                    data=(32, [delete, X.CurrentTime, 0, 0, 0]),
                ),
                event_mask=0,
            )
            connection.flush()
            if process.wait(timeout=10) != 0:
                raise RuntimeError("HandGhost exited with an error")
            print("PASS: HandGhost opened a desktop window and closed cleanly")
        finally:
            connection.close()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
