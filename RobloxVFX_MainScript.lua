--[[
    TRIPLE AAA SCREEN-BASED VFX SYSTEM
    Press E on interactive objects for INSANE screen effects!
    
    RARITY TIERS:
    - Common: Basic effects
    - Rare: Medium effects
    - Epic: INSANE effects
    
    INSTALLATION:
    1. Put this in StarterPlayer > StarterPlayerScripts as a LocalScript
    2. Add attributes to parts:
       - VFXInteractive (Boolean = true)
       - VFXRarity (String = "Common", "Rare", or "Epic")
--]]

local Players = game:GetService("Players")
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
    self.screenGui = self:CreateScreenGui()
    self.isTriggering = false
    return self
end

function VFXSystem:CreateScreenGui()
    local screenGui = Instance.new("ScreenGui")
    screenGui.Name = "EpicVFXGui"
    screenGui.ResetOnSpawn = false
    screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    screenGui.IgnoreGuiInset = true
    screenGui.Parent = player.PlayerGui
    return screenGui
end

-- RARITY CONFIGS
local RarityConfig = {
    Common = {
        color = Color3.fromRGB(200, 200, 200), -- Gray
        particleCount = 30,
        ringCount = 2,
        beamCount = 8,
        shakeIntensity = 0.5,
        flashIntensity = 0.3,
        blurSize = 15,
        duration = 1.5,
        text = "NICE!",
        buildupTime = 0.5
    },
    Rare = {
        color = Color3.fromRGB(0, 150, 255), -- Blue
        particleCount = 80,
        ringCount = 4,
        beamCount = 16,
        shakeIntensity = 1.5,
        flashIntensity = 0.5,
        blurSize = 30,
        duration = 2.5,
        text = "RARE!",
        buildupTime = 1.0
    },
    Epic = {
        color = Color3.fromRGB(255, 0, 255), -- Purple/Magenta
        particleCount = 150,
        ringCount = 6,
        beamCount = 32,
        shakeIntensity = 3,
        flashIntensity = 0.7,
        blurSize = 50,
        duration = 3.5,
        text = "LEGENDARY!",
        buildupTime = 1.5
    }
}

-- SCREEN SHAKE
function VFXSystem:ScreenShake(intensity, duration)
    spawn(function()
        local elapsed = 0
        local connection
        connection = RunService.RenderStepped:Connect(function(dt)
            elapsed = elapsed + dt
            if elapsed >= duration then
                connection:Disconnect()
                return
            end
            
            local progress = elapsed / duration
            local currentIntensity = intensity * (1 - progress)
            
            local shake = CFrame.new(
                math.random(-100, 100) / 100 * currentIntensity,
                math.random(-100, 100) / 100 * currentIntensity,
                math.random(-100, 100) / 100 * currentIntensity
            )
            
            camera.CFrame = camera.CFrame * shake
        end)
    end)
end

-- COLOR FLASH (SCREEN SPACE)
function VFXSystem:ColorFlash(color, duration, intensity)
    local flash = Instance.new("Frame")
    flash.Name = "ColorFlash"
    flash.Size = UDim2.new(1, 0, 1, 0)
    flash.Position = UDim2.new(0, 0, 0, 0)
    flash.BackgroundColor3 = color
    flash.BackgroundTransparency = 1 - intensity
    flash.BorderSizePixel = 0
    flash.ZIndex = 10000
    flash.Parent = self.screenGui
    
    local gradient = Instance.new("UIGradient")
    gradient.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)),
        ColorSequenceKeypoint.new(0.5, color),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 255, 255))
    })
    gradient.Rotation = 45
    gradient.Parent = flash
    
    TweenService:Create(flash, TweenInfo.new(duration, Enum.EasingStyle.Exponential), {
        BackgroundTransparency = 1
    }):Play()
    
    Debris:AddItem(flash, duration + 0.1)
end

-- RADIAL BLUR
function VFXSystem:RadialBlur(maxSize, duration)
    local blur = Instance.new("BlurEffect")
    blur.Size = 0
    blur.Parent = camera
    
    local tweenIn = TweenService:Create(blur, TweenInfo.new(0.1), {Size = maxSize})
    local tweenOut = TweenService:Create(blur, TweenInfo.new(duration), {Size = 0})
    
    tweenIn:Play()
    tweenIn.Completed:Connect(function()
        tweenOut:Play()
    end)
    
    tweenOut.Completed:Connect(function()
        blur:Destroy()
    end)
