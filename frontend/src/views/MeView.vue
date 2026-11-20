<template>
<section
  class="view mv"
  :class="{ on: active }"
  data-view="me"
  data-no-mask
>
  <!-- 独立的滚动层：让底栏底座可以固定，不跟着内容跑 -->
  <div ref="viewEl" class="mv-scroll" @scroll.passive="onScroll">
  <header class="mv-head">
    <div class="mv-top">
      <span class="mv-eyebrow"><i class="mv-spark"></i>COVE · 两个人的小世界</span>
      <span class="mv-rt">
        <span class="mv-year">第 {{ relation.years }} 年</span>
        <button class="mv-bell" type="button" aria-label="通知" @click="openNotif">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M6.5 9.5a5.5 5.5 0 0 1 11 0c0 3.2.8 4.8 1.6 5.6.5.5.1 1.4-.6 1.4H5.5c-.7 0-1.1-.9-.6-1.4.8-.8 1.6-2.4 1.6-5.6Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
            <path d="M10 19.2a2.1 2.1 0 0 0 4 0" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
          </svg>
          <i v-if="unread > 0" class="mv-bell__dot"></i>
        </button>
      </span>
    </div>
    <h1 class="mv-title">我们</h1>
    <p class="mv-since">{{ sinceLabel }} · 一起慢慢长大</p>
  </header>

  <!-- 关系主卡：两只小怪物 + 天数 -->
  <article
    ref="heroEl"
    class="hero"
    :class="{ boop: boopOn }"
    role="button"
    tabindex="0"
    aria-label="和 TA 打个招呼"
    @pointermove="onPointer"
    @pointerleave="resetPointer"
    @click="burst"
    @keydown.enter.prevent="burst"
    @keydown.space.prevent="burst"
  >
    <div class="hero-sheen" aria-hidden="true"></div>

    <div class="blobs" aria-hidden="true">
      <div class="blob blob--ta">
        <span class="eye eye--l"><i class="pupil"></i></span>
        <span class="eye eye--r"><i class="pupil"></i></span>
        <span class="blob-shine"></span>
      </div>
      <div class="blob blob--me">
        <span class="eye eye--l"><i class="pupil"></i></span>
        <span class="eye eye--r"><i class="pupil"></i></span>
        <span class="blob-shine"></span>
      </div>
      <span class="core-heart">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 21s-8-5.2-8-11a4.6 4.6 0 0 1 8-3 4.6 4.6 0 0 1 8 3c0 5.8-8 11-8 11Z" fill="currentColor"/>
        </svg>
      </span>
      <span class="bursts">
        <i
          v-for="p in particles"
          :key="p.id"
          class="spark"
          :style="{ '--x': p.x + 'px', '--y': p.y + 'px', '--s': p.s, '--e': p.e }"
        ></i>
      </span>
    </div>

    <div class="hero-body">
      <span class="hero-eyebrow">在一起</span>
      <div class="hero-num" :class="{ 'hero-num--todo': !relation.startSet }">
        <template v-if="relation.startSet"><b>{{ animatedDays }}</b><span>天</span></template>
        <template v-else><b>待填</b></template>
      </div>
      <div class="hero-track" role="presentation">
        <i :style="{ width: relation.progress + '%' }"></i>
        <em :style="{ left: relation.progress + '%' }"></em>
      </div>
      <p class="hero-foot">
        <template v-if="relation.startSet">
          第 <b>{{ relation.years }}</b> 周年走过 <b>{{ relation.progress }}%</b> · 还有 <b>{{ relation.daysToAnniv }}</b> 天
        </template>
        <template v-else>
          在一起那天还没填 · 去「纪念日」补上
        </template>
      </p>
    </div>
  </article>

  <!-- 纪念日 -->
  <article class="mv-card card--anniv" :style="{ '--i': 1 }" @click="open('anniversary', $event)">
    <div class="c-head">
      <span class="c-ic" v-html="ICONS.heart"></span>
      <span class="c-name">纪念日</span>
      <span class="c-pill" v-if="anniv.ok && annivList.length">{{ annivList.length }} 个</span>
      <span class="chev" v-html="CHEV"></span>
    </div>

    <div v-if="anniv.error" class="c-note">登录后查看我们的纪念日</div>
    <div v-else-if="anniv.loading" class="c-skel"><i></i><i></i></div>
    <div v-else-if="!annivList.length" class="c-note">
      {{ startFilled ? '还没有自己加的纪念日，去添加一个吧' : '在一起那天还没填，填上才有日子可数' }}
    </div>
    <div v-else class="anniv">
      <div class="anniv-main">
        <span class="anniv-sub">
          <i class="anniv-sub__lb">{{ nearestAnniv.passed ? '上个日子' : '下个日子' }}</i>
        </span>
        <span class="anniv-title">
          {{ nearestAnniv.title }}<em v-if="nearestAnniv.years"> · {{ yearsText(nearestAnniv) }}</em>
        </span>
        <span class="anniv-date">{{ annivDateText(nearestAnniv) }}</span>
      </div>
      <span v-if="nearestAnniv.is_today" class="anniv-badge is-today">就是今天</span>
      <span v-else class="anniv-badge">
        <i class="anniv-badge__lb">{{ nearestAnniv.passed ? '已经' : '还有' }}</i>
        <span class="anniv-badge__n">
          <b>{{ Math.abs(nearestAnniv.days_left || 0) }}</b><small>天</small>
        </span>
      </span>
    </div>
  </article>

  <!-- 共同清单 -->
  <article class="mv-card card--todo" :style="{ '--i': 2 }" @click="open('todo', $event)">
    <div class="c-head">
      <span class="c-ic" v-html="ICONS.check"></span>
      <span class="c-name">共同清单</span>
      <span class="c-pill" v-if="todo.ok">{{ todoPending }} 件待办</span>
      <span class="chev" v-html="CHEV"></span>
    </div>

    <div v-if="todo.error" class="c-note">登录后查看我们一起要做的事</div>
    <div v-else-if="todo.loading" class="c-skel"><i></i><i></i></div>
    <div v-else-if="!todo.items.length" class="c-note">清单还是空的，一起列点想做的事吧</div>
    <div v-else class="todo">
      <div class="todo-top">
        <span class="todo-count"><b>{{ todoDone }}</b><small>/ {{ todo.items.length }}</small></span>
        <span class="todo-cap">已经一起做完</span>
      </div>
      <div class="todo-bar"><i :style="{ width: todoProgress + '%' }"></i></div>
    </div>
  </article>

  <!-- 恋爱账本 -->
  <article class="mv-card card--bill" :style="{ '--i': 3 }" @click="open('bill', $event)">
    <div class="c-head">
      <span class="c-ic" v-html="ICONS.wallet"></span>
      <span class="c-name">恋爱账本</span>
      <span class="c-pill" v-if="bill.ok && bill.stats">{{ billMoneyCount }} 笔</span>
      <span class="chev" v-html="CHEV"></span>
    </div>

    <div v-if="bill.error" class="c-note">登录后查看我们的共同账本</div>
    <div v-else-if="bill.loading" class="c-skel"><i></i><i></i></div>
    <div v-else class="bill">
      <div class="bill-num">
        <span class="bill-cny">¥</span>
        <span class="bill-fig">{{ bill.stats ? animatedMoney : '0.00' }}</span>
      </div>
      <div class="bill-chips">
        <span>共同 <b>{{ bill.stats ? fmtMoney(bill.stats.shared_total) : '0' }}</b></span>
        <span>个人 <b>{{ bill.stats ? fmtMoney(bill.stats.personal_total) : '0' }}</b></span>
      </div>
      <p v-if="billLast" class="bill-last">
        最近一笔 · {{ billLast.category }}
        <b>¥{{ fmtMoney(billLast.amount) }}</b>
      </p>
    </div>
  </article>

  <!-- 设置 -->
  <article class="mv-card card--set" :style="{ '--i': 4 }" @click="open('settings', $event)">
    <div class="c-head">
      <span class="c-ic" v-html="ICONS.gear"></span>
      <span class="c-name">设置</span>
      <span class="c-pill soft" :class="{ on: me.couple }">{{ me.couple ? '已绑定' : '未绑定' }}</span>
      <span class="chev" v-html="CHEV"></span>
    </div>

    <div class="set">
      <span class="avatar">
        <img v-if="me.ok && me.profile?.avatar_url" :src="me.profile.avatar_url" alt="" />
        <span v-else>{{ me.profile?.nickname?.slice(0, 1) || '客' }}</span>
      </span>
      <span class="set-main">
        <span class="set-name">{{ me.error ? '未登录 · 点我登录' : (me.profile?.nickname || '我') }}</span>
        <span class="set-sub">{{ me.error ? '登录后同步全部数据' : (me.profile?.phone ? maskPhone(me.profile.phone) : '还没有填手机号') }}</span>
      </span>
    </div>
  </article>
  </div>

  <!-- 背景极光：在滚动层外面，不参与滚动高度；内部按滚动量做反向视差 -->
  <div class="mv-bg" aria-hidden="true">
    <div class="mv-orbs">
      <span class="orb orb--a"></span>
      <span class="orb orb--b"></span>
      <span class="orb orb--c"></span>
    </div>
    <span class="mv-grain"></span>
  </div>

  <!-- 顶部渐隐：内容滚到状态栏下面时把字压下去 -->
  <div class="mv-topfade" aria-hidden="true"></div>

  <!-- 底部压层：内容滚到导航胶囊前面时收掉，别让卡片从胶囊底下透出来 -->
  <div class="mv-fade" aria-hidden="true"></div>
