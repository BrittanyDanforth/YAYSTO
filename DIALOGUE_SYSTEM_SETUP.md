# DIALOGUE SYSTEM SETUP GUIDE

## 📁 File Locations

### ReplicatedStorage
- **DialogueMemory.lua** → ModuleScript (already created)

### ServerScriptService  
- **NotificationHandler.lua** → Script (already created)

### StarterGui > DialogueGUI > ScreenGui
- **DialogueGUIController.lua** → LocalScript (already created)

### StarterPlayerScripts
- **FacialAnimationController.lua** → LocalScript (already created)

## 🔧 Required RemoteEvents (Create in ReplicatedStorage)

1. **NotificationEvent** (RemoteEvent)
   - Used to send notifications from server to client

2. **ChoiceMade** (RemoteEvent)
   - Used to send choice data from client to server

3. **facialExpressionEvent** (RemoteEvent)
   - Used to trigger facial expressions

## 🎨 Required GUI Structure (Create in StarterGui)

### ScreenGui named "DialogueGUI"
```
DialogueGUI (ScreenGui)
├─ DialogueFrame (Frame)
│   ├─ DialogueLabel (TextLabel)
│   ├─ Choice1 (TextButton)
│   ├─ Choice2 (TextButton)
│   └─ TimerLabel (Frame)
│       └─ timebar (Frame)
└─ SummaryFrame (Frame)
    └─ SummaryLabel (TextLabel)
```

## 📝 GUI Element Properties

### DialogueFrame
- Size: UDim2.new(0, 600, 0, 400)
- Position: UDim2.new(0.5, -300, 0.5, -200)
- BackgroundColor3: Color3.fromRGB(20, 20, 25)
- BackgroundTransparency: 0.1

### DialogueLabel
- Size: UDim2.new(1, -20, 0, 200)
- Position: UDim2.new(0, 10, 0, 10)
- Text: ""
- TextSize: 18
- TextWrapped: true
- Font: Enum.Font.Gotham

### Choice1 & Choice2
- Size: UDim2.new(0.45, 0, 0, 50)
- Position: Choice1 at (0.025, 0, 220, 0), Choice2 at (0.525, 0, 220, 0)
- Text: ""
- TextSize: 16
- BackgroundColor3: Color3.fromRGB(40, 40, 50)

### TimerLabel
- Size: UDim2.new(1, -20, 0, 30)
- Position: UDim2.new(0, 10, 0, 280)
- Text: "15 seconds"
- TextSize: 14

### timebar (inside TimerLabel)
- Size: UDim2.new(1, 0, 0.5, 0)
- Position: UDim2.new(0, 0, 0.5, 0)
- BackgroundColor3: Color3.fromRGB(255, 0, 0)

### SummaryFrame
- Size: UDim2.new(0, 500, 0, 400)
- Position: UDim2.new(0.5, -250, 0.5, -200)
- BackgroundColor3: Color3.fromRGB(15, 15, 20)
- Visible: false

### SummaryLabel
- Size: UDim2.new(1, -20, 1, -20)
- Position: UDim2.new(0, 10, 0, 10)
- Text: ""
- TextSize: 14
- TextWrapped: true

## 🎮 Story Features

### Branching Story Tree
- **30+ dialogue branches** covering different story paths
- **No conflicting branches** - each path tracked separately
- **Complex decision trees** affecting relationships, stats, and story progression

### Character Relationships
- The Gambler (self-reflection)
- Old Man (survivor)
- Scavenger (opportunistic)
- Child (lost child)
- Memories (past self)
- The Casino (hatred/love)

### Player Stats
- Courage (affects combat choices)
- Empathy (affects helping others)
- Survival (affects resource management)
- Cunning (affects negotiation)
- Guilt (tracks guilt over losses)
- Hope (tracks hope for redemption)

### Currency System
- **Shekels**: The currency that became worthless (starts at 0, max was 10,000)
- **Items Found**: Track items that could be traded

### Story Flags
- metGambler
- foundShelter
- lostEverything (starts true)
- encounteredZombies
- foundWeapon
- metSurvivors
- betrayed
- redeemed
- rememberedPast

## 🚀 Usage

1. Place all files in their correct locations
2. Create RemoteEvents in ReplicatedStorage
3. Create GUI structure in StarterGui
4. The dialogue system will automatically start when a player joins
5. Players make choices that affect the story branching
6. Facial expressions change based on dialogue mood
7. Summary shows at the end of dialogue sequences

## 🎭 Facial Expression Integration

The FacialAnimationController automatically responds to `facialExpressionEvent` RemoteEvents. You can trigger expressions from dialogue:

```lua
facialExpressionEvent:FireClient(player, "sad") -- or "happy", "angry", "fear", "guilt", "determined", "neutral"
```

## 📊 Story Tracking

All choices, relationships, stats, and story flags are tracked in the DialogueMemory module. Access the summary:

```lua
local summary = DialogueMemory:getStorySummary()
```

This returns a table with all current story state information.
