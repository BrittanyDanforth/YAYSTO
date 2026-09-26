"""Vessel graph rows (RB §3.3; R03 §4-§11, R05 §10.4) - B0 transcription, B5 extends.

Every row of the bible's vessel table is here with its numbers kept verbatim
(``note`` keeps the original bleed text).  Where the bible gives only an end
point, a landmark phrase or "along X", B0 added the missing waypoints as E fits
(``fit_points`` lists which ones) so every segment is a usable polyline; B5
refines them (plan §3.4.1) and adds the K additions of the plan (intracranial
arteries, dural sinuses, epigastric, gluteal, lumbar, limb veins, azygos ...).

Conventions
-----------
* Waypoints: body frame, metres, LEFT side for bilateral rows (mirrored x for
  the right) unless ``pts_R`` gives the right side explicitly.
* ``listed``: order of the bible's waypoints.  ``vessel_segments()`` returns
  every segment *proximal first*: arteries start at their parent (upstream),
  veins start at the vessel they drain into (heart side).
* ``parent``: upstream vessel for arteries / the vessel a vein drains into; a
  heart chamber (LV, RV, RA, LA) marks a root.  A dict gives per-side parents.
* kind: E elastic artery, M muscular artery, V vein [RB §3.3].
* ``bleed``: initial rate at normal BP (mL/min), LOC (s) and death (min),
  untreated, supine [RB §3.3].
* Segment ids: ``<vessel>[_<branch>][_<L|R>]`` (side suffix only for bilateral rows).
"""
import numpy as np

# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------
ROWS = []


def _row(vid, name, kind, d_mm, d_range, flow, parent, side, branches, *, circuit="systemic_art",
         listed="proximal_first", pts_R=None, landmarks="", depth_mm=None, bleed=None, self_stop="no",
         compressible="no", stump_frac=None, collaterals=(), tag="V/C", fit_points=(), d_end_mm=None,
         d_R_mm=None, outlet_default="external", in_bone_canal=False, air_entry=False, pulse_delay_ms=None,
         extra_parents=(), branch_d_mm=None, branch_side=None, branch_parent=None, note=""):
    """Register one bible row.  ``branches``: list of (suffix, [points]) or a single point list."""
    if branches and not isinstance(branches[0][0], str):
        branches = [("", branches)]
    ROWS.append(dict(
        id=vid, name=name, kind=kind, d_mm=d_mm, d_range_mm=d_range, rest_flow_ml_min=flow, parent=parent,
        side=side, branches=branches, circuit=circuit, listed=listed, pts_R=pts_R, landmarks=landmarks,
        depth_mm=depth_mm, bleed=bleed or {}, self_stop=self_stop, compressible=compressible,
        stump_frac=stump_frac, collaterals=list(collaterals), tag=tag, fit_points=list(fit_points),
        d_end_mm=d_end_mm, d_R_mm=d_R_mm, outlet_default=outlet_default, in_bone_canal=in_bone_canal,
        air_entry=air_entry, pulse_delay_ms=pulse_delay_ms, extra_parents=list(extra_parents),
        branch_d_mm=branch_d_mm or {}, branch_side=branch_side or {}, branch_parent=branch_parent or {},
        note=note))


def _b(initial=None, loc_s=None, death_min=None, note=""):
    return {"initial_ml_min": initial, "loc_s": loc_s, "death_min": death_min, "note": note}


VEN = "systemic_ven"

# ===========================================================================
# Central and neck (RB §3.3)
# ===========================================================================
_row("A01", "ascending aorta", "E", 32.0, (28, 36), (5000, 5000), "LV", "mid",
     [(0.008, -0.038, 1.360), (-0.008, -0.048, 1.405)],
     landmarks="Behind left sternal half, 3rd ICS; inside pericardium; 4-6 cm deep", depth_mm=(40, 60),
     bleed=_b((3000, 6000), (5, 15), (1, 3)), outlet_default="pericardium")
_row("A02", "aortic arch", "E", 27.0, (25, 30), (3600, 5000), "A01", "mid",
     [(-0.008, -0.048, 1.405), (0.0, -0.020, 1.428), (0.022, 0.030, 1.418)],
     landmarks="Top 2-3 cm below the jugular notch; ends at T4", bleed=_b((3000, 6000), (5, 15), (1, 3), "as A01"),
     outlet_default="mediastinum")
_row("A03", "brachiocephalic trunk", "E", 12.0, (12, 12), (650, 800), "A02", "R",
     [(-0.002, -0.035, 1.430), (-0.025, -0.030, 1.455)],
     landmarks="Splits behind the right SC joint", bleed=_b((1000, 2500), (30, 90), None),
     outlet_default="mediastinum")
_row("A04", "common carotid", "E", 6.5, (6.0, 8.0), (350, 450), {"L": "A02", "R": "A03"}, "LR",
     [(0.010, -0.025, 1.432), (0.028, -0.018, 1.515), (0.030, -0.012, 1.558)],
     pts_R=[(-0.025, -0.030, 1.455), (-0.028, -0.018, 1.515), (-0.030, -0.012, 1.558)],
     landmarks="Beside trachea/larynx under the SCM anterior border, IJV lateral; bifurcation at upper "
               "thyroid cartilage (C3-C4); 1.5-4 cm deep", depth_mm=(15, 40),
     bleed=_b((1000, 2500), (20, 90), (2, 5), "+100-300 distal backflow"), compressible="partial (finger)",
     stump_frac=0.6, collaterals=["A06", "A05_other_side (circle of Willis)"], pulse_delay_ms=(90, 140),
     note="F 6.1 mm")
