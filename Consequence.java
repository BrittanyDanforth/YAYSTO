import java.util.*;
import java.util.function.Consumer;
import java.util.function.Predicate;

/**
 * CONSEQUENCE (Console Edition, Java)
 * Endings-first narrative engine with a compact, readable scene graph.
 * - Time UI is separate from story text (Day/Hour header each turn)
 * - Max 4 choices per scene
 * - Six endings: Saint, Tyrant, Ghost, Manipulator, Lone Survivor, Bloomborne
 */
public class Consequence {
	public static void main(String[] args) {
		NarrativeEngine engine = new NarrativeEngine();
		engine.run();
	}
}

class NarrativeEngine {
	private final Map<String, Scene> idToScene = new LinkedHashMap<>();
	private final List<Ending> endings = new ArrayList<>();
	private final GameState state = new GameState();
	private final Scanner scanner = new Scanner(System.in);

	public NarrativeEngine() {
		buildEndings();
		buildScenes();
	}

	public void run() {
		println("=== CONSEQUENCE (Java Console) ===");
		println("Controls: enter a number 1-4 to choose; q exits.");
		goTo("intro");
		while (true) {
			Scene scene = idToScene.get(state.currentSceneId);
			if (scene == null) {
				println("[Engine] Missing scene: " + state.currentSceneId + ". Ending now.");
				renderEnding(pickEnding());
				return;
			}
			printStatusLine();
			println(scene.text);
			List<Choice> choices = scene.choices.size() > 4 ? scene.choices.subList(0, 4) : scene.choices;
			for (int i = 0; i < choices.size(); i++) {
				println("  " + (i + 1) + ") " + choices.get(i).text);
			}
			print("Choose [1-" + choices.size() + "] or q: ");
			String input = scanner.nextLine().trim();
			if (input.equalsIgnoreCase("q")) {
				println("Exiting.");
				return;
			}
			int idx;
			try { idx = Integer.parseInt(input) - 1; } catch (Exception e) { println("Invalid."); continue; }
			if (idx < 0 || idx >= choices.size()) { println("Out of range."); continue; }
			selectChoice(choices.get(idx));
			if ("THE_END".equals(state.currentSceneId)) {
				renderEnding(pickEnding());
				return;
			}
		}
	}

	private void buildEndings() {
		endings.add(new Ending(
			"ending_bloomborne",
			"Bloomborne",
			"You listened to the whisper until it answered back. Filaments under skin. You became the song the city hums.",
			s -> s.flags.contains("bloomChoice")
		));
		endings.add(new Ending(
			"ending_tyrant",
			"Tyrant of the Block",
			"You seized control and carved order from fear. Survivors live, but flinch when floorboards creak.",
			s -> s.morality <= -45 && s.trauma < 80
		));
		endings.add(new Ending(
			"ending_manipulator",
			"Smiling Knives",
			"Debts, favors, secrets—your web held the city. No one can point to a weapon, only to your smile.",
			s -> s.flags.contains("manipulator")
		));
		endings.add(new Ending(
			"ending_ghost",
			"The Ghost in the Vents",
			"You vanished between walls and rooftops. A rumor with a heartbeat.",
			s -> s.flags.contains("stalker")
		));
		endings.add(new Ending(
			"ending_saint",
			"Saint of Ashes",
			"You spent yourself saving the broken. Mercy cost you much, but the world remembers kindness.",
			s -> s.morality >= 45
		));
		endings.add(new Ending(
			"ending_lone_survivor",
			"Alone On Purpose",
			"You chose yourself over the many. In the quiet, you learned the shape of your own shadow.",
			s -> s.flags.contains("loneWolf")
		));
	}

