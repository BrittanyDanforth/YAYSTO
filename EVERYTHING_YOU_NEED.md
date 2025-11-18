# 🔥 EVERYTHING YOU NEED - ONE PLACE! 🔥

## 🎯 WHICH SYSTEM DO YOU WANT?

### 🥚 OPTION A: EGG REVEALS (Cinematic Camera + 3D Egg)
**Use this for:** Pet hatching, gacha, loot boxes (like Pet Simulator X)
- ✅ Camera moves to show egg
- ✅ 3D egg model with glowing crack
- ✅ UI shows pet name + rarity
- ✅ Super cinematic!

**GO TO:** Section 1 below

---

### ⚡ OPTION B: SCREEN VFX ONLY (No Camera Movement)
**Use this for:** Collectibles, power-ups, quick feedback
- ✅ NO camera movement (stays in gameplay)
- ✅ Screen effects only
- ✅ Quick and non-intrusive
- ✅ Beams, particles, waves, etc.

**GO TO:** Section 2 below

---

### 🎮 OPTION C: BOTH!
**Use both systems together**
- Rare stuff → Egg reveals (cinematic)
- Common stuff → Screen VFX (quick)

**GO TO:** Both sections below

---

---

# 📦 SECTION 1: EGG REVEAL SYSTEM (Cinematic)

## Step 1: Create Folders

In **Roblox Studio**:

1. Open **ReplicatedStorage**
2. Create folder called `VFX`
3. Create folder called `Assets`

```
ReplicatedStorage
├── VFX (Folder)
└── Assets (Folder)
```

---

## Step 2: Add Module #1 - EggRevealVFX

1. Inside `ReplicatedStorage.VFX`, insert a **ModuleScript**
2. Name it: `EggRevealVFX`
3. Paste this code:

```lua
--!strict
-- EggRevealVFX Module

local TweenService = game:GetService("TweenService")
local RS = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

export type EggRevealConfig = {
	color: Color3?,
	text: string?,
	tier: string?,
	petName: string?,
	duration: number?,
	cameraDistance: number?
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

function EggRevealVFX.new(player: Player): EggRevealVFX
	local self = setmetatable({}, EggRevealVFX)
	self.Player = player
	self.ScreenVFX = nil
	return self
end

local function getRoot(participant: Player): BasePart?
	local char = participant.Character or participant.CharacterAdded:Wait()
	local root = char:FindFirstChild("HumanoidRootPart")
	if root and root:IsA("BasePart") then
		return root
	end
	return nil
end

local function safeWait(t: number)
	if t > 0 then
		task.wait(t)
	end
end

function EggRevealVFX:Play(eggTemplate: Model, config: EggRevealConfig?)
	config = config or {}
	local color = config.color or Color3.fromRGB(255, 255, 255)
	local duration = config.duration or 2.5
	local camDistance = config.cameraDistance or 10

	local eggModel: Model = eggTemplate:Clone()
	eggModel.Name = "EggRevealModel"
	eggModel.Parent = Workspace

	local eggBase = eggModel:WaitForChild("EggBase") :: BasePart
	local aura = eggModel:WaitForChild("Aura") :: BasePart
	local light = aura:WaitForChild("PointLight") :: PointLight

	local sparkleAttachment = eggBase:FindFirstChild("SparkleAttachment")
	local sparkleEmitter = sparkleAttachment and sparkleAttachment:FindFirstChildWhichIsA("ParticleEmitter")

	if eggModel.PrimaryPart == nil then
		eggModel.PrimaryPart = eggBase
	end

	local root = getRoot(self.Player)
	if root then
		local rootCF = root.CFrame
		local eggCF = rootCF * CFrame.new(0, 2, -camDistance)
		eggModel:SetPrimaryPartCFrame(eggCF)
		aura.CFrame = eggBase.CFrame
	end

	local camera = Workspace.CurrentCamera
	assert(camera, "No CurrentCamera")

	local oldCamType = camera.CameraType
	local oldCamCF = camera.CFrame

	local targetPos = eggBase.Position
	local camOffset = Vector3.new(0, 2, camDistance * 0.6)
	local camPos = targetPos + (eggBase.CFrame.LookVector * camDistance * 0.4) + camOffset

	camera.CameraType = Enum.CameraType.Scriptable
	camera.CFrame = CFrame.new(camPos, targetPos)

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

	if self.ScreenVFX then
		self.ScreenVFX:Show({
			color = color,
			text = config.text,
			tier = config.tier,
			petName = config.petName
		})
	end

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

	safeWait(0.1)

	buildAura:Play()
	buildLight:Play()
	buildAura.Completed:Wait()

	if sparkleEmitter then
		sparkleEmitter:Emit(80)
	end
	if self.ScreenVFX then
		self.ScreenVFX:Pulse(color)
	end

	flashAura:Play()
	flashLight:Play()
	flashAura.Completed:Wait()

	safeWait(duration * 0.3)

	fadeAura:Play()
	fadeLight:Play()
	fadeAura.Completed:Wait()

	if self.ScreenVFX then
		self.ScreenVFX:Hide()
	end

	eggModel:Destroy()

	camera.CameraType = oldCamType
	camera.CFrame = oldCamCF
end

return EggRevealVFX
```

