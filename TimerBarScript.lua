--[[
	TIMER BAR SCRIPT
	
	Place this script INSIDE the timebar Frame.
	Structure should be:
	DialogueGui (ScreenGui)
	└─ DialogueFrame (Frame)
	    └─ TimerLabel (Frame)
	        └─ timebar (Frame)
	            └─ Script (this script)
]]

local timeBar = script.Parent -- The timebar Frame
local dialogueFrame = script.Parent.Parent.Parent -- Go up: timebar -> TimerLabel -> DialogueFrame
local choice1 = dialogueFrame:WaitForChild("Choice1")
local choice2 = dialogueFrame:WaitForChild("Choice2")

local timeLimit = 15
local choiceMade = false

-- Reset the fill bar to full
timeBar.Size = UDim2.new(1, 0, 1, 0)
timeBar.BackgroundColor3 = Color3.fromRGB(0, 150, 0) -- Start with green

-- Function to handle choice made
local function onChoiceMade()
	choiceMade = true
end

-- Connect to choice buttons (if they exist)
if choice1 then
	choice1.MouseButton1Click:Connect(onChoiceMade)
end
if choice2 then
	choice2.MouseButton1Click:Connect(onChoiceMade)
end

-- Function to start countdown
function startCountdown()
	timeLimit = 15 -- Reset the time limit
	choiceMade = false
	timeBar.Size = UDim2.new(1, 0, 1, 0)
	timeBar.BackgroundColor3 = Color3.fromRGB(0, 150, 0) -- Reset to green
	
	local elapsed = 0
	
	-- Decrease the size over time
	while elapsed < timeLimit and not choiceMade do
		wait(0.1)
		elapsed = elapsed + 0.1
		local remaining = timeLimit - elapsed
		local newSize = remaining / timeLimit
		timeBar.Size = UDim2.new(newSize, 0, 1, 0)
		
		-- Change color as time runs out
		if remaining <= 2 then
			timeBar.BackgroundColor3 = Color3.fromRGB(255, 0, 0) -- Red for urgency
		elseif remaining <= 5 then
			timeBar.BackgroundColor3 = Color3.fromRGB(255, 165, 0) -- Orange as warning
		end
	end
	
	if not choiceMade then
		-- Default to Choice 1 if time runs out
		if choice1 then
			choice1.MouseButton1Click:Fire() -- Trigger the click
		end
	end
end

-- Expose function globally so DialogueGUIController can call it
_G.StartTimerCountdown = startCountdown

-- Auto-start if needed (comment out if DialogueGUIController handles it)
-- startCountdown()
