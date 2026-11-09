/* Mini Spotify player
 *
 * Any element with class "play-btn" and these attributes
 * can be played: data-track-id, data-src, data-title, data-artist, data-cover.
 */
(function () {
  "use strict";

  const audio = document.getElementById("audio");
  if (!audio) return; // page has no player

  const els = {
    bar: document.getElementById("player"),
    cover: document.getElementById("player-cover"),
    coverPlaceholder: document.getElementById("player-cover-placeholder"),
    title: document.getElementById("player-title"),
    artist: document.getElementById("player-artist"),
    play: document.getElementById("btn-play"),
    prev: document.getElementById("btn-prev"),
    next: document.getElementById("btn-next"),
    status: document.getElementById("player-status"),
    timeTotal: document.getElementById("time-total"),
    volume: document.getElementById("volume"),
    volumeIcon: document.getElementById("volume-icon"),
  };
  const VOLUME_KEY = "miniSpotifyVolume";

  // 1. Build the queue from every play button on the page (each track once).
  const queue = [];
  document.querySelectorAll(".play-btn").forEach(function (btn) {
    const id = btn.dataset.trackId;
    if (!queue.some(function (t) { return t.id === id; })) {
      queue.push({
        id: id,
        src: btn.dataset.src,
        title: btn.dataset.title,
        artist: btn.dataset.artist,
        cover: btn.dataset.cover,
      });
    }
  });
  let current = -1; // index in queue of the loaded track

  function showError(message) {
    els.status.textContent = message;
    els.bar.classList.add("has-error");
  }

  function clearError() {
    els.status.textContent = "";
    els.bar.classList.remove("has-error");
  }

  // 2. Keep every play icon, label and card highlight in sync with the audio.
  function updateButtons() {
    const playing = !audio.paused && !audio.ended;
    const currentId = current >= 0 ? queue[current].id : null;

    els.play.innerHTML = playing
      ? '<i class="bi bi-pause-fill" aria-hidden="true"></i>'
      : '<i class="bi bi-play-fill" aria-hidden="true"></i>';
    els.play.setAttribute("aria-label", playing ? "Pause" : "Play");

    document.querySelectorAll(".play-btn").forEach(function (btn) {
      const isCurrent = btn.dataset.trackId === currentId;
      const active = isCurrent && playing;
      const icon = btn.querySelector("i");
      if (icon) icon.className = active ? "bi bi-pause-fill" : "bi bi-play-fill";
      btn.setAttribute("aria-pressed", active ? "true" : "false");
      btn.setAttribute("aria-label",
        (active ? "Pause " : "Play ") + btn.dataset.title + " by " + btn.dataset.artist);
      const card = btn.closest("[data-track-card]");
      if (card) card.classList.toggle("is-playing", isCurrent);
    });
  }

  // never covers content (its height changes on phones and when an error shows).
  function fitPageToPlayer() {
    document.body.style.paddingBottom = els.bar.hidden ? "" : (els.bar.offsetHeight + 16) + "px";
  }
  if ("ResizeObserver" in window) {
    new ResizeObserver(fitPageToPlayer).observe(els.bar);
  }
  window.addEventListener("resize", fitPageToPlayer);

  // 3. Load a track into the player bar.
  function load(index) {
    const track = queue[index];
    current = index;
    clearError();
    audio.src = track.src;
    els.title.textContent = track.title;
    els.artist.textContent = track.artist;
    if (track.cover) {
      els.cover.src = track.cover;
      els.cover.alt = "Cover art for " + track.title;
      els.cover.hidden = false;
      els.coverPlaceholder.hidden = true;
    } else {
      els.cover.hidden = true;
      els.coverPlaceholder.hidden = false;
    }
    els.bar.hidden = false;
    document.body.classList.add("player-open");
    fitPageToPlayer();
  }

  function play() {
    const attempt = audio.play();
    if (attempt) {
      attempt.catch(function (err) {
        // NotAllowedError = browser blocked autoplay; anything else = bad file
        if (err.name !== "NotAllowedError" && err.name !== "AbortError") {
          showError("Sorry, this track can't be played.");
        }
        updateButtons();
      });
    }
  }

  function toggle() {
    if (current === -1) return;
    if (audio.paused) play(); else audio.pause();
  }

    // Skip forwards: play the following track; after the last, wrap to the first.
  function next() {
    if (current === -1) return;                // nothing loaded yet
    load((current + 1) % queue.length);        // % makes the last track wrap to index 0
    play();
  }

  // Skip backwards: more than 3 seconds in => restart this track,
  // otherwise play the one before (the first track wraps to the last).
  function prev() {
    if (current === -1) return;
    if (audio.currentTime > 3) {
      audio.currentTime = 0;
      return;
    }
    load((current - 1 + queue.length) % queue.length);
    play();
  }

  // When a track ends, the next one starts automatically.
  function onEnded() {
    if (queue.length > 1) {
      next();
    } else {
      updateButtons();  // a lone track (e.g. on a track detail page) just stops, no endless loop
    }
  }

  // 4. Clicks on any card / detail-page play button (event delegation).
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".play-btn");
    if (!btn) return;
    const index = queue.findIndex(function (t) { return t.id === btn.dataset.trackId; });
    if (index === -1) return;
    if (index === current) {
      toggle();          // same track: pause / resume
    } else {
      load(index);       // new track: load and play
      play();
    }
  });

  els.play.addEventListener("click", toggle);
  els.prev.addEventListener("click", prev);
  els.next.addEventListener("click", next);

  // 5. Audio events drive the UI.
  audio.addEventListener("play", updateButtons);
  audio.addEventListener("pause", updateButtons);
  audio.addEventListener("ended", onEnded);  // onEnded calls next(), which updates the buttons itself
    // US17: volume. Storage can be blocked (private mode, strict settings),
  // so every read and write is wrapped in try/catch and the player keeps working.
  function loadVolume() {
    try {
      const saved = parseFloat(localStorage.getItem(VOLUME_KEY));
      if (saved >= 0 && saved <= 1) return saved;
    } catch (e) { /* storage blocked: use the default */ }
    return parseFloat(els.volume.value); // default from the HTML (0.8)
  }

  function saveVolume(value) {
    try {
      localStorage.setItem(VOLUME_KEY, String(value));
    } catch (e) { /* storage blocked: volume still works, just isn't remembered */ }
  }

  function setVolume(value) {
    audio.volume = value;
    els.volume.value = value;
    const pct = Math.round(value * 100);
    els.volume.setAttribute("aria-valuetext", pct + "%");
    els.volume.style.setProperty("--level", pct + "%");
    els.volumeIcon.className = value === 0 ? "bi bi-volume-mute"
      : value < 0.5 ? "bi bi-volume-down" : "bi bi-volume-up";
  }

  setVolume(loadVolume());

  els.volume.addEventListener("input", function () {
    const value = parseFloat(els.volume.value);
    setVolume(value);   // changes straight away, while dragging
    saveVolume(value);
  });
  audio.addEventListener("error", function () {
    if (!audio.getAttribute("src")) return;
    showError("Sorry, this track can't be played.");
    updateButtons();
  });
})();