---

## Step 3: Add Module #2 - ScreenVFX

1. Inside `ReplicatedStorage.VFX`, insert another **ModuleScript**
2. Name it: `ScreenVFX`
3. Paste this code:

```lua
--!strict
-- ScreenVFX Module

local TweenService = game:GetService("TweenService")

export type EggRevealConfig = {
	color: Color3?,
	text: string?,
	tier: string?,
	petName: string?
}

export type ScreenVFX = {
	Player: Player,
	Gui: ScreenGui,
	Show: (self: ScreenVFX, config: EggRevealConfig) -> (),
	Pulse: (self: ScreenVFX, color: Color3?) -> (),
	Hide: (self: ScreenVFX) -> ()
}

local ScreenVFX = {}
ScreenVFX.__index = ScreenVFX

local function createGui(player: Player): ScreenGui
	local gui = Instance.new("ScreenGui")
	gui.Name = "EggRevealGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	local overlay = Instance.new("Frame")
	overlay.Name = "Overlay"
	overlay.BackgroundColor3 = Color3.new(0, 0, 0)
	overlay.BackgroundTransparency = 1
	overlay.BorderSizePixel = 0
	overlay.Size = UDim2.new(1, 0, 1, 0)
	overlay.Position = UDim2.new(0, 0, 0, 0)
	overlay.ZIndex = 1
	overlay.Parent = gui

	local card = Instance.new("Frame")
	card.Name = "Card"
	card.AnchorPoint = Vector2.new(0.5, 0.5)
	card.Position = UDim2.new(0.5, 0, 0.7, 0)
	card.Size = UDim2.new(0, 320, 0, 120)
	card.BackgroundColor3 = Color3.fromRGB(15, 23, 42)
	card.BackgroundTransparency = 1
	card.BorderSizePixel = 0
	card.ZIndex = 2
	card.Parent = gui

	local uicorner = Instance.new("UICorner")
	uicorner.CornerRadius = UDim.new(0, 16)
	uicorner.Parent = card

	local stroke = Instance.new("UIStroke")
	stroke.Name = "Stroke"
	stroke.Thickness = 0
	stroke.Color = Color3.fromRGB(255, 255, 255)
	stroke.Parent = card

	local padding = Instance.new("UIPadding")
	padding.PaddingTop = UDim.new(0, 10)
	padding.PaddingBottom = UDim.new(0, 10)
	padding.PaddingLeft = UDim.new(0, 14)
	padding.PaddingRight = UDim.new(0, 14)
	padding.Parent = card

	local tierLabel = Instance.new("TextLabel")
	tierLabel.Name = "TierLabel"
	tierLabel.BackgroundTransparency = 1
	tierLabel.Size = UDim2.new(1, 0, 0, 24)
	tierLabel.Position = UDim2.new(0, 0, 0, 0)
	tierLabel.Font = Enum.Font.GothamBold
	tierLabel.TextScaled = true
	tierLabel.TextColor3 = Color3.fromRGB(148, 163, 184)
	tierLabel.TextXAlignment = Enum.TextXAlignment.Left
	tierLabel.TextYAlignment = Enum.TextYAlignment.Center
	tierLabel.TextTransparency = 1
	tierLabel.ZIndex = 3
	tierLabel.Parent = card

	local nameLabel = Instance.new("TextLabel")
	nameLabel.Name = "NameLabel"
	nameLabel.BackgroundTransparency = 1
	nameLabel.Size = UDim2.new(1, 0, 0, 40)
	nameLabel.Position = UDim2.new(0, 0, 0, 26)
	nameLabel.Font = Enum.Font.GothamBlack
	nameLabel.TextScaled = true
	nameLabel.TextColor3 = Color3.fromRGB(248, 250, 252)
	nameLabel.TextXAlignment = Enum.TextXAlignment.Left
	nameLabel.TextYAlignment = Enum.TextYAlignment.Center
	nameLabel.TextTransparency = 1
	nameLabel.ZIndex = 3
	nameLabel.Parent = card

	local subLabel = Instance.new("TextLabel")
	subLabel.Name = "SubLabel"
	subLabel.BackgroundTransparency = 1
	subLabel.Size = UDim2.new(1, 0, 0, 28)
	subLabel.Position = UDim2.new(0, 0, 0, 68)
	subLabel.Font = Enum.Font.Gotham
	subLabel.TextScaled = true
	subLabel.TextColor3 = Color3.fromRGB(148, 163, 184)
	subLabel.TextXAlignment = Enum.TextXAlignment.Left
	subLabel.TextYAlignment = Enum.TextYAlignment.Center
	subLabel.TextTransparency = 1
	subLabel.ZIndex = 3
	subLabel.Parent = card

	return gui
end

function ScreenVFX.new(player: Player): ScreenVFX
	local existing = player:FindFirstChildOfClass("PlayerGui")
	if not existing then
		player.CharacterAdded:Wait()
	end

	local gui = player.PlayerGui:FindFirstChild("EggRevealGui") :: ScreenGui?
	if not gui then
		gui = createGui(player)
	end

	local self = setmetatable({}, ScreenVFX)
	self.Player = player
	self.Gui = gui
	return self
end

local function getGuiParts(gui: ScreenGui)
	local overlay = gui:WaitForChild("Overlay") :: Frame
	local card = gui:WaitForChild("Card") :: Frame
	local tierLabel = card:WaitForChild("TierLabel") :: TextLabel
	local nameLabel = card:WaitForChild("NameLabel") :: TextLabel
	local subLabel = card:WaitForChild("SubLabel") :: TextLabel
	local stroke = card:WaitForChild("Stroke") :: UIStroke
	return overlay, card, tierLabel, nameLabel, subLabel, stroke
end

function ScreenVFX:Show(config: EggRevealConfig)
	local overlay, card, tierLabel, nameLabel, subLabel, stroke = getGuiParts(self.Gui)
	local color = config.color or Color3.fromRGB(255, 255, 255)

	card.BackgroundColor3 = Color3.fromRGB(15, 23, 42)
	stroke.Color = color

	tierLabel.Text = (config.text or config.tier or ""):upper()
	nameLabel.Text = config.petName or ""
	subLabel.Text = "You hatched a new pet!"

	overlay.BackgroundTransparency = 1
	card.BackgroundTransparency = 1
	tierLabel.TextTransparency = 1
	nameLabel.TextTransparency = 1
	subLabel.TextTransparency = 1
	stroke.Thickness = 0

	local info = TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.Out)

	TweenService:Create(overlay, info, {
		BackgroundTransparency = 0.35
	}):Play()

	TweenService:Create(card, info, {
		BackgroundTransparency = 0.05
	}):Play()

	TweenService:Create(tierLabel, info, {
		TextTransparency = 0
	}):Play()

	TweenService:Create(nameLabel, info, {
		TextTransparency = 0
	}):Play()

	TweenService:Create(subLabel, info, {
		TextTransparency = 0.1
	}):Play()

	TweenService:Create(stroke, info, {
		Thickness = 1.5
	}):Play()
end

function ScreenVFX:Pulse(color: Color3?)
	local _, card, _, _, _, stroke = getGuiParts(self.Gui)
	color = color or Color3.fromRGB(255, 255, 255)

	stroke.Color = color

	local infoOut = TweenInfo.new(0.12, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	local infoIn = TweenInfo.new(0.15, Enum.EasingStyle.Quad, Enum.EasingDirection.In)

	card.AnchorPoint = Vector2.new(0.5, 0.5)

	local pulseOut = TweenService:Create(card, infoOut, {
		Size = UDim2.new(0, 340, 0, 130)
	})
	local strokeOut = TweenService:Create(stroke, infoOut, {
		Thickness = 3
	})

	local pulseIn = TweenService:Create(card, infoIn, {
		Size = UDim2.new(0, 320, 0, 120)
	})
	local strokeIn = TweenService:Create(stroke, infoIn, {
		Thickness = 1.5
	})

	pulseOut:Play()
	strokeOut:Play()
	pulseOut.Completed:Wait()

	pulseIn:Play()
	strokeIn:Play()
end

function ScreenVFX:Hide()
	local overlay, card, tierLabel, nameLabel, subLabel, stroke = getGuiParts(self.Gui)

	local info = TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.In)

	local t1 = TweenService:Create(overlay, info, {
		BackgroundTransparency = 1
	})
	local t2 = TweenService:Create(card, info, {
		BackgroundTransparency = 1
	})
	local t3 = TweenService:Create(tierLabel, info, {
		TextTransparency = 1
	})
	local t4 = TweenService:Create(nameLabel, info, {
		TextTransparency = 1
	})
	local t5 = TweenService:Create(subLabel, info, {
		TextTransparency = 1
	})
	local t6 = TweenService:Create(stroke, info, {
		Thickness = 0
	})

	t1:Play()
	t2:Play()
	t3:Play()
	t4:Play()
	t5:Play()
	t6:Play()
	t1.Completed:Wait()
end

return ScreenVFX
```

