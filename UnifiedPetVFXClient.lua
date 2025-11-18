--[[ 
    UNIFIED PET + VFX CLIENT (v2 - POLISHED & FIXED)

    Put this LocalScript in StarterPlayerScripts.
    Delete / disable your old PetFollower and any old egg-vfx client scripts.

    Features:
      - Screen VFX: _G.TriggerVFX("Common"/"Rare"/"Epic"/"Legendary")
      - Pet hatch flow with 3D preview (ViewportFrame) + follower
      - Axolotl pet floats behind you Pet Simulator–style
      - Press E near parts tagged "VFXInteractive" to trigger
      - FIXED: GUI only shows when actually near eggs (no premature display)
      - POLISHED: Smooth animations, better UI design

    PET SETUP (IMPORTANT):
      ReplicatedStorage
        └─ Pets
             └─ Axolotl  (Model, anchored, welded, with a clear "front"; PrimaryPart or HRP inside)

    TO MAKE A PET HATCH TRIGGER:
      1) Place a Part (e.g. AxolotlEgg, MagicOrb, whatever).
      2) Tag it with CollectionService tag "VFXInteractive".
      3) Add attributes:
           VFXRarity = "Epic"   (or Common/Rare/Legendary)
           PetName   = "Axolotl"
           VFXType   = "Pet"    (optional; we also auto-detect via PetName)
]]

----------------------------------------------------------------
-- SERVICES
----------------------------------------------------------------
local RS               = game:GetService("ReplicatedStorage")
local Players          = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local RunService       = game:GetService("RunService")
local CollectionService= game:GetService("CollectionService")
local TweenService     = game:GetService("TweenService")
local Debris           = game:GetService("Debris")

local player           = Players.LocalPlayer
local character        = player.Character or player.CharacterAdded:Wait()
local humanoidRootPart = character:WaitForChild("HumanoidRootPart")
local camera           = workspace.CurrentCamera

player.CharacterAdded:Connect(function(char)
	character = char
	humanoidRootPart = char:WaitForChild("HumanoidRootPart")
end)

print("🔥 UNIFIED PET + VFX CLIENT v2 (POLISHED) - Loading...")

----------------------------------------------------------------
-- GLOBAL PET-FOLLOW DEFAULTS
----------------------------------------------------------------
local DEFAULT_FOLLOW_OFFSET        = Vector3.new(4, 2.3, -4) -- right, up, back
local DEFAULT_FOLLOW_SMOOTHNESS    = 6
local DEFAULT_BOB_SPEED            = 1.8
local DEFAULT_BOB_HEIGHT           = 0.35
local DEFAULT_MIN_FLAT_DISTANCE    = 5

----------------------------------------------------------------
-- RARITY CONFIGS (for screen VFX & colors)
----------------------------------------------------------------
local ScreenRarityConfig = {
	Common = {
		color           = Color3.fromRGB(200, 200, 200),
		particleCount   = 30,
		ringCount       = 2,
		beamCount       = 8,
		shakeIntensity  = 0.5,
		flashIntensity  = 0.3,
		blurSize        = 15,
		bloomIntensity  = 0.5,
		duration        = 1.5,
		text            = "NICE!",
		buildupTime     = 0.5,
		titleText       = "NEW PET!",
		nameColor       = Color3.fromRGB(255, 255, 255),
	},
	Rare = {
		color           = Color3.fromRGB(0, 150, 255),
		particleCount   = 80,
		ringCount       = 4,
		beamCount       = 16,
		shakeIntensity  = 1.5,
		flashIntensity  = 0.5,
		blurSize        = 30,
		bloomIntensity  = 1.0,
		duration        = 2.5,
		text            = "RARE!",
		buildupTime     = 1.0,
		titleText       = "RARE PET!",
		nameColor       = Color3.fromRGB(200, 230, 255),
	},
	Epic = {
		color           = Color3.fromRGB(138, 43, 226),
		particleCount   = 150,
		ringCount       = 6,
		beamCount       = 32,
		shakeIntensity  = 3,
		flashIntensity  = 0.7,
		blurSize        = 50,
		bloomIntensity  = 1.5,
		duration        = 3.5,
		text            = "EPIC!",
		buildupTime     = 1.5,
		titleText       = "EPIC PET!",
		nameColor       = Color3.fromRGB(230, 210, 255),
	},
	Legendary = {
		color           = Color3.fromRGB(255, 215, 0),
		particleCount   = 200,
		ringCount       = 8,
		beamCount       = 48,
		shakeIntensity  = 4,
		flashIntensity  = 0.9,
		blurSize        = 60,
		bloomIntensity  = 2.0,
		duration        = 4.0,
		text            = "LEGENDARY!",
		buildupTime     = 2.0,
		titleText       = "LEGENDARY PET!",
		nameColor       = Color3.fromRGB(255, 255, 200),
	},
}

