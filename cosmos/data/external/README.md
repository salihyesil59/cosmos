# Bundled observational data

These files are **real measurements**, redistributed here unmodified so that the
course works offline. They are the work of the teams below; if you use them for
anything beyond learning, cite the papers, not this app.

| File | Source | Retrieved | Cite |
|---|---|---|---|
| `PantheonPlusSH0ES.dat` | [PantheonPlusSH0ES/DataRelease](https://github.com/PantheonPlusSH0ES/DataRelease) (`Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat`) | 2026-09-16 | Scolnic et al. 2022, ApJ 938, 113; Brout et al. 2022, ApJ 938, 110; Riess et al. 2022, ApJ 934, L7 |
| `Rotmod_LTG.zip` | [SPARC](http://astroweb.cwru.edu/SPARC/) rotation curves of 175 disk galaxies | 2026-09-16 | Lelli, McGaugh & Schombert 2016, AJ 152, 157 |
| `SPARC_Lelli2016c.mrt` | [SPARC](http://astroweb.cwru.edu/SPARC/) galaxy table (Table 1) | 2026-09-16 | Lelli, McGaugh & Schombert 2016, AJ 152, 157 |

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
- Everything else the app plots — the supernova samples labelled *simulated*, the
  N-body universe, the CMB teaching model, the Olbers star fields — is generated
  inside the app and labelled as such.
