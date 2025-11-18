--[[
    VFX SERVER SCRIPT - FIXED & UPDATED
    
    Creates interactive objects that work with the Unified VFX Client!
    
    INSTALLATION:
    Put this in ServerScriptService as a Script
]]

local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

print("🖥️ VFX Server Script Starting...")

-- Wait for assets
local Assets = ReplicatedStorage:WaitForChild("Assets", 10)
local EggTemplate = Assets:WaitForChild("EggModel", 10)

if not EggTemplate then
	warn("⚠️ WARNING: EggModel not found in ReplicatedStorage.Assets!")
	warn("   Interactive eggs will not work until EggModel is added!")
end

-- Helper: Create interactive egg (for Egg Reveal VFX) - NOW USES ACTUAL EGG MODEL!
local function createInteractiveEgg(position, rarity, petName)
	if not EggTemplate then
		warn("❌ Cannot create egg - EggModel not found!")
		return nil
	end

	-- Clone the actual EggModel!
	local egg = EggTemplate:Clone()
	egg.Name = rarity .. "Egg"
	egg.Parent = workspace

	-- Find the root part (PrimaryPart, EggBase, or first BasePart)
	local root = egg.PrimaryPart or egg:FindFirstChild("EggBase") or egg:FindFirstChildWhichIsA("BasePart")
	if not root then
		warn("❌ EggModel has no parts! Cannot create interactive egg.")
		egg:Destroy()
		return nil
	end

	-- Set PrimaryPart if not already set
	if not egg.PrimaryPart then
		egg:SetPrimaryPartCFrame(CFrame.new(position))
	else
		egg:SetPrimaryPartCFrame(CFrame.new(position))
	end

	-- Disable collisions on all parts, but DON'T anchor root (needed for BodyPosition!)
	for _, inst in ipairs(egg:GetDescendants()) do
		if inst:IsA("BasePart") then
			inst.CanCollide = false
			-- Only anchor non-root parts
			if inst ~= root then
				inst.Anchored = true
			end
		end
	end

	-- Root part must be UNANCHORED for BodyPosition to work!
	root.Anchored = false
	root.CanCollide = false

	-- Weld all direct child parts to root so model stays together when root moves
	for _, child in ipairs(egg:GetChildren()) do
		if child:IsA("BasePart") and child ~= root then
			local weld = Instance.new("WeldConstraint")
			weld.Part0 = root
			weld.Part1 = child
			weld.Parent = root
		end
	end

	-- Set attributes on the root part (this is what the client looks for!)
	root:SetAttribute("VFXInteractive", true)
	root:SetAttribute("VFXRarity", rarity)
	root:SetAttribute("VFXType", "Screen") -- USE SCREEN VFX (no pet reveal, just effects!)
	root:SetAttribute("PetName", petName or "Mystery Pet")

	-- Tag the root part for CollectionService (client looks for tagged BaseParts)
	CollectionService:AddTag(root, "VFXInteractive")

	-- Add or update PointLight on root part
	local pointLight = root:FindFirstChildWhichIsA("PointLight")
	if not pointLight then
		pointLight = Instance.new("PointLight")
		pointLight.Parent = root
	end

	-- Rarity colors
	local rarityColors = {
		Common = Color3.fromRGB(200, 200, 200),
		Rare = Color3.fromRGB(0, 150, 255),
		Epic = Color3.fromRGB(138, 43, 226),
		Legendary = Color3.fromRGB(255, 215, 0)
	}

	local eggColor = rarityColors[rarity] or rarityColors.Common
	pointLight.Color = eggColor
	pointLight.Brightness = 2
	pointLight.Range = 20

	-- Add floating animation (BodyPosition on root - REQUIRES UNANCHORED!)
	local bodyPosition = Instance.new("BodyPosition")
	bodyPosition.MaxForce = Vector3.new(0, math.huge, 0)
	bodyPosition.Position = position
	bodyPosition.D = 200
	bodyPosition.P = 5000
	bodyPosition.Parent = root

	-- Add spinning (BodyAngularVelocity on root - REQUIRES UNANCHORED!)
	local bodyAngularVelocity = Instance.new("BodyAngularVelocity")
	bodyAngularVelocity.AngularVelocity = Vector3.new(0, 1, 0)
	bodyAngularVelocity.MaxTorque = Vector3.new(0, math.huge, 0)
	bodyAngularVelocity.P = 1000
	bodyAngularVelocity.Parent = root

	-- Bobbing animation
	task.spawn(function()
		local startY = position.Y
		local time = 0
		while egg.Parent and root.Parent do
			time += 0.05
			local offset = math.sin(time * 2) * 0.5
			bodyPosition.Position = Vector3.new(position.X, startY + offset, position.Z)
			task.wait(0.05)
		end
	end)

	print("✨ Created", rarity, "egg model at", position)
	return egg