end

-- SCREEN PARTICLES (GUI-based)
function VFXSystem:ScreenParticles(color, count, duration)
    local centerX = 0.5
    local centerY = 0.5
    
    for i = 1, count do
        local particle = Instance.new("Frame")
        particle.Name = "Particle"
        particle.Size = UDim2.new(0, math.random(3, 10), 0, math.random(3, 10))
        particle.Position = UDim2.new(centerX, 0, centerY, 0)
        particle.BackgroundColor3 = color
        particle.BorderSizePixel = 0
        particle.ZIndex = 9900 + i
        particle.Parent = self.screenGui
        
        -- Glow effect
        local glow = Instance.new("UIStroke")
        glow.Color = color
        glow.Thickness = 2
        glow.Transparency = 0
        glow.Parent = particle
        
        local corner = Instance.new("UICorner")
        corner.CornerRadius = UDim.new(1, 0)
        corner.Parent = particle
        
        -- Random direction
        local angle = math.rad(math.random(0, 360))
        local distance = math.random(200, 600)
        local targetX = centerX + (math.cos(angle) * distance) / (camera.ViewportSize.X)
        local targetY = centerY + (math.sin(angle) * distance) / (camera.ViewportSize.Y)
        
        -- Gravity effect
        targetY = targetY + math.random(100, 300) / camera.ViewportSize.Y
        
        -- Animate
        task.wait(math.random() * 0.3)
        
        TweenService:Create(particle, TweenInfo.new(duration, Enum.EasingStyle.Exponential), {
            Position = UDim2.new(targetX, 0, targetY, 0),
            Size = UDim2.new(0, 0, 0, 0),
            BackgroundTransparency = 1
        }):Play()
        
        TweenService:Create(glow, TweenInfo.new(duration), {
            Transparency = 1
        }):Play()
        
        Debris:AddItem(particle, duration + 0.5)
    end
end

-- SCREEN BEAMS (Radiating lines from center)
function VFXSystem:ScreenBeams(color, count, duration)
    for i = 1, count do
        local angle = (360 / count) * i
        
        local beam = Instance.new("Frame")
        beam.Name = "Beam"
        beam.Size = UDim2.new(0, 0, 0, 3)
        beam.Position = UDim2.new(0.5, 0, 0.5, 0)
        beam.AnchorPoint = Vector2.new(0, 0.5)
        beam.BackgroundColor3 = color
        beam.BorderSizePixel = 0
        beam.ZIndex = 9800
        beam.Rotation = angle
        beam.Parent = self.screenGui
        
        local glow = Instance.new("UIStroke")
        glow.Color = color
        glow.Thickness = 3
        glow.Transparency = 0
        glow.Parent = beam
        
        local gradient = Instance.new("UIGradient")
        gradient.Transparency = NumberSequence.new({
            NumberSequenceKeypoint.new(0, 0),
            NumberSequenceKeypoint.new(1, 1)
        })
        gradient.Parent = beam
        
        -- Animate
        task.wait(math.random() * 0.2)
        
        TweenService:Create(beam, TweenInfo.new(0.5), {
            Size = UDim2.new(0.7, 0, 0, 3)
        }):Play()
        
        task.wait(0.5)
        
        TweenService:Create(beam, TweenInfo.new(duration - 0.5), {
            BackgroundTransparency = 1
        }):Play()
        
        TweenService:Create(glow, TweenInfo.new(duration - 0.5), {
            Transparency = 1
        }):Play()
        
        Debris:AddItem(beam, duration + 0.1)
    end
end

-- CIRCULAR WAVES (Screen space)
function VFXSystem:CircularWaves(color, count, duration)
    for i = 1, count do
        task.wait(0.2)
        
        local wave = Instance.new("Frame")
        wave.Name = "CircularWave"
        wave.Size = UDim2.new(0, 50, 0, 50)
        wave.Position = UDim2.new(0.5, -25, 0.5, -25)
        wave.BackgroundTransparency = 1
        wave.ZIndex = 9990 + i
        wave.Parent = self.screenGui
        
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

