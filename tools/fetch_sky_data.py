"""Fetch the real sky data the course bundles (S24, E15).

    python tools/fetch_sky_data.py            # download, process, write into cosmos/data/external
    python tools/fetch_sky_data.py --check    # only say what would be downloaded

Two public data sets, both free to redistribute:

* the **WMAP 9-year ILC map** — the cosmic microwave background as NASA's WMAP
  team cleaned it, plus the KQ85 analysis mask that marks where the Galaxy is too
  bright to trust. 25 MB and 3 MB of HEALPix FITS, resampled here onto a
  longitude–latitude grid so the app needs no HEALPix library at run time.
* an **SDSS galaxy slice** — spectroscopic redshifts in the equatorial strip that
  produced the famous cone diagrams, fetched from SkyServer as CSV.

The heavy files are downloaded to ``build/skydata`` and are not committed; only the
small processed results go into the repository. Run this once after cloning if you
want to rebuild them — the app ships with the results already.

Requires astropy (``pip install -r requirements-dev.txt``); the app itself does not.
"""

from __future__ import annotations

import argparse
import ssl
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "build" / "skydata"
TARGET = ROOT / "cosmos" / "data" / "external"

WMAP_MAP = ("https://lambda.gsfc.nasa.gov/data/map/dr5/dfp/ilc/wmap_ilc_9yr_v5.fits",
            "wmap_ilc_9yr_v5.fits")
WMAP_MASK = ("https://lambda.gsfc.nasa.gov/data/map/dr5/ancillary/masks/"
             "wmap_temperature_kq85_analysis_mask_r9_9yr_v5.fits",
             "wmap_kq85_mask_9yr_v5.fits")

# The equatorial strip that made the SDSS cone diagrams: |dec| < 1.5°, 120° < RA < 250°.
SDSS_QUERY = """
SELECT s.ra, s.dec, s.z, p.petroMag_r
FROM SpecObj AS s JOIN PhotoObj AS p ON s.bestObjID = p.objID
WHERE s.class = 'GALAXY' AND s.zWarning = 0
  AND s.z BETWEEN 0.005 AND 0.15
  AND s.dec BETWEEN -1.5 AND 1.5
  AND s.ra BETWEEN 120 AND 250
"""
SDSS_URL = "https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch"

GRID_LON, GRID_LAT = 1024, 512          # about a third of a degree; plenty for a teaching viewer


