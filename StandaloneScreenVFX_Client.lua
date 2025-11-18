--[[
    STANDALONE SCREEN VFX SYSTEM
    
    Triple-A quality screen-space VFX for interactive objects!
    Press E on interactive objects for INSANE screen effects!
    
    FEATURES:
    - Screen shake (no camera drift!)
    - Radial blur + bloom + color correction
    - Screen particles (GUI-based)
    - Radial beams (FIXED - no wonky rendering!)
    - Circular waves
    - Text popups
    - Vignette pulse
    - Buildup animation
    - Rarity-based intensity (Common/Rare/Epic/Legendary)
    
    INSTALLATION:
    1. Put this in StarterPlayer > StarterPlayerScripts as a LocalScript
    2. Add attributes to parts:
       - VFXInteractive (Boolean = true)
       - VFXRarity (String = "Common", "Rare", "Epic", or "Legendary")
    3. Tag parts with CollectionService tag "VFXInteractive"
    
    NOTE: This is for screen-only VFX. For egg reveals with camera control,
          use the EggRevealVFX module system instead!
]]

local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local CollectionService = game:GetService("CollectionService")
local Debris = game:GetService("Debris")

local player = Players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local humanoidRootPart = character:WaitForChild("HumanoidRootPart")
local camera = workspace.CurrentCamera

-- VFX System (OOP)
local ScreenVFX = {}
ScreenVFX.__index = ScreenVFX

function ScreenVFX.new()
	local self = setmetatable({}, ScreenVFX)
	self.ScreenGui = self:CreateScreenGui()
	self.Camera = camera
	self.IsTriggering = false
	return self
end

function ScreenVFX:CreateScreenGui()
	local screenGui = Instance.new("ScreenGui")
	screenGui.Name = "StandaloneVFXGui"
	screenGui.ResetOnSpawn = false
	screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	screenGui.IgnoreGuiInset = true
	screenGui.Parent = player.PlayerGui
	return screenGui
end

-- RARITY CONFIGS
local RarityConfig = {
	Common = {
		color = Color3.fromRGB(200, 200, 200),
		particleCount = 30,
		ringCount = 2,
		beamCount = 8,
		shakeIntensity = 0.5,
		flashIntensity = 0.3,
		blurSize = 15,
		bloomIntensity = 0.5,
		duration = 1.5,
		text = "NICE!",
		buildupTime = 0.5
	},
	Rare = {
		color = Color3.fromRGB(0, 150, 255),
		particleCount = 80,
		ringCount = 4,
		beamCount = 16,
		shakeIntensity = 1.5,
		flashIntensity = 0.5,
		blurSize = 30,
		bloomIntensity = 1.0,
		duration = 2.5,
		text = "RARE!",
		buildupTime = 1.0
	},
	Epic = {
		color = Color3.fromRGB(138, 43, 226),
		particleCount = 150,
		ringCount = 6,
		beamCount = 32,
		shakeIntensity = 3,
		flashIntensity = 0.7,
		blurSize = 50,
		bloomIntensity = 1.5,
		duration = 3.5,
		text = "EPIC!",
		buildupTime = 1.5
	},
	Legendary = {
		color = Color3.fromRGB(255, 215, 0),
		particleCount = 200,
		ringCount = 8,
		beamCount = 48,
		shakeIntensity = 4,
		flashIntensity = 0.9,
		blurSize = 60,
		bloomIntensity = 2.0,
		duration = 4.0,
		text = "LEGENDARY!",
		buildupTime = 2.0
	}
}

-- SCREEN SHAKE (FIXED - no drift!)
function ScreenVFX:ScreenShake(intensity, duration)
	task.spawn(function()
		local baseCFrame = self.Camera.CFrame
		local elapsed = 0
		local conn
		
		conn = RunService.RenderStepped:Connect(function(dt)
			elapsed += dt
			if elapsed >= duration then
				self.Camera.CFrame = baseCFrame
				conn:Disconnect()
				return
			end
			
			local t = 1 - (elapsed / duration)
			local power = intensity * t
			local dx = (math.random() - 0.5) * 2 * power
			local dy = (math.random() - 0.5) * 2 * power
			
			self.Camera.CFrame = baseCFrame * CFrame.new(dx, dy, 0)
		end)
	end)
