--[[
    SCREEN VFX MODULE (Modular, Clean, Optimized)
    
    Usage:
        local ScreenVFX = require(script.ScreenVFX)
        local vfx = ScreenVFX.new(player)
        vfx:TriggerVFX("Epic")
]]

local TweenService = game:GetService("TweenService")
local RunService = game:GetService("RunService")
local Debris = game:GetService("Debris")

local ScreenVFX = {}
ScreenVFX.__index = ScreenVFX

-- RARITY CONFIGS
local RarityConfig = {
    Common = {
        color = Color3.fromRGB(200, 200, 200),
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
        color = Color3.fromRGB(0, 150, 255),
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
        color = Color3.fromRGB(255, 0, 255),
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

function ScreenVFX.new(player)
    local self = setmetatable({}, ScreenVFX)
    
    self.Player = player
    self.Camera = workspace.CurrentCamera
    self.isTriggering = false
    
    -- Create ScreenGui
    self.ScreenGui = Instance.new("ScreenGui")
    self.ScreenGui.Name = "ScreenVFX"
    self.ScreenGui.ResetOnSpawn = false
    self.ScreenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    self.ScreenGui.IgnoreGuiInset = true
    self.ScreenGui.Parent = player:WaitForChild("PlayerGui")
    
    return self
end

-- SCREEN SHAKE (FIXED - No drift!)
function ScreenVFX:ScreenShake(intensity, duration)
    task.spawn(function()
        local baseCFrame = self.Camera.CFrame
        local elapsed = 0
        
        local conn
        conn = RunService.RenderStepped:Connect(function(dt)
            elapsed = elapsed + dt
            
            if elapsed >= duration then
                self.Camera.CFrame = baseCFrame
                conn:Disconnect()
                return
            end
            
            -- Decay over time
            local t = 1 - (elapsed / duration)
            local power = intensity * t
            
            local dx = (math.random() - 0.5) * 2 * power
            local dy = (math.random() - 0.5) * 2 * power
            local dz = (math.random() - 0.5) * 0.5 * power
            
            self.Camera.CFrame = baseCFrame * CFrame.new(dx, dy, dz)
        end)
    end)
end

-- COLOR FLASH
function ScreenVFX:ColorFlash(color, duration, intensity)
    local flash = Instance.new("Frame")
    flash.Name = "ColorFlash"
    flash.Size = UDim2.new(1, 0, 1, 0)
    flash.BackgroundColor3 = color
    flash.BackgroundTransparency = 1 - intensity
    flash.BorderSizePixel = 0
    flash.ZIndex = 10000
    flash.Parent = self.ScreenGui
    
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

-- RADIAL BLUR + POST-PROCESSING
function ScreenVFX:RadialBlur(maxSize, duration)
    local blur = Instance.new("BlurEffect")
    blur.Size = 0
    blur.Parent = self.Camera
    
    -- Add bloom for that glow
    local bloom = Instance.new("BloomEffect")
    bloom.Intensity = 0
    bloom.Size = 24
    bloom.Threshold = 0.8
    bloom.Parent = self.Camera
    
    -- Color correction for tint
    local colorCorrect = Instance.new("ColorCorrectionEffect")
    colorCorrect.Brightness = 0
    colorCorrect.Saturation = 0
    colorCorrect.TintColor = Color3.fromRGB(255, 255, 255)
    colorCorrect.Parent = self.Camera
    
    -- Tween in
    local tweenIn = TweenService:Create(blur, TweenInfo.new(0.2), {Size = maxSize})
    local bloomIn = TweenService:Create(bloom, TweenInfo.new(0.2), {Intensity = 0.5})
    local colorIn = TweenService:Create(colorCorrect, TweenInfo.new(0.2), {
        Brightness = 0.1,
        Saturation = 0.2
    })
    
    tweenIn:Play()
    bloomIn:Play()
    colorIn:Play()
    
    -- Tween out
    task.wait(0.2)
    
    local tweenOut = TweenService:Create(blur, TweenInfo.new(duration), {Size = 0})
    local bloomOut = TweenService:Create(bloom, TweenInfo.new(duration), {Intensity = 0})
    local colorOut = TweenService:Create(colorCorrect, TweenInfo.new(duration), {
        Brightness = 0,
        Saturation = 0
    })
    
    tweenOut:Play()
    bloomOut:Play()
    colorOut:Play()
    
    tweenOut.Completed:Connect(function()
        blur:Destroy()
        bloom:Destroy()
        colorCorrect:Destroy()
    end)
end

-- SCREEN PARTICLES
function ScreenVFX:ScreenParticles(color, count, duration)
    local center = UDim2.fromScale(0.5, 0.5)
    
    for i = 1, count do
        local particle = Instance.new("Frame")
        particle.Name = "Particle"
        particle.Size = UDim2.new(0, math.random(3, 10), 0, math.random(3, 10))
        particle.Position = center
        particle.BackgroundColor3 = color
        particle.BorderSizePixel = 0
        particle.ZIndex = 9900 + i
        particle.Parent = self.ScreenGui
        
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
        local targetX = 0.5 + (math.cos(angle) * distance) / self.Camera.ViewportSize.X
        local targetY = 0.5 + (math.sin(angle) * distance) / self.Camera.ViewportSize.Y + math.random(100, 300) / self.Camera.ViewportSize.Y
        
        -- Animate
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
    end
end

-- SCREEN BEAMS (FIXED - Proper pivot and rotation!)
function ScreenVFX:ScreenBeams(color, count, duration)
    local center = UDim2.fromScale(0.5, 0.5)
    local maxLen = math.max(self.Camera.ViewportSize.X, self.Camera.ViewportSize.Y) * 0.8
    
    for i = 1, count do
        local angle = (i - 1) * (360 / count)
        
        local beam = Instance.new("Frame")
        beam.Name = "Beam"
        beam.AnchorPoint = Vector2.new(0.5, 1) -- Bottom pivot - KEY FIX!
        beam.Position = center
        beam.Size = UDim2.new(0, 4, 0, 0) -- Start at 0 height
        beam.BackgroundColor3 = color
        beam.BorderSizePixel = 0
        beam.Rotation = angle
        beam.ZIndex = 9800
        beam.Parent = self.ScreenGui
        
        local stroke = Instance.new("UIStroke")
        stroke.Color = color
        stroke.Thickness = 4
        stroke.Transparency = 0
        stroke.Parent = beam
        
        local gradient = Instance.new("UIGradient")
        gradient.Transparency = NumberSequence.new{
            NumberSequenceKeypoint.new(0, 0),
            NumberSequenceKeypoint.new(1, 1)
        }
        gradient.Rotation = 90
        gradient.Parent = beam
        
        task.delay(0.02 * i, function()
            local growTime = math.min(0.4, duration * 0.4)
            local fadeTime = math.max(0.1, duration - growTime)
            
            TweenService:Create(beam, TweenInfo.new(growTime, Enum.EasingStyle.Quint, Enum.EasingDirection.Out), {
                Size = UDim2.new(0, 4, 0, maxLen)
            }):Play()
            
            task.delay(growTime, function()
                TweenService:Create(beam, TweenInfo.new(fadeTime), {
                    BackgroundTransparency = 1
                }):Play()
                TweenService:Create(stroke, TweenInfo.new(fadeTime), {
                    Transparency = 1
                }):Play()
            end)
            
            Debris:AddItem(beam, duration + 0.5)
        end)
    end
end

-- CIRCULAR WAVES
function ScreenVFX:CircularWaves(color, count, duration)
    for i = 1, count do
        task.wait(0.2)
        
        local wave = Instance.new("Frame")
        wave.Name = "CircularWave"
        wave.Size = UDim2.new(0, 50, 0, 50)
        wave.Position = UDim2.fromScale(0.5, 0.5)
        wave.AnchorPoint = Vector2.new(0.5, 0.5)
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
            Size = UDim2.new(0, 1500, 0, 1500)
        }):Play()
        
        TweenService:Create(stroke, TweenInfo.new(duration), {
            Transparency = 1
        }):Play()
        
        Debris:AddItem(wave, duration + 0.1)
    end