---

## Step 4: Create the EggModel

1. In **ReplicatedStorage.Assets**, create a **Model** named `EggModel`

2. Inside the model, create:

### Part 1: EggBase (the shell)
- Insert a **Part** named `EggBase`
- Shape: Ball
- Size: `3, 4, 3`
- Material: SmoothPlastic
- Anchored: ✓
- CanCollide: ☐
- Add a **SpecialMesh** inside it:
  - MeshId: `rbxassetid://1527559`

### Part 2: Aura (the glow)
- Insert another **Part** named `Aura`
- Shape: Ball
- Size: `2.7, 3.6, 2.7` (90% of EggBase size - this creates the crack!)
- Material: Neon
- Transparency: 0.3
- Anchored: ✓
- CanCollide: ☐
- Position: **SAME as EggBase** (centered!)

### Part 3: PointLight
- Inside Aura, add a **PointLight**
- Brightness: 2
- Range: 15

### CRITICAL: Set PrimaryPart!
- Right-click `EggModel` → **Set PrimaryPart** → Select `EggBase`

**Your EggModel should look like:**
```
EggModel (Model)
├── Aura (Part, Neon Ball)
│   └── PointLight
└── EggBase (Part, Shell)
    └── Mesh (SpecialMesh)
```

---

## Step 5: Add the Client Script

