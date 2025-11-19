--[[ 
    FACIAL ANIMATION CONTROLLER - LOCALSCRIPT

    • Put this in StarterPlayerScripts.
    • Automatically finds a FaceControls:
        - First looks in Workspace (e.g. Workspace.Rig.Head.FaceControls)
        - Then falls back to the local character's head.
    • Listens to ReplicatedStorage.facialExpressionEvent (server → client).
    • Supports BOTH:
        - FaceControls.ChinRaiser style numeric properties
        - FaceControls:FindFirstChild("ChinRaiser") as NumberValue children
]]

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService      = game:GetService("TweenService")
local RunService        = game:GetService("RunService")

local player = Players.LocalPlayer
local facialExpressionEvent = ReplicatedStorage:WaitForChild("facialExpressionEvent")

local currentModel
local faceControls

---------------------------------------------------------------------
-- FIND / BIND FACECONTROLS
---------------------------------------------------------------------
local function tryBindOnce(): boolean
	-- 1) Any FaceControls in Workspace (NPC rigs etc.)
	for _, inst in ipairs(workspace:GetDescendants()) do
		if inst:IsA("FaceControls") then
			local head = inst.Parent
			local model = head and head.Parent
			if model and model:IsA("Model") then
				currentModel = model
				faceControls = inst
				print(("[FacialAnimationController] Using FaceControls on workspace model: %s\n   Path: %s")
					:format(model.Name, inst:GetFullName()))
				return true
			end
		end
	end

	-- 2) Local character fallback
	local character = player.Character
	if not character or not character.Parent then
		return false
	end

	local head = character:FindFirstChild("Head")
	if head then
		local fc = head:FindFirstChildOfClass("FaceControls")
		if fc then
			currentModel = character
			faceControls = fc
			print(("[FacialAnimationController] Using FaceControls on character: %s\n   Path: %s")
				:format(character.Name, fc:GetFullName()))
			return true
		end
	end

	return false
end

local function bindFaceControls(maxWait: number?): boolean
	maxWait = maxWait or 5
	local deadline = tick() + maxWait

	repeat
		if tryBindOnce() then
			return true
		end
		RunService.RenderStepped:Wait()
	until tick() > deadline

	warn("⚠️ FacialAnimationController: No FaceControls found. Facial anims disabled.")
	return false
end

-- Initial bind
bindFaceControls(5)

-- Re-bind whenever character respawns
player.CharacterAdded:Connect(function()
	task.wait(0.5)
	bindFaceControls(5)
end)

---------------------------------------------------------------------
-- EXPRESSION PRESETS
---------------------------------------------------------------------
local EXPRESSIONS = {
	neutral = {
		ChinRaiser      = 0,
		LipCornerPuller = 0,
		LeftCheekPuff   = 0,
		RightCheekPuff  = 0,
		LipStretcher    = 0,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	happy = {
		ChinRaiser      = 8,
		LipCornerPuller = 20,
		LeftCheekPuff   = 0,
		RightCheekPuff  = 0,
		LipStretcher    = 10,
		JawDrop         = 4,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	sad = {
		ChinRaiser      = -4,
		LipCornerPuller = -15,
		LeftCheekPuff   = 5,
		RightCheekPuff  = 5,
		LipStretcher    = -8,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	angry = {
		ChinRaiser      = 6,
		LipCornerPuller = -18,
		LeftCheekPuff   = 15,
		RightCheekPuff  = 15,
		LipStretcher    = 15,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	fear = {
		ChinRaiser      = 0,
		LipCornerPuller = -10,
		LeftCheekPuff   = 5,
		RightCheekPuff  = 5,
		LipStretcher    = -10,
		JawDrop         = 10,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	guilt = {
		ChinRaiser      = -6,
		LipCornerPuller = -8,
		LeftCheekPuff   = 8,
		RightCheekPuff  = 8,
		LipStretcher    = -4,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	determined = {
		ChinRaiser      = 10,
		LipCornerPuller = 8,
		LeftCheekPuff   = 0,
		RightCheekPuff  = 0,
		LipStretcher    = 8,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},
}

---------------------------------------------------------------------
-- APPLY EXPRESSION (supports property OR NumberValue child)
---------------------------------------------------------------------
local function applyExpression(mood: string)
	if not mood or mood == "" then
		return
	end

	mood = string.lower(mood or "neutral")

	if not faceControls then
		if not bindFaceControls(3) then
			warn("⚠️ [FacialAnimationController] Cannot apply expression - no FaceControls found")
			return
		end
	end

	local preset = EXPRESSIONS[mood] or EXPRESSIONS.neutral
	if not preset then
		warn("⚠️ [FacialAnimationController] Unknown mood: " .. tostring(mood))
		return
	end

	local tweenInfo = TweenInfo.new(0.25, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut)
	local anyApplied = false

	for propertyName, targetValue in pairs(preset) do
		-- 1) Try as direct numeric property on FaceControls (dynamic head)
		local ok, propValue = pcall(function()
			return faceControls[propertyName]
		end)

		if ok and typeof(propValue) == "number" then
			anyApplied = true

			local animValue = Instance.new("NumberValue")
			animValue.Value = faceControls[propertyName]  -- Start from current value

			animValue.Changed:Connect(function()
				pcall(function()
					faceControls[propertyName] = animValue.Value
				end)
			end)

			local tween = TweenService:Create(animValue, tweenInfo, {Value = targetValue})
			tween.Completed:Connect(function()
				animValue:Destroy()
			end)
			tween:Play()
		else
			-- 2) Try as NumberValue child under FaceControls
			local child = faceControls:FindFirstChild(propertyName)
			if child and child:IsA("NumberValue") then
				anyApplied = true
				local tween = TweenService:Create(child, tweenInfo, {Value = targetValue})
				tween:Play()
			end
		end
	end

	if not anyApplied then
		warn("⚠️ [FacialAnimationController] No valid FaceControls properties for expression: " .. mood)
	else
		print("😊 [FacialAnimationController] Facial expression set to: " .. mood)
	end
end

---------------------------------------------------------------------
-- REMOTE HOOK
---------------------------------------------------------------------
facialExpressionEvent.OnClientEvent:Connect(function(mood)
	print("🎭 [FacialAnimationController] Received mood event: " .. tostring(mood))
	applyExpression(mood)
end)

print("✅ Facial Animation Controller loaded!")
