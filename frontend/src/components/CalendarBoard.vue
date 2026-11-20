<template>
  <div class="ivc">
    <div class="ivc-card">
      <header class="ivc-head">
        <button type="button" class="ivc-nav" :aria-label="view === 'day' ? '上个月' : '前 5 年'" @click="step(-1)">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14.5 6.5 9 12l5.5 5.5" /></svg>
        </button>
        <!-- 点标题进「选年月」面板，再点回到日期 -->
        <button type="button" class="ivc-title" :class="{ on: view === 'pick' }" @click="toggleView">
          <template v-if="view === 'day'">{{ cursor.y }} 年 {{ cursor.m }} 月</template>
          <template v-else>{{ pickYear }} 年</template>
        </button>
        <button type="button" class="ivc-nav" :aria-label="view === 'day' ? '下个月' : '后 5 年'" @click="step(1)">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 6.5 15 12l-5.5 5.5" /></svg>
        </button>
      </header>

      <!-- 日期视图在文档流里撑住高度，年月面板绝对叠在上面，两者天然等高 -->
      <div class="ivc-stage">
        <div class="ivc-view" :class="{ show: view === 'day' }">
          <div class="ivc-weeks" aria-hidden="true">
            <span v-for="w in WEEKS" :key="w">{{ w }}</span>
          </div>

          <div ref="gridWrap" class="ivc-gridwrap">
            <div class="ivc-grid">
              <button
                v-for="(c, i) in cells"
                :key="i"
                type="button"
                class="ivc-cell"
                :class="{ dim: !c.inMonth, sel: c.key === modelValue, today: c.isToday, off: isOff(c.key) }"
                :disabled="isOff(c.key)"
                @click="pick(c)"
              >{{ c.d }}</button>
            </div>
          </div>
        </div>

        <div class="ivc-view ivc-view--pick" :class="{ show: view === 'pick' }">
          <div class="ivc-years">
            <button
              v-for="y in yearRow"
              :key="y"
              type="button"
              :class="{ on: y === pickYear }"
              :disabled="isYearOff(y)"
              @click="pickYear = y"
            >{{ y }}</button>
          </div>
          <div class="ivc-months">
            <button
              v-for="m in 12"
              :key="m"
              type="button"
              :class="{ on: pickYear === cursor.y && m === cursor.m }"
              :disabled="isMonthOff(pickYear, m)"
              @click="setMonth(m)"
            >{{ m }} 月</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  /* 可选日期的上界（含），传了就把之后的日期禁掉；纪念日只能选今天及以前 */
  max: { type: String, default: '' },
});
const emit = defineEmits(['update:modelValue']);

const WEEKS = ['日', '一', '二', '三', '四', '五', '六'];

const pad = (n) => String(n).padStart(2, '0');
const toIso = (y, m, d) => `${y}-${pad(m)}-${pad(d)}`;
const readIso = (s) => {
  const [y, m, d] = String(s || '').split('-').map(Number);
  return y && m ? [y, m, d || 1] : [0, 0, 0];
};

const now = new Date();
const todayIso = toIso(now.getFullYear(), now.getMonth() + 1, now.getDate());

const cursor = ref((() => {
  const [y, m] = readIso(props.modelValue);
  return y ? { y, m } : { y: now.getFullYear(), m: now.getMonth() + 1 };
})());

watch(() => props.modelValue, (v) => {
  const [y, m] = readIso(v);
  if (y && (y !== cursor.value.y || m !== cursor.value.m)) cursor.value = { y, m };
});

const cells = computed(() => {
  const { y, m } = cursor.value;
  const lead = new Date(y, m - 1, 1).getDay();          // 周日开头
  const size = new Date(y, m, 0).getDate();
  /* 固定排满 6 行：不管这个月是 5 行还是 6 行，卡片高度都一样，
     切月份 / 切面板时不会有任何重排 */
  const total = 42;
  const list = [];
  for (let i = 0; i < total; i++) {
    const d = new Date(y, m - 1, 1 - lead + i);
    const iso = toIso(d.getFullYear(), d.getMonth() + 1, d.getDate());
    list.push({
      key: iso,
      d: d.getDate(),
      inMonth: d.getFullYear() === y && d.getMonth() + 1 === m,
      isToday: iso === todayIso,
      ym: { y: d.getFullYear(), m: d.getMonth() + 1 },
    });
  }
  return list;
});

/* ---------- 视图 ---------- */
const view = ref('day');
const pickYear = ref(cursor.value.y);
const gridWrap = ref(null);

