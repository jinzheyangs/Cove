import { createApp } from 'vue';
import App from './App.vue';
import './styles/app.css';
import './styles/fonts.css';
import './styles/cream.css';
import { initNative } from './native.js';
import { engine } from './glass/index.js';

/* 独立窗口（PWA / Capacitor）下系统状态栏是真的，页面里那个假的状态栏要收起来 */
const IS_STANDALONE = matchMedia('(display-mode: standalone)').matches
  || navigator.standalone === true
  || new URLSearchParams(location.search).has('sa');
document.documentElement.classList.toggle('sa', !!IS_STANDALONE);

initNative();

/* iOS 键盘：输入框一聚焦，Safari 会把整页往上滚一段去"露出"它，外壳是 fixed 布局
   不跟着走，结果底部导航跑到屏幕中间、下面空出一大片。
   解法是让外壳直接贴住可视视口：键盘弹起时高度收到可视高度，同时跟上位移。
   桌面预览（宽 > 560）不启用，那个带圆角的手机框保持原样。 */
function syncStageToViewport() {
  const vv = window.visualViewport;
  const stage = document.querySelector('.stage');
  if (!vv || !stage) return;
  const reset = () => {
    stage.style.top = '';
    stage.style.height = '';
    stage.style.bottom = '';
  };
  if (window.innerWidth > 560) { reset(); return; }
  const kb = window.innerHeight - vv.height;
  const shift = Math.max(0, vv.offsetTop) + Math.max(0, window.scrollY);
  if (kb < 40 && shift < 40) { reset(); return; }
  const h = kb >= 40 ? vv.height : window.innerHeight - shift;
  /* 键盘弹出/收起的过渡里，个别时刻会给出 0 或很小的值。
     直接照着设会把外壳压成一条线（整页白屏），所以低于阈值就忽略这一帧。 */
  if (!h || h < 160) return;
  stage.style.top = shift + 'px';
  stage.style.height = h + 'px';
  stage.style.bottom = 'auto';
}

if (window.visualViewport) {
  const vv = window.visualViewport;
  vv.addEventListener('resize', syncStageToViewport);
  vv.addEventListener('scroll', syncStageToViewport);
  window.addEventListener('scroll', syncStageToViewport);
  window.addEventListener('orientationchange', () => setTimeout(syncStageToViewport, 250));
  requestAnimationFrame(syncStageToViewport);
  setTimeout(syncStageToViewport, 120);
}

createApp(App).mount('#app');

/* 临时诊断面板：带 ?diag=1 时在左上角显示真实数值，用来确认键盘弹起时
   外壳到底有没有跟着缩。确认完可以删掉。 */
if (new URLSearchParams(location.search).has('diag')) {
  const box = document.createElement('div');
  box.style.cssText = 'position:fixed;left:6px;top:6px;z-index:9999;' +
    'background:rgba(0,0,0,.82);color:#5ef08a;font:11px/1.55 ui-monospace,monospace;' +
    'padding:5px 7px;border-radius:6px;white-space:pre;pointer-events:none';
  document.body.appendChild(box);
  const paint = () => {
    const vv = window.visualViewport;
    const stage = document.querySelector('.stage');
    const r = stage ? stage.getBoundingClientRect() : null;
    box.textContent =
      'v8 · innerH ' + window.innerHeight + '\n' +
      'vv.h ' + (vv ? Math.round(vv.height) : 'n/a') +
      '  vv.top ' + (vv ? Math.round(vv.offsetTop) : 'n/a') + '\n' +
      'stage.y ' + (r ? Math.round(r.top) : '?') +
      '  stage.h ' + (r ? Math.round(r.height) : '?') + '\n' +
      'styleH ' + (stage ? (stage.style.height || '—') : '?');
  };
  paint();
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', paint);
    window.visualViewport.addEventListener('scroll', paint);
  }
  setInterval(paint, 400);
}

/* 调试 / 自动化测试的把手：只有带 ?debug 时才挂到 window 上 */
if (new URLSearchParams(location.search).has('debug')) window.__cove = engine;

/* Service Worker 暂不注册：/sw.js 走 SPA 兜底会返回 HTML，浏览器要求 JS MIME，
   注册本来就会失败；而它一旦真的生效，发版缓存会让每次调试都失真。
   等上线稳定后，单独给它开一条静态路由再启用。 */
const isNative = !!window.Capacitor?.isNativePlatform?.();
const isDevHost = location.hostname === 'localhost'
  || location.hostname === '127.0.0.1'
  || location.hostname === '[::1]';
// 暂时停用（见上方说明）。要重新启用时，先把 /sw.js 改成真正的静态响应，再放回这几行。
// if (!import.meta.env.DEV && !isDevHost && 'serviceWorker' in navigator && location.protocol.startsWith('http') && !isNative) {
//   window.addEventListener('load', () => {
//     navigator.serviceWorker.register('sw.js').catch(() => {});
//   });
// }

/* 自愈：如果这台设备上还留着早期注册成功的 Service Worker，它会一直喂旧包，
   让页面停在老版本甚至白屏。这里主动注销它、并清掉它留下的缓存。
   跑一次就够了，之后彻底干净。 */
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations()
    .then(rs => Promise.all(rs.map(r => r.unregister())))
    .catch(() => {});
  if (window.caches) {
    caches.keys()
      .then(ks => Promise.all(ks.map(k => caches.delete(k))))
      .catch(() => {});
  }
}
