--[[
    OPTIMIZED VFX CLIENT SCRIPT (CollectionService + Cached Parts)
    
    INSTALLATION:
    1. Put this in StarterPlayerScripts as a LocalScript
    2. Put ScreenVFX.lua in ReplicatedStorage.VFX
    3. Tag parts with "VFXInteractive" using CollectionService
    4. Add "VFXRarity" attribute (String: "Common", "Rare", "Epic")
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local CollectionService = game:GetService("CollectionService")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local humanoidRootPart = character:WaitForChild("HumanoidRootPart")

-- Load ScreenVFX module
local ScreenVFX = require(ReplicatedStorage:WaitForChild("VFX"):WaitForChild("ScreenVFX"))
local vfxSystem = ScreenVFX.new(player)

-- CACHED INTERACTIVE PARTS (No more GetDescendants spam!)
local interactiveParts = {}

-- Initialize with existing tagged parts
for _, inst in ipairs(CollectionService:GetTagged("VFXInteractive")) do
    if inst:IsA("BasePart") then
        table.insert(interactiveParts, inst)
    end
end

-- Listen for new tagged parts
CollectionService:GetInstanceAddedSignal("VFXInteractive"):Connect(function(inst)
    if inst:IsA("BasePart") then
        table.insert(interactiveParts, inst)
        print("✅ Added VFX interactive part:", inst.Name)
    end
end)

-- Remove tagged parts
CollectionService:GetInstanceRemovedSignal("VFXInteractive"):Connect(function(inst)
    for i, v in ipairs(interactiveParts) do
        if v == inst then
            table.remove(interactiveParts, i)
            print("❌ Removed VFX interactive part:", inst.Name)
            break
        end
    end
end)

-- INTERACTION HANDLER
local currentInteractable = nil
local interactionRange = 10

-- Create interaction prompt
local function createInteractionPrompt()
    local frame = Instance.new("Frame")
    frame.Name = "InteractionPrompt"
    frame.Size = UDim2.new(0, 220, 0, 60)
    frame.Position = UDim2.new(0.5, -110, 0.85, 0)
    frame.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
    frame.BackgroundTransparency = 0.3
    frame.BorderSizePixel = 0
    frame.Visible = false
    frame.ZIndex = 1000
    frame.Parent = vfxSystem.ScreenGui
    
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(0, 10)
    corner.Parent = frame
    
    local stroke = Instance.new("UIStroke")
    stroke.Color = Color3.fromRGB(0, 255, 255)
    stroke.Thickness = 3
    stroke.Parent = frame
    
    local textLabel = Instance.new("TextLabel")
    textLabel.Size = UDim2.new(1, 0, 1, 0)
    textLabel.BackgroundTransparency = 1
    textLabel.Text = "[E] Interact"
    textLabel.Font = Enum.Font.GothamBold
    textLabel.TextSize = 24
    textLabel.TextColor3 = Color3.fromRGB(0, 255, 255)
    textLabel.Parent = frame
    
    return frame
end

local interactionPrompt = createInteractionPrompt()

-- OPTIMIZED PROXIMITY CHECK (Only cached parts, no GetDescendants!)
RunService.Heartbeat:Connect(function()
    if not character or not humanoidRootPart or vfxSystem.isTriggering then return end
    
    local closestPart = nil
    local closestDistance = interactionRange
    
    -- Loop only cached tagged parts (FAST!)
    for _, part in ipairs(interactiveParts) do
        if part and part.Parent then
            local distance = (humanoidRootPart.Position - part.Position).Magnitude
            if distance < closestDistance then
                closestPart = part
                closestDistance = distance
            end
        end
    end
    
    currentInteractable = closestPart
    interactionPrompt.Visible = currentInteractable ~= nil
    
    -- Update prompt color based on rarity
    if currentInteractable then
        local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
        local rarityColors = {
            Common = Color3.fromRGB(200, 200, 200),
            Rare = Color3.fromRGB(0, 150, 255),
            Epic = Color3.fromRGB(255, 0, 255)
        }
        local color = rarityColors[rarity] or rarityColors.Common
        
        interactionPrompt:FindFirstChildOfClass("UIStroke").Color = color
        interactionPrompt:FindFirstChildOfClass("TextLabel").TextColor3 = color
    end
end)

-- E KEY HANDLER
UserInputService.InputBegan:Connect(function(input, gameProcessed)
    if gameProcessed or vfxSystem.isTriggering then return end
    
    if input.KeyCode == Enum.KeyCode.E then
        if currentInteractable then
            interactionPrompt.Visible = false
            
            -- Get rarity
            local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
            
            -- Trigger VFX
            vfxSystem:TriggerVFX(rarity)
            
            -- Optional: Fire custom event
            if currentInteractable:FindFirstChild("InteractEvent") then
                currentInteractable.InteractEvent:Fire()
            end
        end
    end
end)

print("✨ OPTIMIZED VFX System Loaded!")
print("📋 Using CollectionService (no GetDescendants lag!)")
print("💡 Tag parts with 'VFXInteractive' + add 'VFXRarity' attribute")
print("🎯 Currently tracking", #interactiveParts, "interactive parts")

-- Expose for testing
_G.TriggerVFX = function(rarity)
    vfxSystem:TriggerVFX(rarity or "Epic")
end
