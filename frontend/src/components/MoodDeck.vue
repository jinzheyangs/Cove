<template>
  <div class="mdeck">
    <div class="mdeck__hd">
      <span class="mdeck__t">今日心情</span>
      <span class="mdeck__s">左右滑动看我和 TA</span>
    </div>

    <div class="mdeck__stack" @click.capture="onClickCapture">
      <span class="mdeck__tag mdeck__tag--l" :style="{ opacity: leftOp }">{{ nextPeek }}</span>
      <span class="mdeck__tag mdeck__tag--r" :style="{ opacity: rightOp }">{{ nextPeek }}</span>

      <article
        v-for="c in cards"
        :key="c.key"
        class="mcard"
        :class="[`mcard--${c.key}`, { 'is-top': isTop(c.key), 'is-snap': snap === c.key }]"
        :style="[styleOf(c.key), moodSkin(c)]"
        :aria-hidden="isTop(c.key) ? null : 'true'"
        @pointerdown="onDown"
        @click="onTap(c.key)"
      >
        <div class="mcard__flow"></div>

        <div class="mcard__in">
          <div class="mwho">
            <span class="mav" :class="`mav--${c.key}`">{{ c.initial }}</span>
            <span class="mwho__b">
              <span class="mwho__n">{{ c.name }}</span>
              <span class="mwho__s">今天的心情</span>
            </span>
            <span class="mflag">{{ c.flag }}</span>
          </div>

          <div class="mmid">
            <svg class="mic" viewBox="0 0 40 40" fill="none" aria-hidden="true">
              <circle cx="20" cy="20" r="16.4" fill="rgba(255,255,255,.30)" stroke="currentColor" stroke-width="2.6" />
              <!-- 只写了字、没标情绪 -->
              <template v-if="c.recorded && !c.mood">
                <path d="M13 15h14M13 20h14M13 25h9" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
              </template>
              <template v-else-if="c.mood === 'happy'">
                <path d="M13 15.5c1-1.2 2.4-1.8 4-1.8s3 .6 4 1.8" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
                <path d="M12 22.5c1.8 3 4.6 4.5 8 4.5s6.2-1.5 8-4.5" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
              </template>
              <template v-else-if="c.mood === 'awesome'">
                <path d="M12.5 15c1.2-1.4 2.8-2 4.5-2s3.3.6 4.5 2" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
                <path d="M11 21c2 4 5.2 5.8 9 5.8s7-1.8 9-5.8" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
              </template>
              <template v-else-if="c.mood === 'calm'">
                <circle cx="15" cy="16" r="1.5" fill="currentColor" />
                <circle cx="25" cy="16" r="1.5" fill="currentColor" />
                <path d="M16 24h8" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
              </template>
              <template v-else-if="c.mood === 'tired'">
                <path d="M13.5 16.5l3 1.2M26.5 16.5l-3 1.2" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
                <path d="M16 25h8" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
              </template>
              <template v-else>
                <path d="M16 26c1.2-1.4 2.6-2 4-2s2.8.6 4 2" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" />
              </template>
            </svg>

            <div class="mtxt">
              <span class="mname">{{ c.moodName }}</span>
              <p class="mnote">{{ c.note }}</p>
              <button
                v-if="c.key === 'me'"
                class="mact" type="button"
                @click.stop="openSheet"
              >{{ c.recorded ? '改一下' : '记一下' }}</button>
            </div>
          </div>
        </div>
      </article>
    </div>

    <!-- 记录今天的心情：点卡片或「记一下」都从这里进来 -->
    <Teleport to="body">
      <Transition name="md">
        <div v-if="sheetOpen" class="md-wrap">
          <div class="md-mask" @click="closeSheet"></div>
          <section class="md-card">
            <span class="md-grab" aria-hidden="true"></span>
            <h3 class="md-t">{{ recorded ? '今天的心情' : '今天感觉怎么样' }}</h3>
            <p class="md-sub">选个心情，或者只写一句也行 —— 记下来 TA 都能看到，一天一条，随时能改</p>

            <div class="md-opts">
              <button
                v-for="o in OPTIONS"
                :key="o.key"
                type="button"
                class="md-opt"
                :class="{ on: picked === o.key }"
                :style="{ '--oc': o.color }"
                @click="picked = picked === o.key ? '' : o.key"
              >
                <span class="md-emo">{{ o.emoji }}</span>
                <b>{{ o.name }}</b>
              </button>
            </div>

            <input
              v-model="noteDraft"
              class="md-note"
              type="text"
              maxlength="80"
              placeholder="想写一句就写，可以不写"
            />

            <p v-if="sheetErr" class="md-err">{{ sheetErr }}</p>

            <div class="md-acts">
              <button
                class="md-save" type="button"
                :disabled="(!picked && !noteDraft.trim()) || saving"
                @click="saveMood"
              >{{ saving ? '记下来…' : (recorded ? '改一下' : '记下来') }}</button>
              <button class="md-cancel" type="button" @click="closeSheet">取消</button>
            </div>
          </section>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { get, post } from '../api/client.js';

