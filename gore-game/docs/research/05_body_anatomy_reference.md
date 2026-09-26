# 05 — Full-body anatomy reference for procedural modelling (adult male, 1.78 m, 75 kg)

Project: **Gore Head** (Godot 4.5, Forward+, GDScript, Jolt). This document is research input for the **procedural body generator** (Blender and code), the **skeleton and ragdoll**, the **hit-volume and organ system**, the **spinal-cord and brainstem paralysis map**, and the **bleeding system**, whose vessel waypoints are shared with doc 03.
Scope: body landmarks, surface envelope, every bone to model, the spinal cord and brainstem, the vital organs (not the intestines), and tissue-layer thicknesses. Everything is given in **one coordinate frame**, so the numbers can be typed straight into code.
Audience: technical artists, rigging, gameplay/simulation and VFX engineers. Clinical tone. The subject is a fictional, procedurally generated adult. No real person is modelled.
Cross-references:
- `01_gunshot_wounds.md` (`[D01:Sx]`): skull thickness, wound ballistics.
- `02_sharp_blunt_burn.md` (`[D02:Rx]`): scalp layers, skin and fat colours.
- `03_bleeding_vessels.md` (`[D03:Rx]`): vessel diameters and flows. This document gives the **positions** of the great vessels in the body frame; doc 03 gives their **haemodynamics**.
- `04_neuro_death_eyes.md` (`[D04:Cx]`): brainstem and spinal-cord injury effects. This document gives **where** the brainstem and cord are; doc 04 gives **what happens** when they are hit.

---

## 0. Read this first

### 0.1 Method and limits (important)

- **No web page could be read in this session.**
  - `WebSearch` refused every call: the session's search budget (200 calls) had already been used by earlier research tasks.
  - `WebFetch` returned `EGRESS_BLOCKED` (network egress policy) for every domain tried: en.wikipedia.org, www.ncbi.nlm.nih.gov (StatPearls/Bookshelf), pubmed.ncbi.nlm.nih.gov, radiopaedia.org, teachmeanatomy.info, www.kenhub.com and openstax.org. msis.jsc.nasa.gov (NASA-STD-3000 anthropometry) failed DNS resolution.
  - Following the environment rules, I made no attempt to get around the block. Sibling docs 03 and 04 hit the same block.
- **Consequence: every number here comes from my own knowledge of the standard literature.** That literature is Gray's Anatomy, Moore's *Clinically Oriented Anatomy*, the ANSUR anthropometric surveys, Winter/Dempster segment data, the ICRP reference-man reports, Panjabi's vertebral morphometry, Trotter & Gleser, and the clinical imaging papers listed in §18. **None of these was re-opened in this session.** Each number is tagged (§0.2) so you can see how much weight it carries.
- **The coordinates are an engineering reconstruction.** I fitted anthropometric landmark heights, skeletal stacking (vertebral body plus disc heights), surface-anatomy vertebral levels and the standing plumb line together into one self-consistent body. When two constraints disagreed, I compromised and wrote down the conflict (the main one is the cervicale height, §4.6). Expect **±10–20 mm** accuracy for deep structures, ±5–10 mm for surface landmarks and ±2–5 mm for bone and organ **dimensions**. That is fine for a game body. It is not a surgical atlas.
- Before a number is shown to the player as a "forensic readout", QA should check it against the source listed in §16.

### 0.2 Tags and confidence

| Tag | Meaning |
|---|---|
| `[Bn]` | A specific published source (§18), cited from memory. Not re-read in this session. |
| `[D0x:…]` | A sibling research document in this folder. |
| `[K]` | General textbook anatomy (Gray's, Moore, Netter). No specific source was retrieved. |
| `[E]` | Engineering derivation or fit. The arithmetic or constraint is stated. |
| `[G]` | Game-design choice within, or at the edge of, the real range. |
| **(H) / (M) / (L)** | My confidence that the real value lies in the stated range: high, medium or low. |

### 0.3 Reference body

| Property | Value | Notes | Source |
|---|---|---|---|
| Sex, age | male, ~30 y | Adult, fused epiphyses, costal cartilages not yet calcified | [G] |
| Stature H | 1.780 m | | brief |
| Mass | 75 kg | BMI 23.7 | brief |
| Body fat | ~15 % (12–18 %) | Lean-average. Fixes subcutaneous fat depths in §12 | [G] (M) |
| Body surface area | 1.93 m² | DuBois: 0.007184 × 75^0.425 × 178^0.725 | [E] |
| Body volume | ~70.5 L (+~3 L lung air at FRC) | Whole-body density ≈ 1.064 g/mL at 15 % fat | [E] |
| Closest published reference body | ICRP Reference Adult Male: 1.76 m, 73 kg | Organ masses in §10–11 are anchored to it | [B43] (H) |
| Blood volume | ~5.3 L (70 mL/kg) | Same as doc 03 | [B43] [D03] |

### 0.4 Coordinate frame (use this everywhere)

- **Units: metres.** **+Z up.** The body **faces −Y** (so the back is +Y). The **character's left is +X** and the right is −X.
- **Origin (0, 0, 0)**: on the floor, midway between the feet (x = 0), on the standing **line of gravity** (y = 0). The line of gravity falls **≈ 43 % of foot length in front of the heels**, which is ≈ 5 cm in front of the ankle-joint centres `[B3] [E] (M)`.
  - If you would rather put the origin at the geometric mid-foot, add **−0.019 m to every y**.
- **Pose: relaxed A-pose.**
  - Standing upright, knees straight, head in the Frankfort horizontal plane (ear canal and lower orbital rim level).
  - Arms abducted **30° from vertical** in the coronal plane, elbows straight, forearms in neutral rotation (thumbs forward, palms facing the thighs).
  - Feet ~19 cm apart at the ankles, toes out 7° each side.
- **Mirror rule**: every bilateral structure is given for the **left (+X)** side unless the table shows ±x. For the right side, negate x.
- **This is Blender's convention** (Z up, character facing −Y, the character's left on +X). Blender's glTF exporter converts it to Godot as **(x, y, z)_Godot = (x, z, −y)_body**.
  - The imported character then faces **+Z** in Godot, with its left on +X. Godot 4 treats +Z as the model front: `Vector3.MODEL_FRONT` `[K] (M)`.
  - If you generate geometry directly in GDScript, apply the same mapping: `Vector3(x, z, -y)`.
- **Existing head:** its origin sits **midway between the ear canals, at (0.000, +0.020, 1.655)**. In Godot coordinates that is `(0, 1.655, -0.020)`.
  - Every head-internal structure in this document is also given relative to that point (§3, §9), so the existing head can be dropped onto this body without refitting.
  - If the existing head was modelled with a different vertex-to-ear-canal distance, scale it so that **vertex − ear canal = 0.125 m** (the ear canal sits 12.5 cm below the vertex).

### 0.5 Anatomical terms used in the tables

- **Anterior** = front (−Y). **Posterior** = back (+Y). **Superior/cranial** = up (+Z). **Inferior/caudal** = down (−Z). **Medial** = towards x = 0. **Lateral** = away from x = 0.
- **MCL** = midclavicular line (x ≈ ±0.090–0.100 on this body). **AAL / MAL / PAL** = anterior, mid and posterior axillary lines. **ICS** = intercostal space. **cc** = costal cartilage.
- **Tn / Ln / Cn** refer to vertebral levels. A structure "at T8" has the same z as the **T8 vertebral body centre** in §4.1.

---

## 1. Master landmark table (copy into code)

All values are in metres in the §0.4 frame. "Bone" means the point on the skeleton and "skin" the palpable surface point. Surface points are what the mesh must pass through. Bone points drive the rig and the hit volumes.

### 1.1 Head and neck

| # | Landmark | x | y | z | Level / note | Source |
|---|---|---|---|---|---|---|
| 1 | Vertex (skin, top of head) | 0.000 | +0.020 | 1.780 | = H | brief |
| 2 | **Head origin** (midway between ear canals) | 0.000 | +0.020 | 1.655 | 12.5 cm below the vertex | [B1] [B37] [E] (M) |
| 3 | Ear canal opening (porion region), L | +0.068 | +0.020 | 1.655 | Bitragion breadth ~14.5 cm | [B1] [B37] (M) |
| 4 | Tragion (skin notch above the tragus), L | +0.073 | +0.012 | 1.658 | | [B37] (M) |
| 5 | Glabella (skin) | 0.000 | −0.078 | 1.683 | Head length 19.5 cm to opisthocranion | [B1] (M) |
| 6 | Nasion (skin) | 0.000 | −0.072 | 1.676 | | [B37] (M) |
| 7 | Cornea apex, L eye | +0.032 | −0.074 | 1.666 | Eye height 0.936 H. Interpupillary 64 mm | [B3] [B37] (H) |
| 8 | Eyeball centre, L | +0.032 | −0.062 | 1.666 | Globe Ø 24 mm | [K] (H) |
| 9 | Pronasale (nose tip) | 0.000 | −0.106 | 1.625 | | [B37] (M) |
| 10 | Stomion (lip junction) | 0.000 | −0.088 | 1.592 | | [B37] (M) |
| 11 | Pogonion (most anterior chin, skin) | 0.000 | −0.088 | 1.562 | | [B37] (M) |
| 12 | **Menton (chin, lowest point)** | 0.000 | −0.068 | 1.550 | 0.870 H. Head height 23 cm | [B3] [B1] (H) |
| 13 | Gonion (angle of mandible), L | +0.052 | −0.005 | 1.585 | Bigonial 10.4 cm (skin) | [B37] (M) |
| 14 | Mastoid tip, L | +0.055 | +0.030 | 1.620 | ~3.5 cm below the ear canal. Level of C1 | [K] (M) |
| 15 | Inion (external occipital protuberance) | 0.000 | +0.112 | 1.662 | | [K] (M) |
| 16 | Opisthocranion (back of head) | 0.000 | +0.117 | 1.700 | | [B1] (M) |
| 17 | Euryon (widest point), L | +0.0775 | +0.025 | 1.705 | Head breadth 15.5 cm | [B1] (M) |
| 18 | Hyoid body | 0.000 | −0.030 | 1.556 | C3/C4 | [K] (M) |
| 19 | Laryngeal prominence (skin) | 0.000 | −0.062 | 1.537 | C4/C5. Bone (cartilage) at y −0.058 | [K] (M) |
| 20 | Cricoid cartilage (skin) | 0.000 | −0.055 | 1.515 | C6. Cartilage at y −0.047 | [K] (M) |
| 21 | **C7 spinous tip (cervicale, skin)** | 0.000 | +0.075 | 1.500 | See the conflict note in §4.6. Surveys suggest 1.51–1.53 | [B1] [E] (M/L) |
| 22 | **Suprasternal (jugular) notch, skin** | 0.000 | −0.048 | 1.455 | T2/T3. Bone at (0, −0.042, 1.453) | [B1] [K] (M) |

### 1.2 Trunk and pelvis

| # | Landmark | x | y | z | Level / note | Source |
|---|---|---|---|---|---|---|
| 23 | Sternoclavicular (SC) joint, L | +0.025 | −0.040 | 1.450 | Flanks the notch | [K] (M) |
| 24 | Acromioclavicular (AC) joint, L | +0.165 | +0.010 | 1.462 | | [K] (M) |
| 25 | **Acromion, lateral tip (bone)**, L | +0.200 | +0.015 | 1.458 | 0.819 H. Biacromial ~40–41 cm on skin | [B1] [B3] (H) |
| 26 | **Glenohumeral joint centre**, L | +0.180 | +0.020 | 1.415 | Humeral head centre, 4.3 cm below the acromion | [K] [E] (M) |
| 27 | Sternal angle (skin) | 0.000 | −0.075 | 1.405 | T4/T5. 2nd costal cartilages. Bone at y −0.064 | [K] [B32] (H) |
| 28 | **Nipple**, L | +0.100 | −0.112 | 1.300 | 4th ICS to 5th rib, MCL. Chest height 0.72–0.73 H | [B1] [B3] (M) |
| 29 | Xiphisternal joint (skin) | 0.000 | −0.110 | 1.305 | T9. Bone at y −0.100 | [K] [B32] (M) |
| 30 | **Xiphoid tip (bone)** | 0.000 | −0.094 | 1.273 | Xiphoid 3.5 cm long | [K] (M) |
| 31 | Inferior angle of scapula, L | +0.085 | +0.105 | 1.325 | T7–T8 | [K] (M) |
| 32 | T7 spinous tip (skin) | 0.000 | +0.122 | 1.335 | | [E] |
| 33 | Lowest costal margin (10th costal cartilage), L | +0.112 | −0.050 | 1.125 | Subcostal plane ≈ L3 | [K] [B32] (M) |
| 34 | **Navel** (umbilicus, skin depression) | 0.000 | −0.108 | 1.075 | L3/L4 to L4 when standing. Surrounding skin at y ≈ −0.118 | [B1] [B32] (M) |
| 35 | **Iliac crest, highest point**, L | +0.140 | +0.025 | 1.070 | Supracristal plane = L4/L5 | [B1] [K] (M) |
| 36 | Iliac tubercle (widest part of crest), L | +0.143 | −0.030 | 1.055 | Bicristal breadth 28.5 cm (bone) | [K] (M) |
| 37 | **ASIS (bone)**, L | +0.122 | −0.062 | 1.009 | Inter-ASIS 24.5 cm. Skin at y −0.072 | [B9] [K] (M) |
| 38 | PSIS (bone), L | +0.045 | +0.090 | 1.010 | S2. "Dimples of Venus" on the skin at y +0.100 | [K] (M) |
| 39 | L4 spinous tip (skin) | 0.000 | +0.080 | 1.080 | Bone at y +0.055 | [E] |
| 40 | **Pubic symphysis**, upper border (bone, anterior) | 0.000 | −0.068 | 0.928 | Level with the greater-trochanter tips. Centre (0, −0.062, 0.905) | [K] [E] (M) |
| 41 | **Hip joint centre (femoral head)**, L | +0.087 | −0.015 | 0.935 | Bell's method from the ASIS (§7.1) | [B9] [E] (M) |
| 42 | **Greater trochanter, lateral surface (bone)**, L | +0.158 | 0.000 | 0.930 | 0.52–0.53 H. Skin at x +0.178 | [B1] [B3] (M) |
| 43 | Ischial tuberosity, lowest point, L | +0.055 | +0.020 | 0.858 | | [K] [E] (M) |
| 44 | Coccyx tip | 0.000 | +0.040 | 0.905 | | [E] (L) |
| 45 | Crotch (perineum, skin) | 0.000 | +0.005 | 0.840 | Crotch height ~0.47 H | [B1] (M) |
| 46 | Gluteal fold, L | +0.090 | +0.120 | 0.820 | | [E] (L) |

### 1.3 Limbs (A-pose)

| # | Landmark | x | y | z | Note | Source |
|---|---|---|---|---|---|---|
| 47 | **Elbow joint centre** (flexion axis), L, A-pose | +0.330 | +0.020 | 1.155 | Glenohumeral centre + 0.300 m × (sin 30°, 0, −cos 30°) | [E] |
| 48 | Lateral epicondyle, L, A-pose | +0.358 | +0.020 | 1.171 | Epicondylar width 6.3 cm | [K] [E] |
| 49 | Medial epicondyle, L, A-pose | +0.300 | +0.020 | 1.138 | | [K] [E] |
| 50 | **Wrist joint centre**, L, A-pose | +0.455 | +0.020 | 0.938 | Elbow + 0.250 m along the same direction | [E] |
| 51 | Middle-finger MCP (knuckle), L, A-pose | +0.503 | +0.020 | 0.856 | Wrist + 0.095 m | [E] |
| 52 | Middle fingertip, L, A-pose (fingers straight) | +0.548 | +0.020 | 0.778 | Hand length 19.2 cm | [B3] [E] |
| 53 | Elbow centre, arms hanging (for reference) | +0.195 | +0.030 | 1.115 | 0.630 H | [B3] (H) |
| 54 | Wrist centre, arms hanging | +0.225 | +0.010 | 0.865 | 0.485 H. Supinated, carrying angle ~10° | [B3] (H) |
| 55 | **Knee joint centre** (epicondylar axis), L | +0.092 | +0.020 | 0.505 | The joint line (tibial plateau) is at z 0.487 | [B1] [B3] (M) |
| 56 | Patella centre (bone), L | +0.090 | −0.035 | 0.522 | Skin in front at y −0.047 | [K] (M) |
| 57 | Tibial tuberosity, L | +0.090 | −0.025 | 0.447 | | [K] (M) |
| 58 | Fibular head, L | +0.130 | +0.035 | 0.465 | | [K] (M) |
| 59 | **Ankle joint centre** (mid-malleolar), L | +0.095 | +0.050 | 0.075 | Line of gravity 5 cm in front | [B1] [B3] (M) |
| 60 | Lateral malleolus tip, L | +0.132 | +0.060 | 0.055 | ~1 cm lower than the medial | [K] (H) |
| 61 | Medial malleolus tip, L | +0.065 | +0.045 | 0.068 | | [K] (M) |
| 62 | Heel, most posterior (skin), L | +0.095 | +0.115 | 0.030 | | [E] |
| 63 | 1st MTP joint (ball of the big toe), L | +0.084 | −0.083 | 0.020 | | [E] |
| 64 | 5th MTP joint, L | +0.161 | −0.049 | 0.018 | | [E] |
| 65 | Tip of the 2nd toe, L | +0.128 | −0.151 | 0.010 | Foot length 26.8 cm, toe-out 7° | [B1] [E] |

**How the table was fitted** `[E]`:
- **Heights** come from the ANSUR stature ratios `[B1] [B2]` and the Drillis–Contini segment fractions `[B3] [B4]`, scaled to H = 1.78 m. Examples: acromion 0.819 H, chest 0.72–0.73 H, elbow 0.63 H, wrist 0.485 H, trochanter 0.52–0.53 H, knee 0.28 H, ankle 0.04 H.
- **Front-to-back positions** come from the ideal standing plumb line `[B8]`. It passes through the ear canal, the cervical bodies and the shoulder joint, just behind the hip centre (1.5 cm), just in front of the knee axis (2 cm) and 5 cm in front of the ankle. Everything else is placed from bone and organ depths (§4–§11).

---

## 2. Body envelope: circumferences, widths, cross-sections, segment masses

### 2.1 Target girths and widths (skin)

The girths are for a lean-average 75 kg / 1.78 m man. The ANSUR II means `[B1]` describe a heavier cohort (≈ 85 kg, BMI ≈ 27.7), so I scaled girths by ≈ √(75/85) ≈ 0.94 and trimmed the waist further, because waist girth is the most fat-sensitive measurement `[E] (M)`.

| Level | z (m) | Circumference (cm) | Breadth x (cm) | Depth y (cm) | Section centre (x, y) | Range for 70–80 kg men | Source |
|---|---|---|---|---|---|---|---|
| Head (max, glabella–opisthocranion) | 1.700 | 57.5 | 15.5 | 19.5 | (0, +0.020) | 55–60 | [B1] [B37] (H) |
| Neck (just below the larynx) | 1.515 | 38.0 | 12.0 | 11.7 | (0, +0.004): front −0.055, back +0.063 | 36–40 | [B1] (M) |
| Shoulders, bideltoid | 1.400 | — | 47.0 | — | — | 44–50 | [B1] (M) |
| Shoulders, biacromial (skin over acromia) | 1.458 | — | 40.5 | — | — | 38–42 | [B1] (H) |
| **Chest (at the nipples)** | 1.300 | **98** | 31.5 | 23.0 | (0, +0.003): front −0.112, back +0.118 | 92–104 | [B1] [E] (M) |
| Natural waist (narrowest) | 1.130 | 81 | 28.0 | 19.5 | (0, −0.018) | 76–86 | [B1] [E] (M) |
| **Waist at the navel** | 1.075 | **84** | 29.5 | 20.5 | (0, −0.016): front −0.118, back +0.087 | 78–90 | [B1] [E] (M) |
| **Hips / buttocks (max)** | 0.885 | **97** | 35.0 | 23.5 | (0, +0.028): front −0.090, back +0.145 | 93–101 | [B1] (M) |
| **Upper thigh** (below the gluteal fold) | 0.790 | **56** | 17.5 | 18.5 | (±0.090, +0.020) | 52–60 | [B1] (M) |
| Mid-thigh | 0.700 | 51 | 16.0 | 16.5 | (±0.092, +0.015) | 47–55 | [K] (M) |
| Knee (mid-patella) | 0.520 | 37.5 | 11.0 | 11.5 | (±0.091, +0.010) | 35–40 | [B1] (M) |
| **Calf (max)** | 0.370 | **37.5** | 11.5 | 12.5 | (±0.094, +0.070): shin front +0.008, calf back +0.133 | 35–40 | [B1] (M) |
| Ankle (min, above the malleoli) | 0.120 | 22.5 | 6.5 | 7.5 | (±0.095, +0.055) | 21–24 | [B1] (M) |
| **Upper arm (mid, relaxed)** | along the arm | **30** | 9.0 | 10.0 | on the humeral axis | 28–33 (flexed +3) | [B1] (M) |
| **Forearm (max, 5 cm below the elbow)** | along the arm | **27.5** | 8.5 | 7.5 | | 26–29 | [B1] (M) |
| Wrist | along the arm | 17.0 | 5.8 | 4.0 | | 16–18 | [B1] (M) |
| Hand | | — | 8.7 (metacarpal breadth) | 3.0 (thickness at the metacarpals) | length 19.2 | | [B1] [B3] (H) |
| Foot | | — | 10.2 | — | length 26.8 | | [B1] (H) |