end

-- Helper: Create interactive crystal (for Screen VFX only)
local function createInteractiveCrystal(position, rarity, name)
	local crystal = Instance.new("Part")
	crystal.Name = name or (rarity .. "Crystal")
	crystal.Size = Vector3.new(4, 4, 4)
	crystal.Position = position
	crystal.Anchored = true
	crystal.Material = Enum.Material.Neon
	crystal.Shape = Enum.PartType.Ball
	crystal.Parent = workspace

	local rarityColors = {
		Common = Color3.fromRGB(200, 200, 200),
		Rare = Color3.fromRGB(0, 150, 255),
		Epic = Color3.fromRGB(138, 43, 226),
		Legendary = Color3.fromRGB(255, 215, 0)
	}

	crystal.Color = rarityColors[rarity] or rarityColors.Common

	-- Set attributes
	crystal:SetAttribute("VFXInteractive", true)
	crystal:SetAttribute("VFXRarity", rarity)
	crystal:SetAttribute("VFXType", "Screen") -- THIS MAKES IT USE SCREEN VFX!

	-- Tag for CollectionService
	CollectionService:AddTag(crystal, "VFXInteractive")

	-- Add glow
	local pointLight = Instance.new("PointLight")
	pointLight.Color = crystal.Color
	pointLight.Brightness = 3
	pointLight.Range = 25
	pointLight.Parent = crystal

	-- Add spinning
	local bodyAngularVelocity = Instance.new("BodyAngularVelocity")
	bodyAngularVelocity.AngularVelocity = Vector3.new(0, 2, 0)
	bodyAngularVelocity.MaxTorque = Vector3.new(0, math.huge, 0)
	bodyAngularVelocity.Parent = crystal

	print("💎 Created", rarity, "crystal at", position)
	return crystal
end

-- Expose helper functions globally
_G.CreateInteractiveEgg = createInteractiveEgg
_G.CreateInteractiveCrystal = createInteractiveCrystal

-- Auto-spawn test objects after 2 seconds
task.wait(2)

print("🎮 Spawning test objects...")

-- Spawn eggs (use Egg Reveal VFX - cinematic!) - NOW USING ACTUAL EGG MODEL!
if EggTemplate then
	createInteractiveEgg(Vector3.new(0, 10, 0), "Common", "Doggo")
	createInteractiveEgg(Vector3.new(10, 10, 0), "Rare", "Shadow Wolf")
	createInteractiveEgg(Vector3.new(20, 10, 0), "Epic", "Cerberage")
	createInteractiveEgg(Vector3.new(30, 10, 0), "Legendary", "Phoenix")
else
	warn("⚠️ Skipping egg spawns - EggModel not found!")
end

-- Spawn crystals (use Screen VFX - no camera!)
createInteractiveCrystal(Vector3.new(0, 10, -20), "Rare", "PowerCrystal")
createInteractiveCrystal(Vector3.new(10, 10, -20), "Epic", "MagicOrb")
createInteractiveCrystal(Vector3.new(20, 10, -20), "Legendary", "GodCrystal")

print("✅ VFX Server Script Loaded!")
print("💡 Global functions available:")
print("   _G.CreateInteractiveEgg(position, rarity, petName)")
print("   _G.CreateInteractiveCrystal(position, rarity, name)")
print("🎮 Test objects spawned!")
if EggTemplate then
	print("   - Eggs (front row) = Screen VFX (using actual EggModel, NO pet reveal!)")
else
	print("   - Eggs (front row) = SKIPPED (EggModel not found)")
end
print("   - Crystals (back row) = Screen VFX")