const yearRow = computed(() => {
  const base = pickYear.value;
  return [-2, -1, 0, 1, 2].map((d) => base + d);
});

const reduced = typeof window !== 'undefined'
  && window.matchMedia
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* 翻月：只让网格在合成层上滑一下，不重建节点、不触发 layout */
function slideGrid(dir) {
  const w = gridWrap.value;
  if (!w || reduced || typeof w.animate !== 'function') return;
  w.animate(
    [
      { opacity: .4, transform: `translateX(${dir > 0 ? 18 : -18}px)` },
      { opacity: 1, transform: 'none' },
    ],
    { duration: 300, easing: 'cubic-bezier(.32,.72,0,1)' },
  );
}

function toggleView() {
  if (view.value === 'day') {
    pickYear.value = cursor.value.y;
    view.value = 'pick';
  } else {
    view.value = 'day';
  }
}

function shift(n) {
  const d = new Date(cursor.value.y, cursor.value.m - 1 + n, 1);
  cursor.value = { y: d.getFullYear(), m: d.getMonth() + 1 };
  slideGrid(n);
}

/* 日期视图里步进一个月，选年月面板里步进 5 年 */
function step(n) {
  if (view.value === 'day') {
    shift(n);
  } else {
    pickYear.value += n * 5;
  }
}

function setMonth(m) {
  if (isMonthOff(pickYear.value, m)) return;
  cursor.value = { y: pickYear.value, m };
  view.value = 'day';
}

function isOff(iso) {
  return !!props.max && iso > props.max;
}

/* 整年 / 整月都落在可选上界之后就没得选，压淡禁掉 */
function isYearOff(y) {
  return !!props.max && toIso(y, 1, 1) > props.max;
}
function isMonthOff(y, m) {
  return !!props.max && toIso(y, m, 1) > props.max;
}

function pick(c) {
  if (isOff(c.key)) return;
  cursor.value = c.ym;
  emit('update:modelValue', c.key);
}
</script>

<style scoped>
/* 骨架照「互动日历」稿：大月份标题 + 两侧细箭头 + 宽字距表头 + 方角实心选中，
   颜色换回纪念日页自己的深蓝灰 / 珊瑚 / 淡蓝白，不再用参考稿的紫罗兰 */
.ivc { position: relative; }

.ivc-card {
  position: relative;
  padding: 14px 12px 10px;
  border-radius: 20px;
  background: #FFFFFF;
  border: 1px solid #E8EBF5;
  box-shadow: 0 3px 12px rgba(58, 65, 82, .05);
}

.ivc-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; padding: 0 2px 9px;
}