----------------------------------------------------------------
-- PET CONFIGS (add more pets later)
----------------------------------------------------------------
local PET_CONFIGS = {
	Axolotl = {
		displayName       = "Axolotl",
		templatePath      = {"Pets", "Axolotl"}, -- ReplicatedStorage.Pets.Axolotl
		offset            = DEFAULT_FOLLOW_OFFSET,
		followSmoothness  = DEFAULT_FOLLOW_SMOOTHNESS,
		bobSpeed          = DEFAULT_BOB_SPEED,
		bobHeight         = DEFAULT_BOB_HEIGHT,
		minFlatDistance   = DEFAULT_MIN_FLAT_DISTANCE,
		subtitle          = "It will happily float by your side!",
	},
}

----------------------------------------------------------------
-- TEMPLATE RESOLVER (used by follower + preview)
----------------------------------------------------------------
local function resolveTemplate(pathTable)
	if typeof(pathTable) ~= "table" then return nil end
	local obj = RS
	for _, name in ipairs(pathTable) do
		obj = obj:FindFirstChild(name)
		if not obj then return nil end
	end
	return obj
end

----------------------------------------------------------------
-- SCREEN VFX SYSTEM
----------------------------------------------------------------
local ScreenVFXSystem = {}
ScreenVFXSystem.__index = ScreenVFXSystem

function ScreenVFXSystem.new()
	local self = setmetatable({}, ScreenVFXSystem)
	self.ScreenGui = self:CreateScreenGui()
	self.Camera = camera
	self.IsTriggering = false
	return self
end

function ScreenVFXSystem:CreateScreenGui()
	local screenGui = Instance.new("ScreenGui")
	screenGui.Name = "UnifiedVFXGui"
	screenGui.ResetOnSpawn = false
	screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	screenGui.IgnoreGuiInset = true
	local playerGui = player:WaitForChild("PlayerGui")
	screenGui.Parent = playerGui
	return screenGui
end

function ScreenVFXSystem:ScreenShake(intensity, duration)
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

function ScreenVFXSystem:ColorFlash(color, duration, intensity)
	local flash = Instance.new("Frame")
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

function ScreenVFXSystem:RadialBlur(maxSize, duration, bloomIntensity)
	local blur = Instance.new("BlurEffect")
	blur.Size = 0
	blur.Parent = self.Camera

	local bloom = Instance.new("BloomEffect")
	bloom.Intensity = 0
	bloom.Size = 24
	bloom.Threshold = 0.8
	bloom.Parent = self.Camera

	local colorCorrect = Instance.new("ColorCorrectionEffect")
	colorCorrect.Brightness = 0
	colorCorrect.Saturation = 0
	colorCorrect.Parent = self.Camera

	local infoIn = TweenInfo.new(0.1)
	TweenService:Create(blur, infoIn, {Size = maxSize}):Play()
	TweenService:Create(bloom, infoIn, {Intensity = bloomIntensity}):Play()
	TweenService:Create(colorCorrect, infoIn, {Brightness = 0.1, Saturation = 0.2}):Play()

	task.wait(0.1)

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

function ScreenVFXSystem:ScreenParticles(color, count, duration)
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

			local angle = math.rad(math.random(0, 360))
			local distance = math.random(200, 600)
			local targetX = 0.5 + (math.cos(angle) * distance) / self.Camera.ViewportSize.X
			local targetY = 0.5 + (math.sin(angle) * distance) / self.Camera.ViewportSize.Y
				+ math.random(100, 300) / self.Camera.ViewportSize.Y

			task.wait(math.random() * 0.3)

			TweenService:Create(particle, TweenInfo.new(duration, Enum.EasingStyle.Exponential), {
				Position = UDim2.fromScale(targetX, targetY),
				Size = UDim2.new(0, 0, 0, 0),
				BackgroundTransparency = 1
			}):Play()

			TweenService:Create(glow, TweenInfo.new(duration), {
				Transparency = 1
			}):Play()

			Debris:AddItem(particle, duration + 0.5)
		end)
	end
end

function ScreenVFXSystem:ScreenBeams(color, count, duration)
	local center = UDim2.fromScale(0.5, 0.5)
	local maxLen = math.max(self.Camera.ViewportSize.X, self.Camera.ViewportSize.Y) * 0.8
	local growTime = 0.3

	for i = 1, count do
		local angle = (i - 1) * (360 / count)

		local beam = Instance.new("Frame")
		beam.AnchorPoint = Vector2.new(0.5, 1)
		beam.Position = center
		beam.Size = UDim2.new(0, 4, 0, 0)
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
			TweenService:Create(beam, TweenInfo.new(growTime, Enum.EasingStyle.Quint, Enum.EasingDirection.Out), {
				Size = UDim2.new(0, 4, 0, maxLen)
			}):Play()

			task.wait(growTime)

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

