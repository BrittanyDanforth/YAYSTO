--[[
    TRIPLE AAA EPIC ROBLOX VFX SYSTEM
    Press E on interactive objects for INSANE cinematic effects!
    
    INSTALLATION:
    1. Put this in StarterPlayer > StarterPlayerScripts as a LocalScript
    2. Add "VFXInteractive" attribute (Boolean = true) to any parts
--]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local Debris = game:GetService("Debris")

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

-- BUILDUP ANIMATION (AAA Quality - shows before explosion)
function VFXSystem:BuildupAnimation(part, duration)
    local duration = duration or 1.5
    
    -- Create glow sphere around the part
    local glowSphere = Instance.new("Part")
    glowSphere.Name = "BuildupGlow"
    glowSphere.Size = part.Size * 1.2
    glowSphere.Position = part.Position
    glowSphere.Anchored = true
    glowSphere.CanCollide = false
    glowSphere.Material = Enum.Material.Neon
    glowSphere.Color = Color3.fromRGB(0, 255, 255)
    glowSphere.Transparency = 0.7
    glowSphere.Shape = Enum.PartType.Ball
    glowSphere.Parent = workspace
    
    -- Pulsing light
    local light = Instance.new("PointLight")
    light.Color = Color3.fromRGB(0, 255, 255)
    light.Brightness = 1
    light.Range = 10
    light.Parent = glowSphere
    
    -- Energy rings expanding
    for i = 1, 3 do
        task.wait(0.3)
        local ring = Instance.new("Part")
        ring.Name = "EnergyRing"
        ring.Size = Vector3.new(1, 0.2, 1)
        ring.Position = part.Position
        ring.Anchored = true
        ring.CanCollide = false
        ring.Material = Enum.Material.Neon
        ring.Color = Color3.fromRGB(0, 255, 255)
        ring.Transparency = 0.3
        ring.Shape = Enum.PartType.Cylinder
        ring.Orientation = Vector3.new(0, 0, 90)
        ring.Parent = workspace
        
        -- Expand ring
        TweenService:Create(ring, TweenInfo.new(0.8), {
            Size = Vector3.new(1, part.Size.X * 4, part.Size.Z * 4),
            Transparency = 1
        }):Play()
        
        Debris:AddItem(ring, 0.8)
    end
    
    -- Pulse the glow sphere
    local pulseTween = TweenService:Create(glowSphere, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {
        Size = part.Size * 1.5,
        Transparency = 0.4
    })
    pulseTween:Play()
    
    -- Pulse the light
    local lightTween = TweenService:Create(light, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {
        Brightness = 5,
        Range = 30
    })
    lightTween:Play()
    
    -- Particle buildup
    local buildupParticles = Instance.new("ParticleEmitter")
    buildupParticles.Enabled = true
    buildupParticles.Lifetime = NumberRange.new(0.5, 1)
    buildupParticles.Rate = 50
    buildupParticles.SpreadAngle = Vector2.new(0, 0)
    buildupParticles.Speed = NumberRange.new(-5, -10)
    buildupParticles.Acceleration = Vector3.new(0, 5, 0)
    buildupParticles.Color = ColorSequence.new(Color3.fromRGB(0, 255, 255))
    buildupParticles.Size = NumberSequence.new(0.5, 0)
    buildupParticles.Transparency = NumberSequence.new(0, 1)
    buildupParticles.LightEmission = 1
    buildupParticles.Parent = glowSphere
    
    -- Cleanup after duration
    task.wait(duration)
    pulseTween:Cancel()
    lightTween:Cancel()
    buildupParticles.Enabled = false
    
    -- Final flash before explosion
    TweenService:Create(glowSphere, TweenInfo.new(0.2), {
        Size = part.Size * 2,
        Transparency = 0
    }):Play()
    
    task.wait(0.2)
    glowSphere:Destroy()
end

-- SCREEN SHAKE (Longer and more cinematic)
function VFXSystem:ScreenShake(intensity, duration)
    local intensity = intensity or 1.5
    local duration = duration or 1.5
    
    spawn(function()
        local elapsed = 0
        local connection
        connection = RunService.RenderStepped:Connect(function(dt)
            elapsed = elapsed + dt
            if elapsed >= duration then
                connection:Disconnect()
                return
            end
            
            -- Decay shake over time
            local progress = elapsed / duration
            local currentIntensity = intensity * (1 - progress)
            
            local shake = CFrame.new(
                math.random(-100, 100) / 100 * currentIntensity,
                math.random(-100, 100) / 100 * currentIntensity,
                math.random(-100, 100) / 100 * currentIntensity
            ) * CFrame.Angles(
                math.rad(math.random(-100, 100) / 100 * currentIntensity),
                math.rad(math.random(-100, 100) / 100 * currentIntensity),
                math.rad(math.random(-100, 100) / 100 * currentIntensity)
            )
            
            camera.CFrame = camera.CFrame * shake
        end)
    end)
end

-- COLOR FLASH (More intense and longer)
function VFXSystem:ColorFlash(color, duration, intensity)
    local flash = Instance.new("Frame")
    flash.Name = "ColorFlash"
    flash.Size = UDim2.new(1, 0, 1, 0)
    flash.Position = UDim2.new(0, 0, 0, 0)
    flash.BackgroundColor3 = color or Color3.fromRGB(0, 255, 255)
    flash.BackgroundTransparency = 1 - (intensity or 0.5)
    flash.BorderSizePixel = 0
    flash.ZIndex = 10000
    flash.Parent = self.screenGui
    
    -- Add gradient for cooler effect
    local gradient = Instance.new("UIGradient")
    gradient.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(0, 255, 255)),
        ColorSequenceKeypoint.new(0.5, Color3.fromRGB(255, 255, 255)),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 0, 255))
    })
    gradient.Rotation = 45
    gradient.Parent = flash
    
    TweenService:Create(flash, TweenInfo.new(duration or 1), {
        BackgroundTransparency = 1
    }):Play()
    
    Debris:AddItem(flash, duration or 1)
