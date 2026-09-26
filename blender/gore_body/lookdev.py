"""Cycles look-dev materials (owner B7).  Plan §4.2, §5.2, §7, §8.2 B7.

``build_materials()`` builds the Cycles look-dev / bake-source materials for the whole subject,
reusing the head project's ``materials.py`` read-only (its shader groups and its GH_Skin, GH_Bone,
GH_Brain, GH_Eye, GH_Teeth, GH_Gums, GH_Tongue, GH_MouthInterior and GH_Muscle materials).

The exported glb keeps the named ``GBM_*`` placeholder materials (plan §5.6).  The look-dev
materials (``GBL_*``) are only swapped in temporarily for bakes and renders
(``lookdev_on(objs)`` / ``lookdev_off(state)``), so the export is never affected.

Materials (plan §5.6 slot -> look-dev material)
================================================
==========================  ===============================================================
GBM_skin_head               GBL_skin_head: the head project's GH_Skin (pores, stubble, face
                            regions, lips) moved into the body frame
GBM_mouth_lining            GBL_mouth_lining (GH_MouthInterior)
GBM_skin_torso/arm/leg      GBL_skin_body: the same skin model (same noise frame as the head,
                            so the colour is continuous across the neck seam) plus regional
                            variation read from ``lk_*`` attributes (``prepare_attributes``):
                            lighter pinker palms and soles, darker rougher knees / elbows /
                            knuckles, areola and nipple, sun-exposed dorsal forearms and hands,
                            paler skin under the shorts, superficial veins from B5's fitted
                            centrelines (cephalic, basilic, median cubital, saphenous) and a
                            dorsal venous network on the hands and feet, moles, freckles,
                            light male body hair
GBM_cloth                   GBL_cloth: charcoal cotton-poly twill
GBM_eye                     GBL_eye_L / GBL_eye_R: GH_Eye centred on each eyeball
GBM_teeth/gums/tongue       GBL_teeth / GBL_gums / GBL_tongue (GH_*)
GBM_hair_card               GBL_hair_card: B2's hair_cards.png with alpha
GBM_tearline/eye_occlusion  GBL_tearline / GBL_eye_occlusion
GBM_muscle_*                GBL_muscle (GH_Muscle)
GBM_bone / GBM_cartilage    GBL_bone (GH_Bone + marrow cores by ``gb_class``) / GBL_cartilage
GBM_brain                   GBL_brain (GH_Brain, sulcus depth = ``gb_depth``)
GBM_organ                   GBL_organ: per organ (``gb_organ``, ``gb_sub``) from the bible's
                            surface / interior colours (gb_data/organs.py) with organ-specific
                            texture; cavity and lumen surfaces (``lk_interior``) get the lining
GBM_cord / GBM_vessel_*     GBL_cord, GBL_vessel_art, GBL_vessel_ven
==========================  ===============================================================

Run ``python3 lookdev.py --render`` for look-dev renders of the saved build (``gore_body.blend``)
into ``renders/lookdev_*.png``; ``--baked`` renders the LOD0 meshes with the baked texture sets
instead (what the game shows).
"""
import math
import os
import sys

import numpy as np

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import landmarks as LM  # noqa: E402
from gb_data import organs as OR  # noqa: E402

HEAD_OFFSET = tuple(float(x) for x in gbc.HEAD_OFFSET)

# contract slot -> look-dev material (eyes are per object)
SLOT_LOOKDEV = {
    "GBM_skin_head": "GBL_skin_head", "GBM_mouth_lining": "GBL_mouth_lining",
    "GBM_skin_torso": "GBL_skin_body", "GBM_skin_arm_L": "GBL_skin_body", "GBM_skin_arm_R": "GBL_skin_body",
    "GBM_skin_leg_L": "GBL_skin_body", "GBM_skin_leg_R": "GBL_skin_body",
    "GBM_cloth": "GBL_cloth", "GBM_teeth": "GBL_teeth", "GBM_gums": "GBL_gums", "GBM_tongue": "GBL_tongue",
    "GBM_hair_card": "GBL_hair_card", "GBM_tearline": "GBL_tearline", "GBM_eye_occlusion": "GBL_eye_occlusion",
    "GBM_muscle_head": "GBL_muscle", "GBM_muscle_torso": "GBL_muscle", "GBM_muscle_arm_L": "GBL_muscle",
    "GBM_muscle_arm_R": "GBL_muscle", "GBM_muscle_leg_L": "GBL_muscle", "GBM_muscle_leg_R": "GBL_muscle",
    "GBM_bone": "GBL_bone", "GBM_cartilage": "GBL_cartilage", "GBM_brain": "GBL_brain", "GBM_organ": "GBL_organ",
    "GBM_cord": "GBL_cord", "GBM_vessel_art": "GBL_vessel_art", "GBM_vessel_ven": "GBL_vessel_ven",
}

# superficial veins that show through the skin (B5 vessel ids in vessels.json, prefix match)
SUPERFICIAL_VEINS = ("V20_cephalic", "V20_basilic", "V20_median_cubital", "V17_", "V40_")


# ---------------------------------------------------------------------------
# Head project access
# ---------------------------------------------------------------------------
def _gh():
    return gbc.import_head().materials


def _new(name):
    """(material, ShaderBuilder) with an empty node tree (head project's helper)."""
    return _gh()._new_material(name)


def _finish(mat, t, colour, rough=0.5):
    return _gh()._finish(mat, t, colour, rough)


