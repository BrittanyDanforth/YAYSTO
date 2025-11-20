# ReviveUI Fix - Respawn Button Issue

## Problem
Clicking "RESPAWN" button goes to menu instead of respawning.

## Root Cause
The ReviveUI is firing the **wrong remote event**. It's using `promptReviveRemote` instead of `reviveResponseRemote`.

## Fix

In your ReviveUI script (the one in StarterPlayerScripts), find this function:

```lua
-- Centralized function to send response to server
local function handleResponse(response)
	if isShowing then
		promptReviveRemote:FireServer(response)  -- ❌ WRONG!
		closeRevivePrompt()
	end
end
```

**Change it to:**

```lua
-- Wait for revive response remote
local reviveResponseRemote = remotes:WaitForChild("ReviveResponse")

-- Centralized function to send response to server
local function handleResponse(response)
	if isShowing then
		reviveResponseRemote:FireServer(response)  -- ✅ CORRECT!
		closeRevivePrompt()
	end
end
```

## Also Add This

At the top of your ReviveUI script, make sure you have:

```lua
local remotes = ReplicatedStorage:WaitForChild("Remotes")
local promptReviveRemote = remotes:WaitForChild("PromptRevive")
local reviveResponseRemote = remotes:WaitForChild("ReviveResponse")  -- ADD THIS!
```

This ensures the client is using the correct remote to send responses back to the server.
