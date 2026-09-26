"""Anatomical data tables for the full body, transcribed from the bibles.

Single source of anatomical numbers for every work package (plan §5.2).
Units: metres, body frame (+Z up, face -Y, character's left +X, origin on the
floor between the feet) unless a name says otherwise (``_mm``, ``_deg``,
``_g``, ``_kg``, ``_ml_min``).  Bilateral rows are given for the LEFT side and
mirrored (x -> -x) by the helper functions.

Evidence tags carried in the rows (bible convention, RB §0.1):
  V verified, C consistent with literature, E engineering estimate (tune),
  G game choice, K author knowledge (QA re-check), M/L medium/low confidence.
Rows added by B0 where the bible names a structure but gives no numbers are
tagged ``"E"`` and ``fit="B0"`` so the owning package can refine them.

Modules
-------
landmarks   RB §7.1 landmark CSV, RB §1.2 head contract table, girths (RB §7.1 / R05 §2.1)
rig_table   plan §3.1.1 bones (39), §3.1.2 bodies/joints/limits/caps
segments    segment/region codes (plan §5.5), segment masses (RB §7.2)
vertebrae   RB §7.3 vertebra CSV (25 rows incl. S1), cord segment mapping (RB §4.6), brainstem (RB §7.4)
ribs        RB §7.3 rib table + sternum (R05 §5.1)
bones       long-bone dimensions and girdle/pelvis/hand/foot points (RB §7.3, R05 §6-8)
organs      RB §7.5 organ CSV, tube CSV, organ facts, colours, compartments
vessels     RB §3.3 vessel table (+ beds, collaterals, pulse delays); B5 extends
nerves      main nerves as data-only curves (plan §3.4.1; E/K fits)
myotomes    plan §3.2 myotome map, respiratory capacity by level (RB §4.6)
dermatomes  plan §5.5 dermatome codes and R04 §6.2 anchors
tissue      RB §7.6 tissue layers, skin thickness, fat map, cut colours, bone cortex
"""
