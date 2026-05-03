from dataclasses import dataclass


@dataclass(slots=True)
class Bbox:
    x: float
    y: float
    z: float


@dataclass(slots=True)
class BuildVolume:
    x: float
    y: float
    z: float


def fits(bbox: Bbox, build: BuildVolume, *, margin_pct: float = 5.0) -> bool:
    """Return True if `bbox` fits inside `build` after shrinking the build volume by margin_pct.

    The model can be rotated 90deg around Z, so we test both XY orientations.
    Z is never rotated (printer orientation is fixed).
    """
    factor = 1.0 - margin_pct / 100.0
    bx = build.x * factor
    by = build.y * factor
    bz = build.z * factor

    if bbox.z > bz:
        return False

    fits_natural = bbox.x <= bx and bbox.y <= by
    fits_rotated = bbox.y <= bx and bbox.x <= by
    return fits_natural or fits_rotated
