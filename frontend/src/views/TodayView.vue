<template>
<section class="view today-view" :class="{ on: active }" data-view="today">
  <!-- 顶部固定区：hero 在这里，不随内容滚动，只做收缩 -->
  <div class="today-hero">
    <div
      class="hero glass"
      ref="heroEl"
      :class="{ 'hero--todo': !relation.startSet, 'hero--press': pressing }"
      :data-push="relation.startSet ? null : 'start'"
      :role="relation.startSet ? null : 'button'"
      :tabindex="relation.startSet ? null : 0"
      @pointerdown="press(true)"
      @pointerup="press(false)"
      @pointercancel="press(false)"
      @pointerleave="press(false)"
    >
      <div class="hero__top">
        <div>
          <div class="hero__eyebrow">{{ todayLabel }}</div>
          <h1 class="hero__title">{{ greeting }}，{{ me.nickname || '你' }}</h1>
        </div>
        <!-- 填了起始日：大数字；没填：一枚「待填」小标，别用 0 天冒充 -->
        <span v-if="relation.startSet" class="hero__num">
          <b :key="relation.days">{{ relation.days }}</b><small>天</small>
        </span>
        <span v-else class="hero__todo">待填</span>
      </div>

      <template v-if="relation.startSet">
        <div class="hero__bar"><i :style="{ width: relation.progress + '%' }"></i></div>
        <div class="hero__cap">第 {{ relation.years }} 周年走过 {{ relation.progress }}% · 还有 {{ relation.daysToAnniv }} 天</div>
      </template>

      <!-- 还没填起始日：整张卡就是入口，点哪儿都能去填 -->
      <template v-else>
        <div class="hero__cue">
          <span class="hero__cue-ic">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <rect x="4" y="5.6" width="16" height="14.4" rx="3.4" />
              <path d="M8 3.6v3.4M16 3.6v3.4M4 10.4h16" />
              <path d="M9 14.6h2.2M13.4 14.6h2.2" />
            </svg>
          </span>
          <span class="hero__cue-tx">
            <b>还没填你们的恋爱纪念日</b>
            <span>填上就能开始数天数</span>
          </span>
          <span class="hero__cue-go">
            去填
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <path d="m9.5 6 6 6-6 6" />
            </svg>
          </span>
        </div>
      </template>
    </div>
  </div>

  <!-- 独立滚动内容区 -->
  <div class="today-scroll" ref="scrollEl">
    <div class="chips">
      <button class="chip glass" data-push="simta">
        <span class="chip__ic ic-coral">TA</span>
        <span class="chip__b">
          <b>模拟 Ta</b>
          <span class="chip__m">{{ simtaChip.sub }}</span>
        </span>
      </button>
      <button class="chip glass" data-push="mall">
        <span class="chip__ic ic-gold">店</span>
        <span class="chip__b">
          <span class="chip__t">商城</span>
          <b>{{ mallChip.big }}</b>
          <span class="chip__m">{{ mallChip.sub }}</span>
        </span>
      </button>
    </div>

    <!-- 恋爱账本：从「我们」页搬一张到首页，压在模拟 Ta / 商城两枚入口下面 -->
    <button class="ledger glass" data-push="bill" aria-label="打开恋爱账本">
      <span class="lg-top">
        <span class="lg-ic" v-html="WALLET"></span>
        <span class="lg-name">恋爱账本</span>
        <span class="lg-right">
          <span class="lg-pill" v-if="ledger.count">{{ ledger.count }} 笔</span>
          <span class="lg-chev" v-html="CHEV"></span>
        </span>
      </span>
      <span class="lg-num"><i>¥</i>{{ ledger.total }}</span>
      <span class="lg-chips">
        <span class="lg-chip">共同 <b>{{ ledger.shared }}</b></span>
        <span class="lg-chip">个人 <b>{{ ledger.personal }}</b></span>
      </span>
      <span class="lg-last" v-if="ledger.last">
        最近一笔 · {{ ledger.last.category }} <b>¥{{ fmtMoney(ledger.last.amount) }}</b>
      </span>
      <span class="lg-last" v-else-if="ledger.unbound">绑定 TA 之后，就能一起记账</span>
      <span class="lg-last" v-else>还没有记账，去记第一笔</span>
    </button>

    <MoodDeck />
    <QuestionPanel />
  </div>
