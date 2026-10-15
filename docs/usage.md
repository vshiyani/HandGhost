# Using HandGhost Studio

## Start a session

1. Open **Studio** and select **Hands** or **Eyes**. Switch modes with the camera off.
2. Select a camera index. Linux lists existing `/dev/video*` indices without opening every camera; you can also type an index. Some Linux cameras expose metadata-only devices—try another listed index if a device opens but does not supply frames.
3. Choose **Start camera**. Check the preview, frame rate, processing time, and hand/face count.
4. Practice in preview before enabling **Desktop control**. Preview does not move the pointer or click.
5. Choose **Stop camera** to release the camera. A stopped preview clears the last image.

## Hand gestures

| Action | Default pose |
| --- | --- |
| Move pointer | Right thumb + index pinch; move while holding |
| Left click / drag | Left thumb + index pinch; release to drop |
| Right click | Left thumb + middle pinch |
| Scroll | Right thumb + middle pinch; move vertically |
| Mute | Right fist, only when media gestures are enabled |

Pinch distance is relative to palm width, not camera resolution. Increase it to make activation easier. Smoothing reduces jitter at the cost of response time. Reduce pointer speed for small targets. A pose must last two consecutive frames to activate, with a wider release threshold to reduce pinch chatter. Hand loss releases held buttons immediately on the next processed frame.

Change mappings in **Preferences**. One pose can drive one action; unassign an existing mapping before reusing its pose. Unsupported swipe mappings from the original prototype are no longer offered. Media actions fire once on entering a pose, with a cooldown; enable them separately.

## Eye tracking

Choose a gaze backend in the Eyes session panel. Optional models need setup under Preferences → Gaze models; see [model setup](models.md). Stop the camera before switching. Each backend has its own calibration.

Eye mode is an experimental webcam estimate, not medical/accessibility-certified eye-tracking hardware. It is intended for coarse pointer aiming and testing. Use good front lighting and position your face close enough for both irises to be visible. Keep your camera, screen, and seating position fixed.

1. Select **Eyes**, start the camera, and verify the iris markers in the preview.
2. Choose **Calibrate gaze · 9 points**. A full-screen target appears.
3. Look at the center dot. Press Space and hold your gaze for about one second.
4. Repeat for all nine points. Retry a point if too few usable samples are captured. Press Esc to cancel at any time.
5. After calibration succeeds, enable **Desktop control** and test aiming with clicking off. Recalibrate if the pointer drifts or the fit is rejected. Changing camera index or mirroring invalidates calibration; a screen-size mismatch blocks gaze input.
6. Optionally enable **Dwell to click**. Hold your gaze in a small area until the progress bar fills. Move your gaze away to rearm; blinking alone does not rearm a click. The dwell duration is adjustable in Preferences (0.8–3 seconds). Use your physical mouse for precise clicking when gaze is too noisy.

Closed eyes or a lost face stop gaze events. Open eyes must remain visible briefly before input resumes. Blink-to-click, eye-mode dragging/right clicks, gaze scrolling, and per-monitor calibration are not implemented. A rough head-position correction is included, but significant head movement requires recalibration.

Calibration saves regression parameters, not camera images. Save files are local and may be deleted to reset calibration. Dwell and desktop control start off on each launch.

## Stop or pause input

- Toggle **Desktop control** off to keep preview while pausing input.
- Press **Esc** while the app has focus.
- Move the physical pointer to a screen corner to trigger the desktop fail-safe.
- Stop the camera or close the app to release camera resources and held buttons.

Escape is not a system-wide shortcut. Keep your normal mouse/keyboard available during testing.

## Troubleshooting

**No window:** run in a graphical session. Use `python main.py --diagnostics` for platform information. Xvfb is useful for developer smoke tests but cannot control your real desktop.

**Linux Wayland:** preview and calibration work, but full desktop input is disabled. Use an X11/Xorg session. Installing XWayland alone does not grant system-wide pointer access.

**Camera unavailable / stopped sending frames:** close other camera applications, verify privacy/device permissions, and try another index. Stop then start after reconnecting. On Windows, enable camera access for desktop apps. Do not run as root to bypass Linux permissions.

**Eyes not detected:** improve lighting, move closer, reduce glare on glasses, and ensure both eyes are visible. If calibration is inconsistent, keep your head still, look directly at each dot, and retry. Webcam eye tracking can remain unusable on some cameras; hand mode is independent.

**High CPU / low FPS:** lower the frame rate limit in Preferences. The pipeline defaults to 640×480 and uses a lite hand model. Only the selected tracking model runs. Reported processing time includes frame acquisition/inference/render preparation, not full capture-to-display latency.

**Preferences cannot save:** check write permission on the platform config directory or use `--config` with a writable file. Preview remains usable if saving fails.

**Minimal cloud desktop font warning:** CustomTkinter falls back to vector shapes if the home font directory is read-only. This does not affect model inference. A scalable Arial alias is used for legible typography on minimal X11 installations.

## Hardware validation checklist

Automated checks cover synthetic gesture transitions, calibration math, model loading, cleanup, and GUI flow. Before relying on desktop input, test with actual hardware: click/release, dragging, scrolling, camera disconnect, input pause, corner fail-safe, mode switching, and calibration under your lighting. Windows camera/desktop behavior and gaze accuracy cannot be established by Linux virtual-display tests.
