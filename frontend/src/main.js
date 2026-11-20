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
