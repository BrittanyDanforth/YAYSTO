--[[
ULTRA-SMOOTH & HIGH-PERFORMANCE SLITHER.IO SNAKE SYSTEM V5.2 - LAG FIXED + PVP FIXED
- Fixed segment pooling to remove segments from workspace
- Added periodic cleanup for orphaned segments
- Optimized memory management
- FIXED: PVP collision detection - players now properly die when hitting other players
--]]

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local SnakeSkins = require(ReplicatedStorage:WaitForChild("SnakeSkins"))

-- Fast aliases
local Vector3new = Vector3.new
local CFramenew = CFrame.new
local CFramelookAt = CFrame.lookAt
local mathMin = math.min
local mathMax = math.max
local mathFloor = math.floor
local taskSpawn = task.spawn
local taskWait = task.wait

local Config = {
	HeadSize = Vector3new(3, 3, 3),
	SegmentSize = Vector3new(2.5, 2.5, 2.5),
	SegmentSpacing = 2.2,
	InitialLength = 15,
	MaxSegments = 2450,
	HeadColor = Color3.fromRGB(180, 0, 255),
	BodyColors = {
		Color3.fromRGB(180, 0, 255),
		Color3.fromRGB(255, 0, 150),
		Color3.fromRGB(255, 80, 200),
		Color3.fromRGB(255, 0, 150),
		Color3.fromRGB(180, 0, 255),
	},
	FollowSpeed = 0.96,
	UpdateRate = 30,
	MinDistance = 0.02,
	BoostSpeed = 32,
	BoostFollowSpeed = 0.98,
	HeadMaterial = Enum.Material.ForceField,
	BodyMaterial = Enum.Material.Neon,
	GlowIntensity = 1.5,
	GlowRange = 4,
}

-- Enhanced Segment Pooling with better cleanup
local SegmentPool = {}
local PoolSize = 0
local MAX_POOL_SIZE = 1000

-- Dedicated container for better organization
local SegmentContainer = workspace:FindFirstChild("SegmentContainer")
if not SegmentContainer then
	SegmentContainer = Instance.new("Folder")
	SegmentContainer.Name = "SegmentContainer"
	SegmentContainer.Parent = workspace
end

local function resetSegment(segment)
	segment.Anchored = true
	segment.CanCollide = false
	segment.CanQuery = false
	segment.CanTouch = false
	segment.Transparency = 0
	segment.Size = Config.SegmentSize
	segment.Material = Config.BodyMaterial
	segment.Shape = Enum.PartType.Ball
	segment.TopSurface = Enum.SurfaceType.Smooth
	segment.BottomSurface = Enum.SurfaceType.Smooth
	segment.Color = Config.BodyColors[1]
	segment.Name = "Segment"

	-- Clean up all children efficiently
	for _, child in segment:GetChildren() do
		if child:IsA("PointLight") or child:IsA("SelectionBox") or child:IsA("Attachment") then
			child:Destroy()
		end
	end
end

local function getSegment()
	if PoolSize > 0 then
		local segment = SegmentPool[PoolSize]
		SegmentPool[PoolSize] = nil
		PoolSize = PoolSize - 1
		resetSegment(segment)
		-- Re-parent to container when getting from pool
		segment.Parent = SegmentContainer
		return segment
	else
		local segment = Instance.new("Part")
		resetSegment(segment)
		segment.Parent = SegmentContainer
		return segment
	end
end

-- FIXED: Properly remove segments from workspace
local function returnSegment(segment)
	if not segment or not segment.Parent then return end

	-- Clean up the segment
	segment.Transparency = 1
	segment.CanCollide = false
	segment.CanQuery = false
	segment.CanTouch = false
	segment.Anchored = true

	-- Turn off lights and effects
	for _, child in segment:GetChildren() do
		if child:IsA("PointLight") then
			child.Enabled = false
		elseif child:IsA("SelectionBox") then
			child.Adornee = nil
		elseif child:IsA("Attachment") then
			child:Destroy()
		end
	end

	-- Only return to pool if we haven't exceeded max size
	if PoolSize < MAX_POOL_SIZE then
		PoolSize = PoolSize + 1
		SegmentPool[PoolSize] = segment
		-- CRITICAL FIX: Remove from workspace to prevent lag
		segment.Parent = nil
	else
		-- Destroy excess segments
		segment:Destroy()
	end
