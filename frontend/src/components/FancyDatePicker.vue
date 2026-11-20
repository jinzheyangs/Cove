<template>
  <div class="dp" ref="rootEl">
    <button type="button" class="dp-trigger" :class="{ filled: !!modelValue, compact }" @click="openSheet">
      <span class="dp-val">{{ modelValue ? pretty : placeholder }}</span>
      <svg class="dp-ico" width="17" height="17" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
        <rect x="3.4" y="5.2" width="17.2" height="15.4" rx="3.4" />
        <path d="M7.6 3v3.6M16.4 3v3.6M3.4 10.6h17.2" />
      </svg>
    </button>

    <Teleport :to="hostEl || 'body'" :disabled="!hostEl">
      <Transition name="dp">
      <div v-if="open" class="dp-layer">
        <div class="dp-mask" @click="close"></div>

        <div class="dp-sheet" role="dialog" aria-modal="true" aria-label="选择日期">
          <span class="dp-grip" aria-hidden="true"></span>

          <header class="dp-head">
            <button
              type="button"
              class="dp-title"
              :class="{ open: jumpOpen }"
              :aria-expanded="jumpOpen"
              aria-label="选择年份和月份"
              @click="jumpOpen ? (jumpOpen = false) : openJump()"
            >
              <b>{{ titleMain }}</b>
              <span>{{ titleSub }}</span>
              <svg class="dp-title__chev" width="10" height="6" viewBox="0 0 10 6" fill="none"
                   stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true">
                <path d="M1 1 5 5l4-4" />
              </svg>
            </button>
            <div class="dp-nav">
              <button type="button" aria-label="上个月" @click="shift(-1)">
                <svg width="9" height="15" viewBox="0 0 11 18" fill="none"
                     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9.5 1.5 2 9l7.5 7.5" />
                </svg>
              </button>
              <button type="button" aria-label="下个月" @click="shift(1)">
                <svg width="9" height="15" viewBox="0 0 11 18" fill="none"
                     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1.5 1.5 9 9l-7.5 7.5" />
                </svg>
              </button>
            </div>
          </header>

          <!-- 点标题就能跳年 / 月：不用一个月一个月翻 -->
          <div v-if="jumpOpen" class="dp-jump">
            <div class="dp-jump__cap">
              <span><b>{{ jumpY }}</b> 年</span>
              <button type="button" class="dp-jump__back" @click="jumpOpen = false">回到日历</button>
            </div>
            <div class="dp-years" ref="yearsEl">
              <button
                v-for="y in years"
                :key="y"
                type="button"
                class="dp-y"
                :class="{ on: y === jumpY }"
                @click="pickYear(y)"
              >{{ y }}</button>
            </div>
            <div class="dp-months">
              <button
                v-for="mi in 12"
                :key="mi"
                type="button"
                class="dp-m"
                :class="{ on: mi - 1 === viewM && jumpY === viewY, out: jumpY === thisY && mi - 1 > thisM }"
                :disabled="jumpY === thisY && mi - 1 > thisM"
                @click="pickMonth(mi - 1)"
              >{{ mi }}<i>月</i></button>
            </div>
          </div>

          <!-- 年 / 月 滑动条 -->
          <div v-if="!simple && !jumpOpen" class="dp-strip-wrap">
            <div class="dp-strip" ref="stripEl" @scroll="onStripScroll">
              <div class="dp-strip-inner" ref="stripInner">
                <button
                  v-for="m in months"
                  :key="m.i"
                  type="button"
                  class="dp-mpill"
                  :class="{ on: m.i === activeIdx }"
                  :data-i="m.i"
                  @click="goIndex(m.i)"
                >{{ m.m + 1 }}</button>
              </div>
            </div>
            <span class="dp-year-fix" aria-hidden="true">{{ activeYear }}</span>
          </div>

          <div v-if="!jumpOpen" class="dp-week" aria-hidden="true">
            <span v-for="w in WEEKS" :key="w">{{ w }}</span>
          </div>

          <div
            v-if="!jumpOpen"
            class="dp-stage"
            @pointerdown="onDown"
            @pointermove="onMove"
            @pointerup="onUp"
            @pointercancel="onUp"
            @click.capture="blockClick"
          >
            <div class="dp-track" ref="trackEl">
              <Transition :name="dir > 0 ? 'dp-next' : 'dp-prev'" mode="out-in">
                <div class="dp-grid" :key="`${viewY}-${viewM}`">
                  <template v-for="(c, i) in cells" :key="i">
                    <span v-if="!c.date" class="dp-blank"></span>
                    <button
                      v-else
                      type="button"
                      class="dp-day"
                      :class="{ on: c.key === selected, today: c.key === todayKey, out: c.disabled }"
                      :style="{ '--i': i }"
                      :disabled="c.disabled"
                      @click="pick(c)"
                    ><span>{{ c.day }}</span></button>
                  </template>
                </div>
              </Transition>
            </div>
          </div>

          <footer class="dp-foot">
            <button type="button" class="dp-ghost" @click="jumpToday">今天</button>
            <button type="button" class="dp-ok" :disabled="!selected" @click="confirm">确定</button>
          </footer>
        </div>
      </div>
    </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  /* 不能选到未来的日子 */
  max: { type: String, default: '' },
  placeholder: { type: String, default: '选择日期' },
  /* 设计走查用：带上 openDate=1 时直接摊开 */
  autoOpen: { type: Boolean, default: false },
  /* 紧凑形态（设置页抽屉里用） */
  compact: { type: Boolean, default: false },
  /* 极简形态：不要月份滑动条、不要网格拖拽，只留箭头翻月 */
  simple: { type: Boolean, default: false },
  /* 浮层挂载容器；不传则自动找 .onb / .ds-card */
  host: { type: Object, default: null },
});
const emit = defineEmits(['update:modelValue']);

