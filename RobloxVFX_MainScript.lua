--[[
    EPIC ROBLOX VFX SYSTEM
    Press E on interactive objects for INSANE effects!
    
    INSTALLATION:
    1. Put this in StarterPlayer > StarterPlayerScripts as a LocalScript
    2. Add "VFXInteractive" tag to any parts you want to be interactive
    3. Or use ProximityPrompts
--]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local humanoidRootPart = character:WaitForChild("HumanoidRootPart")
local camera = workspace.CurrentCamera

-- VFX System
local VFXSystem = {}
VFXSystem.__index = VFXSystem

function VFXSystem.new()
    local self = setmetatable({}, VFXSystem)
    self.activeEffects = {}
    self.screenGui = self:CreateScreenGui()
    return self
end

function VFXSystem:CreateScreenGui()
    local screenGui = Instance.new("ScreenGui")
    screenGui.Name = "EpicVFXGui"
    screenGui.ResetOnSpawn = false
    screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    screenGui.Parent = player.PlayerGui
    return screenGui
end

-- SCREEN SHAKE
function VFXSystem:ScreenShake(intensity, duration)
    local intensity = intensity or 0.5
    local duration = duration or 0.5
    
    spawn(function()
        local elapsed = 0
        local connection
        connection = RunService.RenderStepped:Connect(function(dt)
            elapsed = elapsed + dt
            if elapsed >= duration then
                camera.CFrame = camera.CFrame * CFrame.new(0, 0, 0)
                connection:Disconnect()
                return
            end
            
            local shake = CFrame.new(
                math.random(-100, 100) / 100 * intensity,
                math.random(-100, 100) / 100 * intensity,
                math.random(-100, 100) / 100 * intensity
            ) * CFrame.Angles(
                math.rad(math.random(-100, 100) / 100 * intensity),
                math.rad(math.random(-100, 100) / 100 * intensity),
                math.rad(math.random(-100, 100) / 100 * intensity)
            )
            
            camera.CFrame = camera.CFrame * shake
        end)
    end)
end

-- COLOR FLASH
function VFXSystem:ColorFlash(color, duration)
    local flash = Instance.new("Frame")
    flash.Name = "ColorFlash"
    flash.Size = UDim2.new(1, 0, 1, 0)
    flash.Position = UDim2.new(0, 0, 0, 0)
    flash.BackgroundColor3 = color or Color3.fromRGB(0, 255, 255)
    flash.BackgroundTransparency = 0.3
    flash.BorderSizePixel = 0
    flash.ZIndex = 10000
    flash.Parent = self.screenGui
    
    TweenService:Create(flash, TweenInfo.new(duration or 0.4), {
        BackgroundTransparency = 1
    }):Play()
    
    game:GetService("Debris"):AddItem(flash, duration or 0.4)
end

-- RADIAL BLUR
function VFXSystem:RadialBlur(duration)
    local blur = Instance.new("BlurEffect")
    blur.Size = 0
    blur.Parent = camera
    
    local tweenIn = TweenService:Create(blur, TweenInfo.new(0.1), {Size = 24})
    local tweenOut = TweenService:Create(blur, TweenInfo.new(duration or 0.5), {Size = 0})
    
    tweenIn:Play()
    tweenIn.Completed:Connect(function()
        tweenOut:Play()
    end)
    
    tweenOut.Completed:Connect(function()
        blur:Destroy()
    end)
end

-- TEXT POPUP
function VFXSystem:TextPopup(text, position)
    local texts = {"EPIC!", "LEGENDARY!", "INSANE!", "WOW!", "BOOM!", "AMAZING!"}
    local displayText = text or texts[math.random(1, #texts)]
    
    local textLabel = Instance.new("TextLabel")
    textLabel.Name = "TextPopup"
    textLabel.Text = displayText
    textLabel.Font = Enum.Font.GothamBold
    textLabel.TextSize = 80
    textLabel.TextColor3 = Color3.fromRGB(0, 255, 255)
    textLabel.TextStrokeTransparency = 0
    textLabel.TextStrokeColor3 = Color3.fromRGB(255, 0, 255)
    textLabel.BackgroundTransparency = 1
    textLabel.Size = UDim2.new(0, 400, 0, 100)
    textLabel.Position = UDim2.new(0.5, -200, 0.5, -50)
    textLabel.ZIndex = 10001
    textLabel.Parent = self.screenGui
    
    -- Glow effect
    local uiStroke = Instance.new("UIStroke")
    uiStroke.Color = Color3.fromRGB(0, 255, 255)
    uiStroke.Thickness = 3
    uiStroke.Parent = textLabel
    
    local gradient = Instance.new("UIGradient")
    gradient.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(0, 255, 255)),
        ColorSequenceKeypoint.new(0.5, Color3.fromRGB(255, 0, 255)),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(0, 255, 255))
    })
    gradient.Parent = textLabel
    
    -- Animate
    TweenService:Create(textLabel, TweenInfo.new(1.5, Enum.EasingStyle.Exponential), {
        Position = UDim2.new(0.5, -200, 0.2, -50),
        TextTransparency = 1,
        TextStrokeTransparency = 1
    }):Play()
    
    game:GetService("Debris"):AddItem(textLabel, 1.5)
