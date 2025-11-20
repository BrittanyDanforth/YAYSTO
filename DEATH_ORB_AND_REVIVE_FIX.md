# Death Orb & Revive UI Fix - PVP Deaths

## Issues Fixed

### 1. Death Orbs Not Dropping on PVP Deaths ✅
**Problem:** When players died to other players, no death orbs were spawned. When dying to AI, orbs spawned correctly.

**Root Cause:** Segment positions were being captured during death processing, but by that time the segments might have already been destroyed or cleaned up.

**Fix:** 
- Segment positions are now captured **IMMEDIATELY** when `queuePlayerDeath()` is called, before any cleanup happens
- Positions are stored in the death queue entry itself
- This ensures positions are available even if segments are destroyed before processing

**Code Changes:**
```lua
-- In queuePlayerDeath():
-- CRITICAL FIX: Capture segment positions IMMEDIATELY before anything else
local segments = getActualSnakeSegments(player)
local segmentPositions = {}
-- ... capture positions ...
-- Store in death queue entry
table.insert(deathQueue, {
    type = "player",
    target = player,
    segmentPositions = segmentPositions, -- Stored immediately
    snakeLength = snakeLength
})
```

### 2. Revive UI Not Showing on PVP Deaths ✅
**Problem:** Revive UI worked when dying to AI, but didn't show when dying to other players.

**Root Cause:** The revive UI was only shown if `hasRevive or revivesAvailable > 0`, and the response listener was set up after the prompt was sent, causing potential race conditions.

**Fix:**
- Revive UI now **ALWAYS** shows (regardless of revive availability)
- Client handles showing/hiding the appropriate buttons (Revive button vs Buy button)
- Response listener is set up **BEFORE** firing the prompt to prevent race conditions
- This ensures revive UI works for both AI deaths and PVP deaths

**Code Changes:**
```lua
-- ALWAYS show revive UI (client handles buttons)
-- Set up response listener BEFORE firing prompt
responseConnection = reviveResponseRemote.OnServerEvent:Connect(...)
-- Then fire prompt
promptReviveRemote:FireClient(player)
```

## Testing

1. **Death Orbs:**
   - Die to another player → Should see death orbs spawn along your snake
   - Die to AI → Should see death orbs spawn (already working)
   - Check console for: `📍 [IMMEDIATE] Stored X segment positions for orb spawning`

2. **Revive UI:**
   - Die to another player → Revive UI should appear
   - Die to AI → Revive UI should appear
   - If you have revives → Shows "REVIVE" button
   - If no revives → Shows "BUY REVIVE" button
   - Check console for: `🚀 Sending revive prompt to PlayerName (always show, client handles buttons)`

## Files Modified

- `SnakeCollisionHandler_V10_Fixed.lua` - Updated death handling to capture segments immediately and always show revive UI
