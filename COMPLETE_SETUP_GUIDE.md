# 🎮 COMPLETE ROBLOX VFX SYSTEM - SETUP GUIDE

## 📦 What You Get

This project includes **TWO separate VFX systems**:

1. **🥚 Egg Reveal System** - Cinematic egg hatching with camera control
2. **⚡ Standalone Screen VFX** - Screen-space effects for any interactive object

You can use either one or both together!

---

## 🥚 SYSTEM 1: EGG REVEAL (Cinematic)

Perfect for: Pet simulators, gacha games, loot boxes, egg hatching

### Files Needed:
```
ReplicatedStorage/
└── VFX/
    ├── EggRevealVFX.lua (Module)
    └── ScreenVFX.lua (Module)
└── Assets/
    └── EggModel (Model)

StarterPlayer/StarterPlayerScripts/
└── EggReveal_ExampleClient.lua (LocalScript)
```

### Features:
- ✅ **Camera control** (cinematic view of egg)
- ✅ **World-space egg VFX** (crack glow, particles)
- ✅ **Screen overlay UI** (tier badge, pet name)
- ✅ **Smooth sequencing** (buildup → flash → reveal)
- ✅ **Auto camera restore**

### Installation Steps:

#### 1. Create Folder Structure
```lua
-- In ReplicatedStorage:
ReplicatedStorage
├── VFX (Folder)
└── Assets (Folder)
```

#### 2. Add Modules
- Put `EggRevealVFX.lua` in `ReplicatedStorage.VFX` as a **ModuleScript**
- Put `ScreenVFX.lua` in `ReplicatedStorage.VFX` as a **ModuleScript**

#### 3. Create EggModel
See **EGG_MODEL_SPEC.md** for full details!

Quick version:
```
EggModel (Model in ReplicatedStorage.Assets)
├── Aura (Part)
│   └── PointLight
└── EggBase (Part) ← Set as PrimaryPart!
    └── Mesh (SpecialMesh, MeshId = rbxassetid://1527559)
```

**Critical:**
- Aura.Size = EggBase.Size * 0.9 (creates crack glow!)
- Aura.CFrame = EggBase.CFrame (centered!)
- Set EggModel.PrimaryPart = EggBase

#### 4. Add Client Script
- Put `EggReveal_ExampleClient.lua` in `StarterPlayer/StarterPlayerScripts` as a **LocalScript**

#### 5. Create Interactive Objects
Either:
- **Option A**: Use the server script to spawn eggs (see below)
- **Option B**: Manually place parts and:
  - Add attribute: `VFXInteractive` (Boolean) = `true`
  - Add attribute: `VFXRarity` (String) = `"Common"`, `"Rare"`, `"Epic"`, or `"Legendary"`
  - Add attribute: `PetName` (String) = `"Your Pet Name"`
  - Tag with CollectionService: `"VFXInteractive"`

### Test It:
```lua
-- In console:
_G.TestEggReveal("Epic", "Cerberage")
```

---

## ⚡ SYSTEM 2: STANDALONE SCREEN VFX

Perfect for: Collectibles, power-ups, chests, interactive objects

### Files Needed:
```
StarterPlayer/StarterPlayerScripts/
└── StandaloneScreenVFX_Client.lua (LocalScript)
```

### Features:
- ✅ **Screen shake** (no camera drift!)
- ✅ **Radial beams** (proper rendering!)
- ✅ **Particles** (GUI-based)
- ✅ **Blur + Bloom + Color correction**
- ✅ **Circular waves**
- ✅ **Text popups**
- ✅ **Rarity-based intensity**
- ✅ **NO camera control** (stays in normal gameplay)

### Installation Steps:

#### 1. Add Client Script
- Put `StandaloneScreenVFX_Client.lua` in `StarterPlayer/StarterPlayerScripts` as a **LocalScript**

#### 2. Create Interactive Objects
Either:
- **Option A**: Use the server script (see below)
- **Option B**: Manually place parts and:
  - Add attribute: `VFXInteractive` (Boolean) = `true`
  - Add attribute: `VFXRarity` (String) = `"Common"`, `"Rare"`, `"Epic"`, or `"Legendary"`
  - Tag with CollectionService: `"VFXInteractive"`

### Test It:
```lua
-- In console:
_G.TriggerVFX("Epic")
```

---

## 🖥️ SERVER SCRIPT (Optional but Recommended)

**File:** `RobloxVFX_ServerScript.lua`

### Installation:
- Put in **ServerScriptService** as a **Script**

### Features:
- ✅ Spawns interactive eggs/crystals
- ✅ Server-side reward logic
- ✅ VFX replication (multiplayer)
- ✅ CollectionService integration

### Usage:

#### Spawn Interactive Eggs:
```lua
_G.CreateInteractiveEgg(Vector3.new(0, 10, 0), "Epic", "Cerberage")
```