_row("A05", "internal carotid (cervical)", "E", 4.8, (4.0, 5.5), (220, 300), "A04", "LR",
     [(0.030, -0.012, 1.558), (0.024, 0.012, 1.625)],
     landmarks="No neck branches; enters the carotid canal in front of the jugular foramen; 2-4 cm",
     depth_mm=(20, 40), bleed=_b((500, 1000), (60, 180), (3, 8)), compressible="partial", stump_frac=0.6,
     collaterals=["A05 (circle of Willis, complete in 20-50 %)", "A06 via facial/angular, STA/supraorbital"],
     tag="E->M kind; waypoint 2 (E)", pulse_delay_ms=(90, 140))
_row("A06", "external carotid", "M", 4.0, (3.5, 5.0), (100, 150), "A04", "LR",
     [(0.030, -0.012, 1.558), (0.050, 0.000, 1.630)],
     landmarks="Ends in the parotid behind the mandibular neck", bleed=_b((200, 600), (180, 600), (5, 20)),
     self_stop="rarely", compressible="yes", stump_frac=0.6, tag="waypoint 2 (E)")
_row("A07", "superficial temporal", "M", 2.0, (1.5, 2.5), (10, 30), "A06", "LR",
     [("", [(0.050, 0.000, 1.630), (0.068, 0.002, 1.650), (0.070, 0.000, 1.680)]),
      ("frontal", [(0.070, 0.000, 1.680), (0.055, -0.060, 1.720)]),
      ("parietal", [(0.070, 0.000, 1.680), (0.065, 0.030, 1.740)])],
     branch_d_mm={"frontal": 1.5, "parietal": 1.5},
     landmarks="~1 cm in front of the tragus over the zygomatic root (palpable); 3-6 mm deep in scalp "
               "connective tissue", depth_mm=(3, 6),
     bleed=_b((20, 60), None, None, "both ends, pulsatile jet -> scalp-wound course"),
     self_stop="poorly (tethered)", compressible="yes", stump_frac=0.7, tag="E waypoints",
     note="per branch 16-18 mL/min (V); branches 1.2-1.8 mm")
_row("A08", "facial", "M", 2.5, (1.5, 2.5), (20, 40), "A06", "LR",
     [(0.035, -0.012, 1.570), (0.046, -0.032, 1.565), (0.035, -0.078, 1.592), (0.016, -0.072, 1.662)],
     d_end_mm=1.5, landmarks="Palpable notch 2.5-3 cm in front of the jaw angle; 5-10 mm deep; labial branches "
                             "1-1.5 mm inside the lips", depth_mm=(5, 10),
     bleed=_b((10, 40), None, None, "facial/labial, into mouth too"), self_stop="partially", compressible="yes",
     stump_frac=0.7, collaterals=["A05 via angular"], tag="E waypoints")
_row("A09", "occipital", "M", 2.0, (2.0, 2.0), (10, 20), "A06", "LR",
     [(0.034, 0.000, 1.575), (0.045, 0.040, 1.605), (0.032, 0.105, 1.650), (0.030, 0.105, 1.700)],
     fit_points=[0, 1], landmarks="Pierces fascia 2.5-4 cm lateral to the inion at the superior nuchal line; "
                                  "4-8 mm", depth_mm=(4, 8), bleed=_b((20, 60), None, None, "scalp"),
     self_stop="poorly", compressible="yes", stump_frac=0.7, tag="E waypoints")
_row("A10", "vertebral", "M", 3.5, (3.0, 4.0), (70, 120), "A14", "LR",
     [(0.030, -0.008, 1.440), (0.015, 0.004, 1.518), (0.015, 0.007, 1.536), (0.015, 0.008, 1.553),
      (0.015, 0.011, 1.570), (0.018, 0.016, 1.590), (0.030, 0.022, 1.610), (0.028, 0.035, 1.622),
      (0.008, 0.030, 1.630)],
     fit_points=[2, 3, 4, 5, 6],
     landmarks="In bone canal (C6 -> C1 transverse foramina, x +-0.015); loop behind the C1 lateral masses; "
               "4-7 cm deep", depth_mm=(40, 70),
     bleed=_b((100, 400), None, (5, 20), "often contained"), self_stop="often contained", compressible="no",
     in_bone_canal=True, outlet_default="neck_deep", tag="C5-C1 foramen points (E, fit B0)")
_row("A11", "basilar", "M", 3.5, (3.0, 4.0), (150, 200), "A10_L", "mid",
     [(0.0, -0.004, 1.645), (0.0, -0.004, 1.690)], extra_parents=["A10_R"],
     landmarks="Front of the pons on the clivus", bleed=_b(None, None, None, "intracranial (RB §3.9)"),
     outlet_default="cranium")
_row("A12", "middle meningeal", "M", 1.75, (1.5, 2.0), (5, 15), "A06", "LR",
     [(0.022, -0.002, 1.640), (0.050, -0.004, 1.660), (0.058, -0.008, 1.682)], fit_points=[0, 1],
     landmarks="Pterion ~3.5 cm above the midpoint of the zygomatic arch; inside the skull",
     bleed=_b((0.3, 2.0), None, None, "epidural haematoma 0.3-2 mL/min (RB §4.7)"),
     outlet_default="cranium_epidural", tag="parent = maxillary (branch of A06); flow E",
     note="parent in the bible: maxillary artery (terminal ECA branch)")