end

-- COLOR FLASH
function ScreenVFX:ColorFlash(color, duration, intensity)
	local flash = Instance.new("Frame")
	flash.Name = "ColorFlash"
	flash.Size = UDim2.new(1, 0, 1, 0)
	flash.BackgroundColor3 = color
	flash.BackgroundTransparency = 1 - intensity
	flash.BorderSizePixel = 0
	flash.ZIndex = 10000
	flash.Parent = self.ScreenGui

	TweenService:Create(flash, TweenInfo.new(duration, Enum.EasingStyle.Exponential), {
		BackgroundTransparency = 1
	}):Play()

	Debris:AddItem(flash, duration + 0.1)
end

-- RADIAL BLUR + POST-PROCESSING
function ScreenVFX:RadialBlur(maxSize, duration, bloomIntensity)
	-- Blur effect
	local blur = Instance.new("BlurEffect")
	blur.Size = 0
	blur.Parent = self.Camera

	-- Bloom effect
	local bloom = Instance.new("BloomEffect")
	bloom.Intensity = 0
	bloom.Size = 24
	bloom.Threshold = 0.8
	bloom.Parent = self.Camera

	-- Color correction
	local colorCorrect = Instance.new("ColorCorrectionEffect")
	colorCorrect.Brightness = 0
	colorCorrect.Saturation = 0
	colorCorrect.Parent = self.Camera

	-- Tween in
	local infoIn = TweenInfo.new(0.1)
	TweenService:Create(blur, infoIn, {Size = maxSize}):Play()
	TweenService:Create(bloom, infoIn, {Intensity = bloomIntensity}):Play()
	TweenService:Create(colorCorrect, infoIn, {Brightness = 0.1, Saturation = 0.2}):Play()

	task.wait(0.1)

	-- Tween out
	local infoOut = TweenInfo.new(duration)
	TweenService:Create(blur, infoOut, {Size = 0}):Play()
	TweenService:Create(bloom, infoOut, {Intensity = 0}):Play()
	TweenService:Create(colorCorrect, infoOut, {Brightness = 0, Saturation = 0}):Play()

	task.delay(duration, function()
		blur:Destroy()
		bloom:Destroy()
		colorCorrect:Destroy()
	end)
end

-- SCREEN PARTICLES
function ScreenVFX:ScreenParticles(color, count, duration)
	for i = 1, count do
		task.spawn(function()
			local particle = Instance.new("Frame")
			particle.Size = UDim2.new(0, math.random(3, 10), 0, math.random(3, 10))
			particle.Position = UDim2.fromScale(0.5, 0.5)
			particle.BackgroundColor3 = color
			particle.BorderSizePixel = 0
			particle.ZIndex = 9900 + i
			particle.Parent = self.ScreenGui

			local corner = Instance.new("UICorner")
			corner.CornerRadius = UDim.new(1, 0)
			corner.Parent = particle

			local glow = Instance.new("UIStroke")
			glow.Color = color
			glow.Thickness = 2
			glow.Transparency = 0
			glow.Parent = particle

			-- Random direction
			local angle = math.rad(math.random(0, 360))
			local distance = math.random(200, 600)
			local targetX = 0.5 + (math.cos(angle) * distance) / self.Camera.ViewportSize.X
			local targetY = 0.5 + (math.sin(angle) * distance) / self.Camera.ViewportSize.Y + math.random(100, 300) / self.Camera.ViewportSize.Y

			task.wait(math.random() * 0.3)

			TweenService:Create(particle, TweenInfo.new(duration, Enum.EasingStyle.Exponential), {
				Position = UDim2.fromScale(targetX, targetY),
				Size = UDim2.new(0, 0, 0, 0),
				BackgroundTransparency = 1
			}):Play()

			TweenService:Create(glow, TweenInfo.new(duration), {Transparency = 1}):Play()
			Debris:AddItem(particle, duration + 0.5)
		end)
	end
end

