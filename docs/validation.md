# Validation in the cloud workspace

Validated on Debian 13 / x86_64, Python 3.12.14, with a 1600×1000 Xvfb display. No webcam is attached.

| Check | Outcome |
| --- | --- |
| Unit, model, worker, GUI, and isolated X11 pointer tests | 44 passed |
| Ruff checks and Git whitespace checks | Passed |
| Dependency consistency | Passed, 52 installed distributions |
| Source and saved cloud launcher: mapped window, clean close | Passed |
| Native Linux folder bundle: mapped window, clean close | Passed |
| Bundled hand and FaceMesh models: blank-frame inference | Passed in source and packaged app |
| Official iTracker checkpoint: synthetic crop inference | Passed in source and packaged app |
| L2CS-Net / GazeTR: architecture, state loading, finite forward outputs | Passed in source and packaged app using random temporary test weights |
| Official L2CS-Net / GazeTR checkpoints | Unrun: absent; Google Drive denied by current cloud network policy |
| Real webcam hand/gaze accuracy, latency, lighting variations | Unrun: hardware needed |
| Native Windows execution and camera behavior | Unrun here; separate Windows CI workflow added |
| Fresh cloud task restoration/publication | Unrun; setup/start instructions saved as a draft |

The Linux folder bundle is about 1.5 GB with optional CPU Torch/torchvision and their native dependencies. It starts without extracting a single-file archive each launch. The local Debian build has a newer glibc baseline; the Ubuntu 22.04 CI build is intended for broader Linux compatibility. Distribute the entire bundle folder. No research checkpoints are bundled into it.

CustomTkinter reports a font-cache warning on this machine's read-only home directory and falls back to vector shapes. PyAutoGUI's global X11 connections emit resource warnings at test-process exit; explicit application-owned mouse state, model instances, and camera cleanup are covered by tests. These warnings did not change test exit status.

The model contracts above do not establish pretrained gaze accuracy. Follow [model setup](models.md) to import official checkpoints and compare performance on your camera. Keep iTracker assets out of distributed bundles/shared snapshots under its research-only terms. GazeTR is noncommercial. See [usage](usage.md) for safe hardware checks.
