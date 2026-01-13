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

	-- Find the main egg part (try PrimaryPart, EggBase, or any Part)
	local eggBase = eggModel.PrimaryPart or eggModel:FindFirstChild("EggBase") or eggModel:FindFirstChildWhichIsA("BasePart")
	if not eggBase then
		error("EggModel has no parts!")
	end
	
	-- Set PrimaryPart if not set
	if eggModel.PrimaryPart == nil then
		eggModel.PrimaryPart = eggBase
	end
	
	-- Aura and light are OPTIONAL (user's egg might not have them!)
	local aura = eggModel:FindFirstChild("Aura")
	local light = aura and aura:FindFirstChildWhichIsA("PointLight")
	
	-- Sparkles are also optional
	local sparkleAttachment = eggBase:FindFirstChild("SparkleAttachment")
	local sparkleEmitter = sparkleAttachment and sparkleAttachment:FindFirstChildWhichIsA("ParticleEmitter")

	-- Position model in front of player
	local root = getRoot(self.Player)
	if root then
		local rootCF = root.CFrame
		local eggCF = rootCF * CFrame.new(0, 2, -camDistance)
		eggModel:SetPrimaryPartCFrame(eggCF)
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

	-- Initial visual state (only if aura exists) ---------------------------
	local auraBaseSize, auraBuildSize, auraFlashSize
	
	if aura then
		auraBaseSize = aura.Size
		auraBuildSize = auraBaseSize * 1.05
		auraFlashSize = auraBaseSize * 1.2
		
		aura.Color = color
		aura.Size = auraBaseSize
		aura.Transparency = 1
		aura.Material = Enum.Material.Neon
		aura.CanCollide = false
		aura.Anchored = true
		
		-- Position aura with the egg
		aura.CFrame = eggBase.CFrame
	end

	if light then
		light.Color = color
		light.Brightness = 0
		light.Range = 0
	end

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

	-- Tweens (only create if aura/light exist) ------------------------------

	local buildInfo = TweenInfo.new(0.45, Enum.EasingStyle.Sine, Enum.EasingDirection.Out)
	local flashInfo = TweenInfo.new(0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	local fadeInfo = TweenInfo.new(0.5, Enum.EasingStyle.Sine, Enum.EasingDirection.In)

	local buildAura, flashAura, fadeAura
	local buildLight, flashLight, fadeLight
	
	if aura then
		buildAura = TweenService:Create(aura, buildInfo, {
			Transparency = 0.3,
			Size = auraBuildSize
		})
		flashAura = TweenService:Create(aura, flashInfo, {
			Transparency = 0.15,
			Size = auraFlashSize
		})
		fadeAura = TweenService:Create(aura, fadeInfo, {
			Transparency = 1,
			Size = auraBaseSize
		})
	end
	
	if light then
		buildLight = TweenService:Create(light, buildInfo, {
			Brightness = 4,
			Range = 16
		})
		flashLight = TweenService:Create(light, flashInfo, {
			Brightness = 8,
			Range = 24
		})
		fadeLight = TweenService:Create(light, fadeInfo, {
			Brightness = 0,
			Range = 0
		})
	end

	-- Sequence -------------------------------------------------------------

	-- Small lead-in for dramatization
	safeWait(0.1)

	-- BUILDUP (only if aura exists)
	if buildAura then buildAura:Play() end
	if buildLight then buildLight:Play() end
	if buildAura then
		buildAura.Completed:Wait()
	else
		safeWait(0.45)  -- Wait same time even without aura
	end

	-- FLASH
	if sparkleEmitter then
		sparkleEmitter:Emit(80)
	end
	if self.ScreenVFX then
		self.ScreenVFX:Pulse(color)
	end

	if flashAura then flashAura:Play() end
	if flashLight then flashLight:Play() end
	if flashAura then
		flashAura.Completed:Wait()
	else
		safeWait(0.2)  -- Wait same time even without aura
	end

	-- Hold moment on screen
	safeWait(duration * 0.3)

	-- FADE OUT
	if fadeAura then fadeAura:Play() end
	if fadeLight then fadeLight:Play() end
	if fadeAura then
		fadeAura.Completed:Wait()
	else
		safeWait(0.5)  -- Wait same time even without aura
	end

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
