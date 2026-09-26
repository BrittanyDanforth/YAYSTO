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
      (0.016, 0.037, 1.617), (0.010, 0.022, 1.619), (0.0, 0.014, 1.624)],
     fit_points=[2, 3, 4, 5, 6, 8, 9, 10],
     landmarks="In bone canal (C6 -> C1 transverse foramina, x +-0.015); loop behind the C1 lateral masses; "
               "4-7 cm deep", depth_mm=(40, 70),
     bleed=_b((100, 400), None, (5, 20), "often contained"), self_stop="often contained", compressible="no",
     in_bone_canal=True, outlet_default="neck_deep", tag="C5-C1 foramen points (E, fit B0); end (B5)",
     note="B5: the bible end point (0.008, 0.030, 1.630) lies inside the modelled medulla (gore_head brainstem); "
          "the artery now enters the foramen magnum lateral to the medulla and curves in front of it to "
          "the basilar origin at the pontomedullary junction")
_row("A11", "basilar", "M", 3.5, (3.0, 4.0), (150, 200), "A10_L", "mid",
     [(0.0, 0.014, 1.624), (0.0, 0.013, 1.653)], extra_parents=["A10_R"],
     landmarks="Front of the pons on the clivus", bleed=_b(None, None, None, "intracranial (RB §3.9)"),
     outlet_default="cranium", tag="B5 fit to the modelled pons",
     note="B5: bible (0,-0.004,1.645)->(0,-0.004,1.690) lies 20 mm in front of the gore_head pons (front at "
          "y 0.016-0.019 for z 1.632-1.648), i.e. in the clivus; moved onto the pons, top at the interpeduncular "
          "fossa where the posterior cerebral arteries arise")
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
     [(0.092, 0.055, 0.440), (0.108, 0.038, 0.420), (0.112, 0.034, 0.250), (0.104, 0.030, 0.140),
      (0.097, 0.025, 0.085), (0.105, -0.030, 0.050)], d_end_mm=2.5,
     landmarks="DP pulse lateral to the EHL tendon; ankle ~5 mm deep", depth_mm=(5, 20),
     bleed=_b((50, 200), (1200, 3600), (60, 180), "LOC 20-60+ min, death 1-3 h"), self_stop="often",
     compressible="yes", pulse_delay_ms=(220, 300), tag="E waypoints",
     note="B5: bible E waypoints (0.105,0.020,0.420), (0.100,-0.005,0.250), (0.097,0.012,0.080) lay in the tibia or "
          "25 mm in front of the built shin; moved onto the interosseous membrane between the built tibia and "
          "fibula and under the front of the ankle")
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
_row("V17", "great saphenous", "V", 6.5, (3, 8), None, "V15", "LR",
     [(0.060, 0.030, 0.085), (0.060, 0.050, 0.500), (0.038, -0.038, 0.700), (0.050, -0.065, 0.885)],
     circuit=VEN, listed="distal_first", fit_points=[2], d_end_mm=3.5,
     landmarks="Just under the skin: in front of medial malleolus -> behind medial femoral condyle -> "
               "anteromedial thigh -> SFJ 3-4 cm below-lateral pubic tubercle", depth_mm=(2, 6),
     bleed=_b((20, 100), None, None), self_stop="yes", compressible="yes", tag="E waypoints",
     note="4 mm (3-5) along the leg, 6-8 mm at the junction: d_mm is the proximal (junction) end, d_end the "
          "ankle (B5 fix: segments run proximal first)")

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
_row("V20", "superficial arm veins", "V", 3.5, (2, 6), None, "V21", "LR",
     [("cephalic", [(0.452, -0.008, 0.935), (0.390, -0.015, 1.050), (0.342, -0.015, 1.174),
                    (0.270, -0.025, 1.300), (0.150, -0.070, 1.400), (0.125, -0.058, 1.425),
                    (0.105, -0.021, 1.439)]),
      ("basilic", [(0.452, 0.045, 0.930), (0.385, 0.045, 1.045), (0.299, 0.035, 1.149), (0.240, 0.030, 1.280)]),
      ("median_cubital", [(0.345, -0.020, 1.140), (0.310, -0.010, 1.165)])],
     branch_d_mm={"cephalic": 3.5, "basilic": 4.5, "median_cubital": 3.5}, branch_parent={"basilic": "row"},
     circuit=VEN, listed="distal_first",
     landmarks="Cephalic: lateral arm (deltopectoral groove) / basilic: medial arm / median cubital: cubital fossa. "
               "Visible; flatten and vanish in shock", depth_mm=(1, 4), bleed=_b((5, 30), None, None),
     self_stop="yes", compressible="yes", tag="E fit B0 (all waypoints)",
     note="cephalic 2-5, basilic 3-6, median cubital 2-5 mm; drain via the axillary vein (V21, B5) -> V04")

