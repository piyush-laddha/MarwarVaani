// Project MarwarVaani - Web Archive & Dictionary App

let allCards = [];
let filteredCards = [];

// DOM Elements
const cardsGrid = document.getElementById("cardsGrid");
const searchInput = document.getElementById("searchInput");
const clearSearchBtn = document.getElementById("clearSearchBtn");
const themeSelect = document.getElementById("themeSelect");
const typeSelect = document.getElementById("typeSelect");
const sortSelect = document.getElementById("sortSelect");
const resultsCount = document.getElementById("resultsCount");
const resetFiltersBtn = document.getElementById("resetFiltersBtn");
const emptyState = document.getElementById("emptyState");
const toast = document.getElementById("toast");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  loadCards();
  setupEventListeners();
});

// Load JSON data
async function loadCards() {
  try {
    const res = await fetch("data/cards.json?v=" + Date.now());
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    allCards = await res.json();
    applyFilters();
  } catch (err) {
    console.error("Failed to load cards:", err);
    resultsCount.textContent = "Error loading words. Please try refreshing.";
  }
}

// Setup Event Listeners
function setupEventListeners() {
  searchInput.addEventListener("input", () => {
    clearSearchBtn.style.display = searchInput.value ? "block" : "none";
    applyFilters();
  });

  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    clearSearchBtn.style.display = "none";
    searchInput.focus();
    applyFilters();
  });

  themeSelect.addEventListener("change", applyFilters);
  typeSelect.addEventListener("change", applyFilters);
  sortSelect.addEventListener("change", applyFilters);

  resetFiltersBtn.addEventListener("click", () => {
    searchInput.value = "";
    clearSearchBtn.style.display = "none";
    themeSelect.value = "ALL";
    typeSelect.value = "ALL";
    sortSelect.value = "newest";
    applyFilters();
  });
}

// Filter and Sort Cards
function applyFilters() {
  const query = searchInput.value.trim().toLowerCase();
  const selectedTheme = themeSelect.value;
  const selectedType = typeSelect.value;
  const sortBy = sortSelect.value;

  filteredCards = allCards.filter(card => {
    // 1. Theme Filter
    if (selectedTheme !== "ALL" && !card.theme.toLowerCase().includes(selectedTheme.toLowerCase())) {
      return false;
    }

    // 2. Type Filter
    if (selectedType !== "ALL" && card.item_type.toLowerCase() !== selectedType.toLowerCase()) {
      return false;
    }

    // 3. Search Query
    if (query) {
      const matchWord = (card.word_devanagari || "").toLowerCase().includes(query);
      const matchTranslit = (card.word_transliteration || "").toLowerCase().includes(query);
      const matchMeaning = (card.meaning || "").toLowerCase().includes(query);
      const matchVibe = (card.cultural_vibe || "").toLowerCase().includes(query);
      const matchMarwari = (card.dialogue_marwari || "").toLowerCase().includes(query);
      const matchEnglish = (card.dialogue_english || "").toLowerCase().includes(query);
      const matchTheme = (card.theme || "").toLowerCase().includes(query);

      return matchWord || matchTranslit || matchMeaning || matchVibe || matchMarwari || matchEnglish || matchTheme;
    }

    return true;
  });

  // Sort
  if (sortBy === "newest") {
    filteredCards.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  } else if (sortBy === "oldest") {
    filteredCards.sort((a, b) => (a.date || "").localeCompare(b.date || ""));
  } else if (sortBy === "alpha") {
    filteredCards.sort((a, b) => (a.word_transliteration || "").localeCompare(b.word_transliteration || ""));
  }

  renderCards();
}

