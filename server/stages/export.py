import re
import shutil
import subprocess
from pathlib import Path

from ..pipeline import run_subprocess

_NPX_CMD = ["npx", "--yes", "@playcanvas/splat-transform"]


def _step_of(p: Path) -> int:
    m = re.search(r"export_(\d+)\.ply", p.name)
    return int(m.group(1)) if m else -1


def _npx_available() -> bool:
    try:
        subprocess.run(_NPX_CMD + ["--version"], capture_output=True, text=True, timeout=30, check=True)
        return True
    except Exception:
        return False


def run(job, work: Path, preset):
    checkpoints = sorted((work / "checkpoints").glob("export_*.ply"), key=_step_of)
    if not checkpoints:
        raise RuntimeError("no trained checkpoint to export")
    checkpoint = checkpoints[-1]

    exports_dir = work / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    scene_ply = exports_dir / "scene.ply"
    shutil.copyfile(checkpoint, scene_ply)

    job.update(message="exporting scene", progress=0.3)

    if _npx_available():
        for name in ("scene.ply", "scene.spz", "scene.sog"):
            out_path = exports_dir / name
            try:
                run_subprocess(job, _NPX_CMD + [
                    "-w", str(checkpoint), "--filter-nan", str(out_path),
                ])
            except Exception:
                job.update(message=f"splat-transform failed for {name}, skipping")

    job.update(message="collecting artifacts", progress=0.9)

    artifacts = [
        {"name": p.name, "url": job.file_url(f"exports/{p.name}"), "bytes": p.stat().st_size}
        for p in sorted(exports_dir.iterdir())
    ]
    job.update(artifacts=artifacts, progress=1.0, message="export complete")