# ===========================================================================
# B5 additions (plan §3.4.1 list; K = standard anatomy, QA re-check; waypoints E fits by B5 to the
# gb_data landmark/vertebra/rib/organ tables and to the head project's brain and skull)
# ===========================================================================
K5 = "K (B5 addition, QA re-check); waypoints E fit B5"
CRAN = "cranium"

# --- intracranial arteries (circle of Willis) -----------------------------------------------------
# The head project's brainstem lies ~20 mm behind the RB §3.3 basilar line (pons front at y ~ 0.016 for
# z 1.632-1.648 in GB_Brain; basion (0, 0.018, 1.626)).  The bible basilar/vertebral end points would sit
# in the clivus / medulla, so B5 follows the modelled brain (vascular.FIT 'cranial' keeps every
# intracranial vessel outside GB_Brain and inside the skull).  Bible points kept in ``bible_points``.
_row("A50", "internal carotid (petrous, cavernous, supraclinoid)", "M", 4.0, (3.5, 5.0), (220, 300), "A05", "LR",
     [(0.024, 0.012, 1.625), (0.021, 0.004, 1.631), (0.018, -0.004, 1.638), (0.017, -0.013, 1.646),
      (0.015, -0.011, 1.655), (0.016, -0.004, 1.659)],
     landmarks="Carotid canal in the petrous bone -> cavernous sinus beside the sella -> siphon -> terminal "
               "bifurcation under the anterior perforated substance", in_bone_canal=True, outlet_default=CRAN,
     bleed=_b((300, 800), (10, 60), (2, 10), "intracranial: subarachnoid/carotid-cavernous; external only "
                                           "through an open skull base"), stump_frac=0.5,
     collaterals=["circle of Willis"], tag=K5, note="4 mm (plan §3.4.1)")
_row("A51", "middle cerebral", "M", 3.0, (2.5, 3.5), (120, 160), "A50", "LR",
     [("", [(0.016, -0.004, 1.659), (0.028, -0.008, 1.660), (0.040, -0.010, 1.662)]),
      ("M2", [(0.040, -0.010, 1.662), (0.046, 0.000, 1.671), (0.048, 0.020, 1.684), (0.046, 0.040, 1.697)])],
     branch_d_mm={"M2": 2.2}, landmarks="M1 laterally in the stem of the lateral fissure; M2 over the insula",
     outlet_default=CRAN, bleed=_b((50, 150), (30, 300), None, "subarachnoid / intracerebral (RB §3.9)"),
     stump_frac=0.2, tag=K5, note="M1 3 mm (plan §3.4.1); end artery -> distal territory ischaemic")
_row("A52", "anterior cerebral", "M", 2.0, (1.5, 2.5), (60, 90), "A50", "LR",
     [("", [(0.016, -0.004, 1.659), (0.009, -0.015, 1.663), (0.003, -0.020, 1.665)]),
      ("A2", [(0.003, -0.020, 1.665), (0.003, -0.037, 1.680), (0.003, -0.046, 1.704), (0.003, -0.036, 1.728),
              (0.003, -0.008, 1.740), (0.003, 0.030, 1.735)])],
     branch_d_mm={"A2": 1.8}, landmarks="A1 over the optic chiasm; A2 / pericallosal in the interhemispheric "
                                        "fissure around the corpus callosum", outlet_default=CRAN,
     bleed=_b((20, 80), (60, 600), None, "subarachnoid"), stump_frac=0.3, tag=K5, note="A1 2 mm (plan §3.4.1)")
_row("A53", "posterior cerebral", "M", 2.0, (1.8, 2.5), (50, 70), "A11", "LR",
     [(0.000, 0.014, 1.654), (0.010, 0.012, 1.657), (0.020, 0.018, 1.658), (0.028, 0.032, 1.656),
      (0.030, 0.055, 1.650), (0.026, 0.080, 1.645)],
     landmarks="From the basilar tip around the midbrain (ambient cistern) to the medial occipital lobe",
     outlet_default=CRAN, bleed=_b((20, 80), (60, 600), None, "subarachnoid"), stump_frac=0.3, tag=K5)
