--[[
    VFX SERVER SCRIPT – PET EGG VERSION (POLISHED)

    • Works with your UNIFIED PET + VFX client (eggvfxstarterplayer).
    • Spawns 3D egg models that:
        - Glow, float, and spin
        - Are tagged "VFXInteractive"
        - Have attributes the client expects:
              VFXRarity = "Common" | "Rare" | "Epic" | "Legendary"
              VFXType   = "Screen"       (client treats as screen VFX)
              PetName   = "Axolotl"      (so it shows preview + spawns pet)

    • TEST OBJECTS:
        - Only eggs are auto-spawned at GROUND LEVEL (Y=5, reachable!)
        - NO MagicOrb / PowerCrystal / GodCrystal are auto-created anymore.

    Put this script in ServerScriptService.
]]

local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

print("🖥️ VFX Server Script (Pet Eggs - POLISHED) Starting...")

--// Assets -------------------------------------------------------------------

local Assets = ReplicatedStorage:WaitForChild("Assets", 10)
local EggTemplate = Assets and Assets:FindFirstChild("EggModel")

if not Assets or not EggTemplate then
	warn("⚠️ EggModel not found in ReplicatedStorage.Assets! No eggs will spawn.")
end

-- Rarity → color (for lights)
local RARITY_COLORS: { [string]: Color3 } = {
	Common    = Color3.fromRGB(200, 200, 200),
	Rare      = Color3.fromRGB(0, 150, 255),
	Epic      = Color3.fromRGB(138, 43, 226),
	Legendary = Color3.fromRGB(255, 215, 0),
}

--// Helpers ------------------------------------------------------------------

local function getRarityColor(rarity: string): Color3
	return RARITY_COLORS[rarity] or RARITY_COLORS.Common
end

-- Creates a floating, spinning, glowing interactive egg that the **client**
-- will treat as a PET HATCH (preview + Axolotl follower).
local function createInteractiveEgg(position: Vector3, rarity: string?, petName: string?)
	if not EggTemplate then
		warn("❌ Cannot create egg – EggModel missing.")
		return nil
	end

	rarity = rarity or "Epic"
	petName = petName or "Axolotl"

	-- Clone the template model
	local egg = EggTemplate:Clone()
	egg.Name = string.format("%sEgg", rarity)
	egg.Parent = workspace

	-- Find / set root part
	local root =
		egg.PrimaryPart
		or egg:FindFirstChild("EggBase")
		or egg:FindFirstChildWhichIsA("BasePart")

	if not root then
		warn("❌ EggModel has no root part (EggBase / BasePart).")
		egg:Destroy()
		return nil
	end

	egg.PrimaryPart = root

	-- Place the egg
	egg:PivotTo(CFrame.new(position))

	-- Make all parts non-collide; only root is unanchored so physics controllers work
	for _, inst in ipairs(egg:GetDescendants()) do
		if inst:IsA("BasePart") then
			inst.CanCollide = false
			inst.Massless = true
			if inst ~= root then
				inst.Anchored = true
			end
		end
	end

	root.Anchored = false
	root.CanCollide = false

	-- Name the root in a neutral way (no random "MagicOrb"/"Crystal" parts)
	-- The client only cares that it's tagged + has attributes.
	root.Name = "EggBase"

	-- Attributes the **client** uses
	root:SetAttribute("VFXInteractive", true)
	root:SetAttribute("VFXRarity", rarity)
	root:SetAttribute("VFXType", "Screen") -- client is using screen VFX path
	-- IMPORTANT: keep PetName = "Axolotl" so it behaves like MagicOrb did
	root:SetAttribute("PetName", petName)

	-- Tag for CollectionService so the client can discover it
	CollectionService:AddTag(root, "VFXInteractive")

	-- Light / glow
	local pointLight = root:FindFirstChildWhichIsA("PointLight")
	if not pointLight then
		pointLight = Instance.new("PointLight")
		pointLight.Parent = root
	end

	pointLight.Color = getRarityColor(rarity)
	pointLight.Brightness = 3
	pointLight.Range = 25

	-- Floating (BodyPosition on root)
	local bodyPosition = Instance.new("BodyPosition")
	bodyPosition.Name = "FloatPosition"
	bodyPosition.MaxForce = Vector3.new(0, math.huge, 0)
	bodyPosition.D = 300
	bodyPosition.P = 6000
	bodyPosition.Position = position
	bodyPosition.Parent = root

	-- Spinning (BodyAngularVelocity on root)
	local bodyAngularVelocity = Instance.new("BodyAngularVelocity")
	bodyAngularVelocity.Name = "Spin"
	bodyAngularVelocity.AngularVelocity = Vector3.new(0, 1.5, 0)
	bodyAngularVelocity.MaxTorque = Vector3.new(0, math.huge, 0)
	bodyAngularVelocity.P = 2000
	bodyAngularVelocity.Parent = root

	-- Bobbing task (smooth floating animation)
	task.spawn(function()
		local baseY = position.Y
		local t = 0
		while egg.Parent and root.Parent do
			t += RunService.Heartbeat:Wait()
			local offset = math.sin(t * 2) * 0.6
			bodyPosition.Position = Vector3.new(position.X, baseY + offset, position.Z)
		end
	end)

	print(string.format("✨ Created %s pet egg at (%.1f, %.1f, %.1f) for pet '%s'",
		rarity, position.X, position.Y, position.Z, petName))

	return egg