function ScreenVFXSystem:CircularWaves(color, count, duration)
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

		TweenService:Create(stroke, TweenInfo.new(duration), {
			Transparency = 1
		}):Play()

		Debris:AddItem(wave, duration + 0.1)
	end
end

function ScreenVFXSystem:TextPopup(text, color, duration)
	local label = Instance.new("TextLabel")
	label.Text = text
	label.Font = Enum.Font.GothamBold
	label.TextSize = 120
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.TextStrokeTransparency = 0
	label.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
	label.BackgroundTransparency = 1
	label.Size = UDim2.new(0, 800, 0, 200)
	label.Position = UDim2.new(0.5, -400, 0.35, -100)
	label.TextTransparency = 1
	label.TextStrokeTransparency = 1
	label.ZIndex = 10001
	label.Parent = self.ScreenGui

	local stroke = Instance.new("UIStroke")
	stroke.Color = color
	stroke.Thickness = 8
	stroke.Transparency = 1
	stroke.Parent = label

	TweenService:Create(label, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
		TextTransparency = 0,
		TextStrokeTransparency = 0,
		TextSize = 140
	}):Play()

	TweenService:Create(stroke, TweenInfo.new(0.3), {Transparency = 0}):Play()

	task.wait(0.5)

	TweenService:Create(label, TweenInfo.new(duration - 0.8, Enum.EasingStyle.Exponential), {
		Position = UDim2.new(0.5, -400, 0.1, -100),
		TextTransparency = 1,
		TextStrokeTransparency = 1
	}):Play()

	TweenService:Create(stroke, TweenInfo.new(duration - 0.8), {Transparency = 1}):Play()

	Debris:AddItem(label, duration + 0.1)
end

function ScreenVFXSystem:VignettePulse(color, duration)
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

	local tween = TweenService:Create(
		vignette,
		TweenInfo.new(duration, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut),
		{BackgroundTransparency = 0.3}
	)
	tween:Play()

	tween.Completed:Connect(function()
		TweenService:Create(vignette, TweenInfo.new(duration * 0.5), {
			BackgroundTransparency = 1
		}):Play()
	end)

	Debris:AddItem(vignette, duration * 1.5 + 0.1)
end

function ScreenVFXSystem:BuildupAnimation(color, duration)
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

function ScreenVFXSystem:PlaySound(soundId, volume)
	pcall(function()
		local sound = Instance.new("Sound")
		sound.SoundId = soundId
		sound.Volume = volume or 0.5
		sound.Parent = self.Camera
		pcall(function() sound:Play() end)
		Debris:AddItem(sound, 3)
	end)
end

function ScreenVFXSystem:TriggerVFX(rarity)
	if self.IsTriggering then return end
	self.IsTriggering = true

	rarity = rarity or "Epic"
	local config = ScreenRarityConfig[rarity] or ScreenRarityConfig.Common

	print("🔥 SCREEN VFX TRIGGERED - RARITY:", rarity)
	task.spawn(function()
		self:BuildupAnimation(config.color, config.buildupTime)
	end)

	self:PlaySound("rbxassetid://9113880795", 0.3)
	task.wait(config.buildupTime)

	print("💥 EXPLOSION!")

	self:ScreenShake(config.shakeIntensity, config.duration)
	self:ColorFlash(config.color, config.duration * 0.6, config.flashIntensity)
	self:RadialBlur(config.blurSize, config.duration, config.bloomIntensity)
	self:VignettePulse(config.color, config.duration * 0.4)

	task.spawn(function()
		self:ScreenParticles(config.color, config.particleCount, config.duration)
	end)
	task.spawn(function()
		self:ScreenBeams(config.color, config.beamCount, config.duration * 0.8)
	end)
	task.spawn(function()
		self:CircularWaves(config.color, config.ringCount, config.duration)
	end)
	task.spawn(function()
		self:TextPopup(config.text, config.color, config.duration)
	end)

	self:PlaySound("rbxassetid://9114221327", 0.5)

	task.wait(config.duration + 0.5)
	self.IsTriggering = false
end

local screenVfxSystem = ScreenVFXSystem.new()
print("✅ Screen VFX System Loaded!")

----------------------------------------------------------------
-- PET FOLLOWER SYSTEM (Pet Sim–style float)
----------------------------------------------------------------
local PetFollowerSystem = {}
PetFollowerSystem.__index = PetFollowerSystem

function PetFollowerSystem.new()
	local self = setmetatable({}, PetFollowerSystem)
	self.petModel = nil
	self.followConn = nil
	return self