const WEEKS = ['日', '一', '二', '三', '四', '五', '六'];
const MIN_YEAR = 1940;

const open = ref(false);
const selected = ref(props.modelValue || '');
const viewY = ref(0);
const viewM = ref(0);
const dir = ref(1);

const stripEl = ref(null);
const stripInner = ref(null);
const trackEl = ref(null);
const rootEl = ref(null);
const hostEl = ref(null);
const activeIdx = ref(0);
let centers = [];

const pad = (n) => String(n).padStart(2, '0');
const keyOf = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

const now = new Date();
const thisY = now.getFullYear();
const thisM = now.getMonth();
const todayKey = keyOf(now);

/* 触发框永远显示外部传入的值，面板里选中的是临时态 */
const pretty = computed(() => (props.modelValue ? props.modelValue.replace(/-/g, '.') : ''));

/* 可选月份序列：1940 起，到今天所在月为止 */
const months = computed(() => {
  const arr = [];
  for (let y = MIN_YEAR; y <= thisY; y += 1) {
    for (let m = 0; m < 12; m += 1) {
      if (y === thisY && m > thisM) break;
      arr.push({ y, m, i: arr.length, first: m === 0 });
    }
  }
  return arr;
});
const idxOf = (y, m) => (y - MIN_YEAR) * 12 + m;
const activeYear = computed(() => (months.value[activeIdx.value] || {}).y || viewY.value);
const titleMain = computed(() => (props.simple ? viewY.value : viewM.value + 1));
const titleSub = computed(() => (props.simple ? `${viewM.value + 1} 月` : '月'));

const cells = computed(() => {
  const first = new Date(viewY.value, viewM.value, 1);
  const lead = first.getDay();
  const total = new Date(viewY.value, viewM.value + 1, 0).getDate();
  const list = [];
  for (let i = 0; i < lead; i += 1) list.push({ date: null });
  for (let d = 1; d <= total; d += 1) {
    const date = new Date(viewY.value, viewM.value, d);
    const key = keyOf(date);
    list.push({ date, day: d, key, disabled: !!props.max && key > props.max });
  }
  while (list.length % 7 !== 0 || list.length < 35) list.push({ date: null });
  return list;
});

