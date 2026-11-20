<template>
  <div class="wp" :class="{ 'is-open': true }">
    <div class="wp-band" aria-hidden="true"></div>

    <div class="wp-cols">
      <!-- 年 -->
      <div ref="yEl" class="wp-col" data-col="y" @scroll="onScroll('y')">
        <span class="wp-pad" aria-hidden="true"></span>
        <button
          v-for="y in years" :key="'y' + y" type="button" class="wp-it"
          :class="{ on: y === sel.y }" @click="pick('y', y)"
        >{{ y }}</button>
        <span class="wp-pad" aria-hidden="true"></span>
      </div>

      <!-- 月 -->
      <div ref="mEl" class="wp-col wp-col--m" data-col="m" @scroll="onScroll('m')">
        <span class="wp-pad" aria-hidden="true"></span>
        <button
          v-for="m in 12" :key="'m' + m" type="button" class="wp-it"
          :class="{ on: m === sel.m }" @click="pick('m', m)"
        >{{ m }} 月</button>
        <span class="wp-pad" aria-hidden="true"></span>
      </div>

      <!-- 日 -->
      <div ref="dEl" class="wp-col" data-col="d" @scroll="onScroll('d')">
        <span class="wp-pad" aria-hidden="true"></span>
        <button
          v-for="d in days" :key="'d' + d" type="button" class="wp-it"
          :class="{ on: d === sel.d, off: isFuture(d) }" @click="pick('d', d)"
        >{{ d }} 日</button>
        <span class="wp-pad" aria-hidden="true"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  max: { type: String, default: '' },
});
const emit = defineEmits(['update:modelValue']);

const ITEM = 44;          // 每项高度，与 CSS 里的 --it 保持一致
const MIN_YEAR = 1940;

const now = new Date();
const thisY = now.getFullYear();
const today = `${thisY}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
const ceiling = computed(() => props.max || today);

const years = computed(() => {
  const list = [];
  for (let y = MIN_YEAR; y <= thisY; y += 1) list.push(y);
  return list;
});

function parse(v) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v || '');
  if (!m) return null;
  return { y: +m[1], m: +m[2], d: +m[3] };
}

const init = parse(props.modelValue) || parse(ceiling.value) || { y: thisY, m: now.getMonth() + 1, d: now.getDate() };
const sel = ref({ ...init });

const days = computed(() => new Date(sel.value.y, sel.value.m, 0).getDate());

function isFuture(d) {
  return dateOf(d) > ceiling.value;
}

function dateOf(d) {
  const { y, m } = sel.value;
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

const yEl = ref(null);
const mEl = ref(null);
const dEl = ref(null);
const colOf = { y: yEl, m: mEl, d: dEl };

/* 把某一列滚到指定值居中的位置 */
function center(col, index, smooth) {
  const el = colOf[col].value;
  if (!el) return;
  el.scrollTo({ top: index * ITEM, behavior: smooth ? 'smooth' : 'auto' });
}

function syncAll(smooth) {
  center('y', sel.value.y - MIN_YEAR, smooth);
  center('m', sel.value.m - 1, smooth);
  center('d', sel.value.d - 1, smooth);
}

/* 滚动停下后取最靠中间的那一项 —— 滚轮手感的关键 */
let settle = 0;
function onScroll(col) {
  clearTimeout(settle);
  settle = setTimeout(() => {
    const el = colOf[col].value;
    if (!el) return;
    const i = Math.round(el.scrollTop / ITEM);
    if (col === 'y') {
      const y = MIN_YEAR + clamp(i, 0, years.value.length - 1);
      if (y !== sel.value.y) { sel.value = { ...sel.value, y }; clampDay(); }
    } else if (col === 'm') {
      const m = clamp(i + 1, 1, 12);
      if (m !== sel.value.m) { sel.value = { ...sel.value, m }; clampDay(); }
    } else {
      const d = clamp(i + 1, 1, days.value);
      if (d !== sel.value.d) sel.value = { ...sel.value, d };
    }
    commit();
  }, 120);
}

const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

/* 换年月后日子可能超出当月天数，退回月末 */
function clampDay() {
  const last = new Date(sel.value.y, sel.value.m, 0).getDate();
  if (sel.value.d > last) sel.value = { ...sel.value, d: last };
}

function pick(col, v) {
  if (col === 'y') sel.value = { ...sel.value, y: v };
  if (col === 'm') sel.value = { ...sel.value, m: v };
  if (col === 'd') sel.value = { ...sel.value, d: v };
  clampDay();
  syncAll(true);
  commit();
}

function commit() {
  const v = `${sel.value.y}-${String(sel.value.m).padStart(2, '0')}-${String(clamp(sel.value.d, 1, days.value)).padStart(2, '0')}`;
  if (v !== props.modelValue) emit('update:modelValue', v);
}

/* 外部改了值（比如预填、切换步骤）时把三列重新对齐 */
watch(() => props.modelValue, (v) => {
  const p = parse(v);
  if (!p) return;
  if (p.y === sel.value.y && p.m === sel.value.m && p.d === sel.value.d) return;
  sel.value = { ...p };
  nextTick(() => syncAll(false));
});

onMounted(() => nextTick(() => {
  syncAll(false);
  commit();
}));
</script>

<style scoped>
.wp{
  --it: 44px;
  position: relative;
  border-radius: 18px;
  background: #FBFBFC;
  border: 1px solid #ECECEF;
  padding: 6px 6px;
  overflow: hidden;
}

/* 中间那条选中带：唯一的高亮参考线 */
.wp-band{
  position: absolute;
  left: 10px; right: 10px;
  top: 50%;
  height: var(--it);
  transform: translateY(-50%);
  border-radius: 12px;
  background: #FFFFFF;
  box-shadow: 0 1px 0 rgba(0, 0, 0, .04), 0 8px 20px rgba(17, 17, 19, .06);
  pointer-events: none;
}

.wp-cols{
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1.1fr .95fr .9fr;
  height: calc(var(--it) * 3);
  border-radius: 12px;
}

.wp-col{
  height: 100%;
  overflow-y: auto;
  scroll-snap-type: y mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  position: relative;
  mask-image: linear-gradient(180deg, transparent 0, #000 16%, #000 84%, transparent 100%);
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 16%, #000 84%, transparent 100%);
}
.wp-col::-webkit-scrollbar{ width: 0; height: 0; }

/* 上下留白，让首项和末项也能滚到正中 */
.wp-pad{ display: block; height: var(--it); }

.wp-it{
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: var(--it);
  scroll-snap-align: center;
  border: 0;
  background: transparent;
  font: inherit;
  font-size: 17px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.01em;
  color: #C2C2C8;
  cursor: pointer;
  transition: color .18s ease, transform .2s ease, font-weight .2s ease;
}
.wp-it--m, .wp-col--m .wp-it{ font-size: 16px; }

.wp-it.on{ color: #111114; font-weight: 700; transform: scale(1.03); }
.wp-it.off{ color: #E4E4E8; }

.wp-col--m .wp-it{ font-size: 16.5px; }

@media (prefers-reduced-motion: reduce){
  .wp-it{ transition: color .01s; }
}
</style>
