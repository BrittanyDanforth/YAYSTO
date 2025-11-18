--!strict
--[[
    SCREEN VFX MODULE
    
    Minimal, clean UI overlay for egg reveals.
    Shows tier badge + pet name with smooth animations.
    
    LOCATION: ReplicatedStorage.VFX.ScreenVFX
    
    METHODS:
    - Show(config) → Fade in overlay + card
    - Pulse(color) → Flash effect on reveal
    - Hide() → Fade out everything
]]

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

-- Private: build the GUI ---------------------------------------------------

local function createGui(player: Player): ScreenGui
	local gui = Instance.new("ScreenGui")
	gui.Name = "EggRevealGui"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	-- Dark overlay
	local overlay = Instance.new("Frame")
	overlay.Name = "Overlay"
	overlay.BackgroundColor3 = Color3.new(0, 0, 0)
	overlay.BackgroundTransparency = 1
	overlay.BorderSizePixel = 0
	overlay.Size = UDim2.new(1, 0, 1, 0)
	overlay.Position = UDim2.new(0, 0, 0, 0)
	overlay.ZIndex = 1
	overlay.Parent = gui

	-- Card container
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

	-- Tier text (small label)
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

	-- Pet name (big text)
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

	-- Sub text
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

-- Constructor --------------------------------------------------------------

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

-- Helpers ------------------------------------------------------------------

local function getGuiParts(gui: ScreenGui)
	local overlay = gui:WaitForChild("Overlay") :: Frame
	local card = gui:WaitForChild("Card") :: Frame
	local tierLabel = card:WaitForChild("TierLabel") :: TextLabel
	local nameLabel = card:WaitForChild("NameLabel") :: TextLabel
	local subLabel = card:WaitForChild("SubLabel") :: TextLabel
	local stroke = card:WaitForChild("Stroke") :: UIStroke
	return overlay, card, tierLabel, nameLabel, subLabel, stroke
end

-- Public: Show -------------------------------------------------------------

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

	-- Fade in overlay + card + text
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

-- Public: Pulse (called on flash) -----------------------------------------

function ScreenVFX:Pulse(color: Color3?)
	local _, card, _, _, _, stroke = getGuiParts(self.Gui)
	color = color or Color3.fromRGB(255, 255, 255)

	stroke.Color = color

	local infoOut = TweenInfo.new(0.12, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	local infoIn = TweenInfo.new(0.15, Enum.EasingStyle.Quad, Enum.EasingDirection.In)

	-- Slight scale & border pulse
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

-- Public: Hide -------------------------------------------------------------

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
