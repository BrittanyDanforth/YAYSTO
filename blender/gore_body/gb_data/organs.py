"""Organs and hit volumes (RB §7.5; R05 §10-11) plus the per-organ game data of plan §5.8.

``ORGAN_CSV`` is RB §7.5 verbatim: full lengths; ``aabb`` rows have u = +X,
v = +Y; obb/ellipsoid/capsule rows give the u and v unit axes (w = u x v).
Right-side kidney/adrenal come from the bible's comment row.  ``TUBE_CSV`` is
the bible's tube table (radius then a polyline).
"""
import numpy as np

# name,shape,cx,cy,cz,size_u,size_v,size_w,ux,uy,uz,vx,vy,vz,mass_g
ORGAN_CSV = """\
heart,obb,0.035,-0.036,1.325,0.125,0.090,0.065,0.632,-0.498,-0.593,0.466,-0.367,0.805,320
heart_RA,ellipsoid,-0.030,-0.018,1.335,0.045,0.050,0.045,1,0,0,0,1,0,0
heart_RV,ellipsoid,0.012,-0.060,1.312,0.070,0.030,0.060,1,0,0,0,1,0,0
heart_LA,ellipsoid,0.008,-0.008,1.365,0.050,0.038,0.040,1,0,0,0,1,0,0
heart_LV,ellipsoid,0.045,-0.035,1.305,0.090,0.055,0.055,0.632,-0.498,-0.593,0.466,-0.367,0.805,0
lung_R,aabb,-0.075,0.006,1.383,0.130,0.168,0.225,1,0,0,0,1,0,550
lung_L,aabb,0.075,0.008,1.380,0.130,0.165,0.230,1,0,0,0,1,0,480
liver,aabb,-0.033,-0.008,1.235,0.225,0.155,0.160,1,0,0,0,1,0,1550
liver_right_lobe,ellipsoid,-0.075,0.000,1.235,0.140,0.150,0.160,1,0,0,0,1,0,0
liver_left_lobe,ellipsoid,0.035,-0.045,1.270,0.090,0.070,0.060,1,0,0,0,1,0,0
liver_caudate,ellipsoid,-0.010,0.030,1.255,0.030,0.030,0.060,1,0,0,0,1,0,0
gallbladder,capsule,-0.060,-0.043,1.208,0.080,0.035,0.035,0.466,0.699,0.543,0.832,-0.555,0,40
spleen,obb,0.105,0.040,1.228,0.120,0.070,0.030,0.390,-0.547,-0.742,0.445,-0.594,0.672,150
kidney_L,obb,0.070,0.024,1.180,0.115,0.060,0.040,0.258,-0.198,-0.946,-0.804,-0.586,-0.097,150
adrenal_L,ellipsoid,0.042,0.025,1.230,0.030,0.010,0.050,1,0,0,0,1,0,5
stomach,aabb,0.038,-0.025,1.200,0.145,0.120,0.210,1,0,0,0,1,0,150
bladder_empty,sphere,0.000,-0.030,0.898,0.050,0.050,0.050,1,0,0,0,1,0,50
bladder_full,sphere,0.000,-0.035,0.943,0.100,0.100,0.100,1,0,0,0,1,0,50
thyroid_lobe_L,ellipsoid,0.022,-0.028,1.505,0.020,0.018,0.050,1,0,0,0,1,0,9
thyroid_isthmus,ellipsoid,0.000,-0.042,1.492,0.020,0.005,0.020,1,0,0,0,1,0,2
bowel_filler,aabb,0.000,-0.040,1.040,0.240,0.120,0.280,1,0,0,0,1,0,2200
kidney_R,obb,-0.070,0.024,1.160,0.115,0.060,0.040,-0.258,-0.198,-0.946,0.804,-0.586,-0.097,150
adrenal_R,ellipsoid,-0.040,0.030,1.235,0.030,0.010,0.050,1,0,0,0,1,0,5
thyroid_lobe_R,ellipsoid,-0.022,-0.028,1.505,0.020,0.018,0.050,1,0,0,0,1,0,9
"""
# thyroid_lobe_R is the mirror of the left lobe (bible lists the left only).

