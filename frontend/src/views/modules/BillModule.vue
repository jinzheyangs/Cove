<template>
<div class="bl">
  <!-- ---------- 本月基金卡 ---------- -->
  <article
    class="bl-hero bl-in" :style="{ '--i': 0 }"
    role="button" tabindex="0"
    :aria-label="budget ? '改本月共同基金' : '设置本月共同基金'"
    @click="openBudget"
    @keydown.enter.prevent="openBudget"
  >
    <div class="bl-hero-top">
      <span class="bl-hero-label">本月共同基金</span>
      <span class="bl-hero-edit">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4l10-10-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/></svg>
        {{ budget ? '改' : '设置' }}
      </span>
    </div>

    <div class="bl-hero-num"><i>¥</i><b>{{ moneyShown }}</b></div>
    <div class="bl-hero-sub">{{ monthKeyLabel }} · 这个月一起花了 {{ monthCount }} 笔</div>

    <div v-if="budget" class="bl-hero-bar" :class="{ over: budgetOver }">
      <i :style="{ width: barPct + '%' }"></i>
    </div>

    <div class="bl-hero-leg">
      <span v-if="budget">基金 <b>{{ money(budget) }}</b></span>
      <span v-else class="bl-hero-hint">点一下，定个数</span>
      <span v-if="budget">{{ budgetOver ? '超出' : '还剩' }} <b>{{ money(Math.abs(budget - monthSpent)) }}</b></span>
    </div>
  </article>

  <!-- ---------- 分段 ---------- -->
  <div class="bl-seg bl-in" :style="{ '--i': 1, '--n': RANGES.length }" role="tablist">
    <span class="bl-seg-glider" :style="{ transform: `translateX(${segIdx * 100}%)` }" aria-hidden="true"></span>
    <button
      v-for="(r, i) in RANGES" :key="r.key" type="button" role="tab"
      class="bl-seg-btn" :class="{ on: range === r.key }"
      :aria-selected="range === r.key"
      @click="pickRange(r.key)"
    >{{ r.label }}</button>
  </div>

  <!-- ---------- 趋势 ---------- -->
  <article class="bl-card bl-chart bl-in" :style="{ '--i': 2 }">
    <header class="bl-card-head">
      <div>
        <div class="bl-head-t">
          <button
            v-if="zoom" type="button" class="bl-back"
            aria-label="返回上一级" @click.stop="goBack"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m14 6-6 6 6 6"/></svg>
          </button>
          <b>花费趋势</b>
        </div>
        <span>{{ viewSub }}</span>
      </div>
      <div class="bl-head-acts">
        <button
          type="button" class="bl-eye" :class="{ off: !showPeak }"
          :aria-label="showPeak ? '隐藏每日金额' : '显示每日金额'"
          :aria-pressed="showPeak"
          @click="showPeak = !showPeak"
        >
          <svg v-if="showPeak" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2.4 12S6 5.9 12 5.9 21.6 12 21.6 12 18 18.1 12 18.1 2.4 12 2.4 12Z"/>
            <circle cx="12" cy="12" r="2.8"/>
          </svg>
          <svg v-else width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3.2 11.6c1.6-2.2 4.6-5.4 8.8-5.4 1.2 0 2.3.3 3.3.7"/>
            <path d="M20.8 12.2c-1.6 2.2-4.6 5.2-8.8 5.2-1.1 0-2.2-.2-3.1-.6"/>
            <path d="M4 20 20 4"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- 这一段一笔都没有时，别留一张 156px 的空图：压成一行提示，页面往下就紧凑了 -->
    <div
      ref="plotEl" class="bl-plot-scroll" :class="{ 'is-empty': !rangeStat.count }"
      @scroll.passive="onPlotScroll"
    >
      <div class="bl-plot" :style="{ width: chartW + 'px' }">
        <svg :width="chartW" :height="CH" :viewBox="`0 0 ${chartW} ${CH}`" aria-hidden="true">
          <g class="bl-bars">
            <rect
              v-for="(p, i) in points" :key="'b' + i"
              :x="p.bx" :y="p.y" :width="barW" :height="CH - PAD_B - p.y"
              :class="{ peak: i === peakIdx }"
              :style="{ '--d': i * 26 + 'ms' }"
            />
          </g>
          <path class="bl-line s" :d="pathShared" pathLength="100" />
          <g class="bl-hits">
            <rect
              v-for="p in hitPoints" :key="'h' + p.i"
              :x="Math.max(0, Math.min(chartW - hitW, p.x - hitW / 2))"
              y="0" :width="hitW" :height="CH"
              @click="onBucketTap(p.b)"
            />
          </g>
        </svg>

        <div v-if="showPeak" class="bl-tips">
          <div
            v-for="b in bubbles" :key="b.idx"
            class="bl-tip"
            :style="{ left: b.x + 'px', top: b.y + 'px', '--lane': b.lane }"
          >¥{{ shortMoney(b.total) }}</div>
        </div>

        <div class="bl-xaxis" :style="{ width: chartW + 'px' }">
          <span v-for="(t, i) in xTicks" :key="i" :style="{ left: t.x + 'px' }">{{ t.label }}</span>
        </div>
      </div>
    </div>

    <!-- 空态不写字：「这段合计 ¥0.00 / 0 笔」已经说清楚了，
         再补一句就成了和下面「这里还没有账」重复 -->

    <div class="bl-sum">
      <span class="bl-sum-lb">这段合计</span>
      <b>¥{{ money(rangeStat.total) }}</b>
      <span class="bl-sum-sub">
        {{ rangeStat.count }} 笔<template v-if="rangeStat.max"> · 最多一笔 ¥{{ shortMoney(rangeStat.max) }}</template>
      </span>
    </div>
  </article>

  <!-- ---------- 记一笔 ---------- -->
  <button v-if="!form.open" type="button" class="bl-add bl-in" :style="{ '--i': 4 }" @click="openForm()">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
    记一笔
  </button>

  <!-- ---------- 表单 ---------- -->
  <form v-else class="bl-card bl-form" @submit.prevent="submit">
    <header class="bl-form-head">
      <b>{{ form.id ? '改这一笔' : '记一笔' }}</b>
      <button type="button" class="bl-x" @click="closeForm" aria-label="关闭">
        <svg width="13" height="13" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="m5 5 14 14M19 5 5 19"/></svg>
      </button>
    </header>

    <label class="bl-field">
      <span class="bl-lb">多少钱</span>
      <div class="bl-money">
        <i>¥</i>
        <input v-model="form.amount" type="number" min="0" step="0.01"
               inputmode="decimal" placeholder="0.00" />
      </div>
    </label>

    <div class="bl-field">
      <span class="bl-lb">算在哪一类</span>
      <div class="bl-catpicks">
        <button
          v-for="c in CATEGORIES" :key="c" type="button"
          class="bl-pick sm" :class="{ on: form.category === c }"
          @click="form.category = c, customCat = ''"
        >{{ c }}</button>
        <input class="bl-pick-input" v-model="customCat" maxlength="50"
               placeholder="或自己写" @input="form.category = customCat" />
      </div>
    </div>

    <label class="bl-field mt">
      <span class="bl-lb">备注（可以不写）</span>
      <textarea class="bl-area" v-model="form.remark" maxlength="500" placeholder="那天为什么想花这笔…"></textarea>
    </label>

    <div class="bl-form-btns">
      <button type="button" class="bl-btn ghost" @click="closeForm">取消</button>
      <button type="submit" class="bl-btn" :disabled="!canSubmit || saving">{{ saving ? '保存中…' : '记下' }}</button>
    </div>

    <template v-if="form.id">
      <button v-if="!delArm" type="button" class="bl-del" @click="delArm = true">删掉这一笔</button>
      <div v-else class="bl-del-confirm">
        <span>删掉这一笔？</span>
        <button type="button" @click="delArm = false">算了</button>
        <button type="button" class="danger" :disabled="deleting" @click="doDelete(form)">{{ deleting ? '删除中…' : '删掉' }}</button>
      </div>
    </template>

    <p v-if="formError" class="bl-warn">{{ formError }}</p>
  </form>

  <p v-if="error" class="bl-warn box">{{ error }}</p>

  <!-- ---------- 明细 ---------- -->
  <div class="bl-sec">
    <b>账目明细</b>
    <span v-if="filtered.length">{{ filtered.length }} 笔</span>
  </div>

  <div v-if="loading" class="bl-card bl-loading"><i></i><i></i><i></i></div>

  <div v-else-if="!filtered.length" class="bl-card bl-empty">
    <b>这里还没有账</b>
    <span>记下第一笔，日子就有了刻度</span>
  </div>

  <template v-else>
    <section v-for="(g, gi) in dayGroups" :key="g.key" class="bl-daygrp">
      <div class="bl-dayhead">
        <span>{{ g.label }}</span>
        <em v-if="g.total">{{ money(g.total) }}</em>
      </div>
      <article class="bl-rows">
        <button
          v-for="(b, i) in g.items" :key="b.id"
          type="button"
          class="bl-row bl-in"
          :style="{ '--i': gi + i + 7 }"
          @click="openForm(b)"
        >
          <span class="bl-row-ic" :style="{ background: catColor(b.category) }">{{ ch(b.category) }}</span>
          <div class="bl-row-body">
            <div class="bl-row-top">
              <b>{{ b.category }}</b>
            </div>
            <p v-if="b.remark" class="bl-remark">{{ b.remark }}</p>
            <div class="bl-row-meta">
              <span>{{ timeOf(b.created_at) }}</span>
            </div>
          </div>
          <div class="bl-row-amt">
            <b><i>¥</i>{{ money(b.amount) }}</b>
          </div>
        </button>
      </article>
    </section>
  </template>

  <!-- 本月基金 -->
  <Teleport v-if="hostEl" :to="hostEl">
    <div v-if="budgetOpen" class="bl-mask" @click.self="closeBudget">
      <div class="bl-sheet" role="dialog" aria-modal="true" aria-label="本月共同基金">
        <span class="bl-grip" aria-hidden="true"></span>
        <h4>本月共同基金</h4>
        <p>填个数，进度条就按这个数来比。</p>

        <div class="bl-binput">
          <i>¥</i>
          <input
            ref="budgetInput"
            v-model="budgetDraft"
            type="number" min="0" step="1" inputmode="decimal"
            placeholder="输入金额"
            @keydown.enter.prevent="saveBudget"
            @focus="$event.target.select()"
          />
        </div>

        <div v-if="quickPicks.length" class="bl-quick">
          <button v-for="q in quickPicks" :key="q" type="button" @click="budgetDraft = String(q)">{{ q }}</button>
        </div>

        <div class="bl-form-btns">
          <button type="button" class="bl-btn ghost" @click="closeBudget">取消</button>
          <button type="button" class="bl-btn" @click="saveBudget">存下</button>
        </div>
        <button v-if="budget" type="button" class="bl-del" @click="clearBudget">这个月不设了</button>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, onActivated, nextTick, watch } from 'vue';