_row("A54", "posterior communicating", "M", 1.5, (1.0, 2.0), (0, 10), "A50", "LR",
     [(0.016, -0.006, 1.657), (0.013, 0.003, 1.657), (0.010, 0.012, 1.657)], extra_parents=["A53"],
     landmarks="Circle of Willis ICA <-> PCA (complete in 20-50 %)", outlet_default=CRAN,
     bleed=_b((5, 30), None, None, "subarachnoid"), tag=K5)

# --- dural venous sinuses (drain the brain to the internal jugular veins) -------------------------
_row("V30", "superior sagittal sinus", "V", 9.0, (8, 10), (300, 450), "V31_R", "mid",
     [(0.0, -0.052, 1.712), (0.0, -0.040, 1.742), (0.0, -0.012, 1.762), (0.0, 0.030, 1.765),
      (0.0, 0.068, 1.743), (0.0, 0.094, 1.705), (0.0, 0.100, 1.665)],
     circuit=VEN, listed="distal_first", d_end_mm=3.0,
     landmarks="Midline under the inner table of the vault, from the foramen caecum to the confluence at the "
               "internal occipital protuberance; triangular section, rigid walls (does not collapse)",
     outlet_default=CRAN, air_entry=True, depth_mm=(10, 20),
     bleed=_b((100, 500), (60, 600), None, "open skull: heavy dark venous welling, air entry when upright"),
     compressible="no", tag=K5, note="8-10 mm, triangular (plan §3.4.1); section 'tri' in vascular.py")
_row("V31", "transverse sinus", "V", 8.0, (7, 9), (250, 350), "V32", "LR",
     [(0.0, 0.100, 1.665), (0.028, 0.094, 1.658), (0.048, 0.076, 1.650), (0.055, 0.056, 1.644)],
     circuit=VEN, listed="distal_first", outlet_default=CRAN, air_entry=True, depth_mm=(12, 25),
     landmarks="Along the attached margin of the tentorium on the occipital bone", compressible="no",
     bleed=_b((100, 400), (60, 600), None, "open skull"), tag=K5, note="right usually dominant (takes the SSS)")
_row("V32", "sigmoid sinus", "V", 7.0, (6, 8), (250, 350), "V01", "LR",
     [(0.055, 0.056, 1.644), (0.053, 0.044, 1.633), (0.045, 0.036, 1.625), (0.034, 0.031, 1.625),
      (0.030, 0.030, 1.625)],
     circuit=VEN, listed="distal_first", outlet_default=CRAN, air_entry=True, depth_mm=(12, 25),
     landmarks="S-curve in a groove on the mastoid part of the temporal bone, behind the ear, to the jugular "
               "foramen", compressible="no", bleed=_b((100, 400), (60, 600), None, "open skull / mastoid"),
     tag=K5)

# --- face and scalp veins --------------------------------------------------------------------------
_row("V33", "facial vein", "V", 3.0, (2.5, 4.0), (20, 40), "V01", "LR",
     [(0.017, -0.075, 1.664), (0.030, -0.073, 1.622), (0.038, -0.060, 1.590), (0.046, -0.036, 1.566),
      (0.040, -0.008, 1.558)],
     circuit=VEN, listed="distal_first", landmarks="Angular vein at the medial canthus -> behind the facial "
                                                   "artery across the cheek -> jaw at the masseter -> IJV",
     depth_mm=(5, 12), bleed=_b((10, 40), None, None, "dark welling (valveless, drains the face)"),
     self_stop="partially", compressible="yes", tag=K5)
_row("V34", "retromandibular vein", "V", 4.0, (3, 5), (20, 50), "V02", "LR",
     [(0.061, 0.006, 1.648), (0.058, 0.004, 1.625), (0.054, 0.002, 1.598), (0.050, 0.000, 1.572)],
     circuit=VEN, listed="distal_first", landmarks="In the parotid behind the mandibular ramus; its posterior "
                                                   "division forms the external jugular vein",
     depth_mm=(10, 25), bleed=_b((20, 80), None, None), self_stop="sometimes", compressible="yes", tag=K5)
_row("V35", "superficial temporal vein", "V", 2.0, (1.5, 2.5), (10, 20), "V34", "LR",
     [(0.063, 0.032, 1.738), (0.070, 0.006, 1.690), (0.068, 0.006, 1.660), (0.061, 0.006, 1.648)],
     circuit=VEN, listed="distal_first", landmarks="With the superficial temporal artery in front of the ear",
     depth_mm=(3, 6), bleed=_b((10, 30), None, None, "scalp: both ends bleed"), self_stop="poorly",
     compressible="yes", tag=K5)

