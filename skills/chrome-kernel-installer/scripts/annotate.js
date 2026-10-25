/* 组件识别与标注 —— 全类型覆盖（文字 / 标题 / 媒体 / 结构容器 / 各类交互组件）
 *
 * 分层（tier）与识别范围：
 *   interactive  交互组件：a[href] / button / input / select / textarea / label / option /
 *                [role] / [onclick] / [tabindex] / [contenteditable] / [aria-*] /
 *                cursor:pointer / addEventListener 绑定（CDP getEventListeners）/ Web Components
 *   head         标题：h1~h6、[role=heading]
 *   text         文字：p/span/div/li/td/th/dt/dd/blockquote/figcaption/pre/code/… 中
 *                有实际文字的最小语义块（同文本链取最外层，避免父子重复框）
 *   media        媒体：img / picture / svg / canvas / video / audio / iframe / embed / object
 *   region       结构容器：header/nav/main/section/article/aside/footer/form/table/ul/ol/dl/
 *                figure/fieldset/details/dialog 及 [role=region|navigation|main|…]
 *
 * 编号：按 tier 顺序（交互→标题→文字→媒体→结构）分段、段内按视觉位置（上→下、左→右）编号。
 * 写回 data-kbx-n 并缓存 window.__kbxNodes[n]（跨 Shadow DOM 可取用）；叠加彩色边框 + 编号徽标。
 *
 * 由控制器以 Runtime.evaluate(includeCommandLineAPI=true) 执行，幂等。
 * 可选：window.__kbxOpts = { only:[tier|kind...], noRegion:bool, max:N, maxText:N }
 */