import { listBills, createBill, updateBill, deleteBill } from '../../api/bills.js';
import { tap } from '../../native.js';

const QS = new URLSearchParams(location.search);
const DEMO = QS.has('demo');

const bills = ref([]);
const loading = ref(!DEMO);
const error = ref('');
const deleting = ref(false);
const delArm = ref(false);

/* ---------- 本月基金 ---------- */
const nowDate = new Date();
const MONTH_KEY = `${nowDate.getFullYear()}-${String(nowDate.getMonth() + 1).padStart(2, '0')}`;
const BUDGET_KEY = `cove.bill.budget.${MONTH_KEY}`;
const HISTORY_KEY = 'cove.bill.budget.history';
function readHistory(){
  try {
    const v = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(v) ? v.filter(n => Number(n) > 0).slice(0, 3) : [];
  } catch { return []; }
}
const history = ref(readHistory());
const quickPicks = computed(() => (history.value.length ? history.value : [1000, 2000, 3000]));
const qBudget = Number(QS.get('budget') || 0);
const budget = ref(qBudget > 0 ? qBudget : (Number(localStorage.getItem(BUDGET_KEY)) || 0));
const budgetOpen = ref(false);
const budgetDraft = ref('');
const budgetInput = ref(null);
const hostEl = ref(null);

const monthKeyLabel = `${nowDate.getMonth() + 1} 月`;
const monthBills = computed(() => bills.value.filter((b) => {
  if (b.type !== 'money') return false;
  const d = new Date(b.created_at);
  return d.getFullYear() === nowDate.getFullYear() && d.getMonth() === nowDate.getMonth();
}));
const monthSpent = computed(() => monthBills.value.reduce((s, b) => s + Number(b.amount || 0), 0));
const monthCount = computed(() => monthBills.value.length);
const budgetOver = computed(() => !!budget.value && monthSpent.value > budget.value);
const barPct = computed(() => {
  if (!budget.value) return 0;
  return Math.min(100, Math.round((monthSpent.value / budget.value) * 100));
});

function openBudget(){
  tap();
  budgetDraft.value = budget.value ? String(budget.value) : '';
  budgetOpen.value = true;
  requestAnimationFrame(() => budgetInput.value?.focus());
}
function closeBudget(){
  budgetOpen.value = false;
}
function saveBudget(){
  const v = Math.max(0, Number(budgetDraft.value) || 0);
  budget.value = v;
  try {
    if (v) {
      localStorage.setItem(BUDGET_KEY, String(v));
      const h = [v, ...history.value.filter(x => Number(x) !== v)].slice(0, 3);
      history.value = h;
      localStorage.setItem(HISTORY_KEY, JSON.stringify(h));
    } else {
      localStorage.removeItem(BUDGET_KEY);
    }
  } catch { /* 存不上也不影响这一屏 */ }
  budgetOpen.value = false;
}
function clearBudget(){
  budget.value = 0;
  try { localStorage.removeItem(BUDGET_KEY); } catch { /* ignore */ }
  budgetOpen.value = false;
}

const CATEGORIES = ['餐饮', '礼物', '出行', '居家', '旅行', '纪念'];

/* 三段都是「汇总」口径：本周按天、本月按天、今年按月 */
const RANGES = [
  { key: 'week', label: '本周' },
  { key: 'month', label: '本月' },
  { key: 'year', label: '今年' },
];
const qRange = QS.get('range');
const range = ref(RANGES.some(r => r.key === qRange) ? qRange : 'week');
const segIdx = computed(() => Math.max(0, RANGES.findIndex(r => r.key === range.value)));
/* 点图往下钻：{ unit:'year', y } 或 { unit:'month', y, m } */
const zoom = ref(null);