-- SCREEN BEAMS (FIXED - proper radial expansion!)
function ScreenVFX:ScreenBeams(color, count, duration)
	local center = UDim2.fromScale(0.5, 0.5)
	local maxLen = math.max(self.Camera.ViewportSize.X, self.Camera.ViewportSize.Y) * 0.8
	local growTime = 0.3
	
	for i = 1, count do
		local angle = (i - 1) * (360 / count)
		
		local beam = Instance.new("Frame")
		beam.Name = "Beam"
		beam.AnchorPoint = Vector2.new(0.5, 1) -- Bottom pivot!
		beam.Position = center
		beam.Size = UDim2.new(0, 4, 0, 0) -- Start at 0 height
		beam.BackgroundColor3 = color
		beam.BorderSizePixel = 0
		beam.Rotation = angle
		beam.ZIndex = 9800
		beam.Parent = self.ScreenGui

		local stroke = Instance.new("UIStroke")
		stroke.Color = Color3.fromRGB(255, 255, 255)
		stroke.Thickness = 2
		stroke.Transparency = 0
		stroke.Parent = beam

		local gradient = Instance.new("UIGradient")
		gradient.Rotation = 90
		gradient.Transparency = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 0),
			NumberSequenceKeypoint.new(0.8, 0),
			NumberSequenceKeypoint.new(1, 1)
		})
		gradient.Parent = beam

		task.delay(0.02 * i, function()
			-- Grow outward
			TweenService:Create(beam, TweenInfo.new(growTime, Enum.EasingStyle.Quint, Enum.EasingDirection.Out), {
				Size = UDim2.new(0, 4, 0, maxLen)
			}):Play()

			task.wait(growTime)

			-- Fade out
			TweenService:Create(beam, TweenInfo.new(duration - growTime), {
				BackgroundTransparency = 1
			}):Play()

			TweenService:Create(stroke, TweenInfo.new(duration - growTime), {
				Transparency = 1
			}):Play()

			Debris:AddItem(beam, duration + 0.1)
		end)
	end
end

-- CIRCULAR WAVES
function ScreenVFX:CircularWaves(color, count, duration)
	for i = 1, count do
		task.wait(0.2)

		local wave = Instance.new("Frame")
		wave.Size = UDim2.new(0, 50, 0, 50)
		wave.Position = UDim2.new(0.5, -25, 0.5, -25)
		wave.BackgroundTransparency = 1
		wave.ZIndex = 9990 + i
		wave.Parent = self.ScreenGui

		local corner = Instance.new("UICorner")
		corner.CornerRadius = UDim.new(1, 0)
		corner.Parent = wave

		local stroke = Instance.new("UIStroke")
		stroke.Color = color
		stroke.Thickness = 4 + (i * 2)
		stroke.Transparency = 0
		stroke.Parent = wave

		TweenService:Create(wave, TweenInfo.new(duration, Enum.EasingStyle.Exponential), {
			Size = UDim2.new(0, 1500, 0, 1500),
			Position = UDim2.new(0.5, -750, 0.5, -750)
		}):Play()

		TweenService:Create(stroke, TweenInfo.new(duration), {Transparency = 1}):Play()
		Debris:AddItem(wave, duration + 0.1)
	end
end

-- TEXT POPUP
function ScreenVFX:TextPopup(text, color, duration)
	local label = Instance.new("TextLabel")
	label.Text = text
	label.Font = Enum.Font.GothamBold
	label.TextSize = 120
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.TextStrokeTransparency = 0
	label.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
	label.BackgroundTransparency = 1
	label.Size = UDim2.new(0, 800, 0, 200)
	label.Position = UDim2.new(0.5, -400, 0.5, -100)
	label.TextTransparency = 1
	label.TextStrokeTransparency = 1
	label.ZIndex = 10001
	label.Parent = self.ScreenGui

	local stroke = Instance.new("UIStroke")
	stroke.Color = color
	stroke.Thickness = 8
	stroke.Transparency = 1
	stroke.Parent = label

	-- Pop in
	TweenService:Create(label, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
		TextTransparency = 0,
		TextStrokeTransparency = 0,
		TextSize = 140
	}):Play()

	TweenService:Create(stroke, TweenInfo.new(0.3), {Transparency = 0}):Play()

	task.wait(0.5)

	-- Float up and fade
	TweenService:Create(label, TweenInfo.new(duration - 0.8, Enum.EasingStyle.Exponential), {
		Position = UDim2.new(0.5, -400, 0.1, -100),
		TextTransparency = 1,
		TextStrokeTransparency = 1
	}):Play()

	TweenService:Create(stroke, TweenInfo.new(duration - 0.8), {Transparency = 1}):Play()
	Debris:AddItem(label, duration + 0.1)