**Cross-section shape** `[E] (M)`:
- Human trunk sections are **boxier than ellipses**. With ANSUR chest breadth and depth, the true chest girth is ≈ 1.16 × the girth of the inscribed ellipse.
  - Model the torso rings as **superellipses** |x/a|ⁿ + |y/b|ⁿ = 1. Pick **n ≈ 3–4 at the chest** and **n ≈ 2.5–3 at the waist, hips and limbs**, then tune n until the ring's perimeter matches the circumference column.
- **Offset the section centre in y**, not only the size. The chest centre is ~2 cm behind the waist centre, the buttock centre bulges back (+0.028), and the calf's centre is 7 cm behind the shin.
  - That front-to-back asymmetry is what makes a body read as human rather than as a stack of tubes.
- **The limbs are not centred on their bones.** The femur runs ~1 cm anterolateral to the centre of the thigh section. The tibia's anteromedial face is **subcutaneous** (skin to bone 3–6 mm, §12), with the calf muscle mass behind it. The humerus is roughly central in the arm.

### 2.2 Segment masses and centres of mass (for the Jolt ragdoll)

Dempster's cadaver data as tabulated by Winter `[B3] [B5] (H)`: segment mass = fraction × 75 kg. The COM fraction is measured from the proximal joint along the segment.

| Segment | Proximal → distal joint (body frame, §1) | Mass fraction | Mass (kg) | COM from proximal | Radius of gyration about COM / length |
|---|---|---|---|---|---|
| Head + neck | C7/T1 → ear canal | 0.081 | 6.08 | 1.000 (**COM ≈ at the ear canal, i.e. the head origin**) | 0.495 |
| Trunk (total) | greater trochanter → glenohumeral | 0.497 | 37.3 | 0.50 | — |
| — thorax | C7/T1 → T12/L1 | 0.216 | 16.2 | 0.82 | — |
| — abdomen | T12/L1 → L4/L5 | 0.139 | 10.4 | 0.44 | — |
| — pelvis | L4/L5 → greater trochanter | 0.142 | 10.65 | 0.105 | — |
| Upper arm (each) | glenohumeral → elbow | 0.028 | 2.10 | 0.436 | 0.322 |
| Forearm (each) | elbow → wrist | 0.016 | 1.20 | 0.430 | 0.303 |
| Hand (each) | wrist → 2nd knuckle, middle finger | 0.006 | 0.45 | 0.506 | 0.297 |
| Thigh (each) | hip centre → knee centre | 0.100 | 7.50 | 0.433 | 0.323 |
| Leg / shank (each) | knee centre → ankle | 0.0465 | 3.49 | 0.433 | 0.302 |
| Foot (each) | ankle → 2nd metatarsal head | 0.0145 | 1.09 | 0.50 | 0.475 |

Check: 6.08 + 37.3 + 2 × (2.10 + 1.20 + 0.45 + 7.50 + 3.49 + 1.09) = 75.0 kg `[E]`.

### 2.3 Rig joint table (Skeleton3D, body frame, left side)

Suggested humanoid bones. Heads and tails are joint centres from §1 and §4. The parent is listed so the table can be looped over.

| Bone | Parent | Head (x, y, z) | Tail (x, y, z) | Length (m) | Note |
|---|---|---|---|---|---|
| `hips` | root | (0, −0.005, 0.965) | (0, +0.006, 1.027) | 0.063 | Pelvis. Tail at the centre of the S1 endplate |
| `spine` (lumbar) | hips | (0, +0.006, 1.027) | (0, +0.002, 1.212) | 0.185 | L5/S1 → T12/L1 |
| `chest` (lower thoracic) | spine | (0, +0.002, 1.212) | (0, +0.049, 1.353) | 0.149 | → T7 |
| `upper_chest` | chest | (0, +0.049, 1.353) | (0, +0.015, 1.490) | 0.141 | → C7/T1 |
| `neck` | upper_chest | (0, +0.015, 1.490) | (0, +0.015, 1.630) | 0.140 | → occipital condyles (atlanto-occipital joint) |
| `head` | neck | (0, +0.015, 1.630) | (0, +0.020, 1.780) | 0.150 | **Put the existing head's origin at (0, +0.020, 1.655)**, a child offset of (0, +0.005, +0.025) from the bone head |
| `clavicle.L` | upper_chest | (+0.025, −0.040, 1.450) | (+0.165, +0.010, 1.462) | 0.149 | SC → AC |
| `upper_arm.L` | clavicle.L | (+0.180, +0.020, 1.415) | (+0.330, +0.020, 1.155) | 0.300 | A-pose, 30° |
| `forearm.L` | upper_arm.L | (+0.330, +0.020, 1.155) | (+0.455, +0.020, 0.938) | 0.250 | |
| `hand.L` | forearm.L | (+0.455, +0.020, 0.938) | (+0.503, +0.020, 0.856) | 0.095 | → middle MCP |
| `thigh.L` | hips | (+0.087, −0.015, 0.935) | (+0.092, +0.020, 0.505) | 0.431 | |
| `shin.L` | thigh.L | (+0.092, +0.020, 0.505) | (+0.095, +0.050, 0.075) | 0.431 | |
| `foot.L` | shin.L | (+0.095, +0.050, 0.075) | (+0.119, −0.079, 0.025) | 0.140 | → ball of the foot (2nd metatarsal head) |
| `toes.L` | foot.L | (+0.119, −0.079, 0.025) | (+0.128, −0.151, 0.010) | 0.074 | |

- **Head pivots** `[K] (H)`:
  - Nodding (flexion–extension, ~25° of the total) happens at the **atlanto-occipital joint**, (0, +0.015, 1.630).
  - About 50 % of neck rotation happens at **C1–C2** around the dens axis, which is vertical through (0, +0.008, 1.61).
  - The rest is spread over C2–C7.
  - If the rig has only one neck bone, put its head at C7/T1 as above.

### 2.4 Simulation parameters: envelope

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `stature` | 1.780 | m | All heights scale linearly with stature (§14.3) | brief |
| `mass_total` | 75 | kg | | brief |
| `girth_chest / waist_navel / hips` | 98 / 84 / 97 | cm | ±6 cm covers 70–80 kg | [B1] [E] (M) |
| `girth_neck / upperarm / forearm / wrist` | 38 / 30 / 27.5 / 17 | cm | | [B1] (M) |
| `girth_thigh_upper / mid / knee / calf / ankle` | 56 / 51 / 37.5 / 37.5 / 22.5 | cm | | [B1] (M) |
| `breadth_biacromial / bideltoid / chest / hip` | 40.5 / 47 / 31.5 / 35 | cm | | [B1] (M) |
| `depth_chest / waist / buttock` | 23 / 20.5 / 23.5 | cm | | [B1] [E] (M) |
| `superellipse_n_chest / waist / limbs` | 3.5 / 2.8 / 2.5 | — | Tune to match the girths | [E] |
| `segment_mass_fractions` | table §2.2 | — | Dempster / Winter | [B3] [B5] (H) |
| `line_of_gravity_y` | 0 (origin) | m | 5 cm in front of the ankles, 1.5 cm behind the hip centres | [B8] [E] (M) |

### 2.5 Visual/behavioural checklist: envelope

- In profile, the **ear canal, the shoulder-joint centre, the greater trochanter and a point just in front of the ankle line up vertically**. If the head sits in front of the shoulder, the model looks slumped. If the chest sits behind the hips, it looks as if it is leaning back.
- The **lumbar hollow** is real. The back skin at L3 is ~4 cm further forward than at T7 (y +0.08 vs +0.122). The buttocks then bulge back to y +0.145.
- The **shoulders slope**. The acromion (1.458) is 4 cm below C7 (1.50) and at the same height as the jugular notch (1.455).
- **Nipples sit 15.5 cm below the jugular notch and 20 cm apart. The navel is ~20 cm below the xiphoid tip and ~23 cm below the xiphisternal joint.** These proportions are what players notice first.
- **Arms in A-pose**: the fingertips reach z ≈ 0.78 (mid-thigh) at x ≈ ±0.55. The palms face the thighs.

---

## 3. Head–neck interface

The head already exists. This section gives what the body needs from it: where the skull base, the face and the larynx meet the neck, in both frames.

### 3.1 Head and skull dimensions (check the existing head against these)

| Measure | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Head length (glabella–opisthocranion, skin) | 19.5 (18.5–20.5) | cm | | [B1] (H) |
| Head breadth (euryon–euryon, skin) | 15.5 (14.5–16.5) | cm | | [B1] (H) |
| Head height (vertex–menton) | 23.0 (21.5–24.5) | cm | 0.13 H | [B1] [B3] (H) |
| Vertex → ear canal (vertical) | 12.5 (12–13.5) | cm | Tragion to top of head | [B1] [B37] (M) |
| Ear canal → menton (vertical) | 10.5 | cm | | [E] |
| Bitragion breadth | 14.5 | cm | | [B1] (H) |
| Bizygomatic breadth | 14.0 | cm | | [B37] (H) |
| Bigonial breadth (bone) | 9.5–10.0 | cm | | [B37] (M) |
| Skull (bone) maximum length / breadth | 18.5 / 14.0 | cm | | [B38] (H) |
| Basion–bregma height | 13.5–14.0 | cm | | [B38] (M) |
| Vault thickness: frontal / parietal / temporal / occipital | 8 / 7–10 / 4.7 / 8–10 | mm | Diploë sandwiched between two cortical tables | [D01:S31] |
| Cranial capacity / brain mass | ~1,450 / 1,400 (1,300–1,450) | mL / g | | [B43] [B17] (H) |
| Mandible: ramus height / body height at the molars / symphysis height | 6.0 / 3.0 / 3.2 | cm | Cortex 2–3 mm; inferior border 3–5 mm | [K] (M) |
| Foramen magnum (AP × transverse) | 35 × 30 | mm | | [K] (H) |

### 3.2 Skull-base and neck points, body frame and relative to the head origin

Relative offsets are (point − head origin), with the head origin at (0, +0.020, 1.655).

| Point | Body frame (x, y, z) | Relative to head origin (x, y, z) | Level / note | Source |
|---|---|---|---|---|
| Sella turcica (pituitary fossa) | (0, 0.000, 1.676) | (0, −0.020, +0.021) | ~2 cm above the Frankfort plane and 2 cm in front of the ear canal | [B38] [E] (M) |
| Basion (anterior rim of the foramen magnum) | (0, +0.018, 1.634) | (0, −0.002, −0.021) | Clivus runs from here up and forward to the dorsum sellae | [B38] [E] (M) |
| Opisthion (posterior rim of the foramen magnum) | (0, +0.053, 1.628) | (0, +0.033, −0.027) | | [E] (M) |
| Foramen magnum centre | (0, +0.035, 1.631) | (0, +0.015, −0.024) | | [E] (M) |
| Occipital condyles (atlanto-occipital joints) | (±0.013, +0.020, 1.628) | (±0.013, 0.000, −0.027) | Head-nod pivot | [K] (M) |
| Dens tip (C2) | (0, +0.010, 1.627) | (0, −0.010, −0.028) | 5–7 mm below the basion | [K] (M) |
| C1 ring centre | (0, +0.020, 1.618) | (0, 0.000, −0.037) | Anterior arch at y −0.003; posterior arch at y +0.050 | [K] [E] (M) |
| C1 transverse process tip, L | (+0.039, +0.020, 1.618) | (+0.039, 0.000, −0.037) | Just below and in front of the mastoid tip. C1 is the widest cervical vertebra, ~78 mm | [K] (M) |
| Hyoid body | (0, −0.030, 1.556) | (0, −0.050, −0.099) | C3/C4 | [K] (M) |
| Glottis (vocal folds) | (0, −0.035, 1.532) | (0, −0.055, −0.123) | C5 | [K] (M) |

### 3.3 Simulation parameters: head–neck interface

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `head_origin_body` | (0, +0.020, 1.655) | m | Midway between the ear canals | [E] (M) |
| `head_origin_godot` | (0, 1.655, −0.020) | m | glTF mapping (x, z, −y) | [K] |
| `vertex_to_earcanal` | 0.125 | m | Scale the head to this if it differs | [B1] [B37] (M) |
| `basion_rel_head` | (0, −0.002, −0.021) | m | | [E] (M) |
| `atlanto_occipital_pivot` | (0, +0.015, 1.630) | m | | [K] [E] (M) |
| `neck_length_front` (menton → jugular notch) | 0.095 | m | | [E] |
| `neck_length_back` (inion → C7 spinous tip) | 0.16 (0.13–0.17) | m | | [E] (L) |

### 3.4 Visual/behavioural checklist: head–neck

- The **back of the neck is longer than the front**. The occiput overhangs the nape, and the hairline and inion sit 16 cm above C7. The chin sits only ~9.5 cm above the jugular notch.
- The **mastoid tip lies just behind and below the ear lobe**, at the level of C1. A lateral gunshot at ear-lobe height passes through the region of the C1 arch and the cervicomedullary junction (§9).
- **The larynx moves.** The hyoid and thyroid cartilage rise ~2 cm on swallowing, and the laryngeal prominence is visible in lean men.

---

## 4. Vertebral column, sacrum, coccyx

### 4.1 Vertebra table (body centres, sizes, canal, cord)

- All vertebrae have x = 0.
- **Body height** is the mid-body height. **Width** and **depth** are endplate transverse and AP sizes. **Disc** is the mean height of the disc below.
- **Canal** is AP × transverse. **Spinous tip Δy** is the distance from the body centre back to the spinous-process tip (bone).
- **Cord y** is the spinal cord's centre (§9) at that level.
- Sizes are from Panjabi's morphometry `[B10] [B11] [B12]` and Gilad & Nissan `[B33]`, cited from memory (M). Positions are fitted `[E]` (§4.6).

| Level | Body centre y | Body centre z | Body height (mm) | Width (mm) | Depth (mm) | Disc below (mm) | Canal AP × W (mm) | Spinous tip Δy (mm) | Transverse-process span (mm) | Cord centre y | Surface / organ landmarks at this level |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 (atlas, ring) | +0.020 | 1.618 | 10 (anterior arch) | 78 (outer, incl. transverse processes) | 45 (outer ring) | — (no disc; C1–C2 synovial) | 30 × 28 (incl. dens) | 30 (posterior tubercle) | 78 | +0.024 | Mastoid tip, ear lobe |
| C2 (axis) | +0.012 | 1.596 | 23 (+15 dens = 38) | 17 | 15.5 | 5 | 16 × 24 | 43 (large, bifid) | 58 | +0.027 | Angle of mandible |
| C3 | +0.007 | 1.574 | 14 | 16.5 | 15.5 | 5 | 14.5 × 23 | 40 | 52 | +0.023 | Hyoid (C3/4) |
| C4 | +0.004 | 1.555 | 14 | 17.5 | 15.5 | 5 | 14 × 24 | 40 | 52 | +0.020 | Upper border of the thyroid cartilage; carotid bifurcation |
| C5 | +0.003 | 1.536 | 13.5 | 18.5 | 16 | 5 | 14 × 24 | 42 | 53 | +0.019 | Laryngeal prominence, glottis |
| C6 | +0.004 | 1.518 | 13.5 | 20 | 16.5 | 5 | 14 × 24 | 45 | 55 | +0.020 | Cricoid; start of the trachea and oesophagus; carotid tubercle |
| C7 | +0.010 | 1.500 | 15 | 22 | 16.5 | 5 | 14 × 23 | 57 (vertebra prominens) | 70 | +0.026 | C7 spinous tip (cervicale) |
| T1 | +0.019 | 1.481 | 16 | 26 | 16.5 | 4.5 | 14 × 19 | 60 | 75 | +0.035 | Lung apex (posterior); 1st rib |
| T2 | +0.028 | 1.461 | 17 | 27 | 17.5 | 4.5 | 14 × 17 | 60 | 70 | +0.044 | Jugular notch (T2/T3); superior angle of the scapula |
| T3 | +0.036 | 1.441 | 17.5 | 27 | 18.5 | 4.5 | 14 × 16 | 61 | 67 | +0.053 | Scapular spine root (spinous level) |
| T4 | +0.042 | 1.420 | 18 | 27.5 | 20 | 5 | 13.5 × 15.5 | 62 | 65 | +0.060 | **Sternal angle (T4/5)**; aortic arch ends; carina (T4–T5) |
| T5 | +0.046 | 1.398 | 18.5 | 28.5 | 22 | 5 | 13.5 × 15.5 | 63 | 63 | +0.065 | Pulmonary trunk bifurcation |
| T6 | +0.049 | 1.376 | 19 | 30 | 24 | 5 | 13.5 × 15.5 | 64 | 62 | +0.069 | Heart base / left atrium |
| T7 | +0.049 | 1.353 | 19.5 | 31 | 26 | 5 | 13.5 × 15.5 | 64 | 60 | +0.069 | Inferior angle of the scapula (T7/8) |
| T8 | +0.046 | 1.329 | 20 | 32.5 | 27.5 | 5.5 | 14 × 16 | 63 | 58 | +0.067 | IVC hiatus; central tendon |
| T9 | +0.040 | 1.305 | 21 | 34 | 28.5 | 6 | 14 × 16 | 62 | 57 | +0.061 | **Xiphisternal joint** |
| T10 | +0.031 | 1.280 | 22 | 37 | 29.5 | 6.5 | 14.5 × 17 | 62 | 55 | +0.053 | Oesophageal hiatus; lung base, posterior (expiration) |
| T11 | +0.020 | 1.254 | 23 | 40 | 31 | 7 | 15 × 18 | 58 | 50 | +0.043 | Cardia (gastro-oesophageal junction) |
| T12 | +0.008 | 1.227 | 24 | 42 | 32 | 8 | 16 × 21 | 58 | 45 | +0.031 | Aortic hiatus; pleural reflection (posterior); upper pole of the left kidney |
| L1 | −0.004 | 1.197 | 25.5 | 43 | 33 | 10 | 17 × 22 | 68 | 70 | +0.021 (conus) | **Transpyloric plane (L1)**; renal hila (supine); **conus tip at L1/L2** |
| L2 | −0.013 | 1.161 | 26.5 | 45 | 34 | 11 | 17 × 23 | 70 | 80 | +0.013 (cauda) | Renal hila (standing) |
| L3 | −0.018 | 1.124 | 27 | 48 | 35 | 12 | 16 × 23 | 70 | 90 (longest) | +0.008 (cauda) | **Subcostal plane**; lowest costal margin |
| L4 | −0.016 | 1.087 | 27 | 50 | 35 | 12 | 16 × 24 | 70 | 85 | +0.011 (cauda) | **Navel (L3/4–L4)**; aortic bifurcation; iliac crests (L4/5) |
| L5 | −0.005 | 1.050 | 26.5 (anterior 28, posterior 24) | 52 | 35 | 11 (anterior 14, posterior 7) | 17 × 26 | 65 | 85 | +0.022 (cauda) | IVC formation |
| S1 (body centre) | +0.014 | 1.012 | — | 50 | 30 | — | 15 × 30 (sacral canal) | — | — | sac to S2 | Promontory; S1 endplate centre (0, +0.006, 1.027) |

**Interpolate between rows** for anything at a disc level (for example T4/T5 = mean of T4 and T5).

**Body-local geometry of a vertebra** (for procedural generation) `[K] (M)`:
- **Body**: a short elliptic cylinder, width × depth × height as in the table. It is slightly concave on its front and sides (waisted by 1–2 mm). The posterior face is flat or slightly concave toward the canal.
- **Pedicles** run backward from the posterolateral top half of the body, for 20–40 % of the canal AP.
  - Width: cervical 5–7 mm; thoracic 4–8 mm (narrowest T4–T6, ~4.5 mm); lumbar 8–18 mm (widest L5).
  - Height: 7–9 mm (cervical), 12–16 mm (lumbar).
- **Laminae** close the canal behind. They are 5–7 mm (cervical) to 8–12 mm (lumbar) thick.
- **Spinous processes**:
  - Cervical (C3–C6): short, bifid, nearly horizontal.
  - **Thoracic: long, sloping 40–60° downward.** From T5 to T8 each tip overlaps the vertebra below, so a mid-thoracic spinous tip lies at the level of the **next** vertebral body.
  - Lumbar: horizontal, hatchet-shaped, 25–30 mm tall.
- **Transverse processes**:
  - Cervical: short and pierced by the **transverse foramen** (at x ≈ ±14–16 mm from C6 to C1), through which the vertebral artery runs.
  - Thoracic: they carry the rib-tubercle facets and angle backward.
  - Lumbar: long, thin and flat (L3 longest).