(() => {
  try {
    const OID = '__kbx_overlay__';
    const OPT = window.__kbxOpts || {};
    const MAX = Math.min(1200, OPT.max || 900);
    const MAX_TEXT = OPT.maxText || 350;
    const SCAN = 12000;
    const LISTEN = 800;
    const ONLY = (OPT.only || []).map((s) => String(s).toLowerCase().trim()).filter(Boolean);
    const NO_REGION = !!OPT.noRegion;

    /* ---------- 清场（幂等） ---------- */
    const prev = document.getElementById(OID);
    if (prev) prev.remove();
    if (window.__kbxNodes) {
      for (const k in window.__kbxNodes) {
        const el = window.__kbxNodes[k];
        if (el && el.removeAttribute) { el.removeAttribute('data-kbx-n'); el.removeAttribute('data-kbx-m'); }
      }
    }
    window.__kbxNodes = {};

    /* ---------- 1. 收集全部元素（穿透 Shadow DOM） ---------- */
    const all = [];
    const stack = [document];
    while (stack.length && all.length < SCAN) {
      const els = stack.pop().querySelectorAll('*');
      for (let i = 0; i < els.length; i++) {
        if (all.length >= SCAN) break;
        all.push(els[i]);
        if (els[i].shadowRoot) stack.push(els[i].shadowRoot);
      }
    }

    const SKIP = { HTML: 1, BODY: 1, HEAD: 1, SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEMPLATE: 1,
      TITLE: 1, META: 1, LINK: 1, BASE: 1, BR: 1, HR: 1, SOURCE: 1, TRACK: 1, PARAM: 1 };
    const TEXT_TAGS = { P: 1, SPAN: 1, DIV: 1, LI: 1, TD: 1, TH: 1, DT: 1, DD: 1, BLOCKQUOTE: 1,
      FIGCAPTION: 1, LABEL: 1, LEGEND: 1, PRE: 1, CODE: 1, CITE: 1, TIME: 1, ADDRESS: 1,
      CAPTION: 1, MARK: 1, STRONG: 1, EM: 1, B: 1, I: 1, U: 1, S: 1, SMALL: 1, ABBR: 1,
      SUB: 1, SUP: 1, Q: 1, VAR: 1, KBD: 1, SAMP: 1, OUTPUT: 1, SUMMARY: 1, A: 1, BUTTON: 1 };
    const MEDIA_TAGS = { IMG: 1, PICTURE: 1, SVG: 1, CANVAS: 1, VIDEO: 1, AUDIO: 1, IFRAME: 1,
      EMBED: 1, OBJECT: 1 };
    const REGION_TAGS = { HEADER: 1, NAV: 1, MAIN: 1, SECTION: 1, ARTICLE: 1, ASIDE: 1,
      FOOTER: 1, FORM: 1, TABLE: 1, UL: 1, OL: 1, DL: 1, FIGURE: 1, FIELDSET: 1, DETAILS: 1, DIALOG: 1 };
    const REGION_ROLES = { region: 1, navigation: 1, main: 1, banner: 1, contentinfo: 1,
      complementary: 1, search: 1, tabpanel: 1, dialog: 1, list: 1, table: 1, form: 1, group: 1 };

    /* ---------- 2. 几何与可见性（只算一次） ---------- */
    const rects = new Map();
    for (const el of all) rects.set(el, el.getBoundingClientRect());
    const vpArea = Math.max(1, window.innerWidth * window.innerHeight);
    const rectOK = (el) => { const r = rects.get(el); return !!r && r.width >= 3 && r.height >= 3; };
    const visCache = new Map();
    const isVisible = (el) => {
      if (!rectOK(el)) return false;
      if (visCache.has(el)) return visCache.get(el);
      const cs = getComputedStyle(el);
      const v = cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) !== 0;
      visCache.set(el, v);
      return v;
    };
    const isBig = (el) => { const r = rects.get(el); return !!r && r.width * r.height > vpArea * 0.5; };

    /* ---------- 3. 交互组件 ---------- */
    const SEL = ['a[href]', 'area[href]', 'button', 'input:not([type=hidden])', 'select', 'textarea',
      'summary', 'details', 'label', 'option', 'output', 'progress', 'meter',
      '[role]', '[onclick]', '[onmousedown]', '[onpointerdown]', '[ontouchstart]',
      '[tabindex]', '[contenteditable="true"]', '[contenteditable=""]', '[draggable="true"]',
      '[aria-haspopup]', '[aria-expanded]', '[aria-controls]', '[data-action]', '[data-click]',
      'audio[controls]', 'video[controls]'].join(',');
    const selMatch = (el) => { try { return el.matches(SEL); } catch (_) { return false; } };

    const EV = ['click', 'mousedown', 'pointerdown', 'touchstart'];
    const canIntrospect = (typeof getEventListeners === 'function');
    const listened = new WeakSet();
    const hasListener = (el) => {
      if (listened.has(el)) return true;
      if (!canIntrospect) return false;
      try {
        const m = getEventListeners(el) || {};
        for (const t of EV) { if (m[t] && m[t].length) { listened.add(el); return true; } }
      } catch (_) {}
      return false;
    };

    const kindOfInteractive = (el) => {
      const t = el.tagName.toLowerCase();
      if (t === 'a') return 'link';
      if (t === 'button' || el.getAttribute('role') === 'button') return 'button';
      if (['input', 'select', 'textarea', 'option', 'label', 'output', 'progress', 'meter'].indexOf(t) > -1) return 'field';
      if (t.indexOf('-') > -1) return 'custom:' + t;
      if (el.getAttribute('contenteditable') !== null) return 'editable';
      if (listened.has(el)) return 'clickable';
      const role = el.getAttribute('role');
      if (role) return 'role:' + role;
      return 'clickable';
    };

    const picked = [];
    const used = new Set();
    const push = (el, kind, tier) => {
      if (used.has(el)) return false;
      used.add(el);
      el.setAttribute('data-kbx-m', '1');
      picked.push({ el, kind, tier });
      return true;
    };
    const hasPickedAncestor = (el) => {
      let p = el.parentElement;
      while (p) { if (used.has(p) && !isBig(p)) return true; p = p.parentElement; }
      return false;
    };
    const hasPickedInside = (el) => {
      if (!el.children || !el.children.length) return false;
      if (el.querySelector) { try { return !!el.querySelector('[data-kbx-m]'); } catch (_) {} }
      return false;
    };

    for (const el of all) {
      if (SKIP[el.tagName] || !isVisible(el) || hasPickedAncestor(el)) continue;
      if (selMatch(el) || el.tagName.indexOf('-') > -1) { push(el, kindOfInteractive(el), 'interactive'); continue; }
      const cs = getComputedStyle(el);
      if (cs.cursor === 'pointer') { push(el, 'clickable', 'interactive'); continue; }
      if (canIntrospect && hasListener(el)) push(el, 'clickable', 'interactive');
    }

    /* ---------- 4. 标题 ---------- */
    for (const el of all) {
      if (SKIP[el.tagName] || used.has(el) || !isVisible(el) || hasPickedAncestor(el)) continue;
      const role = el.getAttribute ? el.getAttribute('role') : null;
      if (/^H[1-6]$/.test(el.tagName) || role === 'heading') push(el, 'heading', 'head');
    }

    /* ---------- 5. 文字（同文本链只留最外层，避免父子重复） ---------- */
    const txtOf = (el) => (el.textContent || '').replace(/\s+/g, ' ').trim();
    const directText = (el) => {
      let s = '';
      const cn = el.childNodes || [];
      for (let i = 0; i < cn.length; i++) { if (cn[i].nodeType === 3) s += cn[i].nodeValue; }
      return s.replace(/\s+/g, ' ').trim();
    };
    let textN = 0;
    for (const el of all) {
      if (textN >= MAX_TEXT) break;
      const tag = el.tagName;
      if (SKIP[tag] || used.has(el) || !TEXT_TAGS[tag] || !isVisible(el)) continue;
      const T = txtOf(el);
      if (T.length < 2 || T.length > 600) continue;
      const p = el.parentElement;
      if (p && !SKIP[p.tagName] && TEXT_TAGS[p.tagName] && txtOf(p) === T) continue;  // 父级同为文字候选且同文本 → 只留最外层
      if (hasPickedAncestor(el)) continue;
      // 内部已有编号组件时：只有「自身没有文字」才跳过（如纯按钮外壳）；段落含行内链接仍应编号
      if (hasPickedInside(el) && directText(el).length < 2) continue;
      if (push(el, 'text', 'text')) textN++;
    }

    /* ---------- 6. 媒体 ---------- */
    for (const el of all) {
      if (SKIP[el.tagName] || used.has(el) || !isVisible(el) || hasPickedAncestor(el)) continue;
      if (MEDIA_TAGS[el.tagName]) push(el, 'media', 'media');
    }

    /* ---------- 7. 结构容器（只标出含已选内容的容器，避免全页大框） ---------- */
    if (!NO_REGION) {
      for (const el of all) {
        if (SKIP[el.tagName] || used.has(el) || !isVisible(el)) continue;
        const role = el.getAttribute ? el.getAttribute('role') : null;
        if (!REGION_TAGS[el.tagName] && !(role && REGION_ROLES[role])) continue;
        if (!hasPickedInside(el)) continue;
        push(el, 'region', 'region');
      }
    }

    /* ---------- 8. 分段 + 分层配额 + 段内按视觉位置排序 + 过滤 ---------- */
    const TIERS = ['interactive', 'head', 'text', 'media', 'region'];
    // 分层配额：防止某一类（尤其是交互）把名额吃光导致其余类型全被截断
    const CAP = { interactive: 360, head: 80, text: 240, media: 90, region: 70 };
    const scale = OPT.max ? (OPT.max / 840) : 1;
    const tierAllowed = (tier, kind) => {
      if (!ONLY.length) return true;
      const k = String(kind).toLowerCase();
      return ONLY.indexOf(tier) > -1 || ONLY.indexOf(k) > -1 || ONLY.indexOf(k.split(':')[0]) > -1;
    };
    const byPos = (a, b) => {
      const ra = rects.get(a.el), rb = rects.get(b.el);
      return (ra.top - rb.top) || (ra.left - rb.left);
    };
    let list = [];
    for (const t of TIERS) {
      let seg = picked.filter((x) => x.tier === t && tierAllowed(t, x.kind));
      seg.sort(byPos);
      const cap = Math.max(8, Math.round(CAP[t] * scale));
      if (seg.length > cap) seg = seg.slice(0, cap);
      list = list.concat(seg);
    }
    const truncated = list.length < picked.length;
    if (list.length > MAX) list = list.slice(0, MAX);

    /* ---------- 9. 绘制 ---------- */
    const COLOR = { link: '#dc2626', button: '#ea580c', field: '#0284c7', clickable: '#16a34a',
      editable: '#db2777', heading: '#111827', text: '#64748b', media: '#0891b2', region: '#94a3b8' };
    const colorOf = (kind) => kind.indexOf('custom') === 0 ? '#0d9488'
      : kind.indexOf('role') === 0 ? '#d97706' : (COLOR[kind] || '#16a34a');

    const overlay = document.createElement('div');
    overlay.id = OID;
    Object.assign(overlay.style, { position: 'absolute', left: '0', top: '0', width: '0', height: '0',
      zIndex: '2147483647', pointerEvents: 'none' });
    document.documentElement.appendChild(overlay);

    const sx = window.scrollX, sy = window.scrollY;
    const items = [];
    const counts = {};
    let n = 0;

    for (const it of list) {
      n++;
      const el = it.el, kind = it.kind, tier = it.tier;
      el.setAttribute('data-kbx-n', String(n));
      window.__kbxNodes[n] = el;

      const r = el.getBoundingClientRect();
      const L = Math.round(r.left + sx), T = Math.round(r.top + sy);
      const W = Math.round(r.width), H = Math.round(r.height);
      const color = colorOf(kind);
      const faint = tier === 'region' || tier === 'text';

      const box = document.createElement('div');
      Object.assign(box.style, {
        position: 'absolute', left: L + 'px', top: T + 'px', width: W + 'px', height: H + 'px',
        border: (tier === 'region' ? '1px dashed ' : (tier === 'text' ? '1.5px solid ' : '2px solid ')) + color,
        boxSizing: 'border-box', background: faint ? 'transparent' : 'rgba(0,0,0,0.03)',
      });
      overlay.appendChild(box);

      const badge = document.createElement('div');
      badge.textContent = String(n);
      const small = tier === 'text' || tier === 'region';
      Object.assign(badge.style, {
        position: 'absolute', left: (L - 2) + 'px', top: Math.max(T - 16, sy) + 'px',
        background: color, color: '#fff', padding: small ? '0 4px' : '0 5px', borderRadius: '3px',
        font: (small ? '600 10px/15px ' : '600 11px/16px ') +
          '-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif',
        whiteSpace: 'nowrap', opacity: tier === 'region' ? '0.85' : '1',
      });
      overlay.appendChild(badge);

      counts[tier] = (counts[tier] || 0) + 1;
      const label = (el.getAttribute('aria-label') || el.getAttribute('title') ||
        el.getAttribute('placeholder') || el.getAttribute('alt') || txtOf(el) || '').slice(0, 48);
      items.push({ n, kind, tier, tag: el.tagName.toLowerCase(),
        role: (el.getAttribute && el.getAttribute('role')) || '', text: label, w: W, h: H });
    }

    for (const it of picked) { try { it.el.removeAttribute('data-kbx-m'); } catch (_) {} }

    return JSON.stringify({ ok: true, count: items.length, counts, scanned: all.length,
      truncated: truncated || all.length >= SCAN, items });
  } catch (e) {
    return JSON.stringify({ ok: false, error: String((e && e.message) || e) });
  }
})()