_row("A13", "coronary arteries", "M", 4.5, (3.5, 4.5), (225, 250), "A01", "mid",
     [("LM", [(0.010, -0.035, 1.365), (0.020, -0.045, 1.362)]),
      ("LAD", [(0.020, -0.045, 1.362), (0.040, -0.075, 1.340), (0.082, -0.068, 1.285)]),
      ("CX", [(0.020, -0.045, 1.362), (0.045, -0.020, 1.345), (0.060, 0.000, 1.320)]),
      ("RCA", [(0.000, -0.050, 1.360), (-0.035, -0.045, 1.330), (-0.030, -0.020, 1.300)])],
     branch_d_mm={"LM": 4.5, "LAD": 3.5, "CX": 3.5, "RCA": 3.8},
     branch_side={"LM": "L", "LAD": "L", "CX": "L", "RCA": "R"}, branch_parent={"RCA": "row"},
     landmarks="Epicardium", bleed=_b(None, None, None, "spurts in systole and diastole; downstream muscle "
                                                        "turns dusky and stops contracting in 1-5 min"),
     outlet_default="pericardium", stump_frac=0.3, tag="LM->LAD, RCA waypoints (E); CX (E, fit B0)",
     note="rest flow 225-250 total")
_row("A14", "subclavian", "E", 8.5, (7.0, 10.0), (200, 350), {"L": "A02", "R": "A03"}, "LR",
     [(0.020, -0.008, 1.430), (0.065, -0.015, 1.462), (0.090, -0.015, 1.450)],
     pts_R=[(-0.025, -0.030, 1.455), (-0.065, -0.015, 1.462), (-0.090, -0.015, 1.450)],
     landmarks="1.5-2 cm above mid-clavicle; behind anterior scalene; 3-5 cm deep", depth_mm=(30, 50),
     bleed=_b((1000, 2000), (60, 180), (3, 10)), compressible="poor", outlet_default="neck_deep")
_row("A15", "internal thoracic", "M", 2.5, (2.0, 3.0), (20, 50), "A14", "LR",
     [(0.030, -0.060, 1.440), (0.030, -0.060, 1.290)],
     landmarks="1-2 cm lateral to the sternal edge behind the cartilages",
     bleed=_b((50, 150), (1200, 3600), None, "into pleura, systemic pressure -> LOC 20-60 min"),
     outlet_default="pleura", tag="E waypoints")

# A16 intercostal arteries x 11 per side: generated along the lower inner border of ribs 1-11
# (bible: "Along the lower inner border of each rib (rib table)").  E fit B0.


def _intercostal_points(n):
    from .ribs import rib_points
    pts = np.array(rib_points(n), dtype=float)
    out = []
    for p in pts:
        inward = np.array([-p[0], 0.012 - p[1], 0.0])
        nrm = np.linalg.norm(inward)
        inward = inward / nrm if nrm > 1e-9 else inward
        q = p + np.array([0.0, 0.0, -0.007]) + 0.003 * inward
        out.append(tuple(float(round(c, 4)) for c in q))
    return out


for _n in range(1, 12):
    _row(f"A16", "intercostal", "M", 2.0, (1.5, 2.5), (5, 15), "A20" if _n >= 3 else "A14", "LR",
         [(f"{_n:02d}", _intercostal_points(_n))],
         landmarks="Costal groove (vein-artery-nerve top to bottom)", bleed=_b((50, 150), None, None, "-> hours"),
         outlet_default="pleura", tag="E fit B0 from the rib table",
         note="posterior intercostals 3-11 from the aorta, 1-2 via the supreme intercostal (subclavian)")

_row("V01", "internal jugular", "V", 14.0, (10, 20), (300, 700), "V03", "LR",
     [(0.030, 0.030, 1.625), (0.040, -0.018, 1.515), (0.028, -0.030, 1.448)], circuit=VEN, listed="distal_first",
     d_R_mm=16.0, landmarks="Line earlobe -> medial clavicle; < 20 mm deep; collapses when upright; tethered at "
                            "the root -> air entry", depth_mm=(0, 20),
     bleed=_b((200, 1000), (300, 1200), (10, 40), "supine"), compressible="yes", air_entry=True,
     note="R larger (d_R 16 mm, E)")
_row("V02", "external jugular", "V", 5.0, (4, 7), (20, 60), "V04", "LR",
     [(0.050, 0.000, 1.570), (0.085, -0.020, 1.485), (0.075, -0.020, 1.455)], circuit=VEN, listed="distal_first",
     landmarks="3-6 mm under the skin (platysma); visible when distended", depth_mm=(3, 6),
     bleed=_b((50, 200), None, None, "dark steady; air risk"), self_stop="sometimes", compressible="yes",
     air_entry=True, tag="E waypoints")
_row("V03", "brachiocephalic vein", "V", 14.0, (12, 16), None, "V05", "LR",
     [(0.028, -0.030, 1.448), (-0.020, -0.035, 1.440)],
     pts_R=[(-0.028, -0.030, 1.448), (-0.028, -0.035, 1.438)], circuit=VEN, listed="distal_first",
     landmarks="Behind the manubrium", bleed=_b(None, None, None, "into mediastinum"),
     outlet_default="mediastinum")
