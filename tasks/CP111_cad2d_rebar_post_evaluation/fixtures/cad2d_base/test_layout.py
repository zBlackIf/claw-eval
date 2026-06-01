"""
Sample retaining wall rebar layout for post-evaluation testing.

This module creates a simple retaining wall cross-section with:
- A trapezoidal contour
- Distribution rebars along the inner face
- Stirrups (with anchors) wrapping the rebars

Some intentional issues exist in the layout for the post-evaluation to catch.
"""
from cad2d_base.geometry import Point2D, Wire2D
from cad2d_base.entities import LineRebar


def create_contour() -> Wire2D:
    """
    Create retaining wall cross-section contour (mm).

    Shape: trapezoidal, bottom wider than top.
      - Bottom: 2000mm wide
      - Top: 500mm wide
      - Height: 1800mm
      - Front slope offset: 130mm
    """
    vertices = [
        Point2D(0, 0),          # bottom-left
        Point2D(2000, 0),       # bottom-right
        Point2D(1800, 1800),    # top-right
        Point2D(130, 1800),     # top-left (offset by front slope)
    ]
    return Wire2D(vertices, closed=True)


def create_distribution_rebars(cover: float = 40.0) -> list:
    """
    Create distribution rebar positions along the back face.

    Args:
        cover: concrete cover thickness (mm)

    Returns:
        List of (x, y) rebar center positions
    """
    # Place rebars along the back face (right side), spaced at 200mm
    positions = []
    spacing = 200.0
    # Back face runs from (2000, 0) to (1800, 1800)
    # Inner offset by cover
    x_bottom = 2000 - cover
    x_top = 1800 - cover
    num_rebars = int(1800 / spacing)

    for i in range(num_rebars + 1):
        t = i * spacing / 1800.0
        x = x_bottom + (x_top - x_bottom) * t
        y = i * spacing
        positions.append((x, y))

    return positions


def create_stirrups(cover: float = 40.0, diameter: float = 8.0) -> list:
    """
    Create stirrup rebars wrapping the contour.

    Each stirrup is a closed loop with start and end anchors.
    Some stirrups have intentional issues:
    - stirrup_0: anchor direction folds back onto main body (clearance violation)
    - stirrup_1: good anchor with proper clearance
    - stirrup_2: anchor angle < 90 degrees (angle violation)
    """
    stirrups = []

    # Stirrup 0: anchor folds back (clearance issue)
    # Main body follows the inner contour offset by cover
    body = [
        Point2D(cover, cover),
        Point2D(2000 - cover, cover),
        Point2D(2000 - cover, 600),
        Point2D(cover, 600),
    ]
    # Start anchor: folds BACK onto the body segment (bad - too close)
    anchor_start = [Point2D(cover, cover + 280), Point2D(cover, cover)]
    # End anchor: also folds back
    anchor_end = [Point2D(cover, 600), Point2D(cover, 600 - 280)]

    all_pts = anchor_start + body + anchor_end
    s0 = LineRebar(
        points=all_pts,
        diameter=diameter,
        anchor_start_count=len(anchor_start),
        anchor_end_count=len(anchor_end),
    )
    stirrups.append(s0)

    # Stirrup 1: good stirrup with proper anchor direction
    body = [
        Point2D(cover, 700),
        Point2D(2000 - cover, 700),
        Point2D(2000 - cover, 1200),
        Point2D(cover, 1200),
    ]
    # Start anchor: extends OUTWARD from body (good - proper clearance)
    anchor_start = [Point2D(cover + 280, 700), Point2D(cover, 700)]
    # End anchor: extends outward
    anchor_end = [Point2D(cover, 1200), Point2D(cover + 280, 1200)]

    all_pts = anchor_start + body + anchor_end
    s1 = LineRebar(
        points=all_pts,
        diameter=diameter,
        anchor_start_count=len(anchor_start),
        anchor_end_count=len(anchor_end),
    )
    stirrups.append(s1)

    # Stirrup 2: has an acute angle in anchor bend (< 90 degrees)
    body = [
        Point2D(cover, 1300),
        Point2D(1800 - cover, 1300),
        Point2D(1800 - cover, 1700),
        Point2D(cover + 100, 1700),
    ]
    # Start anchor: makes a sharp 60-degree turn (violation)
    anchor_start = [
        Point2D(cover + 50, 1300 + 100),  # creates ~60 degree angle
        Point2D(cover, 1300),
    ]
    # End anchor: acceptable angle
    anchor_end = [Point2D(cover + 100, 1700), Point2D(cover + 100 + 200, 1700 + 50)]

    all_pts = anchor_start + body + anchor_end
    s2 = LineRebar(
        points=all_pts,
        diameter=diameter,
        anchor_start_count=len(anchor_start),
        anchor_end_count=len(anchor_end),
    )
    stirrups.append(s2)

    return stirrups


def get_test_layout() -> dict:
    """
    Get a complete test layout for post-evaluation.

    Returns dict with:
        contour: Wire2D of the wall cross-section
        dist_rebar_positions: list of (x,y) tuples
        stirrups: list of LineRebar objects
        config: evaluation parameters
    """
    contour = create_contour()
    rebars = create_distribution_rebars(cover=40.0)
    stirrups = create_stirrups(cover=40.0, diameter=8.0)

    config = {
        'cover': 40.0,           # concrete cover (mm)
        'spacing': 200.0,        # max rebar spacing (mm)
        'dist_diameter': 10.0,   # distribution rebar diameter (mm)
        'stirrup_diameter': 8.0, # stirrup diameter (mm)
        'anchor_length_d': 35.0, # anchor length multiplier (d = diameter)
        'min_anchor_angle': 90.0,    # minimum bend angle (degrees)
        'min_anchor_clearance': 16.0, # min clearance between anchor and body (mm)
    }

    return {
        'contour': contour,
        'dist_rebar_positions': rebars,
        'stirrups': stirrups,
        'config': config,
    }
