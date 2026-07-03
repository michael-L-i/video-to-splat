"""Helpers shared by the pose backends: viewer artifacts from a pycolmap Reconstruction."""
import random
from pathlib import Path

MAX_VIEWER_POINTS = 200_000


def write_sparse_ply(path: Path, recon) -> None:
    points = list(recon.points3D.values())
    if len(points) > MAX_VIEWER_POINTS:
        points = random.sample(points, MAX_VIEWER_POINTS)
    with open(path, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for p in points:
            x, y, z = p.xyz
            r, g, b = p.color
            f.write(f"{x} {y} {z} {int(r)} {int(g)} {int(b)}\n")


def cameras_json(recon) -> list[dict]:
    cameras = []
    for image in recon.images.values():
        world_from_cam = image.cam_from_world().inverse()
        qx, qy, qz, qw = world_from_cam.rotation.quat
        cameras.append({
            "position": world_from_cam.translation.tolist(),
            "rotation": [qw, qx, qy, qz],
        })
    return cameras