- **Facet joints**: cervical facets are inclined ~45° (tiles on a roof), thoracic ones are nearly coronal, lumbar ones nearly sagittal. This changes how the spine dislocates in a fall.
- **Discs**: the **annulus** is concentric fibrous lamellae, white. The **nucleus pulposus** is a gel centre occupying ~40 % of the disc area, set slightly posterior. Discs make up ≈ 20–25 % of the presacral spine's length.

### 4.2 Curvature summary (standing)

| Parameter | This model | Normal range | Unit | Source |
|---|---|---|---|---|
| Cervical lordosis (C2–C7 Cobb) | ~30 | 15–40 | deg | [B13] [K] (M) |
| Thoracic kyphosis (T4–T12 Cobb) | ~36 | 20–50 (mean ~35–40) | deg | [B13] (H) |
| Lumbar lordosis (L1–S1 Cobb) | ~60 | 40–70 | deg | [B13] [B14] (H) |
| Sacral slope | 40 | 30–50 | deg | [B14] (H) |
| Pelvic tilt | 13 | 5–25 | deg | [B14] (H) |
| Pelvic incidence (= sacral slope + pelvic tilt) | 53 | 40–65 (mean ~52) | deg | [B14] (H) |
| Sagittal vertical axis (C7 centre ahead of the posterosuperior corner of S1) | +1.7 | −2 to +5 | cm | [B13] [E] (M) |
| Presacral column length along the curve, C1 to the S1 top | ~63 | 60–66 | cm | [E] (M) |
| Total vertebral column length including sacrum and coccyx | ~72 | 70–75 (male) | cm | [K] (H) |

### 4.3 Sacrum and coccyx

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Sacrum: 5 fused vertebrae; chord length promontory → apex | 10.5 (10–11.5) | cm | Male sacrum is longer and more curved than the female | [K] (H) |
| Width at the base (across the alae) | 11 (10–12) | cm | | [K] (M) |
| S1 body width × depth | 50 × 30 | mm | | [B12] (M) |
| Thickness at S1–S2 (anterior surface → median sacral crest) | 5–6 | cm | | [K] (M) |
| Promontory (anterior top edge of S1) | (0, −0.006, 1.017) | m | | [E] (M) |
| S1 endplate centre | (0, +0.006, 1.027) | m | Endplate tilted 40° (sacral slope) | [E] (M) |
| Mid-sacrum (S3), anterior surface | (0, +0.038, 0.978) | m | Concave forward; sacral hollow depth 2–3 cm | [E] (L) |
| Apex (S5) | (0, +0.050, 0.932) | m | | [E] (L) |
| Sacroiliac joints (auricular surfaces), L | from (+0.045, +0.050, 1.030) to (+0.040, +0.065, 0.975) | m | Ear-shaped, ~5–6 cm tall. Faces lateral-posterior | [K] [E] (M) |
| Coccyx: 3–5 fused segments, length | 3–4 | cm | Curves forward | [K] (H) |
| Coccyx tip | (0, +0.040, 0.905) | m | ~9.5 cm behind the lower symphysis (pelvic outlet AP) | [K] [E] (M) |
| Dural sac ends | S2, ≈ (0, +0.035, 0.995) | m | | [K] (H) |

### 4.4 Simulation parameters: spine

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `vertebra_table` | §4.1 | m, mm | 25 rows (C1–S1). Loop over them to generate the bodies, discs and posterior elements | [B10–B12] [E] (M) |
| `disc_height_cervical / thoracic / lumbar` | 5 / 4.5–8 / 10–12 | mm | L4/5 largest | [B33] (M) |
| `vertebral_body_cortical_shell` | 0.3–0.5 | mm | The body is essentially trabecular; the endplate is 0.5–1 mm | [K] (M) |
| `vertebral_body_trabecular_density_apparent` | 0.15–0.30 | g/cm³ | Mineral only. With marrow, ≈ 1.1 g/cm³ | [K] (M) |
| `lamina_thickness_cervical / lumbar` | 5–7 / 8–12 | mm | | [K] (M) |
| `pedicle_width_T5 / L5` | 4.5 / 15 | mm | | [B11] [B12] (M) |
| `transverse_foramen_x` (vertebral artery, C6–C1) | ±0.014–0.016 (C1 loop ±0.028) | m | | [K] (M) |
| `curvatures` | §4.2 | deg | | [B13] [B14] (H) |
| `spinous_tip_offset_thoracic` | 1 level caudal (T5–T8) | levels | Surface T7 spinous = T8 body height | [K] (H) |

### 4.5 Visual/behavioural checklist: spine

