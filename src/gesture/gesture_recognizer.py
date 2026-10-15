"""Palm-relative, debounced gestures independent of camera resolution and OS APIs."""

import math
import time
from dataclasses import dataclass

from src.utils.settings_manager import PRIMITIVES


@dataclass(frozen=True)
class Gesture:
    type: str
    data: object = None


class GestureRecognizer:
    PRIMITIVE_GESTURES = PRIMITIVES

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self._active = set()
        self._counts = {}
        self._held = set()
        self._move = None
        self._scroll = None
        self._last_media = -math.inf
        self._mapping = None

    def reset(self):
        releases = [Gesture(f"{action}_up") for action in sorted(self._held)]
        self._active.clear()
        self._counts.clear()
        self._held.clear()
        self._move = self._scroll = None
        self._media_active = set()
        return releases

    @staticmethod
    def _distance(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def recognize(self, all_hands_landmarks, all_hands_handedness, image, now=None):
        now = time.monotonic() if now is None else now
        settings = self.settings_manager.snapshot()
        mapping = settings["gestures"]
        events = []
        if mapping != self._mapping:
            events.extend(self.reset())
            self._mapping = mapping
        candidates, tips, visible = set(), {}, set()
        for hand, handedness in zip(all_hands_landmarks, all_hands_handedness):
            label = handedness.classification[0].label.lower()
            if label not in ("left", "right"):
                continue
            visible.add(label)
            points = hand.landmark
            palm = max(self._distance(points[5], points[17]), 0.001)
            threshold = settings["pinch_threshold"] / 100
            for pose, tip in (("index_pinch", 8), ("middle_pinch", 12)):
                primitive = f"{label}_hand_{pose}"
                release_margin = 1.35 if primitive in self._active else 1.0
                if self._distance(points[4], points[tip]) / palm < threshold * release_margin:
                    candidates.add(primitive)
            if all(
                self._distance(points[tip], points[0]) < self._distance(points[pip], points[0])
                for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))
            ):
                candidates.add(f"{label}_hand_fist")
            tips[label] = (points[8].x * image.shape[1], points[8].y * image.shape[0])

        for primitive in PRIMITIVES[1:]:
            # Immediately release on hand loss; a detected pose needs two consecutive frames.
            if primitive.split("_")[0] not in visible:
                self._active.discard(primitive)
                self._counts[primitive] = 0
            elif primitive in candidates:
                self._counts[primitive] = self._counts.get(primitive, 0) + 1
                if self._counts[primitive] >= 2:
                    self._active.add(primitive)
            else:
                self._counts[primitive] = 0
                self._active.discard(primitive)

        for action in ("left_click", "right_click"):
            active = mapping.get(action) in self._active
            if active and action not in self._held:
                events.append(Gesture(f"{action}_down"))
                self._held.add(action)
            elif not active and action in self._held:
                events.append(Gesture(f"{action}_up"))
                self._held.remove(action)

        position = self._position(mapping.get("activate_movement"), tips)
        if position is not None and self._move is not None:
            events.append(
                Gesture("move_relative", (position[0] - self._move[0], position[1] - self._move[1]))
            )
        self._move = position
        position = self._position(mapping.get("scroll"), tips)
        if position is not None and self._scroll is not None:
            delta = self._scroll - position[1]
            if abs(delta) >= 8:
                events.append(Gesture("scroll", int(delta / 8)))
                self._scroll = position[1]
        else:
            self._scroll = position[1] if position is not None else None

        media_active = {
            action
            for action in ("mute", "volume_up", "volume_down", "next_track", "prev_track")
            if mapping.get(action) in self._active
        }
        if settings["media_control_enabled"] and now - self._last_media >= 0.8:
            # Fire on entry, never repeatedly for a held pose.
            for action in sorted(media_active - getattr(self, "_media_active", set())):
                events.append(Gesture(action))
                self._last_media = now
                break
        self._media_active = media_active
        return events

    def _position(self, primitive, tips):
        if primitive not in self._active:
            return None
        return tips.get(primitive.split("_")[0])
