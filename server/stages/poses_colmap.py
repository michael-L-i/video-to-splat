from pathlib import Path

import pycolmap

from .sfm_common import cameras_json, write_sparse_ply


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
        # SIMPLE_RADIAL: fx=fy + one distortion param. Richer models (OPENCV)
        # overfit garbage intrinsics when the init pair is forward-dominated
        reader_options=pycolmap.ImageReaderOptions(camera_model="SIMPLE_RADIAL"),
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
    # video walkthroughs are forward-motion dominated: defaults (16° init
    # triangulation angle, forward-motion cap) reject every init pair
    opts = pycolmap.IncrementalPipelineOptions()
    opts.mapper.init_min_tri_angle = 4.0
    opts.mapper.init_max_forward_motion = 1.0
    opts.mapper.abs_pose_min_num_inliers = 20
    reconstructions = pycolmap.incremental_mapping(
        database_path=db_path, image_path=frames_dir, output_path=sparse_dir,
        options=opts,
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

    write_sparse_ply(work / "sparse.ply", best)
    cameras = cameras_json(best)

    job.update(
        progress=1.0,
        message=f"registered {registered}/{n_frames} frames",
        sparse_url=job.file_url("sparse.ply"),
        cameras=cameras,
    )
