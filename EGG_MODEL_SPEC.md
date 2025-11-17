# 🥚 EGG MODEL SPECIFICATION (Official Contract)

## 📍 Location

```
ReplicatedStorage
└── Assets
    └── EggModel (Model)
```

---

## 🏗️ Hierarchy

```
EggModel (Model)
│
├── Aura (Part) ← Creates the "cracked" glowing band
│   └── PointLight
│
└── EggBase (Part) ← The egg shell
    └── Mesh (SpecialMesh)
        └── Optional: SparkleAttachment (Attachment)
            └── ParticleEmitter (optional)
```

**Important:**
- ✅ **NO RingBurst part!** (Rings are done via screen VFX, not physical parts)
- ✅ **Aura intersects the egg** to create the cracked glow effect
- ✅ **EggBase is PrimaryPart** (set this in Studio!)

---

## 🥚 EggBase (The Shell)

### Properties:
```lua
Name: "EggBase"
Type: Part
Shape: Ball (or custom)
Anchored: true
CanCollide: false
Material: SmoothPlastic (or your choice)
Size: Vector3.new(3, 4, 3)  -- Adjust to your egg size
```

### Mesh Child:
```lua
Mesh (SpecialMesh)
├── MeshId: "rbxassetid://1527559"
├── TextureId: (optional)
└── Scale: Vector3.new(1, 1, 1)
```

### Optional Particles:
```lua
SparkleAttachment (Attachment) ← Optional!
└── ParticleEmitter
    ├── Enabled: false (script controls)
    ├── Lifetime: NumberRange.new(0.5, 1)
    ├── Rate: 50
    ├── Speed: NumberRange.new(5, 15)
    ├── SpreadAngle: Vector2.new(180, 180)
    ├── Acceleration: Vector3.new(0, 5, 0)
    ├── LightEmission: 1
    ├── Size: NumberSequence(0.5 → 0)
    ├── Transparency: NumberSequence(0 → 1)
    └── Texture: "rbxassetid://6490035152"
```

---

## 🔮 Aura (The Cracked Glow)

**This is KEY!** The Aura creates the glowing crack/band by **intersecting** with the egg shell.

### Properties:
```lua
Name: "Aura"
Type: Part
Shape: Ball
Anchored: true
CanCollide: false
Material: Neon
Color: Color3.fromRGB(0, 255, 255)  -- Any (script overwrites)
Transparency: 0.2 - 0.5  -- For visible crack
Size: EggBase.Size * 0.9  -- Slightly smaller to intersect!
CFrame: EggBase.CFrame  -- Centered on egg
```

### Why This Creates the Crack:
When a **Neon Ball** (Aura) is slightly smaller than and **inside** the egg shell, the intersection creates a glowing band that looks like a crack!

**Tuning the Effect:**
- **More obvious crack:** `Aura.Size = EggBase.Size * 0.85`, `Transparency = 0.2`
- **Softer glow:** `Aura.Size = EggBase.Size * 0.95`, `Transparency = 0.5`

### PointLight Child:
```lua
PointLight
├── Brightness: 2  -- Script tweens to 8 for flash
├── Range: 10-20
└── Color: Aura.Color  -- Matches aura
```

---

## 📋 Script API Contract

Any VFX script can safely assume this structure:

```lua
local RS = game:GetService("ReplicatedStorage")
local EggModelTemplate = RS:WaitForChild("Assets"):WaitForChild("EggModel")

-- Clone
local eggModel = EggModelTemplate:Clone()
eggModel.Parent = workspace

-- Required parts (MUST exist)
local eggBase = eggModel:WaitForChild("EggBase") :: BasePart
local aura = eggModel:WaitForChild("Aura") :: BasePart
local light = aura:WaitForChild("PointLight") :: PointLight

-- Optional particles
local sparkleAttachment = eggBase:FindFirstChild("SparkleAttachment")
local sparkleEmitter = sparkleAttachment 
    and sparkleAttachment:FindFirstChildWhichIsA("ParticleEmitter")

-- Use PrimaryPart for positioning
eggModel:SetPrimaryPartCFrame(targetCFrame)
```

### Guaranteed:
- ✅ `EggBase` exists
- ✅ `Aura` exists
- ✅ `Aura.PointLight` exists
- ✅ `EggModel.PrimaryPart == EggBase`

### Optional (use FindFirstChild):
- ⚠️ `SparkleAttachment`
- ⚠️ `ParticleEmitter`

### **NOT in model:**
- ❌ `RingBurst` (rings are VFX, not parts!)
- ❌ Any other fixed parts

---

## 🔧 Setup Checklist

### In Roblox Studio:

1. **Create Model Structure:**
   ```
   EggModel (Model)
   ├── Aura (Part - Ball, Neon)
   │   └── PointLight
   └── EggBase (Part with SpecialMesh)
   ```

2. **Set EggBase Properties:**
   - Anchored: ✓
   - CanCollide: ☐
   - Add SpecialMesh child
   - MeshId: `rbxassetid://1527559`

3. **Set Aura Properties:**
   - Shape: Ball
   - Material: Neon
   - Size: `EggBase.Size * 0.9`
   - Transparency: `0.3` (adjust for crack visibility)
   - **Position:** Centered on EggBase!

4. **Center Aura on EggBase:**
   ```lua
   -- In Command Bar:
   workspace.EggModel.Aura.CFrame = workspace.EggModel.EggBase.CFrame
   ```

5. **Add PointLight to Aura:**
   - Brightness: 2
   - Range: 15
   - Color: Match Aura color

6. **Set PrimaryPart:**
   - Right-click EggModel
   - Set PrimaryPart → EggBase

7. **Move to ReplicatedStorage:**
   - Create: `ReplicatedStorage` → `Assets` folder
   - Drag `EggModel` into `Assets`

---

## 🎨 Visual Effect Breakdown

### Buildup Phase (0.6s):
```
Aura changes:
├── Transparency: 0.5 → 0.2 (more visible crack!)
├── Size: Original * 1.1 (expands slightly)
└── Color: Set to rarity color

PointLight changes:
├── Brightness: 2 → 5
└── Range: 10 → 20

Result: Glowing crack intensifies!
```

### Explosion Phase (0.15s flash):
```
Aura changes:
├── Transparency: 0.2 → 0 (fully visible!)
├── Size: * 1.2 (expands more)
└── INTENSE GLOW

PointLight changes:
├── Brightness: 5 → 8
└── Range: 20 → 30

ParticleEmitters:
└── Emit(100) burst

Result: Blinding crack flash, then fade!
```

---

## 🎯 Why This Structure Works

### Crack Glow Effect:
1. **Neon Ball** (Aura) sits **inside** the egg shell
2. Aura is slightly **smaller** than egg (`Size * 0.9`)
3. Where they **intersect** = glowing band/crack
4. Scripts pulse the Aura = crack glows brighter!

### No Physical Ring:
- Screen VFX handles rings (GUI circles)
- No need for physical RingBurst part
- Cleaner, lighter model

### Modular Particles:
- Optional `SparkleAttachment`
- Scripts check `FindFirstChild` before using
- Model works with or without particles

---

## 📊 Size Examples

For an egg with `EggBase.Size = Vector3.new(3, 4, 3)`:

| Aura Size | Effect |
|-----------|--------|
| `2.7, 3.6, 2.7` (0.9x) | **Visible crack**, bright band |
| `2.55, 3.4, 2.55` (0.85x) | **Obvious crack**, very defined |
| `2.85, 3.8, 2.85` (0.95x) | **Subtle glow**, softer |
| `3.3, 4.4, 3.3` (1.1x) | **Outside glow**, no crack |

**Recommended:** Start with `0.9x` for clear crack!

---

## ✅ Validation Script

Run this in Command Bar to verify your model:

```lua
local model = workspace.EggModel

assert(model:IsA("Model"), "EggModel must be a Model")
assert(model.PrimaryPart, "PrimaryPart not set!")

local eggBase = model:FindFirstChild("EggBase")
assert(eggBase, "EggBase missing!")
assert(eggBase:IsA("BasePart"), "EggBase must be a Part")
assert(model.PrimaryPart == eggBase, "PrimaryPart should be EggBase")

local aura = model:FindFirstChild("Aura")
assert(aura, "Aura missing!")
assert(aura.Shape == Enum.PartType.Ball, "Aura should be Ball")
assert(aura.Material == Enum.Material.Neon, "Aura should be Neon")

local light = aura:FindFirstChild("PointLight")
assert(light, "PointLight missing in Aura!")

print("✅ EggModel structure is valid!")
print("📊 Aura size:", aura.Size)
print("📊 Aura size ratio:", aura.Size / eggBase.Size)
```

---

## 🎉 Summary

**Your EggModel Contract:**
```
EggModel (Model)
├── Aura (Neon Ball) ← Creates crack glow by intersecting
│   └── PointLight
└── EggBase (Shell with Mesh) ← PrimaryPart
    └── Optional: SparkleAttachment
```

**NO RingBurst!** Rings are screen VFX.

**The crack magic:** Aura intersects shell = glowing band!

**Ready for:** `EggRevealVFX:Play()`
