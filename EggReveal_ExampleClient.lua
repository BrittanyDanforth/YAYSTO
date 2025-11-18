--[[
    EGG REVEAL - EXAMPLE CLIENT SCRIPT
    
    This shows how to wire up EggRevealVFX + ScreenVFX together.
    
    INSTALLATION:
    1. Put EggRevealVFX.lua in ReplicatedStorage.VFX
    2. Put ScreenVFX.lua in ReplicatedStorage.VFX
    3. Put this script in StarterPlayerScripts as a LocalScript
    4. Create your EggModel in ReplicatedStorage.Assets
    
    USAGE:
    - Walk up to interactive parts with VFXInteractive attribute
    - Press E to trigger egg reveal VFX
    - Or call _G.TestEggReveal() from console
]]

local RS = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local CollectionService = game:GetService("CollectionService")

local player = Players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local humanoidRootPart = character:WaitForChild("HumanoidRootPart")

-- Load modules
local VFXFolder = RS:WaitForChild("VFX")
local EggRevealVFX = require(VFXFolder:WaitForChild("EggRevealVFX"))
local ScreenVFX = require(VFXFolder:WaitForChild("ScreenVFX"))

-- Load egg template
local eggTemplate = RS:WaitForChild("Assets"):WaitForChild("EggModel") :: Model

-- RARITY CONFIGURATIONS
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

-- Initialize VFX system
local eggVfx = EggRevealVFX.new(player)
eggVfx.ScreenVFX = ScreenVFX.new(player)

-- State
local isPlaying = false
local currentInteractable = nil
local interactionRange = 10

-- Create interaction prompt
local function createInteractionPrompt()
	local playerGui = player:WaitForChild("PlayerGui")
	
	-- Check if already exists
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

-- Trigger egg reveal with rarity
local function triggerEggReveal(rarity: string, petName: string?)
	if isPlaying then return end
	isPlaying = true

	local config = RarityConfigs[rarity] or RarityConfigs.Common
	config.petName = petName or "Mystery Pet"

	print("🥚 Hatching egg:", rarity, "-", config.petName)

	-- Play the egg reveal!
	eggVfx:Play(eggTemplate, config)

	-- Cooldown
	task.wait(config.duration + 1)
	isPlaying = false
end

-- Interactive part detection (using CollectionService for performance)
local interactiveParts = {}

-- Initialize with existing tagged parts
for _, inst in ipairs(CollectionService:GetTagged("VFXInteractive")) do
	if inst:IsA("BasePart") then
		table.insert(interactiveParts, inst)
	end
end

-- Listen for new/removed tagged parts
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

-- Find nearby interactables (optimized loop)
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

		-- Update prompt color based on rarity
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

-- Handle E key press
UserInputService.InputBegan:Connect(function(input, gameProcessed)
	if gameProcessed or isPlaying then return end

	if input.KeyCode == Enum.KeyCode.E then
		if currentInteractable then
			-- Hide prompt
			local frame = interactionPrompt:FindFirstChild("PromptFrame")
			if frame then frame.Visible = false end

			-- Get rarity and pet name from attributes
			local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
			local petName = currentInteractable:GetAttribute("PetName") or "Mystery Pet"

			-- Trigger VFX
			triggerEggReveal(rarity, petName)
		end
	end
end)

-- Global test function
_G.TestEggReveal = function(rarity: string?, petName: string?)
	triggerEggReveal(rarity or "Epic", petName or "Cerberage")
end

print("✨ Egg Reveal VFX System Loaded!")
print("💡 Press E near interactive parts to hatch eggs")
print("🧪 Test with: _G.TestEggReveal('Epic', 'Cerberage')")