1. Go to **StarterPlayer** → **StarterPlayerScripts**
2. Insert a **LocalScript**
3. Name it whatever you want
4. Paste this code:

```lua
-- EGG REVEAL CLIENT

local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local CollectionService = game:GetService("CollectionService")

local player = Players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local humanoidRootPart = character:WaitForChild("HumanoidRootPart")

local VFXFolder = RS:WaitForChild("VFX")
local EggRevealVFX = require(VFXFolder:WaitForChild("EggRevealVFX"))
local ScreenVFX = require(VFXFolder:WaitForChild("ScreenVFX"))

local eggTemplate = RS:WaitForChild("Assets"):WaitForChild("EggModel") :: Model

-- RARITY CONFIGS
local RarityConfigs = {
	Common = {
		color = Color3.fromRGB(200, 200, 200),
		text = "COMMON",
		tier = "Common",
		duration = 2.0,
		cameraDistance = 10
	},
	Rare = {
		color = Color3.fromRGB(0, 150, 255),
		text = "RARE",
		tier = "Rare",
		duration = 2.5,
		cameraDistance = 11
	},
	Epic = {
		color = Color3.fromRGB(138, 43, 226),
		text = "EPIC",
		tier = "Epic",
		duration = 3.0,
		cameraDistance = 12
	},
	Legendary = {
		color = Color3.fromRGB(255, 215, 0),
		text = "LEGENDARY",
		tier = "Legendary",
		duration = 3.5,
		cameraDistance = 13
	}
}

local eggVfx = EggRevealVFX.new(player)
eggVfx.ScreenVFX = ScreenVFX.new(player)

local isPlaying = false
local currentInteractable = nil
local interactionRange = 10

local function createInteractionPrompt()
	local playerGui = player:WaitForChild("PlayerGui")
	
	local existing = playerGui:FindFirstChild("InteractionPrompt")
	if existing then
		return existing
	end
	
	local screenGui = Instance.new("ScreenGui")
	screenGui.Name = "InteractionPrompt"
	screenGui.ResetOnSpawn = false
	screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	screenGui.Parent = playerGui

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

	local textLabel = Instance.new("TextLabel")
	textLabel.Name = "Label"
	textLabel.Size = UDim2.new(1, 0, 1, 0)
	textLabel.BackgroundTransparency = 1
	textLabel.Text = "[E] Hatch Egg"
	textLabel.Font = Enum.Font.GothamBold
	textLabel.TextSize = 24
	textLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
	textLabel.Parent = frame

	return screenGui
end

local interactionPrompt = createInteractionPrompt()

local function triggerEggReveal(rarity: string, petName: string?)
	if isPlaying then return end
	isPlaying = true

	local config = RarityConfigs[rarity] or RarityConfigs.Common
	config.petName = petName or "Mystery Pet"

	print("🥚 Hatching egg:", rarity, "-", config.petName)

	eggVfx:Play(eggTemplate, config)

	task.wait(config.duration + 1)
	isPlaying = false
end

local interactiveParts = {}

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

RunService.Heartbeat:Connect(function()
	if not character or not humanoidRootPart or isPlaying then
		if interactionPrompt then
			local frame = interactionPrompt:FindFirstChild("PromptFrame")
			if frame then frame.Visible = false end
		end
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
			local config = RarityConfigs[rarity]
			if config then
				local stroke = frame:FindFirstChild("Stroke") :: UIStroke?
				local label = frame:FindFirstChild("Label") :: TextLabel?
				if stroke then stroke.Color = config.color end
				if label then label.TextColor3 = config.color end
			end
		end
	end
end)

UserInputService.InputBegan:Connect(function(input, gameProcessed)
	if gameProcessed or isPlaying then return end

	if input.KeyCode == Enum.KeyCode.E then
		if currentInteractable then
			local frame = interactionPrompt:FindFirstChild("PromptFrame")
			if frame then frame.Visible = false end

			local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
			local petName = currentInteractable:GetAttribute("PetName") or "Mystery Pet"

			triggerEggReveal(rarity, petName)
		end
	end
end)

_G.TestEggReveal = function(rarity: string?, petName: string?)
	triggerEggReveal(rarity or "Epic", petName or "Cerberage")
end

print("✨ Egg Reveal VFX System Loaded!")
print("💡 Press E near interactive parts to hatch eggs")
print("🧪 Test with: _G.TestEggReveal('Epic', 'Cerberage')")
```

