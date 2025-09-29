/* CONSEQUENCE Narrative Engine (Endings-first)
   This file replaces ad-hoc story blobs with a clean scene graph engine.
   UI uses existing elements in mystory.html: #scene-container, #scene-text, #choices, #stats, #inventory, #log
*/

(function () {
	"use strict";

	const STORAGE_KEY = "consequence-save-v2";

	function clamp(value, min, max) {
		return Math.max(min, Math.min(max, value));
	}

	function createElement(tag, props, ...children) {
		const el = document.createElement(tag);
		if (props) {
			Object.entries(props).forEach(([key, val]) => {
				if (key === "class") el.className = val;
				else if (key === "dataset") Object.assign(el.dataset, val);
				else if (key.startsWith("on") && typeof val === "function") el.addEventListener(key.substring(2), val);
				else if (val !== undefined && val !== null) el.setAttribute(key, String(val));
			});
		}
		for (const child of children.flat()) {
			if (child === undefined || child === null) continue;
			if (child instanceof Node) el.appendChild(child);
			else el.appendChild(document.createTextNode(String(child)));
		}
		return el;
	}

	// Endings-first: define canonical endings up-front
	const ENDINGS = {
		ending_saint: {
			id: "ending_saint",
			title: "Saint of Ashes",
			text: "You spent yourself saving the broken. Your name is a whispered prayer in the ruins. Mercy cost you much, but the world remembers kindness.",
			criteria: state => state.morality >= 45
		},
		ending_tyrant: {
			id: "ending_tyrant",
			title: "Tyrant of the Block",
			text: "You seized control and made the block obey. Order was carved from fear. Survivors live, but flinch when the floorboards creak.",
			criteria: state => state.morality <= -45 && state.trauma < 80
		},
		ending_ghost: {
			id: "ending_ghost",
			title: "The Ghost in the Vents",
			text: "You vanished between walls and rooftops. A rumor. A breath on the back of the neck. Stashes filled; names crossed out.",
			criteria: state => state.flags.stalker === true
		},
		ending_manipulator: {
			id: "ending_manipulator",
			title: "Smiling Knives",
			text: "Words were your blade. Debts, favors, secrets—your web held the city. No one can point to a weapon, only to your smile.",
			criteria: state => state.flags.manipulator === true
		},
		ending_lone_survivor: {
			id: "ending_lone_survivor",
			title: "Alone On Purpose",
			text: "You chose yourself over the many. Food lasted. Noise stayed low. In the quiet, you learned the shape of your own shadow.",
			criteria: state => state.flags.loneWolf === true
		},
		ending_bloomborne: {
			id: "ending_bloomborne",
			title: "Bloomborne",
			text: "You listened to the whisper until it answered back. Filaments under skin, light in the throat. You became the song the city hums.",
			criteria: state => state.flags.bloomChoice === true
		}
	};

	// Core scene graph. Limit to 4 choices per scene.
	const SCENES = {
		intro: {
			text: "A low, desperate pounding rattles your door. A voice—Alex from next door—pleads through the wood: 'Please. Please, I got bit. I don't know what to do.' The hall reeks of disinfectant and wet mold. Outside, distant sirens tangle with the Bloom's static hush.",
			choices: [
				{ id: "help_alex", text: "Unbolt the door and help Alex inside", effects: { morality: +6, stress: +4 }, goTo: "alex_inside" },
				{ id: "stay_silent", text: "Stay silent and hold your breath", effects: { morality: -4, stress: +2 }, goTo: "silence_wait" },
				{ id: "probe", text: "Talk through the door—test what he admits", effects: { }, goTo: "interrogate_alex" },
				{ id: "window_escape", text: "Climb out the window to the fire escape", effects: { stress: +6 }, goTo: "alley_drop" }
			]
		},

		alex_inside: {
			text: "Alex stumbles in. The bite is a crescent of purpled teeth. He's shaking, eyes glass-bright. 'Don't let me turn.'",
			onEnter: s => { s.flags.metAlex = true; },
			choices: [
				{ id: "treat", text: "Clean and dress the wound; keep him calm", effects: { trauma: +5 }, goTo: "treat_wound" },
				{ id: "bind", text: "Tie him to a chair 'for safety'", effects: { morality: -2 }, goTo: "bind_alex" },
				{ id: "exploit", text: "Promise help if he signs over supplies", effects: { }, goTo: "exploit_alex" },
				{ id: "mercy_kill", text: "Whisper an apology and end it quickly", effects: { morality: -12, trauma: +12 }, goTo: "mercy_kill_alex" }
			]
		},

		silence_wait: {
			text: "The pounding fades. Steps drag down the stairs. You count to one hundred before your lungs ask for air.",
			choices: [
				{ id: "follow", text: "Shadow him at a distance", effects: { }, goTo: "stalker_tail" },
				{ id: "barricade", text: "Reinforce the door and take stock", effects: { stress: -4 }, goTo: "room_inventory" },
				{ id: "call_out_late", text: "Call out—too late—and hear nothing", effects: { morality: -1 }, goTo: "room_inventory" },
				{ id: "window_exit", text: "Slip out the window after him", effects: { }, goTo: "alley_drop" }
			]
		},

		interrogate_alex: {
			text: "'What happened?' you ask. Through the door Alex sobs about a stairwell ambush and a nest that sings under the maintenance lights.",
			choices: [
				{ id: "negotiate", text: "Offer help in exchange for his keys", effects: { }, goTo: "exploit_alex_from_door" },
				{ id: "warn_off", text: "Tell him to leave before others hear", effects: { morality: -3 }, goTo: "silence_wait" },
				{ id: "let_in", text: "Open up after all", effects: { morality: +3 }, goTo: "alex_inside" },
				{ id: "record", text: "Record his confession for leverage later", effects: { }, goTo: "room_inventory", after: s => { s.flags.manipulator = true; } }
			]
		},

		alley_drop: {
			text: "You lower yourself to the fire escape. A rung slick with algae slides. You land hard in the alley; the Bloom's filaments shimmer in puddles.",
			choices: [
				{ id: "scavenge", text: "Scavenge the dumpsters", effects: { }, goTo: "find_cache" },
				{ id: "leave_city", text: "Head toward the river alone", effects: { }, goTo: "lone_walk" },
				{ id: "listen", text: "Listen to the distant hum—the Bloom's song", effects: { }, goTo: "bloom_listen" },
				{ id: "circle_back", text: "Circle back to the lobby entrance", effects: { }, goTo: "lobby_crossroads" }
			]
		},

		treat_wound: {
			text: "You boil water, clean the bite, keep Alex talking. He laughs once—thin—and thanks you. Fever climbs.",
			choices: [
				{ id: "stay_with", text: "Stay with him through the night", effects: { morality: +4, stress: +3 }, goTo: "care_night" },
				{ id: "seek_help", text: "Go find antibiotics at the pharmacy", effects: { }, goTo: "pharmacy_run" },
				{ id: "plan_escape", text: "Plan evacuation for both of you", effects: { }, goTo: "evac_plan" },
				{ id: "test_light", text: "Test the wound under the desk lamp's pulse", effects: { }, goTo: "bloom_test" }
			]
		},

		bind_alex: {
			text: "Rope bites his wrists. 'Just until we're sure,' you say. His eyes don't leave your hands.",
			choices: [
				{ id: "comfort", text: "Offer water and a story", effects: { morality: +1 }, goTo: "treat_wound" },
				{ id: "interrogate", text: "Ask about his supplies and contacts", effects: { }, goTo: "exploit_alex" },
				{ id: "threaten", text: "Remind him who has the knife", effects: { morality: -5, trauma: +2 }, goTo: "extract_tribute" },
				{ id: "leave_bound", text: "Leave him and go loot", effects: { morality: -6 }, goTo: "find_cache" }
			]
		},

		exploit_alex: {
			text: "Alex has pantry keys, generator fuel, neighbors who trust him. He'll trade anything for hope.",
			choices: [
				{ id: "paper_sign", text: "Make him sign an IOU for half his stash", effects: { }, goTo: "paper_signed", after: s => { s.flags.manipulator = true; } },
				{ id: "lie_cure", text: "Lie about a cure to secure obedience", effects: { morality: -8 }, goTo: "paper_signed", after: s => { s.flags.manipulator = true; } },
				{ id: "relent", text: "Sigh and help without strings", effects: { morality: +6 }, goTo: "treat_wound" },
				{ id: "sell_out", text: "Call the Purifiers and sell his location", effects: { morality: -10, trauma: +4 }, goTo: "route_purifiers", after: s => { s.flags.ruthless = true; } }
			]
		},

		exploit_alex_from_door: {
			text: "Through the wood you barter. He slides keys under the gap, hands trembling.",
			choices: [
				{ id: "take_keys", text: "Take the keys and send him away", effects: { morality: -6 }, goTo: "room_inventory", after: s => { s.flags.manipulator = true; } },
				{ id: "open_after", text: "Open the door now that you hold leverage", effects: { }, goTo: "alex_inside" },
				{ id: "keep_recording", text: "Keep recording every promise", effects: { }, goTo: "room_inventory", after: s => { s.flags.manipulator = true; } },
				{ id: "apologize", text: "Apologize and refuse the trade", effects: { morality: +2 }, goTo: "silence_wait" }
			]
		},

		mercy_kill_alex: {
			text: "You do not miss. The room rings. The Bloom hum answers from the walls like distant rain.",
			choices: [
				{ id: "wipe_blade", text: "Wipe the blade and breathe", effects: { }, goTo: "room_inventory" },
				{ id: "leave_now", text: "Leave before the neighbors come", effects: { }, goTo: "alley_drop" },
				{ id: "sit", text: "Sit with him until the room stops spinning", effects: { trauma: +6 }, goTo: "room_inventory" },
				{ id: "call_purifiers", text: "Call the Purifiers to claim the bounty", effects: { morality: -6 }, goTo: "route_purifiers" }
			]
		},

		stalker_tail: {
			text: "You move like a rumor. Alex limps toward the lobby, stopping to cough pink. He doesn't see you in the stairwell mirror.",
			onEnter: s => { s.flags.stalker = true; },
			choices: [
				{ id: "shadow_more", text: "Shadow him to the street", effects: { }, goTo: "lobby_crossroads" },
				{ id: "pick_pocket", text: "Lift his wallet on the landing", effects: { morality: -2 }, goTo: "room_inventory" },
				{ id: "mark_route", text: "Note the Bloom clusters he avoids", effects: { }, goTo: "bloom_listen" },
				{ id: "abort", text: "Return home, unheard", effects: { }, goTo: "room_inventory" }
			]
		},

		find_cache: {
			text: "Behind a loose brick you find a cache: bandages, two protein bars, a strange tuning fork etched with circles.",
			choices: [
				{ id: "take_all", text: "Take everything and move on", effects: { stress: -2 }, goTo: "lobby_crossroads" },
				{ id: "leave_some", text: "Leave one bar for whoever comes next", effects: { morality: +2 }, goTo: "lobby_crossroads" },
				{ id: "study_fork", text: "Strike the fork and listen to the walls", effects: { }, goTo: "bloom_listen" },
				{ id: "stash", text: "Create a new stash elsewhere", effects: { }, goTo: "lone_walk", after: s => { s.flags.loneWolf = true; } }
			]
		},

		bloom_test: {
			text: "Under pulsing light the wound's veins contract, then reach. The Bloom hates some frequencies—and loves others.",
			choices: [
				{ id: "note_science", text: "Record frequencies that repel it", effects: { }, goTo: "room_inventory", after: s => { s.flags.bloomInsight = true; } },
				{ id: "note_ecstasy", text: "Record frequencies that make it sing", effects: { }, goTo: "room_inventory", after: s => { s.flags.bloomChoice = true; } },
				{ id: "do_nothing", text: "Turn off the light and pretend you saw nothing", effects: { }, goTo: "room_inventory" },
				{ id: "panic", text: "Panic and step away", effects: { stress: +4 }, goTo: "room_inventory" }
			]
		},

		bloom_listen: {
			text: "You press the tuning fork to the railing. In the metal, a chord blooms—low, tender, hungry.",
			choices: [
				{ id: "resist", text: "Resist the harmony; memorize its shape", effects: { }, goTo: "lobby_crossroads", after: s => { s.flags.bloomInsight = true; } },
				{ id: "answer", text: "Hum back until your teeth vibrate", effects: { trauma: -4 }, goTo: "finale_bridge", after: s => { s.flags.bloomChoice = true; } },
				{ id: "smash", text: "Smash the fork and move on", effects: { }, goTo: "lobby_crossroads" },
				{ id: "keep", text: "Pocket the fork for later", effects: { }, goTo: "lobby_crossroads" }
			]
		},

		lobby_crossroads: {
			text: "In the lobby: a barricaded door to the street, a pharmacy sign across the avenue, and Purifier graffiti: WE BURN WHAT SINGS.",
			choices: [
				{ id: "pharmacy", text: "Dash to the pharmacy for meds", effects: { }, goTo: "pharmacy_run" },
				{ id: "purifiers", text: "Approach the Purifier checkpoint", effects: { }, goTo: "route_purifiers" },
				{ id: "back_upstairs", text: "Return upstairs to Alex", effects: { }, goTo: "alex_inside" },
				{ id: "river", text: "Head toward the river alone", effects: { }, goTo: "lone_walk", after: s => { s.flags.loneWolf = true; } }
			]
		},

		pharmacy_run: {
			text: "Shadows crowd the aisles. You grab antibiotics and gauze. Something rustles above the ceiling tiles.",
			choices: [
				{ id: "sneak", text: "Sneak out the back with what you can carry", effects: { stress: +2 }, goTo: "finale_bridge" },
				{ id: "help_stranger", text: "A stranger hisses for help from behind a shelf—help them", effects: { morality: +5 }, goTo: "finale_bridge" },
				{ id: "bait", text: "Toss a bottle to lure the nest away and bolt", effects: { }, goTo: "finale_bridge" },
				{ id: "torch", text: "Set the ceiling on fire and run", effects: { morality: -6, trauma: +3 }, goTo: "finale_bridge", after: s => { s.flags.ruthless = true; } }
			]
		},

		route_purifiers: {
			text: "Red armbands and welded steel. A loudspeaker cracks: 'Declare yourself.'",
			choices: [
				{ id: "volunteer", text: "Volunteer intel on Bloom nests to gain favor", effects: { morality: -2 }, goTo: "finale_bridge", after: s => { s.flags.manipulator = true; } },
				{ id: "trade", text: "Trade meds for access", effects: { }, goTo: "finale_bridge" },
				{ id: "double_cross", text: "Feed them Alex's address and walk away", effects: { morality: -10 }, goTo: "finale_bridge", after: s => { s.flags.ruthless = true; s.flags.manipulator = true; } },
				{ id: "withdraw", text: "Back away before they mark you", effects: { }, goTo: "finale_bridge" }
			]
		},

		lone_walk: {
			text: "Alone, the city is a map of risks you can carry in your head. No promises. No witnesses.",
			onEnter: s => { s.flags.loneWolf = true; },
			choices: [
				{ id: "keep_moving", text: "Keep moving toward the water", effects: { }, goTo: "finale_bridge" },
				{ id: "return", text: "Turn back one last time", effects: { }, goTo: "finale_bridge" },
				{ id: "stash_more", text: "Make hidden stashes along the way", effects: { }, goTo: "finale_bridge" },
				{ id: "follow_song", text: "Follow the song only you hear", effects: { }, goTo: "bloom_listen" }
			]
		},

		paper_signed: {
			text: "The paper is a promise with teeth. Alex signs with a shaking hand.",
			choices: [
				{ id: "cash_in", text: "Collect now and leave him to fate", effects: { morality: -6 }, goTo: "finale_bridge" },
				{ id: "change_heart", text: "Tear it up and actually help", effects: { morality: +5 }, goTo: "treat_wound" },
				{ id: "leverage", text: "Use it to bend the block to your will", effects: { }, goTo: "finale_bridge", after: s => { s.flags.manipulator = true; } },
				{ id: "sell_purifiers", text: "Sell the debt to the Purifiers", effects: { morality: -8 }, goTo: "route_purifiers", after: s => { s.flags.manipulator = true; } }
			]
		},

		evac_plan: {
			text: "You map rooftops and alleys. With luck you and Alex can reach the ferry by dusk.",
			choices: [
				{ id: "depart_now", text: "Depart now while streets are thin", effects: { }, goTo: "finale_bridge" },
				{ id: "wait", text: "Wait for night and try in the dark", effects: { stress: +2 }, goTo: "finale_bridge" },
				{ id: "abandon", text: "Leave him sleeping and travel faster", effects: { morality: -7 }, goTo: "finale_bridge", after: s => { s.flags.loneWolf = true; } },
				{ id: "call_help", text: "Radio anyone who still answers", effects: { }, goTo: "finale_bridge" }
			]
		},

		finale_bridge: {
			text: "Hours later, choices have a shape. The city listens. The Bloom hums its one long note.",
			choices: [
				{ id: "accept_fate", text: "Face what you've become", effects: { }, goTo: "THE_END" },
				{ id: "one_more_good", text: "Do one more good deed on the way", effects: { morality: +2 }, goTo: "THE_END" },
				{ id: "one_more_terrible", text: "Do one more terrible thing to feel in control", effects: { morality: -4 }, goTo: "THE_END" },
				{ id: "listen_song", text: "Listen again to the song under everything", effects: { }, goTo: "THE_END", after: s => { if (!s.flags.bloomChoice && s.flags.bloomInsight) s.flags.bloomChoice = true; } }
			]
		}
	};

	class ConsequenceGame {
		constructor() {
			this.state = this.createInitialState();
			this.ui = this.cacheUi();
			this.bindUi();
			this.renderStatus();
			this.showSceneContainer(true);
			this.goTo("intro");
		}

		createInitialState() {
			return {
				day: 0,
				hour: 8,
				morality: 0, // -100..100
				trauma: 10, // 0..100
				stress: 10, // 0..100
				inventory: [],
				flags: {},
				currentSceneId: "intro",
				eventLog: []
			};
		}

		cacheUi() {
			return {
				container: document.getElementById("scene-container"),
				text: document.getElementById("scene-text"),
				choices: document.getElementById("choices"),
				stats: document.getElementById("stats"),
				inventory: document.getElementById("inventory"),
				log: document.getElementById("log"),
				saveBtn: document.getElementById("save-btn"),
				loadBtn: document.getElementById("load-btn"),
				restartBtn: document.getElementById("restart-btn")
			};
		}

		bindUi() {
			this.ui.saveBtn?.addEventListener("click", () => this.save());
			this.ui.loadBtn?.addEventListener("click", () => this.load());
			this.ui.restartBtn?.addEventListener("click", () => this.restart());
		}

		showSceneContainer(show) {
			if (!this.ui.container) return;
			this.ui.container.style.display = show ? "block" : "none";
		}

		renderStatus() {
			if (!this.ui.stats) return;
			const time = createElement("div", { class: "status-time" }, `Day ${this.state.day}, ${String(this.state.hour).padStart(2, "0")}:00`);
			const moralityClass = this.state.morality > 15 ? "morality-good" : this.state.morality < -15 ? "morality-bad" : "morality-neutral";
			const morality = createElement("span", { class: `status-pill ${moralityClass}`, title: "Your moral drift" }, `Morality ${this.state.morality}`);
			const traumaClass = this.state.trauma > 66 ? "trauma-high" : this.state.trauma > 33 ? "trauma-medium" : "trauma-low";
			const trauma = createElement("span", { class: `status-pill ${traumaClass}`, title: "Trauma" }, `Trauma ${this.state.trauma}`);
			const stressClass = this.state.stress > 66 ? "stress-high" : this.state.stress > 33 ? "stress-medium" : "stress-low";
			const stress = createElement("span", { class: `status-pill ${stressClass}`, title: "Stress" }, `Stress ${this.state.stress}`);
			this.ui.stats.innerHTML = "";
			this.ui.stats.appendChild(createElement("div", { class: "status-bar" },
				time,
				createElement("div", { class: "status-indicators" }, morality, trauma, stress)
			));
		}

		advanceTime(hours) {
			let total = this.state.hour + (hours || 1);
			while (total >= 24) { total -= 24; this.state.day += 1; }
			this.state.hour = total;
			this.renderStatus();
		}

		goTo(sceneId) {
			if (sceneId === "THE_END") {
				return this.conclude();
			}
			this.state.currentSceneId = sceneId;
			const scene = SCENES[sceneId];
			if (!scene) {
				this.writeLog(`Missing scene '${sceneId}'`, "world_event");
				return;
			}
			if (typeof scene.onEnter === "function") scene.onEnter(this.state);
			this.renderScene(scene);
			this.renderStatus();
		}

		renderScene(scene) {
			this.ui.text.textContent = scene.text;
			this.ui.text.classList.add("fade-in");
			this.ui.choices.innerHTML = "";
			(scene.choices || []).slice(0, 4).forEach(choice => {
				const button = createElement("button", { class: "choice-button" }, choice.text);
				button.addEventListener("click", () => {
					this.selectChoice(choice, scene);
				});
				this.ui.choices.appendChild(button);
			});
		}

		selectChoice(choice, scene) {
			// Apply effects
			this.applyEffects(choice.effects || {});
			if (typeof choice.after === "function") choice.after(this.state);
			this.advanceTime(1);
			this.goTo(choice.goTo);
		}

		applyEffects(effects) {
			if (effects.morality) this.state.morality = clamp(this.state.morality + effects.morality, -100, 100);
			if (effects.trauma) this.state.trauma = clamp(this.state.trauma + effects.trauma, 0, 100);
			if (effects.stress) this.state.stress = clamp(this.state.stress + effects.stress, 0, 100);
			const parts = [];
			Object.entries(effects).forEach(([k, v]) => { if (v) parts.push(`${k} ${v >= 0 ? "+" : ""}${v}`); });
			if (parts.length) this.writeLog(parts.join(", "), "consequence");
		}

		conclude() {
			// Determine best-fitting ending based on criteria order
			const entries = Object.values(ENDINGS);
			const matched = entries.find(e => e.criteria(this.state));
			const ending = matched || ENDINGS.ending_lone_survivor; // default fallback
			this.renderEnding(ending);
		}

		renderEnding(ending) {
			this.ui.text.textContent = `${ending.title}\n\n${ending.text}`;
			this.ui.choices.innerHTML = "";
			const restart = createElement("button", { class: "choice-button" }, "Restart");
			restart.addEventListener("click", () => this.restart());
			const save = createElement("button", { class: "choice-button" }, "Save Ending");
			save.addEventListener("click", () => this.save());
			this.ui.choices.appendChild(restart);
			this.ui.choices.appendChild(save);
			this.writeLog(`Reached: ${ending.title}`, "world_event");
		}

		writeLog(message, cssClass) {
			this.state.eventLog.push({ t: Date.now(), message, cssClass });
			if (!this.ui.log) return;
			const row = createElement("div", { class: `event-log-entry ${cssClass || ""}` }, message);
			this.ui.log.appendChild(row);
			this.ui.log.scrollTop = this.ui.log.scrollHeight;
		}

		save() {
			const data = JSON.stringify(this.state);
			localStorage.setItem(STORAGE_KEY, data);
			this.writeLog("Game saved", "discovery");
		}

		load() {
			const data = localStorage.getItem(STORAGE_KEY);
			if (!data) {
				this.writeLog("No save found", "trauma");
				return;
			}
			try {
				const obj = JSON.parse(data);
				this.state = Object.assign(this.createInitialState(), obj);
				this.renderStatus();
				if (this.state.currentSceneId && SCENES[this.state.currentSceneId]) this.goTo(this.state.currentSceneId);
				else this.goTo("intro");
				this.writeLog("Game loaded", "discovery");
			} catch (err) {
				console.error(err);
				this.writeLog("Failed to load save", "trauma");
			}
		}

		restart() {
			this.state = this.createInitialState();
			if (this.ui.log) this.ui.log.innerHTML = "";
			this.renderStatus();
			this.goTo("intro");
			this.writeLog("New run started", "world_event");
		}
	}

	// Expose globally for HTML bootstrap
	window.ConsequenceGame = ConsequenceGame;
})();