end

function PetFollowerSystem:Cleanup()
	if self.followConn then
		self.followConn:Disconnect()
		self.followConn = nil
	end
	if self.petModel then
		self.petModel:Destroy()
		self.petModel = nil
	end
end

function PetFollowerSystem:EquipPet(petKey)
	local config = PET_CONFIGS[petKey]
	if not config then
		warn("[PetFollowerSystem] Unknown pet key:", petKey)
		return
	end

	self:Cleanup()

	local template = resolveTemplate(config.templatePath)
	if not template or not template:IsA("Model") then
		warn("[PetFollowerSystem] Template not found or not a Model for pet:", petKey)
		return
	end

	local pet = template:Clone()
	pet.Name = (config.displayName or petKey) .. "Pet"
	pet.Parent = workspace
	self.petModel = pet

	local root = pet.PrimaryPart
		or pet:FindFirstChild("HumanoidRootPart")
		or pet:FindFirstChildWhichIsA("BasePart")

	if not root then
		warn("[PetFollowerSystem] Pet model has no root part:", petKey)
		self:Cleanup()
		return
	end

	pet.PrimaryPart = root

	for _, part in ipairs(pet:GetDescendants()) do
		if part:IsA("BasePart") then
			part.Anchored = true
			part.CanCollide = false
			part.Massless = true
		end
	end

	local startTime = tick()
	local currentCF = nil

	self.followConn = RunService.RenderStepped:Connect(function(dt)
		local char = player.Character
		if not char or not char.Parent then
			return
		end

		local hrp = char:FindFirstChild("HumanoidRootPart")
		if not hrp then
			return
		end

		local t = tick() - startTime
		local bobSpeed = config.bobSpeed or DEFAULT_BOB_SPEED
		local bobHeight = config.bobHeight or DEFAULT_BOB_HEIGHT
		local bob = math.sin(t * bobSpeed) * bobHeight

		local offset = config.offset or DEFAULT_FOLLOW_OFFSET
		local targetCF = hrp.CFrame * CFrame.new(
			offset.X,
			offset.Y + bob,
			offset.Z
		)

		if not currentCF then
			currentCF = targetCF
		else
			local smooth = config.followSmoothness or DEFAULT_FOLLOW_SMOOTHNESS
			local alpha = math.clamp(dt * smooth, 0, 1)
			currentCF = currentCF:Lerp(targetCF, alpha)
		end

		local hrpPos = hrp.Position
		local petPos = currentCF.Position
		local flatDelta = Vector3.new(petPos.X - hrpPos.X, 0, petPos.Z - hrpPos.Z)
		local flatDist = flatDelta.Magnitude
		local minDist = config.minFlatDistance or DEFAULT_MIN_FLAT_DISTANCE

		if flatDist > 0 and flatDist < minDist then
			local push = minDist - flatDist
			local adjust = flatDelta.Unit * push
			petPos += Vector3.new(adjust.X, 0, adjust.Z)
		end

		local lookDir = hrp.CFrame.LookVector
		local flatLook = Vector3.new(lookDir.X, 0, lookDir.Z)
		if flatLook.Magnitude < 0.01 then
			flatLook = Vector3.new(0, 0, -1)
		else
			flatLook = flatLook.Unit
		end

		local lookAt = petPos + flatLook
		local finalCF = CFrame.new(petPos, lookAt)
		self.petModel:PivotTo(finalCF)
	end)

	print("🐾 Equipped pet:", config.displayName or petKey)
end

local petFollower = PetFollowerSystem.new()

----------------------------------------------------------------
-- PET PREVIEW UI (3D viewport card - POLISHED)
----------------------------------------------------------------
local PetPreviewUI = {}
PetPreviewUI.__index = PetPreviewUI

