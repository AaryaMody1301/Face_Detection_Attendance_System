"""Benchmark the local YuNet + MiniFAS + SFace camera pipeline."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from src.core.camera import ResilientCamera
from src.core.face_engine import DEFAULT_GALLERY_PATH, FaceEngine
from src.core.liveness import MiniFASLiveness, TemporalLivenessGate, recognize_faces_guarded


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark local face attendance inference")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index")
    parser.add_argument("--frames", type=int, default=120, help="Measured frames")
    parser.add_argument("--warmup", type=int, default=10, help="Warm-up frames")
    parser.add_argument(
        "--gallery",
        type=Path,
        default=DEFAULT_GALLERY_PATH,
        help="Optional SFace gallery path",
    )
    args = parser.parse_args()

    engine = FaceEngine()
    liveness = MiniFASLiveness()
    gate = TemporalLivenessGate()
    camera = ResilientCamera(args.camera)

    if args.gallery.is_file():
        engine.load_model(args.gallery)
    engine.ensure_models()
    liveness.ensure_models()

    if not camera.open():
        raise SystemExit(f"Could not open camera {args.camera}")

    timings = []
    faces_seen = 0
    measured = 0
    total_target = max(1, args.warmup) + max(1, args.frames)

    try:
        for index in range(total_target):
            ok, frame = camera.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue

            started = time.perf_counter()
            results = recognize_faces_guarded(engine, frame, liveness, gate)
            elapsed = time.perf_counter() - started
            faces_seen += len(results)

            if index >= args.warmup:
                timings.append(elapsed)
                measured += 1
                if measured >= args.frames:
                    break
    finally:
        camera.release()
        gate.reset()
        liveness.cleanup()
        engine.cleanup()

    if not timings:
        raise SystemExit("No frames were measured")

    average = statistics.fmean(timings)
    ordered = sorted(timings)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    report = {
        "frames": len(timings),
        "faces_seen": faces_seen,
        "average_pipeline_ms": round(average * 1000, 2),
        "p95_pipeline_ms": round(p95 * 1000, 2),
        "pipeline_fps": round(1.0 / average, 2) if average > 0 else 0.0,
        "camera_reconnects": camera.reconnects,
        "camera_read_failures": camera.read_failures,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