end

-- VIGNETTE PULSE
function ScreenVFX:VignettePulse(color, duration)
	local vignette = Instance.new("Frame")
	vignette.Size = UDim2.new(1, 0, 1, 0)
	vignette.BackgroundColor3 = color
	vignette.BackgroundTransparency = 1
	vignette.BorderSizePixel = 0
	vignette.ZIndex = 9700
	vignette.Parent = self.ScreenGui

	local gradient = Instance.new("UIGradient")
	gradient.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1),
		NumberSequenceKeypoint.new(0.7, 0.5),
		NumberSequenceKeypoint.new(1, 0)
	})
	gradient.Rotation = 90
	gradient.Parent = vignette

	local tween = TweenService:Create(vignette, TweenInfo.new(duration, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
		BackgroundTransparency = 0.3
	})
	tween:Play()

	tween.Completed:Connect(function()
		TweenService:Create(vignette, TweenInfo.new(duration * 0.5), {BackgroundTransparency = 1}):Play()
	end)

	Debris:AddItem(vignette, duration * 1.5 + 0.1)
end

-- BUILDUP ANIMATION
function ScreenVFX:BuildupAnimation(color, duration)
	local circle = Instance.new("Frame")
	circle.Size = UDim2.new(0, 100, 0, 100)
	circle.Position = UDim2.new(0.5, -50, 0.5, -50)
	circle.BackgroundTransparency = 0.5
	circle.BackgroundColor3 = color
	circle.BorderSizePixel = 0
	circle.ZIndex = 10002
	circle.Parent = self.ScreenGui

	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(1, 0)
	corner.Parent = circle

	local stroke = Instance.new("UIStroke")
	stroke.Color = color
	stroke.Thickness = 4
	stroke.Parent = circle

	-- Finite pulse loop
	local pulseCount = 0
	local maxPulses = math.floor(duration / 0.6)

	local function pulse()
		if pulseCount >= maxPulses then
			circle:Destroy()
			return
		end

		pulseCount += 1

		TweenService:Create(circle, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.Out), {
			Size = UDim2.new(0, 150, 0, 150),
			Position = UDim2.new(0.5, -75, 0.5, -75),
			BackgroundTransparency = 0.2
		}):Play()

		task.wait(0.3)

		TweenService:Create(circle, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.In), {
			Size = UDim2.new(0, 100, 0, 100),
			Position = UDim2.new(0.5, -50, 0.5, -50),
			BackgroundTransparency = 0.5
		}):Play()

		task.wait(0.3)
		pulse()
	end

	pulse()
end

-- SOUND EFFECT
function ScreenVFX:PlaySound(soundId, volume)
	pcall(function()
		local sound = Instance.new("Sound")
		sound.SoundId = soundId
		sound.Volume = volume or 0.5
		sound.Parent = self.Camera

		pcall(function() sound:Play() end)
		Debris:AddItem(sound, 3)
	end)
end

-- MAIN TRIGGER
function ScreenVFX:TriggerVFX(rarity)
	if self.IsTriggering then return end
	self.IsTriggering = true

	local config = RarityConfig[rarity] or RarityConfig.Common
	print("🔥 VFX TRIGGERED - RARITY:", rarity)

	-- BUILDUP
	task.spawn(function()
		self:BuildupAnimation(config.color, config.buildupTime)
	end)

	self:PlaySound("rbxassetid://9113880795", 0.3)
	task.wait(config.buildupTime)

	-- EXPLOSION
	print("💥 EXPLOSION!")

	self:ScreenShake(config.shakeIntensity, config.duration)
	self:ColorFlash(config.color, config.duration * 0.6, config.flashIntensity)
	self:RadialBlur(config.blurSize, config.duration, config.bloomIntensity)
	self:VignettePulse(config.color, config.duration * 0.4)

	task.spawn(function() self:ScreenParticles(config.color, config.particleCount, config.duration) end)
	task.spawn(function() self:ScreenBeams(config.color, config.beamCount, config.duration * 0.8) end)
	task.spawn(function() self:CircularWaves(config.color, config.ringCount, config.duration) end)
	task.spawn(function() self:TextPopup(config.text, config.color, config.duration) end)

	self:PlaySound("rbxassetid://9114221327", 0.5)

	-- Cooldown
	task.wait(config.duration + 0.5)
	self.IsTriggering = false
