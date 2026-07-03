from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    frames: int
    max_resolution: int
    total_steps: int
    growth_stop: int
    max_splats: int
    export_every: int
    lpips_weight: float = 0.0


PRESETS = {
    "preview": Preset(
        frames=100,
        max_resolution=1536,
        total_steps=10_000,
        growth_stop=6_000,
        max_splats=1_500_000,
        export_every=500,
    ),
    "high": Preset(
        frames=200,
        max_resolution=2048,
        total_steps=30_000,
        growth_stop=15_000,
        max_splats=4_000_000,
        export_every=1000,
    ),
    "max": Preset(
        frames=250,
        max_resolution=2560,
        total_steps=45_000,
        growth_stop=25_000,
        max_splats=6_000_000,
        export_every=1000,
        lpips_weight=0.25,
    ),
}

DEFAULT_PRESET = "high"
