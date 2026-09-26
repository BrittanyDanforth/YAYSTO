# 02 — Non-gunshot injury morphology: sharp force, blunt force, burns

Project: **Gore Head** (Godot 4.5, Forward+, Jolt). Research input for the damage, bleeding and appearance systems.
Scope: knife (incised, stab), fist, hammer and torch on a fictional, procedurally generated adult. Firearms are covered in a separate document.
Audience: engineers and technical artists who turn these numbers into simulation parameters, shaders and decals.

---

## 0. Read this first: method, confidence tags, conventions

### 0.1 How this was researched (and its limits)

- All sources were found through web search. **Direct page fetching (WebFetch) was blocked** by the environment's egress proxy for every domain tried (Medscape, PMC/NCBI, PubMed, forensicmed.co.uk, PathologyOutlines, Wikipedia, Radiopaedia, ACEP Now). So the numbers below come from the search engine's extracts and summaries of the cited pages, not from reading the full text.
- The search budget ran out partway through the burns section. The rest of that section relies more on the author's own clinical/forensic knowledge and is tagged as such.
- **Before a number becomes a hard-coded constant, QA should open the cited URL and check it.** The load-bearing values are listed in §9.

### 0.2 Confidence tags used in every table

| Tag | Meaning |
|---|---|
| `[S:Rn]` | Sourced. Rn is an entry in the reference list (§11). |
| `[K]` | Author's own medical/forensic knowledge. No source was retrieved in this session. Standard textbook material, but unverified here. |
| `[E]` | Engineering estimate or derivation: a model fitted to sourced data, or a design value chosen to look right. The table notes say what it rests on. |

### 0.3 Colour conventions

- Hex values are **authored approximations** `[K]` for light-to-medium skin (roughly Fitzpatrick II–III) under neutral daylight (D65). They are *overlay/target* colours, not measured spectra. For dark skin (Fitzpatrick V–VI), bruises look darker purple-brown to near black, erythema and yellow stages are much harder to see, and abrasions look grey-pink. The literature notes that skin tone strongly affects how bruise colour is perceived [S:R25, R26].
- Blood colours: arterial #C4161C, venous #7A0A10, fresh clot #5A0A0E, dried film #3B1512 `[K]`. The full palette is in §7.

### 0.4 Time scales

Several processes (bruise colour, abrasion scab, blister growth, raccoon eyes) take **hours to weeks**. Give each lesion an `age` value and let the game run a *time-scale multiplier* (real time, or accelerated such as 1 real s = 1 game h) so players can see the evolution. **After death, vital processes stop** (§2.8): no new bruising, no swelling, no scab formation, no colour ageing of bruises beyond minor diffusion.

---

## 1. Shared tissue reference (head, face, neck)

These are the layer thicknesses and vessel sizes that the sharp, blunt and burn depth models below all index into.

### 1.1 Layers

- **Scalp** has five layers (Skin, dense Connective tissue, Aponeurosis/galea, Loose areolar tissue, Pericranium). The first three are bound together and move as one unit over the loose areolar plane [S:R16]. Skin is about **3.5–5.5 mm** [S:R16]; the dense subcutaneous layer is about **1.5 mm** [S:R16]; the galea is **1–2 mm**, inelastic [S:R16]. Total scalp thickness to bone is about **5–8 mm** `[K]`.
- **Skull (calvaria) thickness, CT** [S:R17]: frontal **5.8–8.0 mm**, parietal **5.4–7.0 mm**, occipital **8.0–8.6 mm**, temporal **4.7 mm mean**, and the temporal squama can be as thin as **~2.1 mm** [S:R17]. There is an outer table, a diploë (cancellous, red marrow) and an inner table `[K]`.
- **Orbital floor** is about **0.5 mm**; the medial wall (lamina papyracea) is about **0.25 mm** [S:R44].
- **General skin** is **0.5–4 mm** depending on site [S:R8]. Eyelid skin is the thinnest at about **0.5 mm** `[K]`; facial skin is about **1.5–2.5 mm** `[K]`.
- **Facial soft tissue to bone**, as used in forensic facial reconstruction `[K]`, approximating the Stephan tallied tables [R86]: glabella 5–6 mm, nasion 6–7 mm, rhinion (lower nasal bridge) 2–3 mm, supraorbital ridge 5–7 mm, zygion (cheekbone) 5–8 mm, mid-philtrum 10–12 mm, chin/pogonion 10–12 mm, mid-cheek over masseter 15–25 mm, gonion (jaw angle) 10–15 mm. Where the depth is small (eyebrow, cheekbone, nasal bridge, chin, scalp), skin is crushed against bone and **split lacerations** happen (§3.4).

### 1.2 Vessels relevant to these weapons

- **Superficial temporal artery**: diameter **1.7 ± 0.4 mm** (trunk) to **2.2–2.3 mm** (frontal/parietal branches). Physiological flow is about **16–18 mL/min** per branch [S:R19].
- **Facial artery**: about 2–3 mm, running tortuously from the jaw margin in front of the masseter to the corner of the mouth and the side of the nose `[K]`. **Labial arteries** lie inside the lips, about 1 mm across, close to the mucosa `[K]`.
- **Internal jugular vein (IJV)**: usually **< 2 cm** under the skin; mean right IJV diameter **11.5 mm** [S:R18]. The common carotid lies deeper and medial to the IJV [S:R18]. The **external jugular vein** lies just under the platysma, about 3–6 mm deep `[K]`.
- **Face and scalp** keep high, fairly constant skin blood flow with **little cold-induced vasoconstriction** [S:R20]. Scalp vessels are **tethered in dense connective tissue, so they cannot retract or constrict** when cut, which is why scalp wounds bleed so much [S:R15].

### 1.3 Simulation parameters: tissue reference

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| scalp_skin_thickness | 3.5–5.5 | mm | Hair-bearing skin | [S:R16] |
| scalp_dense_subcut | ~1.5 | mm | Vessels tethered here | [S:R16] |
| galea_thickness | 1–2 | mm | Inelastic sheet, pulled front-to-back by frontalis/occipitalis | [S:R16, R7] |
| scalp_total_to_bone | 5–8 | mm | Use 6 mm default | [K] |
| skull_frontal | 5.8–8.0 | mm | Use 7 mm | [S:R17] |
| skull_parietal | 5.4–7.0 | mm | Use 6 mm | [S:R17] |
| skull_temporal_squama | 2.1–4.7 | mm | Thinnest; fractures and penetrates first | [S:R17] |
| skull_occipital | 8.0–8.6 | mm | Thickest | [S:R17] |
| orbital_floor | 0.5 | mm | Blowout site | [S:R44] |
| medial_orbital_wall | 0.25 | mm |  | [S:R44] |
| eyelid_skin | ~0.5 | mm | Bruises and swells the most | [K] |
| face_skin | 1.5–2.5 | mm |  | [K] |
| soft_tissue_eyebrow / cheekbone / chin | 5–7 / 5–8 / 10–12 | mm | Anvil sites for splits | [K], R86 |
| soft_tissue_mid_cheek | 15–25 | mm | Full-thickness cheek cut opens into the mouth | [K] |
| STA_diameter | 1.7–2.3 | mm |  | [S:R19] |
| STA_flow_physiological | 16–18 | mL/min | Per branch | [S:R19] |
| IJV_depth | < 20 | mm |  | [S:R18] |
| IJV_diameter | 11.5 (can be < 5) | mm |  | [S:R18] |
| EJV_depth | 3–6 | mm | Beneath platysma | [K] |