function pickRange(key){
  tap();
  range.value = key;
  zoom.value = null;
}
function goBack(){
  tap();
  if (!zoom.value) return;
  if (zoom.value.unit === 'month') zoom.value = { unit: 'year', y: zoom.value.y };
  else zoom.value = null;
}
const rangeLabel = computed(() => {
  const now = new Date();
  if (range.value === 'week') return '本周 · 周一到周日 7 天';
  const d = now.getDate();
  if (range.value === 'month') return `${now.getMonth() + 1} 月 · ${d === 1 ? '1 日' : `1 – ${d} 日`}`;
  if (range.value === 'year') return `${now.getFullYear()} 年 · ${now.getMonth() === 0 ? '1 月' : `1 – ${now.getMonth() + 1} 月`}`;
  return '本周 · 周一到周日 7 天';
});
/* 头部标题：下钻后换成钻到的那一层 */
const viewTitle = computed(() => {
  const z = zoom.value;
  if (z?.unit === 'year') return `${z.y} 年 · 12 个月按月汇总`;
  if (z?.unit === 'month') return `${z.y} 年 ${z.m + 1} 月 · 按天汇总`;
  return rangeLabel.value;
});

/* ---------- 金额 ---------- */
function money(v){
  const n = Number(v ?? 0);
  if (!Number.isFinite(n)) return '0.00';
  const [i, d] = n.toFixed(2).split('.');
  return `${i.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${d}`;
}
/* 图上标注用：整数，省地方 */
function shortMoney(v){
  const n = Math.round(Number(v ?? 0));
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/* ---------- 数字滚动 ---------- */
const moneyShown = ref('0.00');
let raf = 0;
function rollMoney(to){
  const target = Number(to || 0);
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    moneyShown.value = money(target);
    return;
  }
  cancelAnimationFrame(raf);
  const t0 = performance.now();
  const DUR = 1200;
  const step = (t) => {
    const p = Math.min(1, (t - t0) / DUR);
    const e = 1 - Math.pow(1 - p, 4);
    moneyShown.value = money(target * e);
    if (p < 1) raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
}

/* ---------- 趋势分桶：一律按自然周期 ---------- */
const moneyBills = computed(() => bills.value.filter(b => b.type === 'money'));

const buckets = computed(() => {
  const now = new Date();
  const y0 = now.getFullYear();
  const dayMs = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1).getTime();

  /* 某月按天；当月只到今天，别把还没到的日子画出来 */
  const dayBuckets = (yy, mm) => {
    const full = new Date(yy, mm + 1, 0).getDate();
    const isThisMonth = yy === now.getFullYear() && mm === now.getMonth();
    const days = isThisMonth ? now.getDate() : full;
    const out = [];
    for (let i = 1; i <= days; i += 1) {
      const d = new Date(yy, mm, i);
      out.push({
        unit: 'day', y: yy, m: mm, d: i, label: `${i}`,
        from: d.getTime(), to: dayMs(d), total: 0,
      });
    }
    return out;
  };
  /* 某年按月；今年只到当月 */
  const monthBuckets = (yy) => {
    const upto = yy === now.getFullYear() ? now.getMonth() : 11;
    const out = [];
    for (let m = 0; m <= upto; m += 1) {
      out.push({
        unit: 'month', y: yy, m, label: `${m + 1} 月`,
        from: new Date(yy, m, 1).getTime(), to: new Date(yy, m + 1, 1).getTime(), total: 0,
      });
    }
    return out;
  };

  let out;
  if (zoom.value?.unit === 'year') {
    out = monthBuckets(zoom.value.y);
  } else if (zoom.value?.unit === 'month') {
    out = dayBuckets(zoom.value.y, zoom.value.m);
  } else if (range.value === 'week') {
    /* 本周：周一 → 今天。还没到的日子不画（否则图上会出现一笔没发生过的未来） */
    out = [];
    const wd = (new Date(y0, now.getMonth(), now.getDate()).getDay() + 6) % 7;  // 周一 = 0
    const monday = new Date(y0, now.getMonth(), now.getDate() - wd);
    for (let i = 0; i <= wd; i += 1) {
      const d = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i);
      out.push({
        unit: 'day', y: d.getFullYear(), m: d.getMonth(), d: d.getDate(),
        label: '一二三四五六日'[i], from: d.getTime(), to: dayMs(d), total: 0,
      });
    }
  } else if (range.value === 'month') {
    out = dayBuckets(y0, now.getMonth());
  } else {
    out = monthBuckets(y0);
  }

  for (const b of moneyBills.value) {
    const t = new Date(b.created_at).getTime();
    for (const k of out) {
      if (t >= k.from && t < k.to) k.total += Number(b.amount || 0);
    }
  }
  return out;
});

/* 这一段汇总：合计 / 笔数 / 最多一笔 */
const rangeStat = computed(() => {
  const bs = buckets.value;
  if (!bs.length) return { total: 0, count: 0, max: 0 };
  const from = bs[0].from;
  const to = bs[bs.length - 1].to;
  const list = moneyBills.value.filter((b) => {
    const t = new Date(b.created_at).getTime();
    return t >= from && t < to;
  });
  return {
    total: list.reduce((s, b) => s + Number(b.amount || 0), 0),
    count: list.length,
    max: list.reduce((m, b) => Math.max(m, Number(b.amount || 0)), 0),
  };
});

/* ---------- 图表几何 ---------- */
const BASE_W = 326;
const CH = 156;
const PAD_T = 42;
const PAD_B = 16;
const INSET = 11;

/* 每个桶至少留这么宽：横轴标签写得全，金额气泡也不会和隔壁叠在一起 */
const PER_MIN = computed(() => 44);
const chartW = computed(() => {
  const n = buckets.value.length;
  const body = Math.max(0, n - 1) * PER_MIN.value + INSET * 2;
  return Math.max(BASE_W, body);
});
const showPeak = ref(!QS.has('nopeak'));

const barW = computed(() => Math.min(9, Math.max(3, (chartW.value - INSET * 2) / Math.max(buckets.value.length, 1) * 0.5)));
/* 每桶一整个可点的竖条，柱太细也点得中 */
const hitW = computed(() => chartW.value / Math.max(buckets.value.length, 1));

/* 横滑状态：滑到哪儿，头部副标题就写那一段 */
const plotEl = ref(null);
const plotLeft = ref(0);
const plotW = ref(BASE_W);
const needScroll = computed(() => chartW.value > BASE_W + 1);
const stepPx = computed(() => {
  const n = buckets.value.length;
  return n > 1 ? (chartW.value - INSET * 2) / (n - 1) : 0;
});
const viewIdx = computed(() => {
  const n = buckets.value.length;
  if (!n) return [0, 0];
  if (!needScroll.value) return [0, n - 1];
  const sp = stepPx.value || 1;
  const vw = plotW.value || BASE_W;
  const i0 = Math.round(plotLeft.value / sp);
  const i1 = Math.round((plotLeft.value + vw - INSET * 2) / sp);
  return [Math.max(0, Math.min(n - 1, i0)), Math.max(0, Math.min(n - 1, i1))];
});
function syncPlot(){
  const el = plotEl.value;
  if (!el) return;
  plotLeft.value = el.scrollLeft;
  plotW.value = el.clientWidth - 32;   /* 去掉左右各 16 的留白 */
}
let snapT = 0;
function onPlotScroll(e){
  plotLeft.value = e.target.scrollLeft;
  /* 松手后吸附到最近的刻度，别把某个数字裁一半停在边里 */
  clearTimeout(snapT);
  snapT = setTimeout(() => {
    const el = plotEl.value;
    if (!el || !needScroll.value) return;
    const sp = stepPx.value || 1;
    const max = el.scrollWidth - el.clientWidth;
    let target = Math.round(el.scrollLeft / sp) * sp;
    if (max - target < sp) target = max;   /* 快到尽头就贴到头，末桶别被裁一半 */
    target = Math.min(max, Math.max(0, target));
    if (Math.abs(target - el.scrollLeft) > 1) el.scrollTo({ left: target, behavior: 'smooth' });
  }, 220);
}
function frameText(a, b){
  if (!a || !b) return '';
  const nowY = new Date().getFullYear();
  if (a.unit === 'month') {
    if (a.y === b.y) return `${a.y} 年 ${a.m + 1} – ${b.m + 1} 月`;
    return `${a.y} 年 ${a.m + 1} 月 – ${b.y} 年 ${b.m + 1} 月`;
  }
  const yp = a.y === nowY && b.y === nowY ? '' : `${a.y} 年 `;
  if (a.y === b.y && a.m === b.m) return `${yp}${a.m + 1} 月 ${a.d} – ${b.d} 日`;
  return `${a.m + 1} 月 ${a.d} 日 – ${b.m + 1} 月 ${b.d} 日`;
}
/* 副标题：不用滑时是口径，要滑时是当前这一屏的起止 */
const viewSub = computed(() => {
  const bs = buckets.value;
  if (!needScroll.value) {
    if (range.value === 'week' && !zoom.value) return `本周 · ${frameText(bs[0], bs[bs.length - 1])}`;
    return viewTitle.value;
  }
  const [i0, i1] = viewIdx.value;
  return frameText(bs[i0], bs[i1]);
});