	private void buildScenes() {
		// Intro - Alex at the door. Core premise.
		scene("intro",
			"A low, desperate pounding rattles your door. Alex—your neighbor—pleads: 'Please. I got bit.' The hall reeks of disinfectant and wet mold.",
			choices(
				choice("help_alex", "Unbolt the door and help Alex inside", eff(+6, 0, +4), go("alex_inside")),
				choice("stay_silent", "Stay silent and hold your breath", eff(-4, 0, +2), go("silence_wait")),
				choice("probe", "Talk through the door—test what he admits", eff(0, 0, 0), go("interrogate_alex")),
				choice("window_escape", "Climb out the window to the fire escape", eff(0, 0, +6), go("alley_drop"))
			)
		);

		scene("alex_inside",
			"Alex stumbles in. The bite is a crescent of purpled teeth. He's shaking. 'Don't let me turn.'",
			choices(
				choice("treat", "Clean and dress the wound; keep him calm", eff(0, +5, 0), go("treat_wound")),
				choice("bind", "Tie him to a chair 'for safety'", eff(-2, 0, 0), go("bind_alex")),
				choice("exploit", "Promise help if he signs over supplies", eff(0, 0, 0), go("exploit_alex")).after(s -> s.flags.add("manipulator")),
				choice("mercy_kill", "Whisper an apology and end it quickly", eff(-12, +12, 0), go("mercy_kill_alex"))
			)
		);

		scene("silence_wait",
			"The pounding fades. Steps drag down the stairs. You count to one hundred before lungs beg for air.",
			choices(
				choice("follow", "Shadow him at a distance", eff(0, 0, 0), go("stalker_tail")).after(s -> s.flags.add("stalker")),
				choice("barricade", "Reinforce the door and take stock", eff(0, 0, -4), go("room_inventory")),
				choice("late_call", "Call out—too late—and hear nothing", eff(-1, 0, 0), go("room_inventory")),
				choice("window_exit", "Slip out the window after him", eff(0, 0, 0), go("alley_drop"))
			)
		);

		scene("interrogate_alex",
			"'What happened?' you ask through the door. He sobs about a stairwell ambush and a nest that sings under maintenance lights.",
			choices(
				choice("negotiate", "Offer help in exchange for his keys", eff(0, 0, 0), go("exploit_alex_from_door")).after(s -> s.flags.add("manipulator")),
				choice("warn_off", "Tell him to leave before others hear", eff(-3, 0, 0), go("silence_wait")),
				choice("let_in", "Open up after all", eff(+3, 0, 0), go("alex_inside")),
				choice("record", "Record his promises for leverage", eff(0, 0, 0), go("room_inventory")).after(s -> s.flags.add("manipulator"))
			)
		);

		scene("alley_drop",
			"You lower yourself to the fire escape. A rung slick with algae slides. You land hard; filaments shimmer in puddles.",
			choices(
				choice("scavenge", "Scavenge the dumpsters", eff(0, 0, 0), go("find_cache")),
				choice("leave_city", "Head toward the river alone", eff(0, 0, 0), go("lone_walk")).after(s -> s.flags.add("loneWolf")),
				choice("listen", "Listen to the distant hum—the Bloom's song", eff(0, 0, 0), go("bloom_listen")),
				choice("circle_back", "Circle back to the lobby entrance", eff(0, 0, 0), go("lobby_crossroads"))
			)
		);

		scene("treat_wound",
			"You boil water, clean the bite, keep Alex talking. He laughs once—thin—and thanks you. Fever climbs.",
			choices(
				choice("stay_with", "Stay with him through the night", eff(+4, 0, +3), go("care_night")),
				choice("seek_help", "Go find antibiotics at the pharmacy", eff(0, 0, 0), go("pharmacy_run")),
				choice("plan_escape", "Plan evacuation for both of you", eff(0, 0, 0), go("evac_plan")),
				choice("test_light", "Test the wound under a pulsing lamp", eff(0, 0, 0), go("bloom_test"))
			)
		);

		scene("bind_alex",
			"Rope bites his wrists. 'Just until we're sure,' you say. His eyes don't leave your hands.",
			choices(
				choice("comfort", "Offer water and a story", eff(+1, 0, 0), go("treat_wound")),
				choice("interrogate", "Ask about his supplies and contacts", eff(0, 0, 0), go("exploit_alex")).after(s -> s.flags.add("manipulator")),
				choice("threaten", "Remind him who has the knife", eff(-5, +2, 0), go("extract_tribute")).after(s -> s.flags.add("manipulator")),
				choice("leave_bound", "Leave him and go loot", eff(-6, 0, 0), go("find_cache"))
			)
		);

		scene("exploit_alex",
			"Alex has pantry keys, generator fuel, neighbors who trust him. He'll trade anything for hope.",
			choices(
				choice("paper_sign", "Make him sign an IOU for half his stash", eff(0, 0, 0), go("paper_signed")).after(s -> s.flags.add("manipulator")),
				choice("lie_cure", "Lie about a cure to secure obedience", eff(-8, 0, 0), go("paper_signed")).after(s -> s.flags.add("manipulator")),
				choice("relent", "Help without strings", eff(+6, 0, 0), go("treat_wound")),
				choice("sell_out", "Call the Purifiers and sell his location", eff(-10, +4, 0), go("route_purifiers")).after(s -> s.flags.add("manipulator"))
			)
		);

		scene("exploit_alex_from_door",
			"Through the wood you barter. Keys slide under the gap, his hands trembling.",
			choices(
				choice("take_keys", "Take keys and send him away", eff(-6, 0, 0), go("room_inventory")).after(s -> s.flags.add("manipulator")),
				choice("open_after", "Open the door now that you have leverage", eff(0, 0, 0), go("alex_inside")),
				choice("keep_recording", "Keep recording every promise", eff(0, 0, 0), go("room_inventory")).after(s -> s.flags.add("manipulator")),
				choice("apologize", "Apologize and refuse the trade", eff(+2, 0, 0), go("silence_wait"))
			)
		);

		scene("mercy_kill_alex",
			"You do not miss. The room rings. The Bloom hum answers from the walls like distant rain.",
			choices(
				choice("wipe_blade", "Wipe the blade and breathe", eff(0, 0, 0), go("room_inventory")),
				choice("leave_now", "Leave before the neighbors come", eff(0, 0, 0), go("alley_drop")),
				choice("sit", "Sit with him until the room stops spinning", eff(0, +6, 0), go("room_inventory")),
				choice("call_purifiers", "Call Purifiers to claim bounty", eff(-6, 0, 0), go("route_purifiers"))
			)
		);

		scene("stalker_tail",
			"You move like a rumor. Alex limps toward the lobby, stopping to cough pink.",
			choices(
				choice("shadow_more", "Shadow him to the street", eff(0, 0, 0), go("lobby_crossroads")).after(s -> s.flags.add("stalker")),
				choice("pick_pocket", "Lift his wallet on the landing", eff(-2, 0, 0), go("room_inventory")),
				choice("mark_route", "Note Bloom clusters he avoids", eff(0, 0, 0), go("bloom_listen")),
				choice("abort", "Return home, unheard", eff(0, 0, 0), go("room_inventory"))
			)
		);

		scene("find_cache",
			"Behind a loose brick, a cache: bandages, two protein bars, a strange tuning fork etched with circles.",
			choices(
				choice("take_all", "Take everything and move on", eff(0, 0, -2), go("lobby_crossroads")),
				choice("leave_some", "Leave one bar for whoever comes next", eff(+2, 0, 0), go("lobby_crossroads")),
				choice("study_fork", "Strike the fork and listen to the walls", eff(0, 0, 0), go("bloom_listen")),
				choice("stash", "Create a new stash elsewhere", eff(0, 0, 0), go("lone_walk")).after(s -> s.flags.add("loneWolf"))
			)
		);

		scene("bloom_test",
			"Under pulsing light the veins contract, then reach. The Bloom hates some frequencies—and loves others.",
			choices(
				choice("note_science", "Record frequencies that repel it", eff(0, 0, 0), go("room_inventory")).after(s -> s.flags.add("bloomInsight")),
				choice("note_ecstasy", "Record frequencies that make it sing", eff(0, 0, 0), go("room_inventory")).after(s -> { s.flags.add("bloomChoice"); s.flags.add("bloomInsight"); }),
				choice("do_nothing", "Turn off the light and pretend you saw nothing", eff(0, 0, 0), go("room_inventory")),
				choice("panic", "Panic and step away", eff(0, +4, 0), go("room_inventory"))
			)
		);

		scene("bloom_listen",
			"You press the tuning fork to the railing. In the metal, a chord blooms—low, tender, hungry.",
			choices(
				choice("resist", "Resist the harmony; memorize its shape", eff(0, 0, 0), go("lobby_crossroads")).after(s -> s.flags.add("bloomInsight")),
				choice("answer", "Hum back until your teeth vibrate", eff(0, -4, 0), go("finale_bridge")).after(s -> s.flags.add("bloomChoice")),
				choice("smash", "Smash the fork and move on", eff(0, 0, 0), go("lobby_crossroads")),
				choice("keep", "Pocket the fork for later", eff(0, 0, 0), go("lobby_crossroads"))
			)
		);

		scene("lobby_crossroads",
			"In the lobby: a barricaded door to the street, a pharmacy sign across the avenue, and Purifier graffiti: WE BURN WHAT SINGS.",
			choices(
				choice("pharmacy", "Dash to the pharmacy for meds", eff(0, 0, 0), go("pharmacy_run")),
				choice("purifiers", "Approach the Purifier checkpoint", eff(0, 0, 0), go("route_purifiers")),
				choice("back_upstairs", "Return upstairs to Alex", eff(0, 0, 0), go("alex_inside")),
				choice("river", "Head toward the river alone", eff(0, 0, 0), go("lone_walk")).after(s -> s.flags.add("loneWolf"))
			)
		);

		scene("pharmacy_run",
			"Shadows crowd the aisles. You grab antibiotics and gauze. Something rustles above the ceiling tiles.",
			choices(
				choice("sneak", "Sneak out the back with what you can carry", eff(0, 0, +2), go("finale_bridge")),
				choice("help_stranger", "A stranger hisses for help—help them", eff(+5, 0, 0), go("finale_bridge")),
				choice("bait", "Toss a bottle to lure the nest away and bolt", eff(0, 0, 0), go("finale_bridge")),
				choice("torch", "Set the ceiling on fire and run", eff(-6, +3, 0), go("finale_bridge")).after(s -> s.flags.add("manipulator"))
			)
		);

		scene("route_purifiers",
			"Red armbands and welded steel. A loudspeaker cracks: 'Declare yourself.'",
			choices(
				choice("volunteer", "Volunteer intel on Bloom nests", eff(-2, 0, 0), go("finale_bridge")).after(s -> s.flags.add("manipulator")),
				choice("trade", "Trade meds for access", eff(0, 0, 0), go("finale_bridge")),
				choice("double_cross", "Feed them Alex's address and walk away", eff(-10, 0, 0), go("finale_bridge")).after(s -> s.flags.add("manipulator")),
				choice("withdraw", "Back away before they mark you", eff(0, 0, 0), go("finale_bridge"))
			)
		);

		scene("lone_walk",
			"Alone, the city is a map of risks you can carry in your head. No promises. No witnesses.",
			choices(
				choice("keep_moving", "Keep moving toward the water", eff(0, 0, 0), go("finale_bridge")).after(s -> s.flags.add("loneWolf")),
				choice("return", "Turn back one last time", eff(0, 0, 0), go("finale_bridge")),
				choice("stash_more", "Make hidden stashes along the way", eff(0, 0, 0), go("finale_bridge")).after(s -> s.flags.add("loneWolf")),
				choice("follow_song", "Follow the song only you hear", eff(0, 0, 0), go("bloom_listen"))
			)
		);

		scene("paper_signed",
			"The paper is a promise with teeth. Alex signs with a shaking hand.",
			choices(
				choice("cash_in", "Collect now and leave him to fate", eff(-6, 0, 0), go("finale_bridge")).after(s -> s.flags.add("manipulator")),
				choice("change_heart", "Tear it up and actually help", eff(+5, 0, 0), go("treat_wound")),
				choice("leverage", "Use it to bend the block to your will", eff(0, 0, 0), go("finale_bridge")).after(s -> s.flags.add("manipulator")),
				choice("sell_purifiers", "Sell the debt to the Purifiers", eff(-8, 0, 0), go("route_purifiers")).after(s -> s.flags.add("manipulator"))
			)
		);

		scene("evac_plan",
			"You map rooftops and alleys. With luck you and Alex can reach the ferry by dusk.",
			choices(
				choice("depart_now", "Depart now while streets are thin", eff(0, 0, 0), go("finale_bridge")),
				choice("wait", "Wait for night and try in the dark", eff(0, 0, +2), go("finale_bridge")),
				choice("abandon", "Leave him sleeping and travel faster", eff(-7, 0, 0), go("finale_bridge")).after(s -> s.flags.add("loneWolf")),
				choice("call_help", "Radio anyone who still answers", eff(0, 0, 0), go("finale_bridge"))
			)
		);

		scene("finale_bridge",
			"Hours later, choices have a shape. The city listens. The Bloom hums its one long note.",
			choices(
				choice("accept_fate", "Face what you've become", eff(0, 0, 0), go("THE_END")),
				choice("one_more_good", "Do one more good deed on the way", eff(+2, 0, 0), go("THE_END")),
				choice("one_more_terrible", "Do one more terrible thing to feel in control", eff(-4, 0, 0), go("THE_END")),
				choice("listen_song", "Listen again to the song under everything", eff(0, 0, 0), go("THE_END")).after(s -> { if (!s.flags.contains("bloomChoice") && s.flags.contains("bloomInsight")) s.flags.add("bloomChoice"); })
			)
		);
	}

