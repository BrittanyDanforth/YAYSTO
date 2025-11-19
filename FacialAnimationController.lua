--[[
	FACIAL ANIMATION CONTROLLER - LOCALSCRIPT
	
	Controls facial expressions based on dialogue mood/emotion.
	Located in StarterPlayerScripts
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local player = Players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local head = character:WaitForChild("Head")

-- Wait for FaceControls (R15 characters)
local faceControls = head:WaitForChild("FaceControls", 5)

if not faceControls then
	warn("⚠️ FaceControls not found! Facial animations disabled.")
	return
end

-- Get RemoteEvent from ReplicatedStorage
local facialExpressionEvent = ReplicatedStorage:WaitForChild("facialExpressionEvent")

-- Store original values for smooth transitions
local originalValues = {
	ChinRaiser = faceControls.ChinRaiser.Value,
	LipCornerPuller = faceControls.LipCornerPuller.Value,
	LeftCheekPuff = faceControls.LeftCheekPuff.Value,
	RightCheekPuff = faceControls.RightCheekPuff.Value,
	LipStretcher = faceControls.LipStretcher.Value or 0,
	JawDrop = faceControls.JawDrop.Value or 0,
	MouthLeft = faceControls.MouthLeft.Value or 0,
	MouthRight = faceControls.MouthRight.Value or 0,
}

-- Facial expression presets
local expressions = {
	happy = {
		ChinRaiser = 10,
		LipCornerPuller = 10,
		LeftCheekPuff = 0,
		RightCheekPuff = 0,
		LipStretcher = 0,
		JawDrop = 2,
	},
	sad = {
		ChinRaiser = 0,
		LipCornerPuller = -10,
		LeftCheekPuff = 10,
		RightCheekPuff = 10,
		LipStretcher = -5,
		JawDrop = 0,
	},
	angry = {
		ChinRaiser = 5,
		LipCornerPuller = -5,
		LeftCheekPuff = 10,
		RightCheekPuff = 10,
		LipStretcher = 10,
		JawDrop = 0,
	},
	fear = {
		ChinRaiser = 0,
		LipCornerPuller = -8,
		LeftCheekPuff = 5,
		RightCheekPuff = 5,
		LipStretcher = -8,
		JawDrop = 5,
	},
	guilt = {
		ChinRaiser = -5,
		LipCornerPuller = -8,
		LeftCheekPuff = 8,
		RightCheekPuff = 8,
		LipStretcher = -3,
		JawDrop = 0,
	},
	determined = {
		ChinRaiser = 8,
		LipCornerPuller = 5,
		LeftCheekPuff = 0,
		RightCheekPuff = 0,
		LipStretcher = 5,
		JawDrop = 0,
	},
	neutral = {
		ChinRaiser = 0,
		LipCornerPuller = 0,
		LeftCheekPuff = 0,
		RightCheekPuff = 0,
		LipStretcher = 0,
		JawDrop = 0,
	}
}

-- Function to set facial expression with smooth transition
local function setFacialExpression(mood)
	mood = string.lower(mood or "neutral")
	local expression = expressions[mood] or expressions.neutral
	
	if not faceControls then return end
	
	-- Smoothly transition each facial control
	for controlName, targetValue in pairs(expression) do
		local control = faceControls:FindFirstChild(controlName)
		if control then
			local currentValue = control.Value
			local tweenInfo = TweenInfo.new(0.3, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut)
			
			-- Create a NumberValue to tween (since FaceControls use NumberValues)
			local tempValue = Instance.new("NumberValue")
			tempValue.Value = currentValue
			
			local tween = TweenService:Create(tempValue, tweenInfo, {Value = targetValue})
			tween:Play()
			
			-- Update the actual control value during tween
			tween:GetPropertyChangedSignal("Value"):Connect(function()
				control.Value = tempValue.Value
			end)
			
			-- Clean up
			tween.Completed:Connect(function()
				control.Value = targetValue
				tempValue:Destroy()
			end)
		end
	end
	
	print("😊 Facial expression set to: " .. mood)
end

-- Connect RemoteEvent listener
facialExpressionEvent.OnClientEvent:Connect(function(mood)
	setFacialExpression(mood)
end)

-- Auto-set expression based on dialogue (optional integration)
local DialogueMemory = ReplicatedStorage:FindFirstChild("DialogueMemory")
if DialogueMemory then
	-- You can add logic here to automatically change expressions based on dialogue
	-- For example, detect keywords in dialogue text and set appropriate mood
end

-- Handle character respawn
player.CharacterAdded:Connect(function(newCharacter)
	character = newCharacter
	head = newCharacter:WaitForChild("Head")
	faceControls = head:WaitForChild("FaceControls", 5)
	
	if faceControls then
		-- Reset to neutral on respawn
		setFacialExpression("neutral")
	end
end)

print("✅ Facial Animation Controller loaded!")