end

-- CIRCULAR WAVES (GUI)
function VFXSystem:CircularWaves(count)
    for i = 1, count or 3 do
        task.wait(0.2)
        
        local wave = Instance.new("Frame")
        wave.Name = "CircularWave"
        wave.Size = UDim2.new(0, 100, 0, 100)
        wave.Position = UDim2.new(0.5, -50, 0.5, -50)
        wave.BackgroundTransparency = 1
        wave.ZIndex = 9990 + i
        wave.Parent = self.screenGui
        
        local corner = Instance.new("UICorner")
        corner.CornerRadius = UDim.new(1, 0)
        corner.Parent = wave
        
        local stroke = Instance.new("UIStroke")
        stroke.Color = Color3.fromRGB(0, 255, 255)
        stroke.Thickness = 4
        stroke.Transparency = 0
        stroke.Parent = wave
        
        TweenService:Create(wave, TweenInfo.new(1), {
            Size = UDim2.new(0, 600, 0, 600),
            Position = UDim2.new(0.5, -300, 0.5, -300)
        }):Play()
        
        TweenService:Create(stroke, TweenInfo.new(1), {
            Transparency = 1
        }):Play()
        
        game:GetService("Debris"):AddItem(wave, 1)
    end
end

-- PARTICLE EXPLOSION (3D World Space)
function VFXSystem:ParticleExplosion(position)
    local part = Instance.new("Part")
    part.Name = "VFXEmitter"
    part.Size = Vector3.new(1, 1, 1)
    part.Position = position
    part.Anchored = true
    part.CanCollide = false
    part.Transparency = 1
    part.Parent = workspace
    
    -- Main particle explosion
    local particleEmitter = Instance.new("ParticleEmitter")
    particleEmitter.Enabled = false
    particleEmitter.Lifetime = NumberRange.new(1, 2)
    particleEmitter.Rate = 100
    particleEmitter.SpreadAngle = Vector2.new(180, 180)
    particleEmitter.Speed = NumberRange.new(20, 40)
    particleEmitter.Acceleration = Vector3.new(0, -10, 0)
    particleEmitter.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(0, 255, 255)),
        ColorSequenceKeypoint.new(0.5, Color3.fromRGB(255, 0, 255)),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(138, 43, 226))
    })
    particleEmitter.Size = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 2),
        NumberSequenceKeypoint.new(1, 0)
    })
    particleEmitter.Transparency = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 0),
        NumberSequenceKeypoint.new(1, 1)
    })
    particleEmitter.LightEmission = 1
    particleEmitter.Parent = part
    
    -- Sparkles
    local sparkles = Instance.new("Sparkles")
    sparkles.SparkleColor = Color3.fromRGB(0, 255, 255)
    sparkles.Parent = part
    
    -- Glow
    local light = Instance.new("PointLight")
    light.Color = Color3.fromRGB(0, 255, 255)
    light.Brightness = 5
    light.Range = 30
    light.Parent = part
    
    -- Emit
    particleEmitter:Emit(100)
    
    -- Fade light
    TweenService:Create(light, TweenInfo.new(1), {
        Brightness = 0,
        Range = 0
    }):Play()
    
    game:GetService("Debris"):AddItem(part, 3)
end

-- ENERGY BEAMS
function VFXSystem:EnergyBeams(position, count)
    for i = 1, count or 12 do
        local angle = (math.pi * 2 * i) / (count or 12)
        local direction = Vector3.new(math.cos(angle), 0, math.sin(angle))
        
        local attachment0 = Instance.new("Attachment")
        local attachment1 = Instance.new("Attachment")
        
        local startPart = Instance.new("Part")
        startPart.Size = Vector3.new(0.5, 0.5, 0.5)
        startPart.Position = position
        startPart.Anchored = true
        startPart.CanCollide = false
        startPart.Transparency = 1
        startPart.Parent = workspace
        
        local endPart = Instance.new("Part")
        endPart.Size = Vector3.new(0.5, 0.5, 0.5)
        endPart.Position = position + (direction * 30)
        endPart.Anchored = true
        endPart.CanCollide = false
        endPart.Transparency = 1
        endPart.Parent = workspace
        
        attachment0.Parent = startPart
        attachment1.Parent = endPart
        
        local beam = Instance.new("Beam")
        beam.Attachment0 = attachment0
        beam.Attachment1 = attachment1
        beam.Width0 = 2
        beam.Width1 = 0
        beam.Color = ColorSequence.new(Color3.fromRGB(0, 255, 255))
        beam.LightEmission = 1
        beam.LightInfluence = 0
        beam.FaceCamera = true
        beam.Parent = startPart
        
        game:GetService("Debris"):AddItem(startPart, 0.6)
        game:GetService("Debris"):AddItem(endPart, 0.6)
    end
end