_row("V04", "subclavian vein", "V", 10.0, (7, 12), (150, 300), "V03", "LR",
     [(0.090, -0.025, 1.450), (0.028, -0.030, 1.448)], circuit=VEN, listed="distal_first",
     landmarks="In front of anterior scalene; ~5 mm above the apical pleura; held open -> air",
     bleed=_b((200, 800), (300, 1200), None, "+ air"), compressible="poor", air_entry=True)
_row("V05", "superior vena cava", "V", 20.0, (18, 22), (1300, 1700), "RA", "R",
     [(-0.028, -0.035, 1.438), (-0.028, -0.028, 1.378)], circuit=VEN, listed="distal_first",
     landmarks="Right sternal border; lower half intrapericardial",
     bleed=_b((500, 2000), None, (1, 5), "-> tamponade or mediastinum"), outlet_default="pericardium")
_row("P01", "pulmonary trunk and arteries", "E", 27.0, (25, 30), (5000, 5000), "RV", "mid",
     [("", [(0.022, -0.058, 1.378), (0.012, -0.030, 1.405)]),
      ("RPA", [(0.012, -0.030, 1.405), (-0.060, 0.005, 1.385)]),
      ("LPA", [(0.012, -0.030, 1.405), (0.055, 0.015, 1.395)])],
     branch_d_mm={"RPA": 20.0, "LPA": 20.0}, branch_side={"RPA": "R", "LPA": "L"}, circuit="pulmonary_art",
     landmarks="Mean pressure 15 mmHg", bleed=_b((1000, 4000), (30, 120), None, "hilar hit"),
     outlet_default="pericardium", note="low pressure elastic artery; RPA/LPA 18-22 mm")
_row("P02", "pulmonary veins", "V", 12.5, (10, 15), (5000, 5000), "LA", "mid",
     [("L_sup", [(0.050, 0.020, 1.388), (0.008, -0.008, 1.365)]),
      ("L_inf", [(0.050, 0.025, 1.380), (0.008, -0.008, 1.365)]),
      ("R_sup", [(-0.050, 0.020, 1.388), (0.008, -0.008, 1.365)]),
      ("R_inf", [(-0.050, 0.025, 1.380), (0.008, -0.008, 1.365)])],
     branch_side={"L_sup": "L", "L_inf": "L", "R_sup": "R", "R_inf": "R"}, branch_parent={"*": "row"},
     circuit="pulmonary_ven",
     listed="distal_first", landmarks="Hila -> LA", bleed=_b((1000, 4000), (30, 120), None, "as P01"),
     note="x4; 5,000 mL/min total")

# ===========================================================================
# Trunk, abdomen, pelvis
# ===========================================================================
_row("A20", "descending thoracic aorta", "E", 24.0, (20, 26), (3600, 3600), "A02", "mid",
     [(0.022, 0.030, 1.418), (0.020, 0.030, 1.329), (0.006, -0.012, 1.227)],
     landmarks="Left front of vertebral bodies; isthmus = blunt-rupture site",
     bleed=_b((2000, 5000), (10, 30), (1, 5), "into left pleura"), outlet_default="pleura_L")
_row("A21", "abdominal aorta", "E", 21.0, (18, 21), (1000, 3600), "A20", "mid",
     [(0.006, -0.012, 1.227), (0.008, -0.030, 1.180), (0.010, -0.045, 1.085)], d_end_mm=18.0,
     landmarks="Just left of midline on the vertebral bodies; bifurcation 1-2 cm below-left of the navel; "
               "~7-8 cm under navel skin (lean ~6)", depth_mm=(60, 80),
     bleed=_b((1500, 4000), (20, 60), (2, 10), "free; contained retroperitoneal 100-500 -> 5-30 min / hours"),
     outlet_default="retroperitoneum", note="F 16.7 mm")
_row("A22", "coeliac trunk", "M", 7.0, (7, 7), (800, 1100), "A21", "mid",
     [("", [(0.006, -0.020, 1.215), (0.006, -0.032, 1.212)]),
      ("splenic", [(0.006, -0.032, 1.212), (0.040, -0.030, 1.212), (0.095, 0.030, 1.225)]),
      ("hepatic", [(0.006, -0.032, 1.212), (-0.030, -0.020, 1.230)])],
     branch_d_mm={"splenic": 5.0, "hepatic": 4.5}, branch_side={"splenic": "L", "hepatic": "R"},
     landmarks="Deep", bleed=_b((300, 1000), None, None, "intraperitoneal"), outlet_default="peritoneum",
     stump_frac=0.3, tag="E waypoints; trunk end and splenic mid point fit B0")
_row("A23", "superior mesenteric", "M", 7.0, (7, 7), (500, 700), "A21", "mid",
     [(0.008, -0.030, 1.195), (0.010, -0.060, 1.120)], landmarks="Behind pancreatic neck",
     bleed=_b((300, 1000), None, None), outlet_default="peritoneum", stump_frac=0.3, tag="E waypoints")
_row("A24", "renal artery", "M", 5.5, (4, 7), (500, 600), "A21", "LR",
     [(0.008, -0.030, 1.180), (0.048, 0.010, 1.180)],
     pts_R=[(0.006, -0.028, 1.175), (-0.048, 0.010, 1.160)], fit_points=[0],
     landmarks="Right passes behind IVC", bleed=_b((300, 1000), (300, 1200), None,
                                                   "retroperitoneal (Gerota may contain)"),
     self_stop="partly", outlet_default="retroperitoneum", stump_frac=0.3)