# ---------------------------------------------------------------------------
# Copies of head-project materials moved into the body frame
# ---------------------------------------------------------------------------
def _shifted_copy(src, name, offset=(0.0, 0.0, 0.0), attr_map=None):
    """Copy a GH_* material, feeding its Object coordinates through ``p - offset`` and renaming
    attribute lookups (``attr_map``: old -> new).  The head material expects head space (origin at
    the ear-canal midpoint, or the eyeball centre for GH_Eye); body meshes are in the body frame."""
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    mat = src.copy()
    mat.name = name
    nt = mat.node_tree
    if any(abs(c) > 0 for c in offset):
        for node in list(nt.nodes):
            if node.bl_idname != 'ShaderNodeTexCoord':
                continue
            links = [lk for lk in nt.links if lk.from_node == node and lk.from_socket.name == 'Object']
            if not links:
                continue
            sub = nt.nodes.new('ShaderNodeVectorMath')
            sub.operation = 'SUBTRACT'
            sub.inputs[1].default_value = offset
            sub.location = (node.location.x + 120, node.location.y - 120)
            nt.links.new(node.outputs['Object'], sub.inputs[0])
            for lk in links:
                to = lk.to_socket
                nt.links.remove(lk)
                nt.links.new(sub.outputs[0], to)
    for node in nt.nodes:
        if node.bl_idname == 'ShaderNodeAttribute' and attr_map and node.attribute_name in attr_map:
            node.attribute_name = attr_map[node.attribute_name]
    mat["gb_lookdev"] = True
    return mat


def eye_centre(obj):
    """Eyeball centre of a GB_Eye_* mesh in the body frame (bbox centre in x/z, back pole - radius in y)."""
    v = gbc.get_verts(obj.data)
    lo, hi = v.min(0), v.max(0)
    return (float((lo[0] + hi[0]) * 0.5), float(hi[1] - 0.012), float((lo[2] + hi[2]) * 0.5))


# ---------------------------------------------------------------------------
# Body skin
# ---------------------------------------------------------------------------
SKIN_SSS = {'IOR': 1.4, 'Specular IOR Level': 0.5, 'Subsurface Radius': (1.0, 0.40, 0.22),
            'Subsurface Scale': 0.0035, 'Subsurface IOR': 1.4, 'Subsurface Anisotropy': 0.8,
            'Sheen Roughness': 0.35}


def _body_skin_material():
    """GBL_skin_body: the head project's skin model with body-specific regional variation.

    The shared noises run in head space (``p - HEAD_OFFSET``) with the head's scales, so the
    colour field is continuous across the neck seam.  Regional inputs are ``lk_*`` point
    attributes (0 when missing = plain skin)."""
    mat, t = _new("GBL_skin_body")
    p = t.coord()
    ph = p - HEAD_OFFSET
    tone, pallor = t.control("skin_tone"), t.control("pallor")
    palm, joint, areola = t.attr("lk_palm"), t.attr("lk_joint"), t.attr("lk_areola")
    nipple, sun, covered = t.attr("lk_nipple"), t.attr("lk_sun"), t.attr("lk_covered")
    vein, mole, hair = t.attr("lk_vein"), t.attr("lk_mole"), t.attr("lk_hair")
    dorsum, oily = t.attr("lk_dorsum"), t.attr("lk_oily")

    base = tone.ramp([(0.0, (0.61, 0.43, 0.35)), (0.25, (0.48, 0.30, 0.225)), (0.5, (0.30, 0.16, 0.10)),
                      (0.75, (0.13, 0.062, 0.038)), (1.0, (0.05, 0.026, 0.018))])
    m_low = t.noise(ph, 22.0, 3.0, 0.55)
    m_red = t.noise(ph + (7.3, 1.1, 3.7), 30.0, 3.0, 0.55)
    m_fine = t.noise(ph, 190.0, 3.0, 0.6)
    redness = (m_red.smooth(0.5, 0.8) * 0.26 + (m_fine - 0.5) * 0.2 + joint * 0.30 + palm * 0.22
               + nipple * 0.3).clamp()
    redness = redness * (1.0 - pallor)
    col = t.mix(redness, base, base * (1.04, 0.64, 0.66))
    col = col * (0.84 + 0.30 * m_low)
    col = t.mix((m_fine - 0.5).abs() * 0.5, col, col * (1.0, 0.92, 0.80))           # sallow / olive
    # sun-exposed skin (dorsal forearms, hands, shoulders): a little darker and warmer
    col = t.mix(sun * 0.55, col, col * (0.90, 0.78, 0.68))
    # skin that is always covered (under the shorts): paler, a touch pinker
    col = t.mix(covered * 0.5, col, col * (1.06, 1.03, 1.02))
    # palms and soles: little melanin, thick translucent stratum corneum -> lighter, pink-yellow
    palm_col = t.mix(0.5, base * (1.18, 0.96, 0.84), (0.58, 0.36, 0.27)) * (0.9 + 0.2 * m_low)
    col = t.mix(palm * 0.85, col, palm_col)
    # extensor surfaces of joints: darker, slightly purplish-brown, lined
    jl = t.ridge(t.noise(t.vec(p.x * 0.15, p.y * 0.15, p.z), 700.0, 2.0, 0.5), 0.06) * joint
    col = t.mix(joint * 0.45, col, col * (0.80, 0.66, 0.62))
    col = col * (1.0 - jl * 0.18)
    # freckles and melanin spots (more on sun-exposed skin)
    fd, fcol, _ = t.voronoi(t.warp(ph, 300.0, 0.0006), 260.0)
    frk = (1.0 - fd.smooth(0.0, 0.3)) * t.sep(fcol)[0].smooth(0.82 - sun * 0.1, 0.95) * (0.25 + sun * 0.35)
    col = t.mix(frk * (1.0 - palm), col, col * (0.72, 0.58, 0.48))
    # areola and nipple (with Montgomery tubercles)
    ar_col = t.mix(m_fine, (0.20, 0.085, 0.065), (0.27, 0.12, 0.09))
    col = t.mix(areola * 0.9, col, ar_col)
    md, mcol, _ = t.voronoi(p, 700.0)
    mont = (1.0 - md.smooth(0.0, 0.25)) * t.sep(mcol)[0].smooth(0.8, 0.85) * areola.smooth(0.3, 0.9) \
        * (1.0 - nipple)
    col = t.mix(nipple * 0.9, col, (0.17, 0.065, 0.05))
    # superficial veins (B5 centrelines) and the dorsal venous network of hands and feet
    net = t.ridge(t.noise(t.warp(p, 60.0, 0.012), 45.0, 3.0), 0.03) * t.noise(p, 25.0).smooth(0.4, 0.6) * dorsum
    vv = (vein + net * 0.7).clamp()
    col = t.mix(vv * (0.30 + 0.45 * pallor), col, col * (0.60, 0.72, 0.92))
    # moles
    col = t.mix(mole, col, t.mix(m_fine, (0.10, 0.052, 0.035), (0.16, 0.085, 0.06)))
    # light male body hair: fine dark strokes along the local down/distal direction (object z)
    hd, hcol, _ = t.voronoi(p * (1.0, 1.0, 0.28), 900.0)
    strand = (1.0 - hd.smooth(0.0, 0.16)) * t.sep(hcol)[1].smooth(0.92 - hair * 0.35, 0.95 - hair * 0.35)
    col = t.mix(strand * hair * 0.45, col, (0.030, 0.020, 0.014))
    # micro relief (body pores are smaller and fainter than on the face)
    pd, _, _ = t.voronoi(p, 2600.0)
    pore = 1.0 - pd.smooth(0.0, 0.26)
    gd, _, _ = t.voronoi(p * (1.0, 1.0, 1.5), 1100.0, 'DISTANCE_TO_EDGE', rand=0.9)
    groove = (1.0 - gd.smooth(0.0, 0.12)) * m_fine.smooth(0.3, 0.7) * 0.45
    fine = t.noise(p, 6000.0, 2.0)
    col = col * (1.0 - pore * 0.05 - groove * 0.03)
    lum = t.luminance(col)
    skin_col = t.mix(pallor * 0.72, col, t.vec(lum, lum, lum) * (0.97, 1.0, 1.06) * 1.08)
    mid = t.noise(p, 160.0, 2.0)
    h = -pore * 0.6 - groove * 0.5 + fine * 0.2 + mid * 0.4 - jl * 1.2 + mont * 1.5 + mole * 0.6 \
        + vv * 0.8 * (1.0 - pallor * 0.5) + strand * hair * 0.3
    rough = 0.47 + (m_fine - 0.5) * 0.12 + (fine - 0.5) * 0.10 - oily * 0.08 + joint * 0.08 + palm * 0.05 \
        + pore * 0.06
    n_skin = t.bump(h, 0.0001)
    bsdf = t.principled(dict(SKIN_SSS, **{
        'Base Color': skin_col, 'Roughness': rough, 'Subsurface Weight': 1.0 - palm * 0.15,
        'Coat Weight': 0.06 + oily * 0.08, 'Coat Roughness': 0.35, 'Coat IOR': 1.45, 'Coat Normal': n_skin,
        'Sheen Weight': 0.05 + hair * 0.05, 'Normal': n_skin}), sss_method='RANDOM_WALK_SKIN')
    t.output(bsdf)
    return _finish(mat, t, (0.47, 0.28, 0.19), 0.47)


