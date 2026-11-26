/* MAIN world: hook Play checkout like google_pro_6_12_24. Do not click the page. */
(() => {
  if (window.__G1_PK_HOOKED) return;
  window.__G1_PK_HOOKED = true;

  const PREFIX = "subs:com.google.android.apps.subscriptions.red:";
  const YT_SKU = "g1.youtube_premium_individual_add_on";
  const TOKENS = {
    ultra20tb_12m: "AYrTWi65Jbm3KRubLXLLA3Re29zKibSnRbvAJEPfxEIVs/d57w8vEhsU7hSkSAfGyjZH8B7/5aj5UTlidbsEwUH8aPN2RTA6pKiltA==",
    ultra20tb_6m: "AYrTWi6lMoHTB2cVb1VC+i3DHvfp1Q9VGblBeF9b1+O8e5+kNws87YdcgNEUJOuHJDp/mitKx1KmBCYurbXIubpM50o4AqgcBB3gMGk85mQ=",
    ultra20tb_3m: "AYrTWi6sldhCH+REVXA3inXWB+LuAvtnSPYHMvhbqKmv3TRdQPhoynS4ZTLxPEiaNGnaAmDTqliYzrLwJ3Aq49Vi9ktjNP+xcTF5R9Yn1MQ=",
    ultra20tb_1m: "AYrTWi5QWD5gc0ZxMJHAAUvXbYRFJgI6w5vnF9PKIFg1DFQML36iijrmN5Vum7u9ty2JnHvt9JFLgsfGKwScJcfZaKttqn0hSX4Fnpdn9No=",
    ultra30tb_12m: "AYrTWi51Eo3HG0tq1J6SYr4u3FDCCxb6xSEEWHskaFwSA7Vn4y+Lfqlfy+Lbkx2T/xPi4uCRB71ZIn+weD0kHZsMgS6ogUiZ8hG9SA==",
    ultra30tb_6m: "AYrTWi5hXUkLGa1e7nBstxl4Z3cUcYWzHF38Xks304ClJj8yVxeFCwDg/pJg82w8w9xHsk8Wl5WNhYKk26LB9besC0kYJ6AvlXapJA==",
    ultra30tb_3m: "AYrTWi4iJ8AzqZkDL53g/dcS7g93mZgiEBJANI0lOucBiUITWEYqCiwLsIXY7P62rmMWb+wFR4WW9tQlFrskR67oCzzwVHghPSs29w==",
    ultra30tb_1m: "AYrTWi7nBQ2Zn0z4s+QJOwg9kQRwH3+z+HXpzRqw9IIU4/C48vPvjH32Bub8SHrWq3YX+yI4g1wJgviYiLCobJNqc9DqRd9WZnDdaQ==",
    ultra20tb_1m_yt: "AYrTWi5QWD5gc0ZxMJHAAUvXbYRFJgI6w5vnF9PKIFg1DFQML36iijrmN5Vum7u9ty2JnHvt9JFLgsfGKwScJcfZaKttqn0hSX4Fnpdn9No=",
    ultra30tb_1m_yt: "AYrTWi7nBQ2Zn0z4s+QJOwg9kQRwH3+z+HXpzRqw9IIU4/C48vPvjH32Bub8SHrWq3YX+yI4g1wJgviYiLCobJNqc9DqRd9WZnDdaQ==",
    yt: "AVbCH/eW4Nfp8KBl0zlm7x9PhaiCvpnqwUuL2D8NFPBQgmM9+HuYS1h2xH5lLWU/BsBj775LK5GqK8UHKqoSzhDDz+PqP3paNesqLU0r9i6XCrYa"
  };
  const SKUS = {
    ultra20tb_12m: "g1.play.20tb",
    ultra20tb_6m: "g1.play.20tb",
    ultra20tb_3m: "g1.play.20tb",
    ultra20tb_1m: "g1.play.20tb",
    ultra30tb_12m: "g1.play.ai.pro",
    ultra30tb_6m: "g1.play.ai.pro",
    ultra30tb_3m: "g1.play.ai.pro",
    ultra30tb_1m: "g1.play.ai.pro",
    ultra20tb_1m_yt: "g1.play.20tb",
    ultra30tb_1m_yt: "g1.play.ai.pro"
  };

  let currentTest = null;
  let subId = null;
  const CAPTURED = {};
  const PRO_OFFERS = ["12months-eft", "6months-eft", "6months-eft-2", "6months-eft-ss-2026"];

  function captureTokens(text) {
    if (typeof text !== "string" || text.length < 20) return;
    const found = text.match(/AYrTWi[A-Za-z0-9+\/=_-]{80,}/g);
    if (!found) return;
    const low = text.toLowerCase();
    let key = PRO_OFFERS.find((o) => low.includes(o.toLowerCase()));
    if (!key) key = "auto";
    if (!CAPTURED[key] || CAPTURED[key].length < found[0].length) CAPTURED[key] = found[0];
    window.__G1_TOKENS = CAPTURED;
    try {
      window.postMessage({ __g1pk: 1, type: "tokens", tokens: CAPTURED }, "*");
    } catch (e) {}
  }

  const origXhrOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (...args) {
    this.addEventListener("load", function () {
      try { captureTokens(this.responseText); } catch (e) {}
    });
    return origXhrOpen.apply(this, args);
  };
  const origFetch = window.fetch;
  if (typeof origFetch === "function") {
    window.fetch = async function (...args) {
      const res = await origFetch.apply(this, args);
      try {
        const clone = res.clone();
        clone.text().then(captureTokens).catch(() => {});
      } catch (e) {}
      return res;
    };
  }

  function makeItem(skuShort, token) {
    return [[PREFIX + skuShort, 21], null, null, null, 1, [token]];
  }

  const PRO_SKU = "g1.play.ai.pro";
  const PRO_OFFER = {
    pro12: "12months-eft", pro6: "6months-eft",
    pro6b: "6months-eft-2", pro6c: "6months-eft-ss-2026",
  };

  function makeCfg(presetId, includeYt, tokenOverride) {
    const isPro = String(presetId || "").startsWith("pro");
    const sku = isPro ? PRO_SKU : SKUS[presetId];
    const offer = isPro ? PRO_OFFER[presetId] : "";
    const tok = (tokenOverride && String(tokenOverride).trim()) ||
      (isPro ? CAPTURED[offer] || "" : TOKENS[presetId]);
    if (!sku) return null;
    if (!tok) {
      // Mode probe: minta Google mengirim offer untuk SKU ini, lalu capture token dari respons.
      return { name: "g1pk_" + presetId, presetId, full_items: null, probeSku: sku,
               offer: offer || "", ear8: null, includeYt: true };
    }
    const full_items = [makeItem(sku, tok)];
    if (!isPro) full_items.push(makeItem(YT_SKU, TOKENS.yt));
    return { name: "g1pk_" + presetId, presetId, full_items, probeSku: sku,
             offer: offer || "", ear8: null, includeYt: true };
  }

  function patchNode(node) {
    if (!Array.isArray(node) || !currentTest || !Array.isArray(currentTest.full_items)) return false;
    let patched = false;
    if (node.length > 12 && Array.isArray(node[12])) {
      if (Array.isArray(node[7]) && Array.isArray(node[7][5]) && node[7][5].length > 0) subId = node[7][5][0];
      node[12] = currentTest.full_items;
      const mode = (currentTest.ear8 && currentTest.ear8[1]) || 5;
      if (currentTest.ear8) node[7] = currentTest.ear8;
      else if (Array.isArray(node[7]) && Array.isArray(node[7][5]) && node[7][5].length > 0) node[7][1] = mode;
      else if (subId) node[7] = [null, mode, null, null, null, [subId]];
      patched = true;
    }
    if (node.length > 10 && Array.isArray(node[10]) && Array.isArray(node[10][0])) {
      node[10] = [currentTest.full_items];
      if (Array.isArray(node[2]) && Array.isArray(node[2][2]) && Array.isArray(node[2][2][8])) {
        node[2][2][8] = [currentTest.full_items];
      }
      if (currentTest.ear8) node[6] = currentTest.ear8;
      patched = true;
    }
    return patched;
  }

  function rewriteFreq(bodyStr) {
    if (typeof bodyStr !== "string" || !bodyStr.includes("f.req=") || !currentTest) return bodyStr;
    try {
      const parts = bodyStr.split("&");
      for (let i = 0; i < parts.length; i++) {
        if (parts[i].startsWith("f.req=")) {
          const raw = decodeURIComponent(parts[i].slice(6).replace(/\\+/g, " "));
          let rawText = raw;
          let changed = false;
          if (!currentTest.full_items && currentTest.probeSku) {
            rawText = raw.split("g1.play.ai.pro").join(currentTest.probeSku)
                         .split("g1.play.20tb").join(currentTest.probeSku);
            changed = rawText !== raw;
          }
          const outer = JSON.parse(rawText);
          if (Array.isArray(outer)) {
            for (const group of outer) {
              if (!Array.isArray(group)) continue;
              for (const call of group) {
                if (Array.isArray(call) && call[0] === "Ngbm" && typeof call[1] === "string") {
                  const payload = JSON.parse(call[1]);
                  if (Array.isArray(payload)) {
                    if (patchNode(payload[0])) changed = true;
                    if (patchNode(payload[1])) changed = true;
                  }
                  if (changed) call[1] = JSON.stringify(payload);
                }
              }
            }
          }
          if (changed) {
            parts[i] = "f.req=" + encodeURIComponent(JSON.stringify(outer));
            return parts.join("&");
          }
        }
      }
    } catch (e) {}
    return bodyStr;
  }

  const origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function (body) {
    try {
      if (typeof body === "string" && body.includes("Ngbm")) body = rewriteFreq(body);
    } catch (e) {}
    return origSend.call(this, body);
  };

  function rewriteUrl(val) {
    let s = String(val || "");
    if (!s.includes("/eacquire/multiline") || !currentTest) return val;
    if (!currentTest.full_items && currentTest.probeSku) {
      s = s.split("g1.play.ai.pro").join(currentTest.probeSku)
          .split("g1.play.20tb").join(currentTest.probeSku);
    }
    try {
      const u = new URL(s, location.origin);
      const earStr = u.searchParams.get("ear");
      if (!earStr) return val;
      const ear = JSON.parse(earStr);
      if (Array.isArray(ear[8]) && Array.isArray(ear[8][5]) && ear[8][5].length > 0) subId = ear[8][5][0];
      if (Array.isArray(ear[13]) && Array.isArray(currentTest.full_items)) ear[13][0] = currentTest.full_items;
      if (Array.isArray(ear[4]) && typeof ear[4][0] === "string" && Array.isArray(currentTest.full_items)) {
        try {
          const inner4 = JSON.parse(atob(ear[4][0]));
          if (Array.isArray(inner4) && inner4.length > 8) {
            inner4[8] = [currentTest.full_items];
            ear[4][0] = btoa(JSON.stringify(inner4));
          }
        } catch (e4) {}
      }
      const mode = (currentTest.ear8 && currentTest.ear8[1]) || 5;
      if (currentTest.ear8) ear[8] = currentTest.ear8;
      else if (Array.isArray(ear[8]) && Array.isArray(ear[8][5]) && ear[8][5].length > 0) ear[8][1] = mode;
      else if (subId) ear[8] = [null, mode, null, null, null, [subId]];
      ear[24] = null;
      u.searchParams.set("ear", JSON.stringify(ear));
      return u.toString();
    } catch (e) {
      return val;
    }
  }

  if (window.TrustedTypePolicy && TrustedTypePolicy.prototype.createScriptURL) {
    const origCreate = TrustedTypePolicy.prototype.createScriptURL;
    TrustedTypePolicy.prototype.createScriptURL = function (input, ...args) {
      return origCreate.call(this, rewriteUrl(input), ...args);
    };
  }

  const srcDesc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, "src");
  if (srcDesc && srcDesc.set) {
    Object.defineProperty(HTMLIFrameElement.prototype, "src", {
      ...srcDesc,
      set(v) {
        if (typeof v === "string") v = rewriteUrl(v);
        return srcDesc.set.call(this, v);
      }
    });
  }
  const origSetAttr = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function (name, val) {
    if (this instanceof HTMLIFrameElement && String(name).toLowerCase() === "src") val = rewriteUrl(String(val));
    return origSetAttr.call(this, name, val);
  };

  function applyCfg(presetId, includeYt, tokenOverride) {
    const cfg = makeCfg(presetId, includeYt, tokenOverride);
    currentTest = cfg;
    window.__G1_PK_STATE = { presetId: presetId || "", mounted: !!currentTest, includeYt: includeYt !== false };
    try {
      window.postMessage({ __g1pk: 1, type: "state", state: window.__G1_PK_STATE }, "*");
    } catch (e) {}
  }

  window.addEventListener("message", (ev) => {
    const d = ev.data;
    if (!d || d.__g1pk !== 1) return;
    if (d.type === "tokens" && d.tokens) {
      Object.assign(CAPTURED, d.tokens);
      window.__G1_TOKENS = CAPTURED;
      if (currentTest) applyCfg(currentTest.presetId, true, "");
    }
    if (d.type === "cfg") applyCfg(d.presetId, d.includeYt, d.token);
    if (d.type === "ping") {
      try {
        window.postMessage({ __g1pk: 1, type: "state", state: window.__G1_PK_STATE || { presetId: "", mounted: false } }, "*");
      } catch (e) {}
    }
  });

  const attr = document.documentElement.getAttribute("data-g1pk-preset");
  applyCfg(attr || "ultra20tb_12m", true, "");
})();