_row("A25", "common iliac", "E", 10.0, (8.8, 10.0), (350, 500), "A21", "LR",
     [(0.010, -0.045, 1.085), (0.040, -0.030, 1.035)],
     pts_R=[(0.010, -0.045, 1.085), (-0.040, -0.030, 1.035)],
     landmarks="To the SI joint (L5/S1)", bleed=_b((1000, 2500), (120, 360), (5, 15), "retroperitoneal"),
     outlet_default="retroperitoneum")
_row("A26", "internal iliac", "M", 6.0, (5, 7), (100, 150), "A25", "LR",
     [(0.040, -0.030, 1.035), (0.050, 0.020, 0.980)], landmarks="Pelvis, gluteal",
     bleed=_b(None, None, None, "pelvic"), outlet_default="pelvis", tag="E waypoints")
_row("A27", "external iliac", "M", 8.0, (7, 9), (250, 350), "A25", "LR",
     [(0.040, -0.030, 1.035), (0.065, -0.068, 0.940)], landmarks="Along the pelvic brim, medial to psoas",
     bleed=_b((1000, 2500), None, None), outlet_default="retroperitoneum")
_row("A28", "common femoral", "M", 9.0, (8.2, 9.0), (250, 400), "A27", "LR",
     [(0.065, -0.068, 0.940), (0.068, -0.060, 0.895)],
     landmarks="Mid-inguinal point (midway ASIS-pubic symphysis); NAV lateral->medial; pulse palpable; "
               "2-4 cm deep", depth_mm=(20, 40), bleed=_b((800, 2000), (120, 300), (3, 10)),
     compressible="poor-moderate (junctional)", pulse_delay_ms=(150, 220), note="M 9.0 / F 8.2 mm (V)")
_row("A29", "profunda femoris", "M", 5.5, (5, 6), (100, 150), "A28", "LR",
     [(0.068, -0.060, 0.895), (0.090, -0.010, 0.800), (0.095, 0.010, 0.700)],
     landmarks="Posterolateral, deep (4-8 cm)", depth_mm=(40, 80), bleed=_b((400, 1000), (240, 600), (8, 20)),
     self_stop="rarely", compressible="yes (proximal)", stump_frac=0.5,
     collaterals=["A31 (profunda <-> popliteal)"], tag="E waypoints")
_row("A30", "superficial femoral", "M", 6.0, (5, 7), (150, 250), "A28", "LR",
     [(0.068, -0.060, 0.895), (0.075, -0.030, 0.760), (0.080, 0.030, 0.610)],
     landmarks="Anteromedial thigh (under sartorius); 3-6 cm deep; adductor hiatus", depth_mm=(30, 60),
     bleed=_b((400, 1000), None, None), self_stop="rarely", compressible="yes")
_row("A31", "popliteal", "M", 5.5, (5, 7), (80, 150), "A30", "LR",
     [(0.080, 0.030, 0.610), (0.092, 0.055, 0.497), (0.092, 0.055, 0.440)],
     landmarks="Deepest in the popliteal fossa, on the capsule; 3-5 cm", depth_mm=(30, 50),
     bleed=_b((300, 800), (300, 720), (10, 30)), self_stop="rarely", compressible="yes", stump_frac=0.5,
     collaterals=["geniculate network", "A29"])
_row("A32", "anterior tibial -> dorsalis pedis", "M", 3.0, (2.5, 3.5), (30, 50), "A31", "LR",
     [(0.092, 0.055, 0.440), (0.105, 0.020, 0.420), (0.100, -0.005, 0.250), (0.097, 0.012, 0.080),
      (0.105, -0.030, 0.050)], d_end_mm=2.5,
     landmarks="DP pulse lateral to the EHL tendon; ankle ~5 mm deep", depth_mm=(5, 20),
     bleed=_b((50, 200), (1200, 3600), (60, 180), "LOC 20-60+ min, death 1-3 h"), self_stop="often",
     compressible="yes", pulse_delay_ms=(220, 300), tag="E waypoints",
     note="waypoint (0.100,-0.005,0.250) lies at/over the shin skin line: B5 must deepen it (FB-5)")
_row("A33", "posterior tibial", "M", 3.0, (2.5, 3.5), (30, 50), "A31", "LR",
     [(0.092, 0.055, 0.440), (0.088, 0.060, 0.250), (0.075, 0.075, 0.080)],
     landmarks="Between medial malleolus and Achilles; ~1 cm deep at the ankle", depth_mm=(8, 12),
     bleed=_b((50, 200), None, None), self_stop="often", compressible="yes", tag="E waypoints")
_row("A34", "peroneal", "M", 2.5, (2.5, 2.5), (20, 40), "A33", "LR",
     [(0.095, 0.060, 0.420), (0.120, 0.055, 0.200)], landmarks="Along the fibula, deep",
     bleed=_b((50, 150), None, None), self_stop="often", tag="E waypoints")
_row("V10", "inferior vena cava", "V", 17.0, (13, 21), (3000, 3500), "RA", "R",
     [(-0.020, -0.035, 1.050), (-0.022, -0.015, 1.260), (-0.022, -0.010, 1.325), (-0.025, -0.015, 1.315)],
     circuit=VEN, listed="distal_first", landmarks="Right of the aorta; retrohepatic part embedded in liver",
     bleed=_b((500, 2000), (60, 300), None, "infrarenal 500-2,000 (50-200 tamponaded); retrohepatic/hepatic "
                                            "veins 1,000-3,000 -> 1-5 min"),
     self_stop="partly / no", outlet_default="retroperitoneum")
