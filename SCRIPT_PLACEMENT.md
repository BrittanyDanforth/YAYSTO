# Script Placement Guide

## ✅ Correct Script Locations

### DialogueGUIController.lua
**Location:** `StarterGui > DialogueGUI > ScreenGui > LocalScript`
- ✅ **CORRECT:** Script parent is `ScreenGui`
- ❌ **WRONG:** Don't put it inside `DialogueLabel` or `DialogueFrame`
- The script needs to access multiple GUI elements, so it must be at the ScreenGui level

### FacialAnimationController.lua
**Location:** `StarterPlayer > StarterPlayerScripts > LocalScript`
- This runs on the client for each player
- Automatically finds FaceControls in Workspace or on the character

### DialogueServerController.lua
**Location:** `ServerScriptService > ServerScript`
- Handles server-side dialogue logic

### DialogueMemory.lua
**Location:** `ReplicatedStorage > ModuleScript`
- Shared dialogue data accessible by both client and server

### NotificationHandler.lua
**Location:** `StarterGui > NotificationsGUI > NotificationFrame > LocalScript`
- Script parent should be the `NotificationFrame` GUI element

## ⚠️ Conflicting Scripts

### DialogueManager.lua (OLD/CONFLICTING)
**Issue:** This script is looking for `DialogueLabel` in the wrong location:
```lua
local gui = player:WaitForChild("PlayerGui"):WaitForChild("DialogueGui")
local dialogueLabel = gui:WaitForChild("DialogueLabel")  -- ❌ WRONG PATH
```

**Correct path should be:**
```lua
local gui = player:WaitForChild("PlayerGui"):WaitForChild("DialogueGui")
local screenGui = gui:WaitForChild("ScreenGui")  -- or whatever your ScreenGui is named
local dialogueFrame = screenGui:WaitForChild("DialogueFrame")
local dialogueLabel = dialogueFrame:WaitForChild("DialogueLabel")  -- ✅ CORRECT
```

**Solution:**
- Either delete `DialogueManager.lua` if `DialogueGUIController.lua` handles everything
- Or update `DialogueManager.lua` to use the correct GUI path
- **Recommendation:** Delete it since `DialogueGUIController` is the main controller

## GUI Structure Expected

```
StarterGui
├── DialogueGUI (ScreenGui)
│   └── ScreenGui (or whatever it's named)
│       ├── DialogueFrame
│       │   ├── DialogueLabel
│       │   ├── Choice1
│       │   ├── Choice2
│       │   ├── TimerLabel
│       │   │   └── timebar
│       │   └── SummaryFrame
│       │       └── SummaryLabel
│       └── DialogueGUIController (LocalScript) ← HERE
└── NotificationsGUI
    └── NotificationFrame
        ├── NotificationLabel
        └── NotificationHandler (LocalScript) ← HERE
```

## Why DialogueGUIController Must Be at ScreenGui Level

The script needs to access:
- `screenGui:WaitForChild("DialogueFrame")`
- `dialogueFrame:WaitForChild("DialogueLabel")`
- `dialogueFrame:WaitForChild("Choice1")`
- etc.

If you put it inside `DialogueLabel`, then `script.Parent` would be `DialogueLabel`, and it couldn't find `DialogueFrame` or other siblings.
