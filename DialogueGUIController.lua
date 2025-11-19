--[[
	DIALOGUE GUI CONTROLLER - LOCALSCRIPT
	
	Handles the dialogue GUI interface for the zombie apocalypse gambler story.
	Located in StarterGui > DialogueGUI > ScreenGui
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local SoundService = game:GetService("SoundService")
local Players = game:GetService("Players")

local player = Players.LocalPlayer
local DialogueMemory = require(ReplicatedStorage:WaitForChild("DialogueMemory"))
local NotificationEvent = ReplicatedStorage:WaitForChild("NotificationEvent")
local ChoiceMade = ReplicatedStorage:WaitForChild("ChoiceMade")

-- Reference GUI elements
-- Script should be in: StarterGui > DialogueGUI > ScreenGui > LocalScript
local screenGui = script.Parent
if not screenGui:IsA("ScreenGui") then
	warn("⚠️ Script parent is not a ScreenGui! Expected: StarterGui > DialogueGUI > ScreenGui")
	warn("   Current parent: " .. tostring(screenGui))
end
local dialogueFrame = screenGui:WaitForChild("DialogueFrame")
local dialogueLabel = dialogueFrame:WaitForChild("DialogueLabel")
local choice1 = dialogueFrame:WaitForChild("Choice1")
local choice2 = dialogueFrame:WaitForChild("Choice2")
local timerLabel = dialogueFrame:WaitForChild("TimerLabel")
local timeBar = timerLabel:WaitForChild("timebar")
local summaryFrame = screenGui:WaitForChild("SummaryFrame")
local summaryLabel = summaryFrame:WaitForChild("SummaryLabel")

-- State tracking
local dialogueState = {
	memory = DialogueMemory,
	currentIndex = 1,
	choiceMade = false,
	playerChoices = {},
	relationshipStatus = {}
}

-- Initialize relationship tracking
for char, _ in pairs(DialogueMemory.characterRelationships) do
	dialogueState.relationshipStatus[char] = 0
end

-- Notification handler
NotificationEvent.OnClientEvent:Connect(function(notificationData)
	local message = notificationData.message or "Notification"
	print("📢 [Client] " .. message)

	-- You can add visual notification here if needed
	-- For now, it just prints
end)

-- Function to play sounds
local function playSound(soundName)
	if soundName then
		local sound = Instance.new("Sound")
		sound.SoundId = "rbxassetid://" .. tostring(soundName)
		sound.Volume = 0.5
		sound.Parent = SoundService
		sound:Play()
		game:GetService("Debris"):AddItem(sound, sound.TimeLength + 1)
	end
end

-- Function to trigger facial expression (via server)
-- Note: The mood is sent to server via ChoiceMade, and server broadcasts it
local function triggerFacialExpression(mood)
	if mood and mood ~= "" then
		print("😊 [Dialogue] Choice has mood: " .. tostring(mood) .. " (will be sent to server)")
		-- Mood will be included in ChoiceMade event, server will broadcast it
	end
end

-- Forward declarations (will be defined later)
local startCountdown, makeChoice, fadeOutChoices, displaySummary

-- Function to start countdown timer
startCountdown = function(entry)
	timerLabel.Visible = true
	timeBar.Visible = true
	timeBar.Size = UDim2.new(1, 0, timeBar.Size.Y.Scale, 0)

	local timeLimit = entry.timer or 15
	dialogueState.choiceMade = false

	-- Animate timer bar
	local tweenInfo = TweenInfo.new(timeLimit, Enum.EasingStyle.Linear, Enum.EasingDirection.Out)
	local tween = TweenService:Create(timeBar, tweenInfo, {
		Size = UDim2.new(0, 0, timeBar.Size.Y.Scale, 0)
	})
	tween:Play()

	-- Update timer text
	local elapsedTime = 0
	local connection
	connection = game:GetService("RunService").Heartbeat:Connect(function()
		elapsedTime = elapsedTime + game:GetService("RunService").Heartbeat:Wait()

		if elapsedTime >= timeLimit or dialogueState.choiceMade then
			connection:Disconnect()
			return
		end

		local remaining = math.ceil(timeLimit - elapsedTime)
		timerLabel.Text = remaining .. " seconds"

		-- Color coding
		if remaining <= 2 then
			timerLabel.TextColor3 = Color3.fromRGB(255, 0, 0)
		elseif remaining <= 5 then
			timerLabel.TextColor3 = Color3.fromRGB(255, 255, 0)
		else
			timerLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
		end
	end)

	-- Auto-select default if time runs out
	task.delay(timeLimit, function()
		if not dialogueState.choiceMade then
			makeChoice(entry.defaultOption or 1)
		end
	end)
end

-- Function to fade out choices
fadeOutChoices = function()
	local fadeInfo = TweenInfo.new(0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	TweenService:Create(choice1, fadeInfo, {BackgroundTransparency = 1, TextTransparency = 1}):Play()
	TweenService:Create(choice2, fadeInfo, {BackgroundTransparency = 1, TextTransparency = 1}):Play()
end

-- Function to update dialogue display
local function updateDialogue()
	local step = dialogueState.memory.currentStep
	local entry = dialogueState.memory.dialogue[step]

	if not entry then
		warn("Dialogue entry is nil for step " .. tostring(step) .. " - ending dialogue")
		displaySummary()
		return
	end

	-- Check condition
	if not entry.condition(dialogueState.memory) then
		-- Skip to next valid dialogue
		dialogueState.memory.currentStep = step + 1
		updateDialogue()
		return
	end

	dialogueState.memory.currentDialogue = entry
	dialogueLabel.Text = ""
	choice1.Visible = false
	choice2.Visible = false
	timerLabel.Visible = false
	dialogueState.choiceMade = false

	-- Reset facial expression to neutral when new dialogue appears
	triggerFacialExpression("neutral")

	-- Typewriter effect
	local text = entry.text
	for i = 1, #text do
		dialogueLabel.Text = string.sub(text, 1, i)
		wait(0.02)
	end

	-- Show choices if available
	if entry.options and #entry.options > 0 then
		choice1.Visible = true
		choice2.Visible = true
		choice1.Text = entry.options[1].text
		choice2.Text = entry.options[2] and entry.options[2].text or "Continue"
		startCountdown(entry)
	else
		-- No choices, auto-advance or end
		if entry.nextStep then
			dialogueState.memory.currentStep = entry.nextStep
			wait(1)
			updateDialogue()
		else
			displaySummary()
		end
	end
end

-- Function to handle player choice
makeChoice = function(optionIndex)
	if dialogueState.choiceMade then return end
	dialogueState.choiceMade = true

	local entry = dialogueState.memory.currentDialogue
	if not entry or not entry.options or not entry.options[optionIndex] then
		warn("Invalid choice")
		return
	end

	local choice = entry.options[optionIndex]

	-- 🔥 CRITICAL FIX: Trigger facial expression IMMEDIATELY when choice is made
	if choice.impact and choice.impact.mood then
		local mood = choice.impact.mood
		print("🎭 [Choice] Applying mood: " .. tostring(mood))
		triggerFacialExpression(mood)
	end

	-- Send choice to server
	ChoiceMade:FireServer({
		choiceIndex = optionIndex,
		text = choice.text,
		impact = choice.impact,
		impactMessage = choice.impact and "Choice made: " .. choice.text or nil,
		mood = choice.impact and choice.impact.mood or nil  -- Include mood in server message
	})

	-- Apply impact locally
	if choice.impact then
		dialogueState.memory:applyChoiceImpact(choice)
	end

	-- Track choice
	table.insert(dialogueState.playerChoices, {
		text = choice.text,
		step = dialogueState.memory.currentStep,
		branch = dialogueState.memory.currentBranch
	})

	-- Update relationships
	if choice.impact and choice.impact.relationship then
		for char, change in pairs(choice.impact.relationship) do
			dialogueState.relationshipStatus[char] = 
				(dialogueState.relationshipStatus[char] or 0) + change
		end
	end

	-- Fade out choices
	fadeOutChoices()

	-- Advance dialogue - check if nextStep is nil (end of dialogue)
	if choice.impact and choice.impact.nextStep == nil then
		-- End of dialogue reached
		wait(0.3)
		displaySummary()
	else
		-- Continue to next step
		wait(0.3)
		updateDialogue()
	end
end

-- Function to display summary
displaySummary = function()
	local summaryText = "=== STORY SUMMARY ===\n\n"

	-- Choices made
	summaryText = summaryText .. "Choices Made:\n"
	for i, choice in ipairs(dialogueState.playerChoices) do
		summaryText = summaryText .. "- " .. choice.text .. "\n"
	end

	-- Relationships
	summaryText = summaryText .. "\nRelationships:\n"
	for char, value in pairs(dialogueState.relationshipStatus) do
		local status = "Neutral"
		if value > 20 then status = "Positive"
		elseif value < -20 then status = "Negative"
		end
		summaryText = summaryText .. "- " .. char .. ": " .. status .. " (" .. value .. ")\n"
	end

	-- Stats
	summaryText = summaryText .. "\nYour Stats:\n"
	for stat, value in pairs(dialogueState.memory.playerStats) do
		summaryText = summaryText .. "- " .. stat .. ": " .. value .. "\n"
	end

	-- Currency
	summaryText = summaryText .. "\nCurrency:\n"
	summaryText = summaryText .. "- Shekels Lost: " .. (dialogueState.memory.currency.maxShekels - dialogueState.memory.currency.shekels) .. "\n"
	summaryText = summaryText .. "- Items Found: " .. dialogueState.memory.currency.itemsFound .. "\n"

	summaryLabel.Text = summaryText
	summaryFrame.Visible = true
	TweenService:Create(summaryFrame, TweenInfo.new(0.5), {BackgroundTransparency = 0.2}):Play()
end

-- Connect button clicks
choice1.MouseButton1Click:Connect(function() makeChoice(1) end)
choice2.MouseButton1Click:Connect(function() makeChoice(2) end)

-- Initialize dialogue
wait(1) -- Wait for GUI to load
updateDialogue()

print("✅ Dialogue GUI Controller loaded!")
