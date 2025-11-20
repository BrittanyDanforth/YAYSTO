--[[
SNAKE SYSTEM INTEGRATION - FINAL VERSION
Works with OLD CharacterSetup (SnakeModel_UserId format)
FIXED: PVP support
FIXED: Works with both old and new naming conventions
--]]

local ServerScriptService = game:GetService("ServerScriptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

-- *** FASTER MODULE LOADER ***
local snakeSystemsToTry = {
	"OptimizedSnakeSystemV9",
	"OptimizedSnakeSystemV4",
	"OptimizedSnakeSystemV3",
	"OptimizedSnakeSystemV2",
	"OptimizedSnakeSystem" -- V1
}
local OptimizedSnakeSystem = nil

for _, name in ipairs(snakeSystemsToTry) do
	local module = ReplicatedStorage:FindFirstChild(name)
	if module then
		local success, result = pcall(require, module)
		if success and result then
			OptimizedSnakeSystem = result
			print("✅ Loaded Snake System:", name)
			break
		else
			warn("⚠️ Found snake system '"..name.."' but failed to require it:", result)
		end
	end
end

-- If no optimized system found, CharacterSetup handles it directly
if not OptimizedSnakeSystem then
	warn("⚠️ No OptimizedSnakeSystem found - CharacterSetup will handle snake creation directly")
end

-- Initialize the system if it has init function
if OptimizedSnakeSystem and OptimizedSnakeSystem.init then
	OptimizedSnakeSystem.init()
	wait(0.1)
end

-- NOW load the network handler
local SnakeNetworkHandler = nil
pcall(function()
	SnakeNetworkHandler = require(ServerScriptService:FindFirstChild("SnakeNetworkHandler"))
	if SnakeNetworkHandler and SnakeNetworkHandler.init then
		SnakeNetworkHandler.init()
	end
end)

-- Store active snakes
local activeSnakes = {}

-- Create/Get RemoteEvents for menu integration
local remoteEvents = ReplicatedStorage:FindFirstChild("RemoteEvents") or Instance.new("Folder", ReplicatedStorage)
remoteEvents.Name = "RemoteEvents"

local spawnSnake = remoteEvents:FindFirstChild("SpawnSnake") or Instance.new("RemoteEvent", remoteEvents)
spawnSnake.Name = "SpawnSnake"

local respawnSnake = remoteEvents:FindFirstChild("RespawnSnake") or Instance.new("RemoteEvent", remoteEvents)
respawnSnake.Name = "RespawnSnake"

-- Default configuration
local DEFAULT_CONFIG = {
	InitialLength = 85,
	MaxSegments = 50000,
	SegmentSpacing = 3.2,
	SegmentSize = Vector3.new(4, 4, 4),
	HeadSize = Vector3.new(4.5, 4.5, 4.5),
	HeadColor = Color3.fromRGB(76, 217, 100),
	BodyColors = {
		Color3.fromRGB(60, 180, 80),
		Color3.fromRGB(80, 200, 100),
		Color3.fromRGB(100, 220, 120),
		Color3.fromRGB(80, 200, 100),
		Color3.fromRGB(60, 180, 80),
	},
	HeadMaterial = Enum.Material.Neon,
	BodyMaterial = Enum.Material.Neon,
	GlowIntensity = 2,
	GlowRange = 6
}

-- Get skin configuration
local function getSkinConfig(player)
	local skinName = player:GetAttribute("SelectedSkin") or "Default"

	local skinData = nil
	pcall(function()
		local snakeSkins = require(ReplicatedStorage:WaitForChild("SnakeSkins"))
		if snakeSkins and snakeSkins[skinName] then
			skinData = snakeSkins[skinName]
		end
	end)

	if skinData then
		local config = {}
		for k, v in pairs(DEFAULT_CONFIG) do
			config[k] = skinData[k] or v
		end
		return config
	end

	return DEFAULT_CONFIG
end

-- Handle character spawning
local function onCharacterAdded(character)
	local player = Players:GetPlayerFromCharacter(character)
	if not player then
		wait(0.1)
		player = Players:GetPlayerFromCharacter(character)
		if not player then
			warn("Could not get player from character")
			return
		end
	end

	-- Simple revive teleport
	if player:GetAttribute("JustRevived") then
		local revivePos = player:GetAttribute("RevivePosition")
		if revivePos then
			local x, y, z = revivePos:match("([%d.-]+),%s*([%d.-]+),%s*([%d.-]+)")
			if x and y and z then
				local deathPos = Vector3.new(tonumber(x), tonumber(y), tonumber(z))
				local rootPart = character:WaitForChild("HumanoidRootPart")
				if rootPart then
					rootPart.CFrame = CFrame.new(deathPos)
					print("✅ Revived at:", deathPos)
				end
			end
		end
	end

	-- Clean up old snake
	if activeSnakes[player] then
		if activeSnakes[player].destroy then
			activeSnakes[player]:destroy()
		elseif activeSnakes[player].cleanup then
			activeSnakes[player].cleanup()
		end
		activeSnakes[player] = nil
	end

	-- Wait for character to load
	local humanoid = character:WaitForChild("Humanoid")
	local rootPart = character:WaitForChild("HumanoidRootPart")

	-- Check revive snake length
	local reviveSnakeLength = player:GetAttribute("ReviveSnakeLength")
	local isReviving = player:GetAttribute("RevivingNow") or player:GetAttribute("JustRevived")

	if reviveSnakeLength and reviveSnakeLength > 0 then
		print("🔄 Found revive snake length:", reviveSnakeLength, "for", player.Name)
	elseif isReviving then
		warn("⚠️ ReviveSnakeLength attribute missing during revive! Checking leaderstats...")
		local leaderstats = player:FindFirstChild("leaderstats")
		if leaderstats then
			local lengthValue = leaderstats:FindFirstChild("Length")
			if lengthValue and lengthValue.Value > 55 then
				reviveSnakeLength = lengthValue.Value
				print("🔄 Using leaderstats length as fallback:", reviveSnakeLength)
			end
		end
	end

	wait(0.5)

	-- CharacterSetup handles snake creation automatically
	-- We just need to ensure it's registered in _G.PlayerSnakes for collision handler
	
	-- Wait for snake to be created by CharacterSetup
	local maxWait = 3
	local waitTime = 0
	while waitTime < maxWait do
		wait(0.1)
		waitTime = waitTime + 0.1
		
		-- Check if snake was created by CharacterSetup
		if _G.PlayerSnakes and _G.PlayerSnakes[player] then
			local snake = _G.PlayerSnakes[player]
			activeSnakes[player] = snake
			print("✅ Snake found for", player.Name, "from CharacterSetup")
			
			-- Apply revive snake length if available
			if reviveSnakeLength and reviveSnakeLength > 0 and snake.grow then
				local currentLength = 0
				if snake.segments then
					currentLength = #snake.segments
				end
				local growAmount = reviveSnakeLength - currentLength
				if growAmount > 0 then
					snake.grow(growAmount)
					print("✅ Applied revive snake length:", reviveSnakeLength)
				end
				player:SetAttribute("ReviveSnakeLength", nil)
			end
			
			-- Ensure leaderstats exist
			local leaderstats = player:FindFirstChild("leaderstats")
			if not leaderstats then
				leaderstats = Instance.new("Folder")
				leaderstats.Name = "leaderstats"
				leaderstats.Parent = player
			end

			local lengthValue = leaderstats:FindFirstChild("Length")
			if not lengthValue then
				lengthValue = Instance.new("IntValue")
				lengthValue.Name = "Length"
				lengthValue.Value = snake.segments and #snake.segments or 85
				lengthValue.Parent = leaderstats
			else
				if snake.segments then
					lengthValue.Value = #snake.segments
				end
			end

			-- Handle length updates
			if lengthValue and snake.grow then
				lengthValue.Changed:Connect(function(newLength)
					if snake and activeSnakes[player] == snake and snake.grow then
						local currentLength = snake.segments and #snake.segments or 0
						local growAmount = newLength - currentLength
						if growAmount > 0 then
							snake.grow(growAmount)
						end
					end
				end)
			end
			
			break
		end
	end
	
	-- If CharacterSetup didn't create snake, try OptimizedSnakeSystem
	if not activeSnakes[player] and OptimizedSnakeSystem then
		local config = getSkinConfig(player)

		if reviveSnakeLength and reviveSnakeLength > 0 then
			config.InitialLength = reviveSnakeLength
			print("✅ Applying revive snake length:", reviveSnakeLength)
			player:SetAttribute("ReviveSnakeLength", nil)
		end

		print("Creating snake with config - InitialLength:", config.InitialLength, "MaxSegments:", config.MaxSegments)

		print("🐍 Creating snake for", player.Name, "with config:", config.InitialLength, "length")
		local success, snake = pcall(function()
			return OptimizedSnakeSystem.createSnake(character, config)
		end)

		if success and snake then
			print("✅ Snake created successfully for", player.Name)
			activeSnakes[player] = snake

			if not _G.PlayerSnakes then
				_G.PlayerSnakes = {}
			end
			_G.PlayerSnakes[player] = snake
		else
			warn("❌ Error creating snake:", snake)
		end
	end

	-- Setup boost tracking
	if activeSnakes[player] and activeSnakes[player].setBoosting then
		local boostEvent = remoteEvents:FindFirstChild("UpdateBoostState")
		if not boostEvent then
			boostEvent = Instance.new("RemoteEvent")
			boostEvent.Name = "UpdateBoostState"
			boostEvent.Parent = remoteEvents
		end

		local boostConnection
		boostConnection = boostEvent.OnServerEvent:Connect(function(eventPlayer, isBoosting)
			if eventPlayer == player and activeSnakes[player] then
				activeSnakes[player]:setBoosting(isBoosting)
			end
		end)

		if activeSnakes[player]._connections then
			activeSnakes[player]._connections.boost = boostConnection
		end
	end

	-- Ensure leaderstats exist
	local leaderstats = player:FindFirstChild("leaderstats")
	if not leaderstats then
		leaderstats = Instance.new("Folder")
		leaderstats.Name = "leaderstats"
		leaderstats.Parent = player
	end

	local lengthValue = leaderstats:FindFirstChild("Length")
	if not lengthValue then
		lengthValue = Instance.new("IntValue")
		lengthValue.Name = "Length"
		local currentLength = activeSnakes[player] and activeSnakes[player].segments and #activeSnakes[player].segments or 85
		lengthValue.Value = currentLength
		lengthValue.Parent = leaderstats
	end

	-- Handle skin changes
	local skinConnection
	skinConnection = player:GetAttributeChangedSignal("SelectedSkin"):Connect(function()
		if activeSnakes[player] then
			local newConfig = getSkinConfig(player)
			if activeSnakes[player].headParts and activeSnakes[player].headParts.head then
				activeSnakes[player].headParts.head.Color = newConfig.HeadColor
				activeSnakes[player].headParts.head.Material = newConfig.HeadMaterial
			end
			if activeSnakes[player].config then
				activeSnakes[player].config = newConfig
			end
		end
	end)

	if activeSnakes[player] then
		activeSnakes[player].skinConnection = skinConnection
	end

	-- Handle death
	local deathConnection
	deathConnection = humanoid.Died:Connect(function()
		if activeSnakes[player] then
			if skinConnection then
				skinConnection:Disconnect()
			end
			if deathConnection then
				deathConnection:Disconnect()
			end

			if activeSnakes[player]._connections and activeSnakes[player]._connections.boost then
				activeSnakes[player]._connections.boost:Disconnect()
			end

			if activeSnakes[player].destroy then
				activeSnakes[player]:destroy()
			elseif activeSnakes[player].cleanup then
				activeSnakes[player].cleanup()
			end
			activeSnakes[player] = nil

			if _G.PlayerSnakes then
				_G.PlayerSnakes[player] = nil
			end
		end
	end)
end

-- Handle players
Players.PlayerAdded:Connect(function(player)
	local leaderstats = player:FindFirstChild("leaderstats")
	if not leaderstats then
		leaderstats = Instance.new("Folder")
		leaderstats.Name = "leaderstats"
		leaderstats.Parent = player

		local length = Instance.new("IntValue")
		length.Name = "Length"
		length.Value = 55
		length.Parent = leaderstats
	end

	player.CharacterAdded:Connect(onCharacterAdded)

	if player.Character then
		onCharacterAdded(player.Character)
	end
end)

-- Cleanup on player leaving
Players.PlayerRemoving:Connect(function(player)
	if activeSnakes[player] then
		if activeSnakes[player].destroy then
			activeSnakes[player]:destroy()
		elseif activeSnakes[player].cleanup then
			activeSnakes[player].cleanup()
		end
		activeSnakes[player] = nil
	end
	if _G.PlayerSnakes then
		_G.PlayerSnakes[player] = nil
	end
end)

-- Handle existing players
for _, player in pairs(Players:GetPlayers()) do
	if player.Character then
		onCharacterAdded(player.Character)
	else
		player.CharacterAdded:Connect(onCharacterAdded)
	end
end

-- CRITICAL FIX: Handle initial spawn requests from Play button
spawnSnake.OnServerEvent:Connect(function(player)
	print("🎮 Play button clicked - spawning", player.Name)
	if not player.Character then
		player:LoadCharacter()
	end
end)

-- Handle spawn requests from menu
local respawnEvent = ReplicatedStorage:FindFirstChild("RespawnSnake")
if respawnEvent then
	respawnEvent.OnServerEvent:Connect(function(player)
		print("🎮 Respawn requested for:", player.Name)
		if player.Character then
			player.Character:Destroy()
		end
		wait(0.1)
		local success, err = pcall(function()
			player:LoadCharacter()
		end)
		if not success then
			warn("❌ Failed to load character:", err)
		else
			print("✅ Character loaded for:", player.Name)
		end
		print("🐍 Respawned player:", player.Name)
	end)
end

print("✅ Snake System Integration loaded! (Works with OLD CharacterSetup)")
