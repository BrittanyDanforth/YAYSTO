# QUICK FIX INSTRUCTIONS

## 🔴 CRITICAL: Clear Roblox Studio Cache

The DialogueMemory error is likely due to **cached files**. Do this:

1. **Close Roblox Studio completely**
2. **Delete cache folder:**
   - Windows: `%LOCALAPPDATA%\Roblox\Cache`
   - Mac: `~/Library/Caches/com.roblox.roblox`
3. **Reopen Studio**
4. **Re-insert DialogueMemory module** (delete old one, insert new one from GitHub)

## 🔧 Fix PointLight Script Error

**Error:** `PointLight is not a valid member of PointLight`

**Current script location:** `Workspace.Part.PointLight.Script`

**Problem:** Script is trying to access `script.Parent.PointLight` but the script IS inside the PointLight.

**Fix:** Replace the script code with this:

```lua
-- Place this script INSIDE the PointLight object
local light = script.Parent -- The script IS inside PointLight, so Parent IS the PointLight

-- Validate
if not light:IsA("PointLight") and not light:IsA("SpotLight") then
	warn("Parent is not a Light object!")
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
```

**Structure should be:**
```
Workspace
└─ Part
    └─ PointLight (the Light object)
        └─ Script (your script goes HERE, inside PointLight)
```

## ✅ Verification Checklist

After fixes:
1. ✅ Clear Studio cache
2. ✅ Re-insert DialogueMemory module
3. ✅ Fix PointLight script (use `script.Parent` not `script.Parent.PointLight`)
4. ✅ RemoteEvents created (already done)
5. ✅ Test in Studio

## 🎯 If Errors Persist

1. **Delete the DialogueMemory module** from ReplicatedStorage
2. **Download fresh copy** from GitHub
3. **Insert as ModuleScript** named "DialogueMemory"
4. **Test again**

The file has been completely rewritten and should work now!