end

-- Optional: simple crystal helper if you ever want screen-VFX only orbs again.
-- NOTE: this function does NOT auto-spawn anything by itself.
local function createInteractiveCrystal(position: Vector3, rarity: string?, name: string?)
	rarity = rarity or "Rare"

	local crystal = Instance.new("Part")
	crystal.Name = name or (rarity .. "Crystal")
	crystal.Size = Vector3.new(4, 4, 4)
	crystal.Position = position
	crystal.Anchored = true
	crystal.Material = Enum.Material.Neon
	crystal.Shape = Enum.PartType.Ball
	crystal.Color = getRarityColor(rarity)
	crystal.Parent = workspace

	crystal:SetAttribute("VFXInteractive", true)
	crystal:SetAttribute("VFXRarity", rarity)
	crystal:SetAttribute("VFXType", "Screen") -- SCREEN VFX ONLY (no pet)

	CollectionService:AddTag(crystal, "VFXInteractive")

	local pointLight = Instance.new("PointLight")
	pointLight.Color = crystal.Color
	pointLight.Brightness = 3
	pointLight.Range = 25
	pointLight.Parent = crystal

	print(string.format("💎 Created %s screen-VFX crystal '%s' at (%.1f, %.1f, %.1f)",
		rarity, crystal.Name, position.X, position.Y, position.Z))

	return crystal
end

-- Expose helpers globally so you can spawn from other scripts if you want
_G.CreateInteractiveEgg = createInteractiveEgg
_G.CreateInteractiveCrystal = createInteractiveCrystal

--// Auto test spawn (EGGS ONLY - AT GROUND LEVEL!) --------------------------

task.delay(2, function()
	if not EggTemplate then
		warn("⚠️ Skipping egg test spawns – EggModel missing.")
		return
	end

	print("🎮 Spawning test PET eggs at GROUND LEVEL (reachable!)...")

	-- SPAWN AT GROUND LEVEL (Y=5 instead of Y=10 - 50% lower!)
	-- These positions are reachable by players!
	createInteractiveEgg(Vector3.new(0, 5, 0),   "Common",    "Axolotl")
	createInteractiveEgg(Vector3.new(10, 5, 0),  "Rare",      "Axolotl")
	createInteractiveEgg(Vector3.new(20, 5, 0),  "Epic",      "Axolotl")
	createInteractiveEgg(Vector3.new(30, 5, 0),  "Legendary", "Axolotl")

	print("✅ VFX Server Script Loaded!")
	print("💡 Global functions available:")
	print("   _G.CreateInteractiveEgg(Vector3.new(x,y,z), 'Epic', 'Axolotl')")
	print("   _G.CreateInteractiveCrystal(Vector3.new(x,y,z), 'Epic', 'SomeName')  -- only if you WANT orbs again")
	print("📍 Eggs spawned at Y=5 (ground level, reachable!)")
end)