- **The spine is not in the middle of the body.** It lies in the **back third** of the trunk: vertebral body centres sit 5–7 cm in front of the back skin in the thorax and 9–10 cm in the lumbar region, while the front of the abdomen is 10–12 cm further forward still. A front-to-back torso wound meets the heart, liver or aorta long before bone.
- In the lumbar region the **aorta and IVC lie directly on the front of the vertebral bodies** (§10.4). A bullet that clips the front of L1–L4 is also a great-vessel hit.
- From behind, only the **spinous tips** are subcutaneous (8–12 mm of tissue in the thorax). Everything else is covered by 3–6 cm of erector spinae.
- The **C7 bump** is the first prominent midline knob at the base of the neck. T1 is just below and nearly as prominent.
- **Cut bone colour**: vertebral bodies are **dark red spongy bone**, full of red marrow (#B5524A) inside a paper-thin shell. Discs show a **white annulus** (#E3E0D6) around a **glistening translucent nucleus** (#D8DDD2).
- **Sound**: vertebral bodies crush with a muffled crunch, not a crack. Only the dense posterior elements (laminae, spinous processes) snap.

### 4.6 Fitting note: the cervicale conflict

- Standing anthropometric surveys put the C7 spinous tip ~24–25 cm below the vertex (≈ 1.51–1.53 m for this stature) `[B1] [B35] [B36] (M)`.
- Stacking the skeleton down from the skull base gives ≈ 1.49 m, using the skull base 14–15 cm below the vertex plus C2–C7 body and disc heights `[B10] [B33] [B38]`.
- I used **1.500** and kept the vertebral stack. The other trunk landmarks match their standard vertebral levels at this compromise: jugular notch at T2/T3, sternal angle at T4/T5, xiphisternum at T9, subcostal plane at L3 and iliac crests at L4/L5 `[B32]`.
- If the neck looks too long from behind, thin the cervical discs from 5 to 4 mm. That raises C7 by ~5 mm without moving anything else.

---

## 5. Thoracic cage: sternum, ribs, costal cartilages

### 5.1 Sternum

The sternum is inclined **~20° from vertical**, with its lower end forward. Unit vector down its front surface: (0, −0.342, −0.940) `[K] [E] (M)`.

| Part | Top point (anterior surface) | Bottom point | Length (cm) | Width (cm) | Thickness (cm) | Notes | Source |
|---|---|---|---|---|---|---|---|
| Manubrium | jugular notch (0, −0.047, 1.453) | sternal angle (0, −0.064, 1.406) | 5.0 (4.5–5.5) | 5.5 at the clavicular notches → 3 at the bottom | 1.5 | Clavicles and 1st ribs attach to its upper lateral corners | [K] (M) |
| Body (gladiolus) | sternal angle | xiphisternal joint (0, −0.100, 1.307) | 10.5 (9.5–11.5) | 2.5 → 3.5 (at the 4th–5th costal cartilages) → 2.5 | 1.0–1.2 | Costal notches for cartilages 2–7 | [K] (M) |
| Xiphoid | xiphisternal joint | tip (0, −0.094, 1.273) | 3.5 (2–5) | 1.5–2 | 0.3–0.6 | Cartilaginous in youth; ossifies from the 40s; may be bifid | [K] (M) |
| **Total** | | | **17–19** | | | Males ~2 cm longer than females | [K] (H) |

- Sternal cortex is ~1 mm thick. The interior is red-marrow trabecular bone, so the **sternum bleeds from its marrow when split** `[K] (H)`.
- **Soft tissue in front of the sternum** is only 5–12 mm (skin plus fat; the pectorals attach beside it, §12). **The heart (right ventricle) lies directly behind the lower body of the sternum**, 2.5–3.5 cm from the skin `[E] (M)`.

### 5.2 Rib table (left side; negate x for the right)

- **Head** is where the rib articulates with the spine. For ribs 2–9 it sits at the disc above its own vertebra (z ≈ vertebra centre + 8 mm).
- **Lateral** is the most lateral point, near the mid-axillary line. **CCJ** is the costochondral junction, where bone becomes cartilage. **Cartilage end** is where the cartilage meets the sternum or the cartilage above.
- **Arc** is the bony length along the curve. **Cartilage** is the costal-cartilage length.
- Values are fitted `[E]` to classical surface anatomy `[K] [B32]` and to adult rib morphometry `[B39]` (M).

| Rib | Type | Head (x, y, z) | Posterior angle (x, y, z) | Lateral (x, y, z) | CCJ (x, y, z) | Cartilage end (x, y, z) | Arc (mm) | Cartilage (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | true | (+0.018, +0.030, 1.481) | (+0.035, +0.050, 1.478) | (+0.055, −0.005, 1.462) | (+0.035, −0.030, 1.440) | manubrium (+0.020, −0.042, 1.440) | 80 | 25 |
| 2 | true | (+0.020, +0.038, 1.469) | (+0.045, +0.075, 1.462) | (+0.085, +0.015, 1.440) | (+0.045, −0.052, 1.405) | **sternal angle** (+0.016, −0.062, 1.405) | 150 | 30 |
| 3 | true | (+0.020, +0.046, 1.449) | (+0.052, +0.085, 1.440) | (+0.105, +0.022, 1.414) | (+0.058, −0.066, 1.372) | sternum (+0.015, −0.071, 1.380) | 195 | 35 |
| 4 | true | (+0.020, +0.052, 1.428) | (+0.056, +0.090, 1.418) | (+0.118, +0.025, 1.388) | (+0.070, −0.075, 1.340) | sternum (+0.016, −0.079, 1.355) | 225 | 45 |
| 5 | true | (+0.021, +0.056, 1.406) | (+0.058, +0.092, 1.395) | (+0.127, +0.025, 1.362) | (+0.082, −0.080, 1.308) | sternum (+0.017, −0.086, 1.332) | 245 | 55 |
| 6 | true | (+0.021, +0.059, 1.384) | (+0.060, +0.092, 1.372) | (+0.133, +0.022, 1.336) | (+0.092, −0.080, 1.275) | sternum (+0.015, −0.094, 1.312) | 260 | 75 |
| 7 | true | (+0.022, +0.059, 1.361) | (+0.062, +0.090, 1.348) | (+0.137, +0.018, 1.308) | (+0.100, −0.075, 1.240) | xiphisternal (+0.010, −0.098, 1.302) | 270 | 110 |
| 8 | false | (+0.022, +0.056, 1.337) | (+0.063, +0.088, 1.323) | (+0.139, +0.015, 1.280) | (+0.110, −0.062, 1.205) | joins 7th cartilage (+0.060, −0.090, 1.245) | 270 | 90 |
| 9 | false | (+0.023, +0.050, 1.313) | (+0.064, +0.084, 1.298) | (+0.139, +0.015, 1.250) | (+0.118, −0.048, 1.175) | joins 8th cartilage (+0.085, −0.078, 1.200) | 260 | 70 |
| 10 | false | (+0.024, +0.041, 1.280) | (+0.064, +0.078, 1.268) | (+0.136, +0.018, 1.212) | (+0.125, −0.030, 1.150) | joins 9th cartilage (+0.100, −0.065, 1.150); lowest point of the margin (+0.112, −0.050, 1.125) | 240 | 55 |
| 11 | floating | (+0.025, +0.030, 1.254) | (+0.062, +0.070, 1.243) | (+0.130, +0.030, 1.185) | free tip (+0.125, +0.010, 1.160) | cartilage cap only | 190 | 10 |
| 12 | floating | (+0.025, +0.018, 1.227) | (+0.055, +0.058, 1.218) | — | free tip (+0.085, +0.060, 1.180) | cartilage cap only | 120 (50–180) | 5 |

- **True ribs (1–7)** reach the sternum through their own costal cartilages. **False ribs (8–10)** join the cartilage above to form the **costal margin**. **Floating ribs (11–12)** end free in the posterolateral abdominal wall `[K] (H)`.
- **Rule of thumb for ribs 3–10** `[K] (H)`: the front end of a rib is **2.5–3 vertebral levels (6–8 cm) lower** than its head. Costal cartilages 3–7 then **rise** medially to reach the sternum, with the 7th cartilage rising ~6 cm. So a horizontal cut through the front of the chest crosses several ribs.
- **Build each rib** as a Catmull–Rom spline through head → angle → lateral → CCJ, then sweep a rounded-rectangle section along it `[E]`:
  - Mid-shaft height (up–down) 12–15 mm and thickness 5–7 mm.
  - Rib 1: flat, 25–30 mm wide and 5 mm thick. Ribs 11–12: 8–10 mm high.
  - Put a **costal groove** on the lower inner edge; the intercostal vein, artery and nerve run in it, top to bottom.
  - Sweep the cartilages the same way at 10–15 × 6–10 mm.
- **Rib cortex**: 0.6–1.8 mm, mean ~1 mm, around trabecular bone `[B40] (M)`.
- **Intercostal spaces**: 15–25 mm at the front (2nd and 3rd widest), 12–18 mm at the side and 8–12 mm at the back. Each holds three thin muscle layers, 5–7 mm in total `[K] (M)`.

### 5.3 Cage dimensions (bone)

| Measure | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Superior aperture (thoracic inlet), transverse × AP | 10–11 × 5–6 | cm | Kidney-shaped. Plane slopes forward-down ~45° (T1 at the back → jugular notch at the front) | [K] (H) |
| Transverse outer width at ribs 4 / 6 / 8–9 / 10 | 23.6 / 26.6 / **27.8** / 27.2 | cm | 2 × "lateral" x in §5.2. Maximum at ribs 8–9 | [E] [B39] (M) |
| AP outer depth at T7 (sternum front → rib angles at the back) | 18–19 | cm | | [E] (M) |
| Internal AP, sternum back → vertebral body front, at T8 | 11–12 | cm | The heart occupies most of this space | [K] [E] (M) |
| Infrasternal (subcostal) angle | 70–90 (male ~75) | deg | Apex at the xiphisternal joint | [K] (M) |
| Posterior cage height (T1 → T12) | 26 | cm (vertical) | | [E] |
| Front cage height (jugular notch → lowest costal margin) | 33 | cm (vertical) | | [E] |
| Cage mass (ribs + sternum + cartilages, fresh) | ~1.0–1.3 | kg | | [K] (L) |

### 5.4 Simulation parameters: thoracic cage

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `sternum_incline_from_vertical` | 20 (15–25) | deg | Lower end forward | [K] (M) |
| `sternum_len_manubrium / body / xiphoid` | 50 / 105 / 35 | mm | | [K] (M) |
| `sternum_thickness_manubrium / body` | 15 / 11 | mm | | [K] (M) |
| `rib_table` | §5.2 | m | 12 splines per side | [E] (M) |
| `rib_section_h × t` | 13 × 6 (rib 1: 27 × 5) | mm | | [B39] (M) |
| `rib_cortex` | 1.0 (0.6–1.8) | mm | | [B40] (M) |
| `costal_cartilage_section` | 12 × 8 | mm | Hyaline; uncalcified at 30 y | [K] (M) |
| `intercostal_space_ant / lat / post` | 20 / 15 / 10 | mm | | [K] (M) |
| `cage_max_width_bone` | 0.278 | m | Ribs 8–9 | [E] (M) |
| `infrasternal_angle` | 75 | deg | | [K] (M) |

### 5.5 Visual/behavioural checklist: thoracic cage

- **Cut or broken ribs**: a thin ivory rim (#E9DFCC) around dark red cancellous bone (#B5524A). Ends are sharp and splintery. Rib fractures make a **dull snap**, quieter than a long bone.
- **Costal cartilage** is **glossy, translucent bluish-white** (#CBD5D8). It is rubbery: a knife can cut through it (autopsy rib cutters work here), blunt force bends it, and it rarely shatters at 30 y.
- **The lower ribs flex**. The floating ribs 11–12 and the costal margin move visibly with breathing and deform before breaking.
- **Flail segment**: when ≥ 3 adjacent ribs are each broken in two places, that patch of chest **moves in when the rest expands** (paradoxical motion) `[K] (H)`.
- The **sternum** is thick and flat. A hammer produces a transverse fracture, most often at the body or the manubriosternal joint, with a deep bruise over it.

---

## 6. Shoulder girdle and upper limb (A-pose, left side)

**Arm direction in A-pose** `[E]`: d = (sin 30°, 0, −cos 30°) = **(0.500, 0, −0.866)**.
- Humerus, radius and ulna run along d.
- The elbow's flexion axis is perpendicular to d in the coronal plane: (0.866, 0, 0.500).
- The **front of the arm faces −Y**. With the forearm in neutral rotation, the **radius is on the −Y (thumb) side**.

### 6.1 Clavicle

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Length (straight, sternal → acromial end) | 14.8 (13.5–16) | cm | | [K] (H) |
| Shape | S-curve: medial ⅔ convex forward, lateral ⅓ concave forward | — | | [K] (H) |
| Waypoints (left) | sternal end (+0.025, −0.040, 1.450) → front-bulge point (+0.070, −0.050, 1.452) → (+0.125, −0.020, 1.462) → acromial end (+0.165, +0.010, 1.462) | m | Rises ~1 cm laterally and sweeps ~20° backward | [E] (M) |
| Cross-section | sternal end 25 × 20 (bulbous); mid-shaft 13 × 10 (round-oval); acromial end 25 × 10 (flat) | mm | | [K] (M) |
| Cortex (mid-shaft) | 2–3 | mm | | [K] (M) |
| What lies under the middle third | subclavian artery and vein, brachial plexus, all over the 1st rib | — | Why a clavicle fracture or a stab above the clavicle bleeds badly (doc 03) | [K] (H) |

### 6.2 Scapula

| Item | Value (left) | Unit | Notes | Source |
|---|---|---|---|---|
| Height (superior → inferior angle) | 15.5 (14–17) | cm | Spans ribs 2–7 | [K] (H) |
| Breadth (spine root → glenoid) | 10.5 (9.5–11.5) | cm | | [K] (M) |
| Superior angle | (+0.080, +0.085, 1.475) | m | T2 | [K] [E] (M) |
| Root of the spine (medial border) | (+0.075, +0.095, 1.440) | m | T3 spinous level | [K] [E] (M) |
| Inferior angle | (+0.085, +0.105, 1.325) | m | T7–T8 | [K] [E] (M) |
| Glenoid centre | (+0.156, +0.022, 1.415) | m | Pear-shaped fossa 38 × 28 mm. Faces lateral and ~30° forward | [K] (M) |
| Acromion | lateral tip (+0.200, +0.015, 1.458); posterior angle (+0.180, +0.050, 1.455) | m | 45 × 25 mm, 7–9 mm thick | [K] (M) |
| Coracoid tip | (+0.135, −0.020, 1.425) | m | Palpable 2.5 cm below the clavicle's lateral third | [K] (M) |
| Scapular plane | 35–40° from the coronal plane | deg | Blade lies on the back of the ribs, under trapezius and rhomboids | [K] (H) |
| Blade thickness | 1–3 mm in the fossae (translucent); lateral border 6–10; spine 10–15; glenoid neck 15–20 | mm | | [K] (M) |

### 6.3 Humerus

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Maximum length | 33.5 (31–36) | cm | Trotter–Gleser predicts 34.9 ± 1.3 for 178 cm; the landmark fit (acromion → radiale) gives 33.5 | [B7] [B3] (M) |
| Head: diameter / centre | 48 (vertical, 45–51) / glenohumeral (+0.180, +0.020, 1.415) | mm / m | Head retroverted 20–30° | [K] (H) |
| Surgical neck | 15–20 mm below the head | mm | Common fracture site | [K] (H) |
| Mid-shaft outer diameter | 22 × 20 (ML × AP) | mm | | [K] (M) |
| **Mid-shaft cortex** | **4–6 (default 5)** | mm | Canal Ø 10–12 | [K] (M) |
| Distal epicondylar width / articular width | 63 / 42 | mm | | [K] (M) |
| Axis in A-pose | glenohumeral centre → elbow centre (+0.330, +0.020, 1.155) | m | Joint-to-joint length 0.300 | [E] |
| Radial nerve | spirals behind the mid-shaft (radial groove) | — | Mid-shaft fractures cause **wrist drop** | [K] (H) |

### 6.4 Radius and ulna

| Item | Radius | Ulna | Unit | Source |
|---|---|---|---|---|
| Maximum length | 25.5 (24–27) | 27.5 (26–29) | cm | [B7] [K] (M) |
| Proximal end | head: 22-mm disc, 1 cm below the elbow axis | olecranon 2.5 cm proximal to the axis (point of the elbow); coronoid process | — | [K] (H) |
| Mid-shaft diameter | 14 × 12 | 13 × 12 | mm | [K] (M) |
| **Cortex (mid-shaft)** | **2.5–3.5** | **2.5–3.5** | mm | [K] (M) |
| Distal end | 33 wide × 20 AP; styloid ~1 cm beyond the ulnar head | head 16–18 mm; small styloid | mm | [K] (M) |
| Position in A-pose | on the −Y (anterolateral) side of the forearm axis, at y ≈ +0.010 | on the +Y (posteromedial) side, at y ≈ +0.030; subcutaneous along its whole back border | m | [K] [E] (M) |

- The **forearm axis** runs from the elbow centre (+0.330, +0.020, 1.155) to the wrist centre (+0.455, +0.020, 0.938), 0.250 m `[E]`.
- The radius and ulna are ~1.5–2 cm apart at mid-forearm, joined by the **interosseous membrane** `[K] (H)`.

### 6.5 Hand (simplified, left)

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Carpal block (8 carpals as one) | 30 (proximal–distal) × 55 (radial–ulnar) × 20 (dorsal–palmar) | mm | Centre ~15 mm distal to the wrist centre: (+0.463, +0.020, 0.925) | [K] (M) |
| Metacarpal lengths MC1–MC5 | 46 / 69 / 66 / 58 / 54 | mm | Shafts 7–10 mm Ø; cortex 1–1.5 mm | [K] (M) |
| Proximal phalanges (thumb, index, middle, ring, little) | 32 / 41 / 46 / 43 / 34 | mm | | [K] (M) |
| Middle phalanges (index → little) | 24 / 28 / 27 / 20 | mm | Thumb has none | [K] (M) |
| Distal phalanges (thumb, index → little) | 23 / 18 / 19 / 19 / 17 | mm | | [K] (M) |
| Hand length / breadth | 19.2 / 8.7 | cm | 0.108 H | [B1] [B3] (H) |
| Rest pose in A-pose | palm faces the thigh (+X side of the hand faces −X); MCP 15–20°, PIP 20–30°, DIP 10° of flexion; thumb 30° abducted | deg | Relaxed hand | [K] [G] |

### 6.6 Simulation parameters: upper limb

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `a_pose_abduction` | 30 | deg | From vertical, in the coronal plane | brief |
| `gh_centre_L` | (+0.180, +0.020, 1.415) | m | | [E] (M) |
| `len_gh_to_elbow / elbow_to_wrist / wrist_to_mcp3 / wrist_to_tip3` | 0.300 / 0.250 / 0.095 / 0.185 | m | Joint-to-joint | [B3] [E] (M) |
| `humerus_len / radius_len / ulna_len / clavicle_len` | 0.335 / 0.255 / 0.275 / 0.148 | m | Bone maximum lengths | [B7] [K] (M) |
| `humerus_head_d / midshaft_d / cortex` | 48 / 21 / 5 | mm | | [K] (M) |
| `radius_ulna_midshaft_d / cortex` | 13–14 / 3 | mm | | [K] (M) |
| `clavicle_midshaft_d / cortex` | 12 / 2.5 | mm | | [K] (M) |
| `scapula_blade_thickness` | 1–3 | mm | Thin: a bullet makes a clean hole with radiating cracks | [K] (M) |
| `carrying_angle` (anatomical position only) | 10–13 | deg | Zero in neutral-rotation A-pose | [K] (H) |

### 6.7 Visual/behavioural checklist: upper limb

- **The clavicle is S-shaped and sits directly under the skin.** Its whole length is visible and palpable. A fracture tents the skin, and the lateral fragment drops with the arm's weight.
- **The olecranon and the whole back border of the ulna are subcutaneous.** Defensive blows (arms raised) break the ulna ("nightstick fracture").
- The **humeral head** sits under ~2–3 cm of deltoid, below and in front of the acromion. When the shoulder dislocates (usually forward and down), the deltoid contour goes square and flat.
- **Long-bone fractures**: humerus, radius and ulna break with a sharp crack. Ends are jagged and the marrow cavity shows **yellow fatty marrow** (#E4C36A) in the shafts of an adult, with red marrow only at the ends.
- **Hands and feet** have thin cortex and many small bones. Blunt injury crushes them into a grating mass rather than making one clean break.

---

## 7. Pelvis and lower limb (left side)

### 7.1 Pelvis (hip bones: ilium, ischium, pubis, fused at the acetabulum)

**Hip-centre fit** `[B9] (M)`:
- Bell's method places the hip-joint centre relative to the midpoint of the two ASIS, as fractions of the inter-ASIS width W (0.245 m): **30 % below, 19 % behind and 36 % lateral**.
- So HJC = (±0.36 W, ASIS_y + 0.19 W, ASIS_z − 0.30 W) = **(±0.087, −0.015, 0.935)**.

| Item | Value (left) | Unit | Notes | Source |
|---|---|---|---|---|
| Iliac crest, highest point | (+0.140, +0.025, 1.070) | m | L4/L5 (supracristal plane) | [K] (M) |
| Iliac tubercle (widest crest point) | (+0.143, −0.030, 1.055) | m | Bicristal breadth 28.5 (27–30) cm | [K] (M) |
| ASIS | (+0.122, −0.062, 1.009) | m | Inter-ASIS 24.5 (23–26) cm | [K] [B9] (M) |
| AIIS | (+0.105, −0.055, 0.975) | m | | [K] (L) |
| PSIS | (+0.045, +0.090, 1.010) | m | S2 | [K] (M) |
| Acetabulum centre = HJC | (+0.087, −0.015, 0.935) | m | Cup Ø ~55 mm; opens lateral, forward (anteversion 15–20°) and down (inclination ~45°) | [K] [B9] (M) |
| Pubic tubercle | (+0.022, −0.068, 0.930) | m | Inguinal ligament runs ASIS → pubic tubercle | [K] (M) |
| Pubic symphysis | upper anterior (0, −0.068, 0.928); centre (0, −0.062, 0.905); lower (0, −0.055, 0.883) | m | Height 45 mm; fibrocartilage disc ~4 mm; bone ~15 mm thick AP | [K] [E] (M) |
| Ischial spine | (+0.045, +0.035, 0.915) | m | | [K] (L) |
| Ischial tuberosity (lowest point) | (+0.055, +0.020, 0.858) | m | The sitting bones | [K] [E] (M) |
| Obturator foramen centre | (+0.050, −0.040, 0.895) | m | 5 × 3.5 cm oval, closed by membrane | [K] (L) |
| Pelvic inlet, AP (true conjugate) × transverse | 10.5 × 12.5 (male, heart-shaped) | cm | Inlet plane ~60° to horizontal when standing | [K] (H) |
| Pelvic outlet, AP (lower symphysis → coccyx tip) × bi-ischial | 9.5 × 9 | cm | | [K] (M) |
| Subpubic angle | 50–60 (male) | deg | Female 80–90 | [K] (H) |
| Pelvic height (crest top → ischial tuberosity) | 21 | cm | | [K] [E] (M) |
| **Iliac wing thickness** | 2–4 mm in the thin centre of the iliac fossa; 10–15 mm at the crest; > 30 mm around the acetabulum and sacroiliac joint | mm | Cortex 1–2 mm around trabecular bone | [K] (M) |
| Pelvis mass (both hip bones + sacrum, fresh) | ~1.0–1.3 | kg | | [K] (L) |

### 7.2 Femur

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Maximum length | **47.0** (44–50) | cm | The landmark fit (hip centre 0.935 → joint line 0.487) gives 46.5–47. Trotter–Gleser (white males) predicts ~49 ± 1.4. Stature/femur ≈ 3.79 | [B7] [E] (M) |
| Head: diameter / centre | **49** (46–52) / HJC (+0.087, −0.015, 0.935) | mm / m | | [K] (H) |
| Neck: length / section (SI × AP) / neck–shaft angle / anteversion | 35 / 32 × 26 / **127°** (120–135) / **12°** (10–15) | mm, deg | | [K] (H) |
| Greater trochanter: tip / lateral surface | tip (+0.145, 0.000, 0.940); lateral (+0.158, 0.000, 0.930) | m | Tip level with the head centre and the upper symphysis | [K] (M) |
| Lesser trochanter | (+0.075, +0.010, 0.880) | m | Posteromedial, 5–6 cm below the head centre | [K] (L) |
| Shaft (anatomical axis) | piriform fossa (+0.120, +0.005, 0.940) → intercondylar notch (+0.092, +0.015, 0.500) | m | 5–7° from the mechanical axis. Anterior bow radius ~1.2–1.5 m | [K] [E] (M) |
| Mid-shaft outer diameter | 29 (AP) × 27 (ML) | mm | | [K] (M) |
| **Mid-shaft cortex** | **6–8 (default 7)**; up to 9–10 posteriorly (linea aspera) | mm | Medullary canal 12–14 mm (isthmus 11–13) | [K] (M) |
| Distal: bicondylar width / condylar AP depth | 84 (80–88) / 60–65 | mm | | [K] (M) |
| Knee joint centre (epicondylar axis) | (+0.092, +0.020, 0.505) | m | Joint line (tibial plateau) at 0.487 | [E] (M) |
| Femoral artery path | groin (mid-inguinal point) (+0.065, −0.068, 0.955) → adductor hiatus (+0.080, +0.030, 0.620) → popliteal fossa (+0.092, +0.055, 0.510) | m | Medial, then posterior. See doc 03 | [K] [E] (M) |

### 7.3 Patella, tibia, fibula

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Patella size | 53 tall × 51 wide × 25 thick | mm | Thin cortex over trabecular bone; articular cartilage up to 5–7 mm (the thickest in the body) | [K] (M) |
| Patella centre (knee straight) | (+0.090, −0.035, 0.522) | m | Lower pole ~1 cm above the joint line | [K] (M) |
| Patellar tendon | 45–50 long × 25–30 wide × 4–6 thick; to the tibial tuberosity (+0.090, −0.025, 0.447) | mm / m | | [K] (M) |
| Tibia maximum length | **41** (38–43) | cm | Including the medial malleolus. (Trotter's original tibia measure excluded the malleolus, so her regression gives a shorter 39.4) | [B7] [E] (M) |
| Tibial plateau | width 78 × AP 50; z 0.487 | mm / m | | [K] (M) |
| Tibial mid-shaft | triangular, 32 (AP) × 23 (ML) | mm | **The anteromedial face is subcutaneous** (§12) | [K] (M) |
| **Tibial cortex (mid-shaft)** | **5–7** (anterior crest up to 8) | mm | Canal 10–12 mm | [K] (M) |
| Tibial plafond (distal joint surface) | z 0.090; width 45 mm | m / mm | | [E] (M) |
| Medial malleolus tip | (+0.065, +0.045, 0.068) | m | | [K] (M) |
| Fibula length / mid-shaft Ø / cortex | 39.5 cm / 14–16 mm / 2.5–3.5 mm | | Non-weight-bearing strut | [K] (M) |
| Fibular head | (+0.130, +0.035, 0.465) | m | **Common peroneal nerve** wraps its neck, just below: foot drop if cut | [K] (H) |
| Lateral malleolus tip | (+0.132, +0.060, 0.055) | m | | [K] (H) |
| Ankle joint centre | (+0.095, +0.050, 0.075) | m | Axis passes just below both malleolar tips, tilted ~8° (lateral end lower) | [K] (M) |

### 7.4 Foot (simplified, left, 7° toe-out)

**Foot axis direction (heel → 2nd toe)**: (sin 7°, −cos 7°, 0) = **(0.122, −0.993, 0)** `[E]`.

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Talus | 55 long × 40 wide × 32 tall; dome top at z 0.090 under the plafond; head points forward-medially | mm | Carries the whole body weight; no muscle attachments | [K] (M) |
| Calcaneus | 80 long × 42 wide × 45 tall; posterior tuber at (+0.095, +0.100, 0.035) | mm / m | Heel pad under it: 15–20 mm thick | [K] (M) |
| Midfoot block (navicular, cuboid, 3 cuneiforms) | 50 × 70 × 30; centre (+0.100, −0.005, 0.045) | mm / m | Navicular tuberosity 3.5–4.5 cm above the floor (medial arch) | [K] (M) |
| Metatarsal lengths MT1–MT5 | 64 / 75 / 70 / 68 / 69 | mm | MT1 thick (16–20 mm Ø); others 8–10 mm | [K] (M) |
| Phalanges | hallux: proximal 30, distal 23; toes 2–5: proximal 26–30, middle 10–12, distal 8–10 | mm | | [K] (M) |
| Foot length / breadth | 26.8 / 10.2 | cm | | [B1] (H) |
| Heel / 1st MTP / 5th MTP / toe tip | see §1.3 (#62–65) | m | | [E] |

### 7.5 Simulation parameters: pelvis and lower limb

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hjc_L` | (+0.087, −0.015, 0.935) | m | Bell's method | [B9] (M) |
| `knee_centre_L / ankle_centre_L` | (+0.092, +0.020, 0.505) / (+0.095, +0.050, 0.075) | m | | [E] (M) |
| `len_thigh / len_shank` (joint to joint) | 0.431 / 0.431 | m | | [E] (M) |
| `femur_len / tibia_len / fibula_len` | 0.470 / 0.410 / 0.395 | m | | [B7] [E] (M) |
| `femur_head_d / neck_shaft_angle / anteversion` | 49 mm / 127° / 12° | | | [K] (H) |
| `femur_midshaft_d / cortex / canal` | 28 / 7 / 13 | mm | Thickest cortex in the body | [K] (M) |
| `tibia_midshaft_ap_ml / cortex` | 32 × 23 / 6 | mm | | [K] (M) |
| `patella_hwt` | 53 / 51 / 25 | mm | | [K] (M) |
| `pelvis_bicristal / inter_asis / bitrochanteric_bone` | 0.285 / 0.245 / 0.316 | m | | [K] (M) |
| `iliac_wing_thin_centre` | 2–4 | mm | Bullets perforate it cleanly | [K] (M) |
| `toe_out_angle` | 7 (5–15) | deg | | [K] [G] |

### 7.6 Visual/behavioural checklist: pelvis and lower limb

- **The shin has no padding.** The anteromedial tibia is 3–6 mm under the skin along its whole length. A hammer blow splits the skin over the bone (a "split laceration" with bruised edges) and often cracks the bone. Little blood welling up, but **white bone visible in the wound floor**.
- **The femur is deep.** Mid-thigh, it lies under 5–7 cm of quadriceps at the front and 6–8 cm of hamstrings behind. A femoral shaft fracture shortens the thigh by 2–5 cm, rotates the foot outward and **swells the thigh visibly**, because 1–1.5 L of blood can hide inside it (doc 03).
- **Hip-fracture posture**: a neck-of-femur fracture leaves the leg **shortened and externally rotated**, with the foot turned out ~45–90°.
- The **iliac crests, ASIS, pubic tubercles, greater trochanters, patellae, malleoli and heels** are the palpable, visible bone points of the lower body. Keep them readable in the skin mesh.
- **Sound**: femur and tibia fractures are the loudest bone sounds on the body, a sharp crack. Pelvic ring fractures are dull and deep.

---

## 8. Bone summary: every bone to model, sections, cortex, material, colour

### 8.1 Bone list (per side where paired): what to build and at what detail

| Bone | Count | Build as | Key size | Cortex (mm) | Interior | Source |
|---|---|---|---|---|---|---|
| Cranium (existing head) | 1 | existing mesh | §3.1 | tables 1.5–2 each; total vault 5–10 | diploë | [D01:S31] |
| Mandible | 1 | existing mesh | §3.1 | 2–5 | trabecular | [K] (M) |
| Hyoid | 1 | small U-shaped bone | 35 mm wide | thin | — | [K] (M) |
| Cervical vertebrae C1–C7 | 7 | procedural (§4.1) | body ~16 × 16 × 14 mm | shell 0.3–0.5 | red marrow | [B10] (M) |
| Thoracic vertebrae T1–T12 | 12 | procedural | body 26–42 wide | shell 0.3–0.5 | red marrow | [B11] (M) |
| Lumbar vertebrae L1–L5 | 5 | procedural | body 43–52 wide | shell 0.4–0.6 | red marrow | [B12] (M) |
| Intervertebral discs | 23 (C2/3 → L5/S1) | procedural elliptic slabs | 5–12 mm tall | annulus / nucleus | — | [B33] (M) |
| Sacrum | 1 | sculpted or procedural wedge | 10.5 × 11 cm | 0.5–1 | red marrow | [K] (M) |
| Coccyx | 1 | 3–4 tapered beads | 3–4 cm | — | — | [K] (M) |
| Ribs 1–12 | 12 × 2 | spline sweep (§5.2) | 13 × 6 mm section | ~1 | red marrow | [B39] [B40] (M) |
| Costal cartilages | 10 × 2 | spline sweep | 12 × 8 mm | — (hyaline cartilage) | — | [K] (M) |
| Sternum (manubrium, body, xiphoid) | 3 parts | extruded plates | 17–19 cm total | ~1 | red marrow | [K] (M) |
| Clavicle | 2 | S-spline sweep | 14.8 cm, Ø 12 | 2–3 | — | [K] (M) |
| Scapula | 2 | sculpted plate | 15.5 × 10.5 cm | blade 1–3 total | thin | [K] (M) |
| Humerus | 2 | lathe + sculpt ends | 33.5 cm, Ø 21 | 4–6 | yellow marrow in the shaft | [K] (M) |
| Radius | 2 | lathe | 25.5 cm, Ø 13 | 2.5–3.5 | yellow in the shaft | [K] (M) |
| Ulna | 2 | lathe | 27.5 cm, Ø 13 | 2.5–3.5 | yellow in the shaft | [K] (M) |
| Carpals | 1 block × 2 | rounded box | 30 × 55 × 20 mm | thin | trabecular | [K] [G] |
| Metacarpals | 5 × 2 | lathe | 46–69 mm | 1–1.5 | | [K] (M) |
| Hand phalanges | 14 × 2 | lathe | 17–46 mm | ~1 | | [K] (M) |
| Hip bone (ilium, ischium, pubis) | 2 | sculpted | §7.1 | 1–2 | trabecular; red marrow | [K] (M) |
| Femur | 2 | lathe + sculpt ends | 47 cm, Ø 28 | 6–8 | yellow in the shaft; red in the neck/head | [K] (M) |
| Patella | 2 | rounded triangle | 53 × 51 × 25 mm | thin | trabecular | [K] (M) |
| Tibia | 2 | lathe (triangular section) | 41 cm | 5–7 | yellow in the shaft | [K] (M) |
| Fibula | 2 | lathe | 39.5 cm, Ø 15 | 2.5–3.5 | | [K] (M) |
| Talus, calcaneus | 2 × 2 | sculpted blocks | §7.4 | ~1 | trabecular | [K] (M) |
| Midfoot tarsals (navicular, cuboid, 3 cuneiforms) | 1 block × 2 | block | 50 × 70 × 30 mm | thin | | [K] [G] |
| Metatarsals | 5 × 2 | lathe | 64–75 mm | 1.5–2.5 (MT1 thicker) | | [K] (M) |
| Foot phalanges | 14 × 2 | lathe (or merged per toe) | 8–30 mm | ~1 | | [K] (M) |

- The real adult skeleton has **206 bones**. With the carpal and midfoot blocks and merged toe phalanges, this list gives ≈ 150 meshes `[K] (H)`.
- **Game budget** `[G]`:
  - **Render** the skeleton only where wounds expose it, using fracture / cut shaders on the visible bone. Keep a single merged mesh per body region, split at the ragdoll bones.
  - **Hit-test** against primitive proxies (§15), not against the bone meshes.

### 8.2 Material properties (for hit resolution and effects)

| Property | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Cortical bone density | 1.85–1.95 (use 1.9) | g/cm³ | | [K] (H) |
| Trabecular bone apparent density (mineralised tissue only) | 0.15–0.40 (vertebra ~0.2, femoral head ~0.4) | g/cm³ | Marrow-filled: ≈ 1.0–1.1 | [K] (M) |
| Cortical bone longitudinal Young's modulus | 17–20 | GPa | Transverse ~10–12 | [K] (H) |
| Cortical bone ultimate stress: tension / compression / shear | ~130 / ~190 / ~70 | MPa | Longitudinal. Bone is weakest in shear and tension | [K] (H) |
| Trabecular (vertebral) compressive strength | 1–7 | MPa | Hence vertebral crush (wedge) fractures | [K] (M) |
| Hyaline cartilage (costal) density | ~1.1 | g/cm³ | Rubbery; cuts rather than shatters | [K] (M) |
| Whole fresh skeleton mass (75 kg male) | ~10.5 (incl. marrow and cartilage) | kg | ~14 % of body mass | [B43] (H) |
| Red marrow volume (adult, axial skeleton) | ~1.2 L | L | Sternum, vertebrae, ribs, pelvis, proximal femur and humerus | [B43] (M) |

### 8.3 Bone and joint tissue colours (sRGB, D65, fresh, living or recently dead)

| Tissue | Hex | Description | Source |
|---|---|---|---|
| Cortical bone, fresh cut surface | #E9DFCC | Ivory, faintly pink | [K] [G] |
| Periosteum-covered bone surface | #E6CFC4 | Pinkish white, glossy; bleeds from pinpoints when scraped | [K] [G] |
| Trabecular bone with red marrow | #B5524A | Dark red sponge; oozes blood | [K] [G] |
| Yellow marrow (long-bone shafts) | #E4C36A | Greasy yellow fat; floats fat droplets into the wound | [K] [G] |
| Articular cartilage | #DDE3E6 | Glossy bluish-white, very smooth | [K] [G] |
| Costal cartilage | #CBD5D8 | Translucent bluish-white | [K] [G] |
| Disc annulus / nucleus | #E3E0D6 / #D8DDD2 | White lamellae / translucent gel | [K] [G] |
| Ligament / tendon | #E8E6DF | Silvery white, glistening, fibrous | [K] [G] |
| Dura mater | #D9D6CE | Tough, silver-white | [K] [G] |

### 8.4 Simulation parameters: bone material

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `bone_cortical_density` | 1.9 | g/cm³ | | [K] (H) |
| `bone_cortex_by_bone` | femur 7, tibia 6, humerus 5, radius/ulna 3, fibula 3, clavicle 2.5, rib 1, scapula blade 1–3 (total), vertebral shell 0.4, skull §3.1 | mm | Drives penetration and fracture thresholds in docs 01/02 | [K] (M) |
| `bone_marrow_type` | red: axial skeleton + proximal femur/humerus; yellow: long-bone shafts | enum | Picks the colour and bleeding of the cut surface | [K] (H) |
| `skeleton_mass_total` | 10.5 | kg | | [B43] (H) |

### 8.5 Visual/behavioural checklist: bone

- **Long bones** (femur, tibia, humerus) break into **sharp, spiral or butterfly fragments** with a bright ivory rim and a yellow-fat core. **Flat and axial bones** (ribs, sternum, pelvis, vertebrae) show a dark red spongy core that **keeps oozing blood**.
- **Gunshot through a thin flat bone** (scapula blade, iliac wing): a clean round hole with **bevelling on the exit side** and radiating cracks, as in the skull (doc 01).
- **Periosteum** peels back as a thin shiny sleeve over a fracture and bleeds from many pinpoints.
- **Fat globules** float on the blood pooling from a long-bone shaft wound.

---

## 9. Spinal cord, cauda equina and brainstem

Doc 04 covers what injury to these structures does. This section covers **where they are and how big they are**.

### 9.1 Cord overview

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Length (foramen magnum → conus tip) | 45 (42–46, male) | cm | | [K] (H) |
| Mass | ~30 | g | | [B43] (H) |
| **Conus medullaris tip** | **L1/L2 disc** (range T12 → L3; mean lower third of L1) | level | Body frame ≈ (0, +0.017, 1.180) | [B28] (H) |
| Filum terminale | ~20 cm, conus → dural sac (S2) → coccyx | cm | | [K] (H) |
| **Cauda equina** | roots L2–S5 (+ coccygeal) hanging in the thecal sac from L1/L2 to S2 | — | Lower-motor-neuron roots; float in CSF | [K] (H) |
| Dural (thecal) sac ends | S2, (0, +0.035, 0.995) | — | | [K] (H) |
| Coverings | pia (on the cord) → subarachnoid space with CSF → arachnoid → dura (0.3–1 mm) → epidural fat and veins | — | | [K] (H) |
| Subarachnoid CSF around the cord | 2–4 mm in front and behind (cervical); wider behind in the thoracic region | mm | | [K] (M) |
| Epidural fat, posterior (lumbar) | 3–6 | mm | | [K] (M) |
| Spinal nerve roots | 31 pairs: C1–C8, T1–T12, L1–L5, S1–S5, Co1 | — | C1–C7 exit **above** their vertebra; C8 below C7; T1 onward exit **below** their vertebra | [K] (H) |

### 9.2 Cord cross-section by level (transverse × AP, mm) and centreline

The cord centre is at (0, y, z) with y from the "Cord centre y" column of §4.1 and z = the vertebral body centre z. Between levels, interpolate with a spline. Cross-sections are ellipses `[B26] [B27] (M)`.

| Level | Cord size (transverse × AP, mm) | Canal (AP × transverse, mm) | Cord / canal AP | Note |
|---|---|---|---|---|
| Cervicomedullary junction (at the foramen magnum) | 11 × 9 | FM 35 × 30 | — | Point (0, +0.030, 1.627) |
| C1 | 11.5 × 8.5 | 30 × 28 | ~⅓ | Steel's rule of thirds: dens, cord, free space |
| C2 | 11.5 × 8.5 | 16 × 24 | 0.53 | |
| C3–C4 | 12.5–13 × 8 | 14–14.5 × 23–24 | 0.55 | |
| **C5–C6 (cervical enlargement, max)** | **13.5 × 7.7** | 14 × 24 | 0.55 | Brachial-plexus segments C5–T1 |
| C7 | 12 × 7.5 | 14 × 23 | 0.54 | |
| T1 | 10.5 × 7 | 14 × 19 | 0.50 | |
| T2–T9 (thinnest ~T7–T8) | 8–9 × 6.3–6.5 | 13.5–14 × 15.5–16 | 0.46 | Round canal. **Watershed blood supply around T4–T8** |
| T10 | 8.5 × 7 | 14.5 × 17 | 0.48 | |
| T11–T12 (lumbosacral enlargement) | 9.5–10 × 7.5–8 | 15–16 × 18–21 | 0.50 | Lumbar segments L1–L5 lie here |
| L1 (conus) | tapers 8 → 3 | 17 × 22 | — | Sacral segments S1–S5 and coccygeal |
| L2–S1 | cauda equina bundle, ~12–15 mm spread | 16–17 × 23–26 | — | Roots only |

- **Cord hit volume** `[G]`: a capsule chain of 26 nodes (C1 → L1) using the §4.1 cord y and z, with radii = half the transverse and AP sizes above.
- Add a separate **cauda equina** capsule chain from L1/L2 to S2 (radius 7 mm).
- Add a **canal** chain (radius = half the canal AP) so near-misses can bruise the cord through concussion (doc 04).

### 9.3 Vertebral level → cord segments (for the paralysis map)

The cord is shorter than the spine, so its segments sit above the vertebra of the same name `[K] (H)`. Rule of thumb: add **+1** in the cervical region, **+2** in the upper thoracic region and **+3** in the lower thoracic region. T11–L1 contain all the lumbar and sacral segments.

| Vertebral level of the injury | Cord segments there | Key function lost below (see doc 04) |
|---|---|---|
| Foramen magnum / C1 | C1 (+ medulla above) | Everything below. **Apnoea** (C3–C5 phrenic cut off). Upper cord only: can stay awake |
| C2 | C2–C3 | Apnoea; quadriplegia |
| C3 | C3–C4 | Apnoea or severe hypoventilation (phrenic C3–C5) |
| C4 | C4–C5 | Diaphragm partly spared at best; quadriplegia |
| C5 | C5–C6 | Shoulder shrug and some elbow flexion remain; no wrist or hand function |
| C6 | C6–C7 | Wrist extension kept; no triceps or hand |
| C7 | C7–C8 | Triceps partial; no hand intrinsics |
| T1 | C8–T1 (T2) | Hand intrinsics lost; **Horner's** eye if T1 is affected |
| T2–T5 | T3–T7 | Paraplegia; trunk partly spared. **Above T6: neurogenic shock** (bradycardia, hypotension; sympathetic T1–T4 cardiac outflow lost) |
| T6–T9 | T8–T12 | Paraplegia; lower abdominal muscles lost |
| T10 | T11–L1 | Paraplegia; hip flexion lost |
| T11 | L1–L3 | Legs: hips and knees lost |
| T12 | L3–L5 | Knees and ankles lost; lumbar enlargement |
| L1 | S1–S5 (conus) | Ankles, **bladder, bowel and sexual function** (conus medullaris syndrome) |
| L2–S2 | cauda equina roots only | Flaccid, often **asymmetric and incomplete** leg weakness; saddle anaesthesia; bladder |

- Motor levels for the paralysis map `[K] (H)`:
  - Diaphragm C3–C5
  - Deltoid and biceps C5; wrist extensors C6; triceps C7; finger flexors C8; hand intrinsics T1
  - Hip flexion L2; knee extension L3–L4; ankle dorsiflexion L5; plantarflexion S1
  - Bladder and bowel S2–S4

### 9.4 Brainstem, cerebellum and cervicomedullary junction (body frame and relative to the head origin)

- The brainstem lies **on the clivus**, behind the sphenoid and nasopharynx and in front of the cerebellum.
- Its long axis (Meynert's axis) is **tilted ~15–25° from vertical, top forward**.
- **Key fit**: the **pontomedullary junction lies at almost exactly the height and AP position of the head origin**. The vestibulocochlear nerve (CN VIII) leaves the brainstem there and runs out through the internal acoustic meatus, which is nearly level with the ear canal `[K] [E] (M)`.

| Structure | Centre, body frame (x, y, z) | Centre relative to head origin | Size (length along axis × width × AP, mm) | Notes | Source |
|---|---|---|---|---|---|
| Midbrain | (0, +0.010, 1.690) | (0, −0.010, +0.035) | 15–20 × 30 (peduncles) × 25 | Passes through the tentorial notch; top joins the thalamus | [K] [D04] (M) |
| Pons | (0, +0.014, 1.667) | (0, −0.006, +0.012) | 25–27 × 35–38 × 25 | Front (basis) at y ≈ +0.001 on the clivus / basilar artery; back = floor of the 4th ventricle at y ≈ +0.026 | [K] [D04] (M) |
| **Pontomedullary junction** | (0, +0.020, 1.655) | **(0, 0.000, 0.000)** | — | CN VI, VII, VIII exit here | [K] [E] (M) |
| Medulla oblongata | (0, +0.025, 1.641) | (0, +0.005, −0.014) | 30 × 20 (at the olives) → 12 × 12–13 | Respiratory and vasomotor centres (doc 04) | [K] [D04] (M) |
| Cervicomedullary junction | (0, +0.030, 1.627) | (0, +0.010, −0.028) | 11 × 9 | Just below the basion–opisthion plane | [K] [E] (M) |
| Cord at C1 | (0, +0.024, 1.618) | (0, +0.004, −0.037) | 11.5 × 8.5 | Behind the dens | [K] [E] (M) |
| Cerebellum | (0, +0.065, 1.650); hemispheres at x ±0.045 | (0, +0.045, −0.005) | 100 wide × 50 tall × 55 deep | 140–150 g. Sits under the tentorium, above the foramen magnum | [K] (M) |
| Clivus (bone) | from the dorsum sellae (0, +0.008, 1.680) to the basion (0, +0.018, 1.634) | — | length 45 mm | Brainstem lies just behind it | [B38] [E] (M) |
| Basilar artery | along the front of the pons, y ≈ −0.004, z 1.645 → 1.690 | — | Ø 3–4 mm | Formed by the vertebral arteries at the pontomedullary junction | [K] (M) |
| Vertebral arteries | through the C6 → C1 transverse foramina (x ±0.015), loop behind the C1 lateral masses (x ±0.028, y +0.035, z 1.622), enter the foramen magnum | — | Ø 3–4 mm | | [K] [D03] (M) |

- **Total brainstem**: ~7.5 cm long, 25–30 g `[D04] [K] (M)`.
- **From the side**, the brainstem column sits on the line joining the ear canals, spanning ~3 cm below to ~4 cm above it, and 0–2 cm in front of it. This agrees with doc 04's T-zone description.

### 9.5 Simulation parameters: cord and brainstem

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `cord_centreline` | §4.1 "Cord centre y" + body-centre z, C1 → L1 | m | 26-node capsule chain | [E] (M) |
| `cord_radius_transverse / ap` | per §9.2 (C5: 6.75 / 3.85 mm; T7: 4.0 / 3.15 mm) | mm | | [B26] [B27] (M) |
| `conus_tip` | (0, +0.017, 1.180) = L1/L2 | m | | [B28] (H) |
| `cauda_equina_chain` | L1/L2 → S2, radius 7 mm | m | | [K] (M) |
| `thecal_sac_end` | S2 (0, +0.035, 0.995) | m | | [K] (H) |
| `cord_segment_offset` | cervical +1, upper thoracic +2, lower thoracic +3; T11–L1 = lumbosacral | levels | Paralysis map §9.3 | [K] (H) |
| `brainstem_nodes_rel_head_origin` | midbrain (0, −0.010, +0.035); pons (0, −0.006, +0.012); medulla (0, +0.005, −0.014); CMJ (0, +0.010, −0.028) | m | Existing head space | [K] [E] (M) |
| `medulla / pons / midbrain length` | 30 / 25 / 18 | mm | Matches doc 04 | [D04] (M) |
| `cord_depth_from_back_skin` T7 / L1 (conus) / C5 | ~53 / ~60 / ~45 | mm | Thin people less, heavy people more | [E] (M) |

### 9.6 Visual/behavioural checklist: cord and brainstem

- The **cord is a white, soft, pencil-thick rope** (#EEE5D6). In section it shows a **grey butterfly** (#B9A89E) inside white matter, with pink surface vessels. It sits in a **silvery dural tube** (#D9D6CE) filled with **clear CSF**, which leaks as a watery, blood-tinged fluid from a canal wound.
- **Below the conus** (L2 and lower) there is no cord, only the **cauda equina**, a loose bundle of white strands like a horse's tail. A stab there causes partial, patchy weakness, not a clean cord transection.
- A **knife between spinous processes** reaches the canal most easily in the **lower cervical region (C5–C7) and the lumbar region**. In the thoracic region, the overlapping, downward-sloping spinous processes and laminae shield the cord unless the blade is angled upward.
- Brainstem hits: see doc 04 §2 for the instant flaccid collapse, apnoea and pupils.

---

## 10. Neck and thoracic organs

All positions are **standing, at end-expiration**. For supine and breathing offsets see §14.

### 10.1 Thyroid, larynx, trachea, main bronchi

| Structure | Position (body frame) | Size | Mass / volume | Notes | Source |
|---|---|---|---|---|---|
| Thyroid lobe, L | centre (+0.022, −0.028, 1.505); upper pole z 1.535 (thyroid cartilage oblique line), lower pole z 1.475 (5th–6th tracheal ring) | 50 tall × 20 wide × 18 AP mm | 8–10 mL per lobe | Hugs the anterolateral trachea; the carotid sheath is directly lateral | [K] (M) |
| Thyroid isthmus | (0, −0.042, 1.492), over tracheal rings 2–4 | 20 × 20 × 3–6 mm | — | ~1 cm under the skin | [K] (M) |
| Thyroid, total | — | — | **20 g** (15–25) | Beefy dark red-brown (#8B3A2E); very vascular | [B43] (H) |
| Larynx: thyroid cartilage | prominence (0, −0.058, 1.537); laminae 40 mm wide | — | — | C4–C5 | [K] (M) |
| Cricoid ring | (0, −0.033, 1.513) lumen centre; anterior arch at y −0.047 | ring outer AP ~25 mm | — | C6. The only complete tracheal-airway ring | [K] (M) |
| **Trachea** | from the lower cricoid (0, −0.030, 1.508) → at the jugular notch (0, −0.018, 1.455) → **carina (−0.003, +0.008, 1.402)**, T4/T5 | length **11 (10–12) cm**; outer Ø **20 coronal × 18 sagittal mm** (15–25); wall ~3 mm | — | 16–20 C-shaped cartilage rings (~4 mm tall), open at the back (membranous wall on the oesophagus) | [K] (H) |
| Right main bronchus | carina → (−0.028, +0.012, 1.380) | 25 mm long, Ø 15; 25° from vertical | — | Wider and more vertical, so inhaled objects go right | [K] (H) |
| Left main bronchus | carina → (+0.042, +0.020, 1.380) | 50 mm long, Ø 12; 45° from vertical | — | Passes under the aortic arch, in front of the oesophagus and descending aorta | [K] (H) |

### 10.2 Oesophagus

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Path | C6 start (0, −0.012, 1.508) → T2/3, slightly left (+0.004, +0.012, 1.450) → behind the arch, right of it (0, +0.022, 1.415) → behind the left atrium at T7 (+0.002, +0.024, 1.355) → curves left and forward (+0.012, +0.012, 1.310) → **hiatus at T10 (+0.022, −0.008, 1.280)** → gastro-oesophageal junction at T11 (+0.030, −0.018, 1.255) | m | Lies in front of the vertebral bodies and behind the trachea and heart | [K] [E] (M) |
| Length | 25–26 | cm | 15 → 40 cm from the incisors | [K] (H) |
| Diameter | collapsed ~20 × 15; distended up to 30 | mm | | [K] (H) |
| Wall | 3–4 (empty) | mm | No serosa, so leaks spread fast into the mediastinum | [K] (H) |
| Colour | outside pink-red muscle (#B86A60); mucosa pale pink-white (#D9A9A0) | — | | [K] [G] |

### 10.3 Heart

**Orientation** `[K] [E] (M)`:
- Long axis from the **centre of the base** (atria, posterior-superior, right) (0.000, −0.005, 1.360) to the **apex** (+0.082, −0.068, 1.285).
- Length 0.127 m. Unit vector **u = (0.632, −0.498, −0.593)**.
- The axis points **left, forward and down**: ~45° left of the sagittal plane and ~35° below horizontal.
- The **apex beat is at the 5th left ICS, mid-clavicular line** (~9 cm from the midline).

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| External size | **12–13 (base–apex) × 8.5–9 (transverse) × 6–6.5 (AP)** | cm | Roughly a clenched fist | [K] (H) |
| **Mass** | **320 (range 250–380)** | g | Molina & DiMaio male mean ≈ 330 g; ICRP reference male 330 g | [B17] [B43] (H) |
| Volume (tissue) / with blood in the chambers | ~300 / ~750 | mL | End-diastolic chamber volumes total ~450 mL | [B22] [E] (M) |
| Centre (geometric) | **(+0.030, −0.035, 1.330)** | m | ~⅔ of the heart lies left of the midline | [K] [E] (M) |
| Axis-aligned extents | x [−0.048, +0.090], y [−0.082, +0.010], z [1.278, 1.405] | m | For a quick AABB; use the oriented box for hits | [E] (M) |
| Right border | right atrium, 1–2 cm right of the sternal edge, from the 3rd to the 6th right costal cartilage: x ≈ −0.045, z 1.310–1.380 | m | | [K] (H) |
| Left border | from the 2nd left ICS, 2 cm from the sternal edge (+0.035, 1.395), curving to the apex | m | | [K] (H) |
| Inferior border | from the 6th right costal cartilage (−0.030, 1.305) to the apex, along the central tendon (≈ xiphisternal level) | m | | [K] (H) |
| Anterior surface | right ventricle, directly behind the lower half of the sternum and the left 3rd–6th costal cartilages; y ≈ −0.075 to −0.082 | m | **2.5–3.5 cm below the skin over the lower sternum** | [K] [E] (M) |
| Posterior surface | left atrium at y ≈ +0.010, directly in front of the oesophagus and descending aorta (T6–T8) | m | | [K] (H) |

**Chambers and walls** (centres in body frame; sizes from echocardiography norms `[B22] (H)` unless marked):

| Chamber | Centre (x, y, z) | Cavity size / volume | Wall | Notes |
|---|---|---|---|---|
| Right atrium | (−0.030, −0.018, 1.335) | ~45 × 50 mm; ~60 mL max | 2–3 mm | Receives the SVC (top) and IVC (bottom) |
| Right ventricle | (+0.012, −0.060, 1.312) | EDV 150–170 mL; basal Ø ≤ 41 mm | **3–5 mm** | Crescent wrapped around the LV. **Most anterior chamber: the one a stab wound behind the sternum hits first** |
| Left atrium | (+0.008, −0.008, 1.365) | AP ~35–40 mm; ~55 mL | 2–3 mm | Most posterior chamber; 4 pulmonary veins enter it |
| Left ventricle | (+0.045, −0.035, 1.305) | EDV ~140 mL (male 100–190); end-diastolic Ø 48–50 mm (42–58); stroke volume 70–80 mL | **9–11 mm** (normal ≤ 12); septum 9–11 mm | Forms the apex and most of the left border |
| Pericardium | encloses the heart plus the first 2–3 cm of the great vessels | 15–50 mL fluid | fibrous sac 1–2 mm | Tamponade from ~150–200 mL of acute bleeding (doc 03) |
| Epicardial fat | along the AV and interventricular grooves | ~5 mm | — | Yellow (#E6C45A) |

**Valves** (surface projection `[K] (H)` → body frame `[E]`):

| Valve | Surface projection | Position (x, y, z) | Annulus Ø (mm) |
|---|---|---|---|
| Pulmonary | behind the left 3rd costal cartilage, sternal edge | (+0.022, −0.058, 1.378) | 20–25 |
| Aortic | behind the left half of the sternum at the 3rd ICS | (+0.008, −0.038, 1.360) | 21–25 |
| Mitral | behind the left 4th costal cartilage | (+0.030, −0.030, 1.340) | 30–35 |
| Tricuspid | behind the sternum at the 4th ICS | (−0.008, −0.048, 1.325) | 35–40 |

- **Coronary arteries** `[K] [D03:R45] (H)`:
  - Left main 4–4.5 mm Ø, splitting into the LAD (in the anterior interventricular groove, 3.5 mm Ø) and the circumflex.
  - The RCA (in the right AV groove, 3.5 mm Ø) runs around the right border to the back.

### 10.4 Great vessels: centreline waypoints (body frame)

Diameters follow doc 03 `[D03:R43–R49]`. The positions are this document's fit `[K] [E] (M)`. Build each vessel as a capsule chain through the waypoints.

| Vessel | Waypoints (x, y, z), in order | Lumen Ø (mm) | Notes |
|---|---|---|---|
| Ascending aorta | aortic valve (+0.008, −0.038, 1.360) → (−0.008, −0.048, 1.405) | 30 (28–35) | Rises forward and right to the sternal-angle level. Inside the pericardium |
| Aortic arch | (−0.008, −0.048, 1.405) → apex (0.000, −0.020, 1.428) → (+0.022, +0.030, 1.418) (T4, left) | 27 (25–30) | Top ~2.5 cm below the jugular notch, behind the manubrium |
| Brachiocephalic trunk | (−0.002, −0.035, 1.430) → split behind the right SC joint (−0.025, −0.030, 1.455) | 12 | → right subclavian + right CCA |
| Left common carotid (CCA) | (+0.010, −0.025, 1.432) → C6 (+0.028, −0.018, 1.515) → bifurcation at C4 (+0.030, −0.012, 1.558) | 7 (6–8) | ~2–3 cm deep to the skin in the neck. Right CCA mirrors it from the brachiocephalic split |
| Left subclavian | (+0.020, −0.008, 1.430) → over the 1st rib, behind the mid-clavicle (+0.065, −0.015, 1.462) → becomes the axillary at the rib's outer border (+0.090, −0.015, 1.450) | 8.5 | |
| Internal jugular vein (IJV), L | jugular foramen (+0.030, +0.030, 1.625) → lateral to the CCA at C6 (+0.040, −0.018, 1.515) → joins the subclavian vein behind the SC joint (+0.028, −0.030, 1.448) | 10–20 | |
| Superior vena cava (SVC) | (−0.028, −0.035, 1.438) → right atrium (−0.028, −0.028, 1.378) | 20 | 7 cm long; right of the ascending aorta |
| Pulmonary trunk | pulmonary valve (+0.022, −0.058, 1.378) → bifurcation under the arch (+0.012, −0.030, 1.405) | 27 (25–30) | RPA → right hilum (−0.060, +0.005, 1.385); LPA → left hilum (+0.055, +0.015, 1.395) |
| Descending thoracic aorta | T4 (+0.022, +0.030, 1.418) → T8 (+0.020, +0.030, 1.329) → aortic hiatus at T12 (+0.006, −0.012, 1.227) | 24 (20–26) | Left front of the vertebral bodies. Isthmus just past the left subclavian = classic blunt-rupture site |
| Abdominal aorta | T12 → renal arteries at L1/L2 (+0.008, −0.030, 1.180) → **bifurcation at L4 (+0.010, −0.045, 1.085)** | 21 → 18 | Just left of midline, on the vertebral bodies; ~7–8 cm under the skin of the navel |
| Common iliac arteries | bifurcation → (±0.040, −0.030, 1.035) (L5/S1, internal/external split) | 10 | |
| External iliac → femoral | → mid-inguinal point (±0.065, −0.068, 0.955) | 8.5 | The femoral artery lies just medial to the femoral head (§7.2) |
| Inferior vena cava (IVC) | formed at L5 (−0.020, −0.035, 1.050) → behind the liver (−0.022, −0.015, 1.260) → caval hiatus at T8 (−0.022, −0.010, 1.325) → right atrium (−0.025, −0.015, 1.315) | 21 (17–25) | Right of the aorta. The retrohepatic segment is embedded in the liver |
| Renal arteries / veins | aorta at L1/L2 → hila (±0.048, +0.010, 1.170) | artery 5–6; left vein 8–10 | The left renal vein crosses in front of the aorta |

### 10.5 Lungs and pleura

| Item | Right lung | Left lung | Unit | Notes | Source |
|---|---|---|---|---|---|
| Lobes | upper, middle, lower (3) | upper (with lingula), lower (2) | — | | [K] (H) |
| Centre (FRC, standing) | (−0.080, +0.012, 1.385) | (+0.082, +0.020, 1.390) | m | The left is displaced by the heart (cardiac notch) | [E] (M) |
| Extents x | [−0.140, −0.010] | [+0.010, +0.140] | m | The two anterior borders nearly meet behind the sternum from T2 to T4 | [E] (M) |
| Extents y | [−0.078, +0.090] | [−0.075, +0.090] | m | The lungs fill the paravertebral gutters behind | [E] (M) |
| Extents z (apex → lowest peripheral base) | [1.270, 1.495] | [1.265, 1.495] | m | Height ~23–25 cm | [E] (M) |
| Apex | (−0.040, +0.015, 1.495) | (+0.040, +0.015, 1.495) | m | **2.5–3 cm above the medial third of the clavicle**; at the neck of rib 1 (T1) behind | [K] (H) |
| Hilum | (−0.050, +0.020, 1.380) | (+0.050, +0.025, 1.388) | m | T5–T7 | [K] (M) |
| Lower border, lung (quiet expiration) | 6th rib at the MCL; 8th at the MAL; 10th at the back (T10) | same, slightly lower | — | "6-8-10" rule; z ≈ 1.27–1.28 all round | [K] (H) |
| Lower border, pleura | 8th rib at the MCL; 10th at the MAL; 12th at the back (T12) | same | — | "8-10-12" rule; costodiaphragmatic recess z ≈ 1.21–1.23. A stab there can cross pleura and diaphragm into the liver or spleen | [K] (H) |
| Fissures | oblique: T3 spinous (back) → along the 5th rib → 6th costal cartilage (front); horizontal: 4th costal cartilage → meets the oblique at the MAL | oblique only (same line) | — | | [K] (H) |
| Mass (autopsy, with blood) | 550–650 (use 550 living) | 450–550 (use 480 living) | g | ICRP: both lungs 1,200 g with blood | [B17] [B43] (M) |
| Volume at FRC / TLC | ~1.8 / 3.9 | ~1.55 / 3.2 | L | Right ≈ 55 % | [B19] [E] (M) |

**Whole-lung volumes for this man** (ERS 1993 reference equations, H in m, age A = 30) `[B19] (H)`:

| Volume | Equation | Value |
|---|---|---|
| TLC | 7.99 H − 7.08 | **7.1 L** |
| FRC | 2.34 H + 0.009 A − 1.09 | **3.35 L** |
| RV | 1.31 H + 0.022 A − 1.23 | 1.76 L |
| VC | 6.10 H − 0.028 A − 4.65 | 5.4 L |
| Tidal volume | — | ~0.5 L at 12–16 breaths/min |

- **Lung tissue** is only ~10–20 % of lung volume. Density at FRC is ≈ 0.25–0.3 g/mL including blood, ≈ −800 HU on CT `[K] (M)`.
- **Visceral and parietal pleura** are ~0.1 mm thick, glossy, with 5–15 mL of fluid between them `[K] (H)`.

### 10.6 Diaphragm

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Right dome apex (standing, end-expiration) | (−0.070, −0.005, 1.320) | m | 5th rib / 4th ICS at the front (MCL); T8–T9 behind | [K] [E] (M) |
| Left dome apex | (+0.075, +0.005, 1.300) | m | ~1.5–2 cm lower than the right; 5th ICS / 6th rib | [K] [E] (M) |
| Central tendon (the heart sits on it) | (0.000, −0.030, 1.310) | m | ≈ xiphisternal level | [K] (H) |
| Openings | IVC at T8 (−0.022, −0.010, 1.325); oesophagus at T10 (+0.022, −0.008, 1.280); aorta at T12 (+0.006, −0.012, 1.227) | m | "I 8 10 Eggs At 12" | [K] (H) |
| Peripheral attachments | xiphoid; inner surfaces of costal cartilages 7–10 and ribs 11–12 (z ≈ 1.12–1.30 around the margin); arcuate ligaments; crura to L1–L3 (right) and L1–L2 (left) bodies | — | | [K] (H) |
| Thickness | muscle 3–5; central tendon 1–2 | mm | | [K] (M) |
| Excursion | quiet 1.5–2 cm; deep 6–10 cm | cm | Upper abdominal organs move with it (§14) | [K] (H) |
| Posture | supine: domes ~2–4 cm higher than standing | cm | | [K] (M) |

### 10.7 Simulation parameters: neck and thoracic organs

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `heart_centre` | (+0.030, −0.035, 1.330) | m | | [E] (M) |
| `heart_axis_base_to_apex` | (0, −0.005, 1.360) → (+0.082, −0.068, 1.285) | m | Oriented-box long axis | [K] [E] (M) |
| `heart_obb_half_extents` | 0.063 (long) × 0.045 × 0.032 | m | 12.5 × 9 × 6.5 cm | [K] (H) |
| `heart_mass` | 320 | g | | [B17] [B43] (H) |
| `lv_wall / rv_wall / atrial_wall` | 10 / 4 / 2.5 | mm | | [B22] (H) |
| `lv_edv / rv_edv / sv` | 140 / 160 / 75 | mL | | [B22] (H) |
| `chamber_centres` | table §10.3 | m | 4 ellipsoids inside the heart OBB | [E] (M) |
| `great_vessel_waypoints` | table §10.4 | m | Shared with doc 03 | [K] [E] (M) |
| `lung_R / lung_L` centre, extents | table §10.5 | m | Use 3 + 2 lobe sub-volumes split by the fissure planes | [E] (M) |
| `lung_mass_R / L` | 550 / 480 | g | | [B43] (M) |
| `tlc / frc / tidal` | 7.1 / 3.35 / 0.5 | L | | [B19] (H) |
| `diaphragm_dome_R / L / central` | z 1.320 / 1.300 / 1.310 | m | End-expiration, standing | [K] [E] (M) |
| `diaphragm_excursion_quiet / deep` | 0.018 / 0.08 | m | | [K] (H) |
| `trachea` | cricoid (0, −0.030, 1.508) → carina (−0.003, +0.008, 1.402), outer Ø 20 mm | m | | [K] (H) |
| `oesophagus_path` | table §10.2 | m | | [K] [E] (M) |
| `thyroid_lobes / isthmus` | table §10.1; mass 20 g | m | | [B43] (H) |

### 10.8 Visual/behavioural checklist: neck and thoracic organs

- **Heart**: glossy, **dark red-brown myocardium** (#7B2626) streaked with **yellow epicardial fat** (#E6C45A) along the grooves, under a thin shiny pericardium. It beats at the physiology heart rate. The apex swings forward and left in systole, and the **RV is the first thing seen** through a lower-sternal or left parasternal wound.
- **Lungs**: soft, spongy and **pink** (#E0A0A0) in life. They crackle (crepitate) when squeezed and float in water. Adult urban lungs have **grey-black speckling** (#3A3A3A, anthracosis) along the lobules. After death they become dark red-purple where blood pools (#A04A55, lowest parts).
- **Collapse**: an opened pleura lets the lung **shrink toward the hilum** (pneumothorax). A sucking chest wound hisses and bubbles with each breath.
- **Trachea**: white C-rings (#E2DDD2) with a soft back wall. Cut, it shows the **pink mucosa** (#D98A8A) inside and whistles or bubbles with each breath.
- **Diaphragm**: a red muscular sheet (#9E3A34) with a **pearly central tendon** (#E4E0D8). It rises and falls with breathing.
- **Thyroid**: a beefy, **dark red-brown**, very vascular butterfly just below the larynx. Cuts bleed briskly.

---

## 11. Abdominal and pelvic organs (no intestines)

Positions are **standing, end-expiration**. Upper abdominal organs sit ~2–4 cm lower than the supine CT-based textbook levels `[B32] [K] (M)`, and the kidneys ~2–3 cm lower.

### 11.1 Liver and gallbladder

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Mass | **1,550** (1,400–1,800) | g | Molina & DiMaio male mean ~1,560 g; ICRP 1,800 g | [B17] [B43] (H) |
| Volume | ~1,450 | mL | Density 1.06 | [E] |
| Centre of mass | **(−0.055, −0.005, 1.230)** | m | Right upper quadrant, under ribs 7–11 | [K] [E] (M) |
| Extents x | [−0.145, +0.080] | m | Transverse 22.5 cm (20–23); the left lobe reaches the left MCL | [K] [E] (M) |
| Extents y | [−0.085, +0.070] | m | Right lobe AP 13–15 cm; left lobe 5–7 cm thick | [K] [E] (M) |
| Extents z | dome [1.315] (under the right hemidiaphragm, ~5th rib); lower edge 1.155 at the right MAL, 1.19 at the midline, 1.21 at the left MCL | m | Craniocaudal at the right MCL: **14.5 cm** (ultrasound normal ≤ 16) | [B23] [K] (M) |
| Lower border | follows the right costal margin; crosses the midline roughly halfway between xiphoid and navel (≈ transpyloric plane) | — | In a lean man the edge may be felt just below the right costal margin on deep inspiration | [K] (H) |
| Right lobe | ~60–65 % of volume; centre (−0.075, +0.005, 1.230) | — | | [K] (M) |
| Left lobe (segments II–III) | centre (+0.040, −0.045, 1.270); thin, extends over the stomach | — | | [K] (M) |
| Caudate lobe | (−0.010, +0.030, 1.255); wraps the IVC | — | | [K] (M) |
| Bare area (no peritoneum) | back of the dome, against the diaphragm; retrohepatic IVC groove at x −0.022 | — | Retrohepatic IVC tears are lethal (doc 03) | [K] (H) |
| Capsule (Glisson) | < 0.1 mm; parenchyma friable | — | Tears and bursts easily under blunt force | [K] (H) |
| Blood flow | ~1.5 L/min (25 % of CO; ⅔ portal, ⅓ arterial) | L/min | See doc 03 for bleed rates | [K] (H) |
| Gallbladder | fundus at the tip of the right 9th costal cartilage (lateral rectus border): (−0.075, −0.065, 1.190); pear-shaped, 8 × 3.5 cm; 30–50 mL bile | — | Green (#4F6E3E); bile stains tissue yellow-green | [K] (H) |

### 11.2 Spleen

| Item | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Size | **12 × 7 × 4** (length 9–13) | cm | "1-3-5-7-9-11": 1 × 3 × 5 in, ~7 oz, ribs 9–11 | [B25] [K] (H) |
| Mass | **150** (80–250) | g | ICRP 150 g | [B43] [B17] (H) |
| Centre | **(+0.105, +0.040, 1.228)** | m | Left posterior, under ribs 9–11 | [K] [E] (M) |
| Long axis | along the 10th rib: upper pole (+0.080, +0.075, 1.275) → lower pole (+0.130, +0.005, 1.180) | m | The normal spleen does not reach in front of the MAL | [K] (H) |
| Relations | diaphragm and ribs behind and to the side; stomach in front; left kidney below and medial; pancreatic tail at the hilum | — | Lower rib fractures (9–11) on the left → splenic tear | [K] (H) |
| Capsule | 1–2 mm | mm | | [K] (M) |
| Blood flow | ~150–250 | mL/min | Pulp holds ~30–50 mL of blood; very high bleed potential (doc 03) | [K] (M) |
| Colour | purple-red (#5E2433); cut surface dark red pulp (#6A1E2B) | — | | [K] [G] |

### 11.3 Kidneys and adrenals

| Item | Left kidney | Right kidney | Unit | Notes | Source |
|---|---|---|---|---|---|
| Size | 11.5 × 6 × 4 | 11 × 6 × 4 | cm | Normal length 10–13 cm | [B24] (H) |
| Mass | 150 | 145 | g | ICRP: 310 g for both | [B43] [B17] (H) |
| Centre (standing) | **(+0.070, +0.025, 1.180)** (L1–L2) | **(−0.070, +0.025, 1.160)** (L2) | m | **Right ~2 cm lower** (liver above it). Supine: +2 cm | [K] [E] (M) |
| Upper pole | (+0.055, +0.035, 1.235) | (−0.055, +0.035, 1.215) | m | Poles are tilted: upper medial and posterior | [K] [E] (M) |
| Lower pole | (+0.085, +0.012, 1.125) | (−0.085, +0.012, 1.105) | m | | [K] [E] (M) |
| Hilum | (+0.048, +0.010, 1.180) | (−0.048, +0.010, 1.160) | m | Faces forward and medially (kidney rotated ~30° about its long axis) | [K] (M) |
| Depth from back skin | 5–7 cm to the posterior surface | same | cm | Under the 12th rib, quadratus lumborum and erector spinae | [K] [E] (M) |
| Structure | cortex 7–10 mm; medulla (8–12 pyramids); sinus fat; renal pelvis → ureter | | | Perirenal fat 5–30 mm (lean: 5–10) | [K] (H) |
| Blood flow | ~0.55 L/min each (≈ 20–25 % of CO for both) | | L/min | | [K] (H) |
| Adrenal gland | crescent on the upper-medial pole: (+0.042, +0.025, 1.230) | pyramid above the upper pole, behind the IVC: (−0.040, +0.030, 1.235) | m | Each 5 × 3 × 0.6 cm, 4–6 g. Yellow cortex (#D9A441), brown medulla | [K] [B43] (M) |

### 11.4 Stomach, pancreas, bladder

| Organ | Position | Size / capacity | Mass | Notes | Source |
|---|---|---|---|---|---|
| **Stomach** (moderately full, ~500 mL, standing) | cardia at T11 (+0.030, −0.018, 1.255); fundus under the left dome (+0.070, +0.010, 1.290); body down the left side; greater curvature low point (+0.050, −0.050, 1.100); antrum across the midline (0.000, −0.065, 1.140); pylorus (−0.025, −0.045, 1.170) at L1–L2 | AABB x [−0.035, +0.110], y [−0.085, +0.035], z [1.095, 1.305]; empty ~50 mL, meal 0.5–1 L, max 1.5–4 L | wall ~150 g | Wall 3–5 mm distended, 5–8 mm empty (rugae). Serosa pink-grey (#C9A0A0); mucosa red-pink (#C4676B). **Gastric contents spill on penetration** | [K] [B43] (M) |
| **Pancreas** (retroperitoneal) | head in the duodenal C (−0.035, −0.035, 1.160), L2; neck (−0.005, −0.050, 1.180); body over the aorta at L1 (+0.025, −0.045, 1.195); tail to the splenic hilum (+0.090, +0.015, 1.215) | 14 cm long; head 3 cm thick, body and tail 2 cm | 90–140 g | Pale tan, lobulated (#D8B49A). Crushed against L1 by a blow to the upper abdomen | [K] [B43] (M) |
| **Urinary bladder** | empty: (0, −0.030, 0.915), behind the symphysis; full (500 mL): centre (0, −0.035, 0.960), dome up to z ≈ 1.01 (above the pubis) | empty ~5 × 5 × 4 cm; capacity 400–600 mL (urge at 300–400) | wall ~50 g | Wall 3 mm distended, 5+ mm empty. Pale pink-tan (#D8B5A5) | [K] [B43] (H) |
| Prostate (optional) | (0, −0.025, 0.880), below the bladder neck | 4 × 3 × 3 cm | ~20 g | | [K] (M) |

### 11.5 Space the intestines fill (placeholder, not modelled in detail)

- The user excluded intestines. The abdominal and pelvic cavity still needs a **mass and volume filler** so that the abdomen does not read as empty to hit resolution and the ragdoll.
- ICRP puts small-intestine wall plus contents at ≈ 1.0 kg and colon wall plus contents at ≈ 0.7–1.0 kg `[B43] (M)`.
- Use one soft "bowel mass" volume of **~2.0–2.5 kg** occupying the space below the liver, stomach and spleen, from z ≈ 0.90 (pelvis) to z ≈ 1.18 and y from −0.100 to +0.020 (in front of the kidneys, aorta and IVC) `[G]`.

### 11.6 Simulation parameters: abdominal organs

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `liver_centre / aabb` | (−0.055, −0.005, 1.230); x [−0.145, 0.080], y [−0.085, 0.070], z [1.155, 1.315] | m | Model as right lobe, left lobe and caudate sub-volumes | [K] [E] (M) |
| `liver_mass` | 1,550 | g | | [B17] (H) |
| `gallbladder_fundus` | (−0.075, −0.065, 1.190) | m | | [K] (M) |
| `spleen_centre / axis` | (+0.105, +0.040, 1.228); poles (+0.080, +0.075, 1.275) → (+0.130, +0.005, 1.180) | m | 12 × 7 × 4 cm OBB | [K] [E] (M) |
| `spleen_mass` | 150 | g | | [B43] (H) |
| `kidney_L / R centre` | (+0.070, +0.025, 1.180) / (−0.070, +0.025, 1.160) | m | 11.5 × 6 × 4 cm OBB along the pole axis | [K] [E] (M) |
| `kidney_mass` | 150 each | g | | [B43] (H) |
| `adrenal_L / R` | (+0.042, +0.025, 1.230) / (−0.040, +0.030, 1.235) | m | 5 g each | [K] (M) |
| `stomach_aabb` | x [−0.035, 0.110], y [−0.085, 0.035], z [1.095, 1.305] | m | Fill level changes volume | [K] (M) |
| `pancreas_path` | head → neck → body → tail, as §11.4 | m | Capsule chain, r 10–15 mm | [K] (M) |
| `bladder_centre_empty / full` | (0, −0.030, 0.915) / (0, −0.035, 0.960) | m | Radius 25 / 50 mm | [K] (M) |
| `bowel_filler_mass` | 2.0–2.5 | kg | | [B43] [G] |
| `standing_vs_supine_shift` | liver, spleen −2 to −3 cm; kidneys −2 to −4 cm | m | §14 | [K] (M) |

### 11.7 Visual/behavioural checklist: abdominal organs

- **Liver**: large, smooth and glossy, **red-brown** (#7A2E23). It bursts and fissures ("stellate" tears) under blunt force and **oozes continuously** from the cut surface (#6E2A22). The sharp lower edge peeks below the right costal margin.
- **Spleen**: fist-sized and **purple**, tucked high at the back left under ribs 9–11. Cut, it pours dark blood. A left lower-rib fracture should roll a spleen-injury chance.
- **Kidneys**: bean-shaped and **deep in the back**, embedded in **yellow perirenal fat**. They are reached through the flank or back more easily than from the front. A cut shows a pale brown cortex (#9A5040) over dark striated pyramids (#6E2A2A). Blood in the urine is the tell.
- **Stomach**: a pale pink-grey bag. Penetration spills **sour-smelling gastric contents** (food, acid, bile-green if refluxed).
- **Bladder**: hidden behind the pubic bone unless full. A **full bladder ruptures** under a kick or blow to the lower abdomen.

---

## 12. Tissue layers and depth to structures

### 12.1 Skin thickness by site (epidermis + dermis)

| Site | Total skin (mm) | Epidermis (mm) | Notes | Source |
|---|---|---|---|---|
| Eyelid | 0.5–0.7 | 0.04 | Thinnest | [B31] [K] (H) |
| Face (cheek, forehead) | 1.5–2.0 | 0.05–0.1 | | [B31] (M) |
| Scalp | 3.5–5.5 | — | Scalp total to bone 5–8 mm | [D02:R16] |
| Neck | 1.5–2.0 | 0.05–0.08 | | [B31] (M) |
| Chest | 1.5–2.0 | 0.05–0.08 | | [B31] (M) |
| Abdomen | 1.5–2.5 | 0.05–0.08 | | [B31] (M) |
| **Back** | **2.5–4.0** | 0.08–0.1 | Thickest dermis on the body | [B31] [K] (H) |
| Upper arm / thigh | 1.2–2.0 | 0.05–0.08 | | [B31] (M) |
| Forearm (volar) | 1.0–1.3 | 0.05 | | [B31] (M) |
| Palm | 1.5–2.0 | 0.4–0.6 | Thick epidermis, no hair | [K] (H) |
| Sole / heel | 2–4 | 0.6–1.5 | | [K] (H) |

### 12.2 Region-by-region layer stack (lean-average 75 kg man, ~15 % fat)

- Subcutaneous adipose tissue (**SAT**) ranges cover roughly 12–18 % body fat.
- Muscle thicknesses follow B-mode ultrasound series in young adult men `[B29] (M)`. Chest-wall totals follow CT needle-decompression studies `[B20] [B21] (M)`.
- **Depth** is the straight-line distance from the skin to the named structure along the surface normal.

| Region (point) | Skin | SAT | Muscle(s) | Depth to key structure | Source |
|---|---|---|---|---|---|
| Neck, anterior midline (cricoid) | 1.5 | 2–5 | strap muscles 3–4 | Cricoid / trachea at **8–12 mm**; thyroid isthmus ~10 mm | [K] (M) |
| Neck, anterolateral (over the carotid, C4–C6) | 1.5 | 3–6 | platysma 1–2 + sternocleidomastoid 8–12 | **CCA/IJV at 20–30 mm** | [K] [D03] (M) |
| Neck, posterior (C4 midline) | 3 | 3–8 | trapezius, splenius, semispinalis 25–35 | Lamina ~35 mm; **cord ~45–55 mm** | [K] [E] (M) |
| Over the sternum | 1.5–2 | 3–8 | none | Bone at **5–12 mm**; **right ventricle at 25–35 mm** (lower sternum) | [K] [E] (M) |
| Anterior chest, 2nd ICS MCL | 2 | 5–10 | pectoralis major 15–25 (+ pec minor 8–10) | **Pleura at 35–45 mm** (CT mean ≈ 40–45 mm in men; wide range 20–80) | [B20] [B21] (M) |
| Anterior chest, nipple line (4th–5th ICS, MCL) | 2 | 4–8 | pectoralis major 12–20 | Rib 8–10 mm thick; **pleura at 30–35 mm**; heart at 35–50 mm (left) | [K] [E] (M) |
| Lateral chest, 5th ICS, AAL/MAL | 2 | 5–15 | serratus anterior + latissimus 5–15; intercostals 5–7 | **Pleura at 25–40 mm** (thinner than 2nd ICS MCL in most CT series) | [B21] (M) |
| Upper back, T4–T7, 4–5 cm lateral | 3–4 | 5–10 | trapezius 5–8, rhomboids 5–10, erector spinae 20–35 | Rib at **40–60 mm**; lung just beyond. Over the spinous process: **8–12 mm** | [B29] [K] (M) |
| Scapular blade | 3 | 5–8 | infraspinatus 15–25 behind, subscapularis 15–20 in front | Blade at 20–30 mm; ribs/lung another 25–35 mm deeper | [K] (M) |
| Abdomen, paramedian at the navel (3 cm lateral) | 2 | **12–20 (use 15)** | rectus sheath + rectus abdominis 10–12 | Peritoneum at **25–40 mm**; bowel immediately behind; aorta at ~75 mm | [B29] [K] [E] (M) |
| Linea alba (midline) | 2 | 12–20 | aponeurosis 2 | Peritoneum at 16–24 mm | [K] (M) |
| Flank (MAL, L2) | 2 | 10–25 | external oblique, internal oblique, transversus 15–20 | Peritoneum 30–45 mm; kidney lateral edge ~60–80 mm | [K] (M) |
| Epigastrium (below the xiphoid) | 2 | 8–15 | linea alba / rectus 8 | Left lobe of the liver at 20–30 mm; stomach just below it | [K] [E] (M) |
| Lower back, L3, 4–5 cm lateral | 3–4 | 8–20 | erector spinae + multifidus 40–55 | Transverse process / lamina 55–75 mm; **kidney back surface 50–70 mm**; canal ~70 mm in the midline | [B29] [K] (M) |
| Buttock (upper outer) | 2.5–3 | 15–30 | gluteus maximus 30–50, medius 15–25 | Ilium 50–80 mm; **sciatic nerve (lower inner quadrant) 60–90 mm** | [K] (M) |
| Groin (femoral triangle) | 1.5 | 8–15 | none over the vessels | **Femoral artery at 15–30 mm** | [K] [D03] (M) |
| Deltoid | 1.5–2 | 4–8 | deltoid 15–25 | Humeral head / greater tuberosity at 25–35 mm | [B29] [K] (M) |
| Upper arm, anterior mid | 1.5 | 4–7 | biceps + brachialis 30–40 | Humerus at 40–45 mm; brachial artery medially at 10–20 mm (bicipital groove) | [B29] [K] (M) |
| Upper arm, posterior mid | 1.5 | 6–10 | triceps 25–35 | Humerus at 35–45 mm (radial nerve in contact with bone) | [B29] [K] (M) |
| Forearm, volar mid | 1.0–1.3 | 3–5 | flexors 15–25 | Radius/ulna at 20–30 mm | [B29] [K] (M) |
| Forearm, dorsal ulnar border | 1.2 | 2–3 | none | **Ulna at 3–5 mm** | [K] (H) |
| Wrist, volar | 1.0 | 2–3 | tendons | **Radial artery at 2–5 mm**; ulnar artery 4–7 mm | [K] (H) |
| Palm | 1.5–2 | fat pad 4–8 | palmar aponeurosis 1, then tendons | Metacarpals at 10–15 mm | [K] (M) |
| Back of the hand | 1.0–1.5 | 1–3 | extensor tendons 1–2 | Metacarpals at 3–6 mm | [K] (M) |
| Thigh, anterior mid | 1.5–2 | 6–12 | rectus femoris + vastus intermedius 45–55 | Femur at **55–70 mm** | [B29] [K] (M) |
| Thigh, posterior mid | 1.5–2 | 8–15 | hamstrings 50–65 | Femur at 65–80 mm | [B29] (M) |
| Knee, anterior | 1.5 | 2–4 | (prepatellar bursa) | **Patella at 4–8 mm** | [K] (H) |
| **Shin, anteromedial** | 1.5–2 | 1–3 | **none** | **Tibia at 3–6 mm** | [K] (H) |
| Calf, posterior | 1.5 | 4–8 | gastrocnemius 15–22 + soleus 15–25 | Posterior tibial vessels / tibia at 40–55 mm | [B29] (M) |
| Ankle (malleoli) | 1.5 | 1–2 | none | Malleoli at 2–4 mm | [K] (H) |
| Heel (plantar) | 2–4 | fat pad 15–20 (honeycomb) | — | Calcaneus at 18–24 mm | [K] (H) |

### 12.3 Skinfold cross-check

- Jackson–Pollock 3-site skinfolds (chest, abdomen, thigh) for a 30-year-old man at ~15 % fat total ≈ 45–55 mm. Typical split: chest 8–12, abdomen 18–25, thigh 12–16 mm `[B30] (M)`.
- A skinfold is a **double layer** of skin plus fat, compressed by the caliper. Single-layer SAT is therefore ≈ skinfold/2 − skin, e.g. ≈ 3–4 mm at the chest and 8–10 mm at the abdomen.
- Ultrasound reads somewhat thicker (it does not compress), which is why §12.2 gives 12–20 mm for periumbilical SAT `[K] (M)`.

### 12.4 Tissue colours (cut surfaces, fresh)

Colours match doc 02 where the tissue overlaps `[K] [G]`.

| Tissue | Hex | Description |
|---|---|---|
| Epidermis/dermis (cut edge) | #EAD2C8 | White-pink band 1–4 mm, dotted with bleeding points |
| Subcutaneous fat | #F2D16B | Lobulated, glistening yellow (doc 02) |
| Superficial fascia / aponeurosis / linea alba | #E8E6DF | Silvery white sheet |
| Skeletal muscle (fresh) | #9B2F2B | Striated, beefy red; darkens to #6E2020 as it loses oxygen |
| Muscle fascia (epimysium) | #D9C6BE | Thin translucent film |
| Pleura / peritoneum | — | Transparent glossy film (specular only) over the colour below |

### 12.5 Simulation parameters: tissue layers

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `skin_thickness_map` | §12.1 (face 1.8, trunk front 2, back 3.2, limbs 1.5, palm/sole 2–3) | mm | Paint as a texture channel | [B31] (M) |
| `sat_thickness_map` | chest 6, abdomen 15, flank 15, back 8, buttock 20, thigh 9, arm 6, forearm 4, calf 6, shin 2, hands/feet 2 | mm | Scale × (body fat % / 15) | [B29] [B30] [E] (M) |
| `muscle_thickness_map` | pectoral 18, rectus 11, obliques 17, erector (thoracic/lumbar) 28/48, glute max 40, deltoid 20, biceps+brachialis 35, triceps 30, forearm 20, quadriceps 50, hamstrings 58, calf 38 | mm | Scale × a muscularity factor | [B29] (M) |
| `chest_wall_to_pleura` 2nd ICS MCL / 5th ICS MAL | 42 / 32 | mm | | [B20] [B21] (M) |
| `sternum_skin_to_RV` | 30 | mm | | [E] (M) |
| `abdo_skin_to_peritoneum` (paramedian) | 30 | mm | | [E] (M) |
| `back_skin_to_kidney` | 60 | mm | | [K] [E] (M) |
| `subcutaneous_bone_sites` | tibial shaft, patella, malleoli, olecranon/ulna border, clavicle, iliac crest, ASIS, sternum, spinous processes, knuckles, skull | list | Blunt impacts here split the skin (doc 02) | [K] (H) |

### 12.6 Visual/behavioural checklist: tissue layers

- A clean cut shows, in order: **thin white-pink dermis, then yellow lobulated fat, then a silvery fascia film, then red striated muscle**. In lean regions (shin, back of hand, over the sternum) the **bone comes right after the dermis**.
- **Fat depth sells body type.** Lean areas (shins, hands, sternum, spine) show bone almost immediately. The abdomen and buttocks show a **1.5–3 cm yellow layer** before muscle.
- **Muscle retracts.** Cut across its fibres, muscle pulls apart and gapes widely. Cut along them, the gap stays narrow (doc 02 gape model).
- **Chest wounds reach the pleura within 2.5–4.5 cm** almost everywhere. Knife-length rules for "does it reach the lung/heart" should use §12.2, not a fixed global number.

---

## 13. Code-ready data (plain CSV, body frame, metres)

These blocks repeat the tables above in a form that can be pasted into a data file (`.csv`, or a GDScript `const` array) without retyping.
- Left-side structures only. Mirror by negating x (and the x components of any axis vectors) for `_R`.
- Colons and hash lines are comments. All data are this document's own `[E]`.

### 13.1 Landmarks

```csv
# name,x,y,z,kind   (kind: skin | bone | joint)
vertex,0.000,0.020,1.780,skin
head_origin_mid_ear_canals,0.000,0.020,1.655,joint
ear_canal_L,0.068,0.020,1.655,skin
glabella,0.000,-0.078,1.683,skin
eye_cornea_L,0.032,-0.074,1.666,skin
eye_centre_L,0.032,-0.062,1.666,bone
pronasale,0.000,-0.106,1.625,skin
menton,0.000,-0.068,1.550,skin
gonion_L,0.052,-0.005,1.585,skin
mastoid_tip_L,0.055,0.030,1.620,bone
inion,0.000,0.112,1.662,skin
basion,0.000,0.018,1.634,bone
atlanto_occipital_pivot,0.000,0.015,1.630,joint
laryngeal_prominence,0.000,-0.062,1.537,skin
cricoid,0.000,-0.055,1.515,skin
c7_spinous_cervicale,0.000,0.075,1.500,skin
jugular_notch,0.000,-0.048,1.455,skin
sc_joint_L,0.025,-0.040,1.450,joint
ac_joint_L,0.165,0.010,1.462,joint
acromion_L,0.200,0.015,1.458,bone
gh_joint_L,0.180,0.020,1.415,joint
sternal_angle,0.000,-0.075,1.405,skin
nipple_L,0.100,-0.112,1.300,skin
xiphisternal_joint,0.000,-0.110,1.305,skin
xiphoid_tip,0.000,-0.094,1.273,bone
scapula_inferior_angle_L,0.085,0.105,1.325,bone
costal_margin_lowest_L,0.112,-0.050,1.125,bone
navel,0.000,-0.108,1.075,skin
iliac_crest_top_L,0.140,0.025,1.070,bone
iliac_tubercle_L,0.143,-0.030,1.055,bone
asis_L,0.122,-0.062,1.009,bone
psis_L,0.045,0.090,1.010,bone
pubic_symphysis_top,0.000,-0.068,0.928,bone
hip_joint_centre_L,0.087,-0.015,0.935,joint
greater_trochanter_L,0.158,0.000,0.930,bone
ischial_tuberosity_L,0.055,0.020,0.858,bone
coccyx_tip,0.000,0.040,0.905,bone
crotch,0.000,0.005,0.840,skin
elbow_centre_L_apose,0.330,0.020,1.155,joint
wrist_centre_L_apose,0.455,0.020,0.938,joint
mcp3_L_apose,0.503,0.020,0.856,joint
fingertip3_L_apose,0.548,0.020,0.778,skin
knee_centre_L,0.092,0.020,0.505,joint
patella_centre_L,0.090,-0.035,0.522,bone
tibial_tuberosity_L,0.090,-0.025,0.447,bone
fibular_head_L,0.130,0.035,0.465,bone
ankle_centre_L,0.095,0.050,0.075,joint
lateral_malleolus_L,0.132,0.060,0.055,bone
medial_malleolus_L,0.065,0.045,0.068,bone
heel_L,0.095,0.115,0.030,skin
mtp1_L,0.084,-0.083,0.020,joint
mtp5_L,0.161,-0.049,0.018,joint
toe2_tip_L,0.128,-0.151,0.010,skin
```

### 13.2 Organs and hit volumes

- `size_u, size_v, size_w` are **full lengths** along the axes u, v and w = u × v. For `aabb` shapes, u = +X and v = +Y.
- Centres of `aabb` rows are **box centres**, which differ slightly from the centres of mass given in §10–11.
- Mass 0 means "part of the organ above".

```csv
# name,shape,cx,cy,cz,size_u,size_v,size_w,ux,uy,uz,vx,vy,vz,mass_g
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
spleen,obb,0.105,0.040,1.228,0.120,0.070,0.040,0.390,-0.547,-0.742,0.445,-0.594,0.672,150
kidney_L,obb,0.070,0.024,1.180,0.115,0.060,0.040,0.258,-0.198,-0.946,-0.804,-0.586,-0.097,150
adrenal_L,ellipsoid,0.042,0.025,1.230,0.030,0.010,0.050,1,0,0,0,1,0,5
stomach,aabb,0.038,-0.025,1.200,0.145,0.120,0.210,1,0,0,0,1,0,150
bladder_empty,sphere,0.000,-0.030,0.915,0.050,0.050,0.050,1,0,0,0,1,0,50
bladder_full,sphere,0.000,-0.035,0.960,0.100,0.100,0.100,1,0,0,0,1,0,50
thyroid_lobe_L,ellipsoid,0.022,-0.028,1.505,0.020,0.018,0.050,1,0,0,0,1,0,9
thyroid_isthmus,ellipsoid,0.000,-0.042,1.492,0.020,0.005,0.020,1,0,0,0,1,0,2
bowel_filler,aabb,0.000,-0.040,1.040,0.240,0.120,0.280,1,0,0,0,1,0,2200
# right side: kidney_R centre (-0.070,0.024,1.160) u(-0.258,-0.198,-0.946) v(0.804,-0.586,-0.097); adrenal_R (-0.040,0.030,1.235); thyroid_lobe_R (-0.022,-0.028,1.505)
# bowel_filler has the lowest hit priority: resolve every other organ first
```

### 13.3 Tube structures (capsule chains: name, radius_m, then points)

```csv
# name,radius,x1,y1,z1,x2,y2,z2,...
trachea,0.010,0.000,-0.030,1.508,0.000,-0.018,1.455,-0.003,0.008,1.402
bronchus_R,0.0075,-0.003,0.008,1.402,-0.028,0.012,1.380
bronchus_L,0.006,-0.003,0.008,1.402,0.042,0.020,1.380
oesophagus,0.009,0.000,-0.012,1.508,0.004,0.012,1.450,0.000,0.022,1.415,0.002,0.024,1.355,0.012,0.012,1.310,0.022,-0.008,1.280,0.030,-0.018,1.255
pancreas,0.012,-0.035,-0.035,1.160,-0.005,-0.050,1.180,0.025,-0.045,1.195,0.090,0.015,1.215
aorta_asc_arch,0.014,0.008,-0.038,1.360,-0.008,-0.048,1.405,0.000,-0.020,1.428,0.022,0.030,1.418
aorta_desc,0.012,0.022,0.030,1.418,0.020,0.030,1.329,0.006,-0.012,1.227,0.008,-0.030,1.180,0.010,-0.045,1.085
ivc,0.011,-0.020,-0.035,1.050,-0.022,-0.015,1.260,-0.022,-0.010,1.325,-0.025,-0.015,1.315
svc,0.010,-0.028,-0.035,1.438,-0.028,-0.028,1.378
pulmonary_trunk,0.0135,0.022,-0.058,1.378,0.012,-0.030,1.405
cca_L,0.0035,0.010,-0.025,1.432,0.028,-0.018,1.515,0.030,-0.012,1.558
brainstem,0.011,0.000,0.030,1.627,0.000,0.025,1.641,0.000,0.020,1.655,0.000,0.014,1.667,0.000,0.010,1.690
cauda_equina,0.007,0.000,0.017,1.180,0.000,0.013,1.161,0.000,0.008,1.124,0.000,0.011,1.087,0.000,0.022,1.050,0.000,0.035,0.995
```

### 13.4 Vertebrae (x = 0)

```csv
# level,y,z,body_h_mm,body_w_mm,body_d_mm,disc_below_mm,canal_ap_mm,canal_w_mm,spinous_dy_mm,cord_y,cord_w_mm,cord_ap_mm
C1,0.020,1.618,10,78,45,0,30,28,30,0.024,11.5,8.5
C2,0.012,1.596,23,17,15.5,5,16,24,43,0.027,11.5,8.5
C3,0.007,1.574,14,16.5,15.5,5,14.5,23,40,0.023,12.5,8.0
C4,0.004,1.555,14,17.5,15.5,5,14,24,40,0.020,13.0,7.8
C5,0.003,1.536,13.5,18.5,16,5,14,24,42,0.019,13.5,7.7
C6,0.004,1.518,13.5,20,16.5,5,14,24,45,0.020,13.0,7.5
C7,0.010,1.500,15,22,16.5,5,14,23,57,0.026,12.0,7.5
T1,0.019,1.481,16,26,16.5,4.5,14,19,60,0.035,10.5,7.0
T2,0.028,1.461,17,27,17.5,4.5,14,17,60,0.044,9.0,6.5
T3,0.036,1.441,17.5,27,18.5,4.5,14,16,61,0.053,8.8,6.5
T4,0.042,1.420,18,27.5,20,5,13.5,15.5,62,0.060,8.5,6.5
T5,0.046,1.398,18.5,28.5,22,5,13.5,15.5,63,0.065,8.5,6.4
T6,0.049,1.376,19,30,24,5,13.5,15.5,64,0.069,8.3,6.4
T7,0.049,1.353,19.5,31,26,5,13.5,15.5,64,0.069,8.0,6.3
T8,0.046,1.329,20,32.5,27.5,5.5,14,16,63,0.067,8.0,6.3
T9,0.040,1.305,21,34,28.5,6,14,16,62,0.061,8.3,6.5
T10,0.031,1.280,22,37,29.5,6.5,14.5,17,62,0.053,8.5,7.0
T11,0.020,1.254,23,40,31,7,15,18,58,0.043,9.5,7.5
T12,0.008,1.227,24,42,32,8,16,21,58,0.031,10.0,8.0
L1,-0.004,1.197,25.5,43,33,10,17,22,68,0.021,8.0,7.0
L2,-0.013,1.161,26.5,45,34,11,17,23,70,0.013,0,0
L3,-0.018,1.124,27,48,35,12,16,23,70,0.008,0,0
L4,-0.016,1.087,27,50,35,12,16,24,70,0.011,0,0
L5,-0.005,1.050,26.5,52,35,11,17,26,65,0.022,0,0
S1,0.014,1.012,30,50,30,0,15,30,0,0.035,0,0
# L2-S1 cord_w/ap 0 = no cord (cauda equina only); cord_y there is the thecal-sac centre
```

---

## 14. Posture, breathing and heartbeat offsets; scaling to other bodies

### 14.1 Standing vs lying

| Structure | Standing (this document) → supine shift | Unit | Source |
|---|---|---|---|
| Diaphragm domes | +2 to +4 (higher when supine) | cm | [K] (M) |
| Liver, spleen | +2 to +3 | cm | [K] [B32] (M) |
| Kidneys | +2 to +4 (> 5 cm of drop on standing = nephroptosis) | cm | [K] (M) |
| Heart | +1 to +2; slightly more horizontal | cm | [K] (L) |
| Stomach greater curvature, bladder dome | +3 to +6 | cm | [K] (M) |
| Anterior abdominal wall | falls back 1–3 cm (flatter) | cm | [K] (M) |

**Game rule** `[G]`: organs are parented to trunk bones and do not slide inside the body. Posture shifts are cosmetic. Apply them only to the post-mortem pose, as an optional per-organ offset along body −Z (standing) or toward the ground (lying), blended over ~2 s when the body comes to rest.

### 14.2 Breathing and cardiac motion (to animate the living body)

| Motion | Amplitude (quiet → deep/agonal) | Rate | Notes | Source |
|---|---|---|---|---|
| Diaphragm, craniocaudal | 1.5–2 → 6–10 cm | respiratory rate (12–16/min at rest) | Domes descend on inspiration | [K] (H) |
| Liver, spleen, kidneys, stomach | 1–2 → 4–8 cm down on inspiration | same | Follow the diaphragm at ~0.7–1× its motion | [K] (M) |
| Lungs | inferior borders move with the domes; volume +0.5 L tidal → +3.7 L (FRC → TLC) | same | | [B19] (H) |
| Anterior chest wall | 3–8 mm forward and up (quiet); 2–3 cm (deep) | same | Upper ribs "pump handle" (AP), lower ribs "bucket handle" (lateral) | [K] (M) |
| Anterior abdominal wall | 5–10 mm out on inspiration | same | | [K] (M) |
| Heart, base → apex | ventricles shorten ~1–1.5 cm along u in systole; walls thicken 30–50 % | heart rate | | [B22] [K] (M) |
| Apex beat on the skin | 1–2 mm, visible in lean men at the 5th ICS MCL | heart rate | | [K] (M) |
| Carotid pulse | 0.5–1 mm at the skin | heart rate | | [K] (L) |

### 14.3 Scaling to other generated bodies

`[E] (M)`: the procedural generator will vary height, mass and build.
- **Heights and bone lengths**: multiply all z values and all bone and segment lengths by **k = H/1.78**. Multiply x and y by k as well, then apply the girth scaling below.
- **Girths, breadths and depths**: × √(W/75) × (1/√k), which keeps BMI-type proportions. Distribute the change mostly into SAT (§12). Waist and abdomen take ~2× the average change, hands, feet and head ~0.3×.
- **Organ masses**: scale with body surface area (≈ W^0.425 × H^0.725), not linearly with mass. Organ positions follow the skeleton (k).
- **Vessel diameters**: see doc 03 (× √k).
- **Female bodies** (not required now): a wider, shallower pelvis (subpubic angle 80–90°, inlet 11.5 × 13.5 cm), narrower shoulders, heart ~250 g, shorter sternum, more SAT (hips, thighs). This is a separate parameter set, not a scale factor.

### 14.4 Simulation parameters: offsets and scaling

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `diaphragm_excursion_quiet / deep` | 0.018 / 0.08 | m | | [K] (H) |
| `abdo_organ_follow_factor` | 0.8 | — | × diaphragm displacement | [K] (M) |
| `chest_wall_excursion_quiet` | 0.005 | m | Along the surface normal, upper chest | [K] (M) |
| `heart_systolic_shortening` | 0.012 | m | Along u | [K] (M) |
| `supine_shift_liver / kidney / diaphragm` | +0.025 / +0.03 / +0.03 | m | Post-mortem cosmetic only | [K] (M) |
| `scale_k` | H / 1.78 | — | | [E] |

### 14.5 Visual/behavioural checklist: motion

- A **living body always breathes**. The belly rises first, then the chest, with visible **suprasternal and intercostal tugging** in air hunger. When breathing stops (doc 04), the chest and belly go **completely still**. This is one of the clearest death cues.
- **Agonal gasps** move the jaw and neck more than the chest (doc 04).
- In lean men the apex beat and the carotid pulse can flicker in the skin. Turn both off at cardiac arrest.

---

## 15. Implementation notes (60 fps target)

`[G]` / `[E]`, based on engineering judgement rather than a source:

- **Everything in this document is static data**: about 60 landmarks, 25 vertebrae, 24 ribs, ~25 organ primitives and ~15 tube chains. Load it once, as the CSV above or GDScript `const` arrays, and cache it on the skeleton in bone-local space.
- **Hit resolution**: for each bullet or blade ray, test the organ primitives (OBB, ellipsoid, capsule chain) **in the ray's bone-local space**. That is ~100 analytic ray–primitive tests (sub-microsecond each), negligible next to physics.
  - Order the hits along the ray and hand the sequence to the wound, bleeding and neuro systems (docs 01–04).
  - Use the tissue-layer maps (§12) to give the entry depth to the first organ.
- **Rendering**: skin, muscle and bone as a few layered meshes per region, with organ meshes hidden until a wound opens a window. Show exposed tissue with a layered "cut-surface" shader (dermis → fat → fascia → muscle → bone colours from §8.3 and §12.4). No volumetric rendering is needed.
- **Physics (Jolt)**:
  - The ragdoll uses ~15 rigid bodies with the §2.2 masses and inertias.
  - Organs are **not** rigid bodies. They ride on their parent bone: heart, lungs, trachea and oesophagus on `chest`/`upper_chest`; liver, spleen, stomach, kidneys and pancreas on `spine`; bladder on `hips`.
  - Breathing and heartbeat (§14.2) are bone-local offsets or vertex animation, evaluated at 20–30 Hz. Stop them at death.
- **Procedural generation** (Blender geometry nodes or Python, or offline in Godot):
  - Vertebrae from the §13.4 table plus parametric templates.
  - Ribs as spline sweeps (§5.2).
  - Long bones as lathe profiles with sculpted ends (§6–7).
  - The skin as superellipse ring lofts through the §2.1 levels, then the §12 fat and muscle offsets.
- **Coordinate conversion** is a single mapping at export or generation: (x, y, z)_body → (x, z, −y)_Godot. Do not mix frames inside the data files.

---

## 16. QA priority list (verify these first against the cited sources)

| # | Claim | Value used | Check against |
|---|---|---|---|
| 1 | Vertex → ear canal vertical distance | 12.5 cm | ANSUR "tragion–top of head" [B1]; Farkas [B37] |
| 2 | C7 spinous tip (cervicale) height | 1.500 (surveys ~1.51–1.53) | ANSUR cervicale height [B1]; §4.6 |
| 3 | Jugular notch / sternal angle / xiphisternal levels | T2/3 / T4/5 / T9 | Mirjalili 2012 CT surface anatomy [B32] |
| 4 | Hip-joint-centre offsets from the ASIS | 30 % down, 19 % back, 36 % lateral of W | Bell 1990 [B9] |
| 5 | Long-bone lengths (femur 47, tibia 41, humerus 33.5, radius 25.5, ulna 27.5 cm) | | Trotter & Gleser [B7]; ANSUR segment lengths [B1] |
| 6 | Heart mass and size | 320 g; 12.5 × 9 × 6.5 cm | Molina & DiMaio [B17]; ICRP 89 [B43] |
| 7 | Apex position | 5th left ICS, MCL (~9 cm from the midline) | Gray's [B15]; Mirjalili [B32] (CT shows variation: 4th–6th ICS) |
| 8 | Conus tip level | L1/L2 (T12–L3) | Saifuddin 1998 [B28] |
| 9 | Cord dimensions (C5 13.5 × 7.7; T7 8 × 6.3 mm) | | Kameyama 1994 [B27]; Fradet 2014 [B26] |
| 10 | Pontomedullary junction ≈ ear-canal level | | Any MRI atlas, midsagittal plus the Frankfort plane |
| 11 | Chest-wall thickness at 2nd ICS MCL / 5th ICS AAL | ~42 / ~32 mm | Givens 2004 [B20]; Inaba 2012 [B21] |
| 12 | Liver span and mass | 14.5 cm MCL; 1,550 g | Kratzer 2003 [B23]; Molina [B17] |
| 13 | Spleen size | 12 × 7 × 4 cm, 150 g | Chow 2016 [B25] |
| 14 | Kidney size and level | 11.5 cm; T12–L3; right 2 cm lower | Emamian 1993 [B24] |
| 15 | Lung volumes | TLC 7.1, FRC 3.35 L | Quanjer 1993 [B19] |
| 16 | Vertebral body dimensions (§4.1) | | Panjabi 1991/1992 [B10–B12] |
| 17 | Segment mass fractions | | Winter 2009 Table 4.1 [B3] |
| 18 | Spinal curvature norms | | Roussouly 2005 [B13]; Legaye 1998 [B14] |

---

## 17. Suspicious content

- **None encountered.** No external page content was retrieved in this session: every WebSearch call was refused for budget and every WebFetch was blocked by egress policy, so the only responses were those error messages.
- There was therefore nothing to screen for injected instructions.
- No commands were run, nothing was downloaded, and no code was copied from the web. The only file written is this document.

---

## 18. References

All cited **from memory**; none re-opened in this session (§0.1).
- Where a stable URL is well known it is given, but it was **not** fetched.
- Bibliographic details are given so QA can find each item.

- **[B1]** Gordon CC, Blackwell CL, Bradtmiller B, et al. *2012 Anthropometric Survey of U.S. Army Personnel (ANSUR II): Methods and Summary Statistics.* Natick/TR-15/007. US Army Natick Soldier RD&E Center, 2014.
- **[B2]** Gordon CC, Churchill T, Clauser CE, et al. *1988 Anthropometric Survey of U.S. Army Personnel: Methods and Summary Statistics.* Natick/TR-89/044, 1989.
- **[B3]** Winter DA. *Biomechanics and Motor Control of Human Movement*, 4th ed. Wiley, 2009. Chapter 4 (Drillis–Contini segment-length fractions, Fig. 4.1; Dempster segment masses, COM and radii of gyration, Table 4.1).
- **[B4]** Drillis R, Contini R. *Body Segment Parameters.* Technical Report 1166.03, Office of Vocational Rehabilitation, New York University, 1966.
- **[B5]** Dempster WT. *Space Requirements of the Seated Operator.* WADC Technical Report 55-159, Wright-Patterson AFB, 1955.
- **[B6]** NASA. *Man-Systems Integration Standards* (NASA-STD-3000), Vol. I, Section 3: Anthropometry and Biomechanics, 1995. (Tried at msis.jsc.nasa.gov; host did not resolve.)
- **[B7]** Trotter M, Gleser GC. Estimation of stature from long bones of American Whites and Negroes. *Am J Phys Anthropol* 1952;10:463–514; and 1958;16:79–123.
- **[B8]** Kendall FP, McCreary EK, Provance PG, et al. *Muscles: Testing and Function with Posture and Pain*, 5th ed. Lippincott Williams & Wilkins, 2005 (ideal plumb-line alignment).
- **[B9]** Bell AL, Pedersen DR, Brand RA. A comparison of the accuracy of several hip center location prediction methods. *J Biomech* 1990;23(6):617–621.
- **[B10]** Panjabi MM, Duranceau J, Goel V, Oxland T, Takata K. Cervical human vertebrae: quantitative three-dimensional anatomy of the middle and lower regions. *Spine* 1991;16(8):861–869.
- **[B11]** Panjabi MM, Takata K, Goel V, et al. Thoracic human vertebrae: quantitative three-dimensional anatomy. *Spine* 1991;16(8):888–901.
- **[B12]** Panjabi MM, Goel V, Oxland T, et al. Human lumbar vertebrae: quantitative three-dimensional anatomy. *Spine* 1992;17(3):299–306.
- **[B13]** Roussouly P, Gollogly S, Berthonnaud E, Dimnet J. Classification of the normal variation in the sagittal alignment of the human lumbar spine and pelvis in the standing position. *Spine* 2005;30(3):346–353.
- **[B14]** Legaye J, Duval-Beaupère G, Hecquet J, Marty C. Pelvic incidence: a fundamental pelvic parameter for three-dimensional regulation of spinal sagittal curves. *Eur Spine J* 1998;7(2):99–103.
- **[B15]** Standring S (ed.). *Gray's Anatomy: The Anatomical Basis of Clinical Practice*, 42nd ed. Elsevier, 2020.
- **[B16]** Moore KL, Dalley AF, Agur AMR. *Clinically Oriented Anatomy*, 8th ed. Wolters Kluwer, 2018.
- **[B17]** Molina DK, DiMaio VJM. Normal organ weights in men: part I — the heart; part II — the brain, lungs, liver, spleen, and kidneys. *Am J Forensic Med Pathol* 2012;33(4):362–367 and 368–372.
- **[B18]** Kitzman DW, Scholz DG, Hagen PT, Ilstrup DM, Edwards WD. Age-related changes in normal human hearts during the first 10 decades of life. Part II (Maturity). *Mayo Clin Proc* 1988;63(2):137–146.
- **[B19]** Quanjer PH, Tammeling GJ, Cotes JE, et al. Lung volumes and forced ventilatory flows. Report of the Working Party, European Community for Steel and Coal. *Eur Respir J* 1993;6 Suppl 16:5–40.
- **[B20]** Givens ML, Ayotte K, Manifold C. Needle thoracostomy: implications of computed tomography chest wall thickness. *Acad Emerg Med* 2004;11(2):211–213.
- **[B21]** Inaba K, Branco BC, Eckstein M, et al. Optimal positioning for emergent needle thoracostomy: a cadaver-based study (and CT chest-wall thickness series). *J Trauma* 2011;71(5):1099–1103; Inaba K, et al. Radiologic evaluation of alternative sites for needle decompression of tension pneumothorax. *Arch Surg* 2012;147(9):813–818.
- **[B22]** Lang RM, Badano LP, Mor-Avi V, et al. Recommendations for cardiac chamber quantification by echocardiography in adults (ASE/EACVI). *J Am Soc Echocardiogr* 2015;28(1):1–39.
- **[B23]** Kratzer W, Fritz V, Mason RA, Haenle MM, Kaechele V. Factors affecting liver size: a sonographic survey of 2080 subjects. *J Ultrasound Med* 2003;22(11):1155–1161.
- **[B24]** Emamian SA, Nielsen MB, Pedersen JF, Ytte L. Kidney dimensions at sonography: correlation with age, sex, and habitus in 665 adult volunteers. *AJR Am J Roentgenol* 1993;160(1):83–86.
- **[B25]** Chow KU, Luxembourg B, Seifried E, Bonig H. Spleen size is significantly influenced by body height and sex: establishment of normal values for spleen size at US with a cohort of 1200 healthy individuals. *Radiology* 2016;279(1):306–313.
- **[B26]** Fradet L, Arnoux PJ, Ranjeva JP, Petit Y, Callot V. Morphometrics of the entire human spinal cord and spinal canal measured from in vivo high-resolution anatomical MRI. *Spine* 2014;39(4):E262–E269.
- **[B27]** Kameyama T, Hashizume Y, Ando T, Takahashi A. Morphometry of the normal cadaveric cervical spinal cord. *Spine* 1994;19(18):2077–2081.
- **[B28]** Saifuddin A, Burnett SJ, White J. The variation of position of the conus medullaris in an adult population: a magnetic resonance imaging study. *Spine* 1998;23(13):1452–1456.
- **[B29]** Abe T, Kondo M, Kawakami Y, Fukunaga T. Prediction equations for body composition of Japanese adults by B-mode ultrasound. *Am J Hum Biol* 1994;6(2):161–170 (site muscle and fat thicknesses).
- **[B30]** Jackson AS, Pollock ML. Generalized equations for predicting body density of men. *Br J Nutr* 1978;40(3):497–504.
- **[B31]** Oltulu P, Ince B, Kökbudak N, Findik S, Kiliç F. Measurement of epidermis, dermis, and total skin thicknesses from six different body regions with a new ethical histometric technique. *Turk J Plast Surg* 2018;26(2):56–61; and Lee Y, Hwang K. Skin thickness of Korean adults. *Surg Radiol Anat* 2002;24(3–4):183–189.
- **[B32]** Mirjalili SA, McFadden SL, Buckenham T, Stringer MD. A reappraisal of adult thoracic surface anatomy. *Clin Anat* 2012;25(7):827–834; and Mirjalili SA, et al. A reappraisal of adult abdominal surface anatomy. *Clin Anat* 2012;25(7):844–850.
- **[B33]** Gilad I, Nissan M. A study of vertebra and disc geometric relations of the human cervical and lumbar spine. *Spine* 1986;11(2):154–157.
- **[B35]** Pheasant S, Haslegrave CM. *Bodyspace: Anthropometry, Ergonomics and the Design of Work*, 3rd ed. CRC Press, 2006.
- **[B36]** Aldrich W. *Metric Pattern Cutting for Menswear*, 5th ed. Wiley-Blackwell, 2011 (nape-to-waist and body-block measurements).
- **[B37]** Farkas LG. *Anthropometry of the Head and Face*, 2nd ed. Raven Press, 1994.
- **[B38]** Howells WW. *Cranial Variation in Man.* Papers of the Peabody Museum 67, Harvard University, 1973 (basion–bregma and cranial dimensions); plus standard cephalometric norms (S–N, S–Ba, cranial base angle).
- **[B39]** Weaver AA, Schoell SL, Stitzel JD. Morphometric analysis of variation in the ribs with age and sex. *J Anat* 2014;225(2):246–261; Holcombe SA, Wang SC, Grotberg JB. Modeling female and male rib geometry with logistic curves. *Ann Biomed Eng* 2016;44(10):2980–2990.
- **[B40]** Kemper AR, McNally C, Kennedy EA, et al. Material properties of human rib cortical bone from dynamic tension coupon testing. *Stapp Car Crash J* 2005;49:199–230.
- **[B43]** ICRP. *Basic Anatomical and Physiological Data for Use in Radiological Protection: Reference Values.* ICRP Publication 89. *Ann ICRP* 2002;32(3–4). (Reference Adult Male 176 cm / 73 kg; organ masses.) See also ICRP Publication 110 (2009), Adult Reference Computational Phantoms.
- Sibling documents: `01_gunshot_wounds.md` [D01], `02_sharp_blunt_burn.md` [D02], `03_bleeding_vessels.md` [D03], `04_neuro_death_eyes.md` [D04], in this folder.