end

-- RADIAL BLUR (More dramatic)
function VFXSystem:RadialBlur(duration)
    local blur = Instance.new("BlurEffect")
    blur.Size = 0
    blur.Parent = camera
    
    local tweenIn = TweenService:Create(blur, TweenInfo.new(0.2), {Size = 40})
    local tweenOut = TweenService:Create(blur, TweenInfo.new(duration or 1.5), {Size = 0})
    
    tweenIn:Play()
    tweenIn.Completed:Connect(function()
        tweenOut:Play()
    end)
    
    tweenOut.Completed:Connect(function()
        blur:Destroy()
    end)
end

-- TEXT POPUP (More dramatic with better animation)
function VFXSystem:TextPopup(text, position)
    local texts = {"EPIC!", "LEGENDARY!", "INSANE!", "AMAZING!", "SPECTACULAR!", "PHENOMENAL!"}
    local displayText = text or texts[math.random(1, #texts)]
    
    local textLabel = Instance.new("TextLabel")
    textLabel.Name = "TextPopup"
    textLabel.Text = displayText
    textLabel.Font = Enum.Font.GothamBold
    textLabel.TextSize = 100
    textLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
    textLabel.TextStrokeTransparency = 0
    textLabel.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
    textLabel.BackgroundTransparency = 1
    textLabel.Size = UDim2.new(0, 600, 0, 150)
    textLabel.Position = UDim2.new(0.5, -300, 0.5, -75)
    textLabel.TextTransparency = 1
    textLabel.TextStrokeTransparency = 1
    textLabel.ZIndex = 10001
    textLabel.Parent = self.screenGui
    
    -- Epic stroke effect
    local uiStroke = Instance.new("UIStroke")
    uiStroke.Color = Color3.fromRGB(0, 255, 255)
    uiStroke.Thickness = 6
    uiStroke.Transparency = 1
    uiStroke.Parent = textLabel
    
    -- Gradient
    local gradient = Instance.new("UIGradient")
    gradient.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(0, 255, 255)),
        ColorSequenceKeypoint.new(0.5, Color3.fromRGB(255, 255, 255)),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 0, 255))
    })
    gradient.Rotation = 45
    gradient.Parent = textLabel
    
    -- Fade in
    TweenService:Create(textLabel, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
        TextTransparency = 0,
        TextStrokeTransparency = 0
    }):Play()
    
    TweenService:Create(uiStroke, TweenInfo.new(0.3), {
        Transparency = 0
    }):Play()
    
    -- Hold
    task.wait(0.5)
    
    -- Fade out and move up
    TweenService:Create(textLabel, TweenInfo.new(1.5, Enum.EasingStyle.Exponential), {
        Position = UDim2.new(0.5, -300, 0.1, -75),
        TextTransparency = 1,
        TextStrokeTransparency = 1,
        TextSize = 120
    }):Play()
    
    TweenService:Create(uiStroke, TweenInfo.new(1.5), {
        Transparency = 1
    }):Play()
    
    Debris:AddItem(textLabel, 2)