-- SHOCKWAVE
function VFXSystem:Shockwave(position)
    local part = Instance.new("Part")
    part.Name = "Shockwave"
    part.Size = Vector3.new(1, 0.5, 1)
    part.Position = position
    part.Anchored = true
    part.CanCollide = false
    part.Material = Enum.Material.Neon
    part.Color = Color3.fromRGB(0, 255, 255)
    part.Transparency = 0.5
    part.Shape = Enum.PartType.Cylinder
    part.Orientation = Vector3.new(0, 0, 90)
    part.Parent = workspace
    
    TweenService:Create(part, TweenInfo.new(1), {
        Size = Vector3.new(1, 40, 40),
        Transparency = 1
    }):Play()
    
    game:GetService("Debris"):AddItem(part, 1)
end

-- MAIN TRIGGER FUNCTION
function VFXSystem:TriggerAllEffects(position)
    print("🔥 EPIC VFX TRIGGERED AT:", position)
    
    -- Screen effects
    self:ScreenShake(1, 0.5)
    self:ColorFlash(Color3.fromRGB(0, 255, 255), 0.4)
    self:RadialBlur(0.6)
    
    -- GUI effects
    self:TextPopup()
    self:CircularWaves(3)
    
    -- World space effects
    self:ParticleExplosion(position)
    self:EnergyBeams(position, 12)
    self:Shockwave(position)
    
    -- Sound effect
    self:PlaySound()
end

-- SOUND EFFECT
function VFXSystem:PlaySound()
    local sound = Instance.new("Sound")
    sound.SoundId = "rbxassetid://9125402735" -- Epic impact sound
    sound.Volume = 0.5
    sound.Parent = camera
    sound:Play()
    game:GetService("Debris"):AddItem(sound, 2)
end

-- Initialize VFX System
local vfxSystem = VFXSystem.new()

-- INTERACTION HANDLER
local currentInteractable = nil
local interactionRange = 10

-- Create interaction UI
local function createInteractionPrompt()
    local frame = Instance.new("Frame")
    frame.Name = "InteractionPrompt"
    frame.Size = UDim2.new(0, 200, 0, 50)
    frame.Position = UDim2.new(0.5, -100, 0.85, 0)
    frame.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
    frame.BackgroundTransparency = 0.3
    frame.BorderSizePixel = 0
    frame.Visible = false
    frame.ZIndex = 1000
    frame.Parent = vfxSystem.screenGui
    
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(0, 8)
    corner.Parent = frame
    
    local stroke = Instance.new("UIStroke")
    stroke.Color = Color3.fromRGB(0, 255, 255)
    stroke.Thickness = 2
    stroke.Parent = frame
    
    local textLabel = Instance.new("TextLabel")
    textLabel.Size = UDim2.new(1, 0, 1, 0)
    textLabel.BackgroundTransparency = 1
    textLabel.Text = "[E] Interact"
    textLabel.Font = Enum.Font.GothamBold
    textLabel.TextSize = 20
    textLabel.TextColor3 = Color3.fromRGB(0, 255, 255)
    textLabel.Parent = frame
    
    return frame
end

local interactionPrompt = createInteractionPrompt()

-- Find nearby interactables
RunService.RenderStepped:Connect(function()
    if not character or not humanoidRootPart then return end
    
    local closestPart = nil
    local closestDistance = interactionRange
    
    -- Look for parts tagged as interactive
    for _, part in pairs(workspace:GetDescendants()) do
        if part:IsA("BasePart") and part:GetAttribute("VFXInteractive") then
            local distance = (humanoidRootPart.Position - part.Position).Magnitude
            if distance < closestDistance then
                closestPart = part
                closestDistance = distance
            end
        end
    end
    
    currentInteractable = closestPart
    interactionPrompt.Visible = currentInteractable ~= nil
end)

-- Handle E key press
UserInputService.InputBegan:Connect(function(input, gameProcessed)
    if gameProcessed then return end
    
    if input.KeyCode == Enum.KeyCode.E then
        if currentInteractable then
            -- Trigger VFX at the interactable's position
            vfxSystem:TriggerAllEffects(currentInteractable.Position)
            
            -- Optional: Fire a custom event
            if currentInteractable:FindFirstChild("InteractEvent") then
                currentInteractable.InteractEvent:Fire()
            end
        else
            -- Trigger VFX at player position if no interactable
            vfxSystem:TriggerAllEffects(humanoidRootPart.Position + Vector3.new(0, 3, 0))
        end
    end
end)

-- Handle ProximityPrompts (if you're using them)
local ProximityPromptService = game:GetService("ProximityPromptService")
ProximityPromptService.PromptTriggered:Connect(function(prompt, playerWhoTriggered)
    if playerWhoTriggered == player then
        local position = prompt.Parent.Position
        vfxSystem:TriggerAllEffects(position)
    end
end)

print("✨ Epic VFX System Loaded! Press E near interactive objects!")
print("💡 Tag parts with 'VFXInteractive' attribute to make them interactive")

-- Expose to global for testing
_G.TriggerVFX = function(position)
    vfxSystem:TriggerAllEffects(position or humanoidRootPart.Position)
end