</section>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { relation, applyRelation } from '../composables/useCove.js';
import { listAnniversaries } from '../api/anniversaries.js';
import { listTodos } from '../api/todos.js';
import { listBills, getBillStats } from '../api/bills.js';
import { getMe, getCouple } from '../api/settings.js';
import { unread, refreshUnread } from '../composables/useUnread.js';
import { engine } from '../glass/index.js';
import { tap } from '../native.js';

const emit = defineEmits(['open']);
const props = defineProps({ active: Boolean });

/* ---------- 线性图标（更粗、更圆，配合黏土质感） ---------- */
const ICONS = {
  heart: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20.2s-7-4.6-7-9.4A4.1 4.1 0 0 1 12 7a4.1 4.1 0 0 1 7 3.8c0 4.8-7 9.4-7 9.4Z"/></svg>',
  check: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.4" y="3.4" width="17.2" height="17.2" rx="5"/><path d="m7.9 12.3 2.7 2.7 5.5-5.6"/></svg>',
  wallet: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.8" y="6" width="18.4" height="13" rx="4"/><path d="M2.8 10.2h18.4"/><circle cx="16.8" cy="13.6" r="1.3" fill="currentColor" stroke="none"/></svg>',
  gear: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.3"/><path d="M12 2.9v2.3M12 18.8v2.3M21.1 12h-2.3M5.2 12H2.9M18.3 5.7l-1.6 1.6M7.3 16.7l-1.6 1.6M18.3 18.3l-1.6-1.6M7.3 7.3 5.7 5.7"/></svg>',
};
const CHEV = '<svg width="8" height="13" viewBox="0 0 8 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m1.6 1.6 4.8 4.9-4.8 4.9"/></svg>';

/* ---------- 演示模式：?demo 时用样例数据，方便未登录预览 ---------- */
const DEMO = new URLSearchParams(location.search).has('demo');
/* 设计走查用：?scroll=600 直接把滚动层停在某个位置，方便逐屏截图 */
const SCROLL_TO = Number(new URLSearchParams(location.search).get('scroll') || 0);

/* ---------- 各模块独立预览状态（错误互不影响） ---------- */
const anniv = ref({ items: [], loading: !DEMO, error: '', ok: false });
const todo = ref({ items: [], loading: !DEMO, error: '', ok: false });
const bill = ref({ items: [], stats: null, loading: !DEMO, error: '', ok: false });
const me = ref({ profile: null, couple: null, error: '', ok: false });

/* 页头那行「自 2026.11.13」：没填起始日时 startDate 是绑定日兜底的，别拿它冒充 */
const sinceLabel = computed(() => (
  startFilled.value && relation.startDate
    ? '自 ' + relation.startDate.replace(/-/g, '.')
    : '还没记录在一起那天'
));

/* ---------- 纪念日派生 ---------- */
/* 起始日到底填了没：couple 里有 start_date 就是填了；还没拿到 couple 时，
   退到全局 relation.startSet（App 启动时已经算过一次） */
const startFilled = computed(() => {
  const c = me.value.couple;
  if (c) return !!c.start_date;
  return !!relation.startSet;
});
/* 没填起始日时，纪念日接口里那条「在一起」是拿绑定日兜底的 ——
   卡片上不能拿它冒充「下个日子」，先滤掉 */