-- TEXT POPUP (Screen space)
function VFXSystem:TextPopup(text, color, duration)
    local textLabel = Instance.new("TextLabel")
    textLabel.Name = "TextPopup"
    textLabel.Text = text
    textLabel.Font = Enum.Font.GothamBold
    textLabel.TextSize = 120
    textLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
    textLabel.TextStrokeTransparency = 0
    textLabel.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
    textLabel.BackgroundTransparency = 1
    textLabel.Size = UDim2.new(0, 800, 0, 200)
    textLabel.Position = UDim2.new(0.5, -400, 0.5, -100)
    textLabel.TextTransparency = 1
    textLabel.TextStrokeTransparency = 1
    textLabel.ZIndex = 10001
    textLabel.Parent = self.screenGui
    
    local uiStroke = Instance.new("UIStroke")
    uiStroke.Color = color
    uiStroke.Thickness = 8
    uiStroke.Transparency = 1
    uiStroke.Parent = textLabel
    
    local gradient = Instance.new("UIGradient")
    gradient.Color = ColorSequence.new({
        ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)),
        ColorSequenceKeypoint.new(0.5, color),
        ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 255, 255))
    })
    gradient.Rotation = 45
    gradient.Parent = textLabel
    
    -- Pop in
    TweenService:Create(textLabel, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
        TextTransparency = 0,
        TextStrokeTransparency = 0,
        TextSize = 140
    }):Play()
    
    TweenService:Create(uiStroke, TweenInfo.new(0.3), {
        Transparency = 0
    }):Play()
    
    task.wait(0.5)
    
    -- Float up and fade
    TweenService:Create(textLabel, TweenInfo.new(duration - 0.8, Enum.EasingStyle.Exponential), {
        Position = UDim2.new(0.5, -400, 0.1, -100),
        TextTransparency = 1,
        TextStrokeTransparency = 1
    }):Play()
    
    TweenService:Create(uiStroke, TweenInfo.new(duration - 0.8), {
        Transparency = 1
    }):Play()
    
    Debris:AddItem(textLabel, duration + 0.1)
end

-- VIGNETTE PULSE
function VFXSystem:VignettePulse(color, duration)
    local vignette = Instance.new("Frame")
    vignette.Name = "Vignette"
    vignette.Size = UDim2.new(1, 0, 1, 0)
    vignette.Position = UDim2.new(0, 0, 0, 0)
    vignette.BackgroundTransparency = 1
    vignette.BorderSizePixel = 0
    vignette.ZIndex = 9700
    vignette.Parent = self.screenGui
    
    local gradient = Instance.new("UIGradient")
    gradient.Color = ColorSequence.new(color)
    gradient.Transparency = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 1),
        NumberSequenceKeypoint.new(0.7, 0.5),
        NumberSequenceKeypoint.new(1, 0)
    })
    gradient.Rotation = 90
    gradient.Parent = vignette
    
    vignette.BackgroundColor3 = color
    vignette.BackgroundTransparency = 1
    
    -- Pulse in and out
    local tween = TweenService:Create(vignette, TweenInfo.new(duration, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
        BackgroundTransparency = 0.3
    })
    tween:Play()
    
    tween.Completed:Connect(function()
        TweenService:Create(vignette, TweenInfo.new(duration * 0.5), {
            BackgroundTransparency = 1
        }):Play()
    end)
    
    Debris:AddItem(vignette, duration * 1.5 + 0.1)
end

-- BUILDUP ANIMATION (Screen space)
function VFXSystem:BuildupAnimation(color, duration)
    -- Pulsing circle at center
    local buildupCircle = Instance.new("Frame")
    buildupCircle.Name = "BuildupCircle"
    buildupCircle.Size = UDim2.new(0, 100, 0, 100)
    buildupCircle.Position = UDim2.new(0.5, -50, 0.5, -50)
    buildupCircle.BackgroundTransparency = 0.5
    buildupCircle.BackgroundColor3 = color
    buildupCircle.BorderSizePixel = 0
    buildupCircle.ZIndex = 10002
    buildupCircle.Parent = self.screenGui
    
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(1, 0)
    corner.Parent = buildupCircle
    
    local stroke = Instance.new("UIStroke")
    stroke.Color = color
    stroke.Thickness = 4
    stroke.Transparency = 0
    stroke.Parent = buildupCircle
    
    -- Pulse animation
    local pulseTween = TweenService:Create(buildupCircle, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
        Size = UDim2.new(0, 150, 0, 150),
        Position = UDim2.new(0.5, -75, 0.5, -75),
        BackgroundTransparency = 0.2
    })
    
    local shrinkTween = TweenService:Create(buildupCircle, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
        Size = UDim2.new(0, 100, 0, 100),
        Position = UDim2.new(0.5, -50, 0.5, -50),
        BackgroundTransparency = 0.5
    })
    
    -- Loop pulse
    local pulseCount = 0
    local maxPulses = math.floor(duration / 0.6)
    
    pulseTween.Completed:Connect(function()
        pulseCount = pulseCount + 1
        if pulseCount < maxPulses then
            shrinkTween:Play()
        end
    end)
    
    shrinkTween.Completed:Connect(function()
        if pulseCount < maxPulses then
            pulseTween:Play()
        end
    end)
    
    pulseTween:Play()
    
    -- Cleanup
    task.wait(duration)
    buildupCircle:Destroy()
