"""Geometry of spaces with constant curvature: triangles, circles and angular sizes.

Lengths are measured in units of the curvature radius R unless stated
otherwise. ``k = +1`` is a sphere (closed), ``0`` flat, ``-1`` hyperbolic (open).
"""

from __future__ import annotations

import math

import numpy as np

GEOMETRIES = {1: "closed (spherical)", 0: "flat (Euclidean)", -1: "open (hyperbolic)"}


def sin_k(x, k: int):
    """The generalised sine: sin for k = +1, identity for k = 0, sinh for k = −1."""
    x = np.asarray(x, dtype=float)
    if k > 0:
        return np.sin(x)
    if k < 0:
        return np.sinh(x)
    return x


def cos_k(x, k: int):
    x = np.asarray(x, dtype=float)
    if k > 0:
        return np.cos(x)
    if k < 0:
        return np.cosh(x)
    return np.ones_like(x)


def equilateral_angle(side: float, k: int) -> float:
    """Interior angle [rad] of an equilateral triangle with the given side length.

    Follows from the spherical / hyperbolic law of cosines:
    ``cos A = cos_k(a) / (1 + cos_k(a))``; for flat space A = 60°.
    """
    if k == 0:
        return math.pi / 3
    c = float(cos_k(side, k))
    value = c / (1 + c)
    if k > 0 and side >= 2 * math.pi / 3:
        raise ValueError("an equilateral spherical triangle this large does not exist")
    return math.acos(max(-1.0, min(1.0, value)))


def angle_sum(side: float, k: int) -> float:
    """Sum of the angles [rad] of an equilateral triangle."""
    return 3 * equilateral_angle(side, k)


def triangle_area(side: float, k: int) -> float:
    """Area of an equilateral triangle in units of R².

    For curved spaces Gauss–Bonnet gives ``area = |angle sum − π|``.
    """
    if k == 0:
        return math.sqrt(3) / 4 * side * side
    return abs(angle_sum(side, k) - math.pi)


def circumference(radius, k: int):
    """Circumference of a circle of geodesic radius r: 2π R sin_k(r/R)."""
    return 2 * math.pi * sin_k(radius, k)


def circle_area(radius, k: int):
    r = np.asarray(radius, dtype=float)
    if k > 0:
        return 2 * math.pi * (1 - np.cos(r))
    if k < 0:
        return 2 * math.pi * (np.cosh(r) - 1)
    return math.pi * r * r


def angular_size(length: float, distance, k: int):
    """Angle [rad] subtended by a ruler of given length at a given geodesic distance.

    In curved space the apparent size uses sin_k(distance) instead of the distance,
    so objects look larger in closed space and smaller in open space.
    """
    return length / np.maximum(np.abs(sin_k(distance, k)), 1e-12)


def curvature_radius_mpc(omega_k: float, h0_km_s_mpc: float) -> float:
    """Present curvature radius c / (H0 √|Ωk|) [Mpc] (``inf`` for a flat universe)."""
    if abs(omega_k) < 1e-12:
        return math.inf
    return 299_792.458 / h0_km_s_mpc / math.sqrt(abs(omega_k))


def sphere_geodesic(p, q, n: int = 60) -> np.ndarray:
    """Points along the great-circle arc between unit vectors p and q."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    omega = math.acos(max(-1.0, min(1.0, float(np.dot(p, q)))))
    if omega < 1e-9:
        return np.repeat(p[None, :], n, axis=0)
    t = np.linspace(0, 1, n)[:, None]
    return (np.sin((1 - t) * omega) * p + np.sin(t * omega) * q) / math.sin(omega)


def spherical_triangle(side: float) -> np.ndarray:
    """Vertices (unit vectors) of an equilateral spherical triangle centred on the north pole."""
    # Circumradius ρ from the central isosceles triangle with apex angle 120°:
    # cos a = cos²ρ + sin²ρ cos 120°  →  cos ρ = √((cos a + ½) / 1.5).
    circumradius = math.acos(math.sqrt(max(0.0, (math.cos(side) + 0.5) / 1.5)))
    verts = []
    for i in range(3):
        phi = 2 * math.pi * i / 3 + math.pi / 2
        verts.append([math.sin(circumradius) * math.cos(phi), math.sin(circumradius) * math.sin(phi),
                      math.cos(circumradius)])
    return np.array(verts)


def poincare_triangle(side: float, n: int = 80) -> list[np.ndarray]:
    """Edges of an equilateral hyperbolic triangle in the Poincaré disk model.

    Returns three arrays of (x, y) points. Geodesics in the disk are arcs of circles
    orthogonal to the boundary.
    """
    # Circumradius ρ from the central isosceles triangle with apex angle 120°.
    rho = math.acosh(_solve_circumradius(side))
    disk_r = math.tanh(rho / 2)
    verts = [np.array([disk_r * math.cos(2 * math.pi * i / 3 + math.pi / 2),
                       disk_r * math.sin(2 * math.pi * i / 3 + math.pi / 2)]) for i in range(3)]
    return [_poincare_geodesic(verts[i], verts[(i + 1) % 3], n) for i in range(3)]


def _solve_circumradius(side: float) -> float:
    # cosh a = cosh²ρ − sinh²ρ cos(120°) = cosh²ρ + ½ sinh²ρ = 1.5 cosh²ρ − 0.5
    return math.sqrt((math.cosh(side) + 0.5) / 1.5)


def _poincare_geodesic(p: np.ndarray, q: np.ndarray, n: int) -> np.ndarray:
    # Möbius transformation moving p to the origin, straight line there, transform back.
    pc, qc = complex(*p), complex(*q)

    def to_origin(z):
        return (z - pc) / (1 - pc.conjugate() * z)

    def from_origin(w):
        return (w + pc) / (1 + pc.conjugate() * w)

    target = to_origin(qc)
    points = [from_origin(target * t) for t in np.linspace(0, 1, n)]
    return np.array([[z.real, z.imag] for z in points])
