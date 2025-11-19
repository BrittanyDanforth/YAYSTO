--[[
	POINTLIGHT FLICKER SCRIPT
	
	Place this script INSIDE the PointLight object (not as a sibling).
	The script should be: Workspace.Candle.Flame.PointLight.Script
	OR: Workspace.Part.PointLight.Script
]]

local light = script.Parent -- The script is INSIDE the PointLight, so Parent IS the PointLight

-- Validate that parent is actually a PointLight
if not light:IsA("PointLight") and not light:IsA("SpotLight") then
	warn("⚠️ Parent is not a PointLight or SpotLight! Parent type:", light.ClassName)
	return
end

-- Flickering settings
local minWait = 0.1
local maxWait = 1
local minBrightness = 1
local maxBrightness = 2

while true do
	light.Brightness = math.random(minBrightness * 10, maxBrightness * 10) / 10
	wait(math.random(minWait * 10, maxWait * 10) / 10)
end
