# Troubleshooting Guide

## Current Issues & Solutions

### 1. ✅ FaceControls Properties Not Detected
**Error:** `⚠️ [FacialAnimationController] No valid FaceControls properties for expression: sad`

**Status:** Fixed - Improved property detection with better error handling

**What was wrong:**
- The metatable access was failing (returning nil)
- Properties weren't being detected correctly

**Solution Applied:**
- Simplified property detection to try direct access first
- Added better error handling for metatable access
- Added debug output to show what properties are available

**Next Steps if Still Failing:**
1. Check the debug output - it will show available properties
2. Verify FaceControls is properly set up on the character
3. Ensure the character has a DynamicHead with FaceControls enabled

### 2. ✅ Dialogue Step 2 Missing
**Error:** `Dialogue entry is nil for step 2`

**Status:** Fixed - Added step 2 to DialogueMemory

**What was wrong:**
- Dialogue only had step 1, but choices tried to advance to step 2

**Solution Applied:**
- Added a placeholder step 2 that ends the dialogue gracefully

### 3. ⚠️ DialogueManager Script Issue
**Error:** `Infinite yield possible on 'Players.kinjys.PlayerGui.DialogueGui:WaitForChild("DialogueLabel")'`

**Status:** Needs attention - This is a separate script

**What's wrong:**
- There's another script (`DialogueManager`) trying to find `DialogueLabel` in `DialogueGui`
- But the actual structure is `DialogueGui > ScreenGui > DialogueFrame > DialogueLabel`

**Solution:**
- Either update the DialogueManager script to use the correct path
- Or remove it if it's redundant (DialogueGUIController already handles this)

## Testing Checklist

After applying fixes:

1. ✅ Check if FaceControls properties are now detected
   - Look for `✓ Applied [property]` messages in output
   - If you see debug output, check what properties are available

2. ✅ Verify dialogue flows correctly
   - Step 1 → Choice → Step 2 should work
   - No more "nil for step 2" errors

3. ⚠️ Check DialogueManager script
   - Find it in your game
   - Either fix the path or remove if redundant

## FaceControls Setup Verification

To verify FaceControls is set up correctly:

1. Check that the character has a `Head` part
2. Check that `Head` has a `FaceControls` object
3. Verify FaceControls properties exist:
   - In Studio, select the FaceControls object
   - Check Properties panel - you should see properties like:
     - ChinRaiser (number)
     - LipCornerPuller (number)
     - etc.

4. If using DynamicHead:
   - Ensure DynamicHead is enabled
   - FaceControls should be a child of the Head

## Common FaceControls Issues

### Properties Don't Exist
- **Cause:** FaceControls not properly initialized
- **Fix:** Ensure character has DynamicHead enabled

### Properties Read-Only
- **Cause:** FaceControls might be locked or in use
- **Fix:** Check if any other scripts are modifying FaceControls

### Properties Return nil
- **Cause:** Wrong property names or FaceControls type mismatch
- **Fix:** Check debug output for available properties

## Debug Output Interpretation

When you see:
```
⚠️ [FacialAnimationController] No valid FaceControls properties for expression: sad
  [Debug] FaceControls type: FaceControls
  [Debug] Available children: (No NumberValue children found)
  [Debug] Numeric properties found: ChinRaiser=0, LipCornerPuller=0, ...
```

This means:
- FaceControls exists ✓
- No NumberValue children (using direct properties) ✓
- Properties are detected ✓
- But they're not being applied ✗

If properties are listed but not applied, the issue is likely:
- Properties are read-only
- Properties need different access method
- TweenService isn't working correctly
