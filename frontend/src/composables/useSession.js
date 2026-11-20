/* 全局会话 store：
   统一管理登录页显示、强制登出，以及「关系被解除就退回登录页」的守卫。

   状态挂在 globalThis 上而非常驻模块闭包：Vite HMR 重新加载本模块时，
   普通模块级变量会产生新实例（旧 setInterval 持有旧闭包、新组件绑定新 ref，
   两者不同步）。挂到全局唯一位置后，无论模块被加载多少次都复用同一份状态。 */

import { ref } from 'vue';
import { clearToken, getToken, purgeAccountCache } from '../api/token.js';
import { getCouple } from '../api/settings.js';

const GLOBAL_KEY = '__COVE_SESSION__';
const GUARD_INTERVAL = 5000;

/* 走查 / 截图用的逃生口：?demo=1 看假数据、?shot=1 纯截图，都不拦登录。
   只在开发构建里生效 —— 正式包如果也认这两个参数，
   任何人加个 ?shot=1 就能跳过登录闸门看到主页。 */
function gateBypassed() {
  if (!import.meta.env.DEV) return false;
  try {
    const q = new URLSearchParams(location.search);
    return q.has('demo') || q.has('shot');
  } catch (_) {
    return false;
  }
}

function createState() {
  return {
    showLogin: ref(false),
    closing: ref(false),
    loginReason: ref(''),
    guardTimer: null,
    wasBound: false,      // 曾经处于已绑定关系
    wasLoggedIn: false,  // 曾经登录（本标签拿过 token）
  };
}

// 主世界里 HMR / 多次 import 都命中同一个全局对象
const state = (globalThis[GLOBAL_KEY] = globalThis[GLOBAL_KEY] || createState());

function forceLogout(reason = '') {
  clearToken();
  /* 顺带清掉不按用户区分的本地缓存（账本预算、模拟 TA 会话 id），
     否则同一台设备换个账号登录，新用户会看到上一个人的数字。 */
  purgeAccountCache();
  state.loginReason.value = reason;
  state.showLogin.value = true;
  /* 通知各页面把盖在登录页上面的弹层收起来。
     解绑 / 注销弹层是 Teleport 到 body 上的（z-index 9999），
     登录页只有 50：不收它们，登录页出来了也点不到，看起来就是「关不掉」。 */
  window.dispatchEvent(new Event('cove:logout'));
}

/* 关系守卫 + 登录守卫：
   没有令牌一律退回登录页 —— 未登录不该能进到任何一页。
   唯一的例外是设计走查用的 ?demo / ?shot 参数（截图与假数据调试）。 */
async function checkCouple() {
  if (state.showLogin.value) return;
  if (gateBypassed()) return;

  const token = getToken();
  if (token) state.wasLoggedIn = true;

  if (!token) {
    // 没登录就强制停在登录页；首次打开也一样，不再放行
    state.loginReason.value = state.loginReason.value || '';
    state.showLogin.value = true;
    return;
  }

  try {
    const couple = await getCouple();
    if (state.showLogin.value) return;
    if (!couple) {
      if (state.wasBound) {
        forceLogout('你们已经解除绑定，请重新登录');
        return;
      }
      /* 有账号但还没配对：主页不放行，停在配对屏（绑上了才进得去） */
      state.loginReason.value = '先和 TA 绑上，才能进主页';
      state.showLogin.value = true;
      return;
    }
    state.wasBound = true;
  } catch (_) {
    /* 网络抖动或单次失败：忽略，下一轮再试，避免误踢下线 */
  }
}

function onVisible() {
  if (!document.hidden) checkCouple();
}

function startGuard() {
  // 先清理可能残留的旧定时器/监听，保证任何情况下都只有一个守卫在跑
  if (state.guardTimer) {
    clearInterval(state.guardTimer);
    state.guardTimer = null;
  }
  document.removeEventListener('visibilitychange', onVisible);
  checkCouple();
  state.guardTimer = setInterval(checkCouple, GUARD_INTERVAL);
  document.addEventListener('visibilitychange', onVisible);
}

// 登录页关闭（重新登录成功 / 进入主页）：先播放退出动画再卸载
function requestClose() {
  state.closing.value = true;
  setTimeout(() => {
    state.showLogin.value = false;
    state.closing.value = false;
    state.loginReason.value = '';
    state.wasBound = false;
    state.wasLoggedIn = !!getToken();
    checkCouple();
    /* 登录页是在所有视图挂载之后才盖上的，视图那一轮的请求多半是 401，
       这里通知各视图重拉一次，保证进来看到的就是后端真实数据 */
    window.dispatchEvent(new Event('cove:auth'));
  }, 600);
}

export function useSession() {
  return {
    showLogin: state.showLogin,
    closing: state.closing,
    loginReason: state.loginReason,
    forceLogout,
    checkCouple,
    startGuard,
    requestClose,
  };
}
