/* 页面预注入钩子：
 * 1) 反自动化特征清理（降低被 JS 反爬挑战的概率）
 * 2) 捕获控制台日志 / 未捕获错误 / Promise 拒绝 -> window.__kbx.logs
 *
 * 由控制器通过 Page.addScriptToEvaluateOnNewDocument 在导航前注入，
 * 并在每次连接时补注入当前文档（跨命令自刷新后仍有效）。
 * 幂等：window.__kbx.hooked 为真则直接返回，重复注入无副作用。 */
(() => {
  if (window.__kbx && window.__kbx.hooked) return;
  const box = (window.__kbx = window.__kbx || { logs: [], hooked: true });

  // —— 反自动化特征：抹掉无头/自动化痕迹，避免触发反爬挑战 ——
  try {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    if (!window.chrome) window.chrome = { runtime: {}, loadTimes() {}, csi() {} };
    if (navigator.permissions && navigator.permissions.query) {
      const q = navigator.permissions.query.bind(navigator.permissions);
      navigator.permissions.query = (p) =>
        p && p.name === 'notifications'
          ? Promise.resolve({ state: Notification.permission })
          : q(p);
    }
  } catch (_) {}

  // —— 控制台捕获 ——
  const fmt = (a) => {
    try {
      if (typeof a === 'string') return a;
      if (a instanceof Error) return a.stack || a.message;
      return JSON.stringify(a);
    } catch (_) { return String(a); }
  };
  const push = (level, text) => {
    try {
      box.logs.push({ level, text, t: Date.now() });
      if (box.logs.length > 800) box.logs.shift();
    } catch (_) {}
  };

  ['log', 'info', 'warn', 'error', 'debug'].forEach((lvl) => {
    const orig = console[lvl] ? console[lvl].bind(console) : null;
    console[lvl] = (...args) => {
      push(lvl, args.map(fmt).join(' '));
      if (orig) orig(...args);
    };
  });

  window.addEventListener('error', (e) => {
    push('error', (e.message || 'error') + ' @ ' + (e.filename || '') + ':' + (e.lineno || 0));
  });
  window.addEventListener('unhandledrejection', (e) => {
    const r = e.reason;
    push('error', 'UnhandledRejection: ' + ((r && (r.stack || r.message)) || r));
  });
})();