---

## Step 6: Test It!

1. Press **Play**
2. Open console (F9)
3. Type: `_G.TestEggReveal("Epic", "Cerberage")`
4. Press Enter

**BOOM! EGG REVEAL!** 🥚✨

---

---

# ⚡ SECTION 2: SCREEN VFX ONLY (No Camera)

## Simple - Just ONE File!

1. Go to **StarterPlayer** → **StarterPlayerScripts**
2. Insert a **LocalScript**
3. Name it whatever
4. Paste THIS ENTIRE CODE:

```lua
-- STANDALONE SCREEN VFX (NO CAMERA MOVEMENT!)

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

function ScreenVFX:RadialBlur(maxSize, duration, bloomIntensity)
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

function ScreenVFX:ScreenBeams(color, count, duration)
	local center = UDim2.fromScale(0.5, 0.5)
	local maxLen = math.max(self.Camera.ViewportSize.X, self.Camera.ViewportSize.Y) * 0.8
	local growTime = 0.3
	
	for i = 1, count do
		local angle = (i - 1) * (360 / count)
		
		local beam = Instance.new("Frame")
		beam.Name = "Beam"
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

function ScreenVFX:TriggerVFX(rarity)
	if self.IsTriggering then return end
	self.IsTriggering = true

	local config = RarityConfig[rarity] or RarityConfig.Common
	print("🔥 VFX TRIGGERED - RARITY:", rarity)

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

	task.spawn(function() self:ScreenParticles(config.color, config.particleCount, config.duration) end)
	task.spawn(function() self:ScreenBeams(config.color, config.beamCount, config.duration * 0.8) end)
	task.spawn(function() self:CircularWaves(config.color, config.ringCount, config.duration) end)
	task.spawn(function() self:TextPopup(config.text, config.color, config.duration) end)

	self:PlaySound("rbxassetid://9114221327", 0.5)

	task.wait(config.duration + 0.5)
	self.IsTriggering = false
end

local vfxSystem = ScreenVFX.new()

local currentInteractable = nil
local interactionRange = 10
local interactiveParts = {}

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

UserInputService.InputBegan:Connect(function(input, gameProcessed)
	if gameProcessed or vfxSystem.IsTriggering then return end

	if input.KeyCode == Enum.KeyCode.E and currentInteractable then
		local frame = interactionPrompt:FindFirstChild("PromptFrame")
		if frame then frame.Visible = false end

		local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
		vfxSystem:TriggerVFX(rarity)
	end
end)

_G.TriggerVFX = function(rarity)
	vfxSystem:TriggerVFX(rarity or "Epic")
end

print("✨ Screen VFX System Loaded!")
print("💡 Press E near interactive parts for VFX")
print("🧪 Test with: _G.TriggerVFX('Epic')")
```