**Visual/behavioural checklist**
- Scalp wounds that reach the galea show a white, glistening fibrous layer (#E8E4DC); below the loose areolar layer is the ivory skull with a thin pink periosteum.
- Forehead, eyebrow, cheekbone, nasal bridge and chin have thin cover over bone, so the same blow splits skin there and only bruises the mid-cheek.
- Temporal squama (the side of the head above the ear) is visibly the weak point: fractures and knife points get through there first.

---

## 2. Sharp force injuries (knife)

### 2.1 Classification

- **Incised wound (cut, slash)**: the edge is drawn tangentially across the skin. **Longer than deep** [S:R1].
- **Stab wound**: the point is driven roughly perpendicular to the skin. **Deeper than long** [S:R1].
- **Chop wound**: a heavy edged implement (axe, cleaver). Deep and gaping, with straight margins, often an abraded margin on one side, and a cut groove or comminuted fracture of the bone beneath [S:R84]. This is not a player weapon; it is listed so the knife never produces this morphology.

### 2.2 Incised wound morphology

- **Margins**: clean, straight, sharp-edged, **not abraded, not bruised** `[K]` [S:R2]. Every layer is divided at the same level `[K]`.
- **No tissue bridging**: vessels, nerves and fibrous strands in the depth are **cleanly severed**. Tissue bridges are the pathognomonic sign of a *laceration* and distinguish it from a cut [S:R31]. Hairs along the line are cut through, not crushed `[K]`.
- **Tailing**: the wound starts deeper and ends shallow, with a drawn-out tail. **The tail shows the direction of the stroke** (the tail is at the end) [S:R3]. Tail length is typically **5–30 mm** `[K]`. Several superimposed passes produce several tails or skin tags at one end `[K]`.
- **Ends**: both ends are acute, V-shaped `[K]`.
- **Bleeding**: **profuse even in small incised wounds**, because cleanly cut vessels are not crushed or twisted and so clot poorly. Lacerations bleed less, except on the scalp [S:R14].
- **Slash-attack epidemiology**: most knife-assault victims who reach hospital have slash-type wounds, **mainly to the face**, fewer to the upper limb and trunk; only **11%** have multiple wounds [S:R12]. Of slashing strokes, **23% are single long strokes and 31% single short strokes**; the rest are mixed [S:R12]. A documented cheek slash was about **12 cm** long [S:R12].

### 2.3 Gaping (how far a cut opens)

What is known:
- Skin sits under anisotropic resting tension (Langer's cleavage lines). Wounds **perpendicular to the lines gape widely**; wounds parallel to them stay slit-like and close up easily [S:R5, R6]. Langer mapped this by cutting out **30 mm circles**, which became ellipses: they shrank along the tension direction and elongated across it [S:R6].
- **Scalp**: if the galea is cut **transversely** (at right angles to its front-to-back pull by frontalis and occipitalis), the wound gapes; cuts that do not divide the galea gape little [S:R7]. Galeal wounds ≥ 0.5 cm are surgically repaired [S:R7].
- At autopsy, gaping wounds are re-apposed with tape, and it is the re-apposed dimensions that are interpreted [S:R4].
- **Antemortem wounds gape more than postmortem wounds**, and their edges become everted and swollen [S:R22].

What is not in the literature I found: no source gave gape widths in mm for face, scalp or neck cuts. The model below is an **engineering estimate `[E]`** consistent with the qualitative sources and with typical clinical experience `[K]` (for example, a 4 cm forehead laceration running across the tension lines through the full dermis gapes roughly 5–10 mm).

**Gape model `[E]`** (lens-shaped: maximum at the midpoint, zero at the ends):
```
gape_max_mm = L_mm * G(theta) * f_depth * f_region
G(theta)    = G_par + (G_perp - G_par) * sin^2(theta)     // theta = angle between cut and local tension line
G_par ≈ 0.03–0.05 ; G_perp ≈ 0.15–0.25
f_depth: epidermis only = 0 ; partial dermis = 0.3 ; full dermis = 1.0 ; through galea/platysma/muscle across fibres = 1.3–1.6
f_region: face 1.0 ; forehead 1.0 ; scalp (galea cut transversely) 1.5 ; scalp (galea intact) 0.4 ; neck 1.2 (×1.5 when head extended) ; lips/eyelids 0.7 (loose tissue)
clamp gape_max_mm to 25 mm (face/scalp), 40 mm (neck)
```
Worked examples `[E]`: a 40 mm cut through the dermis perpendicular to the lines gapes about 6–10 mm, and 1–2 mm parallel to them. A 60 mm coronal (side-to-side) scalp cut through the galea gapes about 12–20 mm. A transverse throat cut through the platysma gapes about 10–25 mm, more with the neck extended.

Gape appears **immediately**, within under 1 s of the blade passing, as elastic recoil `[K]`. Antemortem edges then swell over minutes to hours, which slightly everts them `[K]` [S:R22].

### 2.4 Depth per stroke and what it reaches

- Slash wounds are typically long and superficial [S:R12].
- Skin is by far the most resistant layer. **Once the skin is breached, little further force is needed** to go through fat, muscle and organs, unless the blade meets bone or calcified cartilage [S:R8].
- **Cut-throat series** (74 autopsies): skin, platysma and **external jugular veins were involved in every case**; larynx, trachea, carotid and IJV in **91.9%**. Deaths were from **exsanguination (~50%)**, **aspiration of blood (36.5%)** and **air embolism** through open jugular veins (19 cases in one series) [S:R13]. This is a fatal-case series, so it over-represents deep cuts.

Game depth tiers `[E]` (normal blade force; scale by blade sharpness and angle):

| Tier | Depth | Face/forehead reaches | Scalp reaches | Neck reaches |
|---|---|---|---|---|
| Scratch / light drag | 0.2–1 mm | Epidermis to papillary dermis: red line, beads of blood | Same | Same |
| Light cut | 1–3 mm | Full dermis; yellow fat visible in the gape | Dermis | Dermis |
| Moderate slash | 3–8 mm | Subcutaneous fat and facial muscles; can cut facial artery branches and labial artery | Galea (it gapes); knife scores periosteum | Platysma, EJV (dark steady venous bleeding) |
| Hard slash | 8–25 mm | Cheek full thickness into the mouth at 15–25 mm; parotid; facial nerve branches | **Stops at bone**: outer table scored, not cut through | IJV (< 20 mm), then larynx/trachea, then carotid (deeper, medial) |

Bone rule `[K]`: a knife scores or notches the skull's outer table but does not cut through adult calvaria. A forceful **stab** can penetrate the **temporal squama (2–5 mm)** or the orbital roof or medial wall.

### 2.5 Stab wounds

- **Shape**: single-edged blade gives one **acute** end and one **squared-off (blunt) or split "fish-tail"** end; a double-edged blade gives **both ends acute** (spindle-shaped) [S:R10]. A fish-tail also appears when the knife is rotated in the wound [S:R10].
- **Length vs blade width**: skin wound length is **up to ~2 mm shorter** than blade width because of elastic recoil [S:R4, R8]. It becomes **longer** than the blade width if the blade is rocked or withdrawn at an angle (the "cutting on withdrawal" component) `[K]`.
- **Gaping**: a stab across the tension lines opens into an ellipse; one parallel to them stays a slit [S:R4]. Default ellipse width is 20–40% of length across the lines and 5–10% along them `[E]`.
- **Track depth can exceed blade length** where tissue compresses (abdomen, anterior chest wall, and slightly the cheek), because the wall is driven in by the thrust [S:R9].
- **Force to penetrate**: bare skin needs **~10–20 N** with a sharp tip [S:R8, Irish Examiner summary]. Instrumented cadaver work found a **mean skin penetration force of ~49.5 N**, with **initial peaks of ~55 N** [S:R8]. The **sharpness of the tip is the main factor** [S:R8]. **Screwdrivers and closed scissors need about 3× more** [S:R8]. Skin **tents about 0.2–2 mm (mean about 1 mm)** before puncture [S:R8, patent-level source: low confidence].
- **Hilt/guard mark** `[K]`: a full-depth thrust can leave a patterned abrasion or bruise from the guard next to the wound.

### 2.6 Bleeding character by region

- **Scalp**: highly vascular. Even "minor" lacerations can lead to profound blood loss and shock, because vessels held open by dense connective tissue cannot constrict [S:R15]. If the patient is already hypotensive the wound may seem to bleed little, then **bleeds profusely again as blood pressure recovers** [S:R15]. A fatal case had a **10 cm plus a 4 cm scalp laceration**, and death was attributed to anaemia alone [S:R15]. A hammer case with **dozens of weak blows produced multiple scalp lacerations and no skull fracture, with death from scalp haemorrhage** [S:R55].
- **Face**: high, non-constricting blood flow [S:R20]. Brisk bleeding, but capillary and small venous bleeding stops within minutes. Named arteries (STA, facial, labial) bleed as pulsatile jets from **both** cut ends, because facial arteries anastomose richly across the midline and between branches `[K]`.
- **Small skin cuts** (capillary level): normal skin bleeding time is **1–9 min** (Ivy < 5–8 min) [S:R21].
- **Neck veins**: when the head is above the heart, venous pressure can be sub-atmospheric. An opened jugular vein held open by its fascial attachments can **suck in air on inspiration**, causing venous air embolism: a gurgle or hiss, frothy blood, and sudden cardiovascular collapse [S:R13, R18-family sources] `[K]`.

Bleeding-rate defaults `[E]` (initial rates at normal blood pressure; scale with MAP/90 for arteries and with venous pressure for veins; cross-reference the vascular/physiology document):

| Wound | Initial rate | Character | Self-limits? |
|---|---|---|---|
| Abrasion / scratch | 0.01–0.1 mL/min | Pinpoint beads merging into a film plus serum | Yes, 1–9 min [S:R21] |
| 3 cm dermal cut, face | 1–5 mL/min | Welling from the edges, runs downhill | Mostly, 5–15 min `[K]` |
| 5–10 cm scalp laceration through galea | 20–100 mL/min total | Several pulsatile points plus a sheet ooze | **Poorly**: vessels tethered [S:R15]. 500–1500 mL over 30–60 min is plausible if untreated `[E]` |
| Transected STA branch | 20–60 mL/min (both ends) | Pulsatile jet, bright red, jet 10–50 cm at normal BP (low confidence) | Slowly; retracts poorly in scalp |
| Facial / labial artery | 10–40 mL/min | Pulsatile; labial bleeds into the mouth as well | Partially |
| External jugular | 10–50 mL/min | Dark, steady; air entry possible | No |
| IJV / carotid | Hundreds of mL/min | Use the vascular document's values | No |

The last row's scale: physiological STA flow of 16–18 mL/min [S:R19]; open-ended arterial flow with distal resistance removed can exceed physiological flow `[E]`.

### 2.7 Hesitation marks and defence wounds

- **Hesitation (tentative) marks**: multiple, superficial, roughly **parallel** incised wounds of varying depth, clustered in a small area (low dispersion). Typical sites are the front of the wrists, the neck and the left chest [S:R3]. They are present in **> 70%** of sharp-force suicides [S:R3]. Typical count is about 3–15 `[K]`. In game terms, repeated light passes by the player should render as clustered parallel superficial cuts, which is the forensically correct look for repeated shallow strokes.
- **Defence wounds** (relevant if the full-body character is conscious and has working arms):
  - Present in **~41–48%** of homicidal sharp-force victims (literature range 15–61%) [S:R11].
  - Sites: **hands 80%, forearms 65%, fingers 40%** of those with defence injuries. They are **incised in 52–60%**, with the rest chop wounds and abrasions. Usually one side, **left more often (70% unilateral)** [S:R11].
  - Pattern `[K]`: *grasping the blade* gives palmar and finger incised wounds, often across the finger creases. *Warding off* gives cuts and stabs on the back and ulnar side of the forearm and on the back of the hand. Defence wounds are more dispersed than hesitation marks [S:R3].

### 2.8 Antemortem vs postmortem wounds (rule for the dead body)

- **Antemortem**: bleeds freely; firm, rubbery, adherent clot; everted, swollen edges; vital reaction (inflammation); bruising possible [S:R22].
- **Postmortem**: **no active bleeding**, only passive gravity drainage; minimal edge gaping; **no vital reaction**; soft "currant jelly" or "chicken fat" clots at most; **no new bruising**, because blood no longer circulates or clots normally [S:R22].

### 2.9 Simulation parameters: sharp force

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| incised_len_gt_depth | true | bool | Classification rule | [S:R1] |
| stab_depth_gt_len | true | bool | Classification rule | [S:R1] |
| skin_penetration_force_knife | 10–55 (default 30) | N | Sharp tip about 10–20; cadaver mean 49.5 | [S:R8] |
| penetration_force_blunt_tip_mult | 3 | × | Screwdriver/scissors vs knife | [S:R8] |
| skin_tenting_before_puncture | 0.2–2 (mean 1) | mm | Low-confidence source | [S:R8] |
| stab_len_minus_blade_width | 0 to −2 | mm | Elastic recoil | [S:R4, R8] |
| stab_ellipse_width_ratio (perp / par) | 0.2–0.4 / 0.05–0.1 | × length | Gaping ellipse | [E] |
| stab_track_overshoot_compressible | up to +50 | % of blade | Abdomen/chest wall; face ~0–10% | [S:R9], [E] |
| gape_G_perp / G_par | 0.15–0.25 / 0.03–0.05 | mm per mm length | See gape model | [E] |
| gape_region_mult_scalp_galea_cut | 1.5 | × | Transverse galea cut gapes | [S:R7], [E] |
| gape_onset_time | < 1 | s | Elastic recoil | [K] |
| tail_length | 5–30 | mm | Shallow end marks stroke direction | [S:R3], [K] |
| slash_single_long / single_short | 23 / 31 | % of attacks | For AI or animation variety | [S:R12] |
| capillary_bleeding_time | 1–9 | min | Normal haemostasis | [S:R21] |
| scalp_lac_bleed_rate_initial | 20–100 | mL/min | Poor self-limitation | [S:R15], [E] |
| STA_cut_bleed_rate | 20–60 | mL/min | Both ends; pulsatile | [S:R19], [E] |
| EJV_cut_bleed_rate | 10–50 | mL/min | Dark, steady; air-entry flag when head is above the heart | [K], [E] |
| cut_throat_structures_skin_platysma_EJV | 100 | % (fatal series) | Deep structures 91.9% | [S:R13] |
| cut_throat_death_split | exsang 50 / aspiration 36.5 / air embolism (minor) | % | | [S:R13] |
| hesitation_marks_in_suicide | > 70 | % | Parallel, clustered | [S:R3] |
| defence_wounds_present | 41–48 (15–61) | % of homicidal SFI | | [S:R11] |
| defence_sites hands/forearms/fingers | 80 / 65 / 40 | % | Of cases with defence wounds | [S:R11] |
| postmortem_active_bleeding | 0 | mL/min | Gravity drainage only | [S:R22] |
| postmortem_gape_mult | 0.5 | × | "Minimal edge separation" | [S:R22], [E] |

**Visual/behavioural checklist (sharp)**
- A cut opens **instantly** into a lens-shaped gap. It is wide across tension lines and a thin line along them. Scalp cuts that divide the galea spring open wide; coronal (side-to-side) scalp cuts gape the most.
- Edges are **razor-straight and clean**: no grazed rim, no bruising, no strands across the floor, cut hairs. The floor shows the layers in order: white-pink dermis, then **lobulated yellow fat** (#F2D16B), then red-brown muscle or white galea/periosteum.
- Blood **wells from the whole length within 1–3 s** and beads, then runs downhill. Cut arteries **spurt in time with the heartbeat** (bright red). Neck veins pour dark blood steadily and may **hiss or gurgle and froth** on inspiration.
- The end of the stroke tapers into a **shallow tail**, so the stroke direction can be read.
- Stabs: a slit with **one sharp and one square or fish-tailed end** (single-edged knife). Short and slit-like along the lines, an open ellipse across them.
- Scalp cuts **keep bleeding** and soak the hair (matted, glossy, dark). Face cuts bleed briskly, then slow over minutes.
- On a dead body, new cuts **do not bleed or spurt**; they only drip under gravity, and edges gape less.
- Audio `[K]`: a soft skin "tick" or give at puncture on a stab; wet spatter on arterial jets; gurgling respiration with blood in the airway.

---

## 3. Blunt force: soft tissue (abrasions, contusions, swelling, lacerations, punches)

### 3.1 Abrasions

- **Definition**: loss of superficial epidermis by friction or scraping; deeper ones reach the papillary or reticular dermis [S:R30].
- **Types** [S:R83, R30]:
  - *Scratch*: linear, narrow at the start and broader at the end, with loosened epidermis heaped at the end showing direction.
  - *Graze/brush*: broad, tangential, parallel striations, epidermal **tags at the terminal end** showing direction.
  - *Pressure/impact (patterned)*: imprints the object's shape. A hammer face leaves a ring or square; knuckles leave a row of small ovals; a pressure abrasion needs minimal force.
- **Fresh appearance**: bright red and moist, with **pinpoint bleeding from the dermal papillae** and clear or yellow **serum ooze** [S:R30].
- **Age timeline** (gross appearance, autopsy series) [S:R29]:
  - Bright red: < 12–24 h.
  - Reddish scab: 10–32 h.
  - Brownish scab: 16.5–72 h.
  - Dark brown scab: 35.5–157 h.
  - **Black scab only after 72 h**.
  - Scab complete within **24–48 h in 93%**.
  - **Scab falls off at 7–10 days**, leaving pink/hypopigmented skin; fully exposed hypopigmented skin by > 2 weeks.
  - Microscopy: cell infiltration at 4–6 h; three-layer structure at 12 h; epithelial regeneration at the periphery by about 48 h [S:R29].
- Minutes-scale behaviour `[K]`: a skin scuff first looks pale or whitish (shredded epidermis), reddens within seconds, beads with pinpoint blood within 10–60 s, glazes with serum over 5–30 min, and starts to dry and darken after about 30–120 min.

### 3.2 Contusions (bruises): development and colour timeline

**Development**
- Visibility delay runs from **minutes to 48 h or more** depending on depth. Superficial bruises show almost at once; deep ones can take **1–2 days** to surface [S:R27]. Forensic practice re-examines at 48 h [S:R27].
- **Blood migrates under gravity**: a bruise can appear some centimetres below the impact point days later [S:R27]. For example, a forehead or scalp impact tracks down into the eyelids (a black eye with no direct eye blow) `[K]`.
- **Lax tissue bruises more** (eyelids, cheeks, genitals); dense fibrous tissue (palms, soles, scalp over galea) bruises less. Older and thinner skin bruises more easily [S:R28 family, R26].
- **Force does not reliably predict bruise appearance** in controlled human studies [S:R28]. In game terms, treat bruise size and darkness as a noisy function of energy and local tissue laxity, not a deterministic one.
- **Patterned bruises**:
  - *Rod or cane* gives a **tramline**: two parallel bruise lines with a pale centre [S:R33].
  - *Knuckles* give **grouped round bruises** in a row [S:R35].
  - *Hammer face* gives a circular or square bruise or abrasion, often a ring `[K]`.

**Colour sequence**
- Chemistry: haemoglobin (red to blue-purple), then **biliverdin (green)**, then **bilirubin (yellow)**, then **haemosiderin (golden-brown)** [S:R25].
- Textbook timeline used for colorimetric scales [S:R25]: **red 0–2 d; blue/purple 2–5 d; green 5–7 d; yellow 7–10 d; brown 10–14 d**.
- Evidence-based caveat, the main constraint for the sim: in Langlois & Gresham (369 photographs of 89 subjects), **a bruise with yellow in it was > 18 h old**; red, blue and purple can appear **at any time from 1 h until resolution (up to 21 days)**; yellow appeared **faster in under-65s** [S:R23]. Yellow **generally shows at 24–72 h** [S:R24]. Other authors put yellow at 7 days to 2 weeks [S:R24]. Perception of yellow varies between observers and declines with observer age [S:R23, R24].
- Resolution: small bruises in about 1–2 weeks; large or deep haematomas in weeks to more than a month [S:R26-family (R26, clinical sources)].

**Game colour model `[E]`** (satisfies the sourced constraints). A bruise has `blood_volume`, `depth`, `age_h`, and a radial coordinate r from 0 (centre) to 1 (edge):

| Age | Centre colour | Edge colour | Notes |
|---|---|---|---|
| 0–0.5 h | Faint pink-red flush #E07A6E (erythema) | none | Plus swelling (§3.3) |
| 0.5–6 h | Red-purple #9E3350 | Red #C0485A | Superficial bruises only; deep ones stay invisible |
| 6–48 h | Dark purple / blue-purple #5A3F7A | Red-purple #8E3B5E | Darkest at about 12–36 h. Deep bruises start surfacing (fade in over 24–48 h) |
| ≥ 18 h (hard minimum), typical 24–72 h | Blue-purple | **Yellow-green rim #B5B04E starts** | **Never render yellow before 18 h** [S:R23] |
| 2–5 d | Blue #3E4A7A to purple | Green #7D8F4E | |
| 5–7 d | Green-blue fading | Yellow #D8C06A | |
| 7–10 d | Yellow-green | Yellow-brown #B89A5A | |
| 10–14 d | Pale brown / haemosiderin #A07850 | Fading into skin | |
| 14–21 d | Gone (alpha to 0) | | Large haematomas persist longer |

Implementation: per-texel `age_eff = age_h * rate`, with `rate = 1.0 ± 0.3` random per bruise, ×1.3 for young skin. Edges age about 1–2 days ahead of the centre, because thin blood at the periphery is cleared first `[K]`. Colour saturation and alpha scale with `blood_volume` and fall with `depth`.

### 3.3 Swelling and haematoma (non-scalp)

- Head/forehead "goose egg": **visible within 1–5 min**, **peaks over the first 24 h** [S:R50].
- Black eye (periorbital haematoma): swelling **peaks within about 48 h**, can close the eye, and heals in **2–3 weeks**. Colours: red/black/dark purple on days 1–2, blue or dark purple on days 3–5, green then yellow on days 6–10 [S:R53]. A direct-trauma black eye appears **within 24 h** and **can cross the tarsal plate**. Compare raccoon eyes (§5.5) [S:R52].
- No sourced mm values were found for swelling heights. Design values `[K]/[E]`:

| Site | Swelling magnitude | Time to 50% | Peak | Resolution |
|---|---|---|---|---|
| Upper/lower eyelid | +5–15 mm thickness. The eye closes when upper-lid swelling exceeds about 8 mm (palpebral fissure 8–11 mm) | 10–30 min | 24–48 h | 1–2 wk |
| Lips | ×1.5–2 thickness | 10–30 min | 12–24 h | 3–7 d |
| Forehead / scalp goose egg | Dome 2–6 cm diameter, 0.5–2.5 cm high | 1–5 min onset [S:R50] | 24 h [S:R50] | 1–2 wk |
| Cheek over zygoma | +5–15 mm | 30–60 min | 24–48 h | 1–2 wk |
| Nose | +3–8 mm each side; hides deformity [S:R46] | 10–30 min | 24–72 h | Reassess at 3–5 d [S:R46] |

Swelling curve `[E]`: `S(t) = S_hem * (1 - exp(-t/τ1)) + S_oed * (t/T_peak) * exp(1 - t/T_peak)` with τ1 = 3–10 min (bleeding into the tissue) and T_peak = 24–48 h (oedema). The damped oedema term decays with a half-life of about 2–4 days.

### 3.4 Lacerations (blunt tears)

- **Mechanism**: skin is crushed between the object and bone (the "anvil") and **splits sideways** [S:R31, R34]. They happen mostly where skin lies directly on bone: **scalp, eyebrow, cheekbone, nose bridge, chin, back of the hand, shin** [S:R31, R35].
- **Morphology** [S:R31]:
  - **Irregular, ragged edges**.
  - **Abraded and bruised margins**; the abrasion marks the point of impact.
  - **Undermined edges**.
  - **Tissue bridges** (small vessels, nerves, fibrous bands) spanning the depth. This is **pathognomonic** and the key distinction from incised wounds.
  - Hair bulbs crushed and hairs intact across the wound `[K]`.
- **Split lacerations** over bone with little crushing can look like incised wounds (a linear split), especially on the scalp, eyebrows and shin. Look for tissue bridges and an abraded margin [S:R31].
- **Shape vs object** [S:R32]: rounded blunt end gives a **stellate** (star) tear; **edged blunt object such as a hammer gives a crescentic** tear; flat surface gives an irregular, ragged or **Y-shaped** tear; long thin object (rod, pipe) gives a **linear** tear.
- **Facial sites** with reproducible laceration patterns under blunt force: **forehead, both superior orbital rims (eyebrows), nose, perimaxillary region, chin** [S:R35].
- **Bleeding**: less than an incised wound of the same size, because vessels are torn, twisted and crushed, **except on the scalp**, where they bleed heavily [S:R14, R15].
- **Force** (porcine scalp over skull, drop tower): **minimum ~4,000 N for laceration**. Skull damage also needed > 4,000 N with most implements. **The scalp tolerates dispersed force better than localized force** [S:R34].

### 3.5 Punches (fist)

**Forces and energies**
- **Olympic boxers** (gloved, Hybrid III dummy): **3427 ± 811 N**, hand velocity **9.14 ± 2.06 m/s**, effective mass **2.9 ± 2.0 kg**, head acceleration **58 ± 13 g**, rotational acceleration **6343 ± 1789 rad/s²** [S:R36]. Derived kinetic energy is about **120 J** `[E]`.
- **Untrained adults**: roughly **500–1,500 N**; trained amateurs about 2,500 N; elite above 5,000 N [S:R37, low-quality calculator sources; use as ballpark only]. Derived untrained energy is about 15–60 J (effective mass 1–2 kg, v 5–8 m/s) `[E]`.

**Comparison with thresholds** (details in §4.1): nasal bones fracture at about **111–334 N**; lateral mandible body at **600–700 N**; zygoma at **~900–2000 N**; frontal bone needs about 2–7 kN. So **one untrained punch can break the nose or the jaw's side**, trained punches can break the cheekbone, and bare fists **essentially never fracture the forehead**.

**Clinical anchors**
- In **one-punch assaults, facial fractures were the most common injury (45% of survivors)**. Punches produced linear, diastatic and **blowout** fractures [S:R61].
- **Professional boxing** (gloved): 17.1 injuries per 100 boxer-matches = **3.4 per 100 boxer-rounds**. **Facial lacerations are 51%** of injuries, hand 17%, eye 14%, nose 5% [S:R60]. **Eyebrow laceration is the most common ocular-region injury (46%)**, then eyelid (23%) [S:R60].
- **Where skin splits first** (thin tissue over a prominence): **eyebrow / supraorbital ridge** (the most prominent facial structure after the nose), then **cheekbone**, **nasal bridge**, **inner lip against the teeth** (mucosal laceration; can go through-and-through), and **chin** [S:R62, R63, R35].

**Per-punch damage model `[E]`** (bare knuckle, adult target; multiply probabilities by about 0.05–0.1 for gloves):

| Target | Punch 1 | Punches 2–5 on the same spot | Beyond ~5–10 |
|---|---|---|---|
| Any face skin | **Erythema at once** (knuckle-shaped flush fading in 10–30 min if no bruise); swelling onset 1–5 min | Bruise visible in 15–60 min; knuckle-row pattern | Confluent bruising, tight shiny swelling |
| Eyebrow | P(split) ≈ 2–10% (untrained) / 10–25% (trained) | P rises ×1.5 per prior hit (swollen, tense skin) `[K]` | 2–4 cm linear/crescentic split, bleeds into the eye |
| Nose | Epistaxis likely (60–90%); P(fracture) ≈ 20–50% untrained, 50–90% trained | Deviation or depression, crepitus | Septal haematoma possible |
| Lips | Inner-lip mucosal laceration against incisors, 20–40% | Swelling ×1.5–2; possible through-and-through | Tooth luxation (§4.7) |
| Zygoma | Bruise only | P(ZMC fracture) ≈ 5–20% per hard trained punch | Flattened cheekbone, subconjunctival haemorrhage |
| Jaw (side of body / angle) | P(fracture) ≈ 5–15% per hard hook (lateral threshold 600–700 N) | Angle fractures are the typical assault fracture [S:R41] | Malocclusion, step |
| Orbit | Black eye in 12–48 h | Blowout: 5–15% per direct hit to the globe with a fist larger than the orbital rim `[E]` | Enophthalmos masked by swelling |

Gloved check: 3.4 injuries per 100 rounds × 51% lacerations ≈ 1.7 lacerations per 100 rounds. With roughly 15–40 head punches landed per round `[K]`, that is about 0.05–0.1% per landed gloved punch. So a laceration on the first bare-knuckle punch should be **uncommon but possible**.

Attacker side `[K]`: bare-knuckle punches to the teeth cut the striker's knuckles, and hard punches can fracture the striker's 5th metacarpal ("boxer's fracture"). This matters only if the player character has a body.

### 3.6 Simulation parameters: blunt soft tissue

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| abrasion_bright_red_until | 12–24 | h | | [S:R29] |
| abrasion_scab_complete | 24–48 (93%) | h | | [S:R29] |
| abrasion_scab_red / brown / dark_brown / black | 10–32 / 16.5–72 / 35.5–157 / > 72 | h | Colour of scab | [S:R29] |
| abrasion_scab_falls | 7–10 | d | Pink/hypopigmented beneath | [S:R29] |
| abrasion_pinpoint_bleed_onset | 10–60 | s | Dermal papillae | [S:R30], [K] |
| bruise_visible_delay_superficial | 0–30 | min | | [S:R27] |
| bruise_visible_delay_deep | 12–48 | h | Re-examine at 48 h | [S:R27] |
| bruise_gravity_migration | 1–5 | cm over days | Downward | [S:R27], [E] |
| bruise_yellow_min_age | **18** | h | Hard constraint | [S:R23] |
| bruise_yellow_typical_onset | 24–72 | h | | [S:R24] |
| bruise_colour_stages | red 0–2 d, blue/purple 2–5, green 5–7, yellow 7–10, brown 10–14 | d | Textbook chart; randomize ±30% | [S:R25] |
| bruise_max_duration | 14–21 (large: 30+) | d | | [S:R23, R26] |
| bruise_force_predictiveness | low | — | Add noise | [S:R28] |
| goose_egg_onset / peak | 1–5 min / 24 h | — | | [S:R50] |
| periorbital_swelling_peak | 24–48 | h | Eye may close | [S:R53] |
| black_eye_resolution | 14–21 | d | | [S:R53] |
| laceration_force_min_scalp | 4000 | N | Porcine drop tower; localized impactor | [S:R34] |
| laceration_bridging | true | bool | Pathognomonic | [S:R31] |
| laceration_bleed_mult_vs_incised | 0.3–0.6 (scalp 1.0) | × | | [S:R14], [E] |
| punch_force_untrained | 500–1500 | N | Weak source | [S:R37] |
| punch_force_olympic | 3427 ± 811 | N | | [S:R36] |
| punch_hand_velocity | 9.14 ± 2.06 | m/s | Trained | [S:R36] |
| punch_effective_mass | 2.9 ± 2.0 | kg | Trained | [S:R36] |
| punch_head_accel | 58 ± 13 g / 6343 rad/s² | — | For the brain/concussion system | [S:R36] |
| one_punch_facial_fracture_rate | 45 | % of survivors | | [S:R61] |
| boxing_injury_rate | 3.4 / 100 rounds; lacerations 51% | — | Gloved | [S:R60] |
| eyebrow_share_of_ocular_injuries | 46 | % | Boxing | [S:R60] |

**Visual/behavioural checklist (blunt soft tissue)**
- A punch leaves an **instant red knuckle-shaped flush**; swelling starts within minutes; true bruise colour follows from 15 min to hours. Deep bruises can appear **the next day** and **lower down** than the blow.
- Bruise colour ages from the **edges inward**: purple centre, then a **yellow-green rim (never before 18 h)**, then yellow-brown, then gone in 2–3 weeks.
- Eyelids swell dramatically and can close the eye. Upper-face blows **track down into the eyelids** over 1–2 days.
- Abrasions: bright red, wet, **pin-prick beads of blood**, with a clear/yellow serum glaze. Epidermis heaps at the end of the drag. They dry to a brown then black scab over 1–3 days.
- Lacerations over bone (eyebrow, cheekbone, chin, scalp) are **ragged, with a grazed and bruised rim and strands crossing the floor**. Hammer edges give crescents, rounded objects give stars.
- A split eyebrow **bleeds into the eye**; the character blinks and squints (behaviour hook for the eye system).
- Knuckle impacts on the mouth split the **inner lip against the teeth**, with blood in the mouth before any external wound.

---

## 4. Blunt force: facial skeleton and teeth

### 4.1 Fracture thresholds (impact force or energy)

| Structure | Threshold | Notes | Source |
|---|---|---|---|
| Nasal bones | **111–334 N** minimal (25–75 lbf) | Lowest of all facial bones | [S:R38] |
| Orbital floor (blowout) | **1.22 J** (hydraulic) – **1.54 J** (buckling); direct floor loading 29–127 mJ | 0.5 mm floor | [S:R44] |
| Zygoma body / arch | **900–2000 N** / 850–2000 N; cadaver fractures at 930–2850 N (6.5 cm² impactor) | Load spread over the whole bone raises tolerance by 150–250% for impulses > 4 ms | [S:R38, R39] |
| Mandible | **600–700 N lateral** (body); **2.4–3.1 kN frontal** (chin) | Sides are much weaker than the chin | [S:R40] |
| Maxilla | ~660–1780 N | Commonly cited Nahum range; not verified this session | [K] |
| Frontal bone | **3.6–7.1 kN** (800–1600 lbf); 50% risk at 1.9–2.4 kN (flat cylindrical impactor) | About 3–4× the mandible or zygoma | [S:R38, R56] |
| Temporo-parietal | ~2–5 kN | | [K] |
| General rate effect | Up to ~4.4 kN (1000 lbf) tolerated for ≤ 3 ms; fracture near 890 N (200 lbf) for impulses > 4 ms | Short, sharp impacts are tolerated better | [S:R38] |

### 4.2 Nasal fracture

- The **most commonly fractured facial bones**, because of their central, projecting position [S:R46].
- Signs [S:R46]: **epistaxis first**, then deformity (deviation or depression), swelling, point tenderness, **crepitus**, mobility, lacerations, nasal and periorbital ecchymosis, septal deviation and obstruction.
- **Septal haematoma**: a **purplish, cherry-like bulge** on the septum, often bilateral. Untreated, it causes cartilage necrosis and a saddle nose [S:R46].
- **Swelling masks the deformity**; clinicians reassess at **3–5 days** and reduce within 5–10 days (adults) [S:R46].

### 4.3 Orbit: blowout fracture, black eye, subconjunctival haemorrhage

- **Blowout (orbital floor)** signs [S:R43]:
  - Enophthalmos (sunken eye), **masked by oedema at first and increasingly obvious over 1–2 weeks**.
  - **Vertical diplopia, worst on upgaze**, from inferior rectus entrapment.
  - **Numbness of the cheek and upper gum** (infraorbital nerve).
  - **Orbital/eyelid emphysema**: crackling puffiness, **worse after nose-blowing**.
  - Epistaxis, eyelid ecchymosis; sometimes hyphema or mydriasis.
- **Subconjunctival haemorrhage**: a **sharply demarcated bright-red** patch on the white of the eye (#C0141E). It fades bright red, then maroon, then brown/yellow, and **resolves in 1–2 weeks** [S:R54]. It is the most common ocular sign with ZMC fractures (52%) [S:R45].

### 4.4 Zygomaticomaxillary complex (ZMC) fracture

- Sign frequencies [S:R45]:
  - **Step deformity of the orbital rim: 100%**.
  - **Cheek flattening: 94%**.
  - Periorbital ecchymosis: 90%.
  - Facial asymmetry: 86%.
  - Oedema: 82%.
  - Epistaxis (same side): 68%.
  - Subconjunctival ecchymosis: 52%.
- **Loss of malar prominence can be hidden by swelling** [S:R45]. **Trismus** (limited mouth opening) comes from the depressed arch impinging on temporalis or coronoid; there is **infraorbital numbness** [S:R45].

### 4.5 Le Fort fractures (high-energy midface)

- **I (horizontal)**: fracture above the tooth roots; mobile tooth-bearing maxilla, **malocclusion**, upper-lip swelling, buccal bruising, loose teeth [S:R42].
- **II (pyramidal)**: through the nose, infraorbital rims and orbital floor. Marked midface swelling, **telecanthus** (wider distance between the inner eye corners), mobile maxilla and nose, **"dish-face"** (flattened, retruded midface) [S:R42].
- **III (craniofacial dysjunction)**: the whole midface separates from the skull base, giving a **"floating face"** that moves as one unit. Usually motor-vehicle energy [S:R42].
- Game note `[E]`: Le Fort patterns need energies well above one punch (multiple kN, broad impact). With player weapons they are plausible only from **repeated hammer blows to the midface**.

### 4.6 Mandible fracture

- **Site distribution** [S:R41]: body **~29%**, condyle **~26%**, angle **~25%**, symphysis **~17%**, ramus **~4%**, coronoid **~1%**. One series reports parasymphysis 35–50%. **In assaults the angle is fractured most often**, because of its prominence [S:R41].
- Signs `[K]`:
  - **Malocclusion** (bite feels wrong) and a **step in the tooth row**.
  - **Sublingual haematoma** (bruise under the tongue: a strong sign).
  - Bleeding from the gum at the fracture line.
  - **Numb lower lip and chin** (inferior alveolar nerve).
  - Trismus, drooling, and deviation of the jaw on opening toward a condylar fracture.
  - About half are **two fractures** (the mandible is a ring), for example angle on one side plus parasymphysis on the other.

### 4.7 Teeth: luxation and avulsion

- Classes [S:R47]:
  - **Concussion**: tender, not displaced.
  - **Subluxation**: loose, in position.
  - **Extrusion**: partly out of the socket, looks longer.
  - **Intrusion**: driven into the bone, looks shorter or disappears.
  - **Lateral luxation**: tipped labially or palatally, often locked in a fractured alveolus.
  - **Avulsion**: completely out.
- Maxillary central incisors are the teeth most often avulsed [S:R47]. High-velocity, low-mass impacts tend to **fracture the crown**; slower, heavier impacts **displace the whole tooth** and damage the ligament or alveolar bone [S:R47].
- **Socket bleeding**: expect **steady ooze for about the first hour**; clotting starts after about **5 min** and clots form within 0–15 min; bleeding generally settles with 30–45 min of pressure [S:R48]. In an avulsion the socket fills with blood at once and overflows into the mouth `[K]`. The clot in the socket is dark red and jelly-like and can be dislodged, which restarts bleeding `[K]`.
- Displacement magnitudes `[K]`: extrusion or lateral luxation 1–5 mm. A crown fracture exposing the pulp shows a **pink-red bleeding dot** in the centre of the broken tooth.

### 4.8 Simulation parameters: facial skeleton and teeth

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| frac_nasal_force | 111–334 | N | Minimum | [S:R38] |
| frac_orbital_floor_energy | 1.2–1.5 | J | Globe/rim impact | [S:R44] |
| frac_zygoma_force | 900–2000 (up to 2850) | N | | [S:R39] |
| frac_mandible_lateral / frontal | 600–700 / 2400–3100 | N | | [S:R40] |
| frac_maxilla_force | 660–1780 | N | Unverified | [K] |
| frac_frontal_force | 1900–7100 | N | 50% risk 1.9–2.4 kN (flat impactor) | [S:R38, R56] |
| mandible_site_weights | body 29, condyle 26, angle 25, symphysis 17, ramus 4, coronoid 1 | % | Assault: raise the angle weight | [S:R41] |
| mandible_second_fracture_p | ~0.5 | p | Contralateral | [K] |
| zmc_signs | step 100, flat 94, periorb 90, asym 86, oedema 82, epistaxis 68, subconj 52 | % | | [S:R45] |
| blowout_enophthalmos_reveal | 7–14 | d | Masked by oedema | [S:R43] |
| subconj_haem_resolution | 7–14 | d | Bright red → maroon → brown/yellow | [S:R54] |
| nasal_reassess_window | 3–5 | d | Swelling masks deformity | [S:R46] |
| tooth_socket_ooze_duration | ~60 | min | Clot forms 5–15 min | [S:R48] |
| tooth_displacement | 1–5 | mm | Extrusion/lateral | [K] |

**Visual/behavioural checklist (facial skeleton)**
- A broken nose bleeds **at once** from both nostrils, deviates or flattens, and **crunches** (crepitus audio) when struck again. Swelling fills in and hides the deformity within an hour.
- A cheekbone fracture flattens the cheek (visible when swelling allows), with a **step** at the lower orbital rim, a **bright red patch on the white of the eye**, a nosebleed on the same side, and limited mouth opening.
- Blowout: the eye sits lower and sinks back over days; the character cannot look up in step with the other eye (hook for the eye system); **crackling puffiness** of the lids if air enters.
- Broken jaw: the bite goes off (teeth no longer meet), there is a **step between teeth** with bleeding gum, and a **dark bruise under the tongue**. The jaw hangs or deviates; drooling of bloody saliva.
- Teeth: loose, tipped, pushed in (shorter) or out (longer). A knocked-out tooth leaves a **socket brimming with blood** that oozes for about an hour, with dark clot forming in minutes.
- Le Fort II/III (repeated heavy blows only): a flattened "dish face", widened eye spacing, and a midface that **moves as a block**.

---

## 5. Blunt force: skull and scalp (hammer)

### 5.1 Skull fracture thresholds

- General skull fracture energy threshold: **14.1–68.5 J** [S:R55 (baseball-bat paper)]. By region: **frontal ~22–24 J, temporal ~5–15 J** [S:R56].
- Force: the 50% skull-fracture force spans **1.8–12.5 kN**. The frontal 50% risk is **1.9–2.4 kN** (flat cylindrical impactor). Rigid frontal impacts at 7.7 m/s produced **5.6–14 kN** [S:R56].
- Laceration plus skull damage in porcine tests needed **> 4 kN** [S:R34].

### 5.2 How much energy a hammer delivers

- Volunteer study of striking energies with a 1 m striking object [S:R55]: **men 67–312 J, women 30–203 J**. The optimum mass was about 1.3 kg (men) or 1.65–2.2 kg (women), with the centre of mass in the far quarter. Upper-arm circumference and shoulder width correlate with blow energy; there was no sex or age difference in strike *rate*.
- Everyday objects [S:R55]: **nylon hammer 70.6 ± 9.2 J**, crutch 75.5 J, cooking pot 63.4 J, frying pan 53.2 J.
- Measured contact forces in hammer blows: **2.97–4.68 kN** [S:R55].
- A claw hammer (0.45–0.7 kg head, about 0.3 m handle) `[K]` probably delivers **~30–120 J** in a committed swing `[E]`. That is above the temporal and frontal fracture energies, so **one hard, committed blow can fracture the skull, especially the temporal region**.
- The counter-case [S:R55]: **dozens of weak hammer blows gave multiple scalp contused lacerations and abrasions with no fracture**, and **death from scalp haemorrhage**. The sim should let low-energy repeated blows produce this outcome.

### 5.3 Depressed fracture morphology

- **Mechanism**: focused force drives the outer and inner tables inward [S:R58].
- **Signature fracture**: the outer-table defect is **geometric and matches the size and shape of the hammer face** (round or square). The **outer-table edges are sharp and regular**; the **inner-table edges are bevelled and irregular**, with a larger defect on the inside (a cone of bone pushed in) [S:R55, R58].
- **Claw end** gives **two parallel wounds**, or two wounds in line, from the bifurcated claw [S:R55].
- **Oblique blow** gives a **concentrically terraced** depressed fracture: a stepped series of arcs, deepest where the face bit first `[K]` [S:R58].
- **Broad flat surfaces** give radiating and concentric linear fractures rather than a clean punched-out defect [S:R58].
- **Pond / "ping-pong" fracture**: an inward buckle *without* a break. **Neonates and infants only** (soft skull). **Do not use for the adult model**; an adult shows a true depressed or comminuted fracture instead [S:R59].
- **Clinical significance**: depression **greater than the calvarial thickness (≈ 6–8 mm) or > 1 cm** is the surgical threshold; open depressed fractures risk dural tear, infection and seizures [S:R57].
- Hammer face sizes `[K]`: standard claw hammer face **25–32 mm diameter** round; club or lump hammer about 35–45 mm square with rounded corners.
- Scalp over a hammer impact [S:R32, R55]: a **crescentic laceration** from the face's rim on an angled strike; a **circular or square abrasion/bruise ring** on a flat strike; **stellate** tears over bone with heavy impacts.

### 5.4 Scalp haematomas

| Type | Plane | Boundaries | Feel / look | Adult relevance | Source |
|---|---|---|---|---|---|
| Subcutaneous ("goose egg") | Dense subcutaneous layer | Localized | Firm, tender dome; appears in 1–5 min, peaks 24 h | **Most common adult bump** | [S:R50] |
| **Subgaleal** | Between galea and pericranium (loose areolar) | **Crosses sutures**; can spread **from the nape to the orbits** | **Boggy, fluctuant**, shifts with gravity; can hold large volumes (up to 260 mL in term newborns; more in adults `[K]`) | Adults: from lacerations and depressed fractures; drains into the eyelids over 24–48 h `[K]` | [S:R49] |
| Cephalhaematoma | Subperiosteal | **Bounded by sutures** (limited to one bone) | Firm, well-demarcated | Almost entirely **neonatal**; rare in adults | [S:R49] |

### 5.5 Basal skull fracture signs (with timing)

- **Raccoon eyes**: bilateral periorbital ecchymosis that **spares the tarsal plate** (the orbital septum limits spread). **Delayed 1–3 days (typically 48–72 h)**; anterior cranial fossa fracture [S:R51, R52].
- **Battle's sign**: bruising behind the ear over the mastoid. **At least ~1 day**, hours to days [S:R51].
- **Haemotympanum**: purple eardrum. **Within hours**, often the earliest sign [S:R51].
- **CSF rhinorrhoea/otorrhoea**: clear or blood-tinged fluid from the nose or ear. The "**halo**" or double-ring sign on cloth is **not specific**. It can be **delayed hours to days** [S:R51].
- A **direct black eye** appears **within 24 h** and can **cross the tarsal plate**; this distinguishes it from raccoon eyes [S:R52].

### 5.6 Simulation parameters: skull and scalp

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| skull_frac_energy_general | 14.1–68.5 | J | | [S:R55] |
| skull_frac_energy_frontal / temporal | 22–24 / 5–15 | J | Temporal is weakest | [S:R56] |
| skull_frac_force_50pct_range | 1.8–12.5 | kN | Frontal 50% = 1.9–2.4 kN | [S:R56] |
| hammer_blow_energy_game | 30–120 (default 60) | J | Claw hammer; derived | [S:R55], [E] |
| hammer_contact_force | 2.97–4.68 | kN | | [S:R55] |
| blow_energy_men / women (1 m object) | 67–312 / 30–203 | J | Upper bounds for long tools | [S:R55] |
| nylon_hammer_energy | 70.6 ± 9.2 | J | | [S:R55] |
| hammer_face_diameter | 25–32 | mm | Round claw hammer | [K] |
| depressed_frac_outer_edge | sharp, regular, matches face | — | Signature | [S:R55] |
| depressed_frac_inner_bevel | larger, irregular | — | Cone | [S:R55] |
| depressed_frac_surgical_depth | > calvarial thickness (6–8) or > 10 | mm | | [S:R57] |
| terraced_on_oblique | true | bool | Concentric steps | [S:R58] |
| pond_fracture_adult | false | bool | Infant only | [S:R59] |
| scalp_goose_egg_onset / peak | 1–5 min / 24 h | — | | [S:R50] |
| subgaleal_crosses_sutures | true | bool | Nape to orbits | [S:R49] |
| raccoon_eyes_delay | 24–72 (typ 48–72) | h | Tarsal plate spared | [S:R51, R52] |
| battle_sign_delay | ≥ 24 | h | | [S:R51] |
| haemotympanum_delay | 1–6 | h | Earliest sign | [S:R51], [E] |
| csf_leak_delay | 0–72 | h | | [S:R51] |

**Visual/behavioural checklist (hammer / skull)**
- The first light blows raise **goose eggs within minutes** and **crescentic or star-shaped scalp splits** that bleed heavily into the hair. Many light blows can kill by blood loss with no skull fracture.
- A committed blow leaves a **punched-out defect the shape of the hammer face** (round about 25–32 mm, or square). Bone fragments are pushed in, and the inside of the hole is wider and ragged. Angled blows leave **stepped, terraced arcs**; the claw end leaves **paired parallel wounds**.
- Audio `[K]`: a dull thud on scalp; on fracture, a sharp **crack** followed by a wet, crunchy give on repeat blows to the same spot (comminution).
- A boggy, sliding swelling spreads under the scalp (subgaleal) and **drains into both eyelids** over the following day.
- Base-of-skull fractures: **purple eardrum within hours**; **raccoon eyes and Battle's sign only after 1–3 days** (show them only if game time allows); clear or pink fluid from nose or ear.
- Depressed fragments deeper than about 1 cm link to the brain/dura system (see the head-injury document).

---

## 6. Thermal injury (torch)

### 6.1 Burn depth classes: appearance

| Class | Depth `[K]` | Appearance | Blanching / refill | Blisters | Sensation | Target colour `[K]` | Source |
|---|---|---|---|---|---|---|---|
| 1st / superficial (epidermal) | Epidermis (0.05–0.1 mm) | Red, dry, no blisters; may peel later | Blanches, brisk | No | Painful | #E0705F | [S:R64, R65] |
| 2nd superficial partial | Epidermis + papillary dermis | **Pink / cherry-red, moist, weeping**, blistered | Blanches, **brisk refill** | **Yes** (thin-walled) | Very painful | #E8737A base, blister roof translucent #F4E7B0 | [S:R64] |
| 2nd deep partial | Into reticular dermis | **Mottled white and red, waxy**, dry-ish; **fixed capillary staining by 48 h** | **Does not blanch**, sluggish | Few, thick, or ruptured | Reduced | White #E6DED6 with red mottle #B84A4A | [S:R64] |
| 3rd full thickness | Entire dermis ± fat | **White waxy, leathery grey, tan-brown, or cherry-red (fixed Hb)**; dry, **inelastic, leathery eschar** | None | **No** | **Painless** (nerve endings destroyed) | #EDE6DA / #9B6B43 / #A8322E | [S:R64, R65] |
| 4th (and "5th/6th" extended) | Through skin into fat, muscle, bone | **Black, charred**, cracked; muscle or bone exposed | None | No | None | #1A1614 char; muscle #5A2A1E cooked brown | [S:R64] |

Healing, for game-time evolution `[K]`: superficial 3–7 d with peeling; superficial partial 7–21 d; deep partial > 21 d with scarring; full thickness does not re-epithelialize (eschar separates over 2–3 weeks).

### 6.2 Thermal dose: time, temperature and heat flux

- **Temperature/time** (Moritz & Henriques) [S:R66]:
  - Pain begins when the dermo-epidermal junction exceeds **44 °C**.
  - From 44 to 70 °C the damage rate **rises logarithmically**.
  - Water at **60 °C for 5 s or 70 °C for 1 s** gives a deep partial or full-thickness scald.
  - At 54 °C, 18 s gave superficial partial and 22 s gave full thickness (one dataset).
  - The time-temperature data have been widely misinterpreted in standards, so use them for shape rather than exact thresholds [S:R66].
- **Heat flux, unprotected skin** [S:R67]:
  - ~**2.5 kW/m²** tolerable for minutes.
  - **4.5 kW/m²** gives a 2nd-degree burn in about **30 s**.
  - **6.4 kW/m²** gives pain at 8 s and **blisters at 18 s**.
  - **10 kW/m²** gives 2nd degree in about **10 s**.
  - **16 kW/m²** gives sudden pain and **blistering after 5 s**.
- **Flash fire test** (ASTM F1930 manikin): **84 kW/m²** (about 50% radiant, 50% convective) for **3–4 s** exposures, with sensors kept running **60–120 s afterwards because heat keeps soaking in ("after-burn")** [S:R68].
- **Porcine radiant source at 600 °C** [S:R71]: **5 s gives superficial partial (0.4 mm damage depth), 10 s deep partial (1.3 mm), 15 s full thickness (2.4 mm)**. In another model, 10 s gave deep partial and **20 s full thickness**.
- **Porcine contact, aluminium bar at 80 °C** [S:R72]: 20 s gave endothelial damage at 36% of dermal depth, 30 s at 60%.
- **Torch flame temperature**: air-propane primary flame about **1,100–1,250 °C** typically, **~2,000 °C** adiabatic maximum; MAPP about 2,050 °C; butane blowtorch about 1,430 °C [S:R70]. Jet flames have a **surface emissive power of ~200–400 kW/m²**; an impinging large propane jet measured **up to 340 kW/m² total (~100 kW/m² convective)** [S:R69].

**Fitted dose model `[E]`**. One power law reproduces all four sourced heat-flux points:
```
t2(q) ≈ 10 s × (q / 10 kW·m⁻²)^(−1.33)     // time to 2nd-degree (blister-level) burn
check: 4.5 → 29 s (src 30) ; 6.4 → 18 s (src 18) ; 10 → 10 s ; 16 → 5.3 s (src 5) ; 50 → 1.2 s ; 84 → 0.6 s
t3(q) ≈ 3 × t2(q)                           // full thickness; porcine 5 s vs 15 s at one source [S:R71]
t_char(q) ≈ 8–15 × t2(q)                    // visible surface char needs the tissue water driven off first [K]
t_4th(q)  ≈ 30–60 × t2(q)                   // through to fat/muscle
```
Accumulate a per-texel dose `D += dt / t2(q_local)`:
- D ≥ 0.2: erythema.
- D ≥ 1: superficial partial (blisters).
- D ≥ 2: deep partial.
- D ≥ 3: full thickness.
- D ≥ 10: char.
- D ≥ 40: 4th degree.

**After-burn** `[E]`: keep adding about 30% of the last second's dose over the 1–3 s after the flame moves away (heat soak) [S:R68, qualitative].

Local flux under a handheld torch `[E]`: inside the visible flame (about 3–10 cm from the nozzle), q ≈ **100–250 kW/m²** (default 150), from sourced jet-flame values of 200–400. Beyond the flame tip, fall off roughly ∝ 1/d². Note that the power law is **validated only up to about 84 kW/m²**; above that it is an extrapolation.

### 6.3 Torch exposure timeline at one spot (default q = 150 kW/m², t2 ≈ 0.27 s) `[E]`

| Continuous exposure | What happens | Visual | Audio / smell |
|---|---|---|---|
| 0–0.1 s | Fine hair singes (**hair burns near 233 °C**) [S:R79] | Hairs curl, shrivel, bead into black knobs; wisps of white smoke | Faint crackle; **sulfurous burnt-hair smell** (keratin, H2S/SO2) [S:R78, R79] |
| 0.1–0.3 s | Erythema, epidermis heating | Skin flushes red around the spot | — |
| 0.3–0.8 s | 2nd degree: epidermis coagulates | Epidermis turns **matte grey-white** and wrinkles; lifts and separates | Soft hiss (steam) |
| 0.8–1.5 s | Deep partial to full thickness | Centre **waxy white then pale tan**; surrounding red ring (hyperaemia) | Hiss, faint sizzle |
| 1.5–4 s | Full thickness, dehydrating | Tan-brown **leathery** eschar, shiny then dry; skin **tightens and puckers** (collagen shrinkage) | Sizzle; smell like **charcoal / seared meat** [S:R78] |
| 3–8 s | Charring begins | **Black char** with fine cracks; edges curl; greasy yellow-grey smoke | Crackling, popping |
| 8–20 s | 4th degree: fat renders | **Yellow fat melts and bubbles**, may catch as small flames (burning fat); **heat fissures** open in the char exposing fat or muscle | Fat spitting; **pork-fat smell** [S:R78] |
| > 20 s | Muscle cooked or charred; bone exposure on thin sites (forehead, scalp, shin) | Muscle brown-grey, then black; exposed bone goes ivory, then **brown (~300 °C), black (~400 °C), grey-white calcined (> 500–600 °C)** [S:R80] | Beef-like odour from muscle [S:R78]; bone crackle |

At the edge of the flame, the same stages play out more slowly, following the dose model. A moving torch leaves a **graded trail**: char in the middle, then white/tan, then a blister or peeling margin, then a red rim.

### 6.4 Blisters and peeling

- Superficial partial-thickness burns **form blisters between epidermis and dermis**. Sources vary on timing: **thin-walled blisters "within minutes"**, "within 24 h", or 1–2 days [S:R77, R65]. Heat-flux tables put blister formation at the 5–18 s exposure level for 6–16 kW/m² [S:R67].
- Full-thickness burns **do not blister** [S:R65].
- Game model `[E]`: blister domes start growing **30 s–5 min** after a D≈1–2 texel is created, reach 50% size in about 30 min, and are full at 2–24 h. Diameter is 3 mm to several cm, and neighbouring blisters merge. The roof is translucent and wrinkly; the fluid is clear to straw-yellow (#F4E7B0).
- **Flame burns often peel at once** `[K]`: the coagulated epidermis separates into **grey-white wrinkled sheets** that slide or hang off, exposing moist pink or red dermis beneath. Denudation and sloughing of the epidermis after burns is documented [S:R65].
- First-degree burns peel (desquamate) at about 3–7 days `[K]`.

### 6.5 Shrinkage, eschar and heat-induced splits

- **Collagen thermal shrinkage** starts sharply at about **60 °C**; the transition is 60–70 °C. Linear shrinkage is about **30% at 62.5 °C** (10 min) and **~36% at 65.5 °C** (fast). It is **anisotropic: up to 47% parallel to Langer's lines vs 29% perpendicular**. Above about 70 °C, prolonged heating relaxes it again [S:R73].
- Game model `[E]`: burned patches contract **15–35%** in area-equivalent along the local Langer direction. The pull drags the surrounding skin into radial wrinkles. Near the lips, this retracts the lip and shows the teeth; near the eyelids, it pulls the lid (ectropion) `[K]`.
- **Eschar is stiff, inelastic dead tissue**. Circumferential eschar constricts circulation (limbs) or breathing (chest). Oedema under the eschar **peaks at 24–48 h**, and escharotomy is typically needed at **2–6 h** [S:R74]. This is a full-body physiology hook for large circumferential burns only.
- **Heat-induced skin splits** [S:R75, R85]:
  - Sharply demarcated splits from **vaporization of tissue fluids**.
  - Mostly over **joints, extensor surfaces and the head**.
  - They **follow muscle-fibre direction**, whereas traumatic wounds cut across fibres.
  - They can reach fat and muscle.
  - **No haemorrhage**.
  - Game `[E]`: fissures 1–5 mm wide and 1–10 cm long open in char once D ≥ 10, aligned with the underlying muscle fibres and Langer's lines. They do not bleed.

### 6.6 Pugilistic posture (large or deep burns only)

- Heat **denatures and dehydrates muscle protein**, so muscles contract. **Flexors are bulkier than extensors**, so elbows, wrists, knees, hips and fingers flex into a "boxer's" stance [S:R75].
- It **occurs whether the person was alive or dead**, so it is **not** a sign of life or struggle [S:R75].
- In a cremation furnace (**670–810 °C**) the posture developed after **~10 min**. At **~20 min** the calvaria was bare of soft tissue with **outer-table fissures**; at **~30 min** the body cavities opened; at **~40 min** organs were shrunken and sponge-like; at **~50 min** only the torso remained [S:R76].
- **Game rule `[E]`**: a hand torch cannot produce whole-body posture. Allow **local contracture**: fingers curl or the wrist flexes when deep muscle in the forearm or hand reaches D ≥ 40 over > 30% of the flexor compartment. Whole-body posture only for simulated whole-body fire (> 30–50% body surface with deep burns sustained for minutes).
- **Wick effect** `[K]` [S:R82]: a body does not keep burning on its own unless clothing acts as a wick for rendered fat. In the reference experiment a blanket-wrapped 95 kg pig carcass burned for **> 5 h** at > 760 °C. For the game: flames stop soon after the torch is removed, apart from brief fat flare-ups.

### 6.7 Deep structures and colour

- **Subcutaneous fat**: melts and renders, bubbles, can ignite as small yellow flames, and leaves a greasy sheen and soot `[K]`.
- **Muscle**: cooks grey-brown, then shrinks and chars black `[K]`.
- **Bone** [S:R80]: ivory/yellowish (< 285 °C), **dark brown (~300 °C)**, **black (~400 °C, carbonized)**, then **grey and white "calcined" (> 500–600 °C)** with surface **checking / curved heat fractures**.
- **Burn zones (Jackson)** [S:R81]: a central **coagulation** zone (dead, charred or white), a surrounding **stasis** zone (viable at first, can die over **24–72 h**), and an outer **hyperaemia** zone (red, recovers). Render the red rim around every burn; for game time > 24 h, grow the dead zone by about 10–30% `[E]`.
- **Bleeding**: burned tissue **does not bleed**, because heat coagulates small vessels `[K]`. Cauterization rule `[K]/[E]`: applying the torch to a bleeding wound **stops capillary and small venous bleeding** (vessels < ~1–2 mm) at D ≥ 2, but **cannot seal arteries or large veins** (STA trunk, facial artery, jugulars). Those keep bleeding through the char.

### 6.8 Simulation parameters: thermal

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| pain_threshold_temp_DEJ | 44 | °C | | [S:R66] |
| scald_deep_60C / 70C | 5 / 1 | s | Deep partial / full thickness | [S:R66] |
| flux_tolerable | < 2.5 | kW/m² | Minutes | [S:R67] |
| t2_at_4.5 / 6.4 / 10 / 16 kW/m² | 30 / 18 / 10 / 5 | s | 2nd degree / blister | [S:R67] |
| t2_power_law | t2 = 10·(q/10)^−1.33 | s | Fits all four sourced points | [E] |
| t3_over_t2 | ~3 | × | Porcine 600 °C: 5→15 s | [S:R71], [E] |
| damage_depth_5/10/15 s at 600 °C radiant | 0.4 / 1.3 / 2.4 | mm | Porcine | [S:R71] |
| flash_fire_flux | 84 | kW/m² | ASTM F1930 | [S:R68] |
| afterburn_window | 1–3 (tests log 60–120) | s | Heat soak | [S:R68], [E] |
| torch_flame_temp_propane_air | 1100–1250 (max ~2000) | °C | | [S:R70] |
| jet_flame_surface_emissive | 200–400 | kW/m² | | [S:R69] |
| torch_local_flux_in_flame | 100–250 (default 150) | kW/m² | Extrapolated | [E] |
| hair_burn_temp | ~233 | °C | Weak source | [S:R79] |
| collagen_shrink_onset | 60 | °C | | [S:R73] |
| collagen_shrink_max | 30–36 (47 par / 29 perp) | % | Anisotropic | [S:R73] |
| blister_onset | 0.5–5 min (clinical: minutes–24 h) | — | | [S:R77, R65], [E] |
| blister_full_size | 2–24 | h | | [E] |
| eschar_oedema_peak | 24–48 | h | | [S:R74] |
| escharotomy_window | 2–6 | h | Circumferential deep burns | [S:R74] |
| stasis_zone_progression | 24–72 | h | | [S:R81] |
| deep_partial_fixed_staining | 48 | h | | [S:R64] |
| pugilistic_onset_furnace | ~10 | min at 670–810 °C | Whole-body only | [S:R76] |
| calvaria_bare_outer_table_fissures | ~20 | min at 670–810 °C | | [S:R76] |
| bone_colour_T | brown 300, black 400, grey-white > 500–600 | °C | | [S:R80] |
| cautery_max_vessel | 1–2 | mm | Heat seals only small vessels | [K] |
| wick_effect_burn_duration | > 5 | h | Needs clothing/blanket wick | [S:R82] |

**Visual/behavioural checklist (torch)**
- Hair goes first: it **curls, shrivels and beads** within a fraction of a second, with a **sulfurous burnt-hair smell**.
- Skin under the flame **reddens, then turns matte grey-white and wrinkles**; the epidermis **lifts and peels in grey sheets**, exposing wet pink dermis. A red halo spreads around the spot.
- Held longer, the centre goes **waxy white, then tan-brown leathery**, then **black and cracked**. The burned patch **shrinks and puckers**, dragging nearby skin into radial folds; burned lips pull back to show teeth.
- Fat **bubbles, spits and flares** in small yellow flames; the smoke turns greasy grey-yellow with **black soot** deposits. **Fissures split open along the muscle grain** without bleeding.
- Superficial-partial areas grow **translucent blisters** over the following minutes to hours. Full-thickness areas never blister and are **painless** (for the pain/AI system).
- Burned wounds do not bleed. The torch **stops oozing** from small cuts, but **arterial jets keep spurting** through the char.
- Audio: steam **hiss**, **sizzle**, fat **pops**, char **crackle**. Smells (if represented in UI text or haptics): burnt hair (sulfur), **seared meat / charcoal**, pork fat, burnt liver for viscera [S:R78].
- Whole-body pugilistic posture only for sustained whole-body fire (minutes). A torch on the forearm can curl the fingers.

---

## 7. Colour palette (authored `[K]`, sRGB, light–medium skin, D65)

| Material / stage | Hex | Notes |
|---|---|---|
| Baseline skin, light / medium / dark | #E8BFA4 / #C68E6C / #7B4B32 | Tint targets for blends |
| Erythema flush | #E07A6E | Punch flush, 1st-degree burn |
| Fresh abrasion (raw dermis) | #C8323A | Plus pinpoint beads #9E0F1E |
| Serum glaze | #F2D98A @ 30–50% alpha | Glossy |
| Scab red / brown / dark brown / black | #8A2A20 / #6B3A22 / #4A2A1A / #1E1512 | Abrasion ageing |
| Bruise red / red-purple | #C0485A / #8E3B5E | 0–48 h |
| Bruise dark purple / blue-purple / blue | #4E3368 / #5A3F7A / #3E4A7A | Peak 12–72 h |
| Bruise green / yellow-green / yellow | #7D8F4E / #B5B04E / #D8C06A | Yellow ≥ 18 h only |
| Bruise brown (haemosiderin) | #A07850 | 10–14 d |
| Subconjunctival haemorrhage fresh / old | #C0141E / #7A1A1F | Sharp border |
| Septal haematoma | #6E2A4A | Cherry-purple bulge |
| Blood arterial / venous / clot / dried | #C4161C / #7A0A10 / #5A0A0E / #3B1512 | |
| Subcutaneous fat | #F2D16B | Lobulated |
| Galea / fascia | #E8E4DC | Glistening white |
| Skull outer table / diploë | #E9E0CC / #A9564A | Diploë bleeds |
| Muscle (fresh) / cooked / charred | #8E2A2A / #5A2A1E / #1C1210 | |
| Burn: SPT base / blister fluid | #E8737A / #F4E7B0 | |
| Burn: DPT white / mottle red | #E6DED6 / #B84A4A | |
| Burn: full thickness white / tan-leather / fixed red | #EDE6DA / #9B6B43 / #A8322E | |
| Eschar grey | #7C736A | |
| Char / soot | #1A1614 / #2B2B2B | Add glossy cracks |
| Bone brown (300 °C) / black (400 °C) / calcined | #6B4A2B / #1C1A18 / #F2F0EB | [S:R80] temperatures |

---

## 8. Cross-cutting implementation notes (for engineers)

1. **Per-texel damage channels** (suggested): `bruise_blood` (0–1), `bruise_age_h`, `bruise_depth` (0–1), `abrasion_depth` (mm), `burn_dose D`, `swelling` (mm), `scab_state`. Use a mesh cut or decal system for incisions and lacerations, with fields `{length, depth, orientation vs tension map, edge_type: clean|ragged, bridging: bool, tail_dir}`.
2. **Tension map**: bake a 2D vector field of Langer/RSTL directions on the head UVs (horizontal on the forehead, radiating around the eyes and mouth, near-vertical on the sides of the cheeks, circumferential on the neck `[K]`). Use it for gape (§2.3), stab ellipse orientation (§2.5) and burn shrinkage anisotropy (§6.5).
3. **Anvil map**: bake a soft-tissue-thickness-over-bone map from §1 (eyebrow, zygoma, nasal bridge, chin and scalp have low values). Laceration probability for a blunt hit is proportional to `energy / (contact_area × thickness)`. The same blow bruises the cheek and splits the eyebrow.
4. **Threshold checks per impact**: compare impact force (from Jolt contact impulse ÷ contact duration; use 3–10 ms for fist, 1–3 ms for hammer `[E]`) and energy against §4.1 and §5.1. Add ±25% per-character random variation for bone strength.
5. **Bleeding**: each wound registers vessels crossed and rates (§2.6) with the vascular/physiology system. Scalp wounds get a `tethered=true` flag (no vasoconstriction benefit). Burned texels set `cauterized` for small vessels only.
6. **Death gate**: after death, stop bruise formation, swelling, scab formation and blister growth. New wounds get `postmortem=true` (no active bleeding, gape ×0.5, no vital-reaction colours) [S:R22].
7. **Time-scale**: the bruise/abrasion/blister clocks (hours–days) should read a global `bio_time_scale` so a "fast-forward" mode can show forensic ageing. The sharp and blunt immediate responses (gape, beads, swelling onset) run in real time.

---

## 9. Load-bearing numbers to verify first (QA list)

1. Bruise yellow never before **18 h** (Langlois & Gresham) [R23].
2. Bruise colour chart red 0–2 d / blue-purple 2–5 / green 5–7 / yellow 7–10 / brown 10–14 [R25].
3. Abrasion scab stages and 7–10 d scab loss [R29].
4. Knife skin penetration force **10–55 N**; blunt tips ×3 [R8].
5. Stab wound length ≈ blade width − 0–2 mm [R4].
6. Cut-throat: skin/platysma/EJV 100%; exsanguination ~50%, aspiration 36.5% [R13].
7. Scalp lacerations can cause shock because vessels cannot constrict [R15].
8. Laceration minimum force **4 kN** (porcine scalp) [R34].
9. Olympic punch **3427 ± 811 N, 9.14 m/s, 2.9 kg** [R36].
10. Nasal fracture **111–334 N**; zygoma **0.9–2.0 kN**; mandible lateral **0.6–0.7 kN**, frontal chin **2.4–3.1 kN** [R38–R40].
11. Orbital floor blowout energy **1.2–1.5 J** [R44].
12. Skull fracture energy **14–69 J**; temporal **5–15 J**, frontal **22–24 J** [R55, R56].
13. Hammer/implement blow energies (nylon hammer 70.6 J; men 67–312 J for a 1 m object) [R55].
14. Raccoon eyes **1–3 d**, Battle's sign **≥ 1 d**, haemotympanum **within hours** [R51, R52].
15. Heat-flux burn times (4.5/6.4/10/16 kW/m² → 30/18/10/5 s) [R67] and the fitted power law `[E]`.
16. Porcine 600 °C: 5/10/15 s → SPT/DPT/FT [R71].
17. Collagen shrinkage onset 60 °C, 30–36%, 47% vs 29% anisotropy [R73].
18. Pugilistic posture ~10 min at 670–810 °C [R76].

---

## 10. Suspicious content

- **None observed.** No search result contained text instructing the reader to run commands, install or download anything, change files, visit other URLs, reveal information or ignore instructions.
- WebFetch was blocked for every domain (egress policy). No page bodies were read, so exposure to injected content was limited to search-result snippets.
- Several results came from low-quality or commercial sites (punch-force calculators, salon blogs, SEO health sites, patents). These were used only for ballpark values and are flagged in the tables (R37, R79, the tenting value in R8).

---

## 11. References

Search-extract basis only (see §0.1). Grouped by topic; the IDs match the tables.

**Sharp force**
- R1 — Medscape, *Forensic Autopsy of Sharp Force Injuries*. https://emedicine.medscape.com/article/1680082-overview
- R2 — PathologyOutlines, *Sharp force injuries*. https://www.pathologyoutlines.com/topic/autopsysharpforce.html
- R3 — Karakasi et al. 2016, *Hesitation Wounds and Sharp Force Injuries…*, J Forensic Sci. https://onlinelibrary.wiley.com/doi/10.1111/1556-4029.13146 ; Oncourse revision notes (tailing). https://getoncourse.ai/revision/indian-medical-pg/forensic-medicine/forensic-pathology/sharp-force-injuries/ ; EBSCO Research Starters, hesitation wounds. https://www.ebsco.com/research-starters/science/hesitation-wounds-and-suicide/
- R4 — forensicmed.co.uk, *Stab wounds*. https://www.forensicmed.co.uk/wounds/sharp-force-trauma/stab-wounds/ ; Lablogatory, *Autopsy Examination of Sharp Force Injuries*. https://labmedicineblog.com/2023/08/25/autopsy-examination-of-sharp-force-injuries/
- R5 — *Skin tension and cleavage lines (Langer's lines) causing distortion of ante- and postmortem wound morphology*. https://www.researchgate.net/publication/7945296_Skin_tension_and_cleavage_lines_Langer's_lines_causing_distortion_of_ante-_and_postmortem_wound_morphology
- R6 — ScienceDirect Topics, *Langer's Lines*. https://www.sciencedirect.com/topics/veterinary-science-and-veterinary-medicine/langers-lines ; Wikipedia, *Langer's lines*. https://en.wikipedia.org/wiki/Langer's_lines
- R7 — Maimonides EM, *Galea lacerations*. https://www.maimonidesem.org/blog/galea-lacerations ; AnatomyQA, *Scalp*. https://anatomyqa.com/scalp-layers-nerve-and-arterial-supply/ ; Wikipedia, *Scalp*. https://en.wikipedia.org/wiki/Scalp
- R8 — *Dynamics of stab wounds: force required for penetration of various cadaveric human tissues*, Forensic Sci Int. https://www.sciencedirect.com/science/article/abs/pii/S0379073899001152 ; Irish Examiner (10–20 N). https://www.irishexaminer.com/news/arid-20290990.html ; Heckmann 2023, *Piercing the surface*. https://onlinelibrary.wiley.com/doi/10.1111/1556-4029.15313 ; *Biaxial measurement of knife stab penetration*. https://arxiv.org/pdf/0811.3955 ; tenting value from a patent. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10034628
- R9 — ScienceDirect Topics, *Stab wound*. https://www.sciencedirect.com/topics/medicine-and-dentistry/stab-wound
- R10 — Univ. Utah WebPath, single vs double-edged knife wounds. https://webpath.med.utah.edu/FORHTML/FOR115.html
- R11 — *Pattern and Forensic Significance of Defense Injuries in Homicide Cases* (PMC11964116). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11964116/ ; *Pattern of defence injuries among homicidal victims*. https://www.sciencedirect.com/science/article/pii/S2090536X12000780
- R12 — *Assailant technique in knife slash attacks*. https://www.sciencedirect.com/science/article/abs/pii/S1353113102001578 ; *Knife crimes and facial injuries*, BDJ. https://www.nature.com/articles/s41415-019-0358-8 ; *Cranium-facial trauma by a cutting weapon*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9443784/
- R13 — *An autopsy study of 74 cases of cut throat injuries*. https://www.sciencedirect.com/science/article/pii/S2090536X14000781
- R14 — howMed, *Incised and stab wounds*. https://howmed.net/forensic/incised-and-stab-wounds/ ; ACEP Now, *Laceration or incised wound*. https://www.acepnow.com/article/laceration-incised-wound-know-difference/
- R15 — *Scalp laceration: an obvious 'occult' cause of shock*. https://pubmed.ncbi.nlm.nih.gov/10728511/ ; StatPearls, *Scalp laceration*. https://www.ncbi.nlm.nih.gov/books/NBK541038/ ; *Scalp laceration: still a cause of death… rural settings*. https://www.sciencedirect.com/science/article/pii/S2214751919300362 ; Arné, *Management of scalp hemorrhage and lacerations*, JSOM. https://jsomonline.org/wp-content/uploads/2024/02/2012111Arne.pdf

**Anatomy and vessels**
- R16 — TeachMeAnatomy, *The Scalp*. https://teachmeanatomy.info/head/areas/scalp/ ; Plastic Surgery Key, *Scalp anatomy*. https://plasticsurgerykey.com/scalp-anatomy/ ; Seppic, *Scalp physiology & anatomy*. https://www.seppic.com/article/scalp-physiology-anatomy
- R17 — *Morphometric measurement of cranial vault thickness* (PMC8827567). https://pmc.ncbi.nlm.nih.gov/articles/PMC8827567/ ; *Thickness measurement of alive human skull based on CT*. https://pubmed.ncbi.nlm.nih.gov/18027676/
- R18 — *Ultrasound guidance for internal jugular vein cannulation*, Can J Anesth. https://link.springer.com/article/10.1007/s12630-010-9291-7
- R19 — *Ultrasound assessment of blood flow in branches of the external carotid artery* (PMC13350631). https://pmc.ncbi.nlm.nih.gov/articles/PMC13350631/ ; ScienceDirect Topics, *Superficial temporal artery*. https://www.sciencedirect.com/topics/neuroscience/superficial-temporal-artery
- R20 — *Forehead versus forearm skin vascular responses* (PMC4187183). https://pmc.ncbi.nlm.nih.gov/articles/PMC4187183/ ; Kenhub, *Superficial arteries and veins of the face and scalp*. https://www.kenhub.com/en/library/anatomy/superficial-arteries-and-veins-of-the-face-and-scalp
- R21 — Medscape, *Bleeding time*. https://emedicine.medscape.com/article/2085022-overview ; ScienceDirect Topics, *Bleeding time*. https://www.sciencedirect.com/topics/biochemistry-genetics-and-molecular-biology/bleeding-time
- R22 — EBSCO Research Starters, *Antemortem injuries*. https://www.ebsco.com/research-starters/applied-sciences/antemortem-injuries/ ; MedicoApps, *Antemortem and postmortem wounds*. https://medicoapps.org/antemortem-and-postmortem-wounds/

**Bruises, abrasions, lacerations**
- R23 — Langlois & Gresham 1991, *The ageing of bruises*. https://pubmed.ncbi.nlm.nih.gov/1748358/ ; PDF: http://www.communitychildhealth.co.uk/cp/downloads-5/files/langloss.pdf
- R24 — forensicmed.co.uk, *Ageing bruising*. https://www.forensicmed.co.uk/wounds/blunt-force-trauma/bruises/ageing-bruising/ ; *The perception of yellow in bruises*. https://www.researchgate.net/publication/8228005_The_perception_of_yellow_in_bruises ; *Visual assessment of the timing of bruising by forensic experts*. https://www.researchgate.net/publication/41824834_Visual_assessment_of_the_timing_of_bruising_by_forensic_experts
- R25 — Nuzzolese et al., *Colorimetric scale for bruise age* (PMC5734826). https://pmc.ncbi.nlm.nih.gov/articles/PMC5734826/
- R26 — *Bruises: Is it a case of "the more we know, the less we understand?"*, FSMP 2015. https://link.springer.com/article/10.1007/s12024-015-9661-0 ; *Evaluating change in bruise colorimetry…* https://link.springer.com/article/10.1007/s12024-013-9452-4
- R27 — Godoy Medical Forensics, *Characteristics of bruises*. https://godoymedical.net/the-characteristics-of-bruises/ ; Biology Insights (low quality). https://biologyinsights.com/how-long-do-bruises-take-to-show-up/
- R28 — *On the relationships between applied force, photography technique, and bruise appearance*. https://pubmed.ncbi.nlm.nih.gov/31707237/ ; Wikipedia, *Bruise*. https://en.wikipedia.org/wiki/Bruise
- R29 — *Postmortem wound dating… abrasions* (PMC5457815). https://pmc.ncbi.nlm.nih.gov/articles/PMC5457815/ ; *Age estimation of abrasion by colour changes*, IJFCM. https://ijfcm.org/archive/volume/5/issue/2/article/14432 ; *Estimation of age of abrasion…*, IJFMT. https://medicopublication.com/index.php/ijfmt/article/view/19501
- R30 — StatPearls, *Abrasion*. https://www.ncbi.nlm.nih.gov/sites/books/NBK554465/ ; ScienceDirect Topics, *Skin abrasion*. https://www.sciencedirect.com/topics/pharmacology-toxicology-and-pharmaceutical-science/skin-abrasion
- R31 — PathologyOutlines, *Blunt force injuries*. https://www.pathologyoutlines.com/topic/forensicsbluntforce.html ; forensicmed.co.uk, *Lacerations*. https://www.forensicmed.co.uk/wounds/blunt-force-trauma/lacerations/ ; Pounder, *Lecture notes in forensic medicine*. http://www.chymist.com/Forensic%20Medicine%20Notes.pdf ; howMed, *Lacerations*. https://howmed.net/forensic/lacerations-types-and-forensic-importance/
- R32 — ScienceDirect Topics, *Laceration*. https://www.sciencedirect.com/topics/medicine-and-dentistry/laceration
- R33 — *Patterned bruising caused by an automobile tyre*, SAJS. https://scielo.org.za/pdf/sajsurg/v54n1/09.pdf ; *Autopsy case of tramline bruises*. https://www.sciencedirect.com/science/article/abs/pii/S1752928X22001512
- R34 — Sharkey et al. 2012, *Investigation of the force associated with the formation of lacerations and skull fractures*. https://link.springer.com/article/10.1007/s00414-011-0608-z ; Strathprints. https://strathprints.strath.ac.uk/43470/
- R35 — *Patterns of facial laceration from blunt trauma*. https://pubmed.ncbi.nlm.nih.gov/9145122/ ; *Relationship between aetiology and distribution of facial lacerations*. https://www.sciencedirect.com/science/article/pii/S1572346103000060 ; forensicmed.co.uk, *Patterns*. https://www.forensicmed.co.uk/wounds/blunt-force-trauma/patterns/

**Punches and facial fractures**
- R36 — Walilko, Viano, Bir 2005, *Biomechanics of the head for Olympic boxer punches to the face*. https://pubmed.ncbi.nlm.nih.gov/16183766/
- R37 — Omni Calculator, *Human punch force* (low quality). https://www.omnicalculator.com/sports/human-punch-force ; ArhFoundation (low quality). https://www.arhfoundation.org/force-punch-newtons-physics
- R38 — Nahum 1975, *The biomechanics of facial bone fracture*. https://pubmed.ncbi.nlm.nih.gov/1113592/ ; Hodgson 1967, *Tolerance of the facial bones to impact*. https://onlinelibrary.wiley.com/doi/abs/10.1002/aja.1001200109 ; Musculoskeletal Key, *Skull and facial bone injury biomechanics*. https://musculoskeletalkey.com/skull-and-facial-bone-injury-biomechanics/
- R39 — Yoganandan et al., *Biodynamics of steering wheel induced facial trauma*. https://www.sciencedirect.com/science/article/abs/pii/002243759190028T ; *Biomechanical impact of a zygoma complex fracture using human cadaver*. https://pubmed.ncbi.nlm.nih.gov/33770037/
- R40 — *Blunt force trauma in the human mandible: an experimental investigation*. https://www.sciencedirect.com/science/article/pii/S2665910721000839
- R41 — *Imaging in traumatic mandibular fractures* (PMC5594017). https://pmc.ncbi.nlm.nih.gov/articles/PMC5594017/ ; StatPearls, *Mandible fracture*. https://www.ncbi.nlm.nih.gov/sites/books/NBK507705/ ; StatPearls, *Mandible body fracture*. https://www.ncbi.nlm.nih.gov/books/NBK553119/
- R42 — StatPearls, *Le Fort fractures*. https://www.ncbi.nlm.nih.gov/books/NBK526060/ ; WikEM. https://wikem.org/wiki/Le_Fort_fractures
- R43 — StatPearls, *Orbital floor fracture*. https://www.ncbi.nlm.nih.gov/sites/books/NBK534825/ ; Medscape, *Orbital floor fractures, clinical*. https://emedicine.medscape.com/article/1218283-clinical
- R44 — *Buckling and hydraulic mechanisms in orbital blowout fractures*. https://pubmed.ncbi.nlm.nih.gov/16770178/ ; *Mechanisms of orbital floor fractures*. https://pubmed.ncbi.nlm.nih.gov/10826759/ ; *Pure hydraulic theory*. https://pubmed.ncbi.nlm.nih.gov/12020203/
- R45 — *Symptomatology of fractures of the zygomatic complex*. https://revodonto.bvsalud.org/scielo.php?script=sci_arttext&pid=S1808-52102012000200013 ; EyeWiki, *ZMC fractures*. https://eyewiki.org/Zygomaticomaxillary_Fractures ; Medscape, *Zygomatic complex fractures, clinical*. https://emedicine.medscape.com/article/1218360-clinical
- R46 — Merck Manual, *Nasal fractures*. https://www.merckmanuals.com/professional/injuries-poisoning/facial-trauma/nasal-fractures ; Clinical Advisor. https://www.clinicaladvisor.com/features/diagnosis-management-nasal-bone-fractures/ ; StatPearls, *Nasal fracture reduction*. https://ncbi.nlm.nih.gov/sites/books/NBK538299/
- R47 — *Experts consensus on management of tooth luxation and avulsion*, Int J Oral Sci 2024. https://www.nature.com/articles/s41368-024-00321-z ; StatPearls, *Avulsed tooth*. https://www.ncbi.nlm.nih.gov/sites/books/NBK539876/ ; Dental Update, *Luxation injuries*. https://www.dental-update.co.uk/content/dental-trauma/dental-trauma-part-1-acute-management-of-luxationdisplacement-injuries
- R48 — *Hemorrhage after extraction* (PMC6061292). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6061292/

**Scalp haematoma, skull, basal signs, eye**
- R49 — Wikipedia, *Subgaleal hemorrhage*. https://en.wikipedia.org/wiki/Subgaleal_hemorrhage ; Pediatric Imaging, *Subgaleal hematoma*. https://pediatricimaging.org/diseases/subgaleal-hematoma/ ; *POCUS to distinguish subgaleal and cephalohematoma* (PMC8143819). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8143819/
- R50 — Cleveland Clinic, *Goose egg on head*. https://health.clevelandclinic.org/goose-egg-on-head ; UPMC, *Head bumps*. https://share.upmc.com/2025/05/head-bump-hematoma/
- R51 — StatPearls, *Basilar skull fractures*. https://www.ncbi.nlm.nih.gov/sites/books/NBK470175/ ; StatPearls point-of-care. https://www.statpearls.com/point-of-care/18164 ; Wikipedia, *Battle's sign*. https://en.wikipedia.org/wiki/Battle%27s_sign
- R52 — StatPearls, *Raccoon sign*. https://www.ncbi.nlm.nih.gov/books/NBK542227/ ; WestJEM, *Raccoon eyes* (PMC2850869). https://pmc.ncbi.nlm.nih.gov/articles/PMC2850869/
- R53 — Wikipedia, *Black eye*. https://en.wikipedia.org/wiki/Black_eye ; Rhode Island Eye Institute. https://rieyeinstitute.com/article/black-eye-causes-treatment-and-when-to-worry/
- R54 — StatPearls, *Subconjunctival hemorrhage*. https://www.ncbi.nlm.nih.gov/sites/books/NBK551666/ ; Wikipedia, *Subconjunctival bleeding*. https://en.wikipedia.org/wiki/Subconjunctival_bleeding
- R55 — Hammer and implement studies:
  - *Head injuries caused by hammer blows: a case report and literature review* (2023). https://www.sciencedirect.com/science/article/pii/S266591072300004X
  - Buchaillet et al. 2016, *Specific characteristics of injuries inflicted by claw hammer*. https://pubmed.ncbi.nlm.nih.gov/27356305/
  - *Hammer blows to the head* (FSI 2019). https://pubmed.ncbi.nlm.nih.gov/31212143/
  - *Skull wounds linked with blunt trauma (hammer example)*. https://www.sciencedirect.com/science/article/abs/pii/S1344622312000752
  - *Energies of different assault tools in blunt force trauma* (2025). https://pubmed.ncbi.nlm.nih.gov/41478000/
  - *Impact energy of everyday items used for assault*. https://pubmed.ncbi.nlm.nih.gov/28963580/
  - *Biomechanical examination of blunt trauma due to baseball bat blows to the head* (80–100 J; skull threshold 14.1–68.5 J). https://www.researchgate.net/publication/261611644_Biomechanical_Examination_of_Blunt_Trauma_due_to_Baseball_Bat_Blows_to_the_Head
- R56 — Yoganandan et al. 1995, *Biomechanics of skull fracture*. https://pubmed.ncbi.nlm.nih.gov/8683617/ ; *Biomechanics of temporo-parietal skull fracture* (review PDF). https://waynecountydefendertraining.com/cap-archives/capwayne/handouts/2016/2017-02-24_Sierra-Tankersley-Biomechanics-of-Skull-Fracture.pdf ; *The tolerance of the frontal bone to blunt impact*, J Biomech Eng. https://asmedigitalcollection.asme.org/biomechanical/article-abstract/133/2/021004/383530/The-Tolerance-of-the-Frontal-Bone-to-Blunt-Impact ; *Development of skull fracture criterion…* https://www.sciencedirect.com/science/article/abs/pii/S1751616115004324 ; *Bioengineering approaches… cranial fracture* (Sci Rep). https://www.nature.com/articles/s41598-026-38313-0
- R57 — *Surgical management of depressed cranial fractures* (BTF guideline). https://pubmed.ncbi.nlm.nih.gov/16540744/ ; EM Daily, *Open & depressed skull fractures*. https://emdaily1.cooperhealth.org/content/back-basics-open-depressed-skull-fractures
- R58 — forensicmed.co.uk, *Skull fracture*. https://www.forensicmed.co.uk/pathology/head-injury/skull-fracture/ ; Wikipedia, *Skull fracture*. https://en.wikipedia.org/wiki/Skull_fracture ; ScienceDirect Topics, *Skull fracture*. https://www.sciencedirect.com/topics/veterinary-science-and-veterinary-medicine/skull-fracture
- R59 — Radiopaedia, *Ping pong skull fracture*. https://radiopaedia.org/articles/ping-pong-skull-fracture ; *"Ping-pong" fracture: an exclusive entity of neonates and infants?* (PMC10246367). https://pmc.ncbi.nlm.nih.gov/articles/PMC10246367/
- R60 — *Injury risk in professional boxing*. https://pubmed.ncbi.nlm.nih.gov/16295814/ ; *Ocular injuries in competitive combat sports in Texas* (PMC12548626). https://pmc.ncbi.nlm.nih.gov/articles/PMC12548626/
- R61 — *Kings to cowards: one-punch assaults*. https://www.researchgate.net/publication/323538989_Kings_to_Cowards_One-Punch_Assaults ; *Differentiating fatal one-punch assaults from standing height falls*. https://www.tandfonline.com/doi/abs/10.1080/00450618.2023.2292126
- R62 — RCEMLearning, *Boxing and facial injuries*. https://www.rcemlearning.co.uk/foamed/boxing-and-facial-injuries/ ; WBA, *Common injuries in boxing*. https://www.wbaboxing.com/box-medical-articles/some-common-injuries-in-boxing
- R63 — UpToDate, *Intra-oral lacerations*. https://www.uptodate.com/contents/assessment-and-management-of-intra-oral-lacerations ; Suture.app, *Through-and-through*. https://www.suture.app/techniques/through-and-through/

**Burns**
- R64 — The Plastics Fella, *Burn depth*. https://www.theplasticsfella.com/burn-depth/ ; *Classification of burn depth* (PMC10948199). https://pmc.ncbi.nlm.nih.gov/articles/PMC10948199/ ; Merck Manual, *Burns*. https://www.merckmanuals.com/professional/injuries-poisoning/burns/burns ; UpToDate, *Assessment and classification of burn injury*. https://www.uptodate.com/contents/assessment-and-classification-of-burn-injury/print
- R65 — *Educational case: burn injury* (PMC8637691). https://pmc.ncbi.nlm.nih.gov/articles/PMC8637691/
- R66 — Moritz & Henriques 1947. https://pubmed.ncbi.nlm.nih.gov/19970955/ ; *A review of the evidence for threshold of burn injury*. https://pubmed.ncbi.nlm.nih.gov/28536038/ ; A.O. Smith Bulletin 34. https://www.hotwater.com/info-center/technical-bulletins/bulletin-34.html ; *Predictor of the depth of burn injuries*. https://www.researchgate.net/publication/328631160_Predictor_of_the_depth_of_burn_injuries_A_time-temperature_relationship
- R67 — *The exposure of fire victims to heat* (SFPE-type chapter). https://efiling.energy.ca.gov/GetDocument.aspx?tn=65949 ; NIST SP 1102 *Fire Facts*. https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=903600
- R68 — ASTM F1930. https://store.astm.org/f1930-18.html ; Arcwear, *F1930 manikin test*. https://arcwear.com/astm-f1930-2/
- R69 — Wikipedia, *Jet fire*. https://en.wikipedia.org/wiki/Jet_fire ; *Flame characteristics… jet fire impingement*. https://www.sciencedirect.com/science/article/abs/pii/S0379711222001862
- R70 — Wikipedia, *Propane torch*. https://en.wikipedia.org/wiki/Propane_torch ; Wikipedia, *MAPP gas*. https://en.wikipedia.org/wiki/MAPP_gas ; Bullfinch, *Flame temperatures*. https://bullfinch-gas.co.uk/safety-and-technical/10-safety-technical/26-flame-temperatures
- R71 — *Comparing the reported burn conditions… porcine models: a systematic review* (PMC7949960). https://pmc.ncbi.nlm.nih.gov/articles/PMC7949960/ ; *A porcine burn model* (Springer Protocols). https://link.springer.com/protocol/10.1385/1-59259-332-1:107
- R72 — Singer et al., *Validation of a vertical progression porcine burn model*. https://pubmed.ncbi.nlm.nih.gov/21841494/
- R73 — *Dynamics of tissue shrinkage during ablative temperature exposures* (PMC3924587). https://pmc.ncbi.nlm.nih.gov/articles/PMC3924587/ ; Dermatology Times, *Thermally induced skin-tightening possibly directional*. https://www.dermatologytimes.com/view/thermally-induced-skin-tightening-possibly-directional
- R74 — StatPearls, *Escharotomy*. https://www.ncbi.nlm.nih.gov/books/NBK482120/ ; MSD Manual, *How to do burn escharotomy*. https://www.msdmanuals.com/professional/injuries-poisoning/how-to-do-skin-soft-tissue-and-minor-surgical-procedures/how-to-do-burn-escharotomy
- R75 — Medscape, *Forensic pathology of thermal injuries*. https://emedicine.medscape.com/article/1975728-overview ; Wohlsein et al. 2016, *Thermal injuries in veterinary forensic pathology*. https://journals.sagepub.com/doi/10.1177/0300985816643368
- R76 — Bohnert, Rost, Pollak 1998, *The degree of destruction of human bodies in relation to the duration of the fire*. https://www.sciencedirect.com/science/article/abs/pii/S0379073898000760
- R77 — VCU Student Health, *Burn care fact sheet*. https://health.students.vcu.edu/media/student-affairs-sites/ushs/docs/BURNCARE.pdf ; IU Health, *Understanding burns*. https://iuhealth.org/thrive/understanding-burns-and-when-to-seek-medical-treatment
- R78 — Slate Explainer, *What does burning human flesh smell like?* http://www.slate.com/articles/news_and_politics/explainer/2007/03/barbyou.html
- R79 — Salon Worthy Hair, *At what temperature does hair burn?* (low quality). https://salonworthyhair.com/damaged/heat/at-what-temperature-does-burn/
- R80 — Galloway 2024, *Bone color changes…*, WIREs Forensic Sci. https://wires.onlinelibrary.wiley.com/doi/10.1002/wfs2.1517 ; *Half a century of systematic research on heat-induced colour changes in bone*. https://www.sciencedirect.com/science/article/pii/S1355030623000801
- R81 — *Thermal injury induces early blood vessel occlusion in a porcine model of brass comb burn*, Sci Rep. https://www.nature.com/articles/s41598-021-91874-0 ; RCEMLearning, *Burns pathophysiology*. https://www.rcemlearning.co.uk/modules/major-trauma-burns/lessons/pathophysiology-36/
- R82 — Wikipedia, *Wick effect*. https://en.wikipedia.org/wiki/Wick_effect ; Scientific American, *Understanding the wick effect*. https://www.scientificamerican.com/blog/cocktail-party-physics/burn-baby-burn-understanding-the-wick-effect/

**Misc.**
- R83 — RCEMLearning, *Abrasions*. https://www.rcemlearning.co.uk/modules/soft-tissue-and-skin-injury-descriptions-in-the-ed/lessons/pathophysiology-34/topic/abrasions/
- R84 — forensicmed.co.uk, *Chopping wounds*. https://www.forensicmed.co.uk/wounds/sharp-force-trauma/chopping-wounds/ ; AMBOSS, *Forensic traumatology*. https://www.amboss.com/us/knowledge/forensic-traumatology
- R85 — *Identifying blunt force traumatic injury on thermally altered remains* (PMC8773201). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8773201/ ; Utah WebPath (thermal). https://webpath.med.utah.edu/FORHTML/FOR178.html
- R86 — Stephan 2018, *Tallied facial soft tissue thicknesses* (values not retrieved; ranges in §1 are `[K]`) ; *Systematic review on forensic craniofacial reconstruction I: facial soft-tissue thickness*. https://pubmed.ncbi.nlm.nih.gov/37531497/