end

-- Initialize
local vfxSystem = ScreenVFX.new()

-- Interaction system
local currentInteractable = nil
local interactionRange = 10
local interactiveParts = {}

-- CollectionService integration (OPTIMIZED!)
for _, inst in ipairs(CollectionService:GetTagged("VFXInteractive")) do
	if inst:IsA("BasePart") then
		table.insert(interactiveParts, inst)
	end
end

CollectionService:GetInstanceAddedSignal("VFXInteractive"):Connect(function(inst)
	if inst:IsA("BasePart") then
		table.insert(interactiveParts, inst)
	end
end)

CollectionService:GetInstanceRemovedSignal("VFXInteractive"):Connect(function(inst)
	local index = table.find(interactiveParts, inst)
	if index then
		table.remove(interactiveParts, index)
	end
	if currentInteractable == inst then
		currentInteractable = nil
	end
end)

-- Create interaction prompt
local function createInteractionPrompt()
	local screenGui = Instance.new("ScreenGui")
	screenGui.Name = "InteractionPrompt"
	screenGui.ResetOnSpawn = false
	screenGui.Parent = player.PlayerGui

	local frame = Instance.new("Frame")
	frame.Name = "PromptFrame"
	frame.Size = UDim2.new(0, 220, 0, 60)
	frame.Position = UDim2.new(0.5, -110, 0.85, 0)
	frame.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
	frame.BackgroundTransparency = 0.3
	frame.BorderSizePixel = 0
	frame.Visible = false
	frame.ZIndex = 1000
	frame.Parent = screenGui

	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 10)
	corner.Parent = frame

	local stroke = Instance.new("UIStroke")
	stroke.Name = "Stroke"
	stroke.Color = Color3.fromRGB(255, 255, 255)
	stroke.Thickness = 3
	stroke.Parent = frame

	local label = Instance.new("TextLabel")
	label.Name = "Label"
	label.Size = UDim2.new(1, 0, 1, 0)
	label.BackgroundTransparency = 1
	label.Text = "[E] Interact"
	label.Font = Enum.Font.GothamBold
	label.TextSize = 24
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.Parent = frame

	return screenGui
end

local interactionPrompt = createInteractionPrompt()

-- Find nearby interactables (OPTIMIZED with cached list!)
RunService.Heartbeat:Connect(function()
	if not character or not humanoidRootPart or vfxSystem.IsTriggering then
		local frame = interactionPrompt:FindFirstChild("PromptFrame")
		if frame then frame.Visible = false end
		return
	end

	local closestPart = nil
	local closestDistance = interactionRange
	local playerPos = humanoidRootPart.Position

	for _, part in ipairs(interactiveParts) do
		if part.Parent then
			local distance = (playerPos - part.Position).Magnitude
			if distance < closestDistance then
				closestPart = part
				closestDistance = distance
			end
		end
	end

	currentInteractable = closestPart

	local frame = interactionPrompt:FindFirstChild("PromptFrame")
	if frame then
		frame.Visible = currentInteractable ~= nil

		if currentInteractable then
			local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
			local config = RarityConfig[rarity]
			if config then
				local stroke = frame:FindFirstChild("Stroke")
				local label = frame:FindFirstChild("Label")
				if stroke then stroke.Color = config.color end
				if label then label.TextColor3 = config.color end
			end
		end
	end
end)

-- Handle E key
UserInputService.InputBegan:Connect(function(input, gameProcessed)
	if gameProcessed or vfxSystem.IsTriggering then return end

	if input.KeyCode == Enum.KeyCode.E and currentInteractable then
		local frame = interactionPrompt:FindFirstChild("PromptFrame")
		if frame then frame.Visible = false end

		local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
		vfxSystem:TriggerVFX(rarity)
	end
end)

-- Global test function
_G.TriggerVFX = function(rarity)
	vfxSystem:TriggerVFX(rarity or "Epic")
end

print("✨ Standalone Screen VFX System Loaded!")
print("💡 Press E near interactive parts for VFX")
print("🧪 Test with: _G.TriggerVFX('Epic')")
