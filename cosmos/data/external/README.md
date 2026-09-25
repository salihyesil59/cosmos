# Bundled observational data

The app shows this record to the learner as well, under **Reference → Data &
methods**; `cosmos/provenance.py` holds it in the form the app reads, and a test
keeps the two lists and this folder in step.

These files are **real measurements**, bundled so that the course works offline.
The first three are redistributed unmodified; the last two are a subset and a
resampling of much larger public releases, described below. They are the work of
the teams below; if you use them for anything beyond learning, cite the papers,
not this app.

| File | Source | Retrieved | Cite |
|---|---|---|---|
| `PantheonPlusSH0ES.dat` | [PantheonPlusSH0ES/DataRelease](https://github.com/PantheonPlusSH0ES/DataRelease) (`Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat`) | 2026-09-16 | Scolnic et al. 2022, ApJ 938, 113; Brout et al. 2022, ApJ 938, 110; Riess et al. 2022, ApJ 934, L7 |
| `Rotmod_LTG.zip` | [SPARC](http://astroweb.cwru.edu/SPARC/) rotation curves of 175 disk galaxies | 2026-09-16 | Lelli, McGaugh & Schombert 2016, AJ 152, 157 |
| `SPARC_Lelli2016c.mrt` | [SPARC](http://astroweb.cwru.edu/SPARC/) galaxy table (Table 1) | 2026-09-16 | Lelli, McGaugh & Schombert 2016, AJ 152, 157 |
| `wmap_ilc_9yr.npz` | [NASA LAMBDA](https://lambda.gsfc.nasa.gov/product/wmap/dr5/ilc_map_get.html): WMAP 9-year ILC map and the KQ85 analysis mask | 2026-09-23 | Bennett et al. 2013, ApJS 208, 20; Hinshaw et al. 2013, ApJS 208, 19 |
| `sdss_slice_dr18.csv` | [SDSS SkyServer](https://skyserver.sdss.org/) DR18, spectroscopic galaxies | 2026-09-23 | Almeida et al. 2023, ApJS 267, 44 (SDSS-IV/V DR18) |

Notes

- `PantheonPlusSH0ES.dat` holds 1701 light curves of 1550 type Ia supernovae with
  their standardised magnitudes and distance moduli. The app reads a few columns
  (redshift, `m_b_corr`, `MU_SH0ES`, the calibrator flag) and leaves the file as
  published; the covariance matrix of the full analysis is not bundled, so the
  fits in the app use diagonal errors only and are teaching fits, not the
  published cosmology.
- The SPARC archive contains one `*_rotmod.dat` per galaxy: radius, observed
  rotation velocity and its error, plus the velocities expected from gas, disk
  and bulge. `SPARC_Lelli2016c.mrt` is the machine-readable galaxy table with
  distances, inclinations, luminosities and quality flags.
- `wmap_ilc_9yr.npz` is the WMAP team's Internal Linear Combination map — nine
  years of observations in five frequency bands, combined so that everything
  without a thermal spectrum cancels. The published file is HEALPix (nside 512,
  NESTED); here it has been resampled onto a 1024 × 512 longitude–latitude grid in
  galactic coordinates and converted from mK to µK, so that the app needs no
  HEALPix library. The `mask` array is the KQ85 analysis mask on the same grid: 1
  where WMAP judged the data usable, 0 over the Galaxy and the point sources. The
  resampled map has an rms of 67 µK outside the mask, against the 70 µK of the
  published map at full resolution. `tools/fetch_sky_data.py` rebuilds it.
- `sdss_slice_dr18.csv` holds 25 149 spectroscopic galaxies from the equatorial
  strip that produced the original cone diagrams: 120° < RA < 250°, |dec| < 1.5°,
  0.005 < z < 0.15, with `zWarning = 0`. Columns are right ascension, declination,
  redshift and the r-band Petrosian magnitude (−9999 where SDSS has none). Funding
  for SDSS has been provided by the Alfred P. Sloan Foundation, the U.S. Department
  of Energy Office of Science and the participating institutions; see
  <https://www.sdss.org/> for the full acknowledgement they ask for.
- Everything else the app plots — the supernova samples labelled *simulated*, the
  N-body universe, the lognormal mock catalogues, the CMB teaching model, the
  Olbers star fields — is generated inside the app and labelled as such.