/* 数据来自 GET /mood：{ day, mine, partner }，两边都可能为 null */
const MOOD_NAME = { awesome: '超棒', happy: '开心', calm: '平静', tired: '累了', low: '低落' };

/* 五档心情：文案、表情、以及记下之后整张卡换的配色。
   level 后端要求 1–5，这里按「越高越亮」映射。 */
const OPTIONS = [
  { key: 'awesome', name: '超棒', emoji: '🤩', color: '#FF4D8D', level: 5, g0: '#FFE0EC', g1: '#FF4D8D', g2: '#FFB6CE' },
  { key: 'happy', name: '开心', emoji: '😊', color: '#FF8A5B', level: 4, g0: '#FFE6D9', g1: '#FF8A5B', g2: '#FFC8B0' },
  { key: 'calm', name: '平静', emoji: '😌', color: '#4FB8AA', level: 3, g0: '#DFF3EF', g1: '#4FB8AA', g2: '#B6E3DA' },
  { key: 'tired', name: '累了', emoji: '😮‍💨', color: '#8E86B8', level: 2, g0: '#EDEBF5', g1: '#8E86B8', g2: '#CFC9E5' },
  { key: 'low', name: '低落', emoji: '😔', color: '#7583A2', level: 1, g0: '#E6EAF3', g1: '#7583A2', g2: '#C2CBDD' },
];
const SKIN = Object.fromEntries(OPTIONS.map((o) => [o.key, o]));

function buildCards(pair) {
  const mine = pair?.mine || null;
  const theirs = pair?.partner || null;
  const mineNote = mine ? (mine.note || '今天没写备注') : '今天还没记录自己的心情';
  const theirNote = theirs ? (theirs.note || '今天没写备注') : 'TA 今天还没记录';
  const nameOf = (rec) => {
    if (!rec) return '还没记录';
    return rec.mood ? (MOOD_NAME[rec.mood] || '有心情') : '写下了一句';
  };
  return [
    {
      key: 'me', name: '这是我', initial: '我', flag: '我',
      mood: mine?.mood || 'none',
      moodName: nameOf(mine),
      note: mineNote,
      recorded: !!mine,
    },
    {
      key: 'ta', name: '我的 TA', initial: 'TA', flag: '对方',
      mood: theirs?.mood || 'none',
      moodName: nameOf(theirs),
      note: theirNote,
      recorded: !!theirs,
    },
  ];
}

/* 记了心情的卡按心情换色；只写了字的用安静的暖米色；没记的保持默认粉 */
function moodSkin(c) {
  const s = SKIN[c.mood];
  if (s) return { '--g0': s.g0, '--g1': s.g1, '--g2': s.g2 };
  if (c.recorded) return { '--g0': '#FBF1E8', '--g1': '#DBBB9F', '--g2': '#F4DECD' };
  return null;
}

const cards = ref(buildCards(null));

async function pull() {
  try {
    cards.value = buildCards(await get('/mood'));
  } catch (_) {
    cards.value = buildCards(null);
  }
}

const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

/* ===== 记录今天的心情 ===== */
const sheetOpen = ref(false);
const picked = ref('');
const noteDraft = ref('');
const saving = ref(false);
const sheetErr = ref('');
const recorded = computed(() => !!cards.value.find((c) => c.key === 'me')?.recorded);

function openSheet() {
  const me = cards.value.find((c) => c.key === 'me');
  /* 只写过字的那种记录没有 mood，进来就是「只写字」的状态 */
  picked.value = me?.recorded && SKIN[me.mood] ? me.mood : '';
  noteDraft.value = me?.recorded && me.note !== '今天没写备注' ? me.note : '';
  sheetErr.value = '';
  sheetOpen.value = true;
}

function closeSheet() {
  sheetOpen.value = false;
  sheetErr.value = '';
}

/* 点卡片本身也能记：只有「我」这一张、且必须是当前最上面那张 */
function onTap(key) {
  if (!isTop(key) || key !== 'me') return;
  openSheet();
}

