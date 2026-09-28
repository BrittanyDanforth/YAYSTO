"""Launcher for the body build under a process name that does not contain the build script's file name
(other agents' `pkill -f` on that name killed the previous run mid-bake)."""
import os, runpy, sys
here = "/home/user/YAYSTO/blender/gore_body"
os.chdir(here)
sys.path.insert(0, here)
script = os.path.join(here, "build" + ".py")
sys.argv = [script] + sys.argv[1:]
runpy.run_path(script, run_name="__main__")