_row("V11", "hepatic veins", "V", 10.0, (8, 12), (1350, 1350), "V10", "mid",
     [("right", [(-0.085, 0.000, 1.270), (-0.022, -0.012, 1.300)]),
      ("middle", [(-0.040, -0.030, 1.265), (-0.022, -0.012, 1.300)]),
      ("left", [(0.020, -0.035, 1.275), (-0.022, -0.012, 1.300)])],
     circuit=VEN, listed="distal_first", branch_parent={"*": "row"},
     landmarks="Just below the diaphragm; into IVC ~(-0.022,-0.012,1.300)",
     bleed=_b((1000, 3000), (60, 300), None), outlet_default="peritoneum", tag="E fit B0 (x3)")
_row("V12", "renal vein", "V", 9.0, (7, 9), (550, 550), "V10", "LR",
     [(0.048, 0.010, 1.180), (0.008, -0.045, 1.178), (-0.020, -0.030, 1.175)],
     pts_R=[(-0.048, 0.010, 1.160), (-0.022, -0.025, 1.165)], d_R_mm=7.0, circuit=VEN, listed="distal_first",
     landmarks="Left crosses in front of the aorta below the SMA", bleed=_b(None, None, None, "retroperitoneal"),
     self_stop="partly", outlet_default="retroperitoneum", tag="E waypoints")
_row("V13", "portal vein", "V", 11.0, (10, 13), (1000, 1200), "V11_middle", "mid",
     [(-0.005, -0.045, 1.175), (-0.030, -0.020, 1.235)], circuit="portal", listed="distal_first",
     landmarks="Hepatoduodenal ligament; drains into the liver (sinusoids -> hepatic veins)",
     bleed=_b((500, 1500), (300, 900), (10, 40)), outlet_default="peritoneum", tag="E waypoints",
     note="formed by the SMV + splenic vein (B5 additions); parent = liver -> hepatic veins")
_row("V14", "common iliac vein", "V", 14.0, (12, 16), (500, 500), "V10", "LR",
     [(-0.020, -0.035, 1.050), (0.045, -0.020, 1.030)],
     pts_R=[(-0.020, -0.035, 1.050), (-0.045, -0.020, 1.030)], circuit=VEN,
     landmarks="Behind and right of the arteries", bleed=_b(None, None, None, "pelvic"),
     outlet_default="retroperitoneum", tag="E waypoints")
_row("V15", "common femoral vein", "V", 12.0, (10, 14), (250, 400), "V14", "LR",
     [(0.045, -0.020, 1.030), (0.055, -0.066, 0.940), (0.060, -0.058, 0.895)], circuit=VEN,
     landmarks="Medial to the artery, 2-4 cm deep; ~80-90 mmHg at the foot when standing still",
     depth_mm=(20, 40), bleed=_b((200, 600), (600, 1800), None, "more if the leg hangs"),
     self_stop="sometimes", compressible="yes", tag="E waypoints")
_row("V16", "femoral / popliteal veins", "V", 10.0, (8, 12), None, "V15", "LR",
     [("femoral", [(0.060, -0.058, 0.895), (0.069, -0.024, 0.760), (0.080, 0.040, 0.610)]),
      ("popliteal", [(0.080, 0.040, 0.610), (0.092, 0.064, 0.497), (0.092, 0.064, 0.440)])],
     branch_d_mm={"popliteal": 8.0}, circuit=VEN, landmarks="Deep veins alongside A30 / A31",
     bleed=_b((100, 400), None, None), self_stop="sometimes", compressible="yes",
     tag="E fit B0: A30/A31 offset medial/posterior")
_row("V17", "great saphenous", "V", 4.0, (3, 5), None, "V15", "LR",
     [(0.060, 0.030, 0.085), (0.060, 0.050, 0.500), (0.038, -0.038, 0.700), (0.050, -0.065, 0.885)],
     circuit=VEN, listed="distal_first", fit_points=[2], d_end_mm=7.0,
     landmarks="Just under the skin: in front of medial malleolus -> behind medial femoral condyle -> "
               "anteromedial thigh -> SFJ 3-4 cm below-lateral pubic tubercle", depth_mm=(2, 6),
     bleed=_b((20, 100), None, None), self_stop="yes", compressible="yes", tag="E waypoints",
     note="6-8 mm at the junction")

# ===========================================================================
# Upper limb (A-pose; d = (0.5, 0, -0.866); n_m = (-0.866, 0, -0.5); radial side = -Y) (E)
# ===========================================================================
_row("A40", "axillary", "M", 6.5, (5, 8), (100, 200), "A14", "LR",
     [(0.090, -0.015, 1.450), (0.140, 0.000, 1.410), (0.188, 0.015, 1.350)],
     landmarks="Behind pectoralis minor, among plexus cords; 3-5 cm", depth_mm=(30, 50),
     bleed=_b((600, 1500), (120, 300), (5, 15)), compressible="poor (junctional)", tag="E waypoints")
