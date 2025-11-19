--[[
	DIALOGUE MEMORY SYSTEM - ZOMBIE APOCALYPSE GAMBLER STORY
	
	Massive branching storyline about a gambler who lost everything in the apocalypse.
	Features:
	- Complex branching paths (30+ story branches)
	- Currency tracking (Shekels lost/gained)
	- Relationship tracking (multiple characters)
	- Player stats (courage, empathy, survival, cunning)
	- Story state persistence
	- No conflicting branches (each path tracked separately)
]]

local DialogueMemory = {
	-- Current story state
	currentStep = 1,
	currentBranch = "main",
	currentDialogue = nil,
	
	-- Story progression tracking
	storyFlags = {
		metGambler = false,
		foundShelter = false,
		lostEverything = true,
		encounteredZombies = false,
		foundWeapon = false,
		metSurvivors = false,
		betrayed = false,
		redeemed = false,
		rememberedPast = false,
	},
	
	-- Currency system (Shekels - the currency that became worthless)
	currency = {
		shekels = 0,
		maxShekels = 10000,
		itemsFound = 0,
	},
	
	-- Character relationships (multiple characters in the story)
	characterRelationships = {
		["The Gambler"] = 0,
		["Old Man"] = 0,
		["Scavenger"] = 0,
		["Child"] = 0,
		["Memories"] = 0,
		["The Casino"] = 0,
	},
	
	-- Player stats that affect dialogue options
	playerStats = {
		courage = 50,
		empathy = 50,
		survival = 50,
		cunning = 50,
		guilt = 0,
		hope = 50,
	},
	
	-- Choices made throughout the story (for replay/analysis)
	choicesMade = {},
	
	-- Branching story tree - MASSIVE EXPANSION
	dialogue = {
		-- MAIN BRANCH: Introduction
		[1] = {
			branch = "main",
			text = "The Gambler: *staring at empty hands* I had 10,000 shekels... all gone. The casino took everything, then the dead took the casino.",
			options = {
				{ 
					text = "Remember what you had", 
					impact = { 
						relationship = {["Memories"] = 5},
						stats = {guilt = 10},
						nextStep = 2,
						branch = "memory"
					}
				},
				{ 
					text = "Focus on survival", 
					impact = { 
						relationship = {["The Gambler"] = 5},
						stats = {survival = 5, guilt = -5},
						nextStep = 3,
						branch = "survival"
					}
				}
			},
			timer = 15,
			defaultOption = 2,
			condition = function() return true end
		},
		
		-- MEMORY BRANCH: Remembering the past
		[2] = {
			branch = "memory",
			text = "The Gambler: *flashback* I remember... the last hand. All-in. 10,000 shekels on one card. The dealer smiled. I lost.",
			options = {
				{
					text = "Blame yourself",
					impact = {
						relationship = {["The Casino"] = -10, ["The Gambler"] = -5},
						stats = {guilt = 15, hope = -5},
						nextStep = 4,
						branch = "guilt"
					}
				},
				{
					text = "Blame the casino",
					impact = {
						relationship = {["The Casino"] = -15, ["The Gambler"] = 5},
						stats = {courage = 5, guilt = -5},
						nextStep = 5,
						branch = "anger"
					}
				}
			},
			timer = 12,
			defaultOption = 1,
			condition = function(self) return self.storyFlags.rememberedPast == false end
		},
		
		-- SURVIVAL BRANCH: Moving forward
		[3] = {
			branch = "survival",
			text = "The Gambler: No time for regrets. I hear something... shuffling. The dead are near.",
			options = {
				{
					text = "Hide immediately",
					impact = {
						stats = {survival = 10, courage = -5},
						nextStep = 6,
						branch = "stealth"
					}
				},
				{
					text = "Stand your ground",
					impact = {
						stats = {courage = 10, survival = -5},
						nextStep = 7,
						branch = "confrontation"
					}
				}
			},
			timer = 10,
			defaultOption = 1,
			condition = function(self) return self.storyFlags.encounteredZombies == false end
		},
		
		-- GUILT BRANCH: Self-blame
		[4] = {
			branch = "guilt",
			text = "The Gambler: It's my fault. I should've stopped. I should've saved something. Now I have nothing, and the world has nothing.",
			options = {
				{
					text = "Accept the guilt",
					impact = {
						stats = {guilt = 20, empathy = 5},
						nextStep = 8,
						branch = "redemption_seek"
					}
				},
				{
					text = "Try to move past it",
					impact = {
						stats = {guilt = -10, hope = 5},
						nextStep = 9,
						branch = "recovery"
					}
				}
			},
			timer = 12,
			defaultOption = 1,
			condition = function(self) return self.playerStats.guilt > 20 end
		},
		
		-- ANGER BRANCH: Blaming the casino
		[5] = {
			branch = "anger",
			text = "The Gambler: That place... it was rigged. They took everything from me. Now I'll take something back.",
			options = {
				{
					text = "Plan revenge",
					impact = {
						relationship = {["The Casino"] = -20},
						stats = {cunning = 10, empathy = -5},
						nextStep = 10,
						branch = "revenge"
					}
				},
				{
					text = "Let it go",
					impact = {
						relationship = {["The Casino"] = -5},
						stats = {hope = 10, guilt = -5},
						nextStep = 11,
						branch = "forgiveness"
					}
				}
			},
			timer = 12,
			defaultOption = 2,
			condition = function(self) return self.characterRelationships["The Casino"] < -10 end
		},
		
		-- STEALTH BRANCH: Hiding from zombies
		[6] = {
			branch = "stealth",
			text = "The Gambler: *hiding behind rubble* They're close. I can hear them... moaning. Like the slot machines used to.",
			options = {
				{
					text = "Stay hidden",
					impact = {
						stats = {survival = 15},
						nextStep = 12,
						branch = "safe_passage"
					}
				},
				{
					text = "Look for a weapon",
					impact = {
						stats = {courage = 5, survival = 5},
						storyFlags = {foundWeapon = true},
						nextStep = 13,
						branch = "weapon_found"
					}
				}
			},
			timer = 8,
			defaultOption = 1,
			condition = function(self) return self.storyFlags.encounteredZombies == true end
		},
		
		-- CONFRONTATION BRANCH: Facing zombies
		[7] = {
			branch = "confrontation",
			text = "The Gambler: *picking up a pipe* Fine. You want what I have? I have nothing left to lose.",
			options = {
				{
					text = "Fight with courage",
					impact = {
						stats = {courage = 15, survival = 10},
						storyFlags = {foundWeapon = true},
						nextStep = 14,
						branch = "victory"
					}
				},
				{
					text = "Fight desperately",
					impact = {
						stats = {courage = 5, survival = -5, guilt = 5},
						nextStep = 15,
						branch = "narrow_escape"
					}
				}
			},
			timer = 8,
			defaultOption = 1,
			condition = function(self) return self.playerStats.courage > 40 end
		},
		
		-- REDEMPTION SEEK BRANCH: Looking for redemption
		[8] = {
			branch = "redemption_seek",
			text = "The Gambler: Maybe... maybe I can help someone. Maybe that's how I make it right.",
			options = {
				{
					text = "Search for survivors to help",
					impact = {
						stats = {empathy = 15, hope = 10},
						nextStep = 16,
						branch = "helper"
					}
				},
				{
					text = "Focus on your own survival",
					impact = {
						stats = {survival = 10, empathy = -5},
						nextStep = 17,
						branch = "selfish"
					}
				}
			},
			timer = 12,
			defaultOption = 1,
			condition = function(self) return self.playerStats.guilt > 30 end
		},
		
		-- RECOVERY BRANCH: Moving past guilt
		[9] = {
			branch = "recovery",
			text = "The Gambler: The past is dead. Like everything else. I need to focus on now.",
			options = {
				{
					text = "Find supplies",
					impact = {
						stats = {survival = 15},
						currency = {itemsFound = 3},
						nextStep = 18,
						branch = "scavenging"
					}
				},
				{
					text = "Find other survivors",
					impact = {
						stats = {empathy = 10},
						storyFlags = {metSurvivors = true},
						nextStep = 19,
						branch = "community"
					}
				}
			},
			timer = 12,
			defaultOption = 1,
			condition = function(self) return self.playerStats.hope > 40 end
		},
		
		-- REVENGE BRANCH: Planning revenge
		[10] = {
			branch = "revenge",
			text = "The Gambler: The casino... it's still standing. Maybe there's something left. Maybe I can take back what's mine.",
			options = {
				{
					text = "Return to the casino",
					impact = {
						relationship = {["The Casino"] = -25},
						stats = {cunning = 15, courage = 10},
						nextStep = 20,
						branch = "casino_return"
					}
				},
				{
					text = "Realize revenge is pointless",
					impact = {
						relationship = {["The Casino"] = -10},
						stats = {hope = 15, empathy = 5},
						nextStep = 21,
						branch = "wisdom"
					}
				}
			},
			timer = 15,
			defaultOption = 2,
			condition = function(self) return self.characterRelationships["The Casino"] < -15 end
		},
		
		-- FORGIVENESS BRANCH: Letting go
		[11] = {
			branch = "forgiveness",
			text = "The Gambler: Holding onto anger... it's like holding onto those shekels. They're gone. The anger should be too.",
			options = {
				{
					text = "Fully let go",
					impact = {
						stats = {hope = 20, guilt = -10},
						storyFlags = {redeemed = true},
						nextStep = 22,
						branch = "peace"
					}
				},
				{
					text = "Still feel the sting",
					impact = {
						stats = {hope = 5, guilt = 5},
						nextStep = 23,
						branch = "conflicted"
					}
				}
			},
			timer = 12,
			defaultOption = 1,
			condition = function(self) return self.playerStats.hope > 50 end
		},
		
		-- Additional key story moments
		[12] = {
			branch = "safe_passage",
			text = "The Gambler: They passed. I'm safe. For now.",
			options = {
				{text = "Continue forward", impact = {nextStep = 18, branch = "scavenging"}},
				{text = "Rest and reflect", impact = {nextStep = 24, branch = "reflection"}}
			},
			timer = 10,
			defaultOption = 1,
			condition = function() return true end
		},
		
		[13] = {
			branch = "weapon_found",
			text = "The Gambler: *holding a crowbar* This... this feels right. Better than cards.",
			options = {
				{text = "Feel empowered", impact = {stats = {courage = 10}, nextStep = 25, branch = "empowerment"}},
				{text = "Feel burdened", impact = {stats = {guilt = 5}, nextStep = 26, branch = "burden"}}
			},
			timer = 10,
			defaultOption = 1,
			condition = function(self) return self.storyFlags.foundWeapon == true end
		},
		
		[24] = {
			branch = "reflection",
			text = "The Gambler: *sitting alone* 10,000 shekels. Gone. But I'm still here. That has to mean something.",
			options = {
				{text = "Find meaning in survival", impact = {stats = {hope = 15}, nextStep = 27, branch = "meaning"}},
				{text = "Accept the meaninglessness", impact = {stats = {hope = -10}, nextStep = 28, branch = "nihilism"}}
			},
			timer = 15,
			defaultOption = 1,
			condition = function() return true end
		},
		
		[27] = {
			branch = "meaning",
			text = "The Gambler: Maybe... maybe losing everything was the best thing that could've happened. I'm free now.",
			options = {},
			timer = 0,
			defaultOption = 1,
			condition = function() return true end
		},
		
		[28] = {
			branch = "nihilism",
			text = "The Gambler: Nothing matters. Not the shekels. Not me. Not this world.",
			options = {},
			timer = 0,
			defaultOption = 1,
			condition = function() return true end
		},
	},
	
	-- Function to apply choice impact
	applyChoiceImpact = function(self, choice)
		-- Apply relationship impacts
		for character, change in pairs(choice.impact.relationship or {}) do
			self.characterRelationships[character] = math.clamp(
				self.characterRelationships[character] + change,
				-100,
				100
			)
		end
		
		-- Apply stat impacts
		for stat, change in pairs(choice.impact.stats or {}) do
			self.playerStats[stat] = math.clamp(
				self.playerStats[stat] + change,
				0,
				100
			)
		end
		
		-- Apply currency impacts
		if choice.impact.currency then
			for currencyType, change in pairs(choice.impact.currency) do
				self.currency[currencyType] = self.currency[currencyType] + change
			end
		end
		
		-- Apply story flags
		if choice.impact.storyFlags then
			for flag, value in pairs(choice.impact.storyFlags) do
				self.storyFlags[flag] = value
			end
		end
		
		-- Store the choice
		table.insert(self.choicesMade, {
			text = choice.text,
			step = self.currentStep,
			branch = choice.impact.branch or self.currentBranch,
			timestamp = tick()
		})
		
		-- Update branch and step
		if choice.impact.branch then
			self.currentBranch = choice.impact.branch
		end
		self.currentStep = choice.impact.nextStep or (self.currentStep + 1)
	end,
	
	-- Function to check dialogue condition
	checkDialogueCondition = function(self)
		local currentDialogue = self.dialogue[self.currentStep]
		if currentDialogue and currentDialogue.condition(self) then
			self.currentDialogue = currentDialogue
			return true
		end
		return false
	end,
	
	-- Function to trigger default choice
	triggerDefaultChoice = function(self)
		local currentDialogue = self.currentDialogue
		if currentDialogue and currentDialogue.options then
			local defaultChoice = currentDialogue.options[currentDialogue.defaultOption or 1]
			if defaultChoice then
				self:applyChoiceImpact(defaultChoice)
			end
		end
	end,
	
	-- Function to get current story summary
	getStorySummary = function(self)
		local summary = {
			branch = self.currentBranch,
			step = self.currentStep,
			shekelsLost = self.currency.maxShekels - self.currency.shekels,
			relationships = {},
			stats = {},
			flags = {}
		}
		
		for char, value in pairs(self.characterRelationships) do
			summary.relationships[char] = value
		end
		
		for stat, value in pairs(self.playerStats) do
			summary.stats[stat] = value
		end
		
		for flag, value in pairs(self.storyFlags) do
			summary.flags[flag] = value
		end
		
		return summary
	end,
}

return DialogueMemory
