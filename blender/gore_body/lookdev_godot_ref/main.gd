extends Node3D
# B7 reference stage (plan §8.2 B7 acceptance "Godot vs Cycles renders of the reference stage"):
# loads the exported GB_Subject.glb at runtime (GLTFDocument, no import step), puts the baked texture
# sets on the skin/shorts/mouth with plain StandardMaterial3D, the eyes with a small iris/sclera/cornea shader
# (eye_iris_albedo + eye_sclera_albedo) and the brows/lashes as alpha-scissor cards (hair_cards.png),
# uses the cameras of lookdev.TURNTABLE["ref"]
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
	"eye_close": [Vector3(0.02, 1.690, 0.22), Vector3(0.0315, 1.684, 0.0475), 85.0],
	"neck_side": [Vector3(-0.75, 1.57, 0.02), Vector3(0, 1.53, 0.005), 85.0],
	"body_back": [Vector3(0, 0.95, -3.2), Vector3(0, 0.9, 0), 50.0],
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

const EYE_SHADER := """
shader_type spatial;
render_mode blend_mix, cull_back;
uniform sampler2D sclera_tex : source_color, filter_linear_mipmap;
uniform sampler2D iris_tex : source_color, filter_linear_mipmap;
uniform float iris_uv_radius;   // UV radius of the iris image edge (azimuthal-equidistant eye UV about the gaze)
void fragment() {
	vec4 sc = texture(sclera_tex, UV);
	// iris from the eye's own UV (centred on the gaze pole at (0.5, 0.5)), so it follows the eye bone when the
	// eye rotates (fix round 3: the model-space projection stayed put while the globe turned)
	vec2 iuv = vec2(0.5) + (UV - vec2(0.5)) * (0.5 / iris_uv_radius);
	vec3 iris = texture(iris_tex, iuv).rgb;
	float inside = step(length(UV - vec2(0.5)), iris_uv_radius);
	vec3 col = mix(iris, sc.rgb, mix(1.0, sc.a, inside));
	ALBEDO = col;
	ROUGHNESS = mix(0.06, 0.18, sc.a);
	SPECULAR = 0.6;
	CLEARCOAT = 1.0;
	CLEARCOAT_ROUGHNESS = 0.02;
	SSS_STRENGTH = 0.15 * sc.a;
}
"""

func _eye_mat(_mi: MeshInstance3D, iris_r: float) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = EYE_SHADER
	m.shader = sh
	m.set_shader_parameter("sclera_tex", _tex("eye_sclera_albedo.png", true))
	m.set_shader_parameter("iris_tex", _tex("eye_iris_albedo.png", true))
	# azimuthal-equidistant UV (head_integration._eye_arrays): uv radius = 0.5 * polar angle / pi
	var polar: float = asin(clamp(iris_r / 0.012, 0.0, 1.0))
	m.set_shader_parameter("iris_uv_radius", 0.5 * polar / PI)
	return m

func _lash_mat() -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_texture = _tex("hair_cards.png", true)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.alpha_scissor_threshold = 0.5
	# alpha-to-coverage (MSAA): soft strand edges instead of hard black lines / specks (fix round 3)
	m.alpha_antialiasing_mode = BaseMaterial3D.ALPHA_ANTIALIASING_ALPHA_TO_COVERAGE_AND_TO_ONE
	m.alpha_antialiasing_edge = 0.3
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.roughness = 0.55
	return m

func _iris_radius() -> float:
	var f := FileAccess.open(tex_dir + "/textures.json", FileAccess.READ)
	if f == null:
		return 0.0075
	var j = JSON.parse_string(f.get_as_text())
	return float(j["data"]["eyes"]["iris"]["radius_m"])

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
	var iris_r := _iris_radius()
	for n in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		mi.visible = mi.name in show
		if mi.name in ["GB_Eye_L", "GB_Eye_R"]:
			mi.material_override = _eye_mat(mi, iris_r)
		elif mi.name == "GB_BrowLash":
			mi.material_override = _lash_mat()
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
