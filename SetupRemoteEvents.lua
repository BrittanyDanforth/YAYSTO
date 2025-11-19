--[[
	SETUP REMOTE EVENTS - SERVER SCRIPT
	
	Creates all required RemoteEvents for the dialogue system.
	Place this in ServerScriptService and run it once, or keep it for auto-setup.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")

print("🔧 Setting up RemoteEvents for Dialogue System...")

-- Create RemoteEvents if they don't exist
local function createRemoteEvent(name)
	local existing = ReplicatedStorage:FindFirstChild(name)
	if existing then
		if existing:IsA("RemoteEvent") then
			print("✅ RemoteEvent '" .. name .. "' already exists")
			return existing
		else
			warn("⚠️ '" .. name .. "' exists but is not a RemoteEvent! Deleting and recreating...")
			existing:Destroy()
		end
	end
	
	local remoteEvent = Instance.new("RemoteEvent")
	remoteEvent.Name = name
	remoteEvent.Parent = ReplicatedStorage
	print("✅ Created RemoteEvent: " .. name)
	return remoteEvent
end

-- Create all required RemoteEvents
createRemoteEvent("NotificationEvent")
createRemoteEvent("ChoiceMade")
createRemoteEvent("facialExpressionEvent")

print("✅ All RemoteEvents set up!")
