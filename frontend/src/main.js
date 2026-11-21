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
  stage.style.top = shift + 'px';
  stage.style.height = (kb >= 40 ? vv.height : window.innerHeight - shift) + 'px';
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

/* 调试 / 自动化测试的把手：只有带 ?debug 时才挂到 window 上 */
if (new URLSearchParams(location.search).has('debug')) window.__cove = engine;

/* Service Worker 只在真正的产品环境注册：
   Capacitor 的 WebView 走本地协议，注册了反而会把旧包缓存住；
   本地开发也不注册，否则 cache-first 会把 /src 下的旧模块一直喂给页面。 */
const isNative = !!window.Capacitor?.isNativePlatform?.();
const isDevHost = location.hostname === 'localhost'
  || location.hostname === '127.0.0.1'
  || location.hostname === '[::1]';
if (!import.meta.env.DEV && !isDevHost && 'serviceWorker' in navigator && location.protocol.startsWith('http') && !isNative) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  });
}
