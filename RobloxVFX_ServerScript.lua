--[[
    ROBLOX VFX - SERVER SCRIPT
    
    Handles server-side interactions and replicates effects to all players.
    Also includes helper functions for creating interactive objects.
    
    INSTALLATION:
    Put this in ServerScriptService
    
    FEATURES:
    - VFX replication via RemoteEvent
    - CollectionService integration for interactive objects
    - Helper function to spawn interactive eggs/objects
    - Server-side logic hooks (give rewards, etc.)
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local CollectionService = game:GetService("CollectionService")

-- Create RemoteEvent for VFX replication (if needed for multiplayer)
local vfxEvent = ReplicatedStorage:FindFirstChild("VFXTriggerEvent")
if not vfxEvent then
	vfxEvent = Instance.new("RemoteEvent")
	vfxEvent.Name = "VFXTriggerEvent"
	vfxEvent.Parent = ReplicatedStorage
end

print("📡 VFX RemoteEvent created:", vfxEvent:GetFullName())

-- Server-side interaction handler
vfxEvent.OnServerEvent:Connect(function(player, data)
	if type(data) ~= "table" then
		warn("Invalid VFX data from", player.Name)
		return
	end
	
	local eventType = data.eventType or "vfx_trigger"
	local rarity = data.rarity or "Common"
	local position = data.position
	
	print(string.format("🎮 %s triggered %s VFX at %s", player.Name, rarity, tostring(position)))
	
	-- Replicate to all other players (optional - for multiplayer VFX sync)
	for _, otherPlayer in pairs(game.Players:GetPlayers()) do
		if otherPlayer ~= player then
			vfxEvent:FireClient(otherPlayer, data)
		end
	end
	
	-- Server-side logic hooks
	if eventType == "egg_hatch" then
		-- Example: Give player a pet, points, etc.
		handleEggHatch(player, rarity)
	elseif eventType == "collect_item" then
		-- Example: Award coins, items, etc.
		handleItemCollection(player, rarity)
	end
end)

-- Server logic: Egg hatch
function handleEggHatch(player: Player, rarity: string)
	-- Add your server-side egg hatching logic here
	-- Examples:
	-- - Add pet to player's inventory
	-- - Award coins based on rarity
	-- - Update statistics
	-- - Save to DataStore
	
	print("🥚", player.Name, "hatched a", rarity, "egg!")
	
	-- Example reward system:
	local rewards = {
		Common = 10,
		Rare = 50,
		Epic = 200,
		Legendary = 1000
	}
	
	local coins = rewards[rarity] or 10
	-- leaderstats example:
	local leaderstats = player:FindFirstChild("leaderstats")
	if leaderstats then
		local coinsValue = leaderstats:FindFirstChild("Coins")
		if coinsValue and coinsValue:IsA("IntValue") then
			coinsValue.Value += coins
		end
	end
end

-- Server logic: Item collection
function handleItemCollection(player: Player, rarity: string)
	print("💎", player.Name, "collected a", rarity, "item!")
	-- Add your collection logic here
end

-- Helper: Create interactive egg object in workspace
local function createInteractiveEgg(position: Vector3, rarity: string, petName: string?)
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

-- Helper: Create interactive crystal/orb
local function createInteractiveCrystal(position: Vector3, rarity: string, name: string?)
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

-- Example: Spawn some test objects
-- Uncomment to test in your game:
--[[
task.wait(2) -- Wait for workspace to load

createInteractiveEgg(Vector3.new(0, 10, 0), "Common", "Doggo")
createInteractiveEgg(Vector3.new(10, 10, 0), "Rare", "Shadow Wolf")
createInteractiveEgg(Vector3.new(20, 10, 0), "Epic", "Cerberage")
createInteractiveEgg(Vector3.new(30, 10, 0), "Legendary", "Phoenix")

createInteractiveCrystal(Vector3.new(0, 10, -20), "Rare", "PowerCrystal")
createInteractiveCrystal(Vector3.new(10, 10, -20), "Epic", "MagicOrb")
--]]

print("✨ VFX Server Script Loaded!")
print("💡 Use _G.CreateInteractiveEgg(position, rarity, petName)")
print("💡 Use _G.CreateInteractiveCrystal(position, rarity, name)")
