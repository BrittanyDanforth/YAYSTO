# Installation Guide - Snake System V5.2

## Quick Setup

### Step 1: Replace CharacterSetup
1. Find your existing `CharacterSetup` script in ServerScriptService
2. Replace it with `CharacterSetup_Updated.lua`
3. Rename it to `CharacterSetup` (remove "_Updated" suffix)

### Step 2: Replace SnakeSystemIntegration
1. Find your existing `SnakeSystemIntegration` script in ServerScriptService
2. Replace it with `SnakeSystemIntegration_Updated.lua`
3. Rename it to `SnakeSystemIntegration` (remove "_Updated" suffix)

### Step 3: Verify Collision Handler
1. Ensure `SnakeCollisionHandler` exists in ServerScriptService
2. It should already have the correct collision detection code
3. No changes needed to collision handler

### Step 4: Test
1. Run the game
2. Have two players join
3. Test PVP: Player A should die when hitting Player B's body
4. Test self-collision: Player should NOT die when hitting own body
5. Test AI: Player should die when hitting AI body

## File Locations

```
ServerScriptService/
├── CharacterSetup.lua (UPDATED)
├── SnakeSystemIntegration.lua (UPDATED)
└── SnakeCollisionHandler.lua (NO CHANGES NEEDED)

StarterPlayer/
└── StarterPlayerScripts/
    └── SnakeMovement.lua (NO CHANGES NEEDED)

ReplicatedStorage/
├── SnakeSkins.lua (NO CHANGES NEEDED)
├── SnakeConfig.lua (NO CHANGES NEEDED)
└── AISnake.lua (NO CHANGES NEEDED)
```

## What Changed

### CharacterSetup_Updated.lua
- Model naming convention
- Head part naming
- Segment naming
- Owner tracking
- Enhanced cleanup

### SnakeSystemIntegration_Updated.lua
- Works with new naming convention
- Better integration with CharacterSetup
- Proper snake registration
- Enhanced revive support

## Verification

After installation, check the output for:
- `SLITHER.IO SYSTEM V5.2 - LAG FIXED + PVP FIXED`
- `✅ Snake System Integration loaded! (Updated for CharacterSetup V5.2)`

## Troubleshooting

### Players still not dying in PVP?
1. Check model name: Should be `Snake_PlayerName` in workspace
2. Check head name: Should be `Segment0_Head` in the model
3. Check collision handler: Should be running and detecting collisions

### Still experiencing lag?
1. Check SegmentContainer: Should exist in workspace
2. Check for orphaned segments: Should be cleaned up every 10 seconds
3. Check pool size: Should not exceed 1000

### Snake not appearing?
1. Check CharacterSetup: Should be in ServerScriptService
2. Check player character: Should spawn properly
3. Check leaderstats: Should have Length value

## Rollback

If issues occur, you can:
1. Keep backup of old CharacterSetup
2. Restore old SnakeSystemIntegration
3. The collision handler should work with either version

## Next Steps

After installation:
1. Test PVP thoroughly
2. Monitor performance
3. Check for any errors in output
4. Verify all features work correctly
