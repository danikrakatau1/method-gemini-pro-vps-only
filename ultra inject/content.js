(() => {
  if (window.__G1_ZERO_COST_EXT_LOADED && document.getElementById("g1-zero-cost-floating-panel")) return;
  window.__G1_ZERO_COST_EXT_LOADED = true;

  const PRESETS = window.G1_ZERO_COST_PRESETS || [];
  const PK_URL = window.G1_PK_URL || "https://t.me/tutormint";
  const ALIAS = window.G1_PK_ALIAS || {};
  const PERIODS = [12, 6, 3, 1];
  let activePreset = PRESETS.find((p) => p.id === "ultra20tb_12m") || PRESETS[0] || null;

  function findPreset(presetId) {
    const id = ALIAS[presetId] || presetId;
    return PRESETS.find((p) => p.id === id) || null;
  }

  function presetBy(skuKey, months) {
    return PRESETS.find((p) => p.skuKey === skuKey && p.months === months) || null;
  }

  const CFG = window.G1_ZERO_COST_CFG || { includeYt: true };
  const TOKEN_PREF_KEY = "g1ZcTokenOverrides";
  CFG.includeYt = true;

  const CSS = `
#g1-zero-cost-floating-panel {
  position: fixed;
  right: 14px;
  bottom: 14px;
  z-index: 2147483646;
  width: 278px;
  color: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 12px;
  border-radius: 16px;
  overflow: hidden;
  background: rgba(10, 13, 20, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.5), 0 0 16px rgba(56, 189, 248, 0.15);
}
#g1-zero-cost-floating-panel.g1-zc-min { width: 196px; }
#g1-zero-cost-floating-panel.g1-zc-dragging { user-select: none; }
#g1-zc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.04);
  cursor: grab;
  user-select: none;
  touch-action: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
#g1-zero-cost-floating-panel.g1-zc-dragging #g1-zc-header { cursor: grabbing; }
#g1-zc-brand { display: flex; align-items: center; gap: 8px; min-width: 0; }
#g1-zc-logo {
  flex: 0 0 auto;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  object-fit: cover;
  display: block;
}
#g1-zc-titles { min-width: 0; }
#g1-zc-titles b {
  display: block;
  font-size: 12px;
  line-height: 1.2;
  color: #f8fafc;
  font-weight: 700;
  letter-spacing: -0.2px;
}
#g1-zc-titles span {
  display: block;
  font-size: 10px;
  color: #94a3b8;
  margin-top: 1px;
}
#g1-zc-toggle {
  background: transparent;
  border: 0;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
  flex: 0 0 auto;
}
#g1-zc-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
#g1-zc-status {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(56, 189, 248, 0.3);
  background: rgba(56, 189, 248, 0.1);
  color: #38bdf8;
  font-size: 11px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
#g1-zc-sku-row, #g1-zc-period-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
#g1-zc-period-row { grid-template-columns: repeat(4, 1fr); }
.g1-zc-chip {
  appearance: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
  border-radius: 8px;
  padding: 7px 0;
  cursor: pointer;
  text-align: center;
  font-size: 11.5px;
  font-weight: 600;
  transition: all 0.15s ease;
}
.g1-zc-chip:hover {
  border-color: rgba(56, 189, 248, 0.4);
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8;
}
.g1-zc-chip.is-on {
  border-color: #38bdf8;
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) inset;
}
.g1-zc-adv { display: none; }
#g1-zc-token-input {
  width: 100%;
  height: 28px;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.3);
  color: #f8fafc;
  font-size: 11px;
  outline: none;
}
#g1-zc-token-input:focus { border-color: #38bdf8; }
#g1-zc-foot { display: flex; gap: 6px; }
#g1-zc-foot button, #g1-zc-foot a {
  flex: 1;
  height: 28px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: #cbd5e1;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
}
#g1-zc-foot button:hover, #g1-zc-foot a:hover {
  background: rgba(56, 189, 248, 0.15);
  border-color: rgba(56, 189, 248, 0.4);
  color: #38bdf8;
}
#g1-zc-pk {
  border-color: rgba(42, 171, 238, 0.4) !important;
  color: #38bdf8 !important;
  background: rgba(42, 171, 238, 0.12) !important;
}
`;

  function injectStyles() {
    if (document.getElementById("g1-zc-style")) return;
    const style = document.createElement("style");
    style.id = "g1-zc-style";
    style.textContent = CSS;
    (document.head || document.documentElement).appendChild(style);
  }

  function refreshPresetUi() {
    const sku = (activePreset && activePreset.skuKey) || "20tb";
    const months = (activePreset && activePreset.months) || 12;
    document.querySelectorAll("#g1-zc-sku-row .g1-zc-chip").forEach((b) => {
      b.classList.toggle("is-on", b.dataset.sku === sku);
    });
    document.querySelectorAll("#g1-zc-period-row .g1-zc-chip").forEach((b) => {
      b.classList.toggle("is-on", Number(b.dataset.months) === months);
    });
    fillTokenInput();
  }

  function fillTokenInput() {
    const tokenInput = document.getElementById("g1-zc-token-input");
    if (!tokenInput) return;
    const preset = activePreset;
    tokenInput.value = preset && preset.token ? preset.token : "";
    tokenInput.placeholder = preset && preset.months === 12 && !preset.hasToken ? `${preset.chip} Paste Token` : "Optional: override token";
  }

  function saveTokenOverride(presetId, raw) {
    const val = String(raw || "").trim();
    CFG.tokenOverrides = CFG.tokenOverrides || {};
    if (val) CFG.tokenOverrides[presetId] = val;
    else delete CFG.tokenOverrides[presetId];
    try {
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ [TOKEN_PREF_KEY]: CFG.tokenOverrides });
      }
    } catch (_) {}
    refreshPresetUi();
  }

  function loadTokenOverrides() {
    try {
      if (typeof chrome === "undefined" || !chrome.storage || !chrome.storage.local) return;
      chrome.storage.local.get([TOKEN_PREF_KEY], (res) => {
        const v = res && res[TOKEN_PREF_KEY];
        if (v && typeof v === "object") {
          CFG.tokenOverrides = v;
          refreshPresetUi();
        }
      });
    } catch (_) {}
  }

  function setStatus(text, isSuccess = false, isError = false) {
    const node = document.getElementById("g1-zc-status");
    if (!node) return;
    node.textContent = text;
    node.title = text;
    node.style.background = isError ? "rgba(239, 68, 68, 0.15)" : isSuccess ? "rgba(34, 197, 94, 0.15)" : "rgba(56, 189, 248, 0.12)";
    node.style.borderColor = isError ? "rgba(239, 68, 68, 0.4)" : isSuccess ? "rgba(34, 197, 94, 0.4)" : "rgba(56, 189, 248, 0.35)";
    node.style.color = isError ? "#f87171" : isSuccess ? "#4ade80" : "#38bdf8";
  }

  function pushCfg() {
    const preset = activePreset;
    const presetId = preset && preset.id;
    const includeYt = true;
    const token = preset && preset.token ? preset.token : "";
    try {
      document.documentElement.setAttribute("data-g1pk-preset", presetId || "");
    } catch (_) {}
    window.postMessage(
      { __g1pk: 1, type: "cfg", presetId, includeYt, token },
      "*"
    );
  }

  function selectPreset(presetId) {
    const preset = findPreset(presetId) || activePreset || PRESETS[0];
    if (!preset) return;
    activePreset = preset;
    refreshPresetUi();
    try {
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ g1ZcSelected: preset.id });
      }
    } catch (_) {}
    if (!preset.hasToken) {
      setStatus("No token available for this tier", false, true);
      return;
    }
    pushCfg();
    setStatus(`Mounted: ${preset.title} · Proceed to checkout`, true, false);
  }

  function fillUsTaxFreeAddress() {
    if (!location.hostname.includes("payments.google.com")) {
      window.open("https://payments.google.com/gp/w/home/settings", "_blank");
      return;
    }
    const inputs = Array.from(document.querySelectorAll("input:not([type='hidden'])")).filter(
      (i) => i.offsetWidth > 0 && i.offsetHeight > 0
    );
    const fillMap = [
      { match: /Name|Cardholder|Card\s*Holder|Nama/i, val: "CARD HOLDER" },
      { match: /Address line 1|Street address|Address|Alamat/i, val: "700 Southwest 5th Avenue" },
      { match: /City|Town|Kota/i, val: "Portland" },
      { match: /ZIP|Postal|Postal\s*code|Kode\s*pos/i, val: "97201" }
    ];
    let filledCount = 0;
    for (const inp of inputs) {
      const label =
        inp.getAttribute("aria-label") ||
        inp.getAttribute("placeholder") ||
        (inp.closest("label") ? inp.closest("label").innerText : "") ||
        "";
      for (const item of fillMap) {
        if (item.match.test(label)) {
          inp.focus();
          inp.value = item.val;
          inp.dispatchEvent(new Event("input", { bubbles: true }));
          inp.dispatchEvent(new Event("change", { bubbles: true }));
          filledCount += 1;
          break;
        }
      }
    }
    setStatus(filledCount > 0 ? `Filled OR 97201 · ${filledCount} fields` : "Expand US payment form first", filledCount > 0, false);
  }

  function el(tag, cssText, text) {
    const node = document.createElement(tag);
    if (cssText) node.style.cssText = cssText;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  const POS_KEY = "g1ZcPanelPos";

  function clampPos(left, top, el) {
    const w = el.offsetWidth || 278;
    const h = el.offsetHeight || 160;
    const maxL = Math.max(8, window.innerWidth - w - 8);
    const maxT = Math.max(8, window.innerHeight - h - 8);
    return {
      left: Math.min(Math.max(8, left), maxL),
      top: Math.min(Math.max(8, top), maxT)
    };
  }

  function applyPos(el, pos) {
    el.style.right = "auto";
    el.style.bottom = "auto";
    el.style.left = pos.left + "px";
    el.style.top = pos.top + "px";
  }

  function savePos(pos) {
    try {
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ [POS_KEY]: pos });
      }
    } catch (_) {}
  }

  function enableDrag(container, headerEl, toggleBtn) {
    try {
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get([POS_KEY], (res) => {
          const p = res && res[POS_KEY];
          if (p && typeof p.left === "number" && typeof p.top === "number") {
            applyPos(container, clampPos(p.left, p.top, container));
          }
        });
      }
    } catch (_) {}

    let dragging = false;
    let moved = false;
    let startX = 0;
    let startY = 0;
    let origL = 0;
    let origT = 0;

    container.addEventListener("dragstart", (e) => e.preventDefault());

    headerEl.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      if (e.target === toggleBtn || (toggleBtn.contains && toggleBtn.contains(e.target))) return;
      const rect = container.getBoundingClientRect();
      applyPos(container, { left: rect.left, top: rect.top });
      dragging = true;
      moved = false;
      startX = e.clientX;
      startY = e.clientY;
      origL = rect.left;
      origT = rect.top;
      try {
        headerEl.setPointerCapture(e.pointerId);
      } catch (_) {}
      container.classList.add("g1-zc-dragging");
    });

    headerEl.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) moved = true;
      applyPos(container, clampPos(origL + dx, origT + dy, container));
    });

    function endDrag() {
      if (!dragging) return;
      dragging = false;
      container.classList.remove("g1-zc-dragging");
      if (moved) {
        const rect = container.getBoundingClientRect();
        savePos({ left: rect.left, top: rect.top });
      }
    }

    headerEl.addEventListener("pointerup", endDrag);
    headerEl.addEventListener("pointercancel", endDrag);

    window.addEventListener("resize", () => {
      if (!container.style.left) return;
      const rect = container.getBoundingClientRect();
      const pos = clampPos(rect.left, rect.top, container);
      applyPos(container, pos);
      savePos(pos);
    });

    return () => {
      const v = moved;
      moved = false;
      return v;
    };
  }

  function mountFloatingPanel() {
    if (!document.body || document.getElementById("g1-zero-cost-floating-panel")) return;
    injectStyles();

    const container = el("div");
    container.id = "g1-zero-cost-floating-panel";

    const headerEl = el("div");
    headerEl.id = "g1-zc-header";
    const brand = el("div");
    brand.id = "g1-zc-brand";
    const logo = document.createElement("img");
    logo.id = "g1-zc-logo";
    logo.alt = "Ultra";
    try {
      logo.src = chrome.runtime.getURL("icons/logo.png");
    } catch (_) {
      logo.src = "";
    }
    brand.appendChild(logo);
    const titles = el("div");
    titles.id = "g1-zc-titles";
    titles.appendChild(el("b", "", "Google One Ultra Injector"));
    titles.appendChild(el("span", "", "t.me/tutormint"));
    brand.appendChild(titles);
    const toggleBtn = el("button", "", "−");
    toggleBtn.id = "g1-zc-toggle";
    toggleBtn.title = "Collapse";
    headerEl.appendChild(brand);
    headerEl.appendChild(toggleBtn);
    container.appendChild(headerEl);

    const bodyEl = el("div");
    bodyEl.id = "g1-zc-body";

    const statusEl = el("div", "", "Select tier, then proceed to checkout");
    statusEl.id = "g1-zc-status";
    bodyEl.appendChild(statusEl);

    const skuRow = el("div");
    skuRow.id = "g1-zc-sku-row";
    [
      ["20tb", "Ultra 20TB"],
      ["30tb", "Ultra 30TB"]
    ].forEach(([key, label]) => {
      const b = el("button", "", label);
      b.className = "g1-zc-chip";
      b.dataset.sku = key;
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        const months = (activePreset && activePreset.months) || 12;
        const next = presetBy(key, months) || presetBy(key, 12);
        if (next) selectPreset(next.id);
      });
      skuRow.appendChild(b);
    });
    bodyEl.appendChild(skuRow);

    const periodRow = el("div");
    periodRow.id = "g1-zc-period-row";
    PERIODS.forEach((m) => {
      const b = el("button", "", m + " Mo");
      b.className = "g1-zc-chip";
      b.dataset.months = String(m);
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        const sku = (activePreset && activePreset.skuKey) || "20tb";
        const next = presetBy(sku, m);
        if (next) selectPreset(next.id);
      });
      periodRow.appendChild(b);
    });
    bodyEl.appendChild(periodRow);

    const tokenInput = document.createElement("input");
    tokenInput.type = "text";
    tokenInput.id = "g1-zc-token-input";
    tokenInput.className = "g1-zc-adv";
    tokenInput.spellcheck = false;
    tokenInput.addEventListener("change", () => saveTokenOverride(activePreset && activePreset.id, tokenInput.value));
    tokenInput.addEventListener("blur", () => saveTokenOverride(activePreset && activePreset.id, tokenInput.value));
    bodyEl.appendChild(tokenInput);

    const foot = el("div");
    foot.id = "g1-zc-foot";
    const usBtn = el("button", "", "🇺🇸 OR 97201");
    usBtn.id = "g1-zc-us-addr-btn";
    usBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      fillUsTaxFreeAddress();
    });
    const pkLink = document.createElement("a");
    pkLink.id = "g1-zc-pk";
    pkLink.href = PK_URL;
    pkLink.target = "_blank";
    pkLink.rel = "noopener noreferrer";
    pkLink.textContent = "TELEGRAM";
    pkLink.addEventListener("click", (e) => e.stopPropagation());
    foot.appendChild(usBtn);
    foot.appendChild(pkLink);
    bodyEl.appendChild(foot);

    container.appendChild(bodyEl);
    document.body.appendChild(container);
    refreshPresetUi();

    const wasMoved = enableDrag(container, headerEl, toggleBtn);

    let collapsed = false;
    function toggleCollapse() {
      collapsed = !collapsed;
      bodyEl.style.display = collapsed ? "none" : "flex";
      toggleBtn.textContent = collapsed ? "+" : "−";
      toggleBtn.title = collapsed ? "Expand" : "Collapse";
      container.classList.toggle("g1-zc-min", collapsed);
    }
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleCollapse();
    });
    headerEl.addEventListener("click", () => {
      if (wasMoved()) return;
      toggleCollapse();
    });
  }

  function loadSelectedPreset() {
    try {
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(["g1ZcSelected"], (res) => {
          const id = res && res.g1ZcSelected;
          const found = id && findPreset(id);
          if (found) {
            activePreset = found;
            refreshPresetUi();
          }
          pushCfg();
        });
      }
    } catch (_) {}
  }

  if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (!msg || !msg.action) return;
      if (msg.action === "SELECT_PRESET" || msg.action === "OPEN_ZERO_COST_MODAL") {
        CFG.includeYt = true;
        const go = () => {
          mountFloatingPanel();
          selectPreset(msg.presetId);
          sendResponse({ ok: true });
        };
        try {
          if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
            chrome.storage.local.get([TOKEN_PREF_KEY], (res) => {
              if (res && res[TOKEN_PREF_KEY] && typeof res[TOKEN_PREF_KEY] === "object") {
                CFG.tokenOverrides = res[TOKEN_PREF_KEY];
              }
              go();
            });
            return true;
          }
        } catch (_) {}
        go();
      } else if (msg.action === "GET_PAGE_STATUS") {
        sendResponse({ ok: true, url: location.href });
      } else if (msg.action === "FILL_US_ADDRESS") {
        fillUsTaxFreeAddress();
        sendResponse({ ok: true });
      }
      return true;
    });
  }

  loadTokenOverrides();
  loadSelectedPreset();
  window.__G1OpenZeroCostModal = selectPreset;
  window.addEventListener("message", (ev) => {
    const d = ev.data;
    if (d && d.__g1pk === 1 && d.type === "state" && d.state && d.state.mounted) {
      setStatus("Injection active ($0.00)", true, false);
    }
    if (d && d.__g1pk === 1 && d.type === "tokens" && d.tokens) {
      try {
        chrome.storage.local.set({ g1CapturedTokensV2: d.tokens });
      } catch (e) {}
      const n = Object.keys(d.tokens).length;
      setStatus("Token Google terdeteksi: " + n, true, false);
    }
  });
  try {
    chrome.storage.local.get(["g1CapturedTokensV2"], (res) => {
      if (res && res.g1CapturedTokensV2) {
        window.postMessage({ __g1pk: 1, type: "tokens", tokens: res.g1CapturedTokensV2 }, "*");
      }
    });
  } catch (e) {}

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      mountFloatingPanel();
      pushCfg();
    });
  } else {
    mountFloatingPanel();
    pushCfg();
  }
  setTimeout(pushCfg, 800);
  setTimeout(pushCfg, 2500);
})();