.ivc-title {
  flex: 1 1 auto;
  padding: 3px 10px; border: 0; border-radius: 9px;
  background: transparent;
  font-family: 'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui;
  font-size: 20px; font-weight: 700; letter-spacing: -.02em;
  color: #3A4152;
  cursor: pointer;
  transition: background .16s ease, color .16s ease, transform .16s cubic-bezier(.32,.72,0,1);
}
.ivc-title:hover { background: #F2F4FA; }
.ivc-title:active { transform: scale(.96); }
.ivc-title.on { color: #6B7488; }
.ivc-title.on:hover { color: #3A4152; }

.ivc-nav {
  flex: 0 0 auto;
  width: 28px; height: 28px; padding: 0;
  display: grid; place-items: center;
  border: 0; border-radius: 8px;
  background: transparent; color: #6B7488;
  cursor: pointer;
  transition: background .16s ease, color .16s ease, transform .16s cubic-bezier(.32,.72,0,1);
}
.ivc-nav svg { width: 19px; height: 19px; stroke: currentColor; stroke-width: 2; fill: none; stroke-linecap: round; }
.ivc-nav:hover { background: #F2F4FA; color: #3A4152; }
.ivc-nav:active { transform: scale(.92); }

/* ---------- 舞台：日期视图在流内撑高，面板叠加，两者始终等高 ---------- */
.ivc-stage {
  position: relative;
  overflow: hidden;
}

/* 日期视图留在文档流里，即使隐藏也占位——所以切面板时卡片高度纹丝不动 */
.ivc-view {
  position: relative;
  opacity: 0;
  transform: translateY(8px) scale(.99);
  transform-origin: top center;
  pointer-events: none;
  /* 只动 opacity 和 transform：全程留在合成层，不触碰布局 */
  transition:
    opacity .26s ease,
    transform .34s cubic-bezier(.32, .72, 0, 1);
}
.ivc-view.show {
  opacity: 1;
  transform: none;
  pointer-events: auto;
}

.ivc-view--pick {
  position: absolute; inset: 0;
  z-index: 2;
  box-sizing: border-box;
}

.ivc-weeks {
  display: grid; grid-template-columns: repeat(7, 1fr);
  padding: 0 0 5px;
  border-bottom: 1px solid #F1F3F9;
}
.ivc-weeks span {
  text-align: center;
  font-family: 'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui;
  font-size: 10.5px; font-weight: 600;
  letter-spacing: .16em; text-indent: .16em;
  color: #A3AABC;
}

.ivc-gridwrap { will-change: transform, opacity; }

.ivc-grid {
  display: grid; grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  padding-top: 5px;
}

.ivc-cell {
  position: relative;
  height: 35px; padding: 0;
  display: grid; place-items: center;
  border: 0; border-radius: 8px;
  background: transparent;
  font-family: 'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui;
  font-size: 13.5px; font-weight: 500;
  color: #3A4152;
  cursor: pointer;
  transition: background .16s ease, color .16s ease, transform .16s cubic-bezier(.32,.72,0,1);
}
.ivc-cell.dim { color: #C7CCD8; font-size: 12.5px; }
.ivc-cell:hover { background: #F2F4FA; }
.ivc-cell:active { transform: scale(.92); }

/* 今天：珊瑚数字 + 一点珊瑚，选中后反白 */
.ivc-cell.today { color: #EF7C77; font-weight: 600; }
.ivc-cell.today:not(.sel)::after {
  content: '';
  position: absolute; bottom: 4px; left: 50%; transform: translateX(-50%);
  width: 3px; height: 3px; border-radius: 50%;
  background: #FA9490;
}

.ivc-cell.sel {
  background: #404756; color: #FFFFFF; font-weight: 600;
  box-shadow: 0 2px 6px rgba(64, 71, 86, .18);
  animation: cellPop .3s cubic-bezier(.2, .9, .3, 1.3) both;
}
.ivc-cell.sel.today::after { display: none; }

@keyframes cellPop {
  0%   { transform: scale(.84); }
  55%  { transform: scale(1.06); }
  100% { transform: scale(1); }
}

/* 超出可选范围的日期：压到极淡，点不动 */
.ivc-cell.off {
  color: #DCE0E9;
  cursor: not-allowed;
  background: transparent;
}
.ivc-cell.off:hover { background: transparent; }

/* ---------- 选年月面板：撑满和日期视图同样的高度，切换时卡片不缩不涨 ---------- */
.ivc-view--pick {
  height: 100%;
  display: flex; flex-direction: column;
  justify-content: center;
  padding: 4px 2px 2px;
  box-sizing: border-box;
}
.ivc-years { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; flex: 0 0 auto; }
.ivc-years button {
  height: 33px; padding: 0;
  border: 0; border-radius: 9px;
  background: #F5F6FA; color: #8A91A3;
  font-family: 'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui;
  font-size: 12.5px; font-weight: 600;
  cursor: pointer;
  transition: background .18s ease, color .18s ease, transform .18s cubic-bezier(.32,.72,0,1);
}
.ivc-years button:hover:not(:disabled) { background: #E9ECF5; color: #3A4152; }
.ivc-years button.on { background: #404756; color: #FFFFFF; }
.ivc-years button:disabled { color: #DCE0E9; cursor: not-allowed; }

.ivc-months {
  flex: 0 0 auto;
  display: grid; grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: 44px;
  gap: 8px; margin-top: 10px;
  min-height: 0;
}
.ivc-months button {
  padding: 0;
  border: 0; border-radius: 12px;
  background: #F5F6FA; color: #3A4152;
  font-family: 'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui;
  font-size: 13.5px; font-weight: 600;
  cursor: pointer;
  transition: background .18s ease, color .18s ease, transform .18s cubic-bezier(.32,.72,0,1);
}
.ivc-months button:hover:not(:disabled) { background: #E9ECF5; }
.ivc-months button:active:not(:disabled) { transform: scale(.94); }
.ivc-months button.on {
  background: #404756; color: #FFFFFF;
  box-shadow: 0 2px 6px rgba(64, 71, 86, .18);
}
.ivc-months button:disabled { color: #DCE0E9; cursor: not-allowed; }

@media (prefers-reduced-motion: reduce) {
  .ivc-view, .ivc-cell, .ivc-years button, .ivc-months button, .ivc-title, .ivc-nav {
    transition: none !important;
    animation: none !important;
  }
}
</style>
