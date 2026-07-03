from pathlib import Path

import pycolmap


def _write_sparse_ply(path: Path, recon: "pycolmap.Reconstruction"):
    points = recon.points3D
    with open(path, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for p in points.values():
            x, y, z = p.xyz
            r, g, b = p.color
            f.write(f"{x} {y} {z} {int(r)} {int(g)} {int(b)}\n")


def run(job, work: Path, preset):
    frames_dir = work / "frames"
    n_frames = len(list(frames_dir.glob("*.jpg")))

    colmap_dir = work / "colmap"
    colmap_dir.mkdir(parents=True, exist_ok=True)
    db_path = colmap_dir / "database.db"

    job.update(message="extracting features", progress=0.05)
    pycolmap.extract_features(
        database_path=db_path,
        image_path=frames_dir,
        camera_mode=pycolmap.CameraMode.SINGLE,
        reader_options=pycolmap.ImageReaderOptions(camera_model="OPENCV"),
        extraction_options=pycolmap.FeatureExtractionOptions(
            sift=pycolmap.SiftExtractionOptions(
                estimate_affine_shape=True,
                domain_size_pooling=True,
            ),
        ),
    )
    job.check_cancelled()

    job.update(progress=0.2, message="matching features")
    try:
        pycolmap.match_sequential(
            database_path=db_path,
            pairing_options=pycolmap.SequentialPairingOptions(overlap=20, loop_detection=True),
        )
    except Exception:
        job.update(message="loop detection unavailable, retrying without it")
        pycolmap.match_sequential(
            database_path=db_path,
            pairing_options=pycolmap.SequentialPairingOptions(overlap=20, loop_detection=False),
        )
    job.check_cancelled()

    job.update(progress=0.5, message="running incremental mapping")
    sparse_dir = colmap_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    reconstructions = pycolmap.incremental_mapping(
        database_path=db_path, image_path=frames_dir, output_path=sparse_dir,
    )
    if not reconstructions:
        raise RuntimeError(
            "COLMAP could not reconstruct any camera poses — "
            "recapture the scene with more overlap between frames"
        )

    best = max(reconstructions.values(), key=lambda r: r.num_reg_images())
    registered = best.num_reg_images()
    if n_frames and registered / n_frames < 0.3:
        raise RuntimeError(
            f"only {registered}/{n_frames} frames registered — "
            "recapture the scene with more overlap and steadier motion"
        )
    job.check_cancelled()

    model_dir = sparse_dir / "0"
    model_dir.mkdir(parents=True, exist_ok=True)
    best.write(model_dir)

    job.update(progress=0.9, message="undistorting images")
    dataset_dir = work / "dataset"
    pycolmap.undistort_images(
        output_path=dataset_dir,
        input_path=model_dir,
        image_path=frames_dir,
        output_type="COLMAP",
    )

    _write_sparse_ply(work / "sparse.ply", best)

    cameras = []
    for image in best.images.values():
        world_from_cam = image.cam_from_world().inverse()
        qx, qy, qz, qw = world_from_cam.rotation.quat
        cameras.append({
            "position": world_from_cam.translation.tolist(),
            "rotation": [qw, qx, qy, qz],
        })

    job.update(
        progress=1.0,
        message=f"registered {registered}/{n_frames} frames",
        sparse_url=job.file_url("sparse.ply"),
        cameras=cameras,
    )
