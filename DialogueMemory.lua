-- ReplicatedStorage/DialogueMemory (ModuleScript)

local DialogueMemory = {
	currentStep = 1,
	currentDialogue = nil,
	choicesMade = {},
	currentBranch = "main",

	characterRelationships = {
		Father   = 0,
		Daughter = 0,
	},

	playerStats = {
		courage = 50,
		empathy = 50,
	},

	currency = {
		shekels = 100,
		maxShekels = 100,
		itemsFound = 0,
	},

	dialogue = {
		[1] = {
			text = "Father: I know this is hard, but we have to stay strong.",
			options = {
				{
					text = "Stay silent",
					impact = {
						relationship = { Father = -5 },
						mood = "sad",          -- 👈 FACE EXPRESSION
						nextStep = 2,
					}
				},
				{
					text = "Ask what to do next",
					impact = {
						relationship = { Father = 5 },
						mood = "determined",   -- 👈 FACE EXPRESSION
						nextStep = 2,
					}
				},
			},
			timer = 15,
			defaultOption = 1,
			condition = function() return true end,
		},

		[2] = {
			text = "The journey continues...",
			options = {
				{
					text = "Continue",
					impact = {
						mood = "neutral",
						nextStep = nil,  -- End of dialogue
					}
				},
			},
			timer = 10,
			defaultOption = 1,
			condition = function() return true end,
		},

		-- add more steps here...
	},

	applyChoiceImpact = function(self, choice)
		if not choice or not choice.impact then
			return
		end

		-- Apply relationship changes
		for character, change in pairs(choice.impact.relationship or {}) do
			self.characterRelationships[character] =
				(self.characterRelationships[character] or 0) + change
		end

		-- Track choice
		table.insert(self.choicesMade, choice.text)
		
		-- Advance step
		if choice.impact.nextStep == nil then
			-- Explicitly nil means end dialogue - don't advance
			return
		elseif type(choice.impact.nextStep) == "number" then
			-- Explicit nextStep number provided
			self.currentStep = choice.impact.nextStep
		else
			-- No nextStep specified, auto-increment
			self.currentStep = self.currentStep + 1
		end
	end,

	checkDialogueCondition = function(self)
		local currentDialogue = self.dialogue[self.currentStep]
		if currentDialogue and currentDialogue.condition(self) then
			self.currentDialogue = currentDialogue
			return true
		end
		return false
	end,

	triggerDefaultChoice = function(self)
		local currentDialogue = self.currentDialogue
		if currentDialogue then
			local defaultChoice = currentDialogue.options[currentDialogue.defaultOption]
			if defaultChoice then
				self:applyChoiceImpact(defaultChoice)
			end
		end
	end
}

return DialogueMemory
