/* 未读数：页头铃铛的红点和「我们」页的通知入口说的是同一个数。
   拉取交给 App.vue 的 20 秒心跳（顺便跟着 cove:notif 事件刷），
   这里只负责存一份，谁要显示就引它。 */

import { ref } from 'vue';
import { getUnreadCount } from '../api/settings.js';

const GLOBAL_KEY = '__cove_unread__';

function createState() {
  return { unread: ref(0) };
}

// HMR / 多次 import 都命中同一个全局对象，红点不会因为模块副本而各自算一份
const state = (globalThis[GLOBAL_KEY] = globalThis[GLOBAL_KEY] || createState());

export const unread = state.unread;

export async function refreshUnread() {
  try {
    const d = await getUnreadCount();
    unread.value = d?.unread ?? 0;
  } catch (_) {
    /* 没登录 / 后端没起：红点不亮就行，不打扰 */
  }
}
