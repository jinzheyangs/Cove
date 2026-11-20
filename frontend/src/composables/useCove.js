/* 一处集中算所有「跟今天有关」的数字：在一起第几天、纪念日倒计时、顶栏副标题。
 *
 * 这里的值全部来自后端（couples.start_date / 纪念日的「在一起」条目），
 * 不再有写死的起始日 —— 换了伴侣、改了相识日，界面立刻跟着变。
 *
 * 用 reactive 而不是常量：四个视图和顶栏共享同一份值，登录或绑定成功后
 * 还能重算一次并让所有地方同时刷新。
 */

import { reactive, ref, computed } from 'vue';
import { getCouple, getMe } from '../api/settings.js';
import { listAnniversaries } from '../api/anniversaries.js';

const DAY = 86400000;
const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

export const relation = reactive({
  ready: false,
  /* 伴侣是否真的填过「起始日」。
     false 时只有绑定日兜底，这时候不该假装已经在一起数了几天 ——
     首页那张卡会切成「待填」形态，把人引到设置里补上。 */
  startSet: false,
  startDate: '',   // 'YYYY-MM-DD'
  days: 0,         // 在一起第几天（当天算第 1 天）
  years: 1,        // 正在第几个年头 / 下一个周年是第几周年
  nextDate: '',    // 下一个周年日期
  daysToAnniv: 0,
  progress: 0,     // 本年度已走过的百分比
});

export const me = reactive({ nickname: '' });

const todayStart = () => {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
};

function daysSince(ymd) {
  if (!ymd) return 0;
  const start = new Date(`${ymd}T00:00:00`);
  if (Number.isNaN(start.getTime())) return 0;
  return Math.floor((todayStart() - start) / DAY) + 1;
}

/* 当前周年周期的进度：上一个周年 → 下一个周年 */
function progressOf(nextYmd, daysLeft) {
  if (!nextYmd) return 0;
  const next = new Date(`${nextYmd}T00:00:00`);
  if (Number.isNaN(next.getTime())) return 0;
  const prev = new Date(next);
  prev.setFullYear(next.getFullYear() - 1);
  const len = Math.round((next - prev) / DAY);
  if (!len) return 0;
  return Math.min(100, Math.max(0, Math.round(((len - daysLeft) / len) * 100)));
}

/** 用纪念日接口里的「在一起」条目回填（后端已处理闰年与时区，最准） */
export function applyRelation(entry) {
  if (!entry) return;
  relation.startDate = entry.date || relation.startDate;
  relation.nextDate = entry.next_date || '';
  relation.days = daysSince(relation.startDate);
  relation.years = entry.years || Math.max(1, Math.floor((relation.days - 1) / 365) + 1);
  relation.daysToAnniv = entry.days_left ?? 0;
  relation.progress = progressOf(relation.nextDate, relation.daysToAnniv);
  relation.ready = true;
}

/** 没有现成条目时自己拉一次（顶栏、首页用） */
export async function loadRelation() {
  try {
    const couple = await getCouple();
    if (couple) {
      if (couple.start_date) {
        relation.startDate = couple.start_date;
        relation.startSet = true;
      } else if (couple.bind_at) {
        // bind_at 是 UTC 时间，取北京时间那天做兜底（只是给日期选择器预填，
        // 不用它冒充「在一起第几天」）
        const d = new Date(new Date(couple.bind_at).getTime() + 8 * 3600 * 1000);
        relation.startDate = d.toISOString().slice(0, 10);
        relation.startSet = false;
      }
      if (relation.startSet) {
        relation.days = daysSince(relation.startDate);
        relation.years = Math.max(1, Math.floor((relation.days - 1) / 365) + 1);
      } else {
        relation.days = 0;
        relation.years = 1;
        relation.progress = 0;
        relation.daysToAnniv = 0;
      }
    }
  } catch (_) {
    /* 未登录 / 网络失败：留 0，别让界面出现 NaN */
  }

  try {
    const entries = await listAnniversaries();
    const rel = (entries || []).find((e) => e.source === 'relationship');
    /* 没填起始日时后端会拿绑定日兜底，那条不能当真（否则天数永远是 1） */
    if (rel && relation.startSet) applyRelation(rel);
  } catch (_) {
    /* 同上 */
  }
  relation.ready = true;
}

/** 取当前用户昵称（首页问候用） */
export async function loadMe() {
  try {
    const profile = await getMe();
    if (profile?.nickname) me.nickname = profile.nickname;
  } catch (_) {
    /* 未登录就留空 */
  }
}

export const todayLabel = (() => {
  const d = new Date();
  return `${d.getMonth() + 1}月${d.getDate()}日 · ${WEEK[d.getDay()]}`;
})();

/** 距下一个 mm-dd 还有几天（纪念日倒计时） */
export function daysUntil(md) {
  const today = todayStart();
  const [m, d] = md.split('-').map(Number);
  let t = new Date(today.getFullYear(), m - 1, d);
  if (t < today) t = new Date(t.getFullYear() + 1, m - 1, d);
  return Math.round((t - today) / DAY);
}

/** 顶栏标题 + 副标题 */
export const VIEW_META = {
  today: {
    title: '今天',
    sub: () => (relation.startSet ? `在一起的第 <b>${relation.days}</b> 天` : '还没填恋爱纪念日'),
  },
  diary: { title: '日记', sub: () => '一起写的日子' },
  tree: { title: '秘密树', sub: () => '说不出口的，藏在这里' },
  me: {
    title: '我们',
    sub: () => (relation.startDate ? `自 ${relation.startDate.replace(/-/g, '.')}` : '两个人的小世界'),
  },
};

export function useClock() {
  const text = ref('');
  const tick = () => {
    const d = new Date();
    text.value = d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
  };
  tick();
  setInterval(tick, 20000);
  return { text };
}

export function useCove() {
  const view = ref('today');
  const panel = ref(null);          // 当前面板 key
  const welcomeOpen = ref(false);
  const navIndex = computed(() => ['today', 'diary', 'tree', 'me'].indexOf(view.value));
  return { view, panel, welcomeOpen, navIndex };
}
