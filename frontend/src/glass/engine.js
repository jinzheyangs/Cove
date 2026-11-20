/* Cove · 液态玻璃引擎
 *
 * 它只干三件事：
 *   1. 两遍 WebGL —— 背景画进 FBO，玻璃采样这张 FBO 做折射；
 *   2. 读取 DOM 的 getBoundingClientRect，把每块玻璃喂给着色器（uRect / uRad）；
 *   3. 维护面板的开合几何与手势（上滑打开 / 下拉关闭）。
 *
 * 它不拥有界面内容：视图切换、面板里画什么，全部由 Vue 决定，
 * 通过 hooks 回传（onViewChange / onOpenSheet / onDismiss）。
 */

import { VS, FS_BG, FS_GLASS } from './shaders.js';

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const smoothstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

// 滚动内容在顶栏/底栏下方溶解（写在样式表里会被部分浏览器丢弃，这里落到内联样式）
const VIEW_MASK = 'linear-gradient(180deg,transparent 52px,#000 146px,#000 calc(100% - 124px),transparent calc(100% - 90px))';

export const PANEL_KEYS = ['notif'];

export function createEngine() {
  const S = { W: 390, H: 844, dpr: 1 };
  const state = {
    t: 0, form: 0, press: 0, pulse: 0,
    lx: -0.45, ly: 0.72, lvx: 0, lvy: 0,
    sheet: 0, sheetT: 0, sheetVel: 0, openH: 0, cur: null, view: 'today',
    fit: 1, pf: 1,
  };
  const rects = Array.from({ length: 8 }, () => ({ x: 0, y: 0, w: 0, h: 0, r: 0 }));

  const STATIC = location.search.includes('static');
  const DEBUG = location.search.includes('debug');

  let el = null;             // { canvas, screen, phone, cap, tabs, sheet, sheetBody, scrim, dbg, err }
  let views = [];
  let tabBtns = [];
  let gl = null, progBG, progGlass, quad, bgTex, fbo;
  const U = { bg: {}, gs: {} };
  let rafId = 0;

  const hooks = {
    onViewChange: () => {},
    onOpenSheet: () => {},
    onDismiss: () => {},
  };

  function fail(m) {
    if (el?.err) { el.err.textContent = m; el.err.classList.add('on'); }
    document.body.classList.add('no-gl');
  }

  /* ---------------- WebGL ---------------- */

  function compile(t, s) {
    const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o);
    if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o));
    return o;
  }
  function program(vs, fs) {
    const p = gl.createProgram();
    gl.attachShader(p, compile(gl.VERTEX_SHADER, vs));
    gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
  }

  function initGL() {
    gl = el.canvas.getContext('webgl', { antialias: false, alpha: false, depth: false, stencil: false, powerPreference: 'high-performance' });
    if (gl) gl.getExtension('OES_standard_derivatives');
    if (!gl) { fail('当前浏览器不支持 WebGL，已切到 CSS 兜底'); return; }
    try {
      progBG = program(VS, FS_BG);
      progGlass = program(VS, FS_GLASS);
      quad = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, quad);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      bgTex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, bgTex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      fbo = gl.createFramebuffer();
      ['uRes', 'uCss', 'uTime', 'uPulse', 'uBright', 'uTree'].forEach(n => { U.bg[n] = gl.getUniformLocation(progBG, n); });
      ['uBg', 'uRes', 'uDpr', 'uCss', 'uTime', 'uMerge', 'uThick', 'uDisp', 'uFrost',
        'uForm', 'uPress', 'uScrim', 'uTabA', 'uViewA', 'uLight']
        .forEach(n => { U.gs[n] = gl.getUniformLocation(progGlass, n); });
      for (let i = 0; i < 8; i++) {
        U.gs['r' + i] = gl.getUniformLocation(progGlass, 'uRect[' + i + ']');
        U.gs['a' + i] = gl.getUniformLocation(progGlass, 'uRad[' + i + ']');
      }
      U.aBG = gl.getAttribLocation(progBG, 'aPos');
      U.aGL = gl.getAttribLocation(progGlass, 'aPos');
    } catch (e) {
      fail('着色器编译失败，已切到 CSS 兜底\n' + e.message);
    }
  }

  /* ---------------- 布局 ---------------- */

  function measure() {
    // 用 offsetWidth/Height：不受外层 transform: scale() 影响，
    // 否则预览面板把手机缩小时，画布和玻璃矩形会一起缩，全部错位
    S.W = el.screen.offsetWidth || 390;
    S.H = el.screen.offsetHeight || 844;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(S.W * dpr), h = Math.round(S.H * dpr);
    if (el.canvas.width !== w || el.canvas.height !== h) {
      el.canvas.width = w; el.canvas.height = h;
      if (gl && bgTex) {
        gl.bindTexture(gl.TEXTURE_2D, bgTex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, bgTex, 0);
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      }
    }
    S.dpr = el.canvas.width / S.W;
    layoutStatic();
    kick(400);
  }

  function rectOf(node) {
    const r = node.getBoundingClientRect();
    const s = el.screen.getBoundingClientRect();
    const k = state.fit || 1;
    return { x: (r.left - s.left) / k, y: (r.top - s.top) / k, w: r.width / k, h: r.height / k };
  }

  function layoutStatic() {
    // cap 可能在某些视图被条件渲染移除（如今天页），这里重新取一次并做空值保护，
    // 避免 rectOf(null) 直接抛错；不存在时给一个 0 矩形，那一块就不画玻璃。
    if (!el.cap) el.cap = document.getElementById('cap');
    // 底栏同理：首次布局时它可能还没挂上，取到后补绑一次下拉手势
    if (!el.tabs) el.tabs = document.getElementById('tabs');
    if (el.tabs && !tabsBound) { bindDrag(el.tabs); tabsBound = true; }
    if (el.cap) {
      const c = rectOf(el.cap);
      rects[0] = { x: c.x, y: c.y, w: c.w, h: c.h, r: 25 };
    } else {
      rects[0] = { x: 0, y: 0, w: 0, h: 0, r: 25 };
    }

    const t = el.tabs;
    if (t) {
      const r = rectOf(t);
      rects[7] = { x: r.x, y: r.y, w: r.w, h: r.h, r: 28 };
    } else {
      // 底栏还没渲染出来（或某视图里被移除）时给 0 矩形，
      // 别让 rectOf(null) 抛错把整条布局链打断
      rects[7] = { x: 0, y: 0, w: 0, h: 0, r: 28 };
    }

    for (let i = 1; i <= 5; i++) rects[i] = { x: 0, y: 0, w: 0, h: 0, r: 22 };
    const v = document.querySelector('.view.on');
    if (v) {
      v.querySelectorAll('[data-g]').forEach(node => {
        const i = +node.dataset.g;
        if (i < 1 || i > 5) return;
        const r = rectOf(node);
        if (r.h < 2) return;
        rects[i] = { x: r.x, y: r.y, w: r.w, h: r.h, r: 22 };
      });
    }
    updateSheet();
  }

  function updateSheet() {
    const s = state.sheet;
    const tab = rects[7];
    const openH = state.openH || Math.min(S.H * 0.72, 640);
    const openY = S.H - openH - 24;
    const e = clamp(s, -0.06, 1.08);
    rects[6] = {
      x: lerp(tab.x, S.W * 0.041, e),
      y: lerp(tab.y, openY, e),
      w: lerp(tab.w, S.W * 0.918, e),
      h: lerp(tab.h, openH, e),
      r: lerp(28, 30, e),
    };
    // 收起时让位给标签栏本体，避免两块完全重合的玻璃叠出双倍描边
    if (s < 0.015) rects[6] = { x: 0, y: 0, w: 0, h: 0, r: 0 };

    const r = rects[6];
    el.sheet.style.left = r.x + 'px';
    el.sheet.style.top = r.y + 'px';
    el.sheet.style.width = r.w + 'px';
    el.sheet.style.height = r.h + 'px';
    el.sheet.style.borderRadius = r.r + 'px';
    el.sheet.style.opacity = s > 0.05 ? String(smoothstep(0.05, 0.5, s)) : '0';
    el.sheet.style.pointerEvents = s > 0.6 ? 'auto' : 'none';

    el.tabs.style.opacity = String(1 - smoothstep(0, 0.32, s));
    el.tabs.style.pointerEvents = s > 0.3 ? 'none' : 'auto';

    // 底层内容让位：文字先退，玻璃由压暗层接管
    const vo = 1 - smoothstep(0.02, 0.30, s);
    views.forEach(v => {
      const on = v.classList.contains('on');
      v.style.opacity = vo < 0.999 ? String(on ? vo : 0) : (on ? '' : '0');
      v.style.pointerEvents = on && vo > 0.6 ? '' : 'none';
    });

    el.scrim.style.pointerEvents = s > 0.7 ? 'auto' : 'none';

    if (el.cap) {
      el.cap.style.opacity = s > 0.02 ? String(1 - 0.30 * smoothstep(0, 0.55, s)) : '';
      el.cap.style.pointerEvents = s > 0.5 ? 'none' : '';
    }
  }

  /** 面板内容由 Vue 渲染，渲染完再回来量高度 */
  function measureSheetHeight() {
    const body = el.sheetBody;
    body.scrollTop = 0;
    const kids = [...body.children];
    let h = 0;
    if (kids.length) {
      const first = getComputedStyle(kids[0]);
      const last = getComputedStyle(kids[kids.length - 1]);
      h = kids[kids.length - 1].getBoundingClientRect().bottom
        - kids[0].getBoundingClientRect().top
        + parseFloat(first.marginTop || 0) + parseFloat(last.marginBottom || 0);
    }
    // 面板上下留白 18+16 + 抓手 18 = 52；滚动区自己还有 30 的底部呼吸。
    // 加 88 才刚好让最后一排按钮落进可视区，不然要再滚一下才看得见。
    // 上限放宽到 82% / 700：通知这类逐条列表七八行时，旧的 72% / 640 会把
    // 最后一排按钮切掉一半，看着像不能点。
    state.openH = clamp(h + 88, 268, Math.min(S.H * 0.82, 700));
    /* 内容异步回来（通知列表、接口慢）时，引擎往往已经休眠了；
       光改 openH 不会自动重排，得踢一脚让它下一帧按新高度画一次 */
    kick(400);
  }

  /* ---------------- 面板 ---------------- */

  function openSheet(key) {
    if (!PANEL_KEYS.includes(key)) return;
    state.cur = key;
    state.sheetT = 1;
    hooks.onOpenSheet(key);
    // Vue 的渲染是异步的：等两帧再量，内容高度才准
    requestAnimationFrame(() => requestAnimationFrame(measureSheetHeight));
    kick(600);
  }

  function closeSheet() {
    state.sheetT = 0;
    kick(500);
  }

  function isSheetOpen() {
    return state.sheet > 0.25;
  }

  /* ---------------- 手势 ---------------- */

  /* 坑：pointerdown 里直接 setPointerCapture 会把后面的 pointerup 目标改成捕获元素，
     click 于是落在容器上、按钮自己的 click 永远收不到（底部 tab 就点不动了）。
     所以：不捕获，move/up 挂在 window 上，位移超过阈值才认定为拖动。 */
  let drag = null;
  let dragAte = false;
  let tabsBound = false;

  function bindDrag(node) {
    node.addEventListener('pointerdown', e => {
      if (e.target.closest('[data-sheet]') || e.target.closest('input, textarea')) return;
      drag = { y0: e.clientY, s0: state.sheet, armed: false };
    });
  }

  function onMove(e) {
    if (!drag) return;
    const dy = drag.y0 - e.clientY;
    if (!drag.armed) {
      if (Math.abs(dy) < 7) return;   // 阈值内的抖动不算拖动，click 照常派发
      drag.armed = true;
    }
    state.sheet = clamp(drag.s0 + dy / 230, 0, 1);
    state.sheetT = state.sheet;
    kick(160);   // 拖着的时候要逐帧跟手（引擎可能已经在休眠）
  }

  function endDrag() {
    if (!drag) return;
    const armed = drag.armed;
    drag = null;
    kick(500);   // 松手后弹簧自己回位，这段要逐帧
    if (!armed) return;
    dragAte = true;
    setTimeout(() => { dragAte = false; }, 80);
    /* 上滑到一定位置就停在打开态。没有当前面板时不再随手弹一个默认面板：
       面板只剩「通知」，凭空弹出来只会让人以为点了什么。 */
    if (state.sheet > 0.28 && state.cur) state.sheetT = 1;
    else if (state.sheet > 0.28) state.sheetT = 0;
    else state.sheetT = 0;
  }

  /* ---------------- 视图 ---------------- */

  /** 只做几何与收尾；`.on` 这类由 Vue 的响应式去切 */
  function afterViewChange(name) {
    state.view = name;
    closeSheet();
    el.phone.classList.remove('scrolled');
    tabsDirtyUntil = performance.now() + 900;
    requestAnimationFrame(layoutStatic);
    /* 卡片是近实白的，玻璃罩压在它下面基本看不出来，所以切页不必跟着逐帧重画
       —— 每重画一帧，上面那些 backdrop-filter 卡片就要跟着重算一次模糊。
       给 280ms 覆盖入场的前半段就够，尾段位置已经稳定。 */
    kick(280);
  }

  /* ---------------- 舞台缩放 ---------------- */

  function applyPhone(pf) {
    // 入场不再做任何缩放或位移，只保留淡入（opacity 由 frame 里按 pf 给）。
    // 只要壳在动，底部导航看起来就"没贴底"，所以缩放/位移一律归零。
    // 剩下只有视口自适应的 fit 缩放，且用公式把底边钉住：
    // 中心缩放会让底边上移 H*(1-s)/2，这里补回同样的距离，底栏始终贴在壳底。
    const s = state.fit || 1;
    const H = el.phone.offsetHeight;
    // 手机比舞台高时，grid 的 center 对齐会退化成 start（避免溢出），
    // 于是底部被切掉。这里自己补一个位移把视觉上的盒子摆回正中。
    const base = H > innerHeight ? (innerHeight - H) / 2 : 0;
    const ty = base + (H * (1 - s)) / 2;
    el.phone.style.transform = `translateY(${ty.toFixed(1)}px) scale(${s.toFixed(4)})`;
  }

  function fitStage() {
    if (matchMedia('(max-width:560px)').matches) { state.fit = 1; }
    else {
      // 首帧如果还没量到真实尺寸（0 或异常小），不要按它算缩放，
      // 否则壳先被缩一点、底栏偏上，等真正尺寸出来才掉回底部。
      const w = el.phone.offsetWidth, h = el.phone.offsetHeight;
      if (w < 2 || h < 2) { state.fit = 1; applyPhone(state.pf === undefined ? 1 : state.pf); return; }
      const k = Math.min(1, (innerHeight - 24) / h, (innerWidth - 24) / w);
      state.fit = k < 0.999 ? k : 1;
    }
    applyPhone(state.pf === undefined ? 1 : state.pf);
    const hint = document.getElementById('hint');
    if (hint) hint.style.display = state.fit < 1 ? 'none' : '';
  }

  /* ---------------- 渲染循环 ----------------
   * 以前是无条件逐帧：静止不动的时候也在跑两遍全屏 WebGL、每帧量一次底栏。
   * 手机整页都在动画（切页入场 / 卡片展开）时，这份常驻开销会和它们抢 GPU，
   * 表现就是"切画面那一下发涩"。
   *
   * 现在改成按需渲染：有人操作、面板在动、入场没收敛、刚切过页 / 刚滚过，
   * 这些窗口里逐帧画；安静下来后退到 IDLE_MS 一帧，时间继续推进，
   * 只是玻璃光泽慢下来（肉眼几乎看不出差别，GPU 从常驻变成偶发）。
   */
  const IDLE_MS = 420;
  let last = performance.now(), frames = 0, acc = 0, fps = 0;
  let idleTimer = 0, rafPending = false, busyUntil = 0, firstDraw = true;
  let tabsDirtyUntil = 0, tabsWasOff = false;
  let scrollDirty = false, scrollAt = 0, measureAt = 0;

  function schedule() {
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = 0; }
    if (rafPending) return;
    rafPending = true;
    rafId = requestAnimationFrame(frame);
  }

  /** 交互唤醒：接下来 ms 毫秒内保持逐帧 */
  function kick(ms) {
    if (ms) busyUntil = Math.max(busyUntil, performance.now() + ms);
    schedule();
  }

  function sleepSoon() {
    if (idleTimer) return;
    idleTimer = setTimeout(() => { idleTimer = 0; schedule(); }, IDLE_MS);
  }

  function frame(now) {
    rafPending = false;
    const dtReal = Math.max(0, (now - last) / 1000);
    last = now;
    // 物理用夹住的 dt（休眠后第一帧可能隔了半秒，弹簧会跳），时间轴走真实 dt
    const dt = Math.min(0.05, dtReal);
    state.t += dtReal;

    if (!drag) {
      // 临界阻尼弹簧：k 决定手感，damp 决定回弹。0.86 会在末端留一点点过冲，
      // 面板落位时会"弹"一下，不是干巴巴地停住。
      state.sheetVel += (state.sheetT - state.sheet) * 170 * dt;
      state.sheetVel *= Math.pow(0.86, dt * 60);
      state.sheet = clamp(state.sheet + state.sheetVel * dt, -0.06, 1.08);
      if (Math.abs(state.sheetT - state.sheet) < 0.002 && Math.abs(state.sheetVel) < 0.02) {
        state.sheet = state.sheetT; state.sheetVel = 0;
      }
    }

    state.lvx += (light.x - state.lx) * 14 * dt;
    state.lvy += (light.y - state.ly) * 14 * dt;
    state.lvx *= Math.pow(0.86, dt * 60); state.lvy *= Math.pow(0.86, dt * 60);
    state.lx += state.lvx * dt * 6; state.ly += state.lvy * dt * 6;

    state.form += (1 - state.form) * Math.min(1, dt * 4.2);
    state.pulse *= Math.pow(0.02, dt);
    state.press += ((state.sheet > 0.5 ? 0.4 : 0) - state.press) * Math.min(1, dt * 6);

    const pf = clamp((state.form - 0.10) / 0.90, 0, 1);
    state.pf = pf;
    // 入场淡入只做在玻璃画布上，手机壳和页面底色从一开始就是实的。
    // 以前是把整个 .phone 设成半透明：那会儿下面 stage 的粉白底会透上来，
    // 在紫色日记页尤其明显——切过去先泛一层粉、再慢慢变紫。玻璃自己淡入，
    // 观感不变，但任何一页切进来底色都是一次到位的。
    if (el.canvas) el.canvas.style.opacity = pf;
    applyPhone(pf);
    if (el.cap && pf > 0.55) el.cap.classList.add('in');

    // 底栏只有「滑下去 / 滑上来」时会动：检测 off 类翻转，翻的那 0.7 秒才逐帧量，
    // 其余时间沿用 layoutStatic 量好的那一格 —— 每帧 getBoundingClientRect
    // 会强制同步一次布局，是这条循环里最贵的一步。
    const tEl = el.tabs;
    if (tEl) {
      const off = tEl.classList.contains('off');
      if (off !== tabsWasOff) { tabsWasOff = off; tabsDirtyUntil = now + 700; }
      if (now < tabsDirtyUntil) {
        const r = rectOf(tEl);
        rects[7] = { x: r.x, y: r.y, w: r.w, h: r.h, r: 28 };
      }
    }

    // 滚动时玻璃卡片要跟着内容走，但不必每帧重量：90ms 一次够跟手，
    // 滚动停下 180ms 后再精确量一次收尾。
    if (scrollDirty && now - measureAt > 90) { measureAt = now; layoutStatic(); }
    if (scrollDirty && now - scrollAt > 180) { scrollDirty = false; layoutStatic(); }

    updateSheet();

    if (!gl || !progBG) return;

    const W = el.canvas.width, H = el.canvas.height;

    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.viewport(0, 0, W, H);
    gl.useProgram(progBG);
    gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.enableVertexAttribArray(U.aBG);
    gl.vertexAttribPointer(U.aBG, 2, gl.FLOAT, false, 0, 0);
    gl.uniform2f(U.bg.uRes, W, H);
    gl.uniform2f(U.bg.uCss, S.W, S.H);
    gl.uniform1f(U.bg.uTime, state.t);
    gl.uniform1f(U.bg.uPulse, state.pulse);
    gl.uniform1f(U.bg.uBright, 1.0 + 0.04 * state.press);
    gl.uniform1f(U.bg.uTree, state.view === 'tree' ? 1.0 : 0.0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, W, H);
    gl.useProgram(progGlass);
    gl.enableVertexAttribArray(U.aGL);
    gl.vertexAttribPointer(U.aGL, 2, gl.FLOAT, false, 0, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, bgTex);
    gl.uniform1i(U.gs.uBg, 0);
    gl.uniform2f(U.gs.uRes, W, H);
    gl.uniform1f(U.gs.uDpr, S.dpr);
    gl.uniform2f(U.gs.uCss, S.W, S.H);
    gl.uniform1f(U.gs.uTime, state.t);

    for (let i = 0; i < 8; i++) {
      const r = rects[i];
      gl.uniform4f(U.gs['r' + i], r.x, r.y, r.w, r.h);
      gl.uniform1f(U.gs['a' + i], r.r);
    }
    gl.uniform1f(U.gs.uMerge, smoothstep(0.0, 0.18, state.sheet) * (1 - smoothstep(0.30, 0.62, state.sheet)));
    gl.uniform1f(U.gs.uThick, 22);
    gl.uniform1f(U.gs.uDisp, 0.60);
    gl.uniform1f(U.gs.uFrost, 0.10);
    gl.uniform1f(U.gs.uForm, 0.3 + 0.7 * state.form);
    gl.uniform1f(U.gs.uPress, state.press);
    gl.uniform1f(U.gs.uScrim, smoothstep(0.03, 0.42, state.sheet));
    gl.uniform1f(U.gs.uTabA, 1 - smoothstep(0.12, 0.46, state.sheet));
    gl.uniform1f(U.gs.uViewA, 1 - smoothstep(0.06, 0.40, state.sheet));
    gl.uniform3f(U.gs.uLight, state.lx, state.ly, 0.78);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    frames++; acc += dtReal;
    if (acc > 0.5) {
      fps = Math.round(frames / acc); frames = 0; acc = 0;
      if (el.dbg.classList.contains('on')) {
        el.dbg.textContent = `fps ${fps}\ncanvas ${el.canvas.width}x${el.canvas.height}\ndpr ${S.dpr.toFixed(2)}\ncss ${S.W.toFixed(0)}x${S.H.toFixed(0)}\nsheet ${state.sheet.toFixed(2)}`;
      }
    }

    /* 还有东西在动就接着画，都停住了就睡到下一帧闹钟 */
    const sheetMoving = Math.abs(state.sheetT - state.sheet) > 0.0015 || Math.abs(state.sheetVel) > 0.02;
    const formMoving = state.form < 0.9995;
    const lightMoving = Math.abs(state.lvx) + Math.abs(state.lvy)
      + Math.abs(light.x - state.lx) + Math.abs(light.y - state.ly) > 0.004;
    const pressMoving = Math.abs((state.sheet > 0.5 ? 0.4 : 0) - state.press) > 0.004;
    const busy = !!drag || sheetMoving || formMoving || lightMoving || pressMoving
      || now < busyUntil || now < tabsDirtyUntil || scrollDirty || firstDraw;
    firstDraw = false;
    if (busy) schedule(); else sleepSoon();
  }

  /* ---------------- 光 ---------------- */

  const light = { x: -0.45, y: 0.72 };

  function onPointerMove(e) {
    const r = el.screen.getBoundingClientRect();
    light.x = clamp((e.clientX - r.left) / r.width * 2.2 - 1.1, -1, 1);
    light.y = clamp(1.1 - (e.clientY - r.top) / r.height * 2.2, -1, 1);
    kick(260);   // 光斑要追手，这段时间保持逐帧；停下后自己睡
  }

  /* ---------------- 生命周期 ---------------- */

  function mount(stage) {
    el = {
      stage,
      canvas: stage.querySelector('#gl'),
      screen: stage.querySelector('#screen'),
      phone: stage.querySelector('#phone'),
      cap: stage.querySelector('#cap'),
      tabs: stage.querySelector('#tabs'),
      sheet: stage.querySelector('#sheet'),
      sheetBody: stage.querySelector('#sheetBody'),
      scrim: stage.querySelector('#scrim'),
      dbg: document.getElementById('dbg'),
      err: document.getElementById('err'),
    };
    views = [...stage.querySelectorAll('.view')];
    tabBtns = [...el.stage.querySelectorAll('.tab')];
    views.forEach(v => {
      // 自己管理全屏背景与边缘避让的视图（如日记页）标记 data-no-mask，
      // 不套用通用的顶/底溶解 mask，否则背景会在状态栏处被一起溶解掉
      if (v.dataset.noMask !== undefined) return;
      v.style.webkitMaskImage = VIEW_MASK;
      v.style.maskImage = VIEW_MASK;
    });

    initGL();

    el.scrim.addEventListener('click', closeSheet);
    if (el.tabs) bindDrag(el.tabs);
    if (el.sheet) bindDrag(el.sheet);

    window.addEventListener('pointermove', onPointerMove, { passive: true });
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', endDrag);
    window.addEventListener('pointercancel', endDrag);

    // 刚拖动过 → 吃掉紧随其后的 click，别让 tab 跟着切换
    document.addEventListener('click', e => {
      if (dragAte) { e.stopPropagation(); e.preventDefault(); }
    }, true);

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') closeSheet();
      if (e.key === 'd') el.dbg.classList.toggle('on');
    });

    views.forEach(v => {
      // 滚动只打脏标记，真正的重量放到 frame 里按 90ms 节流做，
      // 免得每次滚动事件都强制同步一次布局（那才是滚动发涩的来源）
      v.addEventListener('scroll', () => {
        scrollAt = performance.now();
        scrollDirty = true;
        kick(120);
      }, { passive: true });
      // 滚动超过一点点，顶栏下方就压一层渐变，内容不会和胶囊里的标题糊在一起
      v.addEventListener('scroll', () => {
        if (v.classList.contains('on')) el.phone.classList.toggle('scrolled', v.scrollTop > 16);
      }, { passive: true });
    });

    fitStage();
    window.addEventListener('resize', () => { fitStage(); measure(); });
    if (window.ResizeObserver) new ResizeObserver(measure).observe(el.screen);

    measure();
    state.form = (matchMedia('(prefers-reduced-motion: reduce)').matches || STATIC) ? 1 : 0;
    layoutStatic();
    if (DEBUG) el.dbg.classList.add('on');

    schedule();
  }

  function unmount() {
    cancelAnimationFrame(rafId);
    rafPending = false;
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = 0; }
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', endDrag);
    window.removeEventListener('pointercancel', endDrag);
  }

  /** 绑定 Vue 的响应式动作 */
  function bind(next) { Object.assign(hooks, next); }

  return {
    state, S, rects,
    mount, unmount, bind,
    measure, measureSheetHeight, layoutStatic, fitStage,
    openSheet, closeSheet, isSheetOpen, afterViewChange,
    setView: (name) => { afterViewChange(name); hooks.onViewChange(name); },
    tabBtns: () => tabBtns,
    pulse: () => { state.pulse = 1; },
    applyPhone,
  };
}