#### Spawn Interactive Crystals:
```lua
_G.CreateInteractiveCrystal(Vector3.new(20, 10, 0), "Rare", "PowerCrystal")
```

#### Add Custom Reward Logic:
Edit the `handleEggHatch` function in the server script:
```lua
function handleEggHatch(player: Player, rarity: string)
    -- Your custom logic here!
    -- Give pets, coins, items, etc.
end
```

---

## 🎨 RARITY TIERS

Both systems support these rarities:

| Rarity | Color | Intensity |
|--------|-------|-----------|
| **Common** | Gray | Basic effects |
| **Rare** | Blue | Medium effects |
| **Epic** | Purple | Intense effects |
| **Legendary** | Gold | INSANE effects |

### Customizing Rarities:

Edit `RarityConfig` in either client script:
```lua
local RarityConfig = {
    MyCustomRarity = {
        color = Color3.fromRGB(255, 0, 0),
        particleCount = 100,
        beamCount = 24,
        duration = 2.5,
        text = "CUSTOM!",
        -- ... more properties
    }
}
```

---

## 📋 COMPARISON: Which System to Use?

### Use **Egg Reveal System** if you want:
- ✅ Cinematic camera movement
- ✅ 3D world-space egg model
- ✅ Pet name + tier display
- ✅ Full player focus (like Pet Simulator X)
- ✅ Egg hatching / gacha mechanics

### Use **Standalone Screen VFX** if you want:
- ✅ NO camera movement (stay in gameplay)
- ✅ Screen-only effects (no 3D models)
- ✅ Quick collectible feedback
- ✅ Non-intrusive VFX
- ✅ Power-ups, coins, chests, etc.

### Use **BOTH** if you want:
- Egg reveals for rare hatches (Egg system)
- Quick feedback for common items (Screen VFX)

---

## 🔧 TROUBLESHOOTING

### "Module not found" error
- ✅ Check modules are in `ReplicatedStorage.VFX`
- ✅ Check they're **ModuleScripts** (not Scripts!)
- ✅ Check names match exactly: `EggRevealVFX`, `ScreenVFX`

### "EggModel not found" error
- ✅ Check model is in `ReplicatedStorage.Assets.EggModel`
- ✅ Check structure matches spec (Aura, EggBase, PointLight)
- ✅ Check PrimaryPart is set to EggBase

### Camera doesn't restore
- ✅ This is fixed in the new version!
- ✅ Make sure you're using `EggRevealVFX.lua` (not old scripts)

### Beams look wonky
- ✅ This is fixed in the new version!
- ✅ Uses `AnchorPoint = Vector2.new(0.5, 1)` for proper rendering

### No interactive parts detected
- ✅ Check parts have `VFXInteractive` attribute set to `true`
- ✅ Check parts are tagged with CollectionService: `"VFXInteractive"`
- ✅ Check parts are BaseParts (not Models!)

### VFX triggers infinitely
- ✅ This is fixed! (cooldown system)
- ✅ Check you're not calling VFX in a loop

---

## 🎯 QUICK START CHECKLIST

### For Egg Reveals:
- [ ] Create `ReplicatedStorage.VFX` folder
- [ ] Add `EggRevealVFX.lua` module
- [ ] Add `ScreenVFX.lua` module
- [ ] Create `ReplicatedStorage.Assets` folder
- [ ] Build `EggModel` (see EGG_MODEL_SPEC.md)
- [ ] Add `EggReveal_ExampleClient.lua` to StarterPlayerScripts
- [ ] (Optional) Add `RobloxVFX_ServerScript.lua` to ServerScriptService
- [ ] Test with `_G.TestEggReveal("Epic", "Cerberage")`

### For Screen VFX:
- [ ] Add `StandaloneScreenVFX_Client.lua` to StarterPlayerScripts
- [ ] (Optional) Add `RobloxVFX_ServerScript.lua` to ServerScriptService
- [ ] Create/spawn interactive parts
- [ ] Test with `_G.TriggerVFX("Epic")`

---

## 📚 ADDITIONAL DOCUMENTATION

- **EGG_MODEL_SPEC.md** - Complete egg model structure
- **WHAT_WAS_FIXED.md** - All bug fixes explained
- **RARITY_SYSTEM_GUIDE.txt** - Rarity system details
- **README.md** - Project overview

---

## 🎉 YOU'RE DONE!

Press **E** near interactive objects to see INSANE VFX! 🔥

Need help? Check the documentation or test with the global functions:
- `_G.TestEggReveal("Epic", "Cerberage")`
- `_G.TriggerVFX("Epic")`
- `_G.CreateInteractiveEgg(Vector3.new(0, 10, 0), "Epic", "Doggo")`