# name,radius,x1,y1,z1,x2,y2,z2,...  (RB §7.5)
TUBE_CSV = """\
trachea,0.010,0.000,-0.030,1.508,0.000,-0.018,1.455,-0.003,0.008,1.402
bronchus_R,0.0075,-0.003,0.008,1.402,-0.028,0.012,1.380
bronchus_L,0.006,-0.003,0.008,1.402,0.042,0.020,1.380
oesophagus,0.009,0.000,-0.012,1.508,0.004,0.012,1.450,0.000,0.022,1.415,0.002,0.024,1.355,0.012,0.012,1.310,0.022,-0.008,1.280,0.030,-0.018,1.255
pancreas,0.012,-0.035,-0.035,1.160,-0.005,-0.050,1.180,0.025,-0.045,1.195,0.090,0.015,1.215
brainstem,0.011,0.000,0.030,1.619,0.000,0.025,1.633,0.000,0.020,1.647,0.000,0.014,1.659,0.000,0.010,1.682
cauda_equina,0.007,0.000,0.017,1.180,0.000,0.013,1.161,0.000,0.008,1.124,0.000,0.011,1.087,0.000,0.022,1.050,0.000,0.035,0.995
"""


def _parse_organs():
    out = {}
    for line in ORGAN_CSV.strip().splitlines():
        p = line.split(",")
        u = np.array([float(v) for v in p[8:11]])
        v = np.array([float(x) for x in p[11:14]])
        out[p[0]] = dict(shape=p[1], c=tuple(float(x) for x in p[2:5]), size=tuple(float(x) for x in p[5:8]),
                         u=tuple(u), v=tuple(v), w=tuple(np.cross(u, v)), mass_g=float(p[14]))
    return out


def _parse_tubes():
    out = {}
    for line in TUBE_CSV.strip().splitlines():
        p = line.split(",")
        vals = [float(x) for x in p[2:]]
        out[p[0]] = dict(radius=float(p[1]), points=[tuple(vals[i:i + 3]) for i in range(0, len(vals), 3)])
    return out


PRIMITIVES = _parse_organs()
TUBES = _parse_tubes()

