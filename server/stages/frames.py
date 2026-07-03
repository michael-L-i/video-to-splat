import subprocess
import sys
from pathlib import Path

from PIL import Image

from ..pipeline import run_subprocess

_SHARP_FRAMES_BIN = str(Path(sys.executable).parent / "sharp-frames")


def _ffprobe_duration(video: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _ffmpeg_fallback(job, video: Path, out_dir: Path, n_frames: int):
    duration = _ffprobe_duration(video)
    fps = max(n_frames / max(duration, 0.1), 0.1)
    run_subprocess(job, [
        "ffmpeg", "-y", "-i", str(video),
        "-vf", f"fps={fps}", "-q:v", "2",
        str(out_dir / "%05d.jpg"),
    ])


def run(job, work: Path, preset):
    video = next(work.glob("input.*"))
    out_dir = work / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)

    job.update(message="selecting sharpest frames", progress=0.05)
    # extract ~3x the target so best-n has real candidates (default 10 fps +
    # min-buffer 3 caps selection at duration*10/3 frames on short videos)
    duration = _ffprobe_duration(video)
    fps = min(30, max(10, -(-3 * preset.frames // max(int(duration), 1))))
    try:
        run_subprocess(job, [
            _SHARP_FRAMES_BIN, str(video), str(out_dir),
            "--fps", str(fps),
            "--min-buffer", "2",
            "--num-frames", str(preset.frames),
            "--format", "jpg",
            "--selection-method", "best-n",
            "--force-overwrite",
        ])
    except (subprocess.CalledProcessError, FileNotFoundError):
        job.update(message="sharp-frames failed, falling back to uniform ffmpeg extraction")
        _ffmpeg_fallback(job, video, out_dir, preset.frames)

    job.check_cancelled()

    image_files = sorted(out_dir.glob("*.jpg"))
    if not image_files:
        raise RuntimeError("no frames were extracted from the video")

    job.update(message="downscaling frames", progress=0.5)
    for path in image_files:
        with Image.open(path) as im:
            if max(im.size) > preset.max_resolution:
                im.thumbnail((preset.max_resolution, preset.max_resolution), Image.LANCZOS)
                im.save(path)

    stride = max(1, len(image_files) // 8)
    sample = [job.file_url(f"frames/{p.name}") for p in image_files[::stride][:8]]

    job.update(
        frames={"count": len(image_files), "sample": sample},
        progress=1.0,
        message=f"extracted {len(image_files)} frames",
    )
