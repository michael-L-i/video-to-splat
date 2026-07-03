"""Depth Anything 3 pose backend (experimental): feed-forward poses + point cloud on MPS.

Runs the `da3` CLI in a subprocess — DA3's torch and pycolmap's bundled OpenMP
cannot coexist in one process (libomp clash).
"""
import shutil
import sys
from pathlib import Path

import pycolmap

from ..pipeline import run_subprocess
from .sfm_common import cameras_json, write_sparse_ply

DA3_MODEL = "depth-anything/DA3-LARGE"


def run(job, work: Path, preset):
    da3_bin = Path(sys.executable).parent / "da3"
    if not da3_bin.exists():
        raise RuntimeError("DA3 backend not installed — run: uv sync --group da3")

    frames_dir = work / "frames"
    export_dir = work / "colmap_da3"
    if export_dir.exists():
        shutil.rmtree(export_dir)  # da3 prompts interactively if the dir exists

    job.update(message="estimating poses with Depth Anything 3 (MPS)", progress=0.1)
    run_subprocess(job, [
        "env", "KMP_DUPLICATE_LIB_OK=TRUE",
        str(da3_bin), "images", str(frames_dir),
        "--model-dir", DA3_MODEL,
        "--export-format", "colmap",
        "--export-dir", str(export_dir),
        "--device", "mps",
    ])

    job.update(message="arranging dataset", progress=0.8)
    recon = pycolmap.Reconstruction(export_dir)

    dataset_dir = work / "dataset"
    model_dir = dataset_dir / "sparse" / "0"
    images_dir = dataset_dir / "images"
    model_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    recon.write(model_dir)
    for src in sorted(frames_dir.glob("*.jpg")):
        shutil.copyfile(src, images_dir / src.name)

    write_sparse_ply(work / "sparse.ply", recon)

    job.update(
        progress=1.0,
        message=f"DA3 estimated {recon.num_reg_images()} camera poses",
        sparse_url=job.file_url("sparse.ply"),
        cameras=cameras_json(recon),
    )
