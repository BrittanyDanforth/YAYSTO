# 🔥 HOW TO USE THE VFX SYSTEM 🔥

## ✅ GOOD NEWS: IT'S ALREADY WORKING!

Look at your console - the server spawned test objects:
```
✨ Created Common egg at 0, 10, 0
✨ Created Rare egg at 10, 10, 0
✨ Created Epic egg at 20, 10, 0
✨ Created Legendary egg at 30, 10, 0
💎 Created Rare crystal at 0, 10, -20
💎 Created Epic crystal at 10, 10, -20
💎 Created Legendary crystal at 20, 10, -20
```

**Those eggs and crystals are floating in your game right now!**

---

## 🎮 HOW TO TRIGGER VFX:

### Method 1: Walk Up and Press E (EASIEST!)

1. **Look around** - You'll see floating eggs and crystals
2. **Walk close** to one (within 10 studs)
3. **Press E**
4. **BOOM! VFX!** 💥

---

### Method 2: Test from Console

Open console (F9) and type:

```lua
-- Test Screen VFX (works from client console):
_G.TriggerVFX("Epic")

-- Test Egg Reveal (works from client console):
_G.TestEggReveal("Epic", "Cerberage")
```

---

## ❌ WHAT YOU DID WRONG:

You tried to call:
```lua
_G.CreateInteractiveEgg(Vector3.new(0, 10, 0), "Epic", "Cerberage")
```

**From the CLIENT console!** 

That function is **SERVER-SIDE ONLY!**

### ✅ To spawn objects from console:

**Switch to SERVER console!**

1. In output, there's a dropdown that says "Client" or "Server"
2. Switch to **"Server"**
3. Then type:
```lua
_G.CreateInteractiveEgg(Vector3.new(0, 10, 0), "Epic", "Cerberage")
```

---

## 🎯 QUICK REFERENCE:

### Client Console (F9):
```lua
_G.TriggerVFX("Epic")                    -- Screen VFX
_G.TestEggReveal("Epic", "Cerberage")    -- Egg Reveal
```

### Server Console (Output → Server dropdown):
```lua
_G.CreateInteractiveEgg(Vector3.new(50, 10, 0), "Legendary", "Phoenix")
_G.CreateInteractiveCrystal(Vector3.new(60, 10, 0), "Epic", "MagicOrb")
```

---

## 🥚 WHAT ARE EGGS VS CRYSTALS?

### Eggs (Front Row):
- Use **Egg Reveal VFX** (cinematic camera!)
- Attribute: `VFXType = "Egg"`
- Shows pet name UI
- Camera moves to egg

### Crystals (Back Row):
- Use **Screen VFX** (no camera!)
- Attribute: `VFXType = "Screen"`
- Quick feedback
- No camera movement

---

## 📍 WHERE ARE THE TEST OBJECTS?

The server spawned them at:

**Eggs (Egg Reveal VFX):**
- Common egg at `(0, 10, 0)`
- Rare egg at `(10, 10, 0)`
- Epic egg at `(20, 10, 0)`
- Legendary egg at `(30, 10, 0)`

**Crystals (Screen VFX):**
- Rare crystal at `(0, 10, -20)`
- Epic crystal at `(10, 10, -20)`
- Legendary crystal at `(20, 10, -20)`

**Can't find them?** Zoom out your camera!

---

## 🔥 TL;DR - WHAT TO DO:

1. **Look around in your game** - You'll see floating eggs/crystals
2. **Walk close to one**
3. **Press E**
4. **BOOM! VFX TRIGGERS!** 💥

**That's it!** No console commands needed!

---

## 🧪 Testing Commands:

### From CLIENT Console (F9):
```lua
-- These work from client:
_G.TriggerVFX("Common")
_G.TriggerVFX("Rare")
_G.TriggerVFX("Epic")
_G.TriggerVFX("Legendary")

_G.TestEggReveal("Common", "Doggo")
_G.TestEggReveal("Rare", "Shadow Wolf")
_G.TestEggReveal("Epic", "Cerberage")
_G.TestEggReveal("Legendary", "Phoenix")
```

### From SERVER Console (Output → Server):
```lua
-- These only work from server:
_G.CreateInteractiveEgg(Vector3.new(50, 10, 0), "Epic", "Test Pet")
_G.CreateInteractiveCrystal(Vector3.new(60, 10, 0), "Rare", "Test Crystal")
```

---

## ✅ YOUR SYSTEM IS WORKING!

The console shows:
```
✅ Egg Reveal System Loaded!
✅ Screen VFX System Loaded!
✅ UNIFIED VFX SYSTEM LOADED!
```

**It's working! Just walk up to the floating objects and press E!** 🎮