/* ---------------- 快速跳年 / 月 ---------------- */
/* 点标题展开一版「年 + 月」网格：出生年份动辄差几十年，
   一个月一个月翻太慢，直接点年点月到位 */
const jumpOpen = ref(false);
const jumpY = ref(2000);
const yearsEl = ref(null);
const years = computed(() => {
  const arr = [];
  for (let y = MIN_YEAR; y <= thisY; y += 1) arr.push(y);
  return arr;
});
function openJump(){
  jumpY.value = viewY.value;
  jumpOpen.value = true;
  nextTick(scrollYearIntoView);
}
function scrollYearIntoView(){
  const el = yearsEl.value;
  if (!el) return;
  const on = el.querySelector('.on');
  if (!on) return;
  el.scrollTop = on.offsetTop - el.clientHeight / 2 + on.offsetHeight / 2;
}
/* 应用某个年月：日历、月份条、选中态一起跟上 */
function applyYM(y, m){
  dir.value = (y > viewY.value || (y === viewY.value && m > viewM.value)) ? 1 : -1;
  viewY.value = y;
  viewM.value = m;
  const i = idxOf(y, m);
  activeIdx.value = i;
  if (centers.length) centerOn(i);
}
function pickYear(y){
  jumpY.value = y;
  applyYM(y, viewM.value);   // 先跳到那年，月份保留；想换月再点下面
}
function pickMonth(m){
  applyYM(jumpY.value, m);
  jumpOpen.value = false;
}

/* ---------------- 月份条：滚动联动 ---------------- */
function measure(){
  const strip = stripEl.value;
  const inner = stripInner.value;
  if (!strip || !inner) return;
  const sRect = strip.getBoundingClientRect();
  const base = strip.scrollLeft;
  centers = Array.from(inner.querySelectorAll('[data-i]')).map((el) => {
    const r = el.getBoundingClientRect();
    return r.left - sRect.left + base + r.width / 2;
  });
}
function centerOn(i, smooth = true){
  const el = stripEl.value;
  if (!el || !centers[i]) return;
  el.scrollTo({ left: centers[i] - el.clientWidth / 2, behavior: smooth ? 'smooth' : 'auto' });
}

let raf = 0;
let settle = 0;
function onStripScroll(){
  if (raf) return;
  raf = requestAnimationFrame(() => {
    raf = 0;
    const el = stripEl.value;
    if (!el || !centers.length) return;
    const mid = el.scrollLeft + el.clientWidth / 2;
    let lo = 0, hi = centers.length - 1, best = 0, bestD = Infinity;
    while (lo <= hi) {
      const i = (lo + hi) >> 1;
      const d = Math.abs(centers[i] - mid);
      if (d < bestD) { bestD = d; best = i; }
      if (centers[i] < mid) lo = i + 1; else hi = i - 1;
    }
    activeIdx.value = best;
    clearTimeout(settle);
    settle = setTimeout(() => applyMonth(best), 120);
  });
}
function applyMonth(i){
  const m = months.value[i];
  if (!m || (m.y === viewY.value && m.m === viewM.value)) return;
  dir.value = i > idxOf(viewY.value, viewM.value) ? 1 : -1;
  viewY.value = m.y;
  viewM.value = m.m;
}
function goIndex(i){
  activeIdx.value = i;
  applyMonth(i);
  centerOn(i);
}

/* ---------------- 网格：左右拖动翻月 ---------------- */
let downX = 0;
let dragging = false;
let swiping = false;
let lastX = 0;