_row("A41", "brachial", "M", 4.2, (3.5, 5.0), (50, 120), "A40", "LR",
     [(0.188, 0.015, 1.350), (0.231, 0.015, 1.277), (0.328, 0.005, 1.148)],
     landmarks="With the median nerve; 1-2 cm deep mid-arm, ~1 cm at the elbow; divides 1-2 cm below the "
               "elbow crease", depth_mm=(10, 20),
     bleed=_b((200, 600), (600, 900), (15, 30), "side laceration ~400 -> Class II 3 min, LOC 10-15 min, "
                                                "arrest 15-30 min; transected 200-600"),
     self_stop="sometimes (spasm)", compressible="yes", tag="E waypoints")
_row("A42", "radial", "M", 2.5, (2.2, 3.0), (20, 40), "A41", "LR",
     [(0.328, 0.005, 1.148), (0.385, 0.005, 1.043), (0.447, 0.005, 0.923)],
     landmarks="At the wrist between the FCR tendon and radial styloid, 3-7 mm deep", depth_mm=(2, 7),
     bleed=_b((100, 300), None, None, "first min -> 20-60 after spasm; stops in 5-20 min after 200-500 mL"),
     self_stop="usually", compressible="yes", stump_frac=0.7, collaterals=["A43 via A44 (palmar arches)"],
     pulse_delay_ms=(170, 250), tag="E waypoints", note="RB §7.6 / FB-5: radial 2-5 mm at the wrist")
_row("A43", "ulnar", "M", 2.4, (2.0, 3.0), (20, 40), "A41", "LR",
     [(0.328, 0.005, 1.148), (0.380, 0.030, 1.050), (0.450, 0.035, 0.924)], fit_points=[1],
     landmarks="Lateral to the FCU tendon/pisiform; 5-10 mm", depth_mm=(5, 10),
     bleed=_b((100, 300), None, None, "as radial"), self_stop="usually", compressible="yes", stump_frac=0.7,
     collaterals=["A42 via A44"], tag="E waypoints")
_row("A44", "palmar arches", "M", 1.75, (1.5, 2.0), (1, 5), "A43", "LR",
     [(0.466, 0.035, 0.900), (0.475, 0.020, 0.881), (0.470, 0.002, 0.893)], fit_points=[0, 2],
     extra_parents=["A42"], landmarks="Superficial arch at the distal border of the extended thumb",
     bleed=_b((5, 30), None, None), self_stop="yes", compressible="yes", tag="E fit B0 around the bible point",
     note="digital arteries 0.8-1.6 mm, 1-5 mL/min per digit")
_row("V20", "superficial arm veins", "V", 3.5, (2, 6), None, "V04", "LR",
     [("cephalic", [(0.452, -0.008, 0.935), (0.390, -0.015, 1.050), (0.342, -0.015, 1.174),
                    (0.270, -0.025, 1.300), (0.150, -0.070, 1.400), (0.110, -0.045, 1.440)]),
      ("basilic", [(0.452, 0.045, 0.930), (0.385, 0.045, 1.045), (0.299, 0.035, 1.149), (0.240, 0.030, 1.280)]),
      ("median_cubital", [(0.345, -0.020, 1.140), (0.310, -0.010, 1.165)])],
     branch_d_mm={"cephalic": 3.5, "basilic": 4.5, "median_cubital": 3.5}, branch_parent={"basilic": "row"},
     circuit=VEN, listed="distal_first",
     landmarks="Cephalic: lateral arm (deltopectoral groove) / basilic: medial arm / median cubital: cubital fossa. "
               "Visible; flatten and vanish in shock", depth_mm=(1, 4), bleed=_b((5, 30), None, None),
     self_stop="yes", compressible="yes", tag="E fit B0 (all waypoints)",
     note="cephalic 2-5, basilic 3-6, median cubital 2-5 mm; drain via the axillary vein (B5 addition) -> V04")

# ---------------------------------------------------------------------------
# Capillary beds [RB §3.3] (Tier 2 R_bed = (P_art - P_ven) / Q_rest)
# ---------------------------------------------------------------------------
BEDS = [
    dict(id="brain", q_rest_ml_min=750, compartment="cranium"),
    dict(id="coronary", q_rest_ml_min=237, q_range=(225, 250), compartment="pericardium"),
    dict(id="kidneys", q_rest_ml_min=1175, q_range=(1100, 1250), compartment="retroperitoneum"),
    dict(id="liver", q_rest_ml_min=1350, note="portal ~1,050 + arterial ~300", compartment="peritoneum"),
    dict(id="skeletal_muscle", q_rest_ml_min=875, q_range=(750, 1000), compartment="per limb / trunk",
         by_limb={"arm_L": 0.08, "arm_R": 0.08, "leg_L": 0.22, "leg_R": 0.22, "trunk": 0.40}),
    dict(id="skin", q_rest_ml_min=350, q_range=(250, 450), note="drops 70-90 % in shock", compartment="external"),
    dict(id="bone", q_rest_ml_min=250, compartment="per bone"),
    dict(id="spleen", q_rest_ml_min=225, q_range=(150, 300), compartment="peritoneum"),
    dict(id="scalp", q_rest_ml_min=75, q_range=(50, 100), compartment="external"),
]
# muscle split by limb is E (G1 may re-weight)