function PetPreviewUI.new()
	local self = setmetatable({}, PetPreviewUI)

	local gui = Instance.new("ScreenGui")
	gui.Name = "PetPreviewGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling

	local playerGui = player:WaitForChild("PlayerGui")
	gui.Parent = playerGui

	local dim = Instance.new("Frame")
	dim.Name = "Dim"
	dim.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
	dim.BackgroundTransparency = 1
	dim.Size = UDim2.new(1, 0, 1, 0)
	dim.BorderSizePixel = 0
	dim.ZIndex = 8900
	dim.Parent = gui

	local card = Instance.new("Frame")
	card.Name = "Card"
	card.Size = UDim2.new(0, 460, 0, 280)
	card.Position = UDim2.new(0.5, -230, 0.55, -140)
	card.BackgroundColor3 = Color3.fromRGB(20, 20, 25)
	card.BackgroundTransparency = 1
	card.BorderSizePixel = 0
	card.ZIndex = 8910
	card.Parent = gui

	local cardCorner = Instance.new("UICorner")
	cardCorner.CornerRadius = UDim.new(0, 24)
	cardCorner.Parent = card

	local cardGradient = Instance.new("UIGradient")
	cardGradient.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.95),
		NumberSequenceKeypoint.new(1, 0.98)
	})
	cardGradient.Rotation = 45
	cardGradient.Parent = card

	local cardStroke = Instance.new("UIStroke")
	cardStroke.Color = Color3.fromRGB(255, 255, 255)
	cardStroke.Thickness = 3
	cardStroke.Transparency = 1
	cardStroke.Parent = card

	local title = Instance.new("TextLabel")
	title.Name = "Title"
	title.BackgroundTransparency = 1
	title.Size = UDim2.new(1, -32, 0, 44)
	title.Position = UDim2.new(0, 16, 0, 12)
	title.Font = Enum.Font.GothamBold
	title.TextSize = 22
	title.TextXAlignment = Enum.TextXAlignment.Left
	title.TextYAlignment = Enum.TextYAlignment.Center
	title.TextColor3 = Color3.fromRGB(180, 180, 190)
	title.ZIndex = 8920
	title.Parent = card

	local nameLabel = Instance.new("TextLabel")
	nameLabel.Name = "PetName"
	nameLabel.BackgroundTransparency = 1
	nameLabel.Size = UDim2.new(1, -32, 0, 48)
	nameLabel.Position = UDim2.new(0, 16, 0, 68)
	nameLabel.Font = Enum.Font.GothamBlack
	nameLabel.TextSize = 36
	nameLabel.TextXAlignment = Enum.TextXAlignment.Left
	nameLabel.TextYAlignment = Enum.TextYAlignment.Center
	nameLabel.TextColor3 = Color3.fromRGB(255, 200, 230)
	nameLabel.ZIndex = 8920
	nameLabel.Parent = card

	local subtitle = Instance.new("TextLabel")
	subtitle.Name = "Subtitle"
	subtitle.BackgroundTransparency = 1
	subtitle.Size = UDim2.new(1, -32, 0, 60)
	subtitle.Position = UDim2.new(0, 16, 0, 128)
	subtitle.Font = Enum.Font.Gotham
	subtitle.TextSize = 18
	subtitle.TextWrapped = true
	subtitle.TextXAlignment = Enum.TextXAlignment.Left
	subtitle.TextYAlignment = Enum.TextYAlignment.Top
	subtitle.TextColor3 = Color3.fromRGB(140, 140, 150)
	subtitle.ZIndex = 8920
	subtitle.Parent = card

	local viewport = Instance.new("ViewportFrame")
	viewport.Name = "Preview"
	viewport.BackgroundTransparency = 1
	viewport.Size = UDim2.new(0, 180, 0, 180)
	viewport.Position = UDim2.new(1, -196, 0, 54)
	viewport.ZIndex = 8920
	viewport.Ambient = Color3.fromRGB(255, 255, 255)
	viewport.LightColor = Color3.fromRGB(255, 255, 255)
	viewport.Parent = card

	local vCorner = Instance.new("UICorner")
	vCorner.CornerRadius = UDim.new(1, 0)
	vCorner.Parent = viewport

	local vStroke = Instance.new("UIStroke")
	vStroke.Color = Color3.fromRGB(255, 255, 255)
	vStroke.Thickness = 3
	vStroke.Transparency = 0.7
	vStroke.Parent = viewport

	local vGlow = Instance.new("UIGradient")
	vGlow.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.3),
		NumberSequenceKeypoint.new(0.5, 0.7),
		NumberSequenceKeypoint.new(1, 1)
	})
	vGlow.Rotation = 0
	vGlow.Parent = viewport

	local cam = Instance.new("Camera")
	cam.Name = "PreviewCamera"
	cam.Parent = viewport
	viewport.CurrentCamera = cam

	self.Gui = gui
	self.Dim = dim
	self.Card = card
	self.CardStroke = cardStroke
	self.TitleLabel = title
	self.PetNameLabel = nameLabel
	self.SubtitleLabel = subtitle
	self.Viewport = viewport
	self.ViewportCamera = cam
	self.ViewportStroke = vStroke
	self.CurrentModel = nil

	return self
end

function PetPreviewUI:ClearPreviewModel()
	if self.CurrentModel then
		self.CurrentModel:Destroy()
		self.CurrentModel = nil
	end
end

