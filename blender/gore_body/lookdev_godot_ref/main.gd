extends Node3D
# B7 reference stage (plan §8.2 B7 acceptance "Godot vs Cycles renders of the reference stage"):
# loads the exported GB_Subject.glb at runtime (GLTFDocument, no import step), puts the baked texture
# sets on the skin/shorts/mouth with plain StandardMaterial3D, uses the cameras of lookdev.TURNTABLE["ref"]
# and saves godot_<view>.png.  Run (from the repo root):
#   xvfb-run -a godot --path blender/gore_body/lookdev_godot_ref --rendering-driver vulkan -- \
#       <abs path GB_Subject.glb> <abs textures dir> <abs output dir>
var glb := ""
var tex_dir := ""
var out_dir := ""
var views := {
	"body_front": [Vector3(0, 0.95, 3.2), Vector3(0, 0.9, 0), 50.0],
	"body_three_q": [Vector3(-2.05, 1.15, 2.45), Vector3(0, 0.9, 0), 50.0],
	"head_three_q": [Vector3(-0.52, 1.66, 0.52), Vector3(0, 1.64, 0.02), 85.0],
	"torso_front": [Vector3(0, 1.30, 1.45), Vector3(0, 1.22, 0), 50.0],
}

func _tex(name: String, srgb: bool) -> ImageTexture:
	var img := Image.load_from_file(tex_dir + "/" + name)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)

func _mat(set_name: String, skin: bool) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_texture = _tex(set_name + "_albedo.png", true)
	m.normal_enabled = true
	m.normal_texture = _tex(set_name + "_normal.png", false)
	var orm := _tex(set_name + "_orm.png", false)
	m.roughness_texture = orm
	m.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_GREEN
	m.roughness = 1.0
	m.metallic = 0.0
	m.ao_enabled = true
	m.ao_texture = orm
	m.ao_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
	if skin:
		m.subsurf_scatter_enabled = true
		m.subsurf_scatter_strength = 0.35
		m.subsurf_scatter_skin_mode = true
	return m

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	glb = args[0]
	tex_dir = args[1]
	out_dir = args[2]
	var doc := GLTFDocument.new()
	var st := GLTFState.new()
	var err := doc.append_from_file(glb, st)
	if err != OK:
		push_error("glb load failed %d" % err)
		get_tree().quit(1)
		return
	var scene := doc.generate_scene(st)
	add_child(scene)
	var mats := {"GB_Body": _mat("body", true), "GB_Head": _mat("head", true), "GB_Shorts": _mat("shorts", false),
		"GB_Mouth": _mat("mouth", false)}
	var show := ["GB_Body", "GB_Head", "GB_Shorts", "GB_Mouth", "GB_Eye_L", "GB_Eye_R", "GB_BrowLash"]
	for n in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		mi.visible = mi.name in show
		if mi.name in mats:
			for s in range(mi.mesh.get_surface_count()):
				if mi.name == "GB_Head" and s == 1:
					continue
				mi.set_surface_override_material(s, mats[mi.name])
	# stage lights like gb_common.setup_stage (Blender z-up -> Godot y-up: (x, z, -y))
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.03, 0.032, 0.036)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.05, 0.052, 0.058)
	e.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.environment = e
	add_child(env)
	for L in [[Vector3(-2.2, 3.0, 3.0), 9.0, Color(1, 0.96, 0.9)], [Vector3(3.0, 1.4, 2.4), 3.0, Color(0.85, 0.9, 1.0)],
			[Vector3(1.2, 2.6, -3.2), 10.0, Color(1, 0.97, 0.95)]]:
		var l := OmniLight3D.new()
		l.position = L[0]
		l.light_energy = L[1]
		l.light_color = L[2]
		l.omni_range = 12.0
		l.omni_attenuation = 2.0
		l.shadow_enabled = true
		add_child(l)
	var floor := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(12, 12)
	floor.mesh = pm
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.045, 0.047, 0.05)
	floor.material_override = fm
	add_child(floor)
	var cam := Camera3D.new()
	add_child(cam)
	cam.current = true
	for key in views:
		var v = views[key]
		cam.position = v[0]
		cam.look_at(v[1], Vector3.UP)
		cam.fov = rad_to_deg(2.0 * atan(18.0 / v[2]))   # Blender AUTO sensor fit: 36 mm on the long (vertical) side
		for i in range(6):
			await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(out_dir + "/godot_" + key + ".png")
	get_tree().quit()
