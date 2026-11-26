/* Google One Ultra Injector — Checkout Price Guard
 * Role: Reads real terms inside the Play checkout iframe. Green = Free trial ($0.00), Red = Charged.
 */
(() => {
  if (window.__G1_PK_GUARD || window.top === window) return; // Only runs in child iframe
  window.__G1_PK_GUARD = true;

  const FREE_WORDS = [
    "free trial", "start your free trial", "trial", "0.00", "$0.00", "us$0.00", "us$0,00", "$0,00", "0,00", "rp 0", "rp0", "€0.00",
    "won't be charged", "free for", "12 months free", "6 months free", "3 months free", "1 month free"
  ];
  const PAID_WORDS = [
    "/mo after", "/month after", "per month after", "pay now", "charged today",
    "due today", "/bln setelahnya", "/bulan setelahnya"
  ];

  let bar = null;
  let dotEl = null;
  let textEl = null;
  let lastKind = "";
  let lastText = "";
  let debounceTimer = null;

  function paint(kind, text) {
    if (!document.body) return;
    if (kind === lastKind && text === lastText && bar && bar.parentNode) return;
    lastKind = kind;
    lastText = text;

    if (!bar || !bar.parentNode) {
      bar = document.createElement("div");
      bar.id = "__g1_guard_bar";
      bar.style.cssText = "position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:2147483647;" +
        "display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:8px 16px;border-radius:9999px;" +
        "background:rgba(10,15,26,0.94);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);" +
        "font:600 12px/1.4 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;" +
        "box-sizing:border-box;max-width:92vw;pointer-events:none;transition:all 0.25s cubic-bezier(0.16,1,0.3,1);";

      dotEl = document.createElement("span");
      dotEl.style.cssText = "width:7px;height:7px;border-radius:50%;flex-shrink:0;";
      bar.appendChild(dotEl);

      textEl = document.createElement("span");
      textEl.style.cssText = "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:82vw;";
      bar.appendChild(textEl);

      document.body.appendChild(bar);
    }

    if (kind === "ok") {
      bar.style.border = "1px solid rgba(34,197,94,0.5)";
      bar.style.boxShadow = "0 8px 30px rgba(0,0,0,0.6), 0 0 16px rgba(34,197,94,0.3)";
      dotEl.style.background = "#22c55e";
      dotEl.style.boxShadow = "0 0 8px #22c55e";
      textEl.style.color = "#ecfdf5";
    } else if (kind === "bad") {
      bar.style.border = "1px solid rgba(239,68,68,0.55)";
      bar.style.boxShadow = "0 8px 30px rgba(0,0,0,0.6), 0 0 16px rgba(239,68,68,0.3)";
      dotEl.style.background = "#ef4444";
      dotEl.style.boxShadow = "0 0 8px #ef4444";
      textEl.style.color = "#fee2e2";
    } else {
      bar.style.border = "1px solid rgba(245,158,11,0.45)";
      bar.style.boxShadow = "0 8px 30px rgba(0,0,0,0.6), 0 0 14px rgba(245,158,11,0.25)";
      dotEl.style.background = "#f59e0b";
      dotEl.style.boxShadow = "0 0 8px #f59e0b";
      textEl.style.color = "#fef3c7";
    }

    textEl.textContent = text;
  }

  function judge() {
    let t = "";
    try {
      t = (document.body && document.body.innerText || "").toLowerCase();
    } catch (e) {
      return;
    }
    if (!t || t.length < 5) return;
    const free = FREE_WORDS.some((w) => t.includes(w.toLowerCase()));
    const paid = PAID_WORDS.some((w) => t.includes(w.toLowerCase()));

    if (free && !paid) {
      paint("ok", "✅ Free trial detected ($0.00) — Safe to subscribe in this popup");
    } else if (paid && !free) {
      paint("bad", "❌ Free trial not detected! Do not subscribe — may charge money");
    } else if (free && paid) {
      paint("warn", "⚠️ Mixed terms detected — Please manually verify amount is $0.00");
    } else {
      paint("warn", "⚡ Verifying price terms ($0.00 check in progress...)");
    }
  }

  function scheduleJudge() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(judge, 400);
  }

  setTimeout(judge, 800);
  setTimeout(judge, 2000);
  setTimeout(judge, 5000);

  try {
    const mo = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.target && (m.target.id === "__g1_guard_bar" || (m.target.closest && m.target.closest("#__g1_guard_bar")))) {
          continue;
        }
        scheduleJudge();
        break;
      }
    });
    if (document.body) {
      mo.observe(document.body, { childList: true, subtree: true, characterData: true });
    } else {
      document.addEventListener("DOMContentLoaded", () => {
        if (document.body) mo.observe(document.body, { childList: true, subtree: true, characterData: true });
      });
    }
  } catch (e) {}
})();