end

-- TEXT POPUP
function ScreenVFX:TextPopup(text, color, duration)
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
    textLabel.Parent = self.ScreenGui
    
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
function ScreenVFX:VignettePulse(color, duration)
    local vignette = Instance.new("Frame")
    vignette.Name = "Vignette"
    vignette.Size = UDim2.new(1, 0, 1, 0)
    vignette.BackgroundTransparency = 1
    vignette.BorderSizePixel = 0
    vignette.ZIndex = 9700
    vignette.Parent = self.ScreenGui
    
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
    
    TweenService:Create(vignette, TweenInfo.new(duration, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
        BackgroundTransparency = 0.3
    }):Play()
    
    task.wait(duration)
    
    TweenService:Create(vignette, TweenInfo.new(duration * 0.5), {
        BackgroundTransparency = 1
    }):Play()
    
    Debris:AddItem(vignette, duration * 1.5 + 0.1)
end

-- BUILDUP ANIMATION
function ScreenVFX:BuildupAnimation(color, duration)
    local buildupCircle = Instance.new("Frame")
    buildupCircle.Name = "BuildupCircle"
    buildupCircle.Size = UDim2.new(0, 100, 0, 100)
    buildupCircle.Position = UDim2.fromScale(0.5, 0.5)
    buildupCircle.AnchorPoint = Vector2.new(0.5, 0.5)
    buildupCircle.BackgroundTransparency = 0.5
    buildupCircle.BackgroundColor3 = color
    buildupCircle.BorderSizePixel = 0
    buildupCircle.ZIndex = 10002
    buildupCircle.Parent = self.ScreenGui
    
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(1, 0)
    corner.Parent = buildupCircle
    
    local stroke = Instance.new("UIStroke")
    stroke.Color = color
    stroke.Thickness = 4
    stroke.Transparency = 0
    stroke.Parent = buildupCircle
    
    -- Pulse loop with finite count
    local pulses = math.floor(duration / 0.6)
    
    for i = 1, pulses do
        TweenService:Create(buildupCircle, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.Out), {
            Size = UDim2.new(0, 150, 0, 150),
            BackgroundTransparency = 0.2
        }):Play()
        
        task.wait(0.3)
        
        if i < pulses then
            TweenService:Create(buildupCircle, TweenInfo.new(0.3, Enum.EasingStyle.Sine, Enum.EasingDirection.In), {
                Size = UDim2.new(0, 100, 0, 100),
                BackgroundTransparency = 0.5
            }):Play()
            
            task.wait(0.3)
        end
    end
    
    buildupCircle:Destroy()