# ---------------------------------------------------------------------------
# Other tissues
# ---------------------------------------------------------------------------
def _cartilage_material():
    """GBL_cartilage: hyaline cartilage (discs' annulus, costal cartilage): bluish pearly white,
    smooth, glossy, translucent."""
    mat, t = _new("GBL_cartilage")
    p = t.coord()
    n1 = t.noise(p, 120.0, 3.0, 0.5)
    col = t.mix(n1, (0.52, 0.52, 0.50), (0.64, 0.63, 0.58))
    col = t.mix(t.noise(p, 30.0, 2.0).smooth(0.55, 0.75) * 0.4, col, (0.60, 0.50, 0.42))
    lam = t.noise(p * (1.0, 1.0, 0.2), 900.0, 2.0)
    bsdf = t.principled({'Base Color': col, 'Roughness': 0.28 + n1 * 0.08, 'IOR': 1.45,
                         'Subsurface Weight': 0.6, 'Subsurface Radius': (1.0, 0.8, 0.7),
                         'Subsurface Scale': 0.002, 'Coat Weight': 0.3, 'Coat Roughness': 0.1,
                         'Normal': t.bump(lam * 0.3 + n1 * 0.4, 0.0001)})
    t.output(bsdf)
    return _finish(mat, t, (0.66, 0.65, 0.6), 0.3)


def _bone_material(gh_bone):
    """GBL_bone: GH_Bone, plus the long-bone marrow cores (gb_class 6) as yellow marrow (#E4C36A)."""
    mat = _shifted_copy(gh_bone, "GBL_bone")
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    src = bsdf.inputs['Base Color'].links[0].from_socket if bsdf.inputs['Base Color'].is_linked else None
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_type = 'GEOMETRY'
    attr.attribute_name = "gb_class"
    rng = nt.nodes.new('ShaderNodeMapRange')
    rng.interpolation_type = 'LINEAR'
    rng.inputs['From Min'].default_value = 5.5
    rng.inputs['From Max'].default_value = 5.6
    nt.links.new(attr.outputs['Fac'], rng.inputs['Value'])
    mixn = nt.nodes.new('ShaderNodeMix')
    mixn.data_type = 'RGBA'
    nt.links.new(rng.outputs['Result'], mixn.inputs['Factor'])
    if src is not None:
        nt.links.new(src, mixn.inputs['A'])
    mixn.inputs['B'].default_value = (*_lin("#E4C36A"), 1.0)
    nt.links.new(mixn.outputs['Result'], bsdf.inputs['Base Color'])
    return mat