const annivList = computed(() => (anniv.value.items || []).filter(
  i => !(i.source === 'relationship' && !startFilled.value)
));
const nearestAnniv = computed(() => annivList.value.find(i => !i.passed) || annivList.value[0] || {});

/* ---------- 清单派生 ---------- */
const todoDone = computed(() => todo.value.items.filter(i => i.status === 'completed').length);
const todoPending = computed(() => todo.value.items.filter(i => i.status === 'pending').length);
const todoProgress = computed(() => todo.value.items.length ? Math.round(todoDone.value / todo.value.items.length * 100) : 0);

/* ---------- 账本派生：账本只记钱 ---------- */
const billMoney = computed(() => bill.value.items.filter(b => b.type === 'money'));
const billMoneyCount = computed(() => billMoney.value.length);
const billLast = computed(() => billMoney.value[0] || null);

/* ---------- 数字滚动 ---------- */
const animatedDays = ref(0);
const animatedMoney = ref('0.00');
function countUp(target, duration, onTick) {
  const start = performance.now();
  function frame(now) {
    const p = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - p, 4);   // easeOutQuart：尾巴更长，停下来更像“落定”
    onTick(eased * target);
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* ---------- 格式化 ---------- */
function yearsText(item) {
  return item.source === 'birthday' ? `${item.years} 岁` : `第 ${item.years} 周年`;
}
const WEEK_CN = ['日', '一', '二', '三', '四', '五', '六'];
/* 纪念日卡上的日期：12 月 13 日 · 周五；不在今年就带上年份 */
function annivDateText(item) {
  const s = item && item.next_date;
  if (!s) return '';
  const [y, m, d] = String(s).split('-').map(Number);
  if (!y || !m || !d) return '';
  const wd = new Date(y, m - 1, d).getDay();
  const head = y === new Date().getFullYear() ? `${m} 月 ${d} 日` : `${y} 年 ${m} 月 ${d} 日`;
  return `${head} · 周${WEEK_CN[wd]}`;
}
function fmtMoney(v) {
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function maskPhone(p) {
  return p.length === 11 ? `${p.slice(0, 3)}****${p.slice(7)}` : p;
}

/* ---------- 滚动视差：只写 CSS 变量，不触发 Vue 重渲染 ---------- */
const viewEl = ref(null);
const heroEl = ref(null);
let scrollRaf = 0;
function onScroll() {
  if (scrollRaf) return;
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = 0;
    const el = viewEl.value;
    if (!el) return;
    const host = el.parentElement;
    if (!host) return;
    host.style.setProperty('--sy', `${Math.min(el.scrollTop, 900)}px`);
    host.style.setProperty('--sc', el.scrollTop > 8 ? '1' : '0');
  });
}

/* ---------- 眼睛跟随指针 ---------- */
function onPointer(e) {
  const r = heroEl.value?.getBoundingClientRect();
  if (!r) return;
  const nx = (e.clientX - r.left) / r.width - 0.5;
  const ny = (e.clientY - r.top) / r.height - 0.5;
  heroEl.value.style.setProperty('--px', (nx * 9).toFixed(2));
  heroEl.value.style.setProperty('--py', (ny * 7).toFixed(2));
  heroEl.value.style.setProperty('--mx', `${((e.clientX - r.left) / r.width * 100).toFixed(1)}%`);
  heroEl.value.style.setProperty('--my', `${((e.clientY - r.top) / r.height * 100).toFixed(1)}%`);
}
function resetPointer() {
  if (!heroEl.value) return;
  heroEl.value.style.setProperty('--px', '0');
  heroEl.value.style.setProperty('--py', '0');
}

/* ---------- 点一下：小怪物蹦一下 + 心形粒子散开 ---------- */
const boopOn = ref(false);
const particles = ref([]);
let burstSeq = 0;
function burst() {
  tap();
  boopOn.value = false;
  requestAnimationFrame(() => { boopOn.value = true; setTimeout(() => { boopOn.value = false; }, 620); });

  const id = ++burstSeq;
  particles.value = Array.from({ length: 14 }, (_, i) => {
    // 用 JS 算偏移，避免依赖 CSS 三角函数（老 WebView 不一定支持）
    const a = (i / 14) * Math.PI * 2 + Math.random() * 0.3;
    const d = 46 + Math.random() * 62;
    return {
      id: `${id}-${i}`,
      x: Math.round(Math.cos(a) * d),
      y: Math.round(Math.sin(a) * d - 14),
      s: 0.55 + Math.random() * 0.5,
      e: i % 3,
    };
  });
  setTimeout(() => { if (id === burstSeq) particles.value = []; }, 920);
}

/* ---------- 点击：传 origin 给 hero 转场（换算为相对屏幕容器坐标） ---------- */
function open(key, e) {
  const r = e.currentTarget.getBoundingClientRect();
  const host = document.getElementById('screen').getBoundingClientRect();
  emit('open', {
    key,
    rect: { x: r.x - host.x, y: r.y - host.y, w: r.width, h: r.height },
  });
}

/* 通知面板：全站只剩这一个 sheet，从「我们」页右上角打开 */
function openNotif() {
  tap();
  refreshUnread();
  engine.openSheet('notif');
}

/* ---------- 取数 ---------- */
function seedDemo() {
  anniv.value = {
    loading: false, error: '', ok: true,
    items: [
      { title: '四周年', next_date: '2027-06-18', days_left: 231, years: 4, source: 'together', passed: false },
      { title: '林深生日', next_date: '2027-03-09', days_left: 120, years: 25, source: 'birthday', passed: false },
    ],
  };
  todo.value = {
    loading: false, error: '', ok: true,
    items: [
      { title: '一起去看海', status: 'pending', type: 'shared' },
      { title: '把阳台种满薄荷', status: 'pending', type: 'shared' },
      { title: '看完那部三小时的电影', status: 'completed', type: 'shared' },
    ],
  };
  bill.value = {
    loading: false, error: '', ok: true,
    stats: { count: 18, shared_total: 1280.5, personal_total: 460, money_total: 1740.5 },
    items: [{ category: '一起吃了顿火锅', amount: 128.0, type: 'money' }],
  };
  me.value = {
    error: '', ok: true, couple: { id: 1 },
    profile: { nickname: '林深', phone: '13800006021', avatar_url: '' },
  };
  applyRelation({ date: '2023-06-18', next_date: '2027-06-18', days_left: 231, years: 4, source: 'relationship' });
  countUp(relation.days, 1200, v => { animatedDays.value = Math.round(v); });
  countUp(1740.5, 1000, v => { animatedMoney.value = fmtMoney(v); });
}