async function saveMood() {
  if (saving.value) return;
  const text = noteDraft.value.trim();
  /* 心情和文字都没有就不提交；只有文字也能记（后端 mood 可以为空） */
  if (!picked.value && !text) {
    sheetErr.value = '选个心情，或者写一句话';
    return;
  }
  saving.value = true;
  sheetErr.value = '';
  try {
    const opt = picked.value ? SKIN[picked.value] : null;
    const pair = await post('/mood', {
      mood: picked.value || null,
      level: opt ? opt.level : 3,
      note: text || null,
    });
    cards.value = buildCards(pair);
    /* 记完之后让「我」这张回到最上面，马上看到新颜色 */
    order.value = [0, 1];
    dx.value = 0;
    progress.value = 0;
    sheetOpen.value = false;
  } catch (e) {
    sheetErr.value = e?.message || '没记上，稍后再试';
  } finally {
    saving.value = false;
  }
}

const order = ref([0, 1]);
const dx = ref(0);
const progress = ref(0);
const dragging = ref(false);
const flying = ref(null);
const flyDir = ref(1);
const snap = ref(null);
const busy = ref(false);

const topKey = computed(() => cards.value[order.value[0]].key);
const isTop = (key) => topKey.value === key;
const nextPeek = computed(() => (topKey.value === 'me' ? '看 TA 的' : '看我的'));

const leftOp = computed(() => clamp(-dx.value / 140, 0, 1));
const rightOp = computed(() => clamp(dx.value / 140, 0, 1));

function styleOf(key) {
  const top = isTop(key);
  const st = {};

  if (flying.value === key) {
    st.transform = `translate3d(${flyDir.value * 620}px,0,0) rotate(${flyDir.value * 26}deg)`;
    st.opacity = 0;
    st.zIndex = 2;
    st.transition = 'transform .4s cubic-bezier(.22,1,.36,1), opacity .34s linear';
    return st;
  }

  if (top) {
    const d = dx.value;
    st.transform = `translate3d(${d}px,0,0) rotate(${clamp(d / 13, -20, 20)}deg)`;
    st['--ang'] = `${118 + clamp(d / 260, -1, 1) * 34}deg`;
    st.zIndex = 2;
    if (!dragging.value) st.transition = 'transform .48s var(--spring), opacity .2s linear';
    return st;
  }

  const p = progress.value;
  st.transform = `translate3d(0,${16 - p * 11}px,0) scale(${0.93 + p * 0.04}) rotate(5deg)`;
  st.zIndex = 1;
  if (!dragging.value) st.transition = 'transform .48s var(--spring)';
  return st;
}

let sx = 0, sy = 0, axis = null, active = false, moved = false;

function onDown(e) {
  if (busy.value) return;
  if (e.pointerType === 'mouse' && e.button !== 0) return;
  active = true; moved = false; axis = null;
  sx = e.clientX; sy = e.clientY;
  window.addEventListener('pointermove', onMove, { passive: true });
  window.addEventListener('pointerup', onUp);
  window.addEventListener('pointercancel', onUp);
}

function detach() {
  window.removeEventListener('pointermove', onMove);
  window.removeEventListener('pointerup', onUp);
  window.removeEventListener('pointercancel', onUp);
}

function onMove(e) {
  if (!active) return;
  const ddx = e.clientX - sx;
  const ddy = e.clientY - sy;

  if (!axis) {
    if (Math.abs(ddx) < 6 && Math.abs(ddy) < 6) return;
    axis = Math.abs(ddx) > Math.abs(ddy) ? 'x' : 'y';
    if (axis === 'y') { detach(); active = false; return; }
    dragging.value = true;
  }

  moved = true;
  const a = Math.abs(ddx);
  const soft = a > 260 ? 260 + (a - 260) * 0.34 : a;
  dx.value = ddx < 0 ? -soft : soft;
  progress.value = Math.min(soft / 260, 1);
}

function onUp() {
  detach();
  if (!active) return;
  active = false;

  if (!moved) { dragging.value = false; return; }

  const d = dx.value;
  dragging.value = false;
  if (Math.abs(d) > 110) { fly(d > 0 ? 1 : -1); return; }
  dx.value = 0;
  progress.value = 0;
}

function onClickCapture(e) {
  if (!moved) return;
  e.stopPropagation();
  e.preventDefault();
  moved = false;
}

let timer = 0;
function fly(dir) {
  if (busy.value) return;
  busy.value = true;
  const key = topKey.value;
  flyDir.value = dir;
  flying.value = key;

  clearTimeout(timer);
  timer = setTimeout(() => {
    order.value = [order.value[1], order.value[0]];
    dx.value = 0;
    progress.value = 0;
    dragging.value = false;
    flying.value = null;
    snap.value = key;
    requestAnimationFrame(() => requestAnimationFrame(() => { snap.value = null; }));
    busy.value = false;
  }, 400);
}