def _organ_material():
    """GBL_organ: every organ in one material, keyed by ``gb_organ`` / ``gb_sub`` / ``lk_interior``.

    Base colours are the bible's surface and interior colours (gb_data/organs.py); each organ adds
    its own texture: myocardium with epicardial fat in the grooves, lungs with lobular outlines and
    anthracotic specks under a glossy pleura, liver lobular mottling, spleen and kidney capsules,
    stomach rugae, pancreatic lobules, tracheal cartilage rings, diaphragm tendon, omental fat."""
    mat, t = _new("GBL_organ")
    p = t.coord()
    oid, sub, inner = t.attr("gb_organ"), t.attr("gb_sub"), t.attr("lk_interior")

    def is_(val, k):
        return 1.0 - (val - float(k)).abs().smooth(0.35, 0.6)
    ids = {o["id"]: int(o["organ_id"]) for o in OR.ORGANS}
    n1 = t.noise(p, 60.0, 3.0, 0.55)
    n2 = t.noise(p, 400.0, 2.0, 0.55)
    col = (0.2, 0.05, 0.05)
    rough = 0.3
    height = n2 * 0.3
    for name, k in ids.items():
        row = _organ_row(name)
        if row is None:
            continue
        sc, ic = _lin(row["surface_colour"]), _lin(row["interior_colour"])
        m = is_(oid, k)
        c = t.mix(inner, sc, ic)
        col = t.mix(m, col, c * (0.85 + 0.3 * n1))
    # --- organ-specific texture -------------------------------------------------------------------
    heart = is_(oid, ids.get("heart", 1))
    fat_d, fat_c, _ = t.voronoi(p, 500.0)
    fatc = t.mix(fat_d.smooth(0.0, 0.6), (0.75, 0.55, 0.15), (0.62, 0.42, 0.10))
    col = t.mix(heart * is_(sub, 5) * 0.9, col, fatc)                              # epicardial fat
    epi_fat = t.noise(p, 25.0, 3.0).smooth(0.62, 0.72) * heart * (1.0 - inner)
    col = t.mix(epi_fat * 0.8, col, fatc)
    lung = is_(oid, ids.get("lung_L", 2)).max(is_(oid, ids.get("lung_R", 3)))
    ld, _, _ = t.voronoi(t.warp(p, 30.0, 0.004), 60.0, 'DISTANCE_TO_EDGE')
    lob = 1.0 - ld.smooth(0.0, 0.04)
    ad, acol, _ = t.voronoi(p, 350.0)
    anth = (1.0 - ad.smooth(0.0, 0.25)) * t.sep(acol)[0].smooth(0.7, 0.8) * t.noise(p, 20.0).smooth(0.4, 0.7)
    col = t.mix(lung * (1.0 - inner) * lob * 0.5, col, (0.22, 0.10, 0.12))
    col = t.mix(lung * (1.0 - inner) * anth * 0.8, col, (0.03, 0.025, 0.03))
    col = t.mix(lung * (1.0 - inner) * t.noise(p, 40.0, 3.0).smooth(0.45, 0.7) * 0.4, col, (0.45, 0.12, 0.14))
    liver = is_(oid, ids.get("liver", 4))
    hd, _, _ = t.voronoi(p, 700.0, 'DISTANCE_TO_EDGE')
    col = t.mix(liver * (1.0 - hd.smooth(0.0, 0.08)) * 0.35, col, (0.12, 0.03, 0.02))
    stom = is_(oid, ids.get("stomach", 11))
    rug = t.ridge(t.noise(p * (1.0, 1.0, 0.25), 90.0, 3.0), 0.08) * stom * inner
    col = t.mix(rug * 0.5, col, (0.30, 0.05, 0.05))
    panc = is_(oid, ids.get("pancreas", 12))
    pd, pc, _ = t.voronoi(p, 350.0)
    col = t.mix(panc * (1.0 - pd.smooth(0.0, 0.5)) * 0.3, col, (0.70, 0.52, 0.34))
    airway = is_(oid, ids.get("trachea", 15)).max(is_(oid, ids.get("bronchus_L", 16))).max(
        is_(oid, ids.get("bronchus_R", 17))).max(is_(oid, ids.get("larynx", 19)))
    col = t.mix(airway * is_(sub, 1) * (1.0 - inner) * 0.8, col, (0.66, 0.64, 0.58))   # cartilage rings
    dia = is_(oid, ids.get("diaphragm", 20))
    col = t.mix(dia * is_(sub, 2) * 0.9, col, (0.72, 0.68, 0.60))                     # central tendon
    oment = is_(oid, ids.get("omentum", 21))
    od, _, _ = t.voronoi(p, 260.0, 'DISTANCE_TO_EDGE')
    col = t.mix(oment * (1.0 - od.smooth(0.0, 0.06)) * 0.6, col, (0.55, 0.18, 0.08))
    kid = is_(oid, ids.get("kidney_L", 7)).max(is_(oid, ids.get("kidney_R", 8)))
    col = t.mix(kid * (is_(sub, 3) + is_(sub, 2)).clamp() * 0.85, col, (0.78, 0.60, 0.20))   # perirenal fat
    # surface vessels on serosa and capsules
    ves = t.ridge(t.noise(t.warp(p, 40.0, 0.006), 55.0, 3.0), 0.02) * t.noise(p, 18.0).smooth(0.45, 0.62) \
        * (1.0 - inner) * (1.0 - lung)
    col = t.mix(ves * 0.55, col, (0.25, 0.02, 0.03))
    # cavity / lumen linings are darker and full of blood
    col = t.mix(inner * 0.35, col, col * (0.6, 0.35, 0.35))
    rough = 0.22 + n2 * 0.1 + anth * lung * 0.1 + oment * 0.05 + inner * 0.05 - lung * 0.04
    height = n2 * 0.3 + lob * lung * -0.6 + rug * 2.0 + (1.0 - pd.smooth(0.0, 0.5)) * panc * 0.8 \
        + oment * (1.0 - od.smooth(0.0, 0.06)) * -0.8 - ves * 0.3
    nrm = t.bump(height, 0.00012)
    bsdf = t.principled({'Base Color': col, 'Roughness': rough, 'IOR': 1.4,
                         'Subsurface Weight': 0.55 - inner * 0.3, 'Subsurface Radius': (1.0, 0.35, 0.25),
                         'Subsurface Scale': 0.003, 'Coat Weight': 0.45, 'Coat Roughness': 0.06,
                         'Coat Normal': nrm, 'Normal': nrm})
    t.output(bsdf)
    return _finish(mat, t, (0.45, 0.15, 0.15), 0.25)


def _organ_row(name):
    rows = OR.ORGANS
    if isinstance(rows, dict):
        return rows.get(name)
    for r in rows:
        if r.get("id") == name:
            return r
    return None


