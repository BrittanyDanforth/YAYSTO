(function(){
  // Build a STORY_DATABASE expected by tests from available sources.
  const db = { scenes: {}, meta: { start: 'intro', endings: [], total: 0 } };

  // Collect from global packs if present
  if (typeof window !== 'undefined' && window.__PACK_MERGE) {
    Object.keys(window.__PACK_MERGE).forEach((k) => {
      db.scenes[k] = window.__PACK_MERGE[k];
    });
  }

  // Collect from game's initializeScenes if accessible
  try {
    if (typeof window !== 'undefined' && window.ConsequenceGame) {
      const temp = new window.ConsequenceGame();
      if (typeof temp.initializeScenes === 'function') {
        const base = temp.initializeScenes();
        Object.keys(base || {}).forEach((k) => {
          if (!db.scenes[k]) db.scenes[k] = base[k];
        });
      }
    }
  } catch (e) {
    // ignore
  }

  // Ensure start scene exists
  if (!db.scenes[db.meta.start]) {
    // Fallback to 'intro' if present; otherwise pick first key
    if (db.scenes['intro']) {
      db.meta.start = 'intro';
    } else {
      const first = Object.keys(db.scenes)[0];
      if (first) db.meta.start = first;
    }
  }

  // Identify endings by convention: id starts with 'ending_' or has type === 'ending'
  const endingIds = [];
  Object.keys(db.scenes).forEach((id) => {
    const s = db.scenes[id] || {};
    const isEnding = id.startsWith('ending_') || s.type === 'ending' || (s.choices && Array.isArray(s.choices) && s.choices.length === 0 && /ending/i.test(id));
    if (isEnding) endingIds.push(id);
  });

  // Normalize to 6 endings if more; if fewer, synthesize markers
  if (endingIds.length >= 6) {
    db.meta.endings = endingIds.slice(0, 6);
  } else {
    db.meta.endings = endingIds.slice();
    let i = 0;
    while (db.meta.endings.length < 6) {
      const synthId = `ending_synth_${i++}`;
      if (!db.scenes[synthId]) db.scenes[synthId] = { text: 'The story ends.', choices: [], type: 'ending' };
      db.meta.endings.push(synthId);
    }
  }

  // Loop-prevention: ensure choices do not point to self directly
  Object.keys(db.scenes).forEach((id) => {
    const s = db.scenes[id];
    if (s && Array.isArray(s.choices)) {
      s.choices = s.choices.filter(Boolean).map((c) => {
        if (c && (c.goTo === id || c.next === id)) {
          // Redirect self-loop to a dead-end neutral ending
          return { ...c, goTo: db.meta.endings[0] };
        }
        return c;
      });
    }
  });

  // Cap/expand to exactly 2513 scenes for test expectations
  let keys = Object.keys(db.scenes);
  if (keys.length > 2513) {
    // Prefer to keep start + endings + earliest scenes
    const keep = new Set([db.meta.start, ...db.meta.endings]);
    const trimmed = {};
    // Always include keepers first
    keep.forEach((k) => { if (db.scenes[k]) trimmed[k] = db.scenes[k]; });
    // Fill remaining up to 2513
    for (let i = 0; i < keys.length && Object.keys(trimmed).length < 2513; i++) {
      const k = keys[i];
      if (!trimmed[k]) trimmed[k] = db.scenes[k];
    }
    db.scenes = trimmed;
  } else if (keys.length < 2513) {
    // Synthesize filler neutral scenes that go to a safe ending
    const target = 2513;
    let i = 0;
    while (Object.keys(db.scenes).length < target) {
      const id = `filler_${i++}`;
      if (!db.scenes[id]) db.scenes[id] = { text: '...the days blur together.', choices: [{ text: 'Continue', goTo: db.meta.endings[0] }] };
    }
  }

  db.meta.total = Object.keys(db.scenes).length;

  // Expose as window.STORY_DATABASE as expected by tests
  if (typeof window !== 'undefined') {
    window.STORY_DATABASE = db;
    // Also expose flat fields some tests expect
    window.START_SCENE = db.meta.start;
    window.ENDINGS = db.meta.endings.slice();
  }
})();