end

-- CIRCULAR WAVES (More and longer lasting)
function VFXSystem:CircularWaves(count)
    for i = 1, count or 5 do
        task.wait(0.3)
        
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
        
        local colors = {
            Color3.fromRGB(0, 255, 255),
            Color3.fromRGB(255, 0, 255),
            Color3.fromRGB(138, 43, 226),
            Color3.fromRGB(0, 200, 255),
            Color3.fromRGB(255, 100, 255)
        }
        
        local stroke = Instance.new("UIStroke")
        stroke.Color = colors[i] or colors[1]
        stroke.Thickness = 6
        stroke.Transparency = 0
        stroke.Parent = wave
        
        TweenService:Create(wave, TweenInfo.new(2, Enum.EasingStyle.Exponential), {
            Size = UDim2.new(0, 1200, 0, 1200),
            Position = UDim2.new(0.5, -600, 0.5, -600)
        }):Play()
        
        TweenService:Create(stroke, TweenInfo.new(2), {
            Transparency = 1,
            Thickness = 2
        }):Play()
        
        Debris:AddItem(wave, 2)
    end
end

-- PARTICLE EXPLOSION (TRIPLE AAA - NO UGLY SPARKLES!)
function VFXSystem:ParticleExplosion(position)
    local part = Instance.new("Part")
    part.Name = "VFXEmitter"
    part.Size = Vector3.new(1, 1, 1)
    part.Position = position
    part.Anchored = true
    part.CanCollide = false
    part.Transparency = 1
    part.Parent = workspace
    
    -- Main explosion particles (cyan/white)
    local mainParticles = Instance.new("ParticleEmitter")
    mainParticles.Enabled = false
    mainParticles.Lifetime = NumberRange.new(2, 3.5)
    mainParticles.Rate = 100
    mainParticles.SpreadAngle = Vector2.new(180, 180)
    mainParticles.Speed = NumberRange.new(25, 50)
    mainParticles.Acceleration = Vector3.new(0, -15, 0)
    mainParticles.Drag = 2
    mainParticles.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)),
        ColorSequenceKeypoint.new(0.3, Color3.fromRGB(0, 255, 255)),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(0, 150, 255))
    })
    mainParticles.Size = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 3),
        NumberSequenceKeypoint.new(0.5, 2),
        NumberSequenceKeypoint.new(1, 0)
    })
    mainParticles.Transparency = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 0),
        NumberSequenceKeypoint.new(0.8, 0.5),
        NumberSequenceKeypoint.new(1, 1)
    })
    mainParticles.LightEmission = 1
    mainParticles.LightInfluence = 0
    mainParticles.Parent = part
    
    -- Secondary smoke particles (purple/magenta)
    local smokeParticles = Instance.new("ParticleEmitter")
    smokeParticles.Enabled = false
    smokeParticles.Lifetime = NumberRange.new(2.5, 4)
    smokeParticles.Rate = 80
    smokeParticles.SpreadAngle = Vector2.new(180, 180)
    smokeParticles.Speed = NumberRange.new(15, 30)
    smokeParticles.Acceleration = Vector3.new(0, 5, 0)
    smokeParticles.Drag = 5
    smokeParticles.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 0, 255)),
        ColorSequenceKeypoint.new(0.5, Color3.fromRGB(138, 43, 226)),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(50, 20, 100))
    })
    smokeParticles.Size = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 1),
        NumberSequenceKeypoint.new(0.5, 4),
        NumberSequenceKeypoint.new(1, 6)
    })
    smokeParticles.Transparency = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 0.3),
        NumberSequenceKeypoint.new(0.5, 0.6),
        NumberSequenceKeypoint.new(1, 1)
    })
    smokeParticles.LightEmission = 0.5
    smokeParticles.Parent = part
    
    -- Glow particles (fast and bright)
    local glowParticles = Instance.new("ParticleEmitter")
    glowParticles.Enabled = false
    glowParticles.Lifetime = NumberRange.new(0.5, 1)
    glowParticles.Rate = 100
    glowParticles.SpreadAngle = Vector2.new(180, 180)
    glowParticles.Speed = NumberRange.new(40, 70)
    glowParticles.Drag = 10
    glowParticles.Color = ColorSequence.new(Color3.fromRGB(255, 255, 255))
    glowParticles.Size = NumberSequence.new(1.5, 0)
    glowParticles.Transparency = NumberSequence.new(0, 1)
    glowParticles.LightEmission = 1
    glowParticles.Parent = part
    
    -- Massive bright light
    local light = Instance.new("PointLight")
    light.Color = Color3.fromRGB(0, 255, 255)
    light.Brightness = 10
    light.Range = 60
    light.Parent = part
    
    -- Emit all particles
    mainParticles:Emit(200)
    smokeParticles:Emit(150)
    glowParticles:Emit(100)
    
    -- Fade light dramatically
    TweenService:Create(light, TweenInfo.new(2.5, Enum.EasingStyle.Exponential), {
        Brightness = 0,
        Range = 10
    }):Play()
    
    Debris:AddItem(part, 5)