/* 进这一段时先看「今天」：把它摆到可视窗口中间，而不是永远从第一天开始 */
const todayIdx = computed(() => {
  const d = new Date();
  return buckets.value.findIndex((k) => {
    if (k.unit === 'month') return k.y === d.getFullYear() && k.m === d.getMonth();
    if (k.unit === 'day') return k.y === d.getFullYear() && k.m === d.getMonth() && k.d === d.getDate();
    return false;
  });
});
function scrollToFocus(){
  const el = plotEl.value;
  if (!el) return;
  const i = todayIdx.value;
  if (!needScroll.value || i < 0) {
    el.scrollLeft = 0;
    syncPlot();
    return;
  }
  const sp = stepPx.value || 1;
  const vw = el.clientWidth - 32;
  const center = INSET + i * sp;
  const max = el.scrollWidth - el.clientWidth;
  el.scrollLeft = Math.min(max, Math.max(0, center - vw / 2));
  syncPlot();
}

/* 切段 / 下钻后回到最左，别停在上次的位置 */
watch([range, zoom, () => buckets.value.length], () => {
  plotLeft.value = 0;
  nextTick(scrollToFocus);
});

const points = computed(() => {
  const bs = buckets.value;
  if (!bs.length) return [];
  const W = chartW.value;
  const max = Math.max(1, ...bs.map(k => k.total));
  const span = W - INSET * 2;
  const step = bs.length > 1 ? span / (bs.length - 1) : 0;
  return bs.map((k, i) => {
    const x = bs.length > 1 ? INSET + i * step : W / 2;
    const y = CH - PAD_B - (k.total / max) * (CH - PAD_T - PAD_B);
    return { x, bx: x - barW.value / 2, y, total: k.total };
  });
});

function smooth(pts, key){
  if (!pts.length) return '';
  if (pts.length === 1) return `M${pts[0].x},${pts[0][key]}`;
  let d = `M${pts[0].x},${pts[0][key]}`;
  for (let i = 0; i < pts.length - 1; i += 1) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1[key] + (p2[key] - p0[key]) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2[key] - (p3[key] - p1[key]) / 6;
    d += ` C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2.x.toFixed(1)},${p2[key].toFixed(1)}`;
  }
  return d;
}
const pathShared = computed(() => smooth(points.value, 'y'));

const peakIdx = computed(() => {
  let idx = 0;
  let max = -1;
  points.value.forEach((p, i) => { if (p.total > max) { max = p.total; idx = i; } });
  return max > 0 ? idx : -1;
});
/* 每一笔有花费的桶都标金额；挤在一起时相邻两天上下错行 */
const bubbles = computed(() => {
  const W = chartW.value;
  const n = points.value.length;
  const stepX = n > 1 ? (W - INSET * 2) / (n - 1) : W;
  const stagger = stepX < 88;
  /* 横滑时：只标这一屏里的桶，贴边的气泡往里挪，别让容器切掉半个 */
  const lo = plotLeft.value;
  const hi = lo + (plotW.value || BASE_W);
  const pad = 38;
  const out = [];
  points.value.forEach((p, i) => {
    if (p.total <= 0) return;
    if (p.x < lo || p.x > hi) return;
    out.push({
      idx: i,
      total: p.total,
      x: Math.min(hi - pad, Math.max(lo + pad, p.x)),
      y: p.y,
      lane: stagger ? i % 2 : 0,
    });
  });
  return out;
});
const WEEK_CN = ['日', '一', '二', '三', '四', '五', '六'];
const xTicks = computed(() => {
  const bs = buckets.value;
  if (!bs.length) return [];
  /* 每个桶都标出来：一周写周几，按天写日号，按月写月份。
     周视图只画到今天，桶数不再是 7，所以按「当前是哪一段」判断，不数个数 */
  const weekly = bs[0].unit === 'day' && range.value === 'week' && !zoom.value;
  return bs.map((k, i) => {
    let label;
    if (k.unit === 'month') label = `${k.m + 1}月`;
    else if (weekly) label = WEEK_CN[new Date(k.y, k.m, k.d).getDay()];
    else label = `${k.d}`;
    return { label, x: points.value[i]?.x ?? 0 };
  });
});

/* ---------- 分类 ---------- */
const CAT_COLOR = {
  餐饮: '#FF8A3D', 礼物: '#FF5C8A', 出行: '#4C7DF0', 居家: '#8B7BF0',
  旅行: '#12B3A8', 纪念: '#F5B93D', 房租: '#6A5AE0', 娱乐: '#22C55E',
};
const FALLBACK = ['#FF8A3D', '#4C7DF0', '#12B3A8', '#8B7BF0', '#FF5C8A', '#F5B93D'];
function catColor(name){
  if (CAT_COLOR[name]) return CAT_COLOR[name];
  let h = 0;
  for (let i = 0; i < String(name).length; i += 1) h = (h * 31 + name.charCodeAt(i)) % 997;
  return FALLBACK[h % FALLBACK.length];
}
function ch(name){ return String(name || '·').slice(0, 1); }

/* ---------- 列表 ---------- */
/* 明细跟着当前区间走：切段、下钻，底下的账目也跟着变 */
/* 账本只记钱 */
const filtered = computed(() => {
  const bs = buckets.value;
  if (!bs.length) return [];
  const from = bs[0].from;
  const to = bs[bs.length - 1].to;
  return bills.value.filter((b) => {
    if (b.type !== 'money') return false;
    const t = new Date(b.created_at).getTime();
    return t >= from && t < to;
  });
});

function dayKey(s){
  const d = new Date(s);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}
