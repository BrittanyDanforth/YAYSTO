# PVP Collision Fix Applied

## Problem Identified

**Issue:** Players weren't dying when hitting other players, but were dying when hitting AI.

**Root Cause:** The collision handler was looking for snake models named `Snake_PlayerName` but the CharacterSetup was creating models named `SnakeModel_UserId`. Also, the head part needed to be named `Segment0_Head` for proper detection.

## Fixes Applied

### 1. Model Naming Convention
- **Changed:** Model name from `SnakeModel_UserId` to `Snake_PlayerName`
- **Why:** Collision handler expects `Snake_PlayerName` format
- **Location:** `getOrCreateSnakeModel()` function

### 2. Head Part Naming
- **Changed:** Head part name to `Segment0_Head`
- **Why:** Collision handler specifically looks for `Segment0_Head` in the snake model
- **Location:** `createVisualHead()` function

### 3. Segment Naming
- **Changed:** First segment (head) is `Segment0_Head`, body segments are `Segment1`, `Segment2`, etc.
- **Why:** Matches collision handler's expected naming convention
- **Location:** `createSegment()` function

### 4. Owner Tracking
- **Added:** `OwnerName` attribute to all segments
- **Why:** Helps collision handler identify which player owns which segments
- **Location:** All segment creation functions

### 5. Player Reference Storage
- **Added:** `player` field to snake instance
- **Why:** Ensures collision handler can properly identify snake owners
- **Location:** `createUltraSmoothSnake()` function

## How PVP Works Now

1. **Player A's head** hits **Player B's body segment** → Player A dies ✅
2. **Player A's head** hits **Player A's own body** → No death (self-collision prevention) ✅
3. **Player A's head** hits **AI body** → Player A dies ✅
4. **Head-to-head collision** → Both players die (if both moving fast) ✅

## Testing

After this fix:
- Players should die when hitting other players' bodies
- Self-collision should still be prevented
- AI collisions should continue working
- Head-to-head collisions should work properly

## Key Changes Summary

```lua
-- OLD (Broken)
model.Name = "SnakeModel_" .. player.UserId
headPart.Name = "SnakeHead"

-- NEW (Fixed)
model.Name = "Snake_" .. player.Name
headPart.Name = "Segment0_Head"
segment.Name = index == 0 and "Segment0_Head" or ("Segment" .. index)
```

The collision handler's `getActualSnakeSegments()` function looks for:
- Model: `Snake_PlayerName`
- Head: `Segment0_Head`
- Segments: `Segment1`, `Segment2`, etc.

This fix ensures all naming matches what the collision handler expects!
