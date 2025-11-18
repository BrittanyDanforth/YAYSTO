--!strict
--[[
    EGG REVEAL VFX MODULE
    
    Handles world-space egg VFX with:
    - Camera control (cinematic view)
    - Aura crack glow (buildup + flash)
    - PointLight effects
    - Optional particle bursts
    - Screen VFX integration
    
    LOCATION: ReplicatedStorage.VFX.EggRevealVFX
    
    REQUIRES: EggModel with structure:
        EggModel
        ├─ Aura (Part, Neon Ball)
        │   └─ PointLight
        └─ EggBase (Part, PrimaryPart)
            └─ Optional: SparkleAttachment
                └─ ParticleEmitter
]]

local TweenService = game:GetService("TweenService")
local RS = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

export type EggRevealConfig = {
	color: Color3?,
	text: string?,          -- e.g. "Epic"
	tier: string?,          -- "Epic"
	petName: string?,       -- "Cerberage"
	duration: number?,      -- total time before cleanup
	cameraDistance: number? -- distance from player
}

export type ScreenVFXLike = {
	Show: (self: any, config: EggRevealConfig) -> (),
	Pulse: (self: any, color: Color3?) -> (),
	Hide: (self: any) -> ()
}

export type EggRevealVFX = {
	Player: Player,
	ScreenVFX: ScreenVFXLike?,

	Play: (self: EggRevealVFX, eggTemplate: Model, config: EggRevealConfig?) -> ()
}

local EggRevealVFX = {}
EggRevealVFX.__index = EggRevealVFX

-- Constructor --------------------------------------------------------------

function EggRevealVFX.new(player: Player): EggRevealVFX
	local self = setmetatable({}, EggRevealVFX)
	self.Player = player
	self.ScreenVFX = nil
	return self
end

-- Utility: get character + root --------------------------------------------

local function getRoot(participant: Player): BasePart?
	local char = participant.Character or participant.CharacterAdded:Wait()
	local root = char:FindFirstChild("HumanoidRootPart")
	if root and root:IsA("BasePart") then
		return root
	end
	return nil
end

-- Utility: safe wait -------------------------------------------------------

local function safeWait(t: number)
	if t > 0 then
		task.wait(t)
	end
end

-- Main Play sequence -------------------------------------------------------

function EggRevealVFX:Play(eggTemplate: Model, config: EggRevealConfig?)
	config = config or {}
	local color = config.color or Color3.fromRGB(255, 255, 255)
	local duration = config.duration or 2.5
	local camDistance = config.cameraDistance or 10

	-- Clone model
	local eggModel: Model = eggTemplate:Clone()
	eggModel.Name = "EggRevealModel"
	eggModel.Parent = Workspace

	-- Grab parts the model guarantees
	local eggBase = eggModel:WaitForChild("EggBase") :: BasePart
	local aura = eggModel:WaitForChild("Aura") :: BasePart
	local light = aura:WaitForChild("PointLight") :: PointLight

	local sparkleAttachment = eggBase:FindFirstChild("SparkleAttachment")
	local sparkleEmitter = sparkleAttachment and sparkleAttachment:FindFirstChildWhichIsA("ParticleEmitter")

	-- Ensure primary part
	if eggModel.PrimaryPart == nil then
		eggModel.PrimaryPart = eggBase
	end

	-- Position model in front of player
	local root = getRoot(self.Player)
	if root then
		local rootCF = root.CFrame
		local eggCF = rootCF * CFrame.new(0, 2, -camDistance)
		eggModel:SetPrimaryPartCFrame(eggCF)
		aura.CFrame = eggBase.CFrame
	end

	-- Setup camera
	local camera = Workspace.CurrentCamera
	assert(camera, "No CurrentCamera")

	local oldCamType = camera.CameraType
	local oldCamCF = camera.CFrame

	local targetPos = eggBase.Position
	local camOffset = Vector3.new(0, 2, camDistance * 0.6)
	local camPos = targetPos + (eggBase.CFrame.LookVector * camDistance * 0.4) + camOffset

	camera.CameraType = Enum.CameraType.Scriptable
	camera.CFrame = CFrame.new(camPos, targetPos)

	-- Initial visual state -------------------------------------------------
	local auraBaseSize = aura.Size
	local auraBuildSize = auraBaseSize * 1.05
	local auraFlashSize = auraBaseSize * 1.2

	aura.Color = color
	aura.Size = auraBaseSize
	aura.Transparency = 1
	aura.Material = Enum.Material.Neon
	aura.CanCollide = false
	aura.Anchored = true

	light.Color = color
	light.Brightness = 0
	light.Range = 0

	if sparkleEmitter then
		sparkleEmitter.Enabled = false
	end

	-- Inform ScreenVFX (UI) ------------------------------------------------
	if self.ScreenVFX then
		self.ScreenVFX:Show({
			color = color,
			text = config.text,
			tier = config.tier,
			petName = config.petName
		})
	end

	-- Tweens ---------------------------------------------------------------

	local buildInfo = TweenInfo.new(0.45, Enum.EasingStyle.Sine, Enum.EasingDirection.Out)
	local flashInfo = TweenInfo.new(0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	local fadeInfo = TweenInfo.new(0.5, Enum.EasingStyle.Sine, Enum.EasingDirection.In)

	local buildAura = TweenService:Create(aura, buildInfo, {
		Transparency = 0.3,
		Size = auraBuildSize
	})

	local buildLight = TweenService:Create(light, buildInfo, {
		Brightness = 4,
		Range = 16
	})

	local flashAura = TweenService:Create(aura, flashInfo, {
		Transparency = 0.15,
		Size = auraFlashSize
	})

	local flashLight = TweenService:Create(light, flashInfo, {
		Brightness = 8,
		Range = 24
	})

	local fadeAura = TweenService:Create(aura, fadeInfo, {
		Transparency = 1,
		Size = auraBaseSize
	})

	local fadeLight = TweenService:Create(light, fadeInfo, {
		Brightness = 0,
		Range = 0
	})

	-- Sequence -------------------------------------------------------------

	-- Small lead-in for dramatization
	safeWait(0.1)

	-- BUILDUP (crack glow intensifies!)
	buildAura:Play()
	buildLight:Play()
	buildAura.Completed:Wait()

	-- FLASH (intense crack burst!)
	if sparkleEmitter then
		sparkleEmitter:Emit(80)
	end
	if self.ScreenVFX then
		self.ScreenVFX:Pulse(color)
	end

	flashAura:Play()
	flashLight:Play()
	flashAura.Completed:Wait()

	-- Hold moment on screen
	safeWait(duration * 0.3)

	-- FADE OUT
	fadeAura:Play()
	fadeLight:Play()
	fadeAura.Completed:Wait()

	-- UI fade-out
	if self.ScreenVFX then
		self.ScreenVFX:Hide()
	end

	-- Cleanup
	eggModel:Destroy()

	-- Restore camera
	camera.CameraType = oldCamType
	camera.CFrame = oldCamCF
end

return EggRevealVFX