# --- upper limb and axilla ------------------------------------------------------------------------
_row("A45", "profunda brachii", "M", 2.5, (2.0, 3.0), (10, 30), "A41", "LR",
     [(0.198, 0.017, 1.334), (0.222, 0.040, 1.302), (0.258, 0.042, 1.252), (0.296, 0.012, 1.206),
      (0.318, 0.000, 1.182)],
     landmarks="With the radial nerve in the spiral groove behind the humerus", depth_mm=(25, 45),
     bleed=_b((30, 100), None, None), self_stop="often", compressible="partial", tag=K5)
_row("A46", "subscapular", "M", 4.0, (3, 5), (30, 60), "A40", "LR",
     [(0.172, 0.012, 1.372), (0.155, 0.040, 1.345), (0.135, 0.062, 1.310), (0.115, 0.080, 1.275)],
     landmarks="Along the lateral border of the scapula (thoracodorsal continuation)", depth_mm=(30, 60),
     bleed=_b((100, 300), None, None), compressible="no", tag=K5)
_row("A47", "lateral thoracic", "M", 2.0, (1.5, 2.5), (10, 20), "A40", "LR",
     [(0.140, 0.000, 1.410), (0.146, -0.015, 1.370), (0.152, -0.022, 1.310), (0.152, -0.020, 1.240)],
     landmarks="On serratus anterior along the lateral chest wall", depth_mm=(12, 30),
     bleed=_b((20, 60), None, None), self_stop="often", compressible="yes", tag=K5)
_row("V21", "axillary vein", "V", 11.0, (10, 12), (100, 200), "V04", "LR",
     [(0.232, 0.030, 1.285), (0.212, 0.022, 1.312), (0.186, 0.008, 1.352), (0.140, -0.010, 1.412),
      (0.090, -0.025, 1.450)],
     circuit=VEN, listed="distal_first", landmarks="Medial (in front of and below) the axillary artery; from "
                                                   "the lower border of teres major to the first rib",
     depth_mm=(25, 50), bleed=_b((100, 400), (600, 1800), None, "dark, air entry near the clavicle"),
     compressible="poor (junctional)", air_entry=True, tag=K5, note="10-12 mm (plan §3.4.1)")
_row("V22", "brachial veins", "V", 3.5, (3, 5), (50, 120), "V21", "LR",
     [("a", [(0.331, 0.012, 1.150), (0.272, 0.024, 1.232), (0.228, 0.026, 1.290)]),
      ("b", [(0.325, -0.002, 1.146), (0.266, 0.006, 1.228), (0.224, 0.012, 1.290)])],
     branch_parent={"*": "row"}, circuit=VEN, listed="distal_first",
     landmarks="Paired venae comitantes either side of the brachial artery", depth_mm=(10, 20),
     bleed=_b((30, 100), None, None), self_stop="sometimes", compressible="yes", tag=K5,
     note="paired 3-5 mm (plan §3.4.1)")
_row("V23", "radial veins", "V", 2.0, (1.5, 2.5), (10, 30), {"L": "V22_a_L", "R": "V22_a_R"}, "LR",
     [(0.449, 0.001, 0.926), (0.387, 0.001, 1.046), (0.331, 0.010, 1.150)], circuit=VEN, listed="distal_first",
     landmarks="Venae comitantes of the radial artery", depth_mm=(3, 8), bleed=_b((10, 30), None, None),
     self_stop="yes", compressible="yes", tag=K5)
_row("V24", "ulnar veins", "V", 2.0, (1.5, 2.5), (10, 30), {"L": "V22_b_L", "R": "V22_b_R"}, "LR",
     [(0.452, 0.039, 0.927), (0.382, 0.034, 1.052), (0.325, -0.002, 1.146)], circuit=VEN, listed="distal_first",
     landmarks="Venae comitantes of the ulnar artery", depth_mm=(5, 10), bleed=_b((10, 30), None, None),
     self_stop="yes", compressible="yes", tag=K5)