async function loadAll(animate = false) {
  if (DEMO) { seedDemo(); return; }

  listAnniversaries().then(items => {
    anniv.value = { items, loading: false, error: '', ok: true };
    // 用后端返回的「在一起」条目回填全局天数/周年/进度，和 hero 保持同一个数
    const rel = (items || []).find(i => i.source === 'relationship');
    /* 起始日没填时，后端那条是拿绑定日兜底的 —— 不能拿它算成「1 天」 */
    if (rel && relation.startSet) {
      applyRelation(rel);
      if (animate) countUp(relation.days, 1200, v => { animatedDays.value = Math.round(v); });
      else animatedDays.value = Math.round(relation.days);
    } else if (!relation.startSet) {
      animatedDays.value = 0;
    }
  }).catch(e => { anniv.value = { items: [], loading: false, error: e.message, ok: false }; });

  listTodos({ type: 'shared' }).then(items => { todo.value = { items, loading: false, error: '', ok: true }; })
    .catch(e => { todo.value = { items: [], loading: false, error: e.message, ok: false }; });

  Promise.all([listBills(), getBillStats()])
    .then(([items, stats]) => {
      bill.value = { items, stats, loading: false, error: '', ok: true };
      const total = Number(stats.money_total || 0);
      if (animate) countUp(total, 1000, v => { animatedMoney.value = fmtMoney(v); });
      else animatedMoney.value = fmtMoney(total);
    })
    .catch(e => { bill.value = { items: [], stats: null, loading: false, error: e.message, ok: false }; });

  Promise.all([getMe(), getCouple()])
    .then(([profile, couple]) => { me.value = { profile, couple, error: '', ok: true }; })
    .catch(e => { me.value = { profile: null, couple: null, error: e.message, ok: false }; });
}

/* 详情页里增删改之后回来，这一页的卡要跟着变，而不是停在进来那次的数据 */
const onDataChange = () => { loadAll(); };
/* 事件监听会把 Event 当第一个参数传进来，包一层免得数字滚动被误开 */
const onAuth = () => { loadAll(); };
const onCouple = () => { loadAll(); };
/* 切回「我们」页、或每 20 秒的静默广播：对方改了清单 / 账本 / 纪念日，
   这页上的四个小卡也要跟着变 */
const onSync = (ev) => {
  if (!props.active) return;
  const v = ev?.detail?.view;
  if (v && v !== 'me') return;
  loadAll();
};

