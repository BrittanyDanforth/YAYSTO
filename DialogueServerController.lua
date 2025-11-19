--[[
	DIALOGUE SERVER CONTROLLER - SERVER SCRIPT
	
	Handles server-side dialogue logic and fires facial expression events.
	Also handles FaceControls modification (requires Plugin capability).
	Located in ServerScriptService
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

-- Wait for remote events
local ChoiceMade = ReplicatedStorage:WaitForChild("ChoiceMade")

-- Get or create FacialExpressionEvent
local FacialExpressionEvent = ReplicatedStorage:FindFirstChild("facialExpressionEvent")
if not FacialExpressionEvent then
	FacialExpressionEvent = Instance.new("RemoteEvent")
	FacialExpressionEvent.Name = "facialExpressionEvent"
	FacialExpressionEvent.Parent = ReplicatedStorage
	print("✅ [Server] Created facialExpressionEvent RemoteEvent")
end

-- FaceControls expressions (server-side, has Plugin capability)
local EXPRESSIONS = {
	neutral = { ChinRaiser = 0, LeftCheekPuff = 0, RightCheekPuff = 0, JawDrop = 0, MouthLeft = 0, MouthRight = 0 },
	happy = { ChinRaiser = 8, LeftCheekPuff = 0, RightCheekPuff = 0, JawDrop = 4, MouthLeft = 0, MouthRight = 0 },
	sad = { ChinRaiser = -4, LeftCheekPuff = 5, RightCheekPuff = 5, JawDrop = 0, MouthLeft = 0, MouthRight = 0 },
	angry = { ChinRaiser = 6, LeftCheekPuff = 15, RightCheekPuff = 15, JawDrop = 0, MouthLeft = 0, MouthRight = 0 },
	fear = { ChinRaiser = 0, LeftCheekPuff = 5, RightCheekPuff = 5, JawDrop = 10, MouthLeft = 0, MouthRight = 0 },
	guilt = { ChinRaiser = -6, LeftCheekPuff = 8, RightCheekPuff = 8, JawDrop = 0, MouthLeft = 0, MouthRight = 0 },
	determined = { ChinRaiser = 10, LeftCheekPuff = 0, RightCheekPuff = 0, JawDrop = 0, MouthLeft = 0, MouthRight = 0 },
}

-- Function to apply facial expression on server (has Plugin capability)
local function applyFacialExpressionServer(mood, characterModel)
	if not characterModel then return end
	
	local head = characterModel:FindFirstChild("Head")
	if not head then return end
	
	local faceControls = head:FindFirstChildOfClass("FaceControls")
	if not faceControls then
		warn("⚠️ [Server] No FaceControls found on " .. characterModel.Name)
		return
	end
	
	local preset = EXPRESSIONS[string.lower(mood or "neutral")] or EXPRESSIONS.neutral
	if not preset then return end
	
	-- Server has Plugin capability, can modify FaceControls directly
	for propertyName, targetValue in pairs(preset) do
		local success, errorMsg = pcall(function()
			faceControls[propertyName] = targetValue
		end)
		if success then
			print("  ✓ [Server] Applied " .. propertyName .. " = " .. tostring(targetValue))
		else
			warn("  ✗ [Server] Failed to set " .. propertyName .. ": " .. tostring(errorMsg))
		end
	end
end

-- Handle choice made from client
ChoiceMade.OnServerEvent:Connect(function(player, choiceData)
	print("🎮 [Server] Player " .. player.Name .. " made choice: " .. (choiceData.text or "Unknown"))
	
	-- 🔥 CRITICAL FIX: Fire facial expression event to ALL clients when choice is made
	if choiceData.mood then
		local mood = choiceData.mood
		print("🎭 [Server] Firing facial expression event: " .. tostring(mood))
		
		-- Try to apply on server-side (has Plugin capability)
		local character = player.Character
		if character then
			applyFacialExpressionServer(mood, character)
		end
		
		-- Also try workspace rigs
		local rig = workspace:FindFirstChild("Rig")
		if rig then
			applyFacialExpressionServer(mood, rig)
		end
		
		-- Fire to all clients so everyone sees the expression change
		FacialExpressionEvent:FireAllClients(mood)
		
		-- Also fire to the player who made the choice (redundant but ensures it works)
		FacialExpressionEvent:FireClient(player, mood)
	end
	
	-- You can add server-side choice processing here
	-- For example, updating server-side state, saving to DataStore, etc.
end)

print("✅ Dialogue Server Controller loaded!")