	private void selectChoice(Choice choice) {
		applyEffects(choice);
		if (choice.afterEffect != null) choice.afterEffect.accept(state);
		advanceTime(1);
		goTo(choice.goToSceneId);
	}

	private void applyEffects(Choice choice) {
		if (choice.deltaMorality != 0) state.morality = clamp(state.morality + choice.deltaMorality, -100, 100);
		if (choice.deltaTrauma != 0) state.trauma = clamp(state.trauma + choice.deltaTrauma, 0, 100);
		if (choice.deltaStress != 0) state.stress = clamp(state.stress + choice.deltaStress, 0, 100);
	}

	private void goTo(String sceneId) {
		state.currentSceneId = sceneId;
		Scene s = idToScene.get(sceneId);
		if (s != null && s.onEnter != null) s.onEnter.accept(state);
	}

	private void renderEnding(Ending ending) {
		println("");
		println("=== THE END ===");
		println(ending.title);
		println("");
		println(ending.text);
	}

	private Ending pickEnding() {
		for (Ending e : endings) {
			if (e.criteria.test(state)) return e;
		}
		return endings.stream().filter(e -> e.id.equals("ending_lone_survivor")).findFirst().orElse(endings.get(endings.size()-1));
	}

	private void printStatusLine() {
		String hourStr = String.format("%02d", state.hour);
		println("");
		println("Day " + state.day + ", " + hourStr + ":00  |  Morality " + state.morality + "  Trauma " + state.trauma + "  Stress " + state.stress);
	}