onMounted(() => {
  loadAll(true);
  refreshUnread();
  /* 登录成功后重拉一次真实数据 */
  window.addEventListener('cove:auth', onAuth);
  /* 起始日在别处被填/改：这一页的天数与进度跟着重算 */
  window.addEventListener('cove:couple', onCouple);
  /* 纪念日 / 清单 / 账本里改过数据：回来时静默重拉，不重播数字滚动 */
  window.addEventListener('cove:data', onDataChange);
  window.addEventListener('cove:sync', onSync);

  if (SCROLL_TO) {
    const el = viewEl.value;
    setTimeout(() => { if (el) { el.scrollTop = SCROLL_TO; onScroll(); } }, 260);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('cove:auth', onAuth);
  window.removeEventListener('cove:couple', onCouple);
  window.removeEventListener('cove:data', onDataChange);
  window.removeEventListener('cove:sync', onSync);
});
</script>

<style scoped>
/* ============================================================
   我们 · 全息奶油（YomoaAI 语言）
   蜜桃 → 薰衣草 → 薄荷，黏土圆角，柔光投影，没有硬边框
   ============================================================ */
.view.mv{
  --cream:#FFF7F2;
  --ink:#2C1B2E;
  --ink2:#6A5570;
  --ink3:#9B87A1;
  --pink:#FF8FB8;
  --peach:#FFB489;
  --lilac:#B69CFF;
  --mint:#5FDCC0;
  --spring:cubic-bezier(.34,1.46,.5,1);
  --out:cubic-bezier(.22,1,.36,1);

  --sy:0px;
  position:absolute; inset:0; z-index:1;
  padding:0;                 /* 全局 .view 的 padding 交给内部滚动层处理 */
  overflow:hidden;
  /* 只让导航胶囊那一段（屏幕底部约 100px）透出玻璃，上面保持原来的奶油底，
     不要整页变透 —— 整页变透会让极光球的青绿直接怼在卡片上。 */
  background:linear-gradient(180deg,
    var(--cream) 0%,
    var(--cream) 88%,
    rgba(255,247,242,.66) 94%,
    rgba(255,247,242,0) 100%);
  color:var(--ink);
  font-family:var(--sans, -apple-system, 'PingFang SC', system-ui, sans-serif);
}
.mv-scroll{
  position:absolute; inset:0;
  overflow-y:auto; overflow-x:hidden;
  /* 58px 是给状态栏留的位置；有刘海 / 灵动岛的机型再多让 12px */
  padding:max(58px, calc(env(safe-area-inset-top,0px) + 24px)) 16px calc(160px + env(safe-area-inset-bottom,0px));
  scrollbar-width:none;
}
/* 底部压层：不用 mask，避免整层栅格化把文字弄糊。
   一层纸白渐变盖在内容上，滚到底部的内容自然消隐，胶囊区保持干净。 */
/* 底部压层：不用 mask（会把整层文字弄糊），改用一层几乎不透明的纸白渐变，
   滚到胶囊前面的内容被压掉；纸张颜色和引擎的纸底一致，接缝看不出来。 */
.mv-fade{
  position:absolute; left:0; right:0; bottom:0; height:150px;
  z-index:3; pointer-events:none;
  background:linear-gradient(180deg,
    rgba(255,247,250,0) 0%,
    rgba(255,247,250,.45) 18%,
    rgba(255,247,250,.94) 42%,
    rgba(255,247,250,.99) 70%,
    rgba(255,247,250,.995) 100%);
}
.mv-scroll::-webkit-scrollbar{ display:none; }

/* ---------- 背景极光 ---------- */
.mv-bg{
  position:absolute; inset:0; z-index:0;
  overflow:hidden; pointer-events:none;
  /* 底部一起收掉：光斑球原本一直铺到屏幕底，会在导航胶囊下面露出橙色圆。
     只收最底那一段，上面的极光保持原样。 */
  -webkit-mask-image:linear-gradient(180deg, #000 0, #000 88%, transparent 96%);
  mask-image:linear-gradient(180deg, #000 0, #000 88%, transparent 96%);
}
.mv-orbs{
  position:absolute; left:0; right:0; top:-12%; height:124%;
  transform:translate3d(0, calc(var(--sy,0px) * -.16), 0);
  will-change:transform;
}
.orb{
  position:absolute; border-radius:50%;
  filter:blur(46px);
  opacity:.72;
  animation:orbDrift 22s ease-in-out infinite alternate;
}
.orb--a{
  width:300px; height:300px; top:-90px; right:-100px;
  background:radial-gradient(circle at 35% 35%, #FFE0EC, #FF9FC2 62%, #D98BF0 100%);
}
.orb--b{
  width:330px; height:330px; top:300px; left:-150px;
  /* 这颗青色球一漂到卡片后面就把整页染绿，压淡一点，只当一层薄雾 */
  background:radial-gradient(circle at 40% 40%, #EFFFF9, #B9F3E2 58%, #8FD9E8 100%);
  opacity:.30;
  animation-duration:27s; animation-delay:-6s;
}
.orb--c{
  width:260px; height:260px; top:620px; right:-120px;
  background:radial-gradient(circle at 45% 40%, #FFF0DC, #FFC9A2 60%, #FFAB9E 100%);
  animation-duration:31s; animation-delay:-14s;
}
.mv-grain{
  position:absolute; inset:0;
  background-image:radial-gradient(rgba(120,80,130,.05) 1px, transparent 1px);
  background-size:4px 4px;
  opacity:.35;
}
@keyframes orbDrift{
  0%{ transform:translate3d(0,0,0) scale(1); }
  50%{ transform:translate3d(-26px,22px,0) scale(1.08); }
  100%{ transform:translate3d(18px,-18px,0) scale(.97); }
}

/* ---------- 标题 ---------- */
.mv-head{ position:relative; z-index:1; margin-bottom:16px; padding:0 6px; }
.mv-top{ display:flex; align-items:center; justify-content:space-between; }
.mv-eyebrow{
  display:flex; align-items:center; gap:6px;
  font-size:9.5px; font-weight:750; letter-spacing:.16em; color:var(--ink3);
}
.mv-spark{
  width:7px; height:7px; border-radius:50%;
  background:linear-gradient(140deg,#FFB3CE,#B69CFF);
  box-shadow:0 0 10px rgba(214,150,255,.65);
  animation:sparkPulse 2.6s ease-in-out infinite;
}
.mv-year{
  font-size:10.5px; font-weight:700; color:#8A5FA8;
  padding:5px 10px; border-radius:999px;
  background:linear-gradient(140deg, rgba(214,180,255,.42), rgba(255,178,206,.36));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.8), 0 8px 18px -14px rgba(150,90,180,.8);
}
/* 铃铛：跟「第 X 年」并排，白玻璃小圆扣，有未读才在右上角点一颗粉点 */
.mv-rt{ display:flex; align-items:center; gap:8px; }
.mv-bell{
  position:relative;
  width:30px; height:30px; border:0; border-radius:999px;
  display:grid; place-items:center;
  background:rgba(255,255,255,.74); color:#7C6389;
  cursor:pointer;
  box-shadow:inset 0 1px 0 #fff, 0 8px 18px -14px rgba(150,90,180,.8);
  transition:transform .22s cubic-bezier(.34,1.4,.64,1), background .22s ease;
}
.mv-bell:active{ transform:scale(.94); background:#fff; }
.mv-bell__dot{
  position:absolute; top:4px; right:4px;
  width:6px; height:6px; border-radius:50%;
  background:linear-gradient(140deg,#FF7099,#FF4B7E);
  box-shadow:0 0 0 1.5px rgba(255,255,255,.9);
}
.mv-title{
  margin:6px 0 0; font-size:36px; line-height:1.02; letter-spacing:-.045em; font-weight:820;
  background:linear-gradient(120deg,#3B2140 10%, #6C3C74 55%, #B25F86 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.mv-since{ margin:8px 0 0; font-size:11.5px; letter-spacing:.02em; color:var(--ink3); }

/* ---------- 关系主卡 ---------- */
.hero{
  position:relative; z-index:1; overflow:hidden;
  margin:0 0 14px; padding:0;
  height:330px; border-radius:34px;
  cursor:pointer;
  -webkit-tap-highlight-color:transparent;
  /* 卡片自己的底色要压得住，别让背景极光把整张卡染色：
     基础是近乎不透明的白，四个主题色只留很淡的一层，颜色主要靠左上角的小图标。 */
  background:
    radial-gradient(120% 92% at 84% 4%, rgba(255,238,244,.82) 0%, rgba(255,238,244,0) 54%),
    radial-gradient(120% 100% at 6% 100%, rgba(240,250,246,.72) 0%, rgba(240,250,246,0) 58%),
    linear-gradient(145deg,#FFFAF5 0%,#FDF6FB 50%,#FDF8F9 100%);
  box-shadow:
    0 30px 58px -36px rgba(160,80,140,.62),
    0 8px 18px -12px rgba(160,80,140,.24),
    inset 0 1px 0 rgba(255,255,255,.9),
    inset 0 0 0 1px rgba(255,255,255,.55);
  transition:transform .5s var(--spring), box-shadow .4s var(--out);
}
.hero:active{ transform:scale(.982); box-shadow:0 18px 34px -26px rgba(150,80,140,.5); }

/* 指针跟随的柔光 */
.hero-sheen{
  position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(120px 120px at var(--mx,78%) var(--my,12%), rgba(255,255,255,.5), transparent 70%);
  mix-blend-mode:soft-light; opacity:.9;
}
/* 底部薄雾：保证大数字压在粉色小怪物上依然清楚 */
.hero::after{
  content:''; position:absolute; left:0; right:0; bottom:0; height:158px;
  background:linear-gradient(0deg, rgba(255,250,245,.9) 0%, rgba(255,250,245,.55) 52%, rgba(255,250,245,0) 100%);
  pointer-events:none; z-index:1;
}

/* 两只小怪物 */
.blobs{ position:absolute; inset:0; pointer-events:none; }
.blob{
  position:absolute;
  width:152px; height:136px;
  border-radius:54% 46% 42% 58% / 56% 58% 42% 44%;
  transform-origin:52% 88%;
  animation:breathe 5.4s ease-in-out infinite;
  will-change:transform;
}
.blob--ta{
  top:14px; right:18px;
  width:146px; height:130px;
  background:
    radial-gradient(120% 110% at 28% 18%, rgba(255,255,255,.55) 0%, rgba(255,255,255,0) 46%),
    linear-gradient(155deg,#C6FBEA 0%, #7BEBD1 42%, #37C9C4 100%);
  box-shadow:
    inset -16px -22px 34px rgba(10,120,120,.22),
    inset 14px 16px 26px rgba(255,255,255,.55),
    0 30px 44px -26px rgba(40,180,170,.55);
  animation-delay:-1.2s;
}
.blob--me{
  top:54px; left:26px;
  width:136px; height:118px;
  background:
    radial-gradient(120% 110% at 30% 16%, rgba(255,255,255,.6) 0%, rgba(255,255,255,0) 46%),
    linear-gradient(155deg,#FFD9E6 0%, #FF9EC0 44%, #D98BF0 100%);
  box-shadow:
    inset -16px -20px 32px rgba(150,30,110,.2),
    inset 14px 14px 24px rgba(255,255,255,.55),
    0 30px 44px -26px rgba(210,90,160,.55);
}
.blob-shine{
  position:absolute; top:14%; left:16%; width:44%; height:26%;
  border-radius:50%;
  background:radial-gradient(closest-side, rgba(255,255,255,.8), rgba(255,255,255,0));
  filter:blur(2px); transform:rotate(-16deg);
}
@keyframes breathe{
  0%,100%{ transform:scale(1,1) rotate(-1.5deg); }
  50%{ transform:scale(1.045,.965) rotate(1.5deg); }
}

/* 眼睛 */
.eye{
  position:absolute; width:34px; height:38px; border-radius:50%;
  background:linear-gradient(180deg,#FFFFFF,#F4EEF8);
  box-shadow:inset 0 -3px 6px rgba(120,90,140,.16);
  overflow:hidden;
  animation:blink 6.4s ease-in-out infinite;
}
.eye--l{ top:26%; left:18%; transform:rotate(-8deg); }
.eye--r{ top:24%; left:46%; transform:rotate(6deg); animation-delay:-.18s; }
.pupil{
  position:absolute; top:24%; left:24%; width:17px; height:22px; border-radius:50%;
  background:radial-gradient(circle at 34% 28%, #5A4460 0%, #1E1424 60%, #120C17 100%);
  transform:translate(calc(var(--px,0) * 1px), calc(var(--py,0) * 1px));
  transition:transform .3s var(--out);
}
.pupil::after{
  content:''; position:absolute; top:12%; right:14%; width:5px; height:5px;
  border-radius:50%; background:rgba(255,255,255,.85); filter:blur(.4px);
}
@keyframes blink{
  0%, 92%, 100%{ transform:scaleY(1) rotate(var(--rot,-8deg)); }
  95%{ transform:scaleY(.1) rotate(var(--rot,-8deg)); }
}
.eye--l{ --rot:-8deg; }
.eye--r{ --rot:6deg; }

/* 中间的小心脏 */
.core-heart{
  position:absolute; left:50%; top:46%; width:22px; height:22px; margin:-11px 0 0 -11px;
  color:#FF6E9E; filter:drop-shadow(0 6px 10px rgba(255,110,158,.5));
  animation:heartBeat 2.8s ease-in-out infinite;
}
.core-heart svg{ width:100%; height:100%; display:block; opacity:.92; }
@keyframes heartBeat{
  0%,100%{ transform:scale(.9); }
  14%{ transform:scale(1.16); }
  28%{ transform:scale(.96); }
  42%{ transform:scale(1.08); }
  70%{ transform:scale(.9); }
}

/* 点击迸发的心 */
.bursts{ position:absolute; left:50%; top:46%; width:0; height:0; }
.spark{
  position:absolute; width:9px; height:9px; left:-4.5px; top:-4.5px;
  border-radius:50% 50% 48% 48% / 60% 60% 40% 40%;
  background:linear-gradient(160deg, #FFD3E3, #FF7BAF 55%, #C97BFF);
  box-shadow:0 4px 10px rgba(255,110,160,.4);
  opacity:0;
  animation:sparkOut .9s var(--out) forwards;
  animation-delay:calc(var(--e) * 40ms);
}
.spark::after{
  content:''; position:absolute; inset:0; border-radius:inherit;
  border:1.5px solid rgba(255,255,255,.55);
}
@keyframes sparkOut{
  0%{ opacity:0; transform:translate(0,0) scale(.4) rotate(0); }
  18%{ opacity:1; }
  100%{
    opacity:0;
    transform:translate(var(--x), var(--y)) scale(var(--s)) rotate(40deg);
  }
}

/* 主卡文案 */
.hero-body{
  position:absolute; left:22px; right:22px; bottom:22px; z-index:2;
  pointer-events:none;
}
.hero-eyebrow{ font-size:10px; font-weight:750; letter-spacing:.16em; color:rgba(60,30,60,.52); }
.hero-num{ display:flex; align-items:baseline; gap:5px; margin-top:2px; }
.hero-num b{
  font-size:52px; line-height:1; font-weight:840; letter-spacing:-.055em;
  font-variant-numeric:tabular-nums;
  background:linear-gradient(120deg,#3A1E3E,#7B3F6E 58%,#B65C86);
  -webkit-background-clip:text; background-clip:text; color:transparent;
  filter:drop-shadow(0 6px 12px rgba(160,80,130,.18));
}
.hero-num span{ font-size:13px; font-weight:700; color:rgba(60,30,60,.5); }
/* 起始日没填：别摆一个 52px 的 0，换成一行「待填」 */
.hero-num--todo b{
  font-size:26px; letter-spacing:-.02em;
  background:linear-gradient(120deg,#C24B6A,#E0407A);
  -webkit-background-clip:text; background-clip:text;
}

.hero-track{
  position:relative; height:8px; margin-top:10px; border-radius:99px;
  background:rgba(255,255,255,.55);
  box-shadow:inset 0 1px 3px rgba(130,80,120,.18);
}
.hero-track i{
  position:absolute; left:0; top:0; bottom:0; border-radius:99px;
  background:linear-gradient(90deg,#FFB3CE,#C89BFF 58%,#6FE3C8);
  box-shadow:0 4px 12px rgba(200,130,220,.42);
  transition:width 1.4s var(--out);
}
.hero-track em{
  position:absolute; top:50%; width:14px; height:14px; margin:-7px 0 0 -7px;
  border-radius:50%;
  background:radial-gradient(circle at 34% 30%, #fff, #FFD6E6 45%, #C29BFF 100%);
  box-shadow:0 0 0 3px rgba(255,255,255,.45), 0 6px 14px rgba(190,120,210,.5);
  transition:left 1.4s var(--out);
}
.hero-foot{ margin:9px 0 0; font-size:11px; line-height:1.5; color:rgba(60,30,60,.5); }
.hero-foot b{ color:rgba(60,30,60,.82); font-weight:750; }

/* ---------- 卡片通用 ---------- */
.mv-card{
  position:relative; z-index:1;
  margin:0 0 13px; padding:15px 16px 16px;
  border-radius:26px;
  background:linear-gradient(160deg, rgba(255,255,255,.99), rgba(255,255,255,.97));
  box-shadow:
    0 22px 42px -30px rgba(120,55,110,.72),
    0 6px 14px -10px rgba(120,55,110,.26),
    inset 0 1px 0 rgba(255,255,255,.95),
    inset 0 0 0 1px rgba(255,255,255,.75);
  cursor:pointer;
  -webkit-tap-highlight-color:transparent;
  transition:transform .42s var(--spring), box-shadow .3s var(--out);
}
.mv-card:active{ transform:scale(.972); box-shadow:0 10px 20px -18px rgba(120,60,120,.5), inset 0 1px 0 #fff; }
.card--anniv{ background:linear-gradient(160deg, rgba(247,242,255,.99), rgba(255,255,255,.97)); }
.card--todo{ background:linear-gradient(160deg, rgba(240,252,248,.99), rgba(255,255,255,.97)); }
.card--bill{ background:linear-gradient(160deg, rgba(255,248,243,.99), rgba(255,255,255,.97)); }
.card--set{ background:linear-gradient(160deg, rgba(255,245,249,.99), rgba(255,255,255,.97)); }

.c-head{ display:flex; align-items:center; gap:9px; }
.c-ic{
  width:34px; height:34px; border-radius:13px; flex:0 0 auto;
  display:flex; align-items:center; justify-content:center; color:#fff;
  box-shadow:0 8px 16px -8px var(--chipShadow), inset 0 1px 0 rgba(255,255,255,.55);
  background:linear-gradient(150deg, var(--chip), var(--chip2));
}
.card--anniv{ --chip:#B69CFF; --chip2:#8F72F0; --chipShadow:rgba(140,100,220,.55); }
.card--todo{ --chip:#67E2C6; --chip2:#2FBE9E; --chipShadow:rgba(40,190,160,.55); }
.card--bill{ --chip:#FFB489; --chip2:#F58A5E; --chipShadow:rgba(240,140,90,.55); }
.card--set{ --chip:#FF9EC0; --chip2:#F06E9C; --chipShadow:rgba(235,110,155,.55); }
.c-name{ font-size:14px; font-weight:780; letter-spacing:-.015em; }
.c-pill{
  margin-left:auto; font-size:10px; font-weight:750; letter-spacing:.02em;
  padding:4px 9px; border-radius:99px; color:var(--ink2);
  background:rgba(255,255,255,.72);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.9), 0 6px 12px -10px rgba(120,70,120,.6);
}
.c-pill.soft.on{ color:#178A6D; background:rgba(120,225,195,.28); }
.c-pill + .chev{ margin-left:8px; }
.chev{ margin-left:auto; color:var(--ink3); display:flex; opacity:.55; }

.c-note{ margin:14px 0 2px; font-size:12px; line-height:1.5; color:var(--ink3); }
.c-skel{ margin-top:14px; display:flex; flex-direction:column; gap:7px; }
.c-skel i{
  display:block; height:8px; border-radius:99px;
  background:linear-gradient(90deg, rgba(255,255,255,.5), rgba(230,220,235,.55), rgba(255,255,255,.5));
  background-size:200% 100%;
  animation:shimmer 1.4s linear infinite;
}
.c-skel i:nth-child(2){ width:62%; animation-delay:.12s; }
@keyframes shimmer{ from{ background-position:120% 0; } to{ background-position:-120% 0; } }

/* ---------- 纪念日 ---------- */
/* 读的顺序：下个日子 → 是什么日子（最重）→ 哪一天 */
.anniv{ display:flex; align-items:center; gap:12px; margin-top:13px; }
.anniv-main{ flex:1; min-width:0; display:flex; flex-direction:column; gap:3px; }
.anniv-sub{
  display:flex; align-items:baseline; gap:5px; min-width:0;
  white-space:nowrap; overflow:hidden;
}
.anniv-sub__lb{
  flex:0 0 auto; font-style:normal; font-size:9.5px; font-weight:600;
  letter-spacing:.04em; color:#8E7CA6;
}
.anniv-title{
  font-size:16.5px; font-weight:800; letter-spacing:-.02em; color:#4B2C63;
  line-height:1.15;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
/* 「· 第 3 周年」跟主标题同一号字：它是这张卡的第二个信息，
   不能缩成脚注大小，否则一眼只读到「在一起」 */
.anniv-title em{
  font-style:normal; font-size:16.5px; font-weight:700; color:#7C6B8A; letter-spacing:-.01em;
}
.anniv-date{
  font-size:11px; font-weight:600; color:#8B7C93;
  font-variant-numeric:tabular-nums;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.anniv-badge{
  flex:0 0 auto; display:flex; flex-direction:column; align-items:flex-end; gap:1px;
  padding:7px 11px 8px; border-radius:16px;
  background:linear-gradient(150deg, rgba(255,255,255,.95), rgba(245,235,255,.95));
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.9), 0 10px 18px -14px rgba(140,90,200,.8);
  font-variant-numeric:tabular-nums;
}
/* 「还有 / 已经」摆在数字上面：只写个 279 天，跟「已经 817 天」分不出来 */
.anniv-badge__lb{
  font-style:normal; font-size:9px; font-weight:700;
  letter-spacing:.16em; color:#A395B8; line-height:1;
}
.anniv-badge__n{ display:flex; align-items:baseline; gap:2px; }
.anniv-badge b{ font-size:22px; line-height:1; font-weight:840; color:#6B3A8C; letter-spacing:-.03em; }
.anniv-badge small{ font-size:9.5px; font-weight:700; color:var(--ink3); }
.anniv-badge.is-today{
  padding:9px 13px; font-size:12px; font-weight:800; color:#fff;
  background:linear-gradient(140deg,#FF9EC0,#C58BFF);
  box-shadow:0 10px 22px -12px rgba(200,110,190,.9);
}

/* ---------- 清单 ---------- */
.todo{ margin-top:14px; }
.todo-top{ display:flex; align-items:baseline; gap:8px; }
.todo-count{ font-variant-numeric:tabular-nums; letter-spacing:-.03em; }
.todo-count b{ font-size:28px; font-weight:840; }
.todo-count small{ font-size:12px; font-weight:700; color:var(--ink3); }
.todo-cap{ margin-left:auto; font-size:10.5px; color:var(--ink3); }
.todo-bar{
  height:7px; margin:8px 0 0; border-radius:99px; overflow:hidden;
  background:rgba(46,120,105,.12);
}
.todo-bar i{
  display:block; height:100%; border-radius:99px;
  background:linear-gradient(90deg,#9FF3DE,#41D5B4);
  box-shadow:0 2px 8px rgba(60,200,170,.5);
  transition:width 1.1s var(--out);
}

/* ---------- 账本 ---------- */
.bill{ margin-top:12px; }
.bill-num{ display:flex; align-items:baseline; gap:3px; }
.bill-cny{ font-size:15px; font-weight:800; color:#B4684A; }
.bill-fig{
  font-size:34px; line-height:1.05; font-weight:840; letter-spacing:-.045em;
  font-variant-numeric:tabular-nums;
  background:linear-gradient(120deg,#4A2B28,#B4653F 60%,#E08C55);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.bill-chips{ display:flex; gap:8px; margin-top:9px; }
.bill-chips span{
  font-size:10px; color:#8A6053; padding:5px 10px; border-radius:99px;
  background:rgba(255,255,255,.72);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.9);
}
.bill-chips b{ font-weight:800; color:#5E3629; font-variant-numeric:tabular-nums; }
.bill-last{
  margin:10px 0 0; font-size:10.5px; color:var(--ink3);
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.bill-last b{ color:#A2664F; font-weight:750; }

/* ---------- 设置 ---------- */
.set{ display:flex; align-items:center; gap:12px; margin-top:14px; }
.avatar{
  width:46px; height:46px; border-radius:18px; overflow:hidden; flex:0 0 auto;
  display:flex; align-items:center; justify-content:center;
  font-size:17px; font-weight:820; color:#7B4B6E;
  background:linear-gradient(150deg,#FFE3EF,#FFC2D8);
  box-shadow:0 12px 22px -14px rgba(220,120,170,.9), inset 0 1px 0 rgba(255,255,255,.9);
}
.avatar img{ width:100%; height:100%; object-fit:cover; }
.set-main{ flex:1; min-width:0; display:flex; flex-direction:column; gap:3px; }
.set-name{ font-size:14px; font-weight:780; }
.set-sub{ font-size:10.5px; color:var(--ink3); font-variant-numeric:tabular-nums; }

/* 底栏那一块不再自己补一块假玻璃：本页底色改成底部渐隐，露出引擎画的那层玻璃，
   和其它三页用同一块胶囊。原来那块 .mv-dock 和导航胶囊同位置同尺寸叠着，
   等于两层壳，边缘还各自带阴影，所以这一页的导航看着总像"多出来一圈"。 */

/* 顶部渐隐：只在下滑后出现，避免和状态栏打架 */
.view.mv .mv-topfade{
  position:absolute; top:0; left:0; right:0; height:124px; z-index:3;
  pointer-events:none; opacity:var(--sc,0);
  transition:opacity .3s var(--out);
  background:linear-gradient(180deg,
    rgba(255,247,242,.99) 0%,
    rgba(255,247,242,.96) 32%,
    rgba(255,247,242,.62) 66%,
    rgba(255,247,242,0) 100%);
}

/* ---------- 入场动画：和全局 rise 分开，避免打架 ---------- */
.view.mv.on > *{ animation:none; }
.view.mv.on .mv-bg{ animation:bgIn 1.2s var(--out) both; }
.view.mv.on .mv-head{ animation:headIn .8s var(--spring) both; }
.view.mv.on .hero{ animation:heroIn 1s var(--spring) both; animation-delay:.06s; }
.view.mv.on .mv-card{
  animation:cardIn .82s var(--spring) both;
  animation-delay:calc(.14s + var(--i) * .075s);
}

@keyframes bgIn{ from{ opacity:0; } to{ opacity:1; } }
@keyframes headIn{
  from{ opacity:0; transform:translateY(14px) scale(.98); filter:blur(6px); }
  to{ opacity:1; transform:none; filter:none; }
}
@keyframes heroIn{
  0%{ opacity:0; transform:translateY(26px) scale(.955); filter:blur(8px); }
  60%{ opacity:1; }
  100%{ opacity:1; transform:none; filter:none; }
}
@keyframes cardIn{
  0%{ opacity:0; transform:translateY(20px) scale(.97); filter:blur(5px); }
  100%{ opacity:1; transform:none; filter:none; }
}
@keyframes fadeIn{ from{ opacity:0; } to{ opacity:.75; } }
@keyframes sparkPulse{
  0%,100%{ transform:scale(.85); opacity:.7; }
  50%{ transform:scale(1.15); opacity:1; }
}

/* 点一下的“蹦” */
.hero.boop .blob--me{ animation:boop .6s var(--spring); }
.hero.boop .blob--ta{ animation:boop .6s var(--spring) .04s; }
@keyframes boop{
  0%{ transform:scale(1,1); }
  35%{ transform:scale(1.12,.86) translateY(2px); }
  65%{ transform:scale(.94,1.08) translateY(-4px); }
  100%{ transform:scale(1,1); }
}

/* ---------- 减少动态 ---------- */
@media (prefers-reduced-motion: reduce){
  .orb, .blob, .eye, .core-heart, .spark, .mv-spark{ animation:none !important; }
  .view.mv.on .mv-bg, .view.mv.on .mv-head, .view.mv.on .hero,
  .view.mv.on .mv-card{
    animation:none !important; opacity:1 !important; transform:none !important; filter:none !important;
  }
  .hero, .mv-card, .hero-track i, .hero-track em, .todo-bar i{ transition-duration:.01ms !important; }
}
</style>
