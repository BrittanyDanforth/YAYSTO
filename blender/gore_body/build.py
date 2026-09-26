"""Full-body build orchestration (owner B0).  Plan §5.1-5.2.

Usage (bpy module or Blender binary)::

    python3 build.py [--stage STAGE ...] [--quick] [--no-bake] [--render] [--no-save] [--no-verify]
                     [--force-export]
    blender -b --python build.py -- [same options]

Stages: placeholder | skin | head | skeleton | viscera | neuro | vascular | rig | bake | export | props | all

Every run starts from an empty scene and does:

1. **placeholder**: the complete B0 stand-in subject with final names (always built, it is the
   fallback for anything that is not built);
2. **geometry stages** (skin B1, head B2, skeleton B3, viscera B4, neuro B4, vascular B5): a requested
   stage is built by its package module and cached (``.cache/<stage>-<key>.blend`` plus the side files
   it wrote, ``.cache/<stage>-<key>.files``).  The key (``stage_key``) covers the stage's whole import
   closure (``SOURCES``), ``gb_common``, ``gb_geom``, ``gb_data``, the head project's sources, the
   Blender version and the key of the upstream stage, so a change anywhere upstream (including the
   head team's ``gore_head`` files) invalidates it.  A stage that is not requested is loaded from its
   cache when one exists for the current sources, else the placeholder objects stay;
3. **rig** (B6): weights, followers, key poses and the single ARMATURE modifier on every mesh;
4. **bake** (``all``/``bake`` without ``--no-bake``): look-dev and texture bakes (B7);
5. **export**: GB_Subject.glb + LOD1 + JSON sidecars + manifest (``export.export_subject``);
6. **props** (``all``/``props``): weapons.glb, room.glb (B8);
7. saves ``gore_body.blend`` (with the GBL_* look-dev materials assigned when they exist) and runs
   ``verify.verify_all`` (exit code 1 on failures).

``--quick`` builds coarse meshes and quick bakes for iteration.  Its outputs go to
``.cache/quick_out`` (never into ``gore-game/assets/generated``) unless ``--force-export`` is given,
and full-accuracy acceptance checks are reported as ``skip``.

``--stage placeholder`` therefore means "placeholder only, no caches"; ``--stage all`` builds
every stage.  Timings are printed and stored in the manifest.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402

QUICK_OUT = os.path.join(gbc.CACHE_DIR, "quick_out")     # --quick output root (not committed)
STAGES = ("placeholder", "skin", "head", "skeleton", "viscera", "neuro", "vascular", "rig", "bake", "export",
          "props")
GEOMETRY = ("skin", "head", "skeleton", "viscera", "neuro", "vascular")
OWNER = {"placeholder": "B0", "skin": "B1", "head": "B2", "skeleton": "B3", "viscera": "B4", "neuro": "B4",
         "vascular": "B5", "rig": "B6", "bake": "B7", "export": "B6", "props": "B8"}
# Import closure of every geometry stage (its own module plus every body module it imports, directly or
# lazily).  gb_common, gb_geom, gb_data and the head project's sources are always part of the key
# (gb_common.StageCache).  Each stage key is also chained to the key of the stage before it in GEOMETRY
# (skin -> head -> skeleton -> viscera -> neuro -> vascular) because later stages load/measure the
# earlier stages' geometry, so an upstream rebuild always invalidates everything downstream.
SOURCES = {"skin": ["body_skin.py", "uv.py", "placeholder.py", "head_integration.py"],
           "head": ["head_integration.py", "uv.py", "placeholder.py", "body_skin.py", "rig.py"],
           "skeleton": ["skeleton.py", "placeholder.py", "body_skin.py"],
           "viscera": ["viscera.py", "placeholder.py", "body_skin.py", "skeleton.py"],
           "neuro": ["neuro.py", "viscera.py", "placeholder.py", "skeleton.py"],
           "vascular": ["vascular.py", "placeholder.py", "rig.py"]}
# files a geometry stage writes into SUBJECT_OUT besides its objects: stored next to the stage cache and
# restored (with the current build_id) when the stage is loaded from cache, so every exported file set is
# complete and consistent even when stages come from the cache or the output root is redirected (--quick).
STAGE_FILES = {"skin": ["textures/body_maps.json", "textures/body_tissue_depth.png", "textures/body_tension.png"],
               "head": ["textures/hair_cards.png"],
               "skeleton": ["bones.json"]}
_KEYS = {}


def stage_cache(stage, quick=False):
    """The ``gb_common.StageCache`` of a geometry ``stage`` (import closure + upstream stage key)."""
    mode = "quick" if quick else "full"
    i = GEOMETRY.index(stage)
    upstream = stage_cache(GEOMETRY[i - 1], quick).key if i > 0 else ""
    cache = gbc.stage_cache(stage, [os.path.join(gbc.HERE, f) for f in SOURCES[stage]],
                            extra=f"{mode}|upstream={upstream}")
    _KEYS[stage] = cache.key
    return cache


def stage_key(stage, quick=False):
    """The cache key (16 hex) of a geometry stage; also used by the modules' own __main__ test paths."""
    return stage_cache(stage, quick).key


