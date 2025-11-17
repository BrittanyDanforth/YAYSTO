--[[
    EGG REVEAL VFX MODULE (Orchestrator for World + Screen VFX)
    
    Usage:
        local EggRevealVFX = require(ReplicatedStorage.VFX.EggRevealVFX)
        local vfx = EggRevealVFX.new(player)
        
        vfx:Play(ReplicatedStorage.Assets.EggModel, {
            color = Color3.fromRGB(255, 230, 75),
            text = "Epic",
            tier = "Epic",
            petName = "Cerberage"
        })
]]

local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local EggRevealVFX = {}
EggRevealVFX.__index = EggRevealVFX

function EggRevealVFX.new(player)
    local self = setmetatable({}, EggRevealVFX)
    
    self.Player = player
    self.Camera = workspace.CurrentCamera
    self._busy = false
    
    -- Create GUI for text overlays
    self.Gui = Instance.new("ScreenGui")
    self.Gui.Name = "EggRevealVFX"
    self.Gui.ResetOnSpawn = false
    self.Gui.IgnoreGuiInset = true
    self.Gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    self.Gui.Parent = player:WaitForChild("PlayerGui")
    
    -- ScreenVFX will be set externally
    self.ScreenVFX = nil
    
    return self
end

-- SPAWN EGG IN WORLD
function EggRevealVFX:_spawnEgg(eggTemplate)
    local clone = eggTemplate:Clone()
    clone.Parent = workspace
    
    -- Position in front of camera
    local cam = self.Camera
    local origin = cam.CFrame.Position + cam.CFrame.LookVector * 8
    clone:PivotTo(CFrame.new(origin))
    
    return clone
end

-- EGG BUILDUP (World-space glow/particles)
function EggRevealVFX:_eggBuildup(eggModel, color)
    -- Find Aura part (creates the cracked glow!)
    local aura = eggModel:FindFirstChild("Aura")
    if aura and aura:IsA("BasePart") then
        local originalSize = aura.Size
        local originalTransparency = aura.Transparency
        
        -- Set color
        aura.Material = Enum.Material.Neon
        aura.Color = color
        aura.CanCollide = false
        aura.Anchored = true
        
        -- Get or create light
        local light = aura:FindFirstChild("PointLight")
        if not light then
            light = Instance.new("PointLight")
            light.Color = color
            light.Brightness = 2
            light.Range = 10
            light.Parent = aura
        else
            light.Color = color
        end
        
        -- Pulse the aura (makes crack glow intensify!)
        TweenService:Create(aura, TweenInfo.new(0.5, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
            Transparency = math.max(0.1, originalTransparency - 0.3),  -- More visible
            Size = originalSize * 1.1  -- Slightly bigger
        }):Play()
        
        TweenService:Create(light, TweenInfo.new(0.5), {
            Brightness = 5,
            Range = 20
        }):Play()
    end
    
    -- Start particle emitters if they exist (optional)
    local eggBase = eggModel:FindFirstChild("EggBase")
    if eggBase then
        local sparkleAttachment = eggBase:FindFirstChild("SparkleAttachment")
        if sparkleAttachment then
            for _, emitter in ipairs(sparkleAttachment:GetChildren()) do
                if emitter:IsA("ParticleEmitter") then
                    emitter.Enabled = true
                    emitter.Rate = 50
                end
            end
        end
    end
end

-- EGG EXPLOSION (World-space burst - NO RingBurst part!)
function EggRevealVFX:_eggExplosion(eggModel, color)
    -- Particle burst (if SparkleAttachment exists)
    local eggBase = eggModel:FindFirstChild("EggBase")
    if eggBase then
        local sparkleAttachment = eggBase:FindFirstChild("SparkleAttachment")
        if sparkleAttachment then
            local emitter = sparkleAttachment:FindFirstChildWhichIsA("ParticleEmitter")
            if emitter then
                emitter:Emit(100)
            end
        end
    end
    
    -- Flash the Aura (creates intense crack glow!)
    local aura = eggModel:FindFirstChild("Aura")
    if aura then
        local light = aura:FindFirstChild("PointLight")
        
        -- INTENSE FLASH for crack effect
        TweenService:Create(aura, TweenInfo.new(0.15), {
            Transparency = 0,  -- Fully visible!
            Size = aura.Size * 1.2  -- Expand slightly
        }):Play()
        
        if light then
            TweenService:Create(light, TweenInfo.new(0.15), {
                Brightness = 8,
                Range = 30
            }):Play()
        end
        
        task.wait(0.15)
        
        -- Fade out
        TweenService:Create(aura, TweenInfo.new(1), {
            Transparency = 1
        }):Play()
        
        if light then
            TweenService:Create(light, TweenInfo.new(1), {
                Brightness = 0,
                Range = 5
            }):Play()
        end
    end
