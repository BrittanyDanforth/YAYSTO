--[[
    ROBLOX VFX - SERVER SCRIPT (OPTIONAL)
    
    This handles server-side interactions and replicates effects to all players
    
    INSTALLATION:
    Put this in ServerScriptService
--]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")

-- Create RemoteEvent for VFX replication
local vfxEvent = Instance.new("RemoteEvent")
vfxEvent.Name = "VFXTriggerEvent"
vfxEvent.Parent = ReplicatedStorage

-- Server-side interaction handler
vfxEvent.OnServerEvent:Connect(function(player, position, effectType)
    print(player.Name .. " triggered VFX at " .. tostring(position))
    
    -- Replicate to all other players
    for _, otherPlayer in pairs(game.Players:GetPlayers()) do
        if otherPlayer ~= player then
            vfxEvent:FireClient(otherPlayer, position, effectType)
        end
    end
    
    -- Optional: Add server-side logic here
    -- Example: Give points, unlock door, spawn item, etc.
end)

-- Example: Create interactive objects in workspace
local function createInteractiveObject(position, name)
    local part = Instance.new("Part")
    part.Name = name
    part.Size = Vector3.new(4, 4, 4)
    part.Position = position
    part.Anchored = true
    part.BrickColor = BrickColor.new("Cyan")
    part.Material = Enum.Material.Neon
    part.Shape = Enum.PartType.Ball
    part.Parent = workspace
    
    -- Make it interactive
    part:SetAttribute("VFXInteractive", true)
    
    -- Add glow
    local pointLight = Instance.new("PointLight")
    pointLight.Color = Color3.fromRGB(0, 255, 255)
    pointLight.Brightness = 2
    pointLight.Range = 20
    pointLight.Parent = part
    
    -- Add spinning animation
    local spin = Instance.new("BodyAngularVelocity")
    spin.AngularVelocity = Vector3.new(0, 2, 0)
    spin.MaxTorque = Vector3.new(0, math.huge, 0)
    spin.Parent = part
    
    -- Add interaction event
    local interactEvent = Instance.new("RemoteEvent")
    interactEvent.Name = "InteractEvent"
    interactEvent.Parent = part
    
    interactEvent.OnServerEvent:Connect(function(player)
        print(player.Name .. " interacted with " .. name)
        -- Add your custom logic here!
    end)
    
    return part
end

-- Example: Spawn some interactive objects
-- Uncomment these to auto-create interactive objects in your game
--[[
createInteractiveObject(Vector3.new(0, 10, 0), "EpicCrystal1")
createInteractiveObject(Vector3.new(20, 10, 0), "EpicCrystal2")
createInteractiveObject(Vector3.new(-20, 10, 0), "EpicCrystal3")
--]]

print("✨ VFX Server Script Loaded!")