# Collaterals for distal-stump backflow [RB §3.3]: stump pressure 0.3-0.8 x MAP
COLLATERALS = [
    dict(a="A42", b="A43", via="A44 palmar arches", stump_frac=(0.6, 0.8)),
    dict(a="A05_L", b="A05_R", via="circle of Willis (complete in 20-50 %)", stump_frac=(0.3, 0.8)),
    dict(a="A06", b="A05", via="facial/angular and STA/supraorbital", stump_frac=(0.5, 0.7)),
    dict(a="A31", b="A30", via="geniculate network", stump_frac=(0.3, 0.6)),
    dict(a="A29", b="A31", via="profunda <-> popliteal", stump_frac=(0.3, 0.6)),
]
SCALP_FACE_BOTH_ENDS = ("A07", "A08", "A09")        # bleed from both cut ends

PULSE = dict(pre_ejection_ms=(60, 100), pwv_aorta_m_s=6.0, pwv_peripheral_m_s=9.0,
             delay_ms={"carotid": (90, 140), "femoral": (150, 220), "radial": (170, 250),
                       "dorsalis_pedis": (220, 300)})
COLOURS = {"arterial": "#C0141E", "venous": "#8E1420", "pool": "#5E070C"}

# Tube meshing rules (plan §3.4.1)
TUBE_SIDES = [(15.0, 12), (6.0, 8), (3.0, 6), (1.5, 4)]     # (min diameter mm, sides); < 1.5 mm: data only
RESAMPLE_STEP = "min(10 mm, 2 * diameter)"


def tube_sides(d_mm):
    """Number of tube sides for a vessel diameter (0 = data only)."""
    for dmin, n in TUBE_SIDES:
        if d_mm >= dmin:
            return n
    return 0


def _seg_id(vid, suffix, side, bilateral):
    s = vid + (f"_{suffix}" if suffix else "")
    return s + (f"_{side}" if bilateral else "")


CHAMBERS = ("LV", "RV", "RA", "LA")


def _row_by_id(vid):
    return next((r for r in ROWS if r["id"] == vid), None)


def _resolve_parent(pid, side, bilateral):
    """Row-level parent id -> segment id (adds the side suffix for bilateral parent rows)."""
    if pid in CHAMBERS:
        return pid
    prow = _row_by_id(pid)
    if prow is not None and prow["side"] == "LR" and bilateral:
        return f"{pid}_{side}"
    return pid


def vessel_segments():
    """Expand ``ROWS`` into segments (left/right, branches), proximal-first, with parents resolved.

    Returns a list of dicts in a stable order with keys: id, vessel, branch, name, side, kind, circuit,
    d_mm, d_end_mm, d_range_mm, rest_flow_ml_min, parent, children, root, points (waypoints, proximal
    first), vessel_index and the row's landmark/bleed/haemostasis fields."""
    segs = []
    for r in ROWS:
        bilateral = r["side"] == "LR"
        for side in (("L", "R") if bilateral else (r["side"],)):
            first_id = None
            for bi, (suffix, pts) in enumerate(r["branches"]):
                if side == "R" and bilateral:
                    if r["pts_R"] is not None and bi == 0:
                        p = [tuple(q) for q in r["pts_R"]]
                    else:
                        p = [(-q[0], q[1], q[2]) for q in pts]
                else:
                    p = [tuple(q) for q in pts]
                if r["listed"] == "distal_first":
                    p = p[::-1]
                d = r["branch_d_mm"].get(suffix, r["d_mm"])
                if side == "R" and r["d_R_mm"] and bi == 0:
                    d = r["d_R_mm"]
                rule = r["branch_parent"].get(suffix, r["branch_parent"].get("*"))
                if bi == 0 or rule == "row":
                    par = r["parent"][side] if isinstance(r["parent"], dict) else r["parent"]
                    parent = _resolve_parent(par, side, bilateral)
                elif rule:
                    parent = rule
                else:
                    parent = first_id
                sid = _seg_id(r["id"], suffix, side, bilateral)
                if bi == 0:
                    first_id = sid
                extra = [_resolve_parent(e, side, bilateral) for e in r["extra_parents"]]
                segs.append(dict(
                    id=sid, vessel=r["id"], branch=suffix, name=r["name"],
                    side=side if bilateral else r["branch_side"].get(suffix, side), kind=r["kind"],
                    circuit=r["circuit"], d_mm=d, d_end_mm=r["d_end_mm"] if bi == 0 else None,
                    d_range_mm=r["d_range_mm"], rest_flow_ml_min=r["rest_flow_ml_min"], parent=parent,
                    extra_parents=extra, children=[], root=parent in CHAMBERS, points=p,
                    landmarks=r["landmarks"], depth_mm=r["depth_mm"], bleed_ref=r["bleed"],
                    self_stop=r["self_stop"], compressible=r["compressible"], stump_frac=r["stump_frac"],
                    collaterals=r["collaterals"], outlet_default=r["outlet_default"],
                    in_bone_canal=r["in_bone_canal"], air_entry=r["air_entry"],
                    pulse_delay_ms=r["pulse_delay_ms"], fit_points=r["fit_points"], tag=r["tag"],
                    note=r["note"], source="RB 3.3"))
    by_id = {s["id"]: s for s in segs}
    if len(by_id) != len(segs):
        raise ValueError("duplicate vessel segment ids")
    for s in segs:
        if s["parent"] in by_id:
            by_id[s["parent"]]["children"].append(s["id"])
    for i, s in enumerate(segs):
        s["vessel_index"] = i
    return segs


def vessel_ids():
    """Bible vessel ids present (A01 ...)."""
    return sorted({r["id"] for r in ROWS})
