"""
IoU-Based Multi-Object Tracker — Lightweight ByteTrack-inspired tracker.
Handles occlusions and re-identification without extra dependencies.
"""
import numpy as np
from collections import defaultdict


class Track:
    """Single tracked object."""
    _id_counter = 0

    def __init__(self, bbox, class_id, confidence):
        Track._id_counter += 1
        self.track_id = Track._id_counter
        self.bbox = np.array(bbox, dtype=float)    # [x1, y1, x2, y2]
        self.class_id = class_id
        self.confidence = confidence
        self.age = 0               # Frames since creation
        self.hits = 1              # Consecutive hits
        self.misses = 0            # Consecutive misses
        self.history = [self.centroid]  # centroid history for speed
        self.is_confirmed = False
        self.velocity = np.array([0.0, 0.0])

    @property
    def centroid(self):
        return np.array([
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        ])

    def predict(self):
        """Simple linear motion prediction."""
        self.bbox[:2] += self.velocity
        self.bbox[2:] += self.velocity
        self.age += 1

    def update(self, bbox, confidence):
        old_center = self.centroid
        self.bbox = np.array(bbox, dtype=float)
        new_center = self.centroid
        self.velocity = 0.7 * self.velocity + 0.3 * (new_center - old_center)
        self.confidence = confidence
        self.hits += 1
        self.misses = 0
        self.history.append(new_center.copy())
        if len(self.history) > 60:
            self.history = self.history[-60:]
        if self.hits >= 3:
            self.is_confirmed = True

    def mark_missed(self):
        self.misses += 1
        self.hits = 0


class IOUTracker:
    """
    IoU-based multi-object tracker inspired by ByteTrack.
    Two-stage matching: high-confidence first, then low-confidence.
    """

    def __init__(self, iou_threshold=0.3, max_age=30, min_hits=3,
                 high_conf=0.5, low_conf=0.1):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.high_conf = high_conf
        self.low_conf = low_conf
        self.tracks = []
        self.frame_count = 0

    def update(self, detections):
        """
        Update tracker with new detections.

        Args:
            detections: list of dicts with keys: bbox, class_id, confidence

        Returns:
            list of active tracks
        """
        self.frame_count += 1

        # Predict positions
        for t in self.tracks:
            t.predict()

        if not detections:
            for t in self.tracks:
                t.mark_missed()
            self.tracks = [t for t in self.tracks if t.misses <= self.max_age]
            return self._get_active()

        # Split detections into high and low confidence
        high_dets = [d for d in detections if d["confidence"] >= self.high_conf]
        low_dets = [d for d in detections if self.low_conf <= d["confidence"] < self.high_conf]

        # Stage 1: Match high-confidence detections to all tracks
        unmatched_tracks = list(range(len(self.tracks)))
        unmatched_dets_high = list(range(len(high_dets)))

        if self.tracks and high_dets:
            iou_matrix = self._compute_iou_matrix(
                [self.tracks[i].bbox for i in unmatched_tracks],
                [high_dets[j]["bbox"] for j in unmatched_dets_high],
            )
            matched_t, matched_d = self._hungarian_match(iou_matrix)

            newly_matched_tracks = set()
            newly_matched_dets = set()
            for ti, di in zip(matched_t, matched_d):
                if iou_matrix[ti, di] >= self.iou_threshold:
                    track_idx = unmatched_tracks[ti]
                    det = high_dets[unmatched_dets_high[di]]
                    self.tracks[track_idx].update(det["bbox"], det["confidence"])
                    newly_matched_tracks.add(ti)
                    newly_matched_dets.add(di)

            unmatched_tracks = [unmatched_tracks[i] for i in range(len(unmatched_tracks)) if i not in newly_matched_tracks]
            unmatched_dets_high = [unmatched_dets_high[i] for i in range(len(unmatched_dets_high)) if i not in newly_matched_dets]

        # Stage 2: Match low-confidence detections to remaining tracks
        if unmatched_tracks and low_dets:
            iou_matrix = self._compute_iou_matrix(
                [self.tracks[i].bbox for i in unmatched_tracks],
                [d["bbox"] for d in low_dets],
            )
            matched_t, matched_d = self._hungarian_match(iou_matrix)
            newly_matched = set()
            for ti, di in zip(matched_t, matched_d):
                if iou_matrix[ti, di] >= self.iou_threshold:
                    track_idx = unmatched_tracks[ti]
                    self.tracks[track_idx].update(low_dets[di]["bbox"], low_dets[di]["confidence"])
                    newly_matched.add(ti)

            unmatched_tracks = [unmatched_tracks[i] for i in range(len(unmatched_tracks)) if i not in newly_matched]

        # Mark unmatched tracks as missed
        for idx in unmatched_tracks:
            self.tracks[idx].mark_missed()

        # Create new tracks for unmatched high-confidence detections
        for di in unmatched_dets_high:
            det = high_dets[di]
            self.tracks.append(Track(det["bbox"], det["class_id"], det["confidence"]))

        # Remove dead tracks
        self.tracks = [t for t in self.tracks if t.misses <= self.max_age]

        return self._get_active()

    def _get_active(self):
        return [t for t in self.tracks if t.is_confirmed and t.misses == 0]

    @staticmethod
    def _iou(boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        inter = max(0, xB - xA) * max(0, yB - yA)
        areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        union = areaA + areaB - inter
        return inter / union if union > 0 else 0

    def _compute_iou_matrix(self, boxes_a, boxes_b):
        m, n = len(boxes_a), len(boxes_b)
        matrix = np.zeros((m, n))
        for i in range(m):
            for j in range(n):
                matrix[i, j] = self._iou(boxes_a[i], boxes_b[j])
        return matrix

    @staticmethod
    def _hungarian_match(cost_matrix):
        """Greedy matching (fast approximation of Hungarian algorithm)."""
        m, n = cost_matrix.shape
        matched_rows, matched_cols = [], []
        used_rows, used_cols = set(), set()

        # Sort all pairs by IoU descending
        pairs = []
        for i in range(m):
            for j in range(n):
                pairs.append((cost_matrix[i, j], i, j))
        pairs.sort(reverse=True)

        for score, i, j in pairs:
            if i not in used_rows and j not in used_cols and score > 0:
                matched_rows.append(i)
                matched_cols.append(j)
                used_rows.add(i)
                used_cols.add(j)

        return matched_rows, matched_cols

    def reset(self):
        self.tracks = []
        self.frame_count = 0
        Track._id_counter = 0