function PetPreviewUI:UpdatePetModel(petConfig)
	self:ClearPreviewModel()
	if not self.Viewport or not self.ViewportCamera then return end
	if not petConfig or not petConfig.templatePath then return end

	local template = resolveTemplate(petConfig.templatePath)
	if not template or not template:IsA("Model") then
		warn("[PetPreviewUI] Cannot resolve pet template for preview:", petConfig.displayName or "Unknown")
		return
	end

	local model = template:Clone()
	model.Parent = self.Viewport
	self.CurrentModel = model

	local primary = model.PrimaryPart
		or model:FindFirstChild("HumanoidRootPart")
		or model:FindFirstChildWhichIsA("BasePart")

	if not primary then
		warn("[PetPreviewUI] Pet model preview has no root part")
		return
	end

	model:PivotTo(CFrame.new(0, 0, 0))

	local _, size = model:GetBoundingBox()
	local maxDim = math.max(size.X, size.Y, size.Z)
	if maxDim <= 0 then maxDim = 5 end
	local dist = maxDim * 1.8
	local focusY = size.Y * 0.5

	local camPos = Vector3.new(0, focusY, dist)
	self.ViewportCamera.CFrame = CFrame.new(camPos, Vector3.new(0, focusY, 0))
end

function PetPreviewUI:Show(petConfig, rarityConfig, duration)
	duration = duration or 2.5
	rarityConfig = rarityConfig or ScreenRarityConfig.Epic

	self.TitleLabel.Text = rarityConfig.titleText or "NEW PET!"
	self.TitleLabel.TextColor3 = rarityConfig.color
	self.PetNameLabel.Text = petConfig.displayName or "Mystery Pet"
	self.PetNameLabel.TextColor3 = rarityConfig.nameColor or rarityConfig.color
	self.SubtitleLabel.Text = petConfig.subtitle or "It will now follow you around!"

	if self.ViewportStroke then
		self.ViewportStroke.Color = rarityConfig.color
	end
	self.CardStroke.Color = rarityConfig.color

	self:UpdatePetModel(petConfig)

	self.Dim.BackgroundTransparency = 1
	self.Card.BackgroundTransparency = 1
	self.Card.Size = UDim2.new(0, 0, 0, 0)
	self.Card.Position = UDim2.new(0.5, 0, 0.55, 0)

	local dimTween = TweenService:Create(
		self.Dim,
		TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.Out),
		{BackgroundTransparency = 0.45}
	)
	local cardTween = TweenService:Create(
		self.Card,
		TweenInfo.new(0.4, Enum.EasingStyle.Back, Enum.EasingDirection.Out),
		{
			BackgroundTransparency = 0,
			Size = UDim2.new(0, 460, 0, 280),
			Position = UDim2.new(0.5, -230, 0.55, -140),
		}
	)
	local strokeTween = TweenService:Create(
		self.CardStroke,
		TweenInfo.new(0.4),
		{Transparency = 0}
	)

	dimTween:Play()
	cardTween:Play()
	strokeTween:Play()

	task.delay(duration, function()
		local dimOut = TweenService:Create(
			self.Dim,
			TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.In),
			{BackgroundTransparency = 1}
		)
		local cardOut = TweenService:Create(
			self.Card,
			TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.In),
			{BackgroundTransparency = 1, Size = UDim2.new(0, 0, 0, 0)}
		)
		local strokeOut = TweenService:Create(
			self.CardStroke,
			TweenInfo.new(0.3),
			{Transparency = 1}
		)

		dimOut:Play()
		cardOut:Play()
		strokeOut:Play()
		self:ClearPreviewModel()
	end)
end

local petPreview = PetPreviewUI.new()

----------------------------------------------------------------
-- HATCH SEQUENCE HELPERS
----------------------------------------------------------------
local isSequenceRunning = false

local function playScreenOnlySequence(rarity)
	if isSequenceRunning or screenVfxSystem.IsTriggering then return end
	isSequenceRunning = true

	local config = ScreenRarityConfig[rarity] or ScreenRarityConfig.Common
	screenVfxSystem:TriggerVFX(rarity)

	task.delay((config.duration or 2) + 1, function()
		isSequenceRunning = false
	end)
end

local function playPetHatchSequence(rarity, petKey)
	if isSequenceRunning or screenVfxSystem.IsTriggering then return end
	petKey = petKey or "Axolotl"
	local petConfig = PET_CONFIGS[petKey]
	if not petConfig then
		warn("No pet config for:", petKey)
		playScreenOnlySequence(rarity)
		return
	end

	isSequenceRunning = true
	rarity = rarity or "Epic"
	local config = ScreenRarityConfig[rarity] or ScreenRarityConfig.Epic

	screenVfxSystem:TriggerVFX(rarity)

	task.spawn(function()
		task.wait((config.buildupTime or 0.5) * 0.6)
		petPreview:Show(petConfig, config, 2.5)
	end)

	task.spawn(function()
		local delayTime = (config.buildupTime or 0.5) + 1.6
		task.wait(delayTime)
		petFollower:EquipPet(petKey)

		local total = (config.duration or 3) + 1
		task.wait(math.max(total - delayTime, 0.5))
		isSequenceRunning = false
	end)