end

-- ENERGY BEAMS (More beams, longer lasting)
function VFXSystem:EnergyBeams(position, count)
    for i = 1, count or 24 do
        local angle = (math.pi * 2 * i) / (count or 24)
        local direction = Vector3.new(math.cos(angle), math.random(-20, 20) / 100, math.sin(angle))
        
        local attachment0 = Instance.new("Attachment")
        local attachment1 = Instance.new("Attachment")
        
        local startPart = Instance.new("Part")
        startPart.Size = Vector3.new(0.5, 0.5, 0.5)
        startPart.Position = position
        startPart.Anchored = true
        startPart.CanCollide = false
        startPart.Transparency = 1
        startPart.Parent = workspace
        
        local distance = 40 + math.random(0, 20)
        
        local endPart = Instance.new("Part")
        endPart.Size = Vector3.new(0.5, 0.5, 0.5)
        endPart.Position = position + (direction * distance)
        endPart.Anchored = true
        endPart.CanCollide = false
        endPart.Transparency = 1
        endPart.Parent = workspace
        
        attachment0.Parent = startPart
        attachment1.Parent = endPart
        
        local colors = {
            Color3.fromRGB(0, 255, 255),
            Color3.fromRGB(255, 0, 255),
            Color3.fromRGB(255, 255, 255)
        }
        
        local beam = Instance.new("Beam")
        beam.Attachment0 = attachment0
        beam.Attachment1 = attachment1
        beam.Width0 = 3
        beam.Width1 = 0.5
        beam.Color = ColorSequence.new(colors[math.random(1, #colors)])
        beam.LightEmission = 1
        beam.LightInfluence = 0
        beam.FaceCamera = true
        beam.Transparency = NumberSequence.new(0, 1)
        beam.Parent = startPart
        
        -- Fade out beam
        task.wait(math.random() * 0.3)
        TweenService:Create(beam, TweenInfo.new(1.2), {
            Transparency = NumberSequence.new(1)
        }):Play()
        
        Debris:AddItem(startPart, 1.5)
        Debris:AddItem(endPart, 1.5)
    end
end

-- SHOCKWAVE (Multiple waves, more dramatic)
function VFXSystem:Shockwave(position)
    for wave = 1, 3 do
        task.wait(0.2)
        
        local part = Instance.new("Part")
        part.Name = "Shockwave"
        part.Size = Vector3.new(1, 0.5, 1)
        part.Position = position
        part.Anchored = true
        part.CanCollide = false
        part.Material = Enum.Material.Neon
        part.Color = wave == 1 and Color3.fromRGB(255, 255, 255) or Color3.fromRGB(0, 255, 255)
        part.Transparency = 0.3
        part.Shape = Enum.PartType.Cylinder
        part.Orientation = Vector3.new(0, 0, 90)
        part.Parent = workspace
        
        TweenService:Create(part, TweenInfo.new(1.5, Enum.EasingStyle.Exponential), {
            Size = Vector3.new(1, 60, 60),
            Transparency = 1
        }):Play()
        
        Debris:AddItem(part, 1.5)
    end
end

-- GROUND CRACK EFFECT (AAA Quality addition)
function VFXSystem:GroundCrack(position)
    local numCracks = 8
    for i = 1, numCracks do
        local angle = (math.pi * 2 * i) / numCracks
        local direction = Vector3.new(math.cos(angle), 0, math.sin(angle))
        
        local crack = Instance.new("Part")
        crack.Name = "GroundCrack"
        crack.Size = Vector3.new(2, 0.1, 15)
        crack.Position = position + Vector3.new(0, -0.5, 0)
        crack.CFrame = CFrame.new(position + Vector3.new(0, -0.5, 0), position + direction)
        crack.Anchored = true
        crack.CanCollide = false
        crack.Material = Enum.Material.Neon
        crack.Color = Color3.fromRGB(0, 255, 255)
        crack.Transparency = 0
        crack.Parent = workspace
        
        TweenService:Create(crack, TweenInfo.new(2), {
            Transparency = 1,
            Size = Vector3.new(2, 0.1, 20)
        }):Play()
        
        Debris:AddItem(crack, 2)
    end
end

-- MAIN TRIGGER FUNCTION (AAA QUALITY WITH BUILDUP)
function VFXSystem:TriggerAllEffects(targetPart)
    print("🔥 TRIPLE AAA VFX TRIGGERED!")
    
    local position = targetPart.Position
    
    -- PHASE 1: BUILDUP (1.5 seconds)
    spawn(function()
        self:BuildupAnimation(targetPart, 1.5)
    end)
    
    -- Anticipation sound
    self:PlaySound("rbxassetid://9113880795", 0.4) -- Charge up sound
    
    -- Wait for buildup
    task.wait(1.5)
    
    -- PHASE 2: EXPLOSION
    print("💥 EXPLOSION!")
    
    -- Screen effects
    self:ScreenShake(2, 2)
    self:ColorFlash(Color3.fromRGB(255, 255, 255), 1.5, 0.7)
    self:RadialBlur(2)
    
    -- GUI effects
    self:TextPopup()
    self:CircularWaves(5)
    
    -- World space effects
    spawn(function() self:ParticleExplosion(position) end)
    spawn(function() self:EnergyBeams(position, 24) end)
    spawn(function() self:Shockwave(position) end)
    spawn(function() self:GroundCrack(position) end)
    
    -- Explosion sound
    self:PlaySound("rbxassetid://9114221327", 0.6) -- Massive explosion
end

-- SOUND EFFECT
function VFXSystem:PlaySound(soundId, volume)
    local sound = Instance.new("Sound")
    sound.SoundId = soundId or "rbxassetid://9125402735"
    sound.Volume = volume or 0.5
    sound.Parent = camera
    sound:Play()
    Debris:AddItem(sound, 3)
end

-- Initialize VFX System
local vfxSystem = VFXSystem.new()

-- INTERACTION HANDLER
local currentInteractable = nil
local interactionRange = 10
local isTriggering = false

-- Create interaction UI
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
    frame.Parent = vfxSystem.screenGui
    
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
    
    -- Pulse animation
    local pulseTween = TweenService:Create(stroke, TweenInfo.new(0.8, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {
        Thickness = 5
    })
    pulseTween:Play()
    
    return frame
end

local interactionPrompt = createInteractionPrompt()

-- Find nearby interactables
RunService.RenderStepped:Connect(function()
    if not character or not humanoidRootPart or isTriggering then return end
    
    local closestPart = nil
    local closestDistance = interactionRange
    
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
    if gameProcessed or isTriggering then return end
    
    if input.KeyCode == Enum.KeyCode.E then
        if currentInteractable then
            isTriggering = true
            interactionPrompt.Visible = false
            
            -- Trigger VFX at the part's position
            vfxSystem:TriggerAllEffects(currentInteractable)
            
            -- Cooldown
            task.wait(3)
            isTriggering = false
        end
    end
end)

print("✨ TRIPLE AAA Epic VFX System Loaded!")
print("💡 Press E near objects with 'VFXInteractive' attribute")

-- Expose to global for testing
_G.TriggerVFX = function(part)
    if part then
        vfxSystem:TriggerAllEffects(part)
    else
        print("❌ Please provide a part to trigger VFX on")
    end
end
