"""Ribs, costal cartilages and sternum (RB §7.3 rib table, R05 §5.1-5.3; E fits, M).

Left side; negate x for the right.  Each rib is swept through
head -> posterior angle -> lateral (~MAL) -> CCJ (costochondral junction), and
its cartilage from the CCJ to its sternal end (ribs 1-7), to the cartilage above
(8-10, forming the costal margin) or as a short cap (11-12, floating).
"""

# rib: (type, head, posterior_angle, lateral, ccj, cartilage_end, cartilage_joins, arc_mm, cartilage_mm)
RIB_TABLE = {
    1: ("true", (0.018, 0.030, 1.481), (0.035, 0.050, 1.478), (0.055, -0.005, 1.462), (0.035, -0.030, 1.440),
        (0.020, -0.042, 1.440), "manubrium", 80, 25),
    2: ("true", (0.020, 0.038, 1.469), (0.045, 0.075, 1.462), (0.085, 0.015, 1.440), (0.045, -0.052, 1.405),
        (0.016, -0.062, 1.405), "sternal_angle", 150, 30),
    3: ("true", (0.020, 0.046, 1.449), (0.052, 0.085, 1.440), (0.105, 0.022, 1.414), (0.058, -0.066, 1.372),
        (0.015, -0.071, 1.380), "sternum", 195, 35),
    4: ("true", (0.020, 0.052, 1.428), (0.056, 0.090, 1.418), (0.118, 0.025, 1.388), (0.070, -0.075, 1.340),
        (0.016, -0.079, 1.355), "sternum", 225, 45),
    5: ("true", (0.021, 0.056, 1.406), (0.058, 0.092, 1.395), (0.127, 0.025, 1.362), (0.082, -0.080, 1.308),
        (0.017, -0.086, 1.332), "sternum", 245, 55),
    6: ("true", (0.021, 0.059, 1.384), (0.060, 0.092, 1.372), (0.133, 0.022, 1.336), (0.092, -0.080, 1.275),
        (0.015, -0.094, 1.312), "sternum", 260, 75),
    7: ("true", (0.022, 0.059, 1.361), (0.062, 0.090, 1.348), (0.137, 0.018, 1.308), (0.100, -0.075, 1.240),
        (0.010, -0.098, 1.302), "xiphisternal", 270, 110),
    8: ("false", (0.022, 0.056, 1.337), (0.063, 0.088, 1.323), (0.139, 0.015, 1.280), (0.110, -0.062, 1.205),
        (0.060, -0.090, 1.245), "cartilage_7", 270, 90),
    9: ("false", (0.023, 0.050, 1.313), (0.064, 0.084, 1.298), (0.139, 0.015, 1.250), (0.118, -0.048, 1.175),
        (0.085, -0.078, 1.200), "cartilage_8", 260, 70),
    10: ("false", (0.024, 0.041, 1.280), (0.064, 0.078, 1.268), (0.136, 0.018, 1.212), (0.125, -0.030, 1.150),
         (0.100, -0.065, 1.150), "cartilage_9", 240, 55),
    11: ("floating", (0.025, 0.030, 1.254), (0.062, 0.070, 1.243), (0.130, 0.030, 1.185), (0.125, 0.010, 1.160),
         None, "cap", 190, 10),
    12: ("floating", (0.025, 0.018, 1.227), (0.055, 0.058, 1.218), None, (0.085, 0.060, 1.180),
         None, "cap", 120, 5),
}
COSTAL_MARGIN_LOWEST = (0.112, -0.050, 1.125)   # 10th costal cartilage (lowest point of the margin)

# Sections (mm): shaft height x thickness; rib 1 flat; floating ribs smaller; cartilage 10-15 x 6-10
RIB_SECTION_MM = {1: (27.5, 5.0), "default": (13.5, 6.0), 11: (9.0, 5.5), 12: (9.0, 5.5)}
CARTILAGE_SECTION_MM = (12.5, 8.0)
RIB_CORTEX_MM = 1.0                 # 0.6-1.8 (L/M)
INTERCOSTAL_SPACE_MM = {"front": (15, 25), "side": (12, 18), "back": (8, 12)}
COSTAL_GROOVE = "lower inner edge; intercostal vein, artery, nerve (top to bottom)"

# Sternum (R05 §5.1), inclined ~20 deg (lower end forward); front-surface points
STERNUM = {
    "manubrium": dict(top=(0.0, -0.047, 1.453), bottom=(0.0, -0.064, 1.406), length_cm=5.0,
                      width_cm=(5.5, 3.0), thickness_cm=1.5),
    "body": dict(top=(0.0, -0.064, 1.406), bottom=(0.0, -0.100, 1.307), length_cm=10.5,
                 width_cm=(2.5, 3.5, 2.5), thickness_cm=1.1),
    "xiphoid": dict(top=(0.0, -0.100, 1.307), bottom=(0.0, -0.094, 1.273), length_cm=3.5,
                    width_cm=(1.75,), thickness_cm=0.45),
}
STERNUM_DOWN_AXIS = (0.0, -0.342, -0.940)
STERNUM_CORTEX_MM = 1.0
SOFT_TISSUE_OVER_STERNUM_MM = (5, 12)
RV_DEPTH_BEHIND_LOWER_STERNUM_SKIN_MM = (25, 35)

# Cage dimensions (R05 §5.3) for checks
CAGE = dict(width_at_rib_cm={4: 23.6, 6: 26.6, 8: 27.8, 10: 27.2}, ap_depth_t7_cm=(18, 19),
            internal_ap_t8_cm=(11, 12), infrasternal_angle_deg=(70, 90), posterior_height_cm=26,
            front_height_cm=33)


def rib_points(n, include_cartilage=False):
    """Ordered control points of rib ``n`` (left), optionally continued through its cartilage."""
    kind, head, angle, lateral, ccj, cart_end, joins, arc, cart = RIB_TABLE[n]
    pts = [head, angle] + ([lateral] if lateral is not None else []) + [ccj]
    if include_cartilage and cart_end is not None:
        pts.append(cart_end)
    return pts


def cartilage_points(n):
    """Control points of the costal cartilage of rib ``n`` (CCJ -> end); [] for floating ribs."""
    kind, head, angle, lateral, ccj, cart_end, joins, arc, cart = RIB_TABLE[n]
    return [] if cart_end is None else [ccj, cart_end]