def _cloth_material():
    """GBL_cloth: charcoal cotton-poly twill shorts (weave at ~34 threads/cm, heathered)."""
    mat, t = _new("GBL_cloth")
    p = t.coord()
    heather = t.noise(p, 1800.0, 2.0)
    wale = t.noise(t.vec(p.x + p.z, p.y + p.z, 0.0), 1.0).smooth(0.2, 0.8) * 0.0
    tw = t.math('SINE', (p.x + p.y * 0.6 + p.z) * 2.0 * math.pi * 3400.0 / 2.0)
    col = t.mix(heather.smooth(0.45, 0.8), (0.030, 0.030, 0.032), (0.052, 0.052, 0.055))
    col = col * (0.85 + 0.15 * t.noise(p, 30.0, 3.0))
    col = col * (1.0 - (tw * 0.5 + 0.5) * 0.12)
    h = tw * 0.1 + t.noise(p, 250.0, 3.0) * 0.6 + wale
    bsdf = t.principled({'Base Color': col, 'Roughness': 0.9, 'Sheen Weight': 0.35, 'Sheen Roughness': 0.5,
                         'Sheen Tint': (0.6, 0.6, 0.62), 'Normal': t.bump(h, 0.0002)})
    t.output(bsdf)
    return _finish(mat, t, (0.04, 0.04, 0.042), 0.9)


def _simple(name, colour, rough, sss=0.0, coat=0.0, alpha=1.0, radius=(1.0, 0.3, 0.2), noise=0.0):
    """Plain principled material (vessels, cord, eye FX)."""
    mat, t = _new(name)
    p = t.coord()
    col = colour
    if noise:
        col = t.mix(t.noise(p, 300.0, 3.0), tuple(c * (1.0 - noise) for c in colour), colour)
    bsdf = t.principled({'Base Color': col, 'Roughness': rough, 'IOR': 1.4, 'Subsurface Weight': sss,
                         'Subsurface Radius': radius, 'Subsurface Scale': 0.002, 'Coat Weight': coat,
                         'Coat Roughness': 0.05, 'Alpha': alpha})
    t.output(bsdf)
    mat.surface_render_method = 'BLENDED' if alpha < 1.0 else 'DITHERED'
    return _finish(mat, t, tuple(colour), rough)


def _hair_card_material():
    """GBL_hair_card: B2's hair_cards.png (RGBA) with alpha, double sided."""
    mat, t = _new("GBL_hair_card")
    path = os.path.join(gbc.SUBJECT_OUT, "textures", "hair_cards.png")
    img = None
    if os.path.exists(path):
        img = bpy.data.images.load(path, check_existing=True)
    if img is not None:
        uvn = t.node('ShaderNodeUVMap', uv_map="atlas")
        tex = t.node('ShaderNodeTexImage', {'Vector': t.o(uvn)}, image=img)
        col, alpha = t.o(tex, 'Color'), t.o(tex, 'Alpha')
    else:
        col, alpha = (0.03, 0.02, 0.015), 1.0
    bsdf = t.principled({'Base Color': col, 'Roughness': 0.45, 'Alpha': alpha, 'Coat Weight': 0.1})
    t.output(bsdf)
    mat.use_backface_culling = False
    return _finish(mat, t, (0.03, 0.02, 0.015), 0.45)


def _lin(hexstr):
    return gbc.hex_to_linear(hexstr)[:3]


# ---------------------------------------------------------------------------
# Public: build, attributes, swap
# ---------------------------------------------------------------------------
def build_materials(eyes=None):
    """Build every GBL_* look-dev material (idempotent).  Returns {name: material}.

    ``eyes``: optional {"GB_Eye_L": obj, "GB_Eye_R": obj} to centre the eye materials; by default the
    scene objects of those names are used."""
    gh = _gh()
    ghm = gh.build_materials()
    out = {}
    out["GBL_skin_head"] = _shifted_copy(ghm["GH_Skin"], "GBL_skin_head", HEAD_OFFSET, {"gh_lip": "gb_lip"})
    out["GBL_mouth_lining"] = _shifted_copy(ghm["GH_MouthInterior"], "GBL_mouth_lining", HEAD_OFFSET)
    out["GBL_teeth"] = _shifted_copy(ghm["GH_Teeth"], "GBL_teeth", HEAD_OFFSET, {"tooth_id": "gb_piece"})
    out["GBL_gums"] = _shifted_copy(ghm["GH_Gums"], "GBL_gums", HEAD_OFFSET)
    out["GBL_tongue"] = _shifted_copy(ghm["GH_Tongue"], "GBL_tongue", HEAD_OFFSET)
    out["GBL_brain"] = _shifted_copy(ghm["GH_Brain"], "GBL_brain", HEAD_OFFSET, {"gh_sulcus": "gb_depth"})
    out["GBL_muscle"] = _shifted_copy(ghm["GH_Muscle"], "GBL_muscle")
    out["GBL_bone"] = _bone_material(ghm["GH_Bone"])
    for side in ("L", "R"):
        o = (eyes or {}).get(f"GB_Eye_{side}") or bpy.data.objects.get(f"GB_Eye_{side}")
        c = eye_centre(o) if o is not None else (0.032 if side == "L" else -0.032, -0.050, 1.669)
        out[f"GBL_eye_{side}"] = _shifted_copy(ghm["GH_Eye"], f"GBL_eye_{side}", c)
    out["GBL_skin_body"] = _body_skin_material()
    out["GBL_cartilage"] = _cartilage_material()
    out["GBL_organ"] = _organ_material()
    out["GBL_cloth"] = _cloth_material()
    out["GBL_hair_card"] = _hair_card_material()
    out["GBL_cord"] = _simple("GBL_cord", (0.62, 0.55, 0.48), 0.3, sss=0.5, coat=0.4, noise=0.15)
    out["GBL_vessel_art"] = _simple("GBL_vessel_art", _lin("#C0141E"), 0.25, sss=0.3, coat=0.5, noise=0.2)
    out["GBL_vessel_ven"] = _simple("GBL_vessel_ven", _lin("#8E1420"), 0.25, sss=0.3, coat=0.5, noise=0.2)
    out["GBL_tearline"] = _simple("GBL_tearline", (0.8, 0.8, 0.8), 0.02, coat=1.0, alpha=0.35)
    out["GBL_eye_occlusion"] = _simple("GBL_eye_occlusion", (0.0, 0.0, 0.0), 1.0, alpha=0.25)
    return out