onMounted(() => {
  pull();
  window.addEventListener('cove:auth', pull);
  /* 首页被切回来 / 每 20 秒静默刷新时，把对方那张卡也拉一遍 */
  window.addEventListener('cove:home', pull);
});

onBeforeUnmount(() => {
  detach();
  clearTimeout(timer);
  window.removeEventListener('cove:auth', pull);
  window.removeEventListener('cove:home', pull);
});
</script>

<style scoped>
.mdeck { margin-top: 14px; }
.mdeck__hd { display: flex; align-items: baseline; gap: 8px; padding: 0 2px 10px; }
.mdeck__t { font-size: 14px; font-weight: 700; letter-spacing: -.01em; color: var(--ink); }
.mdeck__s { margin-left: auto; font-size: 10.5px; color: var(--ink-3); }

.mdeck__stack { position: relative; height: 168px; touch-action: pan-y; user-select: none; -webkit-user-select: none; }

.mcard {
  position: absolute; left: 0; top: 0; width: 100%; height: 168px;
  border-radius: 26px; overflow: hidden;
  background: linear-gradient(var(--ang, 118deg), var(--g0) 0%, var(--g1) 52%, var(--g2) 100%);
  box-shadow:
    0 2px 8px -2px rgba(255, 88, 128, .26),
    0 18px 36px -16px rgba(196, 26, 74, .42),
    inset 0 1px 0 rgba(255, 255, 255, .70);
  transform-origin: 50% 50%;
  will-change: transform;
  color: #3a1526;
  -webkit-tap-highlight-color: transparent;
}
.mcard--me { --g0: #ffd9e8; --g1: #ff7fa9; --g2: #ffc2d8; }
.mcard--ta { --g0: #ffe1d2; --g1: #ff9a87; --g2: #ffc5b2; }
.mcard.is-snap { transition: none !important; }

.mcard__flow {
  position: absolute; inset: -40%; pointer-events: none;
  background:
    radial-gradient(40% 32% at 18% 16%, rgba(255, 255, 255, .62), rgba(255, 255, 255, 0) 70%),
    radial-gradient(46% 40% at 86% 84%, rgba(255, 255, 255, .38), rgba(255, 255, 255, 0) 72%);
  animation: mflow 9s ease-in-out infinite;
}
@keyframes mflow {
  0%, 100% { transform: translate(-3%, -2%) rotate(0deg); }
  50% { transform: translate(4%, 3%) rotate(6deg); }
}

.mdeck__tag {
  position: absolute; top: 13px; z-index: 3; opacity: 0;
  padding: 5px 10px; border-radius: 10px;
  font-size: 11px; font-weight: 800; border: 2px solid currentColor;
  pointer-events: none;
}
.mdeck__tag--l { left: 0; color: #c71f53; background: rgba(255, 255, 255, .55); transform: rotate(-9deg); }
.mdeck__tag--r { right: 0; color: #fff; border-color: transparent; background: rgba(199, 31, 83, .9); transform: rotate(9deg); }

.mcard__in { position: relative; z-index: 2; height: 100%; display: flex; flex-direction: column; padding: 15px 17px; }

.mwho { display: flex; align-items: center; gap: 9px; }
.mav {
  width: 30px; height: 30px; border-radius: 50%; flex: none;
  display: grid; place-items: center;
  font-size: 11.5px; font-weight: 800; color: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .55), 0 5px 12px -5px rgba(190, 25, 72, .55);
}
.mav--me { background: linear-gradient(180deg, #ff6f9e, #f02a66); }
.mav--ta { background: linear-gradient(180deg, #ff9a86, #f0765a); }
.mwho__b { display: flex; flex-direction: column; min-width: 0; }
.mwho__n { font-size: 13.5px; font-weight: 750; letter-spacing: -.012em; }
.mwho__s { font-size: 10.5px; font-weight: 600; color: rgba(58, 21, 38, .52); margin-top: 1px; }
.mflag {
  margin-left: auto; flex: none; padding: 4px 8px; border-radius: 999px;
  font-size: 10px; font-weight: 800; color: #c71f53;
  background: rgba(255, 255, 255, .62);
  box-shadow: inset 0 0 0 .5px rgba(255, 255, 255, .85);
}

.mmid { flex: 1; display: flex; align-items: center; gap: 11px; min-height: 0; }
.mic { width: 52px; height: 52px; flex: none; color: #fff; filter: drop-shadow(0 6px 12px rgba(190, 25, 72, .32)); }
.mtxt { min-width: 0; }
.mname { display: block; font-size: 18px; font-weight: 800; letter-spacing: -.015em; color: #33121f; }
.mnote {
  margin: 3px 0 0; font-size: 12px; line-height: 1.5; color: rgba(58, 21, 38, .72);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
/* 卡片里的写入入口：不写的话这一整块永远是「还没记录」 */
.mact {
  margin-top: 7px; height: 24px; padding: 0 11px;
  border: 0; border-radius: 999px;
  background: rgba(255, 255, 255, .86); color: #B8124B;
  font: inherit; font-size: 11px; font-weight: 800;
  box-shadow: 0 5px 12px -8px rgba(190, 25, 72, .8), inset 0 1px 0 rgba(255, 255, 255, .95);
  transition: transform .16s cubic-bezier(.22, 1, .36, 1), background .16s;
}
.mact:active { transform: scale(.94); background: #fff; }

/* ===== 记录心情的弹窗（黑白底 + 心情本身的颜色） ===== */
.md-wrap { position: fixed; inset: 0; z-index: 88; display: flex; align-items: flex-end; justify-content: center; }
.md-mask {
  position: absolute; inset: 0;
  background: rgba(18, 16, 20, .34);
  backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px);
}
.md-card {
  position: relative; width: 100%; max-width: 400px;
  padding: 10px 16px calc(14px + env(safe-area-inset-bottom, 0px));
  border-radius: 24px 24px 0 0;
  background: #fff;
  box-shadow: 0 -18px 44px -26px rgba(17, 17, 19, .38);
}
@media (min-width: 520px) {
  .md-wrap { padding-bottom: 30px; }
  .md-card { border-radius: 24px; max-width: 372px; }
}
.md-grab { display: block; width: 38px; height: 4px; margin: 0 auto 8px; border-radius: 999px; background: #E4E4E9; }
.md-t { margin: 0; font-size: 16.5px; font-weight: 800; letter-spacing: -.02em; color: #111114; }
.md-sub { margin: 4px 0 0; font-size: 11.5px; line-height: 1.5; color: #7A7A84; }

.md-opts { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; margin-top: 11px; }
.md-opt {
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 9px 0 8px;
  border: 0; border-radius: 14px;
  background: #F5F5F7; color: #52525B;
  font: inherit; font-size: 11px; font-weight: 700;
  transition: transform .2s cubic-bezier(.22, 1, .36, 1), background .2s, box-shadow .2s, color .2s;
}
.md-opt .md-emo { font-size: 19px; line-height: 1; }
.md-opt.on {
  background: #fff; color: var(--oc);
  box-shadow: inset 0 0 0 1.5px var(--oc), 0 10px 20px -16px var(--oc);
  transform: translateY(-2px);
}
.md-opt:active { transform: scale(.95); }

.md-note {
  display: block; width: 100%; height: 40px; margin-top: 10px; padding: 0 12px;
  border: 0; border-radius: 12px; background: #F5F5F7;
  font: inherit; font-size: 12.5px; color: #111114;
  outline: 0;
}
.md-note::placeholder { color: #B6B6BE; }
.md-err { margin: 8px 0 0; font-size: 11.5px; color: #D9235A; }

.md-acts { display: flex; align-items: center; gap: 9px; margin-top: 12px; }
.md-save {
  flex: 1; height: 46px; border: 0; border-radius: 14px;
  background: #111114; color: #fff;
  font: inherit; font-size: 14px; font-weight: 700;
  transition: transform .16s cubic-bezier(.22, 1, .36, 1), background .16s;
}
.md-save:disabled { background: #EFEFF3; color: #B6B6BE; }
.md-save:active:not(:disabled) { transform: scale(.985); }
.md-cancel {
  flex: none; height: 46px; padding: 0 15px;
  border: 0; border-radius: 14px;
  background: #F5F5F7; color: #52525B;
  font: inherit; font-size: 13.5px; font-weight: 600;
}
.md-cancel:active { transform: scale(.985); }

.md-enter-active { transition: opacity .24s ease; }
.md-leave-active { transition: opacity .18s ease; }
.md-enter-from, .md-leave-to { opacity: 0; }
.md-enter-active .md-card { transition: transform .32s cubic-bezier(.22, 1, .36, 1); }
.md-enter-from .md-card { transform: translateY(100%); }

@media (prefers-reduced-motion: reduce) {
  .mact, .md-opt, .md-save, .md-cancel { transition-duration: .01s !important; }
  .md-enter-active, .md-leave-active, .md-enter-active .md-card { transition-duration: .01s !important; }
}
</style>
