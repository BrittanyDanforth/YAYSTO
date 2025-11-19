--[[
	DIALOGUE SERVER CONTROLLER - SERVER SCRIPT
	
	Handles server-side dialogue logic and fires facial expression events.
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

-- Handle choice made from client
ChoiceMade.OnServerEvent:Connect(function(player, choiceData)
	print("🎮 [Server] Player " .. player.Name .. " made choice: " .. (choiceData.text or "Unknown"))
	
	-- 🔥 CRITICAL FIX: Fire facial expression event to ALL clients when choice is made
	if choiceData.mood then
		local mood = choiceData.mood
		print("🎭 [Server] Firing facial expression event: " .. tostring(mood))
		
		-- Fire to all clients so everyone sees the expression change
		FacialExpressionEvent:FireAllClients(mood)
		
		-- Also fire to the player who made the choice (redundant but ensures it works)
		FacialExpressionEvent:FireClient(player, mood)
	end
	
	-- You can add server-side choice processing here
	-- For example, updating server-side state, saving to DataStore, etc.
end)

print("✅ Dialogue Server Controller loaded!")