def lookdev_for(obj, slot_name):
    """Look-dev material name for a contract slot on ``obj``."""
    if slot_name == "GBM_eye":
        return "GBL_eye_R" if obj.name.endswith("_R") else "GBL_eye_L"
    return SLOT_LOOKDEV.get(slot_name)


def lookdev_on(objs):
    """Swap every GBM_* slot of ``objs`` to its look-dev material; returns the state for lookdev_off."""
    state = []
    for o in objs:
        if o is None or o.type != 'MESH':
            continue
        me = o.data
        for i, m in enumerate(me.materials):
            if m is None:
                continue
            name = lookdev_for(o, m.name)
            if name and name in bpy.data.materials:
                state.append((me, i, m))
                me.materials[i] = bpy.data.materials[name]
    return state


def lookdev_off(state):
    """Restore the placeholder materials swapped by lookdev_on."""
    for me, i, m in reversed(state):
        me.materials[i] = m


# ---------------------------------------------------------------------------
# lk_* attributes (numpy, per vertex of the bake-source meshes)
# ---------------------------------------------------------------------------
def _smooth_attr(me, values, iters=4):
    """Average a per-vertex value over edge neighbours ``iters`` times (softens hard region edges)."""
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    v = np.asarray(values, float)
    deg = np.bincount(ev.ravel(), minlength=len(v)).astype(float) + 1.0
    for _ in range(iters):
        acc = v.copy()
        np.add.at(acc, ev[:, 0], v[ev[:, 1]])
        np.add.at(acc, ev[:, 1], v[ev[:, 0]])
        v = acc / deg
    return v


def _normals(me):
    n = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("normal", n)
    return n.reshape(-1, 3).astype(float)


def _lm(name, side="L"):
    """Landmark position (body frame); right side mirrored."""
    rows = dict(LM.LANDMARKS)
    rows.update(getattr(LM, "LANDMARKS_EXTRA", {}) or {})
    key = name.replace("{s}", "L")
    p = np.array(rows[key]["p"], float)
    if side == "R":
        p[0] = -p[0]
    return p


def _gauss(v, c, r):
    d = v - np.asarray(c)
    return np.exp(-(d * d).sum(1) / (r * r))


def _seg_dist(pts, a, b):
    """Distance from points (N,3) to segment a-b and the segment parameter."""
    ab = b - a
    L2 = max(float(ab @ ab), 1e-12)
    t = np.clip(((pts - a) @ ab) / L2, 0.0, 1.0)
    return np.linalg.norm(pts - (a + t[:, None] * ab), axis=1), t


def vein_field(v, vessels_json=None):
    """Visibility (0-1) of the superficial veins at points ``v`` from B5's fitted centrelines."""
    import json
    path = vessels_json or os.path.join(gbc.SUBJECT_OUT, "vessels.json")
    out = np.zeros(len(v))
    if not os.path.exists(path):
        return out
    segs = json.load(open(path))["data"]["segments"]
    for s in segs:
        if not s["id"].startswith(SUPERFICIAL_VEINS) or s.get("blood") == "art":
            continue
        P4 = np.asarray(s["points"], float)
        if len(P4) < 2:
            continue
        P = P4[:, :3]
        rad = P4[:, 3] if P4.shape[1] > 3 else np.full(len(P), float(s.get("d_mm") or 3.0) * 0.5e-3)
        lo, hi = P.min(0) - 0.025, P.max(0) + 0.025
        m = np.all((v >= lo) & (v <= hi), axis=1)
        if not m.any():
            continue
        q = v[m]
        # depth of each centreline point under the skin = distance to the nearest skin vertex - radius
        dep = np.array([np.sqrt(((q - pt) ** 2).sum(1)).min() for pt in P]) - rad
        vis = np.zeros(len(q))
        for i in range(len(P) - 1):
            d, tt = _seg_dist(q, P[i], P[i + 1])
            r = rad[i] + (rad[i + 1] - rad[i]) * tt
            depth = np.maximum(dep[i] + (dep[i + 1] - dep[i]) * tt, 0.0)
            # a vein seen through skin looks about as wide as itself plus half its depth; fades with depth
            w = r + depth * 0.5
            val = np.exp(-(d / np.maximum(w, 1e-4)) ** 2) * np.exp(-np.maximum(depth * 1000.0 - 1.5, 0.0) / 2.5)
            vis = np.maximum(vis, val)
        out[m] = np.maximum(out[m], vis)
    return np.clip(out, 0.0, 1.0)


