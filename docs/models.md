# Switching gaze models

Eye mode offers four independent backends. Stop the camera before changing the model. Only the selected model runs; hand mode never loads a gaze appearance network. Calibrate each model separately. Switching back restores that model's saved calibration when camera, mirroring, and screen dimensions still match.

| Model | Included / setup | Terms and limits |
| --- | --- | --- |
| MediaPipe iris | Built in; works offline | Apache 2.0; landmark geometry plus calibration |
| L2CS-Net | Optional CPU PyTorch engine, pinned upstream definition, official **ResNet50** checkpoint | MIT source; confirm the checkpoint/dataset terms for your intended use |
| GazeTR-Hybrid | Optional CPU PyTorch engine, pinned upstream definitions, official ETH-XGaze checkpoint | Upstream code is **CC BY-NC-SA 4.0**, noncommercial |
| iTracker | OpenCV Caffe inference; official deploy definition, mean images, and pretrained weights downloaded separately | Official GazeCapture release is **research-only and prohibits redistribution** |

The optional research models and weights are **not included in source control or executable data files**. Do not redistribute iTracker assets in installers, public environment snapshots, or release archives. Check upstream terms before using any optional model commercially. The installer preserves upstream licence/readme files next to local assets.

## Set up in the app

1. Select **Eyes** in Studio, then choose the model.
2. Open **Preferences → Gaze models**. Choose/apply a writable model folder if needed. It defaults to the platform's HandGhost configuration directory plus `models`; `HANDGHOST_MODELS_DIR` can override it.
3. Choose **Install selected model files**. Downloads are explicit, run off the UI thread, use HTTPS verification, and must match pinned SHA-256 hashes. iTracker's official checkpoint is available from its GitHub repository, so this installs all required iTracker files.
4. For L2CS-Net or GazeTR, obtain the official checkpoint from the links below, then choose **Import checkpoint…**. Checkpoints are loaded as weights-only state dictionaries, not serialized Python models. The app checks head keys and loads the full network strictly at startup; incompatible architectures report an error instead of silently using another model.
5. Start the camera, run nine-point calibration, and test aiming with dwell clicking off first. Save preferences to remember the folder and selected model.

L2CS/GazeTR need PyTorch and torchvision. CI builds include the optional engines. A minimal source install may need the additional command below. A minimal frozen build without PyTorch must be rebuilt with these dependencies; installing them beside a frozen executable does not add modules to its internal bundle.

## Set up from source

```sh
# CPU-only engines on Linux/Windows; use venv/Scripts/python.exe on Windows.
venv/bin/python -m pip install -r requirements-models.txt --index-url https://download.pytorch.org/whl/cpu

# iTracker: complete official research assets
venv/bin/python scripts/setup_gaze_models.py itracker

# L2CS-Net: source plus your official ResNet50 checkpoint
venv/bin/python scripts/setup_gaze_models.py l2cs --checkpoint /path/to/L2CSNet_gaze360.pkl

# GazeTR: source plus your official GazeTR-Hybrid checkpoint
venv/bin/python scripts/setup_gaze_models.py gazetr --checkpoint /path/to/weights.pt
```

Use `--directory /path/to/models` consistently if overriding the default. In the app, apply the same parent folder (the folder containing `l2cs`, `gazetr`, and `itracker`). Do not point it at an individual provider subfolder.

Official checkpoints and upstream terms:

- [L2CS-Net](https://github.com/Ahmednull/L2CS-Net), [official checkpoint folder](https://drive.google.com/drive/folders/17p6ORr-JQJcw-eYtG2WGNiuS_qVKwdWd), [MIT code licence](https://github.com/Ahmednull/L2CS-Net/blob/master/LICENSE).
- [GazeTR](https://github.com/yihuacheng/GazeTR), [official ETH-XGaze checkpoint](https://drive.google.com/file/d/1WEiKZ8Ga0foNmxM7xFabI4D5ajThWAWj/view). The README specifies CC BY-NC-SA 4.0. The adapter changes its hardcoded CUDA position tensor to use the input device, enabling CPU inference without changing the network.
- [GazeCapture / iTracker](https://github.com/CSAILVision/GazeCapture), [research licence](https://github.com/CSAILVision/GazeCapture/blob/master/LICENSE.md). Citation: Krafka et al., “Eye Tracking for Everyone,” CVPR 2016.

## Accuracy and validation

These are experimental webcam adapters. L2CS uses a 448px RGB face crop with ImageNet normalization; GazeTR uses a 224px BGR tensor divided by 255, matching the upstream reader's channel/scaling convention. iTracker uses three 224px BGR crops, official per-pixel mean images, and a 25×25 face-location grid.

The app uses MediaPipe face landmarks for face/eye crops and eye-closure gating for every backend. That differs from the upstream datasets' face detection, and GazeTR's ETH-XGaze training uses geometrically normalized imagery. This app does **not** reproduce that full camera-intrinsic/3D normalization pipeline. iTracker was trained on mobile-device images rather than desktop webcams. Calibration cannot guarantee that these domain differences disappear. Compare actual aiming error, stability, and FPS on your camera before deciding which model is better.

The adapter maps gaze outputs into bounded calibration features and adds head-position features. It retains per-model calibration, smoothing, blink/lost-face pauses, stale-frame guards, and opt-in dwell clicking. No blink-to-click. A slow appearance model may lower the FPS; only CPU inference with two Torch threads is currently configured.

Local validation includes official iTracker checkpoint inference on a synthetic image in both source and the packaged Linux app. L2CS/GazeTR architecture, weights-only reload, and forward-pass contracts were tested in source and the packaged Linux app with **random temporary test weights** because this cloud environment blocks their Google Drive checkpoints. Those tests do not establish pretrained gaze accuracy or real-checkpoint compatibility. The UI reports missing checkpoints and does not substitute MediaPipe silently.

To rerun optional adapter integration checks after explicit asset installation:

```sh
HANDGHOST_TEST_MODELS_DIR=/path/to/models venv/bin/python -m unittest tests.test_model_registry -v
```

Random test weights are created only in temporary test directories, never installed as usable models. No real webcam or Windows camera behavior was validated in the cloud environment.

For a packaged model-loading check after installation, run `HandGhost --check-gaze-model itracker --model-directory /path/to/models` (or use `l2cs`/`gazetr`). This sends synthetic crops through the selected backend and reports finite outputs; it does not measure eye-tracking accuracy.
