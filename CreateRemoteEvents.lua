--[[
	CREATE REMOTE EVENTS SETUP SCRIPT
	
	Run this ONCE in ServerScriptService to create all required RemoteEvents.
	After running, you can delete this script.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")

-- Create NotificationEvent (RemoteEvent)
local notificationEvent = ReplicatedStorage:FindFirstChild("NotificationEvent")
if not notificationEvent then
	notificationEvent = Instance.new("RemoteEvent")
	notificationEvent.Name = "NotificationEvent"
	notificationEvent.Parent = ReplicatedStorage
	print("✅ Created NotificationEvent")
else
	print("ℹ️ NotificationEvent already exists")
end

-- Create ChoiceMade (RemoteEvent)
local choiceMade = ReplicatedStorage:FindFirstChild("ChoiceMade")
if not choiceMade then
	choiceMade = Instance.new("RemoteEvent")
	choiceMade.Name = "ChoiceMade"
	choiceMade.Parent = ReplicatedStorage
	print("✅ Created ChoiceMade")
else
	print("ℹ️ ChoiceMade already exists")
end

-- Create facialExpressionEvent (RemoteEvent)
local facialExpressionEvent = ReplicatedStorage:FindFirstChild("facialExpressionEvent")
if not facialExpressionEvent then
	facialExpressionEvent = Instance.new("RemoteEvent")
	facialExpressionEvent.Name = "facialExpressionEvent"
	facialExpressionEvent.Parent = ReplicatedStorage
	print("✅ Created facialExpressionEvent")
else
	print("ℹ️ facialExpressionEvent already exists")
end

print("✅ All RemoteEvents created!")
