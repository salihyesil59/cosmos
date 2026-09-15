"""Named cosmological models, including parameters measured by major surveys."""

from __future__ import annotations

from dataclasses import dataclass

from cosmos.physics.cosmology import Cosmology


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    description: str
    cosmology: Cosmology


def _flat(name, H0, Om0, Ob0, Tcmb0=2.7255, Neff=3.046) -> Cosmology:
    return Cosmology.flat(H0=H0, Om0=Om0, Ob0=Ob0, Tcmb0=Tcmb0, Neff=Neff, name=name)


PRESETS: dict[str, Preset] = {
    p.key: p
    for p in [
        Preset(
            "planck18",
            "Planck 2018",
            "Flat ΛCDM parameters from the Planck satellite's 2018 CMB analysis "
            "(TT,TE,EE+lowE+lensing+BAO). The current reference model.",
            _flat("Planck 2018", H0=67.66, Om0=0.30966, Ob0=0.04897),
        ),
        Preset(
            "wmap9",
            "WMAP 9-year",
            "Flat ΛCDM parameters from NASA's WMAP satellite (9-year data combined "
            "with other probes). Planck's predecessor.",
            _flat("WMAP 9-year", H0=69.32, Om0=0.2865, Ob0=0.04628, Tcmb0=2.725, Neff=3.04),
        ),
        Preset(
            "concordance",
            "Round-number ΛCDM",
            "A textbook model with easy-to-remember numbers: H0 = 70, Ωm = 0.3, "
            "ΩΛ = 0.7, no radiation.",
            Cosmology(H0=70.0, Om0=0.3, Ode0=0.7, Ob0=0.05, Tcmb0=0.0, name="Round-number ΛCDM"),
        ),
        Preset(
            "eds",
            "Einstein–de Sitter",
            "A flat universe containing only matter (Ωm = 1). The standard model "
            "before dark energy was discovered; its age is exactly 2/3 of the "
            "Hubble time.",
            Cosmology(H0=70.0, Om0=1.0, Ode0=0.0, Ob0=0.05, Tcmb0=0.0, name="Einstein–de Sitter"),
        ),
        Preset(
            "open_matter",
            "Open, matter only",
            "A low-density universe without dark energy (Ωm = 0.3, ΩΛ = 0). Space "
            "is negatively curved and the expansion never stops.",
            Cosmology(H0=70.0, Om0=0.3, Ode0=0.0, Ob0=0.05, Tcmb0=0.0, name="Open, matter only"),
        ),
        Preset(
            "closed_matter",
            "Closed, matter only",
            "A dense universe (Ωm = 2, ΩΛ = 0). Space is positively curved, the "
            "expansion halts and the universe ends in a Big Crunch.",
            Cosmology(H0=70.0, Om0=2.0, Ode0=0.0, Ob0=0.05, Tcmb0=0.0, name="Closed, matter only"),
        ),
        Preset(
            "milne",
            "Empty (Milne)",
            "A universe with no matter, radiation or dark energy. It expands at a "
            "constant rate, so its age equals the Hubble time.",
            Cosmology(H0=70.0, Om0=0.0, Ode0=0.0, Ob0=0.0, Tcmb0=0.0, name="Empty (Milne)"),
        ),
        Preset(
            "de_sitter",
            "de Sitter (Λ only)",
            "A flat universe containing only a cosmological constant. It expands "
            "exponentially forever and has no Big Bang in the finite past.",
            Cosmology(H0=70.0, Om0=0.0, Ode0=1.0, Ob0=0.0, Tcmb0=0.0, name="de Sitter (Λ only)"),
        ),
    ]
}

DEFAULT_PRESET = "planck18"


def get_preset(key: str) -> Preset:
    return PRESETS[key]