def body_region_fields(obj):
    """Per-vertex ``lk_*`` fields (dict name -> (N,) float) for a body-skin mesh (GB_Body / _HR)."""
    me = obj.data
    v = gbc.get_verts(me)
    nrm = _normals(me)
    region = gbc.read_point_attr(obj, "gb_region", 'INT')
    seg = gbc.read_point_attr(obj, "gb_seg", 'INT')
    n = len(v)
    region = np.zeros(n, int) if region is None else region
    seg = np.zeros(n, int) if seg is None else seg
    f = {}
    f["lk_palm"] = _smooth_attr(me, (region == 7).astype(float), 3)
    joint = np.zeros(n)
    for s in ("L", "R"):
        sg = 1.0 if s == "L" else -1.0
        # knee: skin over the patella and just below (kneeling skin)
        pk = _lm("patella_skin_L", s)
        joint = np.maximum(joint, _gauss(v, pk + (0, -0.005, -0.012), 0.035) * np.clip(-nrm[:, 1] * 1.5, 0, 1))
        # elbow: olecranon skin behind the elbow centre (A-pose: posterior = +y)
        pe = _lm("elbow_centre_L_apose", s) + (0.0, 0.035, -0.01)
        joint = np.maximum(joint, _gauss(v, pe, 0.03) * np.clip(nrm[:, 1] * 1.5, 0, 1))
        # knuckles: dorsal MCP line (hand segment, facing away from the palm)
        hand = seg == (6 if s == "L" else 7)
        if hand.any():
            palm_n = nrm[hand & (region == 7)].mean(0) if (hand & (region == 7)).any() else np.array([-sg, 0, 0])
            palm_n /= max(np.linalg.norm(palm_n), 1e-9)
            dors = np.clip(-(nrm @ palm_n) * 1.5, 0, 1) * hand
            mcp = _lm("mcp3_L_apose", s)
            joint = np.maximum(joint, _gauss(v * (1, 1, 1), mcp, 0.03) * dors)
            f.setdefault("lk_dorsum", np.zeros(n))
            f["lk_dorsum"] = np.maximum(f["lk_dorsum"], dors)
        # ankles: malleoli
        for lm in ("lateral_malleolus_L", "medial_malleolus_L"):
            joint = np.maximum(joint, _gauss(v, _lm(lm, s), 0.018) * 0.6)
        foot = seg == (8 if s == "L" else 9)
        f.setdefault("lk_dorsum", np.zeros(n))
        f["lk_dorsum"] = np.maximum(f["lk_dorsum"], foot * np.clip(nrm[:, 2] * 1.5, 0, 1) * (region != 7))
    f["lk_joint"] = np.clip(joint, 0, 1)
    # areola (r ~14 mm) and nipple (r ~5 mm) around the nearest skin point to each nipple landmark
    ar = np.zeros(n)
    ni = np.zeros(n)
    for s in ("L", "R"):
        c = _lm("nipple_L", s)
        near = np.linalg.norm(v - c, axis=1) < 0.03
        if near.any():
            idx = np.nonzero(near)[0]
            tip = v[idx[np.argmin(v[idx, 1])]]          # most anterior point = nipple tip
            d = np.linalg.norm(v - tip, axis=1)
            ar = np.maximum(ar, 1.0 - np.clip((d - 0.0125) / 0.003, 0, 1))
            ni = np.maximum(ni, 1.0 - np.clip((d - 0.0045) / 0.0015, 0, 1))
    f["lk_areola"] = ar
    f["lk_nipple"] = ni
    # sun exposure: dorsal / lateral forearms and hands, shoulders and upper back, lower legs a little
    arm = np.isin(seg, (2, 3, 6, 7))
    sgn = np.sign(v[:, 0])
    lateral = np.clip(nrm[:, 0] * sgn * 0.7 + nrm[:, 1] * -0.2 + 0.4, 0, 1)
    forearm = arm & (v[:, 2] < 1.20)
    sun = forearm * lateral * 0.9 + np.isin(seg, (6, 7)) * 0.6
    shoulders = (seg == 1) * np.clip((v[:, 2] - 1.35) / 0.1, 0, 1) * np.clip(nrm[:, 2] + 0.3, 0, 1)
    sun = np.maximum(sun, shoulders * 0.6)
    sun = np.maximum(sun, np.isin(seg, (4, 5)) * np.clip((0.45 - v[:, 2]) / 0.2, 0, 1) * 0.35)
    f["lk_sun"] = _smooth_attr(me, np.clip(sun, 0, 1), 6)
    # covered by the shorts (waist to mid-thigh), softened
    f["lk_covered"] = _smooth_attr(me, ((v[:, 2] > 0.60) & (v[:, 2] < 1.02) & (np.isin(seg, (1, 4, 5)))).astype(float), 8)
    # moles: 36 deterministic spots on trunk, back, arms and thighs, 1.2-3 mm radius
    rng = gbc.rng("lookdev")
    cand = np.nonzero(np.isin(seg, (1, 2, 3, 4, 5)) & (region != 7))[0]
    mole = np.zeros(n)
    if len(cand):
        for i in rng.choice(cand, size=min(36, len(cand)), replace=False):
            r = rng.uniform(0.0012, 0.003)
            d = np.linalg.norm(v - v[i], axis=1)
            mole = np.maximum(mole, 1.0 - np.clip((d - r) / 0.0006, 0, 1))
    f["lk_mole"] = mole
    # body hair density (adult male, light): chest, abdomen midline, forearms, legs, axillae
    ax_ = np.abs(v[:, 0])
    front = nrm[:, 1] < 0
    hair = np.zeros(n)
    chest = (seg == 1) * front * np.exp(-((v[:, 2] - 1.30) / 0.07) ** 2) * np.exp(-(ax_ / 0.09) ** 2)
    trail = (seg == 1) * front * np.clip((1.10 - v[:, 2]) / 0.1, 0, 1) * np.exp(-(ax_ / 0.03) ** 2)
    hair = np.maximum(hair, chest * 0.7 + trail * 0.8)
    hair = np.maximum(hair, forearm * lateral * 0.6)
    legs = np.isin(seg, (4, 5)) * np.clip((0.80 - v[:, 2]) / 0.2, 0, 1) * 0.75
    hair = np.maximum(hair, legs)
    for s in ("L", "R"):
        axl = _lm("gh_joint_L", s) + (-0.02 * (1 if s == "L" else -1), 0.0, -0.09)
        hair = np.maximum(hair, _gauss(v, axl, 0.035) * 0.9)
    hair = hair * (region != 7)
    f["lk_hair"] = _smooth_attr(me, np.clip(hair, 0, 1), 4)
    f["lk_vein"] = vein_field(v)
    # oily (sebaceous) centre of chest and upper back
    f["lk_oily"] = (seg == 1) * np.exp(-(ax_ / 0.07) ** 2) * np.clip((v[:, 2] - 1.15) / 0.15, 0, 1)
    f.setdefault("lk_dorsum", np.zeros(n))
    f["lk_dorsum"] = _smooth_attr(me, f["lk_dorsum"], 3)
    return f


def organ_interior(obj):
    """1 on vertices of closed inner (cavity / lumen) surfaces, found as connected components with
    a negative signed volume (their normals face into the cavity)."""
    me = obj.data
    v = gbc.get_verts(me)
    me.calc_loop_triangles()
    tri = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tri)
    tri = tri.reshape(-1, 3)
    comp = _components(len(v), tri)
    vol = np.einsum("ij,ij->i", v[tri[:, 0]], np.cross(v[tri[:, 1]], v[tri[:, 2]])) / 6.0
    cv = np.bincount(comp[tri[:, 0]], weights=vol)
    return (cv[comp] < 0).astype(float)


