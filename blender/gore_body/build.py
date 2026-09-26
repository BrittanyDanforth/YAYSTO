"""Full-body build orchestration (owner B0).  Plan §5.1-5.2.

Usage (bpy module or Blender binary)::

    python3 build.py [--stage STAGE ...] [--quick] [--no-bake] [--render] [--no-save] [--no-verify]
    blender -b --python build.py -- [same options]

Stages: placeholder | skin | head | skeleton | viscera | neuro | vascular | rig | bake | export | props | all

Every run starts from an empty scene and does:

1. **placeholder**: the complete B0 stand-in subject with final names (always built, it is the
   fallback for everything that is not built yet);
2. **geometry stages** (skin, head, skeleton, viscera, neuro, vascular): a requested stage is
   built by its package module and cached (``.cache/<stage>-<hash>.blend``, keyed on the
   stage's sources, ``gb_common``, ``gb_data`` and the Blender version); a stage that is not
   requested is loaded from its cache when one exists for the current sources, else the
   placeholder objects stay.  A builder that raises ``gb_common.NotBuiltYet`` is reported as
   ``pending (<owner>)``;
3. **rig**: weights, parenting and the single ARMATURE modifier on every mesh (``rig.skin_all``);
4. **bake** (``all``/``bake`` without ``--no-bake``): look-dev and texture bakes (B7);
5. **export**: GB_Subject.glb + LOD1 + JSON sidecars + manifest (``export.export_subject``);
6. **props** (``all``/``props``): weapons.glb, room.glb (B8);
7. saves ``gore_body.blend`` and runs ``verify.verify_all`` (exit code 1 on failures).

``--stage placeholder`` therefore means "placeholder only, no caches"; ``--stage all`` builds
every stage.  Timings are printed and stored in the manifest.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402

STAGES = ("placeholder", "skin", "head", "skeleton", "viscera", "neuro", "vascular", "rig", "bake", "export",
          "props")
GEOMETRY = ("skin", "head", "skeleton", "viscera", "neuro", "vascular")
OWNER = {"placeholder": "B0", "skin": "B1", "head": "B2", "skeleton": "B3", "viscera": "B4", "neuro": "B4",
         "vascular": "B5", "rig": "B6", "bake": "B7", "export": "B6", "props": "B8"}
SOURCES = {"skin": ["body_skin.py", "uv.py"], "head": ["head_integration.py", "uv.py"],
           "skeleton": ["skeleton.py"], "viscera": ["viscera.py"], "neuro": ["neuro.py"],
           "vascular": ["vascular.py"]}


def _stage_skin():
    import body_skin
    out = dict(body_skin.build_body_skin())
    skin = out.get("GB_Body")
    out.update(body_skin.build_shorts(skin))
    out.update(body_skin.build_muscle_shell(skin))
    return out


def _stage_head():
    import head_integration as hi
    out = dict(hi.build_head())
    hi.build_face_shapes(out["GB_Head"])
    out.update(hi.build_eye_fx())
    out.update(hi.build_hair_cards())
    return out


def _stage_skeleton():
    import skeleton
    out = dict(skeleton.build_skeleton())
    out.update(skeleton.build_fracture_variants())
    return out


def _stage_viscera():
    import viscera
    return dict(viscera.build_organs())


def _stage_neuro():
    import neuro
    return dict(neuro.build_cord())


def _stage_vascular():
    import vascular
    return dict(vascular.build_vessels())


BUILDERS = {"skin": _stage_skin, "head": _stage_head, "skeleton": _stage_skeleton, "viscera": _stage_viscera,
            "neuro": _stage_neuro, "vascular": _stage_vascular}


def parse(args):
    """Parse the command line into (stages set, options dict)."""
    stages = []
    opts = {"quick": False, "bake": True, "render": False, "save": True, "verify": True}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--stage":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                stages += args[i].split(",")
                i += 1
            continue
        if a == "--quick":
            opts["quick"] = True
        elif a == "--no-bake":
            opts["bake"] = False
        elif a == "--render":
            opts["render"] = True
        elif a == "--no-save":
            opts["save"] = False
        elif a == "--no-verify":
            opts["verify"] = False
        else:
            raise SystemExit(f"unknown option {a!r}\n{__doc__}")
        i += 1
    stages = stages or ["placeholder"]
    if "all" in stages:
        stages = list(STAGES)
    bad = [s for s in stages if s not in STAGES]
    if bad:
        raise SystemExit(f"unknown stage(s) {bad}; choose from {STAGES + ('all',)}")
    return set(stages), opts


def run(stages, opts):
    """Run the build; returns (status dict, verify result or None)."""
    import bpy
    import export
    import placeholder
    import rig
    t_all = time.perf_counter()
    status = {}
    gbc.reset_scene()
    gbc.collections()
    gbc.log(f"stages {sorted(stages, key=STAGES.index)}  quick={opts['quick']}  blender {bpy.app.version_string}")
    with gbc.Timer("stage placeholder"):
        objs = placeholder.build_placeholder(quick=opts["quick"])
    status["placeholder"] = "built"
    only_placeholder = stages == {"placeholder"}
    for st in GEOMETRY:
        cache = gbc.stage_cache(st, [os.path.join(gbc.HERE, f) for f in SOURCES[st]],
                                extra="quick" if opts["quick"] else "full")
        if st in stages:
            try:
                with gbc.Timer(f"stage {st}"):
                    new = BUILDERS[st]()
                objs.update(new)
                cache.save([o for o in new.values() if o is not None])
                status[st] = "built"
            except gbc.NotBuiltYet as exc:
                status[st] = f"pending ({exc.owner}): placeholder stands in"
        elif not only_placeholder and cache.hit:
            with gbc.Timer(f"stage {st} (cache)"):
                objs.update(cache.load())
            status[st] = "cached"
        else:
            status[st] = "placeholder"
    with gbc.Timer("stage rig (skin weights)"):
        present = {n: bpy.data.objects[n] for n in gbc.exported_mesh_names(0) + gbc.exported_mesh_names(1)
                   if n in bpy.data.objects}
        rig.skin_all(present)
    status["rig"] = "v0 weights (B0 draft; B6 owns the final model)"
    if "bake" in stages and opts["bake"]:
        try:
            import bake
            import lookdev
            with gbc.Timer("stage bake"):
                lookdev.build_materials()
                bake.bake_all(present, os.path.join(gbc.SUBJECT_OUT, "textures"))
                bake.bake_tileables(os.path.join(gbc.SUBJECT_OUT, "textures"))
                bake.bake_painter_inputs(present, os.path.join(gbc.SUBJECT_OUT, "textures"))
            status["bake"] = "built"
        except gbc.NotBuiltYet as exc:
            status["bake"] = f"pending ({exc.owner})"
    else:
        status["bake"] = "skipped"
    if "props" in stages:
        try:
            with gbc.Timer("stage props"):
                export.export_props(gbc.PROPS_OUT)
            status["props"] = "built"
        except gbc.NotBuiltYet as exc:
            status["props"] = f"pending ({exc.owner})"
    pending = {k: v for k, v in status.items() if v.startswith(("pending", "placeholder", "skipped"))}
    with gbc.Timer("stage export"):
        exp = export.export_subject(objs, gbc.SUBJECT_OUT, pending=pending, timings=dict(gbc.Timer.records),
                                    quick=opts["quick"])
    status["export"] = f"{len(exp['glb'])} glb + {len(exp['sidecars'])} sidecars + manifest"
    if opts["render"]:
        with gbc.Timer("renders"):
            gbc.render_views("build", samples=24)
    if opts["save"]:
        with gbc.Timer("save .blend"):
            bpy.ops.wm.save_as_mainfile(filepath=gbc.BLEND_PATH, compress=True)
    res = None
    if opts["verify"]:
        import verify
        with gbc.Timer("verify"):
            res = verify.verify_all()
    # the manifest carries the final timings too
    total = time.perf_counter() - t_all
    gbc.Timer.records["total"] = round(total, 2)
    export.write_manifest(gbc.SUBJECT_OUT, exp["glb"], exp["sidecars"], pending, dict(gbc.Timer.records),
                          opts["quick"])
    gbc.log("stage status: " + "; ".join(f"{k}: {v}" for k, v in status.items()))
    gbc.log(f"total {total:.1f} s")
    return status, res


def main():
    stages, opts = parse(gbc.script_args())
    _status, res = run(stages, opts)
    if res is not None:
        import verify
        if verify.failures(res):
            sys.exit(1)


if __name__ == "__main__":
    main()
