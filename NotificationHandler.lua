--[[
	NOTIFICATION HANDLER - SERVER SCRIPT
	
	Handles dialogue choice impacts and sends notifications to clients.
	Located in ServerScriptService.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

-- Wait for RemoteEvents
local NotificationEvent = ReplicatedStorage:WaitForChild("NotificationEvent")
local ChoiceMade = ReplicatedStorage:WaitForChild("ChoiceMade")
local DialogueMemory = require(ReplicatedStorage:WaitForChild("DialogueMemory"))

print("📢 Notification Handler loaded!")

-- Store player dialogue states
local playerDialogueStates = {}

-- Initialize player dialogue state
local function initializePlayerState(player)
	playerDialogueStates[player.UserId] = {
		memory = DialogueMemory,
		currentStep = 1,
		currentBranch = "main"
	}
end

-- Clean up when player leaves
Players.PlayerRemoving:Connect(function(player)
	playerDialogueStates[player.UserId] = nil
end)

-- Listen for choice notifications from clients
ChoiceMade.OnServerEvent:Connect(function(player, choiceData)
	local playerState = playerDialogueStates[player.UserId]
	if not playerState then
		initializePlayerState(player)
		playerState = playerDialogueStates[player.UserId]
	end
	
	local impactMessage = choiceData.impactMessage or "Choice made."
	local choiceIndex = choiceData.choiceIndex
	
	print("📢 [Server] Player " .. player.Name .. " made choice: " .. tostring(choiceIndex))
	print("📢 [Server] Impact: " .. impactMessage)
	
	-- Apply choice impact to player's dialogue memory
	if choiceData.impact then
		playerState.memory:applyChoiceImpact({
			text = choiceData.text or "Unknown choice",
			impact = choiceData.impact
		})
	end
	
	-- Send notification back to client
	NotificationEvent:FireClient(player, {
		message = impactMessage,
		type = "choice_impact",
		timestamp = tick()
	})
end)

-- Handle player joining
Players.PlayerAdded:Connect(function(player)
	initializePlayerState(player)
	print("📢 [Server] Initialized dialogue state for " .. player.Name)
end)

print("✅ Notification Handler ready!")