# --- trunk wall, pelvis, gluteal ------------------------------------------------------------------
_row("A60", "superior epigastric", "M", 2.5, (2.0, 3.0), (10, 20), "A15", "LR",
     [(0.030, -0.060, 1.290), (0.042, -0.082, 1.255), (0.050, -0.090, 1.180), (0.052, -0.092, 1.112)],
     landmarks="Continuation of the internal thoracic behind the rectus abdominis", depth_mm=(18, 32),
     bleed=_b((20, 80), None, None, "rectus sheath haematoma"), self_stop="often", outlet_default="abdominal_wall",
     tag=K5)
_row("A61", "inferior epigastric", "M", 2.5, (2.0, 3.0), (10, 25), "A27", "LR",
     [(0.062, -0.066, 0.950), (0.055, -0.080, 0.990), (0.052, -0.090, 1.050), (0.052, -0.092, 1.112)],
     landmarks="From the external iliac just above the inguinal ligament, up behind the rectus",
     depth_mm=(18, 32), bleed=_b((30, 100), None, None, "rectus sheath / preperitoneal haematoma"),
     self_stop="often", outlet_default="abdominal_wall", tag=K5)
_row("A62", "superior gluteal", "M", 5.0, (4, 6), (40, 80), "A26", "LR",
     [(0.050, 0.020, 0.980), (0.070, 0.050, 0.990), (0.095, 0.078, 0.995), (0.118, 0.095, 0.985)],
     landmarks="Through the greater sciatic foramen above piriformis, under gluteus maximus/medius",
     depth_mm=(40, 80), bleed=_b((200, 600), None, None, "deep gluteal / pelvic"), compressible="no", tag=K5)
_row("A63", "inferior gluteal", "M", 4.0, (3, 5), (30, 60), "A26", "LR",
     [(0.049, 0.012, 0.985), (0.060, 0.045, 0.945), (0.072, 0.078, 0.912), (0.085, 0.100, 0.880)],
     landmarks="Below piriformis with the sciatic nerve, under gluteus maximus", depth_mm=(40, 80),
     bleed=_b((100, 400), None, None), compressible="no", tag=K5)


def _lumbar_points(level):
    """Lumbar artery path around the vertebral body of ``level`` (E fit B5 from the vertebra table)."""
    from .vertebrae import VERTEBRA
    v = VERTEBRA[level]
    c = np.array((0.0, v["y"], v["z"]), float)
    half_d = 0.5e-3 * v["body_d_mm"]
    half_w = 0.5e-3 * v["body_w_mm"]
    front = c[1] - half_d
    pts = [(0.006, front - 0.004, c[2] + 0.004), (0.60 * half_w + 0.004, front + 0.002, c[2]),
           (half_w + 0.004, c[1] + 0.004, c[2] - 0.002), (half_w + 0.010, c[1] + 0.030, c[2] - 0.004),
           (half_w + 0.018, c[1] + 0.055, c[2] - 0.004)]
    return [tuple(float(round(q, 4)) for q in p) for p in pts]


for _lv in ("L1", "L2", "L3", "L4"):
    _row("A64", "lumbar artery", "M", 2.5, (2.0, 3.0), (10, 25), "A21", "LR", [(_lv.lower(), _lumbar_points(_lv))],
         landmarks="Around the waist of the vertebral body under psoas to the back muscles",
         depth_mm=(60, 120), bleed=_b((30, 100), None, None, "retroperitoneal"), outlet_default="retroperitoneum",
         tag=K5)

# --- azygos system, portal tributaries, coronary sinus --------------------------------------------
_row("V36", "azygos vein", "V", 9.0, (8, 10), (150, 300), "V05", "R",
     [(-0.015, -0.017, 1.198), (-0.014, 0.008, 1.254), (-0.013, 0.028, 1.305), (-0.013, 0.037, 1.353),
      (-0.014, 0.035, 1.398), (-0.018, 0.030, 1.422), (-0.026, 0.012, 1.430), (-0.029, -0.008, 1.425),
      (-0.028, -0.024, 1.412)],
     circuit=VEN, listed="distal_first", landmarks="Right front of the thoracic vertebral bodies; arches over "
                                                   "the right main bronchus at T4 into the back of the SVC",
     bleed=_b((100, 400), None, None, "into the right pleura / mediastinum"), outlet_default="pleura_R",
     d_end_mm=6.0, tag=K5, note="8-10 mm (plan §3.4.1)")