	private void advanceTime(int hours) {
		int total = state.hour + Math.max(0, hours);
		while (total >= 24) { total -= 24; state.day += 1; }
		state.hour = total;
	}

	// Scene/Choice DSL helpers
	private void scene(String id, String text, List<Choice> choices) {
		Scene s = new Scene(id, text, null, choices);
		idToScene.put(id, s);
	}

	@SuppressWarnings("unused")
	private void scene(String id, String text, Consumer<GameState> onEnter, List<Choice> choices) {
		Scene s = new Scene(id, text, onEnter, choices);
		idToScene.put(id, s);
	}

	private List<Choice> choices(Choice... list) { return new ArrayList<>(Arrays.asList(list)); }

	private Choice choice(String id, String text, int[] eff, String goTo) { return new Choice(id, text, eff[0], eff[1], eff[2], goTo, null); }

	private Choice choice(String id, String text, int[] eff, Go go) { return new Choice(id, text, eff[0], eff[1], eff[2], go.sceneId, null); }

	private int[] eff(int morality, int trauma, int stress) { return new int[]{ morality, trauma, stress }; }

	private Go go(String sceneId) { return new Go(sceneId); }

	// Printing utilities
	private void println(String s) { System.out.println(s); }
	private void print(String s) { System.out.print(s); }