function dayLabel(s){
  const d = new Date(s);
  const now = new Date();
  const one = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const that = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diff = Math.round((one - that) / 86400000);
  if (diff === 0) return '今天';
  if (diff === 1) return '昨天';
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日`;
}
function groupByDay(list){
  const sorted = [...list].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  const map = new Map();
  for (const b of sorted) {
    const k = dayKey(b.created_at);
    if (!map.has(k)) map.set(k, { key: k, label: dayLabel(b.created_at), items: [], total: 0 });
    const g = map.get(k);
    g.items.push(b);
    if (b.type === 'money') g.total += Number(b.amount || 0);
  }
  return [...map.values()];
}
const dayGroups = computed(() => groupByDay(filtered.value));

/* 点月 / 年那根柱往下钻一层；日这一层不再单独开页面 */
const hitPoints = computed(() => points.value
  .map((p, i) => ({ ...p, i, b: buckets.value[i] }))
  .filter(x => x.b && x.b.unit !== 'day'));

/** 点柱：年 → 该年月视图，月 → 该月日视图 */
function onBucketTap(b){
  if (!b || b.unit === 'day') return;
  tap();
  zoom.value = b.unit === 'year'
    ? { unit: 'year', y: b.y }
    : { unit: 'month', y: b.y, m: b.m };
}

function timeOf(s){
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return '';
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/* ---------- 表单 ---------- */
const form = ref({ open: false, id: null, amount: '', category: '餐饮', remark: '' });
/* 自定义类别：只有不在预置里才写进这个输入框，避免和选中的 chip 重复显示 */
const customCat = ref('');
const formError = ref('');
const saving = ref(false);
const canSubmit = computed(() => {
  if (!form.value.category.trim()) return false;
  const n = Number(form.value.amount);
  return Number.isFinite(n) && n > 0 && form.value.amount !== '';
});

function openForm(b){
  tap();
  formError.value = '';
  delArm.value = false;
  form.value = b
    ? {
      open: true, id: b.id,
      amount: b.amount == null ? '' : String(b.amount),
      category: b.category, remark: b.remark || '',
    }
    : { open: true, id: null, amount: '', category: '餐饮', remark: '' };
  customCat.value = CATEGORIES.includes(form.value.category) ? '' : form.value.category;
}
function closeForm(){
  form.value = { ...form.value, open: false };
  delArm.value = false;
}

/* 数据变了：通知「我」页那几张卡重拉 */
function notifyData(){
  window.dispatchEvent(new Event('cove:data'));
}

async function submit(){
  if (!canSubmit.value || saving.value) return;
  saving.value = true; formError.value = '';
  const body = {
    type: 'money',
    category: form.value.category.trim(),
    scope: 'shared',
    is_private: false,
    remark: form.value.remark.trim() || null,
    amount: Number(form.value.amount),
  };
  try {
    if (form.value.id) await updateBill(form.value.id, body);
    else await createBill(body);
    closeForm();
    await load();
    notifyData();
  } catch (e) {
    formError.value = e.message || '保存失败';
  } finally {
    saving.value = false;
  }
}

async function doDelete(b){
  deleting.value = true;
  try {
    await deleteBill(b.id);
    bills.value = bills.value.filter(x => x.id !== b.id);
    delArm.value = false;
    if (form.value.id === b.id) closeForm();
    notifyData();
  } catch (e) {
    error.value = e.message || '删除失败';
  } finally {
    deleting.value = false;
  }
}

/* ---------- 取数 ---------- */
function seedDemo(){
  bills.value = [
    { id: 31, payer_id: 1, amount: 128.00, category: '餐饮', type: 'money', scope: 'shared', is_private: false, remark: '一起吃了顿火锅，辣锅归我', created_at: '2026-11-09T12:40:00' },
    { id: 32, payer_id: 1, amount: 36.50, category: '餐饮', type: 'money', scope: 'shared', is_private: false, remark: null, created_at: '2026-11-09T09:10:00' },
    { id: 33, payer_id: 2, amount: 260.00, category: '礼物', type: 'money', scope: 'shared', is_private: false, remark: '她一直想要的那盏灯', created_at: '2026-11-08T20:15:00' },
    { id: 34, payer_id: 1, amount: 420.00, category: '房租', type: 'money', scope: 'shared', is_private: false, remark: null, created_at: '2026-11-07T10:00:00' },
    { id: 35, payer_id: 2, amount: 198.00, category: '旅行', type: 'money', scope: 'shared', is_private: false, remark: '订了海边的房间，等周末', created_at: '2026-11-06T22:30:00' },
    { id: 36, payer_id: 1, amount: 64.00, category: '出行', type: 'money', scope: 'shared', is_private: false, remark: '打车去看展', created_at: '2026-11-05T15:20:00' },
    { id: 37, payer_id: 2, amount: 128.00, category: '居家', type: 'money', scope: 'shared', is_private: false, remark: '买菜炖了个汤，喝了一下午', created_at: '2026-11-04T18:00:00' },
    { id: 38, payer_id: 1, amount: 45.00, category: '餐饮', type: 'money', scope: 'shared', is_private: false, remark: null, created_at: '2026-11-03T23:00:00' },
  ];
  loading.value = false;
  rollMoney(monthSpent.value);
}

async function load(){
  if (DEMO) { seedDemo(); return; }
  loading.value = true; error.value = '';
  try {
    bills.value = await listBills();
    rollMoney(monthSpent.value);
  } catch (e) {
    error.value = e.message || '加载失败';
    bills.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await nextTick();
  hostEl.value = document.querySelector('.ds-card') || null;
  syncPlot();
  load();
  if (QS.has('openBudget')) openBudget();
});

/* 退出时数字滚动可能还在跑：卸载就把帧掐掉，别留着每帧改状态 */
onBeforeUnmount(() => {
  cancelAnimationFrame(raf);
  clearTimeout(snapT);
});

/* 页面被 KeepAlive 缓存下来以后再进来，DOM 是旧的：重新拉一次账，
   不然看到的是上次打开时的数字。首次 activated 跟着 onMounted 一起来，跳过以免重复请求 */
let activatedOnce = false;
onActivated(() => {
  if (!activatedOnce) { activatedOnce = true; return; }
  cancelAnimationFrame(raf);
  syncPlot();
  load();
});
</script>

<style scoped>
.bl{
  --bl-ink:#242438;
  --bl-ink2:#6E6E86;
  --bl-ink3:#9A9AB0;
  --bl-line:#EDEDF7;
  --bl-violet:#6A5AE0;
  --bl-violet2:#8B7BF0;
  --bl-orange:#FF8A3D;
  --bl-out:cubic-bezier(.16,1,.3,1);
  --bl-spring:cubic-bezier(.34,1.45,.64,1);
  --bl-shadow:0 18px 34px -20px rgba(64,54,150,.38), 0 3px 9px -6px rgba(64,54,150,.16);

  display:block;
  padding:2px 0 10px;
  color:var(--bl-ink);
  letter-spacing:-.006em;
  -webkit-font-smoothing:antialiased;
}

/* 弹层 Teleport 到 .ds-card，不在 .bl 子树里，token 需在弹层根上重新声明 */
.bl-mask{
  --bl-ink:#242438;
  --bl-ink2:#6E6E86;
  --bl-ink3:#9A9AB0;
  --bl-line:#EDEDF7;
  --bl-violet:#6A5AE0;
  --bl-violet2:#8B7BF0;
  --bl-orange:#FF8A3D;
  --bl-out:cubic-bezier(.16,1,.3,1);
  --bl-spring:cubic-bezier(.34,1.45,.64,1);
  color:var(--bl-ink);
  letter-spacing:-.006em;
  -webkit-font-smoothing:antialiased;
}

/* ---------- 卡片基元 ---------- */
.bl-card{
  position:relative;
  border-radius:22px;
  background:#fff;
  box-shadow:var(--bl-shadow), inset 0 0 0 1px rgba(255,255,255,.9);
  overflow:hidden;
}
.bl-card-head{
  display:flex; align-items:flex-start; justify-content:space-between; gap:10px;
  padding:16px 18px 12px;
}
.bl-card-head > div:first-child{ flex:1; min-width:0; }
.bl-card-head b{ display:block; font-size:13.5px; font-weight:750; letter-spacing:-.01em; }
.bl-card-head span{ display:block; margin-top:3px; font-size:10px; color:var(--bl-ink3); }

/* ---------- 本月基金卡 ---------- */
.bl-hero{
  position:relative;
  border-radius:24px;
  padding:18px 20px 17px;
  color:#fff;
  background:
    linear-gradient(158deg, rgba(255,255,255,.16) 0%, rgba(255,255,255,.05) 34%, rgba(255,255,255,0) 56%),
    linear-gradient(135deg, #8373FA 0%, #6A5AE0 46%, #5145CB 100%);
  box-shadow:0 26px 46px -26px rgba(86,70,224,.72), 0 4px 12px -8px rgba(86,70,224,.42), inset 0 1px 0 rgba(255,255,255,.24);
  overflow:hidden;
  cursor:pointer;
  transition:transform .24s var(--bl-spring), box-shadow .24s var(--bl-out);
}
.bl-hero:active{ transform:scale(.985); box-shadow:0 18px 34px -22px rgba(86,70,224,.7); }
.bl-hero:focus-visible{ outline:2px solid rgba(255,255,255,.6); outline-offset:2px; }
.bl-hero-top{ display:flex; align-items:center; justify-content:space-between; }
.bl-hero-label{
  font-size:10px; font-weight:750; letter-spacing:.16em; text-transform:uppercase;
  color:rgba(255,255,255,.78);
}
.bl-hero-edit{
  display:flex; align-items:center; gap:4px;
  font-size:9.5px; font-weight:700; padding:4px 9px; border-radius:99px;
  color:#fff; background:rgba(255,255,255,.2);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.26);
}
.bl-hero-num{ display:flex; align-items:baseline; gap:4px; margin:12px 0 0; }
.bl-hero-num i{ font-style:normal; font-size:16px; font-weight:600; color:rgba(255,255,255,.82); }
.bl-hero-num b{
  font-size:40px; font-weight:800; line-height:1; letter-spacing:-.045em;
  color:#fff; font-variant-numeric:tabular-nums;
  text-shadow:0 6px 18px rgba(40,26,120,.24);
}
.bl-hero-sub{
  margin-top:6px; font-size:9.5px; color:rgba(255,255,255,.66);
  font-variant-numeric:tabular-nums;
}
.bl-hero-bar{
  margin-top:14px; height:6px; border-radius:99px;
  background:rgba(255,255,255,.15);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);
  overflow:hidden;
}
.bl-hero-bar i{
  display:block; height:100%; border-radius:99px;
  background:linear-gradient(90deg, #FFFFFF, #F0ECFF);
  box-shadow:0 0 10px rgba(255,255,255,.55);
  transition:width 1.2s var(--bl-out);
}
.bl-hero-bar.over i{ background:linear-gradient(90deg, #FFC978, #FF8A3D); }
.bl-hero-leg{
  display:flex; align-items:center; justify-content:space-between;
  margin-top:9px;
}
.bl-hero-leg span{ display:flex; align-items:center; gap:4px; font-size:10px; color:rgba(255,255,255,.78); }
.bl-hero-leg b{ color:#fff; font-weight:700; font-variant-numeric:tabular-nums; }
.bl-hero-hint{ color:rgba(255,255,255,.58) !important; }

/* ---------- 分段 ---------- */
.bl-seg{
  position:relative;
  display:grid; grid-template-columns:repeat(var(--n, 3), minmax(0, 1fr));
  margin:14px 0 0; padding:4px;
  border-radius:16px; background:#fff;
  box-shadow:var(--bl-shadow), inset 0 0 0 1px rgba(255,255,255,.9);
  overflow-x:auto; overflow-y:hidden;
  scrollbar-width:none;
  -webkit-overflow-scrolling:touch;
}
.bl-seg::-webkit-scrollbar{ display:none; }
.bl-seg-glider{
  position:absolute; top:4px; left:4px; bottom:4px;
  width:calc((100% - 8px) / var(--n, 3));
  border-radius:12px;
  background:linear-gradient(135deg, #7C6CF2, #6A5AE0);
  box-shadow:0 8px 18px -12px rgba(96,74,224,.9);
  transition:transform .38s var(--bl-out);
}
.bl-seg-btn{
  position:relative; z-index:1; height:34px; min-width:74px;
  font-family:inherit; font-size:12px; font-weight:600;
  color:var(--bl-ink2); background:none; cursor:pointer;
  transition:color .24s ease;
}
.bl-seg-btn.on{ color:#fff; font-weight:700; }

/* 这一段的小结：合计 / 笔数 / 最多一笔 */
.bl-sum{
  display:flex; align-items:baseline; gap:7px; flex-wrap:wrap;
  width:100%; padding:6px 18px 16px;
  text-align:left;
  border-top:1px solid rgba(96,74,224,.1);
}
.bl-sum-lb{ font-size:10px; color:var(--bl-ink3); }
.bl-sum b{
  font-size:15px; font-weight:800; color:var(--bl-ink);
  font-variant-numeric:tabular-nums; letter-spacing:-.02em;
}
.bl-sum-sub{ margin-left:auto; font-size:10px; color:var(--bl-ink3); }

/* ---------- 趋势 ---------- */
.bl-chart{ margin-top:12px; }
.bl-head-hint{ font-style:normal; }
.bl-eye{
  flex:0 0 auto; display:flex; align-items:center; justify-content:center;
  width:32px; height:32px; margin:-7px -7px 0 0; padding:0;
  border:none; background:transparent; cursor:pointer;
  color:var(--bl-violet2);
  transition:color .22s, opacity .22s, transform .22s var(--bl-spring);
}
.bl-eye:active{ transform:scale(.86); }
.bl-eye.off{ color:#A9A5C2; opacity:.7; }

/* 头部：返回 / 详情 */
.bl-head-t{ display:flex; align-items:center; gap:6px; }
.bl-head-t b{ display:block; font-size:13.5px; font-weight:750; letter-spacing:-.01em; }
.bl-back{
  display:flex; align-items:center; justify-content:center;
  width:20px; height:20px; margin-left:-6px; padding:0;
  border:none; border-radius:8px; background:rgba(108,92,231,.1);
  color:var(--bl-violet2); cursor:pointer;
  transition:transform .2s var(--bl-spring), background .2s;
}
.bl-back:active{ transform:scale(.88); background:rgba(108,92,231,.18); }
.bl-head-acts{ display:flex; align-items:center; gap:4px; flex:0 0 auto; }

/* 每桶一个隐形点击条 */
.bl-hits rect{ fill:transparent; cursor:pointer; }

.bl-plot-scroll{
  overflow-x:auto; overflow-y:hidden;
  margin:-10px -16px 0; padding:10px 16px 0;
  scrollbar-width:none;
  -webkit-overflow-scrolling:touch;
  overscroll-behavior-x:contain;
}
.bl-plot-scroll::-webkit-scrollbar{ display:none; height:0; }
/* 这一段 0 笔：整块图收起来（合计那行会顶上来说明 0 笔） */
.bl-plot-scroll.is-empty{
  height:0; padding-top:0;
  margin:0 -16px;
  overflow:hidden;
}
.bl-plot{ position:relative; }
.bl-plot svg{ display:block; overflow:visible; }
.bl-bars rect{
  fill:#F1EFFE; rx:3;
  transform-box:fill-box; transform-origin:50% 100%;
  animation:blGrow .7s var(--bl-out) both;
  animation-delay:var(--d);
}
.bl-bars rect.peak{ fill:#DCD5FF; }
@keyframes blGrow{ from{ transform:scaleY(0); } to{ transform:scaleY(1); } }

.bl-line{ fill:none; stroke-width:2; stroke-linecap:round; }
.bl-line.s{
  stroke:var(--bl-violet);
  stroke-dasharray:100; stroke-dashoffset:100;
  animation:blDraw 1.1s var(--bl-out) .16s both;
}
@keyframes blDraw{ to{ stroke-dashoffset:0; } }

.bl-tips{ position:absolute; inset:0; pointer-events:none; }
.bl-tip{
  position:absolute; transform:translate(-50%, -100%);
  margin-top:calc(-4px - var(--lane) * 22px);
  padding:3px 6px; border-radius:8px;
  background:rgba(255,255,255,.95); color:var(--bl-violet);
  font-size:9px; font-weight:750; font-variant-numeric:tabular-nums;
  letter-spacing:-.01em;
  box-shadow:0 6px 14px -9px rgba(70,60,160,.75), inset 0 0 0 1px #E9E5FA;
  white-space:nowrap;
  animation:blTipIn .34s ease both;
}
@keyframes blTipIn{ from{ opacity:0; } to{ opacity:1; } }

.bl-xaxis{ position:relative; height:14px; margin:0 0 14px; }
.bl-xaxis span{
  position:absolute; top:0; transform:translateX(-50%);
  font-size:9px; color:var(--bl-ink3); font-variant-numeric:tabular-nums;
  white-space:nowrap;
}

/* ---------- 记一笔 ---------- */
.bl-add{
  display:flex; align-items:center; justify-content:center; gap:7px;
  width:100%; height:48px; margin-top:12px; border-radius:16px; cursor:pointer;
  font-family:inherit; font-size:13px; font-weight:700; color:#fff;
  background:linear-gradient(135deg,#7C6CF2,#6A5AE0);
  box-shadow:0 18px 30px -20px rgba(96,74,224,.95), inset 0 1px 0 rgba(255,255,255,.2);
  transition:transform .2s var(--bl-spring), box-shadow .2s;
}
.bl-add:active{ transform:scale(.985); box-shadow:0 10px 20px -16px rgba(96,74,224,.9); }

/* ---------- 表单 ---------- */
.bl-form{ margin-top:12px; padding:16px 16px 18px; animation:blPop .5s var(--bl-spring) both; }
@keyframes blPop{ from{ opacity:0; transform:translateY(10px) scale(.98); } to{ opacity:1; transform:none; } }

.bl-form-head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.bl-form-head b{ font-size:14px; font-weight:750; }
.bl-x{ display:flex; padding:6px; border-radius:8px; color:var(--bl-ink3); cursor:pointer; }

.bl-field{ margin-top:12px; }
.bl-field.mt{ margin-top:14px; }
.bl-lb{ display:block; margin-bottom:7px; font-size:10.5px; font-weight:650; color:var(--bl-ink3); letter-spacing:.02em; }

.bl-picks{ display:flex; gap:7px; flex-wrap:wrap; }
.bl-catpicks{ display:flex; gap:7px; flex-wrap:wrap; }
.bl-pick{
  height:32px; padding:0 13px; border-radius:10px; cursor:pointer;
  font-family:inherit; font-size:11.5px; font-weight:600; color:var(--bl-ink2);
  background:#FAFAFE; box-shadow:inset 0 0 0 1px #EEECF9;
  transition:transform .18s var(--bl-spring), background .2s, color .2s, box-shadow .2s;
}
.bl-pick.sm{ height:30px; padding:0 11px; font-size:11px; }
.bl-pick:active{ transform:scale(.94); }
.bl-pick.on{
  color:#fff; background:linear-gradient(135deg,#7C6CF2,#6A5AE0);
  box-shadow:0 8px 16px -12px rgba(96,74,224,.95);
}
.bl-pick-input{
  height:30px; width:96px; padding:0 10px; border-radius:10px; outline:none;
  font-family:inherit; font-size:11px; color:var(--bl-ink);
  background:#FAFAFE; box-shadow:inset 0 0 0 1px #EEECF9;
}

.bl-money{
  display:flex; align-items:center; gap:6px;
  height:52px; padding:0 14px; border-radius:14px;
  background:#FAFAFE; box-shadow:inset 0 0 0 1px #EEECF9;
  transition:box-shadow .2s;
}
.bl-money:focus-within{ box-shadow:inset 0 0 0 1.5px var(--bl-violet2); background:#fff; }
.bl-money i{ font-style:normal; font-size:15px; font-weight:650; color:var(--bl-ink3); }
.bl-money input{
  flex:1; min-width:0; border:none; outline:none; background:none;
  font-family:inherit; font-size:22px; font-weight:750; letter-spacing:-.02em;
  color:var(--bl-ink); font-variant-numeric:tabular-nums;
}

.bl-area{
  width:100%; box-sizing:border-box; min-height:66px; padding:11px 13px;
  border:none; border-radius:14px; resize:none; outline:none;
  font-family:inherit; font-size:12px; line-height:1.55; color:var(--bl-ink);
  background:#FAFAFE; box-shadow:inset 0 0 0 1px #EEECF9;
  transition:box-shadow .2s, background .2s;
}
.bl-area:focus{ background:#fff; box-shadow:inset 0 0 0 1.5px var(--bl-violet2); }

.bl-form-btns{ display:flex; gap:9px; margin-top:16px; }
.bl-btn{
  flex:1; height:46px; border-radius:14px; cursor:pointer;
  font-family:inherit; font-size:13px; font-weight:700; color:#fff;
  background:linear-gradient(135deg,#7C6CF2,#6A5AE0);
  box-shadow:0 14px 24px -18px rgba(96,74,224,.95);
  transition:transform .18s var(--bl-spring), opacity .2s;
}
.bl-btn:disabled{ opacity:.45; cursor:default; }
.bl-btn.ghost{
  color:var(--bl-ink2); background:#FAFAFE;
  box-shadow:inset 0 0 0 1px #E9E7F8;
}
.bl-btn:active:not(:disabled){ transform:scale(.975); }

.bl-del{
  display:block; margin:14px auto 0;
  font-family:inherit; font-size:10.5px; font-weight:650; color:#D0637F; cursor:pointer;
}
.bl-del-confirm{
  display:flex; align-items:center; justify-content:center; gap:8px;
  margin-top:12px; font-size:10.5px; color:var(--bl-ink2);
}
.bl-del-confirm button{
  font-family:inherit; font-size:10.5px; font-weight:650; padding:6px 12px;
  border-radius:9px; background:#FAFAFE; box-shadow:inset 0 0 0 1px #E9E7F8; cursor:pointer;
}
.bl-del-confirm button.danger{ color:#fff; background:#D0637F; box-shadow:none; }

.bl-warn{ font-size:11px; color:#B14A6E; margin:10px 2px 0; }
.bl-warn.box{
  padding:11px 14px; border-radius:14px; margin:12px 0 0;
  background:#FFF0F4; box-shadow:inset 0 0 0 1px #FFD7E2;
}

/* ---------- 明细 ---------- */
.bl-sec{
  display:flex; align-items:baseline; justify-content:space-between;
  margin:20px 4px 10px;
}
.bl-sec b{ font-size:12.5px; font-weight:750; color:var(--bl-ink); letter-spacing:.01em; }
.bl-sec span{ font-size:10px; color:var(--bl-ink3); font-variant-numeric:tabular-nums; }

.bl-daygrp{ margin-bottom:12px; }
.bl-dayhead{
  display:flex; align-items:center; justify-content:space-between;
  padding:0 4px; margin-bottom:7px;
}
.bl-dayhead span{ font-size:10.5px; font-weight:650; color:var(--bl-ink3); }
.bl-dayhead em{ font-style:normal; font-size:10px; color:var(--bl-ink3); font-variant-numeric:tabular-nums; }

.bl-rows{
  display:block; border-radius:20px; background:#fff;
  box-shadow:var(--bl-shadow), inset 0 0 0 1px rgba(255,255,255,.9);
  overflow:hidden;
}
.bl-row{
  position:relative;
  display:flex; align-items:center; gap:11px; width:100%;
  padding:12px 14px; text-align:left; cursor:pointer;
  background:none; border:none;
  transition:background .18s ease;
}
.bl-row::after{
  content:''; position:absolute; left:57px; right:0; bottom:0; height:1px;
  background:var(--bl-line);
}
.bl-row:last-child::after{ display:none; }
.bl-row:active{ background:#FAFAFE; }

.bl-row-ic{
  width:38px; height:38px; flex:0 0 auto; border-radius:12px;
  display:flex; align-items:center; justify-content:center;
  font-size:14px; font-weight:750; color:#fff;
  box-shadow:0 10px 18px -14px rgba(50,40,130,.9);
}
.bl-row-ic.sm{
  width:30px; height:30px; border-radius:10px; font-size:12px;
  box-shadow:0 8px 14px -12px rgba(50,40,130,.85);
}
.bl-row-body{ flex:1; min-width:0; }
.bl-row-top{ display:flex; align-items:center; gap:5px; }
.bl-row-top b{ font-size:13px; font-weight:700; letter-spacing:-.01em; color:var(--bl-ink); }
.bl-remark{
  margin:3px 0 0; font-size:10.5px; line-height:1.5; color:var(--bl-ink2);
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.bl-row-meta{
  display:flex; align-items:center; gap:7px; margin-top:5px;
  font-size:9px; color:var(--bl-ink3); font-variant-numeric:tabular-nums;
}

.bl-row-amt{ flex:0 0 auto; text-align:right; }
.bl-row-amt b{
  display:block; font-size:15px; font-weight:750; letter-spacing:-.02em;
  color:var(--bl-ink); font-variant-numeric:tabular-nums;
}
.bl-row-amt b i{ font-style:normal; font-size:10px; font-weight:600; color:var(--bl-ink3); margin-right:1px; }
.bl-row-amt b.soft{ font-size:12px; color:var(--bl-ink3); }
.bl-row-amt b.soft small{ font-size:9px; font-weight:600; }

/* ---------- 状态 ---------- */
.bl-loading{ display:flex; gap:6px; justify-content:center; padding:28px; }
.bl-loading i{ width:7px; height:7px; border-radius:50%; background:#D9D5F5; animation:blBlink 1s ease-in-out infinite; }
.bl-loading i:nth-child(2){ animation-delay:.18s; }
.bl-loading i:nth-child(3){ animation-delay:.36s; }
@keyframes blBlink{ 0%,100%{ opacity:.22; transform:translateY(0); } 50%{ opacity:1; transform:translateY(-3px); } }

.bl-empty{
  padding:26px 18px; text-align:center;
  border-radius:20px;
}
.bl-empty b{ display:block; font-size:13px; font-weight:700; }
.bl-empty span{ display:block; margin-top:5px; font-size:10.5px; color:var(--bl-ink3); }

/* ---------- 本月基金弹层 ---------- */
.bl-mask{
  position:absolute; inset:0; z-index:60;
  display:flex; align-items:flex-end;
  background:rgba(28,24,70,.28);
  -webkit-backdrop-filter:blur(2px); backdrop-filter:blur(2px);
  animation:blMaskIn .26s ease both;
}
@keyframes blMaskIn{ from{ opacity:0; } to{ opacity:1; } }

.bl-sheet{
  width:100%;
  padding:10px 20px 20px;
  border-radius:26px 26px 0 0;
  background:#fff;
  box-shadow:0 -22px 44px -30px rgba(40,30,110,.6);
  animation:blSheetIn .44s var(--bl-out) both;
}
@keyframes blSheetIn{ from{ transform:translateY(100%); } to{ transform:none; } }

.bl-grip{
  display:block; width:38px; height:4px; margin:0 auto 14px;
  border-radius:99px; background:#E4E1F3;
}
.bl-sheet h4{ margin:0; font-size:15px; font-weight:750; letter-spacing:-.02em; }
.bl-sheet > p{ margin:5px 0 14px; font-size:10.5px; line-height:1.6; color:var(--bl-ink3); }

.bl-binput{
  display:flex; align-items:center; gap:6px;
  height:56px; padding:0 16px; border-radius:16px;
  background:#F2F1FA; box-shadow:inset 0 0 0 1.5px #DED8F4;
  transition:box-shadow .2s, background .2s;
}
.bl-binput:focus-within{ background:#fff; box-shadow:inset 0 0 0 1.6px var(--bl-violet2); }
.bl-binput i{ font-style:normal; font-size:16px; font-weight:650; color:var(--bl-ink3); }
.bl-binput input{
  flex:1; min-width:0; border:none; outline:none; background:none;
  font-family:inherit; font-size:26px; font-weight:750; letter-spacing:-.03em;
  color:var(--bl-ink); font-variant-numeric:tabular-nums;
  -moz-appearance:textfield;
}
.bl-binput input::-webkit-outer-spin-button,
.bl-binput input::-webkit-inner-spin-button{ -webkit-appearance:none; margin:0; }
.bl-binput input::placeholder{ color:#B4B1CC; font-weight:650; font-size:18px; letter-spacing:0; }

.bl-quick{ display:flex; gap:7px; margin-top:10px; }
.bl-quick button{
  flex:1; height:32px; border-radius:10px; cursor:pointer;
  font-family:inherit; font-size:11px; font-weight:650; color:var(--bl-ink2);
  background:#FAFAFE; box-shadow:inset 0 0 0 1px #EEECF9;
  font-variant-numeric:tabular-nums;
  transition:transform .18s var(--bl-spring), color .2s, box-shadow .2s;
}
.bl-quick button:active{ transform:scale(.94); color:var(--bl-violet); box-shadow:inset 0 0 0 1px var(--bl-violet2); }

.bl-sheet .bl-del{ color:var(--bl-ink3); margin-top:12px; font-weight:600; }

/* ---------- 入场 ---------- */
.bl-in{ animation:blFade .6s var(--bl-out) both; animation-delay:calc(var(--i) * 42ms); }
@keyframes blFade{ from{ opacity:0; transform:translateY(10px); } to{ opacity:1; transform:none; } }

@media (prefers-reduced-motion: reduce){
  .bl-in, .bl-bars rect, .bl-line, .bl-bubble, .bl-form, .bl-mask, .bl-sheet{ animation:none !important; }
  .bl-line{ stroke-dashoffset:0 !important; }
  .bl-hero-bar i, .bl-seg-glider{ transition:none !important; }
}
</style>