def _components(nv, tri):
    """Connected components of a triangle mesh (vertex labels)."""
    par = np.arange(nv)

    def find(x):
        while True:
            px = par[x]
            ppx = par[px]
            if np.array_equal(px, ppx):
                return px
            par[x] = ppx
            x = ppx
    edges = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    for _ in range(64):
        a, b = find(edges[:, 0]), find(edges[:, 1])
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        if np.array_equal(lo, hi):
            break
        np.minimum.at(par, hi, lo)
    return find(np.arange(nv))


def prepare_attributes(objs=None):
    """Write the lk_* point attributes the look-dev materials read onto the bake sources."""
    names = {"body": ("GB_Body_HR", "GB_Body"), "organ": ("GB_Organs_HR", "GB_Organs")}
    done = {}
    for o_name in names["body"]:
        o = bpy.data.objects.get(o_name)
        if o is None:
            continue
        for k, val in body_region_fields(o).items():
            gbc.point_attr(o, k, np.asarray(val, np.float32), 'FLOAT')
        done[o_name] = "body regions"
    for o_name in names["organ"]:
        o = bpy.data.objects.get(o_name)
        if o is None:
            continue
        gbc.point_attr(o, "lk_interior", organ_interior(o).astype(np.float32), 'FLOAT')
        done[o_name] = "interior"
    return done


# ---------------------------------------------------------------------------
# Renders
# ---------------------------------------------------------------------------
TURNTABLE = {
    # name: (camera location, target, lens)
    "body": [((0.0, -3.4, 1.0), (0, 0, 0.92), 50), ((-2.4, -2.4, 1.1), (0, 0, 0.92), 50),
             ((-3.4, 0.0, 1.0), (0, 0, 0.92), 50), ((0.0, 3.4, 1.0), (0, 0, 0.92), 50)],
    "torso": [((0.0, -1.45, 1.30), (0, 0, 1.22), 50), ((-1.0, -1.05, 1.3), (0, 0, 1.22), 50)],
    "head": [((0.0, -0.75, 1.66), (0, -0.02, 1.64), 85), ((-0.52, -0.52, 1.66), (0, -0.02, 1.64), 85)],
    "arm": [((0.9, -0.7, 1.0), (0.42, 0.0, 0.98), 60)],
    "hand": [((0.75, -0.35, 0.90), (0.50, 0.0, 0.86), 85), ((0.80, 0.25, 0.90), (0.50, 0.0, 0.86), 85)],
    "legs": [((0.0, -1.6, 0.5), (0, 0, 0.45), 50)],
    "feet": [((0.35, -0.65, 0.25), (0.08, -0.03, 0.05), 60)],
    # reference stage shared with the Godot side-by-side (same cameras, lights of gb_common.setup_stage)
    "ref": [((0.0, -3.2, 0.95), (0, 0, 0.9), 50), ((-2.05, -2.45, 1.15), (0, 0, 0.9), 50),
            ((-0.52, -0.52, 1.66), (0, -0.02, 1.64), 85), ((0.0, -1.45, 1.30), (0, 0, 1.22), 50)],
    "inner": [((0.0, -1.5, 1.15), (0, 0, 1.1), 50), ((-1.05, -1.05, 1.2), (0, 0, 1.1), 50)],
    "organs": [((0.0, -0.75, 1.22), (0, -0.02, 1.2), 50), ((-0.55, -0.5, 1.25), (0, -0.02, 1.2), 50)],
    "brain": [((-0.35, -0.42, 1.74), (0, 0.01, 1.68), 85)],
    "spine": [((-0.9, 0.9, 1.0), (0, 0.03, 1.0), 50)],
}


def _studio():
    scene = gbc.setup_stage(floor=True)
    return scene


def render_views(prefix, views, objs_visible, out_dir=gbc.RENDER_DIR, samples=32, res=(480, 640)):
    """Render named TURNTABLE views with only ``objs_visible`` visible."""
    _studio()
    shown = set(objs_visible)
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE'):
            o.hide_render = o.name not in shown and o.name != "GB_StageFloor"
    paths = []
    for key in views:
        for i, (loc, tgt, lens) in enumerate(TURNTABLE[key]):
            cam = gbc.add_camera(f"GBL_cam_{key}_{i}", loc, tgt, lens)
            paths.append(gbc.render(os.path.join(out_dir, f"{prefix}_{key}_{i}.png"), cam, samples, res))
    return paths


def main():
    args = gbc.script_args()
    blend = gbc.BLEND_PATH
    if "--blend" in args:
        blend = args[args.index("--blend") + 1]
    bpy.ops.wm.open_mainfile(filepath=blend)
    views = ["body", "torso", "head", "hand", "feet"]
    if "--views" in args:
        views = args[args.index("--views") + 1].split(",")
    out = gbc.RENDER_DIR
    if "--out" in args:
        out = args[args.index("--out") + 1]
    samples = int(args[args.index("--samples") + 1]) if "--samples" in args else 32
    import bake
    bake.show_all_collections()
    if "--baked" in args:
        state = bake.apply_baked_materials()
        vis = ["GB_Body", "GB_Head", "GB_Shorts", "GB_Eye_L", "GB_Eye_R", "GB_Mouth", "GB_BrowLash",
               "GB_EyeFX_L", "GB_EyeFX_R"]
        render_views("lookdev_baked", views, vis, out, samples)
        return state
    build_materials()
    prepare_attributes()
    hr = {"GB_Body_HR", "GB_Head_HR"}
    objs = [bpy.data.objects[n] for n in ("GB_Body_HR", "GB_Head_HR", "GB_Shorts", "GB_Eye_L", "GB_Eye_R",
                                          "GB_Mouth", "GB_BrowLash", "GB_EyeFX_L", "GB_EyeFX_R")
            if n in bpy.data.objects]
    lookdev_on(objs)
    render_views("lookdev", views, [o.name for o in objs] + list(hr), out, samples)


if __name__ == "__main__":
    main()