end

----------------------------------------------------------------
-- INTERACTION SYSTEM (press E near VFXInteractive parts) - FIXED!
----------------------------------------------------------------
local currentInteractable = nil
local interactionRange = 10
local interactiveParts = {}
local lastPromptUpdate = 0
local PROMPT_UPDATE_THROTTLE = 0.1 -- Update prompt max 10 times per second

for _, inst in ipairs(CollectionService:GetTagged("VFXInteractive")) do
	if inst:IsA("BasePart") then
		table.insert(interactiveParts, inst)
	end
end

CollectionService:GetInstanceAddedSignal("VFXInteractive"):Connect(function(inst)
	if inst:IsA("BasePart") then
		table.insert(interactiveParts, inst)
		print("✨ VFXInteractive added:", inst.Name)
	end
end)

CollectionService:GetInstanceRemovedSignal("VFXInteractive"):Connect(function(inst)
	local idx = table.find(interactiveParts, inst)
	if idx then
		table.remove(interactiveParts, idx)
	end
	if currentInteractable == inst then
		currentInteractable = nil
	end
end)

local function createInteractionPrompt()
	local screenGui = Instance.new("ScreenGui")
	screenGui.Name = "InteractionPrompt"
	screenGui.ResetOnSpawn = false
	local playerGui = player:WaitForChild("PlayerGui")
	screenGui.Parent = playerGui

	local frame = Instance.new("Frame")
	frame.Name = "PromptFrame"
	frame.Size = UDim2.new(0, 280, 0, 68)
	frame.Position = UDim2.new(0.5, -140, 0.82, 0)
	frame.BackgroundColor3 = Color3.fromRGB(15, 15, 20)
	frame.BackgroundTransparency = 1 -- Start invisible
	frame.BorderSizePixel = 0
	frame.Visible = false
	frame.ZIndex = 1000
	frame.Parent = screenGui

	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 14)
	corner.Parent = frame

	local bgGradient = Instance.new("UIGradient")
	bgGradient.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.3),
		NumberSequenceKeypoint.new(1, 0.4)
	})
	bgGradient.Rotation = 45
	bgGradient.Parent = frame

	local stroke = Instance.new("UIStroke")
	stroke.Name = "Stroke"
	stroke.Color = Color3.fromRGB(255, 255, 255)
	stroke.Thickness = 3
	stroke.Transparency = 1 -- Start invisible
	stroke.Parent = frame

	local label = Instance.new("TextLabel")
	label.Name = "Label"
	label.Size = UDim2.new(1, -16, 1, 0)
	label.Position = UDim2.new(0, 8, 0, 0)
	label.BackgroundTransparency = 1
	label.Text = "[E] Hatch Pet"
	label.Font = Enum.Font.GothamBold
	label.TextSize = 26
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.TextTransparency = 1 -- Start invisible
	label.ZIndex = 1010
	label.Parent = frame

	return screenGui, frame, stroke, label
end