end

-- SCREEN BURST (Calls ScreenVFX)
function EggRevealVFX:_screenBurst(rarityConfig)
    if self.ScreenVFX then
        self.ScreenVFX:TriggerVFX(rarityConfig.tier or "Epic")
    end
end

-- SHOW NAME/RARITY TEXT
function EggRevealVFX:_showNameLabel(rarityConfig)
    -- Pet name
    local nameLabel = Instance.new("TextLabel")
    nameLabel.Size = UDim2.new(0, 600, 0, 120)
    nameLabel.Position = UDim2.new(0.5, -300, 0.7, -60)
    nameLabel.AnchorPoint = Vector2.new(0, 0)
    nameLabel.BackgroundTransparency = 1
    nameLabel.ZIndex = 10005
    nameLabel.Font = Enum.Font.FredokaOne
    nameLabel.TextSize = 64
    nameLabel.Text = rarityConfig.petName or "Epic Pet"
    nameLabel.TextColor3 = Color3.new(1, 1, 1)
    nameLabel.TextStrokeTransparency = 0
    nameLabel.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
    nameLabel.TextTransparency = 1
    nameLabel.TextStrokeTransparency = 1
    nameLabel.Parent = self.Gui
    
    -- Rarity text
    local rarityLabel = Instance.new("TextLabel")
    rarityLabel.Size = UDim2.new(0, 600, 0, 60)
    rarityLabel.Position = UDim2.new(0.5, -300, 0.7, 60)
    rarityLabel.BackgroundTransparency = 1
    rarityLabel.ZIndex = 10005
    rarityLabel.Font = Enum.Font.FredokaOne
    rarityLabel.TextSize = 40
    rarityLabel.Text = rarityConfig.text or "Epic"
    rarityLabel.TextColor3 = rarityConfig.color
    rarityLabel.TextStrokeTransparency = 0
    rarityLabel.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
    rarityLabel.TextTransparency = 1
    rarityLabel.TextStrokeTransparency = 1
    rarityLabel.Parent = self.Gui
    
    -- Fade in
    TweenService:Create(nameLabel, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
        TextTransparency = 0,
        TextStrokeTransparency = 0
    }):Play()
    
    TweenService:Create(rarityLabel, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
        TextTransparency = 0,
        TextStrokeTransparency = 0
    }):Play()
    
    -- Fade out
    task.delay(2.5, function()
        TweenService:Create(nameLabel, TweenInfo.new(0.4), {
            TextTransparency = 1,
            TextStrokeTransparency = 1
        }):Play()
        
        TweenService:Create(rarityLabel, TweenInfo.new(0.4), {
            TextTransparency = 1,
            TextStrokeTransparency = 1
        }):Play()
        
        Debris:AddItem(nameLabel, 1)
        Debris:AddItem(rarityLabel, 1)
    end)
end

-- FULL SEQUENCE
function EggRevealVFX:_playSequence(eggTemplate, rarityConfig)
    local egg = self:_spawnEgg(eggTemplate)
    
    -- BUILDUP (0.6s)
    self:_eggBuildup(egg, rarityConfig.color)
    if self.ScreenVFX then
        task.spawn(function()
            self.ScreenVFX:BuildupAnimation(rarityConfig.color, 0.6)
        end)
    end
    task.wait(0.6)
    
    -- EXPLOSION (world + screen)
    self:_eggExplosion(egg, rarityConfig.color)
    self:_screenBurst(rarityConfig)
    
    -- Show name/rarity
    self:_showNameLabel(rarityConfig)
    
    -- Hold then cleanup
    task.wait(3)
    egg:Destroy()
end

-- PUBLIC API
function EggRevealVFX:Play(eggTemplate, rarityConfig)
    if self._busy then
        warn("EggRevealVFX is busy!")
        return
    end
    
    self._busy = true
    
    rarityConfig = rarityConfig or {
        color = Color3.fromRGB(0, 255, 255),
        text = "Epic",
        tier = "Epic",
        petName = "Mystery Pet"
    }
    
    task.spawn(function()
        self:_playSequence(eggTemplate, rarityConfig)
        self._busy = false
    end)
end

return EggRevealVFX