// Render Cards to DOM
function renderCards() {
  cardsGrid.innerHTML = "";

  // Update counts
  if (filteredCards.length === allCards.length) {
    resultsCount.textContent = `Showing all ${allCards.length} Marwari cultural cards`;
  } else {
    resultsCount.textContent = `Showing ${filteredCards.length} of ${allCards.length} cards`;
  }

  // Handle empty state
  if (filteredCards.length === 0) {
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  // Build card elements
  filteredCards.forEach((card, index) => {
    const cardEl = document.createElement("article");
    cardEl.className = "card";

    // Format clean theme title
    const shortTheme = card.theme ? card.theme.split("(")[0].trim() : "Marwari Heritage";

    cardEl.innerHTML = `
      <div class="card-header">
        <div class="badge-group">
          <span class="badge badge-theme" title="${escapeHtml(card.theme)}">🎯 ${escapeHtml(shortTheme)}</span>
          <span class="badge badge-type">${escapeHtml(card.item_type || "Word")}</span>
        </div>
        ${card.date ? `<time class="card-date">${escapeHtml(card.date)}</time>` : ""}
      </div>

      <div class="card-hero">
        <div class="word-head">
          <h2 class="word-devanagari">${escapeHtml(card.word_devanagari)}</h2>
          <button class="speak-btn" aria-label="Listen pronunciation" title="Listen pronunciation" data-word="${escapeHtml(card.word_devanagari)}">
            🔊
          </button>
        </div>
        <p class="word-translit">${escapeHtml(card.word_transliteration || "")}</p>
      </div>

      <div class="card-body">
        <div>
          <span class="section-label">Meaning</span>
          <p class="meaning-block">${escapeHtml(card.meaning)}</p>
        </div>

        ${card.cultural_vibe ? `
          <div class="vibe-box">
            <span class="section-label">Cultural Vibe</span>
            <p>${escapeHtml(card.cultural_vibe)}</p>
          </div>
        ` : ""}

        ${card.dialogue_marwari ? `
          <div class="dialogue-box">
            <span class="section-label">Ghar Ri Boli (In Conversation)</span>
            <p class="marwari-spoken">"${escapeHtml(card.dialogue_marwari)}"</p>
            ${card.dialogue_english ? `<p class="english-trans">↳ <em>${escapeHtml(card.dialogue_english)}</em></p>` : ""}
          </div>
        ` : ""}

        ${card.family_prompt ? `
          <div class="prompt-box">
            <span class="section-label">Family Prompt</span>
            <p>💬 ${escapeHtml(card.family_prompt)}</p>
          </div>
        ` : ""}
      </div>

      <div class="card-footer">
        <button class="copy-wa-btn" data-index="${index}">
          <span>📋</span> Copy WhatsApp Card
        </button>
      </div>
    `;

    cardsGrid.appendChild(cardEl);
  });

  // Attach speech listeners
  document.querySelectorAll(".speak-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const textToSpeak = btn.getAttribute("data-word");
      speakWord(textToSpeak);
    });
  });

  // Attach copy listeners
  document.querySelectorAll(".copy-wa-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.getAttribute("data-index"), 10);
      const card = filteredCards[idx];
      copyWhatsAppFormat(card);
    });
  });
}

// Web Speech API Pronunciation
function speakWord(text) {
  if (!("speechSynthesis" in window)) {
    showToast("Speech synthesis not supported on this browser.");
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  
  // Prefer Hindi or regional Indian voice for authentic Devanagari phonetics
  const voices = window.speechSynthesis.getVoices();
  const indianVoice = voices.find(v => v.lang.includes("hi-IN") || v.lang.includes("hi") || v.lang.includes("IN"));
  
  if (indianVoice) {
    utterance.voice = indianVoice;
    utterance.lang = indianVoice.lang;
  } else {
    utterance.lang = "hi-IN";
  }

  utterance.rate = 0.85; // Slightly slower for clarity
  window.speechSynthesis.speak(utterance);
}

// Copy WhatsApp Markdown to Clipboard
function copyWhatsAppFormat(card) {
  const waMessage = 
`🐪 *MarwarVaani | Daily Marwari*
🎯 *Today's Theme:* ${card.theme}

📖 *${card.word_devanagari}* (${card.word_transliteration})
🏷️ *Type:* ${card.item_type}

🔹 *Meaning:* ${card.meaning}
🔹 *Cultural Vibe:* ${card.cultural_vibe}

🗣️ *Ghar Ri Boli (In Conversation):*
"${card.dialogue_marwari}"
↳ _${card.dialogue_english}_

💬 *Family Question:* ${card.family_prompt}

—
✨ _Keep our roots alive with MarwarVaani_`;

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(waMessage).then(() => {
      showToast(`Copied WhatsApp card for '${card.word_devanagari}'!`);
    }).catch(() => {
      fallbackCopy(waMessage);
    });
  } else {
    fallbackCopy(waMessage);
  }
}

// Fallback copy for older browsers
function fallbackCopy(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  document.body.appendChild(textArea);
  textArea.select();
  try {
    document.execCommand("copy");
    showToast("Copied WhatsApp card to clipboard!");
  } catch (err) {
    showToast("Could not copy text.");
  }
  document.body.removeChild(textArea);
}

// Show Toast
let toastTimeout;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove("show");
  }, 2400);
}

// Utility: Escape HTML
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