_row("V37", "hemiazygos vein", "V", 5.0, (4, 6), (50, 100), "V36", "L",
     [(0.015, -0.016, 1.200), (0.015, 0.010, 1.254), (0.014, 0.028, 1.300), (0.004, 0.036, 1.322),
      (-0.012, 0.037, 1.330)],
     circuit=VEN, listed="distal_first", landmarks="Left of the lower thoracic bodies; crosses behind the aorta "
                                                   "at T8-T9 into the azygos",
     bleed=_b((30, 100), None, None, "left pleura"), outlet_default="pleura_L", tag=K5)
_row("V38", "splenic vein", "V", 8.0, (7, 9), (200, 300), "V13", "mid",
     [(0.090, 0.032, 1.222), (0.060, 0.018, 1.204), (0.028, 0.004, 1.190), (0.008, -0.020, 1.180),
      (-0.005, -0.045, 1.175)],
     circuit="portal", listed="distal_first", landmarks="Behind the pancreas from the splenic hilum to the "
                                                        "portal confluence behind the pancreatic neck",
     bleed=_b((200, 600), (300, 1200), None, "intraperitoneal"), outlet_default="peritoneum", tag=K5)
_row("V39", "superior mesenteric vein", "V", 10.0, (9, 11), (500, 700), "V13", "mid",
     [(-0.004, -0.075, 1.100), (-0.007, -0.060, 1.140), (-0.006, -0.050, 1.165), (-0.005, -0.045, 1.175)],
     circuit="portal", listed="distal_first", landmarks="In the mesentery right of the SMA",
     bleed=_b((300, 900), (300, 1200), None, "intraperitoneal"), outlet_default="peritoneum", tag=K5)
_row("V45", "coronary sinus", "V", 9.0, (7, 11), (200, 250), "RA", "mid",
     [(0.066, -0.012, 1.298), (0.048, 0.002, 1.310), (0.022, 0.006, 1.318), (0.000, 0.000, 1.322),
      (-0.016, -0.010, 1.324)],
     circuit=VEN, listed="distal_first", landmarks="Posterior atrioventricular groove into the right atrium",
     bleed=_b((100, 300), None, None, "pericardium -> tamponade"), outlet_default="pericardium", tag=K5)

# --- lower limb veins -----------------------------------------------------------------------------
_row("V40", "small saphenous vein", "V", 3.0, (2.5, 4.0), (10, 40), {"L": "V16_popliteal_L",
                                                                   "R": "V16_popliteal_R"}, "LR",
     [(0.128, 0.080, 0.065), (0.118, 0.098, 0.140), (0.103, 0.108, 0.260), (0.096, 0.098, 0.380),
      (0.093, 0.080, 0.465), (0.092, 0.064, 0.497)],
     circuit=VEN, listed="distal_first", landmarks="Behind the lateral malleolus, up the middle of the calf "
                                                   "just under the skin, through the popliteal fascia",
     depth_mm=(2, 6), bleed=_b((10, 50), None, None), self_stop="yes", compressible="yes", tag=K5)
_row("V41", "anterior tibial veins", "V", 4.0, (3, 5), (20, 40), {"L": "V16_popliteal_L",
                                                                "R": "V16_popliteal_R"}, "LR",
     [(0.101, 0.027, 0.087), (0.115, 0.037, 0.250), (0.111, 0.041, 0.420), (0.094, 0.060, 0.442)],
     circuit=VEN, listed="distal_first", landmarks="Venae comitantes of the anterior tibial artery on the "
                                                   "interosseous membrane", depth_mm=(10, 30),
     bleed=_b((20, 80), None, None), self_stop="often", compressible="yes", tag=K5)
_row("V42", "posterior tibial veins", "V", 5.0, (4, 6), (30, 50), {"L": "V16_popliteal_L",
                                                                 "R": "V16_popliteal_R"}, "LR",
     [(0.071, 0.078, 0.082), (0.084, 0.064, 0.250), (0.089, 0.059, 0.420), (0.092, 0.062, 0.442)],
     circuit=VEN, listed="distal_first", landmarks="Venae comitantes of the posterior tibial artery",
     depth_mm=(8, 40), bleed=_b((30, 100), None, None), self_stop="often", compressible="yes", tag=K5)
_row("V43", "peroneal veins", "V", 4.0, (3, 5), (20, 40), "V42", "LR",
     [(0.123, 0.059, 0.200), (0.098, 0.064, 0.420), (0.092, 0.062, 0.438)],
     circuit=VEN, listed="distal_first", landmarks="Venae comitantes of the peroneal artery along the fibula",
     bleed=_b((20, 80), None, None), self_stop="often", tag=K5)

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