end

local function getOrCreateSnakeModel(player)
	local modelName = "Snake_" .. player.Name  -- Changed from SnakeModel_UserId to Snake_PlayerName for collision handler
	local existing = workspace:FindFirstChild(modelName)
	if existing and existing:IsA("Model") then
		return existing
	end
	local model = Instance.new("Model")
	model.Name = modelName
	model.Parent = workspace
	model:SetAttribute("IsSnakeModel", true)
	model:SetAttribute("OwnerUserId", player.UserId)
	model:SetAttribute("OwnerName", player.Name)  -- Add name attribute for easier lookup
	return model
end

local function createSegment(index, position, color, config, parentModel)
	local segment = getSegment()
	segment.Name = index == 0 and "Segment0_Head" or ("Segment" .. index)  -- Head is Segment0_Head for collision handler
	segment.Size = config.SegmentSize
	segment.Material = config.BodyMaterial
	segment.Color = color
	segment.CFrame = CFramenew(position)
	segment.Parent = parentModel
	segment.Transparency = 0

	segment:SetAttribute("IsSnakeSegment", true)
	segment:SetAttribute("SegmentIndex", index)
	segment:SetAttribute("OwnerName", parentModel:GetAttribute("OwnerName"))  -- Track owner for collision

	return segment
end

local function createVisualHead(rootPart, config, parentModel)
	local headPart = Instance.new("Part")
	headPart.Name = "Segment0_Head"  -- CRITICAL: Must be Segment0_Head for collision handler
	headPart.Size = config.HeadSize
	headPart.Material = config.HeadMaterial
	headPart.Color = config.HeadColor
	headPart.Shape = Enum.PartType.Ball
	headPart.CanCollide = false
	headPart.CanQuery = false
	headPart.CanTouch = false
	headPart.Anchored = true
	headPart.TopSurface = Enum.SurfaceType.Smooth
	headPart.BottomSurface = Enum.SurfaceType.Smooth
	headPart.Parent = parentModel

	headPart:SetAttribute("IsSnakeHead", true)
	headPart:SetAttribute("IsSnakeSegment", true)
	headPart:SetAttribute("SegmentIndex", 0)
	headPart:SetAttribute("OwnerName", parentModel:GetAttribute("OwnerName"))

	local headLight = Instance.new("PointLight")
	headLight.Color = config.HeadColor
	headLight.Brightness = config.GlowIntensity + 1
	headLight.Range = config.GlowRange + 2
	headLight.Parent = headPart

	local headOutline = Instance.new("SelectionBox")
	headOutline.Adornee = headPart
	headOutline.Color3 = Color3.fromRGB(255, 255, 255)
	headOutline.LineThickness = 0.08
	headOutline.Transparency = 1
	headOutline.Parent = headPart

	local function createEye(name, position, parent)
		local eye = Instance.new("Part")
		eye.Name = name
		eye.Size = Vector3new(0.6, 0.6, 0.6)
		eye.Material = Enum.Material.Neon
		eye.Color = Color3.fromRGB(255, 255, 255)
		eye.Shape = Enum.PartType.Ball
		eye.CanCollide = false
		eye.CanQuery = false
		eye.CanTouch = false
		eye.Anchored = false
		eye.Parent = parent
		eye.CFrame = parent.CFrame * CFramenew(position)

		local weld = Instance.new("WeldConstraint")
		weld.Part0 = parent
		weld.Part1 = eye
		weld.Parent = parent

		return eye, weld
	end

	local function createPupil(name, position, parent)
		local pupil = Instance.new("Part")
		pupil.Name = name
		pupil.Size = Vector3new(0.25, 0.25, 0.25)
		pupil.Material = Enum.Material.Neon
		pupil.Color = Color3.fromRGB(0, 0, 0)
		pupil.Shape = Enum.PartType.Ball
		pupil.CanCollide = false
		pupil.CanQuery = false
		pupil.CanTouch = false
		pupil.Anchored = false
		pupil.Parent = parent
		pupil.CFrame = parent.CFrame * CFramenew(position)

		local weld = Instance.new("WeldConstraint")
		weld.Part0 = parent
		weld.Part1 = pupil
		weld.Parent = parent

		return pupil, weld
	end

	local leftEye, leftEyeWeld = createEye("LeftEye", Vector3new(-0.6, 0.55, 0.8), headPart)
	local rightEye, rightEyeWeld = createEye("RightEye", Vector3new(0.6, 0.55, 0.8), headPart)
	local leftPupil, leftPupilWeld = createPupil("LeftPupil", Vector3new(0, 0, -0.2), leftEye)
	local rightPupil, rightPupilWeld = createPupil("RightPupil", Vector3new(0, 0, -0.2), rightEye)

	return {
		head = headPart,
		headLight = headLight,
		headOutline = headOutline,
		leftEye = leftEye,
		rightEye = rightEye,
		leftPupil = leftPupil,
		rightPupil = rightPupil,
		leftEyeWeld = leftEyeWeld,
		rightEyeWeld = rightEyeWeld,
		leftPupilWeld = leftPupilWeld,
		rightPupilWeld = rightPupilWeld,
	}