function onDown(e){
  if (props.simple) return;
  if (e.pointerType === 'mouse' && e.button !== 0) return;
  downX = e.clientX;
  lastX = e.clientX;
  dragging = true;
  swiping = false;
  try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* ignore */ }
}
function onMove(e){
  if (!dragging) return;
  const dx = e.clientX - downX;
  lastX = e.clientX;
  if (!swiping && Math.abs(dx) > 9) swiping = true;
  if (!swiping) return;
  const off = Math.max(-96, Math.min(96, dx * 0.56));
  const t = trackEl.value;
  if (t) {
    t.style.transition = 'none';
    t.style.transform = `translateX(${off}px)`;
  }
  e.preventDefault();
}
function onUp(){
  if (!dragging) return;
  dragging = false;
  const dx = lastX - downX;
  const t = trackEl.value;
  if (t) {
    t.style.transition = 'transform .34s cubic-bezier(.16,1,.3,1)';
    t.style.transform = 'translateX(0)';
    setTimeout(() => { if (t) t.style.transition = ''; }, 360);
  }
  if (swiping && Math.abs(dx) > 58) shift(dx < 0 ? 1 : -1, false);
  if (swiping) setTimeout(() => { swiping = false; }, 60);
}
function blockClick(e){
  if (swiping) {
    e.stopPropagation();
    e.preventDefault();
  }
}

/* ---------------- 基础动作 ---------------- */
function openSheet(){
  const base = props.modelValue || props.max || todayKey;
  const [y, m] = base.split('-').map(Number);
  viewY.value = y;
  viewM.value = (m || 1) - 1;
  selected.value = props.modelValue || '';
  jumpOpen.value = false;
  open.value = true;
  nextTick(() => {
    measure();
    const i = idxOf(viewY.value, viewM.value);
    activeIdx.value = i;
    centerOn(i, false);
  });
}
function close(){ open.value = false; }

function shift(step, syncStrip = true){
  const target = new Date(viewY.value, viewM.value + step, 1);
  const y = target.getFullYear();
  const m = target.getMonth();
  if (y < MIN_YEAR || (y > thisY) || (y === thisY && m > thisM)) return;
  dir.value = step;
  viewY.value = y;
  viewM.value = m;
  const i = idxOf(y, m);
  activeIdx.value = i;
  if (syncStrip) centerOn(i);
}

function pick(c){
  if (c.disabled) return;
  selected.value = c.key;
}

function jumpToday(){
  viewY.value = thisY;
  viewM.value = thisM;
  selected.value = todayKey;
  jumpOpen.value = false;
  nextTick(() => {
    const i = idxOf(thisY, thisM);
    activeIdx.value = i;
    centerOn(i);
  });
}

function confirm(){
  if (!selected.value) return;
  emit('update:modelValue', selected.value);
  open.value = false;
}
onMounted(() => {
  if (props.host) hostEl.value = props.host;
  else if (rootEl.value) hostEl.value = rootEl.value.closest('.onb, .ds-card') || null;
  window.addEventListener('resize', measure);
  if (props.autoOpen) openSheet();
});
onBeforeUnmount(() => window.removeEventListener('resize', measure));
</script>

<style scoped>
.dp{ display:block; }

