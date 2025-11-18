--[[
    VFX SERVER SCRIPT - FIXED & UPDATED
    
    Creates interactive objects that work with the Unified VFX Client!
    
    INSTALLATION:
    Put this in ServerScriptService as a Script
]]

local CollectionService = game:GetService("CollectionService")

print("🖥️ VFX Server Script Starting...")

-- Helper: Create interactive egg (for Egg Reveal VFX)
local function createInteractiveEgg(position, rarity, petName)
	local egg = Instance.new("Part")
	egg.Name = rarity .. "Egg"
	egg.Size = Vector3.new(3, 4, 3)
	egg.Position = position
	egg.Anchored = true
	egg.CanCollide = false
	egg.Material = Enum.Material.SmoothPlastic
	egg.Shape = Enum.PartType.Ball
	egg.Parent = workspace
	
	-- Rarity colors
	local rarityColors = {
		Common = Color3.fromRGB(200, 200, 200),
		Rare = Color3.fromRGB(0, 150, 255),
		Epic = Color3.fromRGB(138, 43, 226),
		Legendary = Color3.fromRGB(255, 215, 0)
	}
	
	egg.Color = rarityColors[rarity] or rarityColors.Common
	
	-- Set attributes
	egg:SetAttribute("VFXInteractive", true)
	egg:SetAttribute("VFXRarity", rarity)
	egg:SetAttribute("VFXType", "Egg") -- THIS MAKES IT USE EGG REVEAL!
	egg:SetAttribute("PetName", petName or "Mystery Pet")
	
	-- Tag for CollectionService
	CollectionService:AddTag(egg, "VFXInteractive")
	
	-- Add glow
	local pointLight = Instance.new("PointLight")
	pointLight.Color = egg.Color
	pointLight.Brightness = 2
	pointLight.Range = 20
	pointLight.Parent = egg
	
	-- Add floating animation
	local bodyPosition = Instance.new("BodyPosition")
	bodyPosition.MaxForce = Vector3.new(0, math.huge, 0)
	bodyPosition.Position = position + Vector3.new(0, 1, 0)
	bodyPosition.D = 200
	bodyPosition.P = 5000
	bodyPosition.Parent = egg
	
	-- Add spinning
	local bodyAngularVelocity = Instance.new("BodyAngularVelocity")
	bodyAngularVelocity.AngularVelocity = Vector3.new(0, 1, 0)
	bodyAngularVelocity.MaxTorque = Vector3.new(0, math.huge, 0)
	bodyAngularVelocity.P = 1000
	bodyAngularVelocity.Parent = egg
	
	-- Bobbing animation
	task.spawn(function()
		local startY = position.Y
		local time = 0
		while egg.Parent do
			time += 0.05
			local offset = math.sin(time * 2) * 0.5
			bodyPosition.Position = Vector3.new(position.X, startY + offset, position.Z)
			task.wait(0.05)
		end
	end)
	
	print("✨ Created", rarity, "egg at", position)
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

-- Spawn eggs (use Egg Reveal VFX - cinematic!)
createInteractiveEgg(Vector3.new(0, 10, 0), "Common", "Doggo")
createInteractiveEgg(Vector3.new(10, 10, 0), "Rare", "Shadow Wolf")
createInteractiveEgg(Vector3.new(20, 10, 0), "Epic", "Cerberage")
createInteractiveEgg(Vector3.new(30, 10, 0), "Legendary", "Phoenix")

-- Spawn crystals (use Screen VFX - no camera!)
createInteractiveCrystal(Vector3.new(0, 10, -20), "Rare", "PowerCrystal")
createInteractiveCrystal(Vector3.new(10, 10, -20), "Epic", "MagicOrb")
createInteractiveCrystal(Vector3.new(20, 10, -20), "Legendary", "GodCrystal")

print("✅ VFX Server Script Loaded!")
print("💡 Global functions available:")
print("   _G.CreateInteractiveEgg(position, rarity, petName)")
print("   _G.CreateInteractiveCrystal(position, rarity, name)")
print("🎮 Test objects spawned!")
print("   - Eggs (front row) = Egg Reveal VFX")
print("   - Crystals (back row) = Screen VFX")
