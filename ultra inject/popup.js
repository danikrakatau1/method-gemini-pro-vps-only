/* popup.js — Google One Ultra Injector Controller */
(() => {
  const PRESETS = window.G1_ZERO_COST_PRESETS || [];
  const ALIAS = window.G1_PK_ALIAS || {};

  const masterStatus = document.getElementById("master-status");
  const masterStatusText = document.getElementById("master-status-text");
  const hudMainStatus = document.getElementById("hud-main-status");
  const hudSubStatus = document.getElementById("hud-sub-status");
  const copyZipBtn = document.getElementById("copy-zip-btn");
  const openPlansBtn = document.getElementById("open-plans-btn");
  const autofillAddressBtn = document.getElementById("autofill-address-btn");
  const openPlaySubsBtn = document.getElementById("open-play-subs-btn");
  const tsToggle = document.getElementById("troubleshoot-toggle");
  const tsContent = document.getElementById("troubleshoot-content");

  let skuKey = "20tb";
  let months = 12;

  function findPreset(id) {
    const real = ALIAS[id] || id;
    return PRESETS.find((p) => p.id === real) || null;
  }

  function currentPreset() {
    return PRESETS.find((p) => p.skuKey === skuKey && p.months === months) || PRESETS[0];
  }

  function paint() {
    // Update SKU cards
    document.querySelectorAll(".sku-card").forEach((card) => {
      const radio = card.querySelector('input[type="radio"]');
      const isSelected = card.dataset.sku === skuKey;
      if (radio) radio.checked = isSelected;
      card.classList.toggle("selected", isSelected);
    });

    // Update Period cards
    document.querySelectorAll(".period-card").forEach((card) => {
      const radio = card.querySelector('input[type="radio"]');
      const isSelected = Number(card.dataset.months) === months;
      if (radio) radio.checked = isSelected;
      card.classList.toggle("selected", isSelected);
    });

    // Update HUD
    const p = currentPreset();
    if (hudMainStatus && p) {
      hudMainStatus.innerHTML = `<span style="color:#4ade80;">● Mounted:</span> ${p.title} (+ YouTube)`;
    }
    if (hudSubStatus) {
      hudSubStatus.textContent = "Ready! Open one.google.com/plans & subscribe with $0.00 trial.";
    }
    if (masterStatus && masterStatusText) {
      masterStatus.className = "status-badge ok";
      masterStatusText.textContent = "ACTIVE";
    }
  }

  function selectCurrent() {
    const p = currentPreset();
    if (!p) return;
    chrome.storage.local.set({ g1ZcSelected: p.id });

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs && tabs[0];
      if (tab && tab.id && (tab.url || "").includes("one.google.com")) {
        chrome.tabs.sendMessage(tab.id, { action: "SELECT_PRESET", presetId: p.id }, () => {
          void chrome.runtime.lastError;
          if (hudSubStatus) {
            hudSubStatus.innerHTML = `<span style="color:#4ade80;">✓ Injected into active Google One tab.</span>`;
          }
        });
      }
    });
    paint();
  }

  // SKU Card Clicks
  document.querySelectorAll(".sku-card").forEach((card) => {
    card.addEventListener("click", () => {
      skuKey = card.dataset.sku;
      selectCurrent();
    });
  });

  // Period Card Clicks
  document.querySelectorAll(".period-card").forEach((card) => {
    card.addEventListener("click", () => {
      months = Number(card.dataset.months);
      selectCurrent();
    });
  });

  // Quick Action: Open Google One Plans
  if (openPlansBtn) {
    openPlansBtn.addEventListener("click", () => {
      chrome.tabs.create({ url: "https://one.google.com/plans" });
    });
  }

  // Quick Action: Auto-fill US Address on payments.google.com
  if (autofillAddressBtn) {
    autofillAddressBtn.addEventListener("click", () => {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const tab = tabs && tabs[0];
        if (tab && tab.id && (tab.url || "").includes("payments.google.com")) {
          chrome.tabs.sendMessage(tab.id, { action: "FILL_US_ADDRESS" }, () => {
            void chrome.runtime.lastError;
            if (hudSubStatus) {
              hudSubStatus.innerHTML = `<span style="color:#4ade80;">✓ US Oregon 97201 address auto-filled!</span>`;
            }
          });
        } else {
          chrome.tabs.create({ url: "https://payments.google.com/gp/w/home/settings" });
        }
      });
    });
  }

  // Quick Action: Manage Play Subscriptions (Cancel Auto-Renew)
  if (openPlaySubsBtn) {
    openPlaySubsBtn.addEventListener("click", () => {
      chrome.tabs.create({ url: "https://play.google.com/store/account/subscriptions" });
    });
  }

  // Copy US ZIP
  if (copyZipBtn) {
    copyZipBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText("97201").then(() => {
        copyZipBtn.classList.add("copied");
        const originalHtml = copyZipBtn.innerHTML;
        copyZipBtn.innerHTML = '<span>✓ Copied 97201</span>';
        setTimeout(() => {
          copyZipBtn.classList.remove("copied");
          copyZipBtn.innerHTML = originalHtml;
        }, 1500);
      }).catch(() => {});
    });
  }

  // Troubleshooting Drawer
  if (tsToggle && tsContent) {
    tsToggle.addEventListener("click", () => {
      const isExpanded = tsContent.classList.toggle("open");
      tsToggle.classList.toggle("active", isExpanded);
    });
  }

  // Load Saved Selection
  chrome.storage.local.get(["g1ZcSelected"], (res) => {
    const saved = findPreset(res && res.g1ZcSelected);
    if (saved) {
      skuKey = saved.skuKey;
      months = saved.months;
    }
    paint();
    selectCurrent();
  });
})();