# ---------------------------------------------------------------------------
# Organ records (plan §5.8 organs.json).  organ_id is the UV2.x code on GB_Organs.
# parent_bones: RB §7.5 "organ_parent_bones" (G).  compartment feeds internal
# bleeding (RB §3.9).  hit_priority: higher wins when primitives overlap.
# interior_colour: cut interior shading (plan §3.3.6); surface colour from R05.
# ---------------------------------------------------------------------------
ORGANS = [
    dict(id="heart", organ_id=1, hit=["heart"], sub=["heart_RA", "heart_RV", "heart_LA", "heart_LV"],
         parent_bones={"chest": 1.0}, compartment="pericardium", hit_priority=10,
         surface_colour="#7B2626", interior_colour="#7B2626", blend_shapes=["heart_systole"]),
    dict(id="lung_L", organ_id=2, hit=["lung_L"], sub=[], parent_bones={"chest": 0.5, "upper_chest": 0.5},
         compartment="pleura_L", hit_priority=6, surface_colour="#E0A0A0", interior_colour="#A04A55",
         blend_shapes=["lung_inhale_L", "lung_collapse_L"]),
    dict(id="lung_R", organ_id=3, hit=["lung_R"], sub=[], parent_bones={"chest": 0.5, "upper_chest": 0.5},
         compartment="pleura_R", hit_priority=6, surface_colour="#E0A0A0", interior_colour="#A04A55",
         blend_shapes=["lung_inhale_R", "lung_collapse_R"]),
    dict(id="liver", organ_id=4, hit=["liver"], sub=["liver_right_lobe", "liver_left_lobe", "liver_caudate"],
         parent_bones={"spine": 1.0}, compartment="peritoneum", hit_priority=7,
         surface_colour="#7A2E23", interior_colour="#7A2E23", blend_shapes=[]),
    dict(id="gallbladder", organ_id=5, hit=["gallbladder"], sub=[], parent_bones={"spine": 1.0},
         compartment="peritoneum", hit_priority=8, surface_colour="#5E7A3A", interior_colour="#4E6A2A",
         blend_shapes=[]),
    dict(id="spleen", organ_id=6, hit=["spleen"], sub=[], parent_bones={"spine": 1.0}, compartment="peritoneum",
         hit_priority=8, surface_colour="#5E2433", interior_colour="#5E2433", blend_shapes=[]),
    dict(id="kidney_L", organ_id=7, hit=["kidney_L"], sub=[], parent_bones={"spine": 1.0},
         compartment="retroperitoneum", hit_priority=8, surface_colour="#6E2A26",
         interior_colour="#7A2E2A", blend_shapes=[]),
    dict(id="kidney_R", organ_id=8, hit=["kidney_R"], sub=[], parent_bones={"spine": 1.0},
         compartment="retroperitoneum", hit_priority=8, surface_colour="#6E2A26",
         interior_colour="#7A2E2A", blend_shapes=[]),
    dict(id="adrenal_L", organ_id=9, hit=["adrenal_L"], sub=[], parent_bones={"spine": 1.0},
         compartment="retroperitoneum", hit_priority=9, surface_colour="#C9A04A", interior_colour="#B08040",
         blend_shapes=[]),
    dict(id="adrenal_R", organ_id=10, hit=["adrenal_R"], sub=[], parent_bones={"spine": 1.0},
         compartment="retroperitoneum", hit_priority=9, surface_colour="#C9A04A", interior_colour="#B08040",
         blend_shapes=[]),
    dict(id="stomach", organ_id=11, hit=["stomach"], sub=[], parent_bones={"spine": 1.0},
         compartment="peritoneum", hit_priority=5, surface_colour="#C98A7E", interior_colour="#A05050",
         blend_shapes=[]),
    dict(id="pancreas", organ_id=12, hit=[], tube="pancreas", sub=[], parent_bones={"spine": 1.0},
         compartment="retroperitoneum", hit_priority=7, surface_colour="#D9B28A", interior_colour="#C89A74",
         blend_shapes=[]),
    dict(id="bladder", organ_id=13, hit=["bladder_empty"], sub=["bladder_full"], parent_bones={"hips": 1.0},
         compartment="pelvis_extraperitoneal", hit_priority=6, surface_colour="#D8B0A0",
         interior_colour="#C08A80", blend_shapes=[]),
    dict(id="thyroid", organ_id=14, hit=["thyroid_lobe_L", "thyroid_lobe_R", "thyroid_isthmus"], sub=[],
         parent_bones={"neck": 1.0}, compartment="neck", hit_priority=6, surface_colour="#9A3A3A",
         interior_colour="#8A3030", blend_shapes=[]),
    dict(id="trachea", organ_id=15, hit=[], tube="trachea", sub=[], parent_bones={"upper_chest": 0.5, "neck": 0.5},
         compartment="airway", hit_priority=7, surface_colour="#D8C8C0", interior_colour="#C08880",
         blend_shapes=[]),
    dict(id="bronchus_L", organ_id=16, hit=[], tube="bronchus_L", sub=[], parent_bones={"upper_chest": 1.0},
         compartment="airway", hit_priority=7, surface_colour="#D8C8C0", interior_colour="#C08880",
         blend_shapes=[]),
    dict(id="bronchus_R", organ_id=17, hit=[], tube="bronchus_R", sub=[], parent_bones={"upper_chest": 1.0},
         compartment="airway", hit_priority=7, surface_colour="#D8C8C0", interior_colour="#C08880",
         blend_shapes=[]),
    dict(id="oesophagus", organ_id=18, hit=[], tube="oesophagus", sub=[],
         parent_bones={"chest": 0.5, "upper_chest": 0.5}, compartment="mediastinum", hit_priority=6,
         surface_colour="#C88878", interior_colour="#B06060", blend_shapes=[]),
    dict(id="larynx", organ_id=19, hit=["larynx"], sub=[], parent_bones={"neck": 1.0}, compartment="airway",
         hit_priority=7, surface_colour="#D8CFC6", interior_colour="#C09088", blend_shapes=[]),
    dict(id="diaphragm", organ_id=20, hit=[], sub=[], parent_bones={"chest": 0.5, "spine": 0.5},
         compartment="none", hit_priority=3, surface_colour="#8A2A28", interior_colour="#7A2424",
         blend_shapes=["diaphragm_inhale"]),
    dict(id="omentum", organ_id=21, hit=["omentum"], sub=[], parent_bones={"spine": 1.0},
         compartment="peritoneum", hit_priority=2, surface_colour="#E8C766", interior_colour="#E8C766",
         blend_shapes=[]),
    dict(id="pericardium", organ_id=22, hit=[], sub=[], parent_bones={"chest": 1.0}, compartment="pericardium",
         hit_priority=9, surface_colour="#D9CFC0", interior_colour="#7B2626", blend_shapes=[]),
    dict(id="bowel_filler", organ_id=23, hit=["bowel_filler"], sub=[], parent_bones={"spine": 0.5, "hips": 0.5},
         compartment="peritoneum", hit_priority=0, surface_colour="#3A1414", interior_colour="#3A1414",
         blend_shapes=[], note="lowest priority; intestines are not modelled (mass/volume filler only)"),
]
ORGAN_BY_ID = {o["id"]: o for o in ORGANS}

