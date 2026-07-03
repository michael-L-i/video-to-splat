from pathlib import Path

# TODO: implement the Depth Anything 3 pose backend once the `da3` dependency
# group is installed and its Python API is wired up.


def run(job, work: Path, preset):
    raise RuntimeError("DA3 backend not yet installed — run: uv sync --group da3")