</section>
</template>


<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { todayLabel, relation, me, loadRelation, loadMe } from '../composables/useCove.js';
import { getSimtaState } from '../api/simta.js';
import { listMyItems, listOrders } from '../api/mall.js';
import { listBills, getBillStats } from '../api/bills.js';
import MoodDeck from '../components/MoodDeck.vue';
import QuestionPanel from '../components/QuestionPanel.vue';

const props = defineProps({ active: Boolean });

const scrollEl = ref(null);
const heroEl = ref(null);
/* 手机上没有 :active 的可靠消息（合成触摸 / 长按滑动都会漏），
   自己用 pointer 事件驱动按下态，反馈才跟手 */
const pressing = ref(false);
function press(on) {
  if (relation.startSet) return;   // 正常态那张卡不可点，不摆按压动作
  pressing.value = on;
}
// 在这段滚动距离内完成全部收缩，跟手连续、无额外阈值
const COLLAPSE_DIST = 70;

/* 问候语跟真实时间走：写死「早安」到下午还挂着，看着就不对 */
const nowTs = ref(Date.now());
let tickTimer = null;
const greeting = computed(() => {
  const d = new Date(nowTs.value);
  const mins = d.getHours() * 60 + d.getMinutes();
  if (mins >= 5 * 60 && mins < 9 * 60) return '早安';
  if (mins >= 9 * 60 && mins < 11 * 60 + 30) return '上午好';
  if (mins >= 11 * 60 + 30 && mins < 13 * 60 + 30) return '中午好';
  if (mins >= 13 * 60 + 30 && mins < 18 * 60) return '下午好';
  if (mins >= 18 * 60 && mins < 23 * 60) return '晚上好';
  return '夜深了';
});

function onScroll() {
  const c = Math.min(1, Math.max(0, scrollEl.value.scrollTop / COLLAPSE_DIST));
  heroEl.value.style.setProperty('--c', c.toFixed(4));
}

/* 天数与昵称都来自后端；登录页是在本视图已经挂载之后才关掉的，
   所以登录成功要再拉一次，否则进来还是 0 天 / 空昵称 */
function pullLive() {
  loadRelation();
  loadMe();
}

/* 顶部两枚小卡的数也必须是真的：模拟 Ta 的授权状态、商城的商品/订单数 */
/* 模拟 Ta 这枚只报状态，不写花名：卡片上就「模拟 Ta」一个词 + 一个短状态，
   太长的话入口反而看不清是干什么的 */
const simtaChip = ref({ sub: '未开启' });
const mallChip = ref({ big: '去逛逛', sub: '还没有上架商品' });

async function pullChips() {
  try {
    const s = await getSimtaState();
    const ours = !!s?.my_consent;
    const theirs = !!s?.partner_consent;
    if (ours && theirs) {
      simtaChip.value = { sub: '已开启' };
    } else if (ours) {
      simtaChip.value = { sub: '等 TA 授权' };
    } else {
      simtaChip.value = { sub: '未开启' };
    }
  } catch (_) {
    simtaChip.value = { sub: '未开启' };
  }

  try {
    const [items, orders] = await Promise.all([listMyItems(), listOrders()]);
    const n = (items || []).length;
    const pending = (orders || []).filter((o) => o.status === 'pending').length;
    if (n) {
      mallChip.value = {
        big: `${n} 件`,
        sub: pending ? `${pending} 件待核销` : '没有待核销',
      };
    } else {
      mallChip.value = { big: '去逛逛', sub: '还没有上架商品' };
    }
  } catch (_) {
    mallChip.value = { big: '去逛逛', sub: '还没有上架商品' };
  }
}