---

## Test It!

1. Press **Play**
2. Open console (F9)
3. Type: `_G.TriggerVFX("Epic")`

**BOOM! SCREEN VFX!** ⚡

---

---

# 🖥️ BONUS: SERVER SCRIPT (Spawns Test Objects)

Add this to **ServerScriptService** as a **Script**:

```lua
-- SERVER SCRIPT (spawns interactive stuff)

local CollectionService = game:GetService("CollectionService")

local function createInteractiveEgg(position, rarity, petName)
	local egg = Instance.new("Part")
	egg.Name = rarity .. "Egg"
	egg.Size = Vector3.new(3, 4, 3)
	egg.Position = position
	egg.Anchored = true
	egg.CanCollide = false
	egg.Material = Enum.Material.SmoothPlastic
	egg.Shape = Enum.PartType.Ball
	egg.Parent = workspace
	
	local rarityColors = {
		Common = Color3.fromRGB(200, 200, 200),
		Rare = Color3.fromRGB(0, 150, 255),
		Epic = Color3.fromRGB(138, 43, 226),
		Legendary = Color3.fromRGB(255, 215, 0)
	}
	
	egg.Color = rarityColors[rarity] or rarityColors.Common
	
	egg:SetAttribute("VFXInteractive", true)
	egg:SetAttribute("VFXRarity", rarity)
	egg:SetAttribute("PetName", petName or "Mystery Pet")
	
	CollectionService:AddTag(egg, "VFXInteractive")
	
	local pointLight = Instance.new("PointLight")
	pointLight.Color = egg.Color
	pointLight.Brightness = 2
	pointLight.Range = 20
	pointLight.Parent = egg
	
	local bodyPosition = Instance.new("BodyPosition")
	bodyPosition.MaxForce = Vector3.new(0, math.huge, 0)
	bodyPosition.Position = position + Vector3.new(0, 1, 0)
	bodyPosition.D = 200
	bodyPosition.P = 5000
	bodyPosition.Parent = egg
	
	local bodyAngularVelocity = Instance.new("BodyAngularVelocity")
	bodyAngularVelocity.AngularVelocity = Vector3.new(0, 1, 0)
	bodyAngularVelocity.MaxTorque = Vector3.new(0, math.huge, 0)
	bodyAngularVelocity.P = 1000
	bodyAngularVelocity.Parent = egg
	
	task.spawn(function()
		local startY = position.Y
		local time = 0
		while egg.Parent do
			time += 0.05
			local offset = math.sin(time * 2) * 0.5
			bodyPosition.Position = Vector3.new(position.X, startY + offset, position.Z)
			task.wait(0.05)
		end
	end)
	
	print("✨ Created", rarity, "egg at", position)
	return egg
end

_G.CreateInteractiveEgg = createInteractiveEgg

-- Auto-spawn test eggs after 2 seconds
task.wait(2)

createInteractiveEgg(Vector3.new(0, 10, 0), "Common", "Doggo")
createInteractiveEgg(Vector3.new(10, 10, 0), "Rare", "Shadow Wolf")
createInteractiveEgg(Vector3.new(20, 10, 0), "Epic", "Cerberage")
createInteractiveEgg(Vector3.new(30, 10, 0), "Legendary", "Phoenix")

print("✨ Server Script Loaded!")
print("💡 Use: _G.CreateInteractiveEgg(position, rarity, petName)")
```

This spawns 4 test eggs you can walk up to and press E!

---

---

# 🎯 SUMMARY

## For Egg Reveals (Cinematic):
✅ 2 Modules in `ReplicatedStorage.VFX`
✅ EggModel in `ReplicatedStorage.Assets`
✅ 1 Client script in `StarterPlayerScripts`
✅ Optional: Server script

**Test:** `_G.TestEggReveal("Epic", "Cerberage")`

## For Screen VFX (No Camera):
✅ 1 Client script in `StarterPlayerScripts`
✅ Optional: Server script

**Test:** `_G.TriggerVFX("Epic")`

---

**PRESS E FOR EPICNESS!** 🔥
