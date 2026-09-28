"""Main peripheral nerves as data-only curves (plan §3.4.1: v1 data only -> deficits).

The bible names these nerves and their clinical anatomy (R05 §6-7, R04 §6)
but gives no waypoints, so every polyline here is an E fit by B0 to the
landmark, bone and vessel tables (``fit="B0"``); roots are standard
neuro-anatomy (K, QA re-check).  B5 refines paths and depths.  Left side;
mirrored for the right.  Exported as ``GBN_<nerve>_<side>`` curves and in
``vessels.json['nerves']``.
"""

# id: dict(roots, radius_m, points (proximal -> distal), deficit, tag)
NERVES = {
    "brachial_plexus_lateral_cord": dict(
        roots=["C5", "C6", "C7"], radius=0.0035,
        points=[(0.045, 0.004, 1.500), (0.075, -0.004, 1.455), (0.140, 0.000, 1.414), (0.184, 0.010, 1.356)],
        deficit="musculocutaneous (elbow flexion weak), lateral root of median",
        note="roots between anterior and middle scalene, over the 1st rib under the mid clavicle, around A40"),
    "brachial_plexus_medial_cord": dict(
        roots=["C8", "T1"], radius=0.0030,
        points=[(0.040, 0.010, 1.488), (0.074, 0.002, 1.452), (0.138, 0.008, 1.404), (0.184, 0.022, 1.346)],
        deficit="ulnar + medial root of median (hand intrinsics, grip)", note=""),
    "brachial_plexus_posterior_cord": dict(
        roots=["C5", "C6", "C7", "C8", "T1"], radius=0.0035,
        points=[(0.043, 0.012, 1.496), (0.076, 0.006, 1.456), (0.142, 0.012, 1.410), (0.186, 0.024, 1.352)],
        deficit="radial + axillary (deltoid, triceps, wrist/finger extensors)", note=""),
    "median": dict(
        roots=["C5", "C6", "C7", "C8", "T1"], radius=0.0025,
        points=[(0.186, 0.012, 1.350), (0.232, 0.010, 1.276), (0.322, 0.002, 1.146), (0.390, 0.014, 1.040),
                (0.450, 0.010, 0.925), (0.470, 0.012, 0.895)],
        deficit="thumb opposition, radial finger flexion, lateral palm sensation",
        note="with the brachial artery, medial in the cubital fossa, carpal tunnel at the wrist"),
    "ulnar": dict(
        roots=["C8", "T1"], radius=0.0022,
        points=[(0.186, 0.026, 1.346), (0.240, 0.035, 1.268), (0.297, 0.042, 1.150), (0.380, 0.040, 1.050),
                (0.452, 0.040, 0.922), (0.470, 0.040, 0.892)],
        deficit="claw hand, intrinsics, ulnar 1.5 fingers sensation",
        note="behind the medial epicondyle (subcutaneous 'funny bone'), Guyon's canal at the wrist"),
    "radial": dict(
        roots=["C5", "C6", "C7", "C8", "T1"], radius=0.0025,
        points=[(0.188, 0.028, 1.350), (0.228, 0.046, 1.300), (0.262, 0.040, 1.250), (0.300, 0.000, 1.205),
                (0.333, -0.004, 1.160), (0.395, -0.004, 1.045), (0.450, -0.006, 0.940)],
        deficit="wrist drop (mid-shaft humerus fracture), dorsal thumb-web sensation",
        note="spirals behind the mid-shaft humerus (radial groove, in contact with bone), front of the "
             "lateral epicondyle, superficial branch along the radial forearm"),
    "femoral": dict(
        roots=["L2", "L3", "L4"], radius=0.0035,
        points=[(0.060, 0.000, 1.060), (0.078, -0.040, 0.980), (0.080, -0.058, 0.942), (0.085, -0.055, 0.880)],
        deficit="knee extension (quadriceps), anterior thigh sensation",
        note="lateral to the femoral artery at the mid-inguinal point (NAV lateral -> medial)"),
    "sciatic": dict(
        roots=["L4", "L5", "S1", "S2", "S3"], radius=0.0060,
        points=[(0.055, 0.070, 0.965), (0.090, 0.075, 0.900), (0.100, 0.068, 0.850), (0.096, 0.062, 0.700),
                (0.093, 0.060, 0.560)],
        deficit="hamstrings and everything below the knee (foot drop + plantar weakness)",
        note="greater sciatic notch, between the greater trochanter and the ischial tuberosity, posterior "
             "thigh; 60-90 mm deep in the lower inner buttock quadrant (R05 §12)"),
    "tibial": dict(
        roots=["L4", "L5", "S1", "S2", "S3"], radius=0.0040,
        points=[(0.093, 0.060, 0.560), (0.092, 0.062, 0.470), (0.090, 0.064, 0.250), (0.076, 0.072, 0.085)],
        deficit="plantarflexion, toe flexion, sole sensation", note="with the posterior tibial artery"),
    "common_peroneal": dict(
        roots=["L4", "L5", "S1", "S2"], radius=0.0030,
        points=[(0.093, 0.060, 0.560), (0.118, 0.050, 0.480), (0.132, 0.040, 0.440), (0.128, 0.020, 0.420)],
        deficit="foot drop (dorsiflexion, eversion), dorsal foot sensation",
        note="wraps the fibular neck just below the fibular head (subcutaneous)"),
}
TAG = "E fit=B0 (paths), K (roots)"