def _files_dir(cache):
    return cache.path[:-len(".blend")] + ".files"


def _store_stage_files(stage, cache):
    """Copy the side files a freshly built stage wrote into SUBJECT_OUT next to its cache."""
    import shutil
    base = os.path.join(gbc.CACHE_DIR)
    for old in os.listdir(base):
        if old.startswith(stage + "-") and old.endswith(".files") and os.path.join(base, old) != _files_dir(cache):
            shutil.rmtree(os.path.join(base, old), ignore_errors=True)
    for rel in STAGE_FILES.get(stage, []):
        src = os.path.join(gbc.SUBJECT_OUT, rel)
        if os.path.exists(src):
            dst = os.path.join(_files_dir(cache), rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)


def _restore_stage_files(stage, cache):
    """Put a cached stage's side files back into SUBJECT_OUT, stamping JSON envelopes with this build_id."""
    import json
    import shutil
    restored = []
    for rel in STAGE_FILES.get(stage, []):
        src = os.path.join(_files_dir(cache), rel)
        if not os.path.exists(src):
            continue
        dst = os.path.join(gbc.SUBJECT_OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if rel.endswith(".json"):
            with open(src, encoding="utf-8") as fh:
                doc = json.load(fh)
            doc["build_id"] = gbc.build_id()
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(doc, indent=1, ensure_ascii=False, allow_nan=False) + "\n")
        else:
            shutil.copyfile(src, dst)
        restored.append(rel)
    return restored


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
    opts = {"quick": False, "bake": True, "render": False, "save": True, "verify": True, "force_export": False}
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
        elif a == "--force-export":
            opts["force_export"] = True
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
    if opts["quick"]:
        # quick builds are for iteration: coarse meshes and quick bakes, written to a scratch output root
        # so they never overwrite the committed deliverables in gore-game/assets/generated
        os.environ["GB_BAKE_QUICK"] = "1"
    if os.environ.get("GB_OUTPUT_ROOT"):          # verify.py --reproduce builds into a temporary root
        gbc.set_output_root(os.environ["GB_OUTPUT_ROOT"])
    elif opts["quick"] and not opts.get("force_export"):
        gbc.set_output_root(QUICK_OUT)
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
        cache = stage_cache(st, opts["quick"])
        if st in stages:
            try:
                with gbc.Timer(f"stage {st}"):
                    new = BUILDERS[st]()
                objs.update(new)
                cache.save([o for o in new.values() if o is not None])
                _store_stage_files(st, cache)
                status[st] = "built"
            except gbc.NotBuiltYet as exc:
                status[st] = f"pending ({exc.owner}): placeholder stands in"
        elif not only_placeholder and cache.hit:
            with gbc.Timer(f"stage {st} (cache)"):
                objs.update(cache.load())
                _restore_stage_files(st, cache)
            status[st] = "cached"
        else:
            status[st] = "placeholder"
    with gbc.Timer("stage rig (skin weights)"):
        present = {n: bpy.data.objects[n] for n in gbc.exported_mesh_names(0) + gbc.exported_mesh_names(1)
                   if n in bpy.data.objects}
        rig.skin_all(present)
    status["rig"] = "built (B6): skin weights, followers, poses"
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
                                    quick=opts["quick"], stage_keys=dict(_KEYS), status=dict(status))
    status["export"] = f"{len(exp['glb'])} glb + {len(exp['sidecars'])} sidecars + manifest"
    if opts["render"]:
        with gbc.Timer("renders"):
            gbc.render_views("build", samples=24)
    if opts["save"]:
        with gbc.Timer("save .blend"):
            blend = os.path.join(QUICK_OUT, "gore_body_quick.blend") if opts["quick"] else gbc.BLEND_PATH
            bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    res = None
    if opts["verify"]:
        import verify
        verify.CONTEXT.update({"quick": bool(opts["quick"]), "bake": status.get("bake", ""),
                               "stage_keys": dict(_KEYS), "status": dict(status)})
        with gbc.Timer("verify"):
            res = verify.verify_all()
    # the manifest carries the final timings too
    total = time.perf_counter() - t_all
    gbc.Timer.records["total"] = round(total, 2)
    export.write_manifest(gbc.SUBJECT_OUT, exp["glb"], exp["sidecars"], pending, dict(gbc.Timer.records),
                          opts["quick"], stage_keys=dict(_KEYS), status=dict(status))
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