# Added primitives (B0 fit, E) for records without a bible primitive
PRIMITIVES["larynx"] = dict(shape="ellipsoid", c=(0.0, -0.040, 1.528), size=(0.042, 0.034, 0.050),
                            u=(1, 0, 0), v=(0, 1, 0), w=(0, 0, 1), mass_g=30.0, tag="E fit=B0")
PRIMITIVES["omentum"] = dict(shape="aabb", c=(0.0, -0.085, 1.035), size=(0.260, 0.010, 0.170),
                             u=(1, 0, 0), v=(0, 1, 0), w=(0, 0, 1), mass_g=300.0,
                             tag="E fit=B0 (apron z 1.12 -> 0.95, 5-10 mm thick)")

# ---------------------------------------------------------------------------
# Key organ facts (RB §7.5, R05 §10-11)
# ---------------------------------------------------------------------------
HEART = dict(
    mass_g=320, mass_range_g=(250, 380), size_cm=(12.5, 9.0, 6.5),
    axis_base=(0.0, -0.005, 1.360), axis_apex=(0.082, -0.068, 1.285),
    wall_mm={"LV": 9.0, "LV_range": (6, 10), "RV": (3, 5), "atria": (2, 3)},
    valves={"pulmonary": (0.022, -0.058, 1.378), "aortic": (0.008, -0.038, 1.360),
            "mitral": (0.030, -0.030, 1.340), "tricuspid": (-0.008, -0.048, 1.325)},
    pericardium_offset_mm=(2, 3), epicardial_fat="#E6C45A", myocardium="#7B2626",
    systole_volume_change=(-0.20, -0.15),
)
LUNGS = dict(
    apex_z=1.495, lower_border={"mcl_rib": 6, "mal_rib": 8, "back_rib": 10, "z": (1.27, 1.28)},
    pleura_border={"mcl_rib": 8, "mal_rib": 10, "back_rib": 12, "z": (1.21, 1.23)},
    tlc_l=7.1, frc_l=3.35, tidal_l=0.5, colour="#E0A0A0", anthracotic="#3A3A3A", dependent_pm="#A04A55",
    inhale_volume_change=0.10, collapse_volume_change=-0.70,
)
DIAPHRAGM = dict(dome_R_z=1.320, dome_L_z=1.300, central_tendon_z=1.310, excursion_quiet_m=(0.015, 0.020),
                 excursion_deep_m=(0.06, 0.10), openings={"ivc": "T8", "oesophagus": "T10", "aorta": "T12"})
LIVER = dict(mass_g=1550, range_g=(970, 1860), colour="#7A2E23",
             lower_edge="along the right costal margin, crosses the midline ~halfway xiphoid-navel")
SPLEEN = dict(mass_g=150, size_cm=(12, 7, 3), ribs=(9, 11), colour="#5E2433")
KIDNEYS = dict(mass_g=150, levels="T12-L3", right_lower_m=0.02, depth_from_back_skin_mm=(50, 70),
               perirenal_fat="#E8C766")
OMENTUM = dict(colour="#E8C766", thickness_mm=(5, 10), z_top=1.12, z_bottom=0.95,
               backing="dark peritoneal backing shell")
ORGAN_DENSITY_G_CM3 = 1.05       # plan §8.2 B4 mass check (volume x 1.05)
SUPINE_SHIFT_M = (0.02, 0.04)    # organs sit higher supine (cosmetic, post-mortem pose only)


def organ_hit_primitives(organ):
    """Hit primitive records for an organ (plan §5.8 'hit' entries)."""
    out = []
    for name in organ["hit"]:
        p = PRIMITIVES[name]
        out.append(_prim_record(name, p))
    return out


def _prim_record(name, p):
    shape = "obb" if p["shape"] in ("obb", "aabb") else p["shape"]
    return {"id": name, "shape": shape, "c": list(p["c"]), "size": list(p["size"]), "u": list(p["u"]),
            "v": list(p["v"])}


def organ_sub_primitives(organ):
    """Sub-part primitives (chambers, lobes) of an organ."""
    return [dict(_prim_record(n, PRIMITIVES[n]), sub_id=i + 1) for i, n in enumerate(organ["sub"])]
