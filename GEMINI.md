# HandGhost development context

HandGhost Studio is a Python 3.10–3.12 desktop application with separate hand and experimental eye modes. Read README.md and docs/usage.md before changing behavior.

- `src/ui`: CustomTkinter studio, preferences, gesture guide, and nine-point eye calibration overlay. Tk widgets are accessed only on the main thread.
- `src/tracking/worker.py`: paced camera/model/input worker with one latest-frame mailbox. Never queue an unbounded video backlog. Pause/stop release input under a lock independently of camera reads.
- `src/gesture`: palm-relative pinch hysteresis, two-frame activation, drag release, scroll, and opt-in media events.
- `src/eye/model_registry.py`, `appearance_models.py`, and `model_setup.py`: selectable MediaPipe/L2CS/GazeTR/iTracker backends. Optional upstream code/assets are checksum-pinned, installed outside the bundle, and carry separate licences. GazeTR is noncommercial; official iTracker assets prohibit redistribution. Never install random test weights as usable models.
- `src/eye`: bundled FaceMesh iris landmarks, regularized calibration, gaze filtering, eye-closure gating, and optional dwell. Webcam gaze is approximate; don't claim measured accuracy from synthetic tests.
- `src/interaction`: lazy PyAutoGUI backend. X11 supports desktop control; Wayland is preview-only. Keep fail-safe enabled except when releasing owned mouse buttons. Escape pauses only while the window has focus.
- `src/utils/settings_manager.py`: validated snapshots and atomic per-user JSON saves. No startup writes to the checkout. Desktop control and dwell clicks start off every launch.

Install `requirements.txt` in a virtual environment. MediaPipe 0.10.21/OpenCV 4.11/NumPy <2 are compatibility pins for Solutions APIs. Run `python -m unittest discover -v`; UI tests need a graphical display. Linux CI uses Xvfb and HANDGHOST_TEST_DESKTOP=1 to test actual pointer input safely in an isolated display. Never opt into the pointer integration test on a user's real desktop.

Use `python main.py --diagnostics` for capabilities and `--check-models` for bundled model inference. Package using `python -m PyInstaller --noconfirm HandGhost.spec` on each target OS. CI builds Windows .exe and Linux ELF separately; no cross-compilation. Check packaged Linux GUI with `scripts/smoke_desktop.py --executable dist/HandGhost/HandGhost` under Xvfb. Hardware webcam/gaze accuracy and native Windows behavior still need manual validation.