end

local playerSnakes = {}
if not _G.PlayerSnakes then
	_G.PlayerSnakes = {}
end

local function createUltraSmoothSnake(character)
	local humanoid = character:FindFirstChild("Humanoid") or character:WaitForChild("Humanoid", 5)
	local rootPart = character:FindFirstChild("HumanoidRootPart") or character:WaitForChild("HumanoidRootPart", 5)
	local player = Players:GetPlayerFromCharacter(character)
	if not humanoid or not rootPart or not player then return end

	local oldSnakeInstance = character:FindFirstChild("__SnakeInstance")
	if oldSnakeInstance then
		oldSnakeInstance:Destroy()
	end

	local playerSkinName = player:GetAttribute("SelectedSkin")
	local activeConfig = {}
	for k, v in Config do activeConfig[k] = v end
	if playerSkinName and SnakeSkins[playerSkinName] then
		for key, value in SnakeSkins[playerSkinName] do
			activeConfig[key] = value
		end
	end

	local leaderstats = player:FindFirstChild("leaderstats")
	if leaderstats then
		local lengthValue = leaderstats:FindFirstChild("Length")
		if lengthValue then
			lengthValue.Value = activeConfig.InitialLength
		end
	end

	for _, part in character:GetChildren() do
		if part:IsA("BasePart") then
			part.Transparency = 1
			part.CanCollide = false
		elseif part:IsA("Accessory") or part:IsA("Tool") then
			part:Destroy()
		end
	end

	local snakeModel = getOrCreateSnakeModel(player)
	for _, obj in snakeModel:GetChildren() do
		if obj:IsA("BasePart") then
			for _, child in obj:GetChildren() do
				if child:IsA("Attachment") then
					child:Destroy()
				end
			end
		end
		obj:Destroy()
	end

	local headParts = createVisualHead(rootPart, activeConfig, snakeModel)

	local segments = {}
	local startPos = rootPart.Position
	for i = 1, activeConfig.InitialLength do
		local pos = startPos - rootPart.CFrame.LookVector * (i * activeConfig.SegmentSpacing)
		local colorIndex = ((i - 1) % #activeConfig.BodyColors) + 1
		local color = activeConfig.BodyColors[colorIndex]
		local segment = createSegment(i, pos, color, activeConfig, snakeModel)
		segments[i] = segment
	end

	local currentLength = activeConfig.InitialLength
	local maxHistorySize = mathMin(mathFloor(activeConfig.MaxSegments * 1.1) + 10, 2000)
	local positionHistory = table.create(maxHistorySize)
	local historyHead = 1
	local initialHistoryPoint = { position = rootPart.Position, lookVector = rootPart.CFrame.LookVector }
	for i = 1, maxHistorySize do
		positionHistory[i] = initialHistoryPoint
	end

	local function addToHistory(data)
		positionHistory[historyHead] = data
		historyHead = (historyHead % maxHistorySize) + 1
	end

	local function getFromHistory(stepsBack)
		local index = historyHead - stepsBack
		if index < 1 then
			index = index + maxHistorySize
		end
		return positionHistory[index]
	end

	local connections = {}
	local isActive = true
	local updateCounter = 0
	local networkUpdateInterval = 2
	local lastNetworkUpdate = 0

	local function growSnake(amount)
		amount = amount or 5
		local grew = false
		for i = 1, amount do
			if currentLength < activeConfig.MaxSegments then
				grew = true
				currentLength = currentLength + 1
				local colorIndex = ((currentLength - 1) % #activeConfig.BodyColors) + 1
				local color = activeConfig.BodyColors[colorIndex]
				local lastSegment = segments[#segments]
				local newPos = lastSegment and lastSegment.Position or rootPart.Position
				local segment = createSegment(currentLength, newPos, color, activeConfig, snakeModel)
				segments[currentLength] = segment

				segment.Transparency = 1
				segment.Size = Vector3new(0.05, 0.05, 0.05)
				taskSpawn(function()
					local growTime = 0.15
					local t = 0
					local startSize = Vector3new(0.05, 0.05, 0.05)
					local endSize = activeConfig.SegmentSize
					local heartbeat = RunService.Heartbeat

					while t < growTime and segment.Parent do
						t = t + heartbeat:Wait()
						if segment.Parent then
							local alpha = mathMin(t / growTime, 1)
							segment.Size = startSize:Lerp(endSize, alpha)
							segment.Transparency = 1 - alpha
						end
					end
					if segment.Parent then
						segment.Size = endSize
						segment.Transparency = 0
					end
				end)
			end
		end

		if grew and leaderstats and updateCounter % 5 == 0 then
			local lengthValue = leaderstats:FindFirstChild("Length")
			if lengthValue then
				lengthValue.Value = currentLength
			end
		end
	end

	local function cleanup()
		if not isActive then return end
		isActive = false

		for _, conn in connections do
			if typeof(conn) == "RBXScriptConnection" then
				conn:Disconnect()
			end
		end

		for i, segment in pairs(segments) do
			if segment then
				returnSegment(segment)
			end
		end

		for name, part in pairs(headParts) do
			if typeof(part) == "Instance" and part.Parent then
				for _, child in part:GetChildren() do
					if child:IsA("Attachment") then
						child:Destroy()
					end
				end
				part:Destroy()
			end
		end

		if snakeModel and snakeModel.Parent then
			snakeModel:SetAttribute("BeingDestroyed", true)
			taskSpawn(function()
				taskWait(0.05)
				if snakeModel.Parent then
					snakeModel:Destroy()
				end
			end)
		end

		playerSnakes[player] = nil
		_G.PlayerSnakes[player] = nil

		local oldSnakeInstance = character:FindFirstChild("__SnakeInstance")
		if oldSnakeInstance then
			oldSnakeInstance:Destroy()
		end
	end

	local diedConn = humanoid.Died:Connect(cleanup)
	local ancestryConn = character.AncestryChanged:Connect(function()
		if not character.Parent then
			cleanup()
		end
	end)
	table.insert(connections, diedConn)
	table.insert(connections, ancestryConn)

	local heartbeatConn
	heartbeatConn = RunService.Heartbeat:Connect(function(dt)
		if not isActive or not rootPart.Parent then return end

		updateCounter = updateCounter + 1

		local isBoosting = humanoid.WalkSpeed > 16.1
		local followSpeed = isBoosting and activeConfig.BoostFollowSpeed or activeConfig.FollowSpeed

		local currentPos = rootPart.Position
		local currentCFrame = rootPart.CFrame
		local lookVector = currentCFrame.LookVector
		local headOffset = lookVector * 1.5
		local headPos = currentPos + headOffset

		if headParts.head and headParts.head.Parent then
			headParts.head.CFrame = CFramelookAt(headPos, headPos + lookVector)
		end

		local lastHistoryPoint = getFromHistory(1)
		local dist = (currentPos - lastHistoryPoint.position).Magnitude
		if dist > 0.015 then
			if dist > activeConfig.SegmentSpacing * 0.8 then
				local numInterpolations = mathMin(mathFloor(dist / (activeConfig.SegmentSpacing * 0.6)), 3)
				for i = 1, numInterpolations do
					local fraction = i / (numInterpolations + 1)
					local interpPos = lastHistoryPoint.position:Lerp(currentPos, fraction)
					local interpLook = lastHistoryPoint.lookVector:Lerp(lookVector, fraction).Unit
					addToHistory({ position = interpPos, lookVector = interpLook })
				end
			end
			addToHistory({ position = currentPos, lookVector = lookVector })
		end

		local currentTime = tick()

		for i = 1, currentLength do
			local segment = segments[i]
			if segment and segment.Parent then
				local delay = mathFloor(i * 1.15)
				local targetData = getFromHistory(delay)
				if targetData then
					local segmentPos = targetData.position - targetData.lookVector * (activeConfig.SegmentSpacing * 0.08)
					local currentSegmentPos = segment.Position
					local newPos = currentSegmentPos:Lerp(segmentPos, followSpeed)

					segment.CFrame = CFramenew(newPos)
				end
			end
		end

		if currentTime - lastNetworkUpdate > 0.1 then
			lastNetworkUpdate = currentTime
		end
	end)
	table.insert(connections, heartbeatConn)

	local snakeInstance = {
		segments = segments,
		headParts = headParts,
		cleanup = cleanup,
		grow = growSnake,
		model = snakeModel,
		isActive = function() return isActive end,
		player = player,  -- CRITICAL: Store player reference for collision detection
	}
	playerSnakes[player] = snakeInstance
	_G.PlayerSnakes[player] = snakeInstance

	return snakeInstance
end

local function handlePlayer(player)
	local leaderstats = Instance.new("Folder")
	leaderstats.Name = "leaderstats"
	leaderstats.Parent = player

	local length = Instance.new("NumberValue")
	length.Name = "Length"
	length.Value = 0
	length.Parent = leaderstats

	local function onCharacterAdded(character)
		taskSpawn(createUltraSmoothSnake, character)
	end

	if player.Character then
		onCharacterAdded(player.Character)
	end
	player.CharacterAdded:Connect(onCharacterAdded)
end

Players.PlayerRemoving:Connect(function(player)
	local snakeInstance = playerSnakes[player]
	if snakeInstance then
		snakeInstance.cleanup()
	end
	playerSnakes[player] = nil
	_G.PlayerSnakes[player] = nil
end)

-- NEW: Periodic cleanup to prevent orphaned segments
task.spawn(function()
	while true do
		task.wait(10) -- Check every 10 seconds

		local validSegments = {}

		-- Collect all valid segments from active snakes
		for _, player in pairs(Players:GetPlayers()) do
			local snake = playerSnakes[player] or _G.PlayerSnakes[player]
			if snake and snake.segments then
				for _, seg in pairs(snake.segments) do
					if seg and seg.Parent then
						validSegments[seg] = true
					end
				end
			end
		end

		-- Check SegmentContainer for orphaned segments
		if SegmentContainer then
			for _, child in pairs(SegmentContainer:GetChildren()) do
				if child:IsA("BasePart") and child.Name:match("^Segment") then
					if not validSegments[child] then
						-- This is an orphaned segment, destroy it
						child:Destroy()
					end
				end
			end
		end

		-- Clean up snake models without active players
		for _, child in pairs(workspace:GetChildren()) do
			if child:IsA("Model") and child:GetAttribute("IsSnakeModel") then
				local userId = child:GetAttribute("OwnerUserId")
				local playerExists = false

				for _, player in pairs(Players:GetPlayers()) do
					if player.UserId == userId then
						playerExists = true
						break
					end
				end

				if not playerExists then
					child:Destroy()
				end
			end
		end
	end
end)

local function initialize()
	print("SLITHER.IO SYSTEM V5.2 - LAG FIXED + PVP FIXED")
	for _, player in Players:GetPlayers() do
		handlePlayer(player)
	end
	Players.PlayerAdded:Connect(handlePlayer)
	print("System ready with improved performance and PVP!")
end

ReplicatedStorage:WaitForChild("RespawnSnake").OnServerEvent:Connect(function(player)
	if not player then return end
	player:LoadCharacter()
end)

taskSpawn(initialize)