end

-- MAIN TRIGGER FUNCTION
function VFXSystem:TriggerVFX(rarity)
    if self.isTriggering then return end
    self.isTriggering = true
    
    local config = RarityConfig[rarity] or RarityConfig.Common
    print("🔥 VFX TRIGGERED - RARITY:", rarity)
    
    -- PHASE 1: BUILDUP
    spawn(function()
        self:BuildupAnimation(config.color, config.buildupTime)
    end)
    
    self:PlaySound("rbxassetid://9113880795", 0.3)
    
    task.wait(config.buildupTime)
    
    -- PHASE 2: EXPLOSION (ALL SCREEN BASED!)
    print("💥 EXPLOSION!")
    
    -- Screen effects
    self:ScreenShake(config.shakeIntensity, config.duration)
    self:ColorFlash(config.color, config.duration * 0.6, config.flashIntensity)
    self:RadialBlur(config.blurSize, config.duration)
    self:VignettePulse(config.color, config.duration * 0.4)
    
    -- Visual effects
    spawn(function() self:ScreenParticles(config.color, config.particleCount, config.duration) end)
    spawn(function() self:ScreenBeams(config.color, config.beamCount, config.duration * 0.8) end)
    spawn(function() self:CircularWaves(config.color, config.ringCount, config.duration) end)
    spawn(function() self:TextPopup(config.text, config.color, config.duration) end)
    
    -- Explosion sound
    self:PlaySound("rbxassetid://9114221327", 0.5)
    
    -- Reset after total duration
    task.wait(config.buildupTime + config.duration + 0.5)
    self.isTriggering = false
end

-- SOUND EFFECT
function VFXSystem:PlaySound(soundId, volume)
    local sound = Instance.new("Sound")
    sound.SoundId = soundId
    sound.Volume = volume
    sound.Parent = camera
    sound:Play()
    Debris:AddItem(sound, 3)
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
    
    return frame
end

local interactionPrompt = createInteractionPrompt()

-- Find nearby interactables
RunService.RenderStepped:Connect(function()
    if not character or not humanoidRootPart or vfxSystem.isTriggering then return end
    
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
    
    -- Update prompt color based on rarity
    if currentInteractable then
        local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
        local config = RarityConfig[rarity] or RarityConfig.Common
        interactionPrompt:FindFirstChildOfClass("UIStroke").Color = config.color
        interactionPrompt:FindFirstChildOfClass("TextLabel").TextColor3 = config.color
    end
end)

-- Handle E key press
UserInputService.InputBegan:Connect(function(input, gameProcessed)
    if gameProcessed or vfxSystem.isTriggering then return end
    
    if input.KeyCode == Enum.KeyCode.E then
        if currentInteractable then
            interactionPrompt.Visible = false
            
            -- Get rarity from attribute
            local rarity = currentInteractable:GetAttribute("VFXRarity") or "Common"
            
            -- Trigger VFX
            vfxSystem:TriggerVFX(rarity)
        end
    end
end)

print("✨ TRIPLE AAA Screen VFX System Loaded!")
print("💡 Add attributes to parts:")
print("   - VFXInteractive (Boolean = true)")
print("   - VFXRarity (String = 'Common', 'Rare', or 'Epic')")

-- Expose to global for testing
_G.TriggerVFX = function(rarity)
    vfxSystem:TriggerVFX(rarity or "Epic")
end