	// Inner helper types
	private static class Go { final String sceneId; Go(String s) { this.sceneId = s; } }
}

class GameState {
	int day = 0;
	int hour = 8;
	int morality = 0; // -100..100
	int trauma = 10; // 0..100
	int stress = 10; // 0..100
	String currentSceneId = "intro";
	Set<String> flags = new LinkedHashSet<>();

	static int clamp(int value, int min, int max) { return Math.max(min, Math.min(max, value)); }
}

class Scene {
	final String id;
	final String text;
	final Consumer<GameState> onEnter;
	final List<Choice> choices;

	Scene(String id, String text, Consumer<GameState> onEnter, List<Choice> choices) {
		this.id = id;
		this.text = text;
		this.onEnter = onEnter;
		this.choices = choices == null ? new ArrayList<>() : choices;
	}
}

class Choice {
	final String id;
	final String text;
	final int deltaMorality;
	final int deltaTrauma;
	final int deltaStress;
	final String goToSceneId;
	Consumer<GameState> afterEffect;

	Choice(String id, String text, int dM, int dT, int dS, String goToSceneId, Consumer<GameState> after) {
		this.id = id;
		this.text = text;
		this.deltaMorality = dM;
		this.deltaTrauma = dT;
		this.deltaStress = dS;
		this.goToSceneId = goToSceneId;
		this.afterEffect = after;
	}

	Choice after(Consumer<GameState> c) { this.afterEffect = c; return this; }
}

class Ending {
	final String id;
	final String title;
	final String text;
	final Predicate<GameState> criteria;

	Ending(String id, String title, String text, Predicate<GameState> criteria) {
		this.id = id;
		this.title = title;
		this.text = text;
		this.criteria = criteria;
	}
}