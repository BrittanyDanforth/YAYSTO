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
-- FaceControls property names (corrected - some don't exist)
-- Valid properties: ChinRaiser, LeftCheekPuff, RightCheekPuff, JawDrop, MouthLeft, MouthRight
-- Invalid: LipCornerPuller, LipStretcher (these don't exist in FaceControls API)
local EXPRESSIONS = {
	neutral = {
		ChinRaiser      = 0,
		LeftCheekPuff   = 0,
		RightCheekPuff  = 0,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	happy = {
		ChinRaiser      = 8,
		LeftCheekPuff   = 0,
		RightCheekPuff  = 0,
		JawDrop         = 4,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	sad = {
		ChinRaiser      = -4,
		LeftCheekPuff   = 5,
		RightCheekPuff  = 5,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	angry = {
		ChinRaiser      = 6,
		LeftCheekPuff   = 15,
		RightCheekPuff  = 15,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	fear = {
		ChinRaiser      = 0,
		LeftCheekPuff   = 5,
		RightCheekPuff  = 5,
		JawDrop         = 10,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	guilt = {
		ChinRaiser      = -6,
		LeftCheekPuff   = 8,
		RightCheekPuff  = 8,
		JawDrop         = 0,
		MouthLeft       = 0,
		MouthRight      = 0,
	},

	determined = {
		ChinRaiser      = 10,
		LeftCheekPuff   = 0,
		RightCheekPuff  = 0,
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

	-- 🔍 EXTENSIVE DEBUG LOGGING
	print("=" .. string.rep("=", 80))
	print("🔍 [FACIAL DEBUG] Starting expression application for mood: " .. mood)
	print("🔍 [FACIAL DEBUG] FaceControls object details:")
	print("  - ClassName: " .. tostring(faceControls.ClassName))
	print("  - Name: " .. tostring(faceControls.Name))
	print("  - Parent: " .. tostring(faceControls.Parent and faceControls.Parent.Name or "nil"))
	print("  - Full Path: " .. tostring(faceControls:GetFullName()))
	
	-- Check all properties (only valid FaceControls properties)
	print("🔍 [FACIAL DEBUG] Checking all FaceControls properties:")
	local propsToCheck = {"ChinRaiser", "LeftCheekPuff", "RightCheekPuff", 
	                     "JawDrop", "MouthLeft", "MouthRight"}
	for _, propName in ipairs(propsToCheck) do
		local success, value, errorMsg = pcall(function()
			return faceControls[propName]
		end)
		if success then
			print("  ✓ " .. propName .. " = " .. tostring(value) .. " (type: " .. typeof(value) .. ")")
		else
			print("  ✗ " .. propName .. " - ERROR: " .. tostring(errorMsg))
		end
	end
	
	-- Check children
	print("🔍 [FACIAL DEBUG] FaceControls children:")
	local children = faceControls:GetChildren()
	if #children == 0 then
		print("  (No children)")
	else
		for _, child in ipairs(children) do
			print("  - " .. child.Name .. " (" .. child.ClassName .. ")")
			if child:IsA("NumberValue") then
				print("      Value: " .. tostring(child.Value))
			end
		end
	end
	
	-- Check descendants
	print("🔍 [FACIAL DEBUG] FaceControls descendants:")
	local descendants = faceControls:GetDescendants()
	if #descendants == 0 then
		print("  (No descendants)")
	else
		for _, desc in ipairs(descendants) do
			print("  - " .. desc:GetFullName() .. " (" .. desc.ClassName .. ")")
			if desc:IsA("NumberValue") then
				print("      Value: " .. tostring(desc.Value))
			end
		end
	end
	
	-- Try to get properties via reflection
	print("🔍 [FACIAL DEBUG] Attempting property reflection:")
	local mt = getmetatable(faceControls)
	if mt then
		print("  ✓ Metatable exists")
		if mt.__index then
			print("  ✓ __index exists (type: " .. typeof(mt.__index) .. ")")
			if typeof(mt.__index) == "table" then
				local count = 0
				for k, v in pairs(mt.__index) do
					if type(k) == "string" and (type(v) == "number" or typeof(v) == "number") then
						count = count + 1
						if count <= 20 then  -- Limit output
							print("    - " .. tostring(k) .. " = " .. tostring(v) .. " (type: " .. typeof(v) .. ")")
						end
					end
				end
				if count > 20 then
					print("    ... and " .. (count - 20) .. " more")
				end
			elseif typeof(mt.__index) == "function" then
				print("  - __index is a function (cannot enumerate)")
			end
		else
			print("  ✗ __index is nil")
		end
	else
		print("  ✗ No metatable")
	end
	
	-- Try GetPropertyChangedSignal to see if properties exist
	print("🔍 [FACIAL DEBUG] Testing property change signals:")
	for _, propName in ipairs(propsToCheck) do
		local success, signal = pcall(function()
			return faceControls:GetPropertyChangedSignal(propName)
		end)
		if success and signal then
			print("  ✓ " .. propName .. " - PropertyChangedSignal exists")
		else
			print("  ✗ " .. propName .. " - No PropertyChangedSignal")
		end
	end
	
	-- Try GetAttributes
	print("🔍 [FACIAL DEBUG] FaceControls attributes:")
	local attrs = faceControls:GetAttributes()
	if next(attrs) then
		for attrName, attrValue in pairs(attrs) do
			print("  - " .. tostring(attrName) .. " = " .. tostring(attrValue) .. " (type: " .. typeof(attrValue) .. ")")
		end
	else
		print("  (No attributes)")
	end
	
	-- Check if it's a DynamicHead FaceControls
	local head = faceControls.Parent
	if head then
		print("🔍 [FACIAL DEBUG] Head object details:")
		print("  - ClassName: " .. tostring(head.ClassName))
		print("  - Name: " .. tostring(head.Name))
		if head:IsA("BasePart") then
			print("  - Is DynamicHead: " .. tostring(head:IsA("MeshPart") and head.MeshId == "" or false))
		end
	end
	
	print("=" .. string.rep("=", 80))

	local preset = EXPRESSIONS[mood] or EXPRESSIONS.neutral
	if not preset then
		warn("⚠️ [FacialAnimationController] Unknown mood: " .. tostring(mood))
		return
	end

	local tweenInfo = TweenInfo.new(0.25, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut)
	local anyApplied = false

	for propertyName, targetValue in pairs(preset) do
		local applied = false
		
		-- 1) Try direct property access (FaceControls properties should be directly accessible)
		local readSuccess, currentValue = pcall(function()
			return faceControls[propertyName]
		end)

		if readSuccess and typeof(currentValue) == "number" then
			-- Property exists and is a number! Try to set it
			local setSuccess, setError = pcall(function()
				faceControls[propertyName] = targetValue
			end)
			
			if setSuccess then
				-- Direct set worked! Now create a smooth tween from current to target
				anyApplied = true
				applied = true
				
				-- Reset to current value first
				faceControls[propertyName] = currentValue
				
				-- Create tween using NumberValue as intermediary
				local animValue = Instance.new("NumberValue")
				animValue.Value = currentValue

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
				
				print("  ✓ Applied " .. propertyName .. ": " .. tostring(currentValue) .. " → " .. tostring(targetValue))
			else
				-- Can read but not write - try setting without tween
				print("  ⚠ " .. propertyName .. " set failed: " .. tostring(setError))
				-- Try direct assignment without tween as fallback
				local directSet = pcall(function()
					faceControls[propertyName] = targetValue
				end)
				if directSet then
					anyApplied = true
					applied = true
					print("  ✓ Applied " .. propertyName .. " (direct): " .. tostring(currentValue) .. " → " .. tostring(targetValue))
				end
			end
		else
			-- Property doesn't exist or isn't a number
			if not readSuccess then
				local errMsg = tostring(currentValue)  -- pcall returns error as second value
				print("  ⚠ Cannot read " .. propertyName .. " property - Error: " .. errMsg)
				-- Try alternative access methods
				print("    🔍 Trying alternative access methods for " .. propertyName .. ":")
				-- Try with GetAttribute
				local attrSuccess, attrValue = pcall(function()
					return faceControls:GetAttribute(propertyName)
				end)
				if attrSuccess and attrValue then
					print("      ✓ Found as attribute: " .. tostring(attrValue))
				end
				-- Try FindFirstChild
				local child = faceControls:FindFirstChild(propertyName, true)
				if child then
					print("      ✓ Found as descendant: " .. child:GetFullName() .. " (" .. child.ClassName .. ")")
				end
			else
				print("  ⚠ " .. propertyName .. " is not a number (type: " .. typeof(currentValue) .. ", value: " .. tostring(currentValue) .. ")")
			end
		end
		
		-- 2) Try as NumberValue child under FaceControls
		if not applied then
			local child = faceControls:FindFirstChild(propertyName)
			if child and child:IsA("NumberValue") then
				anyApplied = true
				applied = true
				local tween = TweenService:Create(child, tweenInfo, {Value = targetValue})
				tween:Play()
				print("  ✓ Applied " .. propertyName .. " (NumberValue): " .. tostring(child.Value) .. " → " .. tostring(targetValue))
			end
		end
		
		-- 3) Try case-insensitive match for NumberValue children
		if not applied then
			for _, child in ipairs(faceControls:GetChildren()) do
				if string.lower(child.Name) == string.lower(propertyName) and child:IsA("NumberValue") then
					anyApplied = true
					applied = true
					local tween = TweenService:Create(child, tweenInfo, {Value = targetValue})
					tween:Play()
					print("  ✓ Applied " .. child.Name .. " (case-insensitive match): " .. tostring(child.Value) .. " → " .. tostring(targetValue))
					break
				end
			end
		end
	end

	if not anyApplied then
		warn("⚠️ [FacialAnimationController] No valid FaceControls properties for expression: " .. mood)
		print("🔍 [FACIAL DEBUG] SUMMARY - No properties were applied!")
		print("  Attempted to apply " .. mood .. " expression with these target values:")
		for propName, targetValue in pairs(preset) do
			print("    - " .. propName .. " → " .. tostring(targetValue))
		end
		print("  But none of the properties could be accessed or modified.")
		print("  This suggests FaceControls may need to be configured differently.")
		print("  Check the debug output above for available properties and access methods.")
		
		-- Try to list properties safely
		local props = {}
		local mt = getmetatable(faceControls)
		if mt and mt.__index then
			-- Try to get properties from the metatable
			local success, result = pcall(function()
				local propList = {}
				if typeof(mt.__index) == "table" then
					for propName, _ in pairs(mt.__index) do
						if type(propName) == "string" then
							local propValue = faceControls[propName]
							if typeof(propValue) == "number" then
								table.insert(propList, propName)
							end
						end
					end
				end
				return propList
			end)
			
			if success and result then
				props = result
			end
		end
		
		-- Also try direct property access for known FaceControls properties
		local knownProps = {"ChinRaiser", "LeftCheekPuff", "RightCheekPuff", 
		                   "JawDrop", "MouthLeft", "MouthRight"}
		for _, propName in ipairs(knownProps) do
			local success, value = pcall(function()
				return faceControls[propName]
			end)
			if success and typeof(value) == "number" then
				table.insert(props, propName .. "=" .. tostring(value))
			end
		end
		
		if #props > 0 then
			print("  [Debug] Numeric properties found: " .. table.concat(props, ", "))
		else
			print("  [Debug] No numeric properties detected. FaceControls may need to be configured differently.")
		end
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
