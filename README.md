# video-to-splat

Turn a video into a 3D Gaussian Splat — fully locally on Apple Silicon — and watch the world build itself live in your browser. Downloads as `.ply` (plus `.spz` / `.sog` when available).

## How it works

```
video ──▶ sharp frames ──▶ camera poses ──▶ splat training ──▶ cleanup/export
          (ffmpeg +        (COLMAP, or       (Brush: Metal-      (splat-transform:
           sharp-frames)    Depth Anything 3  native 3DGS w/      floater removal,
                            on MPS)           MCMC + mip AA)      .ply/.spz/.sog)
```

- **Poses**: [COLMAP](https://colmap.github.io) (`pycolmap`) with sequential matching + loop detection — best quality. Optional experimental backend: [Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3) running on Apple's MPS — much faster, slightly lower fidelity.
- **Training**: [Brush](https://github.com/ArthurBrussee/brush) — a Rust/Metal Gaussian-splat trainer that matches CUDA gsplat quality (MCMC densification, Mip-Splatting antialiasing, optional LPIPS loss). It exports `.ply` checkpoints throughout training, which the UI streams into a live [Spark](https://sparkjs.dev) viewer — you watch the scene sharpen from fog into a world.
- **Everything runs on your Mac.** No cloud, no CUDA.

## Quickstart

```bash
./setup.sh        # installs ffmpeg/uv if missing, syncs Python env, fetches/builds Brush
./run.sh          # serves http://127.0.0.1:8000
```

Upload a video, pick a preset, watch it build. Presets:

| Preset  | Frames | Steps | Approx. time (M-series Pro) |
|---------|--------|-------|------------------------------|
| Preview | 100    | 10k   | ~20–30 min                   |
| High    | 200    | 30k   | ~2–3 h                       |
| Max     | 250    | 45k   | ~4 h                         |

## Capture tips (quality lives and dies here)

- Move **slowly** in an orbit/arc with lots of overlap; end near where you started (loop closure).
- Lock exposure/white balance if you can; 4K 60 fps gives the frame picker more sharp frames.
- Avoid moving subjects, whip pans, and textureless walls/sky-only shots.

## Notes

- Optional DA3 pose backend: `uv sync --group da3` (Python 3.12 venv, installs PyTorch). Uses `depth-anything/DA3-LARGE` by default; override with `DA3_MODEL=depth-anything/DA3-SMALL ./run.sh` for speed.
- Optional `.spz`/`.sog` export + floater cleanup uses `npx @playcanvas/splat-transform` (needs Node).
- Why not LingBot-World? It's an image→video *world generator* (28B params, CUDA-only, no 3D output) — the wrong tool for video→3D reconstruction, and it can't run on a Mac. This project uses the reconstruction stack that modern world-model papers themselves use for geometry.

## Layout

`server/` FastAPI + pipeline stages · `web/` vanilla-JS UI + Spark viewer · `vendor/` Brush binary + viewer libs · `jobs/` per-run work dirs (gitignored) · `docs/api.md` API contract