function pullAll() {
  pullLive();
  pullChips();
  pullLedger();
}

/* ---------- 恋爱账本入口卡 ---------- */
const WALLET = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.8" y="6" width="18.4" height="13" rx="4"/><path d="M2.8 10.2h18.4"/><circle cx="16.8" cy="13.6" r="1.3" fill="currentColor" stroke="none"/></svg>';
const CHEV = '<svg width="8" height="13" viewBox="0 0 8 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m1.6 1.6 4.8 4.9-4.8 4.9"/></svg>';

const ledger = ref({ total: '0.00', shared: '0.00', personal: '0.00', count: 0, last: null, unbound: false });

function fmtMoney(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/* 账本是「两个人的钱」，没绑定的人后端直接 409 —— 这种时候说「去记第一笔」
   会把人推进一个记不了账的页面，得改成提示先绑定 */
async function pullLedger() {
  try {
    const [items, stats] = await Promise.all([listBills(), getBillStats()]);
    const money = (items || []).filter((b) => b && b.type === 'money');
    ledger.value = {
      total: fmtMoney(stats && stats.money_total),
      shared: fmtMoney(stats && stats.shared_total),
      personal: fmtMoney(stats && stats.personal_total),
      count: (stats && stats.count) ?? money.length,
      last: money[0] || null,
      unbound: false,
    };
  } catch (e) {
    const unbound = (e && e.status === 409) || /绑定/.test((e && e.message) || '');
    ledger.value = { total: '0.00', shared: '0.00', personal: '0.00', count: 0, last: null, unbound };
  }
}

/* 首页是「今天两个人的状态」：切回来、以及每 20 秒的静默广播都要重拉，
   不然对方换了心情、答了今日问题，这边还挂着进来那一天的旧卡片。
   心情卡 / 今日问答是子组件，用 cove:home 通知它们自己刷新。 */
let lastSyncAt = 0;
function refreshHome() {
  if (Date.now() - lastSyncAt < 2000) return;
  lastSyncAt = Date.now();
  pullAll();
  window.dispatchEvent(new Event('cove:home'));
}
function onGlobalSync(ev) {
  if (!props.active) return;
  const v = ev?.detail?.view;
  if (v && v !== 'today') return;
  refreshHome();
}
/* 从别页切回首页那一刻就要是最新的，不等 20 秒的广播 */
watch(() => props.active, (on) => { if (on) refreshHome(); });

onMounted(() => {
  scrollEl.value.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  pullAll();
  window.addEventListener('cove:auth', pullAll);
  window.addEventListener('cove:sync', onGlobalSync);
  /* 在「模拟 Ta」页里改了授权：回来这枚小卡要立刻变，不用等下次刷新 */
  window.addEventListener('cove:simta', pullChips);
  // 跨过时段边界时（比如 11:29 → 11:30）问候语自己换掉，不用重进页面
  tickTimer = setInterval(() => { nowTs.value = Date.now(); }, 60_000);
});

onBeforeUnmount(() => {
  scrollEl.value?.removeEventListener('scroll', onScroll);
  window.removeEventListener('cove:auth', pullAll);
  window.removeEventListener('cove:sync', onGlobalSync);
  window.removeEventListener('cove:simta', pullChips);
  if (tickTimer) clearInterval(tickTimer);
});
</script>

<style scoped>
/* 覆盖默认 .view：今天页改成 flex 列，外层不滚动，由内部 .today-scroll 滚动。
   用 .view.today-view 双类提高特异性，确保压过全局 .view[data-view="today"] 的 padding-top:66 */
.view.today-view {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 顶部固定区：从状态栏下方开始，不收缩宽度只收缩高度；
   max() 让有刘海 / 灵动岛的机型再多让一点，桌面预览保持 66px */
.today-hero {
  flex: none;
  padding: max(66px, calc(env(safe-area-inset-top, 0px) + 30px)) 16px 0;
}
.today-hero .hero {
  margin-bottom: 0;
  /* 提白：白色底更实，背景粉雾透得更少，跟下方卡片统一 */
  background: linear-gradient(180deg, rgba(255, 255, 255, .92), rgba(255, 255, 255, .78));
}

/* 内容滚动区：占满剩余高度，左右内边距，底部给底部导航留空间 */
.today-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 18px 16px 120px;
  scrollbar-width: none;
}
.today-scroll::-webkit-scrollbar { display: none; }
.today-scroll .chips { margin-top: 0; }

/* 调白：给卡片加近实白底色，背景粉色透不上来，文字更清楚，仍保留一点玻璃通透 */
.today-scroll .chip {
  background: rgba(255, 255, 255, .9);
  box-shadow: 0 12px 26px -18px rgba(120, 60, 90, .4), inset 0 0 0 .5px rgba(255, 255, 255, .9);
}
/* 文字图标方块里的字居中、白色 */
.today-scroll .chip__ic {
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: .02em;
}

/* ============================================================
   恋爱账本入口卡（整宽，压在两枚入口卡下面）
   暖橙是账本自己的色，跟粉调首页拉开一点，一眼能认出是钱的事
   ============================================================ */
.today-scroll .ledger {
  display: block;
  width: 100%;
  margin-top: 10px;
  padding: 14px 15px 13px;
  text-align: left;
  border-radius: 22px;
  background: rgba(255, 255, 255, .92);
  box-shadow: 0 12px 26px -18px rgba(120, 60, 90, .4), inset 0 0 0 .5px rgba(255, 255, 255, .9);
  -webkit-tap-highlight-color: transparent;
  transition: transform .18s cubic-bezier(.22, 1, .36, 1);
}
.today-scroll .ledger:active { transform: scale(.995); }

.lg-top { display: flex; align-items: center; gap: 8px; }
.lg-ic {
  flex: none; width: 26px; height: 26px;
  display: grid; place-items: center;
  border-radius: 9px;
  color: #fff;
  background: linear-gradient(180deg, #FFA85C, #FF7A2F);
  box-shadow: 0 8px 14px -10px rgba(255, 122, 47, .95);
}
.lg-name { font-size: 13px; font-weight: 800; color: #3A1C2C; letter-spacing: -.01em; }
/* 右侧「N 笔」+ 箭头成组贴右：没有笔数时箭头也不会挤到标题旁边 */
.lg-right { margin-left: auto; display: inline-flex; align-items: center; gap: 7px; }
.lg-pill {
  font-size: 10.5px; font-weight: 800; color: #B4652A;
  background: rgba(255, 150, 70, .12);
  padding: 3px 8px; border-radius: 8px;
}
.lg-chev { flex: none; display: grid; place-items: center; color: #c9b4bf; }

.lg-num {
  display: flex; align-items: baseline; gap: 2px;
  margin: 8px 0 8px;
  font-size: 27px; font-weight: 800; letter-spacing: -.02em;
  color: #C0561F;
  line-height: 1;
}
.lg-num i { font-style: normal; font-size: 14px; font-weight: 800; }

.lg-chips { display: flex; gap: 8px; }
.lg-chip {
  font-size: 11px; color: #9a7f88;
  background: #FFF4EC;
  border-radius: 9px; padding: 4px 9px;
}
.lg-chip b { color: #B4652A; font-weight: 800; }

.lg-last { display: block; margin-top: 9px; font-size: 11px; color: #a89fb0; }
.lg-last b { color: #8a6a72; font-weight: 800; }

/* ============================================================
   首页 hero · 还没填起始日的那一态
   目标：一眼看出「这里缺东西」，并且整张卡随手一点就能去补，
   不靠一个藏在角落的小链接。
   ============================================================ */

/* 天数换数字时轻轻一顶，填完起始日那一刻的数字有落点 */
.hero__num b {
  display: inline-block;
  animation: numIn .46s cubic-bezier(.22, 1, .36, 1) both;
}
@keyframes numIn {
  from { opacity: 0; transform: translateY(7px) scale(.94); }
  to { opacity: 1; transform: none; }
}

/* 待填小标：虚淡的珊瑚胶囊，和右侧大数字同位置，扫一眼就知道缺什么 */
.hero__todo {
  margin-left: auto; flex: none;
  display: inline-flex; align-items: center;
  height: calc(30px - 6px * var(--c));
  padding: 0 13px;
  border-radius: 999px;
  font-size: 11.5px; font-weight: 800; letter-spacing: .06em;
  color: #D9235A;
  background: rgba(255, 93, 143, .1);
  box-shadow: inset 0 0 0 1px rgba(255, 93, 143, .34);
  animation: todoBreath 2.8s ease-in-out infinite;
}
@keyframes todoBreath {
  0%, 100% { box-shadow: inset 0 0 0 1px rgba(255, 93, 143, .34), 0 0 0 0 rgba(255, 61, 116, 0); }
  50%      { box-shadow: inset 0 0 0 1px rgba(255, 93, 143, .5), 0 0 0 7px rgba(255, 61, 116, .08); }
}

/* 整卡可点：手指落下给一点回弹，否则点了没反应像坏掉 */
.hero--todo {
  cursor: pointer;
  transition: transform .2s cubic-bezier(.22, 1, .36, 1);
  -webkit-tap-highlight-color: transparent;
}
.hero--todo.hero--press { transform: scale(.9925); }
.hero--todo.hero--press .hero__cue { background: rgba(255, 214, 227, .96); }

/* 提示条：替代正常态的进度条 + 副标题，跟着 --c 一起收干净 */
.hero__cue {
  display: flex; align-items: center; gap: 10px;
  margin-top: calc(14px - 14px * var(--c));
  height: calc(54px - 54px * var(--c));
  padding: calc(10px - 7px * var(--c)) calc(11px - 6px * var(--c));
  border-radius: calc(15px - 7px * var(--c));
  background: rgba(255, 236, 242, .9);
  box-shadow: inset 0 0 0 1px rgba(255, 93, 143, .16);
  opacity: calc(1 - var(--c) * 2.4);
  overflow: hidden;
  transition: background .2s var(--ease);
}
.hero__cue-ic {
  flex: none; width: 30px; height: 30px;
  display: grid; place-items: center;
  border-radius: 10px;
  color: #E0407A;
  background: #fff;
  box-shadow: 0 6px 14px -10px rgba(224, 64, 122, .7), inset 0 0 0 1px rgba(255, 93, 143, .14);
}
.hero__cue-ic svg { width: 17px; height: 17px; }
.hero__cue-tx {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.hero__cue-tx b {
  font-size: 12.5px; font-weight: 800; letter-spacing: -.01em; color: #7C2144;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.hero__cue-tx span {
  font-size: 10.5px; line-height: 1.35; color: rgba(124, 33, 68, .62);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.hero__cue-go {
  flex: none;
  display: inline-flex; align-items: center; gap: 2px;
  height: 27px; padding: 0 9px 0 11px;
  border-radius: 999px;
  font-size: 11.5px; font-weight: 800; color: #fff;
  background: linear-gradient(180deg, #FF7DA4, #FF3D74);
  box-shadow: 0 10px 18px -12px rgba(255, 61, 116, .95);
}
.hero__cue-go svg { width: 12px; height: 12px; }

/* 减动效：只留静态终态，别把待填标钉在动画第一帧 */
@media (prefers-reduced-motion: reduce) {
  .hero__num b { animation-duration: .01s !important; }
  .hero__todo { animation: none; }
  .hero--todo { transition: none; }
}
</style>