/* ---- 触发框 ---- */
.dp-trigger{
  width:100%; height:56px; padding:0 14px;
  display:flex; align-items:center; justify-content:space-between; gap:10px;
  border:1px solid #EAEAEF; border-radius:13px; background:#fff;
  font-family:inherit; font-size:15px; color:#A8A8B0;
  cursor:pointer; text-align:left;
  transition:border-color .18s cubic-bezier(.16,1,.3,1), box-shadow .18s cubic-bezier(.16,1,.3,1), transform .18s ease;
}
.dp-trigger.filled{ color:#111114; font-variant-numeric:tabular-nums; }
.dp-trigger.compact{
  height:42px; border-radius:12px; padding:0 12px;
  font-size:13.5px;
}
.dp-trigger:active{ transform:scale(.994); }
.dp-trigger:focus-visible{ outline:none; border-color:#111114; box-shadow:0 0 0 3px rgba(17,17,20,.06); }
.dp-ico{ flex:0 0 auto; color:#B6B6BE; transition:color .2s ease, transform .3s cubic-bezier(.34,1.4,.64,1); }
.dp-trigger.filled .dp-ico{ color:#6C6C75; }
.dp-trigger:hover .dp-ico{ transform:rotate(-6deg) scale(1.04); }

/* ---- 浮层 ---- */
.dp-layer{
  position:absolute; inset:0; z-index:70;
  display:flex; flex-direction:column; justify-content:flex-end;
}
.dp-mask{
  position:absolute; inset:0;
  background:rgba(10,10,14,.44);
  backdrop-filter:blur(3px);
  -webkit-backdrop-filter:blur(3px);
}
.dp-sheet{
  position:relative;
  background:#fff;
  border-radius:26px 26px 0 0;
  padding:9px 0 calc(14px + env(safe-area-inset-bottom,0px));
  box-shadow:0 -22px 60px -34px rgba(0,0,0,.55);
  will-change:transform;
}
.dp-grip{ display:block; width:36px; height:4px; margin:2px auto 12px; border-radius:99px; background:#E8E8EC; }

.dp-head{ display:flex; align-items:center; justify-content:space-between; padding:0 16px 0 18px; }
.dp-title{
  display:flex; align-items:baseline; gap:6px;
  padding:2px 8px 2px 0; border:0; background:none;
  font-family:inherit; cursor:pointer; text-align:left;
  border-radius:10px;
  transition:background .18s ease;
}
.dp-title:active{ background:#F5F5F7; }
.dp-title b{ font-size:20px; font-weight:800; letter-spacing:-.03em; color:#111114; font-variant-numeric:tabular-nums; }
.dp-title span{ font-size:13px; font-weight:600; color:#8A8A92; }
.dp-title__chev{
  align-self:center; margin-left:1px; color:#9B9BA3;
  transition:transform .26s cubic-bezier(.16,1,.3,1), color .18s ease;
}
.dp-title.open .dp-title__chev{ transform:rotate(180deg); color:#111114; }
.dp-title.open{ background:#F5F5F7; }

/* ---- 快速跳年 / 月 ---- */
.dp-jump{ padding:2px 16px 6px; animation:dpJumpIn .24s cubic-bezier(.16,1,.3,1) both; }
@keyframes dpJumpIn{ from{ opacity:0; transform:translateY(6px); } to{ opacity:1; transform:none; } }
.dp-jump__cap{
  display:flex; align-items:center; justify-content:space-between;
  padding:4px 2px 8px;
  font-size:13px; font-weight:600; color:#8A8A92;
}
.dp-jump__cap b{ font-size:15px; font-weight:800; color:#111114; font-variant-numeric:tabular-nums; }
.dp-jump__back{
  border:0; background:none; padding:4px 6px; border-radius:9px;
  font-family:inherit; font-size:12.5px; font-weight:600; color:#3B3B42;
  cursor:pointer;
}
.dp-jump__back:active{ background:#F1F1F5; }

.dp-years{
  display:grid; grid-template-columns:repeat(4, 1fr); gap:6px;
  max-height:126px; overflow-y:auto;
  padding:2px 2px 4px;
  -webkit-overflow-scrolling:touch;
  mask-image:linear-gradient(180deg, transparent 0, #000 8px, #000 calc(100% - 8px), transparent 100%);
  -webkit-mask-image:linear-gradient(180deg, transparent 0, #000 8px, #000 calc(100% - 8px), transparent 100%);
}
.dp-years::-webkit-scrollbar{ display:none; }
.dp-y{
  height:34px; border-radius:10px; border:0; background:#F5F5F7;
  font-family:inherit; font-size:13.5px; font-weight:600; color:#3B3B42;
  font-variant-numeric:tabular-nums; cursor:pointer;
  transition:background .18s ease, color .18s ease, transform .2s cubic-bezier(.34,1.4,.64,1);
}
.dp-y:active{ transform:scale(.95); }
.dp-y.on{ background:#111114; color:#fff; }

.dp-months{
  display:grid; grid-template-columns:repeat(4, 1fr); gap:6px;
  margin-top:10px; padding-top:10px;
  border-top:1px solid #F1F1F5;
}
.dp-m{
  height:40px; border-radius:11px; border:0; background:#F5F5F7;
  display:flex; align-items:baseline; justify-content:center; gap:2px;
  font-family:inherit; font-size:15px; font-weight:700; color:#3B3B42;
  font-variant-numeric:tabular-nums; cursor:pointer;
  transition:background .18s ease, color .18s ease, transform .2s cubic-bezier(.34,1.4,.64,1);
}
.dp-m i{ font-style:normal; font-size:11px; font-weight:600; color:#8A8A92; }
.dp-m.on{ background:#111114; color:#fff; }
.dp-m.on i{ color:rgba(255,255,255,.66); }
.dp-m:active{ transform:scale(.96); }
.dp-m.out{ color:#C9C9D1; cursor:default; }
.dp-m.out i{ color:#C9C9D1; }
.dp-m.out:active{ transform:none; }
.dp-nav{ display:flex; gap:4px; }
.dp-nav button{
  width:34px; height:34px; display:grid; place-items:center;
  border-radius:11px; color:#3B3B42; background:#F5F5F7;
  cursor:pointer;
  transition:background .18s ease, transform .16s cubic-bezier(.34,1.4,.64,1);
}
.dp-nav button:active{ transform:scale(.92); background:#EDEDF1; }

/* ---- 年月滑动条 ---- */
.dp-strip-wrap{ position:relative; margin-top:8px; }
.dp-year-fix{
  position:absolute; left:12px; top:7px; height:34px;
  display:flex; align-items:center; padding:0 12px;
  border-radius:11px; background:#F5F5F7;
  font-size:13.5px; font-weight:800; letter-spacing:-.01em;
  color:#111114; font-variant-numeric:tabular-nums;
  box-shadow:0 0 0 5px #fff;
  pointer-events:none; z-index:2;
}
.dp-strip{
  overflow-x:auto; overflow-y:hidden;
  scroll-snap-type:x mandatory;
  -webkit-overflow-scrolling:touch;
  scrollbar-width:none;
  padding:6px 0 4px;
  mask-image:linear-gradient(90deg, transparent 0, #000 12%, #000 88%, transparent 100%);
  -webkit-mask-image:linear-gradient(90deg, transparent 0, #000 12%, #000 88%, transparent 100%);
}
.dp-strip::-webkit-scrollbar{ display:none; }
.dp-strip-inner{
  display:flex; align-items:center; gap:2px;
  padding:0 calc(50% - 20px);
  width:max-content;
}
.dp-mpill{
  flex:0 0 auto;
  scroll-snap-align:center;
  min-width:40px; height:32px;
  display:grid; place-items:center;
  border-radius:10px; background:none;
  font-family:inherit; font-size:13.5px; font-weight:600;
  color:#3B3B42; font-variant-numeric:tabular-nums;
  cursor:pointer;
  transition:background .2s ease, color .2s ease, transform .22s cubic-bezier(.34,1.4,.64,1);
}
.dp-mpill.on{ background:#111114; color:#fff; transform:scale(1.04); }

.dp-week{
  display:grid; grid-template-columns:repeat(7, 1fr);
  margin-top:10px; padding:0 16px;
}
.dp-week span{ text-align:center; font-size:10px; font-weight:700; letter-spacing:.08em; color:#A8A8B0; }

.dp-stage{
  margin-top:4px; position:relative; overflow:hidden;
  touch-action:pan-y;
  padding:0 16px;
}
.dp-track{ will-change:transform; }
.dp-grid{ display:grid; grid-template-columns:repeat(7, 1fr); gap:2px 0; }
.dp-blank{ height:42px; }

.dp-day{
  position:relative; height:42px;
  display:grid; place-items:center;
  border-radius:10px; background:none;
  font-family:inherit; font-size:14.5px; font-weight:600;
  color:#3B3B42; font-variant-numeric:tabular-nums;
  cursor:pointer;
  animation:dpDayIn .34s cubic-bezier(.16,1,.3,1) both;
  animation-delay:calc(var(--i) * 7ms);
  transition:color .18s ease;
}
.dp-day::before{
  content:''; position:absolute; inset:3px; border-radius:50%;
  background:transparent; transform:scale(.7);
  transition:transform .22s cubic-bezier(.34,1.4,.64,1), background .2s ease;
}
.dp-day > span{ position:relative; z-index:1; line-height:1; }
.dp-day:active{ transform:scale(.94); }
.dp-day.out{ color:#C9C9D1; cursor:default; }
.dp-day.out:active{ transform:none; }
.dp-day.today::after{
  content:''; position:absolute; bottom:6px; left:50%; width:4px; height:4px;
  border-radius:50%; background:#B6B6BE; transform:translateX(-50%);
}
.dp-day.on{ color:#fff; }
.dp-day.on::before{
  background:#111114;
  transform:scale(1);
  animation:dpPick .34s cubic-bezier(.34,1.5,.64,1) both;
}
.dp-day.on::after{ background:rgba(255,255,255,.5); }

@keyframes dpDayIn{
  from{ opacity:0; transform:translateY(6px); }
  to{ opacity:1; transform:none; }
}
@keyframes dpPick{
  0%{ transform:scale(.72); }
  62%{ transform:scale(1.1); }
  100%{ transform:scale(1); }
}

.dp-foot{
  display:flex; align-items:center; gap:10px;
  margin:14px 16px 0; padding-top:12px;
  border-top:1px solid #F1F1F5;
}
.dp-ghost{
  height:52px; padding:0 20px; border-radius:15px;
  background:#F5F5F7; color:#3B3B42;
  font-family:inherit; font-size:13.5px; font-weight:600;
  cursor:pointer;
  transition:background .18s ease, transform .16s cubic-bezier(.34,1.4,.64,1);
}
.dp-ghost:active{ transform:scale(.96); background:#EDEDF1; }
.dp-ok{
  flex:1; height:52px; border-radius:15px;
  background:#111114; color:#fff;
  font-family:inherit; font-size:15px; font-weight:600;
  cursor:pointer;
  transition:transform .16s cubic-bezier(.34,1.4,.64,1), background .2s ease, color .2s ease;
}
.dp-ok:active:not(:disabled){ transform:scale(.98); background:#000; }
.dp-ok:disabled{ background:#EFEFF3; color:#B6B6BE; cursor:default; }

/* ---- 浮层进出 ---- */
.dp-enter-active{ transition:opacity .3s ease; }
.dp-enter-active .dp-sheet{ transition:transform .46s cubic-bezier(.16,1,.3,1); }
.dp-enter-from{ opacity:0; }
.dp-enter-from .dp-sheet{ transform:translateY(102%); }

.dp-leave-active{ transition:opacity .26s ease .04s; }
.dp-leave-active .dp-sheet{ transition:transform .34s cubic-bezier(.4,0,.9,1); }
.dp-leave-to{ opacity:0; }
.dp-leave-to .dp-sheet{ transform:translateY(102%); }

/* ---- 月份切换 ---- */
.dp-next-enter-active,.dp-next-leave-active,
.dp-prev-enter-active,.dp-prev-leave-active{
  transition:opacity .22s ease, transform .26s cubic-bezier(.16,1,.3,1);
}
.dp-next-enter-from{ opacity:0; transform:translateX(26px); }
.dp-next-leave-to{ opacity:0; transform:translateX(-26px); }
.dp-prev-enter-from{ opacity:0; transform:translateX(-26px); }
.dp-prev-leave-to{ opacity:0; transform:translateX(26px); }

@media (prefers-reduced-motion: reduce){
  .dp-day{ animation:none; }
  .dp-day.on::before{ animation:none; }
  .dp-enter-active,.dp-enter-active .dp-sheet,
  .dp-leave-active,.dp-leave-active .dp-sheet,
  .dp-next-enter-active,.dp-next-leave-active,
  .dp-prev-enter-active,.dp-prev-leave-active{
    transition-duration:.01s !important;
  }
}
</style>