# ---------------------------------------------------------------- downloading
def download(url: str, name: str) -> Path:
    """Fetch a file into the cache, preferring urllib and falling back to curl.

    Some machines sit behind a TLS-inspecting proxy whose certificate Python does
    not trust but the system does, and curl uses the system store.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / name
    if target.exists() and target.stat().st_size > 0:
        print(f"  cached  {name} ({target.stat().st_size / 1e6:.1f} MB)")
        return target
    print(f"  fetching {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "Cosmos-course/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            target.write_bytes(response.read())
    except (urllib.error.URLError, ssl.SSLError) as error:
        print(f"  urllib could not: {error}. Trying curl.")
        subprocess.run(["curl", "-fsSL", "--max-time", "600", "-o", str(target), url], check=True)
    print(f"  saved   {name} ({target.stat().st_size / 1e6:.1f} MB)")
    return target


def fetch_text(url: str, params: dict, name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / name
    if target.exists() and target.stat().st_size > 0:
        print(f"  cached  {name} ({target.stat().st_size / 1e6:.1f} MB)")
        return target
    full = url + "?" + urllib.parse.urlencode(params)
    print(f"  querying {url}")
    try:
        request = urllib.request.Request(full, headers={"User-Agent": "Cosmos-course/1.0"})
        with urllib.request.urlopen(request, timeout=600) as response:
            target.write_bytes(response.read())
    except (urllib.error.URLError, ssl.SSLError) as error:
        print(f"  urllib could not: {error}. Trying curl.")
        subprocess.run(["curl", "-fsSL", "--max-time", "900", "-o", str(target), full], check=True)
    print(f"  saved   {name} ({target.stat().st_size / 1e6:.1f} MB)")
    return target


# ------------------------------------------------------- HEALPix to a lat-lon grid
def healpix_ring_angles(nside: int) -> tuple[np.ndarray, np.ndarray]:
    """Colatitude and longitude of every RING-ordered HEALPix pixel, in radians.

    Straight from Górski et al. 2005: the sphere is twelve equal-area diamonds, and
    the ring scheme walks them from the north pole down in rings of constant
    colatitude — increasing in the polar caps, constant across the equatorial belt.
    """
    npix = 12 * nside * nside
    pixels = np.arange(npix)
    theta = np.empty(npix)
    phi = np.empty(npix)

    ncap = 2 * nside * (nside - 1)                      # pixels in the north polar cap
    # --- north cap
    north = pixels[:ncap]
    ring = (1 + np.sqrt(1 + 2 * north)).astype(np.int64) // 2      # 1-based ring index
    index = north - 2 * ring * (ring - 1)
    theta[:ncap] = np.arccos(1.0 - ring**2 / (3.0 * nside * nside))
    phi[:ncap] = (index + 0.5) * (np.pi / 2) / ring

    # --- equatorial belt
    belt = pixels[ncap:npix - ncap]
    offset = belt - ncap
    ring = offset // (4 * nside) + nside                            # 1-based, from the pole
    index = offset % (4 * nside)
    shift = (ring - nside + 1) % 2                                  # rings alternate by half a pixel
    theta[ncap:npix - ncap] = np.arccos((2 * nside - ring) * 2.0 / (3.0 * nside))
    phi[ncap:npix - ncap] = (index + shift / 2) * (np.pi / 2) / nside

    # --- south cap, the mirror of the north
    south = pixels[npix - ncap:]
    flipped = npix - 1 - south
    ring = (1 + np.sqrt(1 + 2 * flipped)).astype(np.int64) // 2
    index = flipped - 2 * ring * (ring - 1)
    theta[npix - ncap:] = np.pi - np.arccos(1.0 - ring**2 / (3.0 * nside * nside))
    phi[npix - ncap:] = (index + 0.5) * (np.pi / 2) / ring
    return theta, phi


# The twelve base faces, as Górski et al. 2005 number them: which ring each face's
# north corner sits on, and where it starts in longitude.
_FACE_RING = np.array([2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4])
_FACE_PHI = np.array([1, 3, 5, 7, 0, 2, 4, 6, 1, 3, 5, 7])


def _deinterleave(pixels: np.ndarray, order: int) -> tuple[np.ndarray, np.ndarray]:
    """Split a NESTED within-face index into its two interleaved coordinates."""
    x = np.zeros_like(pixels)
    y = np.zeros_like(pixels)
    for bit in range(order):
        x |= ((pixels >> (2 * bit)) & 1) << bit
        y |= ((pixels >> (2 * bit + 1)) & 1) << bit
    return x, y


def healpix_nested_angles(nside: int) -> tuple[np.ndarray, np.ndarray]:
    """Colatitude and longitude of every NESTED-ordered HEALPix pixel, in radians.

    A NESTED index says which of the twelve faces a pixel is on and, in the
    remaining bits, where on that face — the two coordinates interleaved bit by bit,
    which is what makes the scheme so good at finding a pixel's neighbours.
    """
    order = int(round(np.log2(nside)))
    if 2 ** order != nside:
        raise ValueError("NESTED ordering needs nside to be a power of two")
    npix = 12 * nside * nside
    pixels = np.arange(npix, dtype=np.int64)
    face = pixels >> (2 * order)
    ix, iy = _deinterleave(pixels & (nside * nside - 1), order)

    ring = _FACE_RING[face] * nside - (ix + iy) - 1          # counted from the north pole
    within = ix - iy                                         # position across the face

    z = np.empty(npix)
    nr = np.empty(npix, dtype=np.int64)                      # pixels per quadrant on this ring
    shift = np.zeros(npix, dtype=np.int64)                   # rings alternate by half a pixel

    north = ring < nside
    nr[north] = ring[north]
    z[north] = 1.0 - nr[north] ** 2 / (3.0 * nside * nside)

    south = ring > 3 * nside
    nr[south] = 4 * nside - ring[south]
    z[south] = nr[south] ** 2 / (3.0 * nside * nside) - 1.0

    belt = ~north & ~south
    nr[belt] = nside
    z[belt] = (2 * nside - ring[belt]) * 2.0 / (3.0 * nside)
    shift[belt] = (ring[belt] - nside) & 1

    # The reference implementation truncates this division towards zero; adding a whole
    # number of turns (8 nr in the numerator is 4 nr in jp) keeps it positive so that
    # Python's floor division agrees.
    jp = (_FACE_PHI[face] * nr + within + 1 + shift + 8 * nr) // 2
    jp = np.mod(jp - 1, 4 * nr) + 1
    phi = (jp - (shift + 1) * 0.5) * (np.pi / 2 / nr)
    return np.arccos(np.clip(z, -1.0, 1.0)), np.mod(phi, 2 * np.pi)


def healpix_angles(nside: int, ordering: str) -> tuple[np.ndarray, np.ndarray]:
    """Pixel centres for whichever ordering the file happens to use."""
    if ordering.upper().startswith("NEST"):
        return healpix_nested_angles(nside)
    return healpix_ring_angles(nside)


def to_grid(values: np.ndarray, nside: int, ordering: str = "RING",
            reduce: str = "mean") -> np.ndarray:
    """Average HEALPix pixels into a longitude–latitude grid (galactic coordinates)."""
    theta, phi = healpix_angles(nside, ordering)
    # Galactic longitude runs 0..360 to the left in the usual Mollweide plot; keep it
    # as 0..360 here and let the viewer decide which way round to draw it.
    column = np.clip((phi / (2 * np.pi) * GRID_LON).astype(np.int64), 0, GRID_LON - 1)
    row = np.clip(((np.pi - theta) / np.pi * GRID_LAT).astype(np.int64), 0, GRID_LAT - 1)
    flat = row * GRID_LON + column
    total = np.bincount(flat, weights=values, minlength=GRID_LON * GRID_LAT)
    count = np.bincount(flat, minlength=GRID_LON * GRID_LAT)
    with np.errstate(invalid="ignore", divide="ignore"):
        grid = np.where(count > 0, total / np.maximum(count, 1), np.nan)
    grid = grid.reshape(GRID_LAT, GRID_LON)
    if reduce == "min":                                 # a mask: any bad pixel spoils the cell
        floor = np.bincount(flat, weights=(values <= 0.5).astype(float),
                            minlength=GRID_LON * GRID_LAT).reshape(GRID_LAT, GRID_LON)
        grid = np.where(floor > 0, 0.0, 1.0)
    return _fill_gaps(grid)


def _fill_gaps(grid: np.ndarray) -> np.ndarray:
    """Cells no HEALPix pixel landed in take the nearest value along the row."""
    filled = grid.copy()
    for row in range(filled.shape[0]):
        line = filled[row]
        bad = np.isnan(line)
        if bad.all():
            continue
        if bad.any():
            good = np.flatnonzero(~bad)
            line[bad] = np.interp(np.flatnonzero(bad), good, line[good], period=len(line))
    return filled


def read_healpix(path: Path, column: str | None = None) -> tuple[np.ndarray, int, str, str]:
    """One map column of a HEALPix FITS file, with its nside and ordering."""
    from astropy.io import fits

    with fits.open(path) as hdul:
        hdu = hdul[1]
        data = hdu.data
        header = hdu.header
        name = column or data.names[0]
        values = np.asarray(data[name], dtype=float).ravel()
        nside = int(header.get("NSIDE", round((len(values) / 12) ** 0.5)))
        ordering = str(header.get("ORDERING", "RING")).strip().upper()
    return values, nside, name, ordering


# ------------------------------------------------------------------- the work
def build_cmb() -> Path:
    print("WMAP 9-year ILC map")
    map_file = download(*WMAP_MAP)
    mask_file = download(*WMAP_MASK)

    values, nside, column, ordering = read_healpix(map_file)
    print(f"  map:  nside {nside}, {len(values)} pixels, column {column!r}, {ordering}")
    mask_values, mask_nside, mask_column, mask_ordering = read_healpix(mask_file)
    print(f"  mask: nside {mask_nside}, column {mask_column!r}, {mask_ordering}, "
          f"{100 * np.mean(mask_values > 0.5):.1f}% of the sky kept")

    temperature = to_grid(values * 1e3, nside, ordering)          # mK in the file, µK here
    mask = to_grid(mask_values, mask_nside, mask_ordering, reduce="min")
    out = TARGET / "wmap_ilc_9yr.npz"
    np.savez_compressed(out, temperature=temperature.astype(np.float32),
                        mask=mask.astype(np.uint8),
                        shape=np.array([GRID_LAT, GRID_LON]))
    print(f"  wrote {out.name} ({out.stat().st_size / 1e6:.2f} MB), "
          f"rms {np.nanstd(temperature[mask > 0]):.1f} µK")
    return out


def build_sdss() -> Path:
    print("SDSS DR18 galaxy slice")
    raw = fetch_text(SDSS_URL, {"cmd": " ".join(SDSS_QUERY.split()), "format": "csv"},
                     "sdss_slice.csv")
    text = raw.read_text(encoding="utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if not lines or not lines[0].lower().startswith("ra"):
        raise SystemExit(f"SkyServer returned something unexpected:\n{text[:400]}")
    out = TARGET / "sdss_slice_dr18.csv"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {out.name} ({out.stat().st_size / 1e6:.2f} MB), {len(lines) - 1} galaxies")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="list the sources and stop")
    parser.add_argument("--only", choices=["cmb", "sdss"], help="rebuild just one data set")
    args = parser.parse_args(argv)

    if args.check:
        for url, name in (WMAP_MAP, WMAP_MASK):
            print(f"{name:34s} {url}")
        print(f"{'sdss_slice_dr18.csv':34s} {SDSS_URL}")
        return 0

    TARGET.mkdir(parents=True, exist_ok=True)
    if args.only != "sdss":
        build_cmb()
    if args.only != "cmb":
        build_sdss()
    print("\nRemember to add or update the entry in cosmos/data/external/README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
