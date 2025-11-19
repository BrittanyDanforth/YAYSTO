-- LocalScript under NotificationsGUI.NotificationFrame

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService      = game:GetService("TweenService")

local notificationFrame = script.Parent
local notificationLabel = notificationFrame:WaitForChild("NotificationLabel")

local function showNotification(payload)
	-- payload might be a table OR a plain string
	local message

	if typeof(payload) == "table" then
		message = payload.message or payload.text or "[Notification]"
	else
		message = tostring(payload)
	end

	notificationLabel.Text = message
	notificationFrame.Visible = true
	notificationFrame.BackgroundTransparency = 0
	notificationLabel.TextTransparency = 0

	task.wait(3)

	local fadeInfo = TweenInfo.new(1, Enum.EasingStyle.Linear, Enum.EasingDirection.Out)
	local fadeBG   = TweenService:Create(notificationFrame, fadeInfo, {BackgroundTransparency = 1})
	local fadeText = TweenService:Create(notificationLabel, fadeInfo, {TextTransparency = 1})

	fadeBG:Play()
	fadeText:Play()
	fadeBG.Completed:Wait()

	notificationFrame.Visible = false
	notificationFrame.BackgroundTransparency = 0
	notificationLabel.TextTransparency = 0
end

local NotificationEvent = ReplicatedStorage:WaitForChild("NotificationEvent")
NotificationEvent.OnClientEvent:Connect(showNotification)