local interactionPrompt, promptFrame, promptStroke, promptLabel = createInteractionPrompt()
print("✅ Interaction system ready! Looking for parts tagged 'VFXInteractive'...")
print("📍 Current interactive parts:", #interactiveParts)

-- FIXED: Only update prompt visibility when actually needed, with throttling
RunService.Heartbeat:Connect(function()
	local now = tick()
	if now - lastPromptUpdate < PROMPT_UPDATE_THROTTLE then return end
	lastPromptUpdate = now

	if not promptFrame then return end

	-- Hide if conditions not met
	if not character or not humanoidRootPart
		or isSequenceRunning or screenVfxSystem.IsTriggering then
		if promptFrame.Visible then
			promptFrame.Visible = false
			promptFrame.BackgroundTransparency = 1
			promptStroke.Transparency = 1
			promptLabel.TextTransparency = 1
		end
		currentInteractable = nil
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

	-- Only show/hide if state changed
	local shouldShow = (closestPart ~= nil)
	local wasVisible = promptFrame.Visible

	if shouldShow ~= wasVisible then
		currentInteractable = closestPart
		promptFrame.Visible = shouldShow

		if shouldShow then
			-- Show with smooth fade-in
			local rarityAttr = closestPart:GetAttribute("VFXRarity")
			local rarity = (typeof(rarityAttr) == "string" and rarityAttr) or "Common"
			local config = ScreenRarityConfig[rarity] or ScreenRarityConfig.Common

			promptStroke.Color = config.color
			local petAttr = closestPart:GetAttribute("PetName")
			local petName = (typeof(petAttr) == "string" and petAttr ~= "") and petAttr or "Pet"
			promptLabel.Text = "[E] Hatch " .. petName
			promptLabel.TextColor3 = config.color

			TweenService:Create(promptFrame, TweenInfo.new(0.2, Enum.EasingStyle.Sine), {
				BackgroundTransparency = 0.3
			}):Play()
			TweenService:Create(promptStroke, TweenInfo.new(0.2, Enum.EasingStyle.Sine), {
				Transparency = 0
			}):Play()
			TweenService:Create(promptLabel, TweenInfo.new(0.2, Enum.EasingStyle.Sine), {
				TextTransparency = 0
			}):Play()
		else
			-- Hide with smooth fade-out
			TweenService:Create(promptFrame, TweenInfo.new(0.15, Enum.EasingStyle.Sine), {
				BackgroundTransparency = 1
			}):Play()
			TweenService:Create(promptStroke, TweenInfo.new(0.15, Enum.EasingStyle.Sine), {
				Transparency = 1
			}):Play()
			TweenService:Create(promptLabel, TweenInfo.new(0.15, Enum.EasingStyle.Sine), {
				TextTransparency = 1
			}):Play()
		end
	elseif shouldShow and closestPart then
		-- Update colors/text if still visible but part changed
		local rarityAttr = closestPart:GetAttribute("VFXRarity")
		local rarity = (typeof(rarityAttr) == "string" and rarityAttr) or "Common"
		local config = ScreenRarityConfig[rarity] or ScreenRarityConfig.Common

		promptStroke.Color = config.color
		local petAttr = closestPart:GetAttribute("PetName")
		local petName = (typeof(petAttr) == "string" and petAttr ~= "") and petAttr or "Pet"
		promptLabel.Text = "[E] Hatch " .. petName
		promptLabel.TextColor3 = config.color
	end
end)

UserInputService.InputBegan:Connect(function(input, gameProcessed)
	if gameProcessed or isSequenceRunning or screenVfxSystem.IsTriggering then return end
	if input.KeyCode ~= Enum.KeyCode.E then return end
	if not currentInteractable then return end

	local rarityAttr = currentInteractable:GetAttribute("VFXRarity")
	local rarity = (typeof(rarityAttr) == "string" and rarityAttr) or "Common"

	local petAttr = currentInteractable:GetAttribute("PetName")
	local petName = (typeof(petAttr) == "string" and petAttr ~= "") and petAttr or "Axolotl"

	local vfxAttr = currentInteractable:GetAttribute("VFXType")
	local vfxType = vfxAttr and string.lower(tostring(vfxAttr)) or nil

	local hasPetConfig = PET_CONFIGS[petName] ~= nil

	local mode
	if vfxType == "screenonly" then
		mode = "screen"
	elseif hasPetConfig then
		mode = "pet"
	elseif vfxType == "screen" then
		mode = "screen"
	else
		mode = hasPetConfig and "pet" or "screen"
	end

	print(("🎮 E pressed on %s rarity:%s pet:%s type:%s (hasPetConfig=%s, mode=%s)"):format(
		currentInteractable.Name,
		rarity,
		petName,
		tostring(vfxType or "nil"),
		tostring(hasPetConfig),
		mode
		))

	-- Hide prompt immediately
	if promptFrame then
		promptFrame.Visible = false
		promptFrame.BackgroundTransparency = 1
		promptStroke.Transparency = 1
		promptLabel.TextTransparency = 1
	end

	if mode == "pet" then
		playPetHatchSequence(rarity, petName)
	else
		playScreenOnlySequence(rarity)
	end
end)

----------------------------------------------------------------
-- GLOBAL TEST FUNCTIONS
----------------------------------------------------------------
_G.TriggerVFX = function(rarity)
	rarity = rarity or "Epic"
	print("🎮 _G.TriggerVFX called with:", rarity)
	playScreenOnlySequence(rarity)
end

_G.TestEggReveal = function(rarity, petName)
	rarity = rarity or "Epic"
	petName = petName or "Axolotl"
	print("🥚 _G.TestEggReveal -> Hatch:", rarity, petName)
	playPetHatchSequence(rarity, petName)
end

----------------------------------------------------------------
-- DONE
----------------------------------------------------------------
print("✅ UNIFIED VFX SYSTEM + PET FOLLOWER v2 (POLISHED) LOADED!")
print("📦 Systems available:")
print("   ✅ Screen VFX System (no 3D eggs spawned by client)")
print("   ✅ Pet hatch 3D preview + Axolotl follower")
print("   ✅ FIXED: GUI only shows when near eggs (no premature display)")
print("💡 Press E near parts tagged 'VFXInteractive' to hatch!")
print("💡 Or test in console: _G.TestEggReveal('Epic','Axolotl')")