end

-- MAIN TRIGGER
function ScreenVFX:TriggerVFX(rarity)
    if self.isTriggering then return end
    self.isTriggering = true
    
    local config = RarityConfig[rarity] or RarityConfig.Common
    print("🔥 VFX TRIGGERED - RARITY:", rarity)
    
    -- PHASE 1: BUILDUP
    task.spawn(function()
        self:BuildupAnimation(config.color, config.buildupTime)
    end)
    
    task.wait(config.buildupTime)
    
    -- PHASE 2: EXPLOSION
    print("💥 EXPLOSION!")
    
    self:ScreenShake(config.shakeIntensity, config.duration)
    self:ColorFlash(config.color, config.duration * 0.6, config.flashIntensity)
    self:RadialBlur(config.blurSize, config.duration)
    self:VignettePulse(config.color, config.duration * 0.4)
    
    task.spawn(function() self:ScreenParticles(config.color, config.particleCount, config.duration) end)
    task.spawn(function() self:ScreenBeams(config.color, config.beamCount, config.duration * 0.8) end)
    task.spawn(function() self:CircularWaves(config.color, config.ringCount, config.duration) end)
    task.spawn(function() self:TextPopup(config.text, config.color, config.duration) end)
    
    -- Reset
    task.wait(config.buildupTime + config.duration + 0.5)
    self.isTriggering = false
end

return ScreenVFX
