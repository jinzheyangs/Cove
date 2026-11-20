<template>
  <div class="dpage" :class="{ 'is-edit': editing }">
    <!-- 顶部：和列表页同一套 40px 圆角 13 白按钮 -->
    <div class="dv-bar">
      <button class="dv-ic" aria-label="返回" @click="emit('back')">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>
      </button>
      <span class="dv-bar-t">{{ entry?.monthLabel }} {{ +entry?.dayNum }} 日 · {{ entry?.weekCN }}</span>
      <span class="dv-bar-pad"></span>
    </div>

    <!-- 内容不满一屏时，划动只让纸面跟手弹一下，松手回弹；内容够长才真的滚 -->
    <div
      class="dv-scroll" ref="bodyEl" @scroll="onScroll"
      @touchstart.passive="onPullStart"
      @touchmove.passive="onPullMove"
      @touchend="onPullEnd"
      @touchcancel="onPullEnd"
    >
      <div class="dv-pull" ref="pullEl">
      <div class="dv-sheet">
        <!-- 一行署名接标题，不再单独占一块头像行 -->
        <div class="dv-tblock">
          <div class="dv-by">
            {{ entry?.info?.writer === 'ta' ? diaryNames.ta : diaryNames.me
            }}<template v-if="entry?.info?.wroteAt"> · {{ entry.info.wroteAt }}</template>
          </div>
          <h1 class="dv-title">{{ entry?.info?.title }}</h1>
          <div class="dv-sub" v-if="subBits.length">
            <span v-for="(b, i) in subBits" :key="b">
              <span v-if="i" class="dv-sep">·</span>{{ b }}
            </span>
          </div>
        </div>

        <!-- 照片跟在标题下，是这一页的内容，不是封面。一张都没有就整块不出现 -->
        <div class="dv-media" ref="heroEl" v-if="allPhotos > 0">
          <!-- 照片组上面只留一枚「摊开 / 叠合」，靠右，不压图；张数在照片里看得出来，不另写 -->
          <div class="dv-pbar" v-if="canFold">
            <button class="dv-pbtn" :class="{ on: open }" @click="open = !open">
              <span>{{ open ? '叠合' : '摊开' }}</span>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
            </button>
          </div>
          <div
            class="dv-pile" :class="{ open: isOpen, foldable: canFold, dragging: swiping }" ref="pileEl"
            :style="{ '--drag': drag + 'px' }"
            @pointerdown="onSwipeDown"
            @pointermove="onSwipeMove"
            @pointerup="onSwipeUp"
            @pointercancel="onSwipeUp"
            @click="onPileClick($event)"
          >
            <div class="dv-deck" v-if="canFold">
              <div class="dv-ply">
                <div class="dv-dl d2" :class="shots[cyc(2)] ? tint(cyc(2)) : 't5'">
                  <img v-if="shots[cyc(2)]" class="dv-dimg" :src="shots[cyc(2)]" alt="" />
                  <span class="dv-glass"></span>
                </div>
                <div class="dv-dl d1" :class="shots[cyc(1)] ? tint(cyc(1)) : 't2'">
                  <img v-if="shots[cyc(1)]" class="dv-dimg" :src="shots[cyc(1)]" alt="" />
                  <span class="dv-glass"></span>
                </div>
                <transition name="dvsw">
                  <div class="dv-dl d0" :key="cur" :class="tint(cyc(0))">
                    <img v-if="shots[cyc(0)]" class="dv-dimg" :src="shots[cyc(0)]" alt="" />
                    <svg v-else class="dv-ip" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="15" rx="2.5"/><circle cx="8.5" cy="10" r="1.5"/><path d="M4 17l5.2-5 4 4 3.2-3L20 17"/></svg>
                  </div>
                </transition>
              </div>
            </div>

            <div class="dv-wall" :class="'w' + Math.min(allPhotos, 3)">
              <div
                v-for="(n, i) in photoList" :key="n"
                class="dv-ph" :class="tint(i)"
                :style="phVars(i)"
                @click="openView(i, $event)"
              >
                <span class="dv-phglow"></span>
                <img
                  v-if="shots[i]"
                  class="dv-phimg"
                  :src="shots[i]"
                  alt=""
                />
                <svg v-else class="dv-ip2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="15" rx="2.5"/><circle cx="8.5" cy="10" r="1.5"/><path d="M4 17l5.2-5 4 4 3.2-3L20 17"/></svg>
              </div>
            </div>
          </div>
        </div>

        <!-- 心得：整块做成一张卡片，标题在卡上——一眼就知道下面这段文字是「心得」，不是别的 -->
        <div class="dv-card">
          <div class="dv-card-h">
            <svg class="dv-card-ic" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5V6.5A2.5 2.5 0 0 1 6.5 4H18v16H6.5A2.5 2.5 0 0 1 4 17.5Z"/><path d="M8 8h6M8 12h4"/></svg>
            <span class="dv-card-t">心得</span>
          </div>

          <div class="dv-notes">
          <!-- 我的一侧 -->
          <div class="dv-note mine" :class="{ editing }">
            <div class="dv-nhead">
              <b>{{ diaryNames.me }}</b>
              <em>{{ entry?.info?.noteAt }}</em>
              <button class="dv-mini" v-if="!editing && entry?.info?.note" @click="startEdit">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                改一下
              </button>
            </div>

            <div class="dv-nbody" v-if="entry?.info?.note && !editing">
              <p :class="{ open: expanded.mine }">{{ entry.info.note }}</p>
              <button v-if="more.mine" class="dv-more" @click="expanded.mine = !expanded.mine">
                {{ expanded.mine ? '收起' : '展开全文' }}
                <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" :style="expanded.mine ? 'transform:rotate(180deg)' : ''"><path d="M6 9l6 6 6-6"/></svg>
              </button>
            </div>
            <button class="dv-empty" v-else-if="!editing" @click="startEdit">
              <span class="dv-empty-ic">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
              </span>
              <span class="dv-empty-tx">
                <b>今天还没写</b>
                <i>点一下，留一句</i>
              </span>
              <span class="dv-empty-go">
                <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>
              </span>
            </button>

            <div class="dv-edit" v-if="editing">
              <textarea
                ref="taEl" class="dv-ta" v-model="draft" maxlength="600"
                placeholder="今天发生了什么，心里是怎么想的…"
              ></textarea>
              <div class="dv-ebar">
                <span class="dv-cnt">{{ draft.length }} / 600</span>
                <button class="dv-etxt" @click="cancel">取消</button>
                <button class="dv-esave" @click="save">保存</button>
              </div>
            </div>
          </div>

          <!-- TA 的一侧 -->
          <div class="dv-note ta" v-if="entry?.info?.tnote">
            <div class="dv-nhead">
              <b>{{ diaryNames.ta }}</b>
              <em>{{ entry?.info?.tnoteAt }}</em>
            </div>
            <div class="dv-nbody">
              <p :class="{ open: expanded.ta }">{{ entry.info.tnote }}</p>
              <button v-if="more.ta" class="dv-more" @click="expanded.ta = !expanded.ta">
                {{ expanded.ta ? '收起' : '展开全文' }}
                <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" :style="expanded.ta ? 'transform:rotate(180deg)' : ''"><path d="M6 9l6 6 6-6"/></svg>
              </button>
            </div>
          </div>

            <div class="dv-wait" v-else>
              <span class="dv-wwave"></span>
              <span>他还没填写</span>
              <em>等他补上</em>
            </div>
          </div>
        </div>

        <div class="dv-tail">
          <span class="dv-fin"></span>
        </div>
      </div>
      </div>
    </div>

    <!-- 滚起来才出现的顶部雾：内容从紫底里淡出去，不在标题栏后面留残影 -->
    <div class="dv-fog" ref="fogEl"></div>

    <!-- 点一张看大图：再点图片本身或背景就缩回去，左右箭头翻页 -->
    <Teleport to="body">
      <div v-if="view >= 0" class="dv-view">
        <div class="dv-view-bg" @click="closeView"></div>
        <div class="dv-view-ph" ref="viewEl" @click="closeView">
          <img v-if="shots[view]" :src="shots[view]" alt="" />
          <span v-else class="dv-view-tint" :class="tint(view)"></span>
        </div>
        <div class="dv-view-top">
          <span>{{ view + 1 }} / {{ allPhotos }}</span>
          <button class="dv-view-x" @click="closeView" aria-label="关闭">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </div>
        <button v-if="allPhotos > 1" class="dv-view-step prev" @click.stop="stepView(-1)" aria-label="上一张">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M14 6 8 12l6 6"/></svg>
        </button>
        <button v-if="allPhotos > 1" class="dv-view-step next" @click.stop="stepView(1)" aria-label="下一张">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m10 6 6 6-6 6"/></svg>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted, reactive } from 'vue';
import { diaryNames } from '../../composables/useDiary.js';

const props = defineProps({
  entry: { type: Object, default: null },
  phClass: { type: String, default: 'ph1' },
});
const emit = defineEmits(['back', 'edit']);

const bodyEl = ref(null);
const pullEl = ref(null);
const heroEl = ref(null);
const fogEl = ref(null);
const taEl = ref(null);
const pileEl = ref(null);
const editing = ref(false);
const draft = ref('');
const open = ref(false);

/* 大图：点一张放大，再点一下缩回去。
   放大要「从那张小图原地长大」，不是凭空淡入一块大图 —— 所以记住被点那张的位置，
   进场时按终点框反算 scale/位移，再一帧内归零。 */
const view = ref(-1);
const viewEl = ref(null);
let flyFrom = null;
let lastPhEl = null;

function openView(i, e) {
  if (!(i >= 0 && i < allPhotos.value)) return;
  const el = e?.currentTarget;
  lastPhEl = el || null;
  if (el && el.getBoundingClientRect) {
    const r = el.getBoundingClientRect();
    /* 叠合态那张是 d0，尺寸跟小图一致，直接用它的框 */
    flyFrom = { x: r.left, y: r.top, w: r.width, h: r.height };
  } else {
    flyFrom = null;
  }
  view.value = i;
  nextTick(() => {
    const box = viewEl.value;
    if (!box) return;
    const img = box.querySelector('img');
    if (img && img.decode) img.decode().then(flyIn, flyIn);
    else flyIn();
  });
}

function flyIn() {
  const box = viewEl.value;
  if (!box || !flyFrom) return;
  const t = box.getBoundingClientRect();
  if (!t.width || !t.height) return;
  const s = Math.max(flyFrom.w / t.width, .05);
  const dx = flyFrom.x + flyFrom.w / 2 - (t.left + t.width / 2);
  const dy = flyFrom.y + flyFrom.h / 2 - (t.top + t.height / 2);
  /* 先掐掉 CSS 入场动画：它的 fill-mode 是 both，终帧会一直压着 transform */
  box.style.animation = 'none';
  box.style.transition = 'none';
  box.style.transform = `translate(${dx}px, ${dy}px) scale(${s})`;
  box.style.borderRadius = '8px';
  requestAnimationFrame(() => requestAnimationFrame(() => {
    box.style.transition = 'transform .52s cubic-bezier(.22,1.08,.3,1), border-radius .42s var(--ease)';
    box.style.transform = 'translate(0px, 0px) scale(1)';
    box.style.borderRadius = '14px';
  }));
}

function closeView() {
  const box = viewEl.value;
  const el = lastPhEl;
  if (!box || !el || !el.isConnected) { view.value = -1; return; }
  const t = box.getBoundingClientRect();
  const r = el.getBoundingClientRect();
  if (!t.width || !r.width) { view.value = -1; return; }
  const s = Math.max(r.width / t.width, .05);
  box.style.transition = 'transform .42s var(--ease), opacity .3s ease';
  box.style.transform = `translate(${r.left + r.width / 2 - (t.left + t.width / 2)}px, ${r.top + r.height / 2 - (t.top + t.height / 2)}px) scale(${s})`;
  box.style.opacity = '.4';
  setTimeout(() => { view.value = -1; flyFrom = null; }, 300);
}
function stepView(d) {
  if (!allPhotos.value) return;
  view.value = (view.value + d + allPhotos.value) % allPhotos.value;
}

/* 叠合态左右划：像拇指拨一摞照片，拨过 34px 就换到下一张，后面的纸边跟着递补 */
const cur = ref(0);
const drag = ref(0);
const swiping = ref(false);
const cyc = (n) => (n >= 0 ? (cur.value + n) % Math.max(allPhotos.value, 1) : 0);
let sx = 0, sy = 0, holding = false, horiz = false, lastDx = 0, lastDragAt = 0;
function onSwipeDown(e) {
  /* 摊开后是网格，纵向要正常滚，这里只吃叠合态 */
  if (!canFold.value || open.value) return;
  holding = true; horiz = false; lastDx = 0;
  sx = e.clientX; sy = e.clientY;
}
function onSwipeMove(e) {
  if (!holding) return;
  const dx = e.clientX - sx, dy = e.clientY - sy;
  /* 先判方向：竖着划就让页面滚，别抢手势 */
  if (!horiz && Math.abs(dx) > 9 && Math.abs(dx) > Math.abs(dy)) {
    horiz = true;
    swiping.value = true;
  }
  if (!horiz) return;
  lastDx = dx;
  drag.value = Math.max(-34, Math.min(34, dx * .42));
}
function onSwipeUp() {
  if (!holding) return;
  holding = false;
  drag.value = 0;
  swiping.value = false;
  if (!horiz) return;
  /* 记一下刚才真的划过，紧接着的那次 click 不能当成「点一下放大」 */
  lastDragAt = Date.now();
  /* 阈值按手指走过的距离算，不是按阻尼后的位移 */
  if (lastDx <= -44) stepCur(1);
  else if (lastDx >= 44) stepCur(-1);
}
function stepCur(dir) {
  if (!canFold.value) return;
  cur.value = (cur.value + dir + allPhotos.value) % allPhotos.value;
}
/* 叠合态轻点一下就是放大看这一张；刚划过的那一下不算点 */
function onPileClick(e) {
  if (!canFold.value || open.value) return;
  if (Date.now() - lastDragAt < 260) return;
  /* 起飞点用最上面那张 d0，不是整个「一摞」的框 */
  const d0 = e?.currentTarget?.querySelector?.('.dv-dl.d0') || null;
  openView(cyc(0), { currentTarget: d0 });
}

/* 长心得：默认压到五行，超出来的用「展开全文」放出来，不把整页撑得没完 */
const more = reactive({ mine: false, ta: false });
const expanded = reactive({ mine: false, ta: false });
function measureNotes() {
  const wrap = bodyEl.value?.querySelector('.dv-notes');
  if (!wrap) return;
  for (const k of ['mine', 'ta']) {
    const p = wrap.querySelector('.dv-note.' + k + ' .dv-nbody p');
    if (!p) { more[k] = false; continue; }
    more[k] = p.scrollHeight - p.clientHeight > 3;
  }
}

/* 这一篇的色相：ph1~ph6 → cv1~cv6 */
const ci = computed(() => {
  const m = /ph([1-6])/.exec(props.phClass || 'ph1');
  return m ? m[1] : '1';
});

/* 照片：超过三张就是「一摞」，默认压着，点一下摊开成网格。
   一张都没有时不能兜底成 1 —— 那会在页面上留下一块空照片。 */
const allPhotos = computed(() =>
  Math.min(Math.max(props.entry?.info?.photos || 0, (props.entry?.info?.shots || []).length), 9)
);

/* 标题下面那行：分类 / 地点 / 心情，空的就不占位，别出现两个孤零零的点 */
const subBits = computed(() =>
  [props.entry?.info?.tag, props.entry?.info?.place, props.entry?.info?.mood]
    .map((s) => (s || '').trim())
    .filter(Boolean)
);
const photoList = computed(() => Array.from({ length: allPhotos.value }, (_, i) => i + 1));
const canFold = computed(() => allPhotos.value > 3);
const isOpen = computed(() => !canFold.value || open.value);
const cntPhoto = computed(() => props.entry?.info?.photos || 0);
/* 数的是「真写了的」心得：空着的一侧不算 */

const TINTS = ['t1', 't2', 't3', 't4', 't5', 't6'];
const tint = (i) => TINTS[i % TINTS.length];
/* 刚在这台手机上发布的那篇带着真图，优先显示真图，没有才用纸色占位 */
const shots = computed(() => {
  const s = props.entry?.info?.shots;
  return Array.isArray(s) ? s : [];
});

/* 折叠位移算成像素：格子边长由实测宽度推出，别用 calc(列号 * (-100% - 6px))
   ——那样写个别元素会整条 transform 解析失败，那一张就永远不动 */
const pileW = ref(0);
const GAP = 6;
function phVars(i) {
  const W = pileW.value || 342;
  const step = (W - GAP * 2) / 3 + GAP;
  const col = i % 3;
  const row = Math.floor(i / 3);
  const cx = -col * step + i * 1.7;
  const cy = -row * step + i * 1.7;
  return {
    '--cx': cx.toFixed(2) + 'px',
    '--cy': cy.toFixed(2) + 'px',
    '--i': i,
    '--rot': (col * 2 + row * 1 + i * 0.42).toFixed(2) + 'deg',
  };
}

async function startEdit() {
  draft.value = props.entry?.info?.note || '';
  editing.value = true;
  await nextTick();
  const ta = taEl.value;
  if (!ta) return;
  ta.focus();
  ta.setSelectionRange(draft.value.length, draft.value.length);
  /* 编辑卡可能落在屏幕外：把它推到顶栏下方，别让用户以为点了没反应 */
  const card = ta.closest('.dv-note');
  if (card && bodyEl.value) {
    const r = card.getBoundingClientRect();
    const br = bodyEl.value.getBoundingClientRect();
    const delta = r.top - br.top - 132;
    if (Math.abs(delta) > 8) {
      bodyEl.value.scrollTo({ top: bodyEl.value.scrollTop + delta, behavior: 'smooth' });
    }
  }
}
function cancel() {
  editing.value = false;
}
function save() {
  emit('edit', draft.value);
  editing.value = false;
}

watch(
  () => props.entry?.key,
  async () => {
    editing.value = false;
    open.value = false;
    cur.value = 0;
    expanded.mine = false;
    expanded.ta = false;
    await nextTick();
    measurePile();
    measureNotes();
  }
);

/* 折叠/摊开两态都必须是明确像素，否则高度一帧就跳满，照片还在飞，看着像卡了一下。
   摊开态没打开时网格还是 absolute + inset:0，offsetHeight 量到的是外面那个框，
   所以这里一律读 scrollHeight（内容自身的高度） */
function measurePile() {
  const wall = pileEl.value?.querySelector('.dv-wall');
  const deck = pileEl.value?.querySelector('.dv-deck');
  if (!wall || !pileEl.value) return;
  pileW.value = wall.offsetWidth;
  /* 折叠态的高度由那一摞决定，摊开态的高度由网格决定 */
  if (deck) {
    pileEl.value.style.setProperty('--oh', deck.scrollHeight + 'px');
  } else {
    const first = wall.querySelector('.dv-ph');
    pileEl.value.style.setProperty('--oh', (first ? first.offsetHeight : 112) + 'px');
  }
  pileEl.value.style.setProperty('--full', wall.scrollHeight + 'px');
}
onMounted(() => {
  /* 挂载当帧布局还没落定，量到的可能是 0，隔两帧再量 */
  requestAnimationFrame(() => requestAnimationFrame(() => { measurePile(); measureNotes(); }));
});
watch(open, async (v) => { if (!v) return; await nextTick(); measurePile(); });
watch(() => [expanded.mine, expanded.ta], async () => { await nextTick(); measurePile(); });
watch(
  () => [props.entry?.info?.note, props.entry?.info?.tnote],
  async () => { await nextTick(); measureNotes(); }
);
window.addEventListener('resize', () => { measurePile(); measureNotes(); });
onUnmounted(() => window.removeEventListener('resize', measurePile));

/* 划的时候跟手、松手弹回去。
   三种情况都接管：内容根本不满一屏；已经在顶上还往下拉；已经到底还往上推。
   内容够长、手指在中间划过时一律不接管，交给原生滚动 */
let pullFrom = 0;
let pullActive = false;
let pullTop0 = 0;

function onPullStart(e) {
  const s = bodyEl.value;
  if (!s) return;
  pullActive = false;
  pullFrom = e.touches[0].clientY;
  pullTop0 = s.scrollTop;
}
function onPullMove(e) {
  const s = bodyEl.value;
  const el = pullEl.value;
  if (!s || !el) return;
  const dy = e.touches[0].clientY - pullFrom;
  if (!pullActive) {
    const short = s.scrollHeight <= s.clientHeight + 2;
    const atTop = dy > 0 && s.scrollTop <= 0;
    const atBottom = dy < 0 && s.scrollTop >= s.scrollHeight - s.clientHeight - 1;
    if (!(short || atTop || atBottom)) return;
    pullActive = true;
    pullTop0 = s.scrollTop;
    el.style.transition = 'none';
  }
  /* 原生已经滚起来了，说明这一下手势不属于回弹，交回去 */
  if (s.scrollTop !== pullTop0) { endPull(); return; }
  const y = Math.max(-88, Math.min(88, dy * 0.42));
  el.style.transform = `translate3d(0,${y.toFixed(1)}px,0)`;
}
function endPull() {
  pullActive = false;
  const el = pullEl.value;
  if (!el) return;
  el.style.transition = 'transform .5s cubic-bezier(.22,1.18,.32,1)';
  el.style.transform = 'translate3d(0,0,0)';
}
function onPullEnd() {
  if (pullActive) endPull();
}

/* 视差：照片整块不缩放、不淡出（淡了像没加载出来），只往上浮一点点 */
let raf = 0;
function onScroll() {
  if (raf) return;
  raf = requestAnimationFrame(() => {
    raf = 0;
    if (!bodyEl.value) return;
    const y = bodyEl.value.scrollTop;
    if (heroEl.value) {
      heroEl.value.style.transform = `translate3d(0,${(-y * 0.05).toFixed(1)}px,0)`;
    }
    /* 雾只在内容快滚出去时才起来：一进来就蒙会让下面那块像残影 */
    if (fogEl.value) fogEl.value.style.opacity = String(Math.min(1, Math.max(0, (y - 150) / 110)));
  });
}
</script>

<style scoped>
/* ============ 与列表页同一套底 ============ */
.dpage {
  --pink: #FF5987;
  --pink-d: #F03E72;
  --lil: #A98BFF;
  --ink: #221c28;
  --ink2: #9a94a2;
  --ink3: #b6afc0;
  --fill: #F7F7F8;
  --line: rgba(100,80,120,.10);
  --ease: cubic-bezier(.16,1,.3,1);
  --spring: cubic-bezier(.32,1.24,.36,1);

  position: absolute; inset: 0; overflow: hidden;
  font-family: "Noto Sans SC", "PingFang SC", "HarmonyOS Sans SC",
               "Microsoft YaHei", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  /* 与 .dlist 完全同一张渐变：从列表点进来底色不跳 */
  background: linear-gradient(120deg, #D6CEF9 0%, #E2CEF0 100%);
}

/* 顶栏：和页面同一张渐变做底，滚动内容从它下面过去，不会在标题后面留半透明残影 */
.dv-bar {
  position: absolute; top: 0; left: 0; right: 0; z-index: 6;
  padding: max(50px, calc(env(safe-area-inset-top, 0px) + 20px)) 20px 12px;
  display: flex; align-items: center; gap: 10px;
  background: linear-gradient(120deg, #D6CEF9 0%, #E2CEF0 100%);
}
/* 下沿 24px 渐隐，内容与底色的交界不出现硬边 */
.dv-bar::after {
  content: ''; position: absolute; left: 0; right: 0; top: 100%; height: 24px;
  background: linear-gradient(180deg, rgba(216,207,246,.99) 0%, rgba(216,207,246,0) 100%);
  pointer-events: none;
}
.dv-ic {
  width: 40px; height: 40px; flex: none; border: 0; border-radius: 13px;
  background: rgba(255,255,255,.78);
  display: grid; place-items: center; color: #ff5c8a;
  transition: transform .34s var(--spring), background .2s;
}
.dv-ic:active { transform: scale(.9); background: #fff; }
.dv-bar-t {
  flex: 1; text-align: left; padding-left: 4px;
  font-size: 17px; font-weight: 800; letter-spacing: -.01em; color: var(--ink);
}
/* 顶栏右侧只做视觉配重，不放按钮 */
.dv-bar-pad { width: 40px; flex: none; }

/* ============ 滚动区 ============ */
.dv-scroll {
  position: absolute; inset: 0; z-index: 2;
  overflow-y: auto; overflow-x: hidden; scrollbar-width: none;
  /* 顶栏高度 + 54px 内容起点；顶栏下移多少，这里就跟多少 */
  padding-top: max(104px, calc(env(safe-area-inset-top, 0px) + 74px));
}
.dv-scroll::-webkit-scrollbar { display: none; }

/* 白色大盒子：和 .sheet-wrap 同手感（白、大圆角、同一档阴影）。
   底边不留缝、至少撑到屏幕底：卡片一路到底，底下不再露出一坨紫 */
/* 橡皮筋的外壳：transform 只加在这，不能加在有意入场动画的 .dv-sheet 上 */
.dv-pull {
  position: relative;
  will-change: transform;
}

.dv-sheet {
  position: relative;
  min-height: calc(100vh - 104px);
  margin: 0 4px 0;
  background: #fff;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 14px 30px -18px rgba(100,75,120,.28), 0 1px 4px -1px rgba(100,75,120,.1);
  animation: dvSheet .82s var(--ease) both;
}

/* ============ 作者行：一行交代「谁·哪天·几点」 ============ */
.dv-head {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 20px 14px;
  animation: dvUp .7s var(--ease) .06s both;
}
.dv-avatar {
  width: 30px; height: 30px; flex: none; border-radius: 50%;
  display: grid; place-items: center;
  background: linear-gradient(150deg, #FFB4CD 0%, #FF5987 100%);
  color: #fff; font-size: 13px; font-weight: 800;
  box-shadow: 0 8px 18px -10px rgba(255,89,135,.65);
}
.dv-hwho { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.dv-hwho b { font-size: 13.5px; font-weight: 800; color: var(--ink); letter-spacing: -.01em; }
.dv-hwho i { font-style: normal; font-size: 10.5px; font-weight: 700; color: var(--ink3); }
.dv-hcnt { flex: none; font-size: 11px; font-weight: 800; color: var(--ink2); }

/* ============ 照片：落在卡片里、四周留白，不做出血 ============ */
.dv-media {
  position: relative;
  padding: 0 20px;
  margin-top: 20px;
  will-change: transform;
  animation: dvMediaIn .92s var(--ease) .24s both;
}
/* 右上角只说有几张，不做成按钮 —— 已并入作者行，这块留空 */
.dv-decktag {
  display: none;
}

/* ============ 标题：衬线上一行，这一页的主角 ============ */
.dv-tblock { padding: 20px 20px 0; animation: dvUp .78s var(--ease) .12s both; }
.dv-by {
  font-size: 10.5px; font-weight: 600; color: var(--ink3);
  letter-spacing: .14em; text-transform: uppercase; margin-bottom: 10px;
}
.dv-title {
  margin: 0 0 11px;
  font-family: "Noto Serif SC", "Songti SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 26px; font-weight: 600; line-height: 1.36;
  letter-spacing: 0; color: var(--ink);
  overflow-wrap: anywhere;
}
.dv-sub {
  display: flex; align-items: center; flex-wrap: wrap; gap: 7px;
  font-size: 11.5px; font-weight: 500; color: #8d84a0; letter-spacing: .06em;
}
.dv-sep { opacity: .4; }

/* ============ 照片组上面：只有一枚右对齐的摊开 / 叠合 ============ */
.dv-pbar {
  display: flex; align-items: center; justify-content: flex-end;
  padding: 0 0 8px;
}
.dv-pn {
  font-size: 10px; font-weight: 500; color: #b6adc0;
  letter-spacing: .18em;
}
.dv-pn b {
  font-family: "Poppins", "Noto Sans SC", sans-serif;
  font-size: 11.5px; font-weight: 600; color: #8a7b9c; letter-spacing: .02em;
}
/* 摊开 / 叠合：站在照片右上方，不遮图 */
.dv-pbtn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 26px; padding: 0 11px 0 12px; border: 0; border-radius: 13px;
  background: rgba(255,255,255,.86); color: #6f4f88;
  -webkit-backdrop-filter: blur(12px) saturate(1.3);
  backdrop-filter: blur(12px) saturate(1.3);
  font-size: 10.5px; font-weight: 700; letter-spacing: .08em;
  font-family: inherit;
  box-shadow: 0 4px 12px -8px rgba(60,40,80,.55), inset 0 0 0 1px rgba(120,95,150,.16);
  transition: transform .32s var(--spring), background .28s;
}
.dv-pbtn:active { transform: scale(.93); }
.dv-pbtn svg { transition: transform .42s var(--spring); }
.dv-pbtn.on svg { transform: rotate(180deg); }
.dv-pbtn.on { background: #fff; }

/* ============ 照片网格：3 列、6px 缝、10px 圆角，像手记里的照片组 ============ */
.dv-wall { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
/* 只有一两张时铺满整宽，别让照片孤零零占着三格里的第一格 */
.dv-wall.w1 { grid-template-columns: 1fr; }
.dv-wall.w1 .dv-ph { aspect-ratio: 16 / 11; border-radius: 14px; }
.dv-wall.w2 { grid-template-columns: repeat(2, 1fr); }
.dv-wall.w2 .dv-ph { aspect-ratio: 4 / 3; }
.dv-ph {
  position: relative; aspect-ratio: 1; border-radius: 10px; overflow: hidden;
  display: grid; place-items: center;
  color: rgba(118,94,114,.40);
}
.dv-ph svg { width: 24px; height: 24px; position: relative; z-index: 1; }
.dv-phimg { position: absolute; inset: 0; z-index: 2; width: 100%; height: 100%; object-fit: cover; }
.dv-phglow {
  position: absolute; inset: 0;
  background: radial-gradient(70% 60% at 30% 22%, rgba(255,255,255,.62), rgba(255,255,255,0) 70%);
}
/* 没有真图时右下角一枚极小的相角，和折叠态同一处理。要压过 .dv-ph svg */
.dv-ph svg.dv-ip2 {
  position: absolute; right: 9px; bottom: 9px; z-index: 2;
  color: rgba(118,94,114,.32);
  width: 14px; height: 14px;
}
/* 与发布页同一组淡奶色：整个日记模块用一套照片纸色，深一块浅一块会显脏。
   每块都叠一层斜光 + 一层暗角，没有真图时也像一张虚焦的照片，而不是一块死色 */
.t1 { background: radial-gradient(62% 46% at 26% 16%, rgba(255,255,255,.6), rgba(255,255,255,0) 64%), radial-gradient(74% 58% at 84% 92%, rgba(170,104,48,.2), rgba(170,104,48,0) 72%), linear-gradient(150deg, #F6D9BC 0%, #EEC79E 100%); }
.t2 { background: radial-gradient(62% 46% at 26% 16%, rgba(255,255,255,.58), rgba(255,255,255,0) 64%), radial-gradient(74% 58% at 84% 92%, rgba(96,66,150,.22), rgba(96,66,150,0) 72%), linear-gradient(150deg, #D8C8F2 0%, #BCA9E6 100%); }
.t3 { background: radial-gradient(62% 46% at 26% 16%, rgba(255,255,255,.58), rgba(255,255,255,0) 64%), radial-gradient(74% 58% at 84% 92%, rgba(36,110,84,.2), rgba(36,110,84,0) 72%), linear-gradient(150deg, #CDE7DB 0%, #A9D2C0 100%); }
.t4 { background: radial-gradient(62% 46% at 26% 16%, rgba(255,255,255,.58), rgba(255,255,255,0) 64%), radial-gradient(74% 58% at 84% 92%, rgba(176,64,104,.2), rgba(176,64,104,0) 72%), linear-gradient(150deg, #F6CFDD 0%, #E9A9C1 100%); }
.t5 { background: radial-gradient(62% 46% at 26% 16%, rgba(255,255,255,.58), rgba(255,255,255,0) 64%), radial-gradient(74% 58% at 84% 92%, rgba(44,78,140,.2), rgba(44,78,140,0) 72%), linear-gradient(150deg, #CFDFF3 0%, #ABBDE0 100%); }
.t6 { background: radial-gradient(62% 46% at 26% 16%, rgba(255,255,255,.58), rgba(255,255,255,0) 64%), radial-gradient(74% 58% at 84% 92%, rgba(150,104,44,.2), rgba(150,104,44,0) 72%), linear-gradient(150deg, #F2DDC2 0%, #DDC09A 100%); }

/* 照片区：折叠就是整宽的一摞（点它自己摊开，再点收回来），摊开才是网格。
   两种形态叠在同一块里交叉过渡。
   这里必须过渡固定高度 —— 用 max-height 的话两态内容都比它矮，高度会直接跳到内容高，
   点开那一下没有「长出来」的过程 */
.dv-pile {
  position: relative;
  height: var(--oh, 250px);
/* 拖动时这一摞要能探出边框一点点，所以不裁；高度过渡期间略溢出也无妨 */
  overflow: visible;
  /* 叠合态要能横划换张，同时别抢走页面上下滚 */
  touch-action: pan-y;
  transition: height .66s cubic-bezier(.25,.46,.45,.94);
  -webkit-tap-highlight-color: transparent;
}
.dv-pile.open { height: var(--full, 236px); }

/* ---- 折叠态：一张主图，右下错出两层玻璃纸，磨砂半透，能看见下面那两张 ---- */
.dv-deck {
  position: relative; padding-bottom: 18px;
  transition: opacity .26s ease, transform .52s var(--ease);
}
/* 展开时这一摞必须让位：只淡出、还占着高度的话会把网格顶到裁切区外面去 */
.dv-pile.open .dv-deck {
  position: absolute; top: 0; left: 0; width: 100%;
  opacity: 0; transform: scale(.965); pointer-events: none;
}
/* 用 padding-top 撑比例：这边没有内容，aspect-ratio 量出来的高度不稳。
   类名不能叫 dv-stack —— 封面那三张拍立得已经占用了这个名字。
   叠合态收窄、压低：默认是「捏在手里的一叠」，点开摊成满宽网格才是「变大」 */
.dv-ply {
  position: relative;
  /* padding 的百分比是按「包含块宽度」算的（deck 约 342），不是 ply 自己的宽度，
     所以高度由 48% 定（约 164），宽度单独收窄到 246：比例才回到 3:2，
     不会变成一条横横幅。 */
  width: calc(100% - 96px); margin: 0 auto; padding-top: 48%;
  transform: translate3d(var(--drag, 0px), 0, 0);
  transition: transform .46s var(--spring);
}
/* 手指按住拖动时不能有过渡，否则每次都慢半拍追手指 */
.dv-pile.dragging .dv-ply { transition: none; }
/* 换张：旧的往左退半步淡出，新的从右边抬进来 */
.dvsw-enter-from { opacity: 0; transform: translate3d(24px, 0, 0) scale(.986) rotate(1deg); }
.dvsw-enter-active { transition: opacity .3s ease, transform .52s var(--spring); }
.dvsw-leave-to { opacity: 0; transform: translate3d(-26px, 0, 0) scale(.99) rotate(-1deg); }
.dvsw-leave-active { transition: opacity .24s ease, transform .38s var(--ease); }
.dv-dl { position: absolute; inset: 0; border-radius: 14px; overflow: hidden; }
/* 下面两层只往下错开：右边留干净，一摞纸的边缘从底下露出来，不是挂着一圈杂边 */
.dv-dl.d2 {
  transform: translate(0, 16px);
  box-shadow: 0 14px 28px -16px rgba(72,44,106,.6), inset 0 0 0 1px rgba(124,96,150,.12);
}
.dv-dl.d1 {
  transform: translate(0, 8px);
  box-shadow: 0 10px 22px -12px rgba(72,44,106,.55), inset 0 0 0 1px rgba(124,96,150,.16);
}
/* 后面这两层必须是「照片」本身（第 2、3 张），只在上面蒙一层很薄的玻璃：
   只铺渐变的话，露出来的那圈就是一块纯紫，看着不像一摞照片 */
.dv-glass {
  position: absolute; inset: 0; z-index: 3; pointer-events: none;
  background: linear-gradient(150deg, rgba(255,255,255,.18) 0%, rgba(214,198,240,.12) 100%);
}
/* 玻璃的反光：左上一条斜高光，露出来的那几像素才像"玻璃"而不是"色卡" */
.dv-dl.d1::after, .dv-dl.d2::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(135deg, rgba(255,255,255,.9) 0%, rgba(255,255,255,.24) 22%, rgba(255,255,255,0) 46%);
}
.dv-dl.d0 {
  display: grid; place-items: center;
  color: rgba(118,94,114,.40);
  /* 白照片压在白卡上会糊成一片：给自己一圈极淡的紫线，边界才立得起来 */
  box-shadow: 0 12px 26px -14px rgba(56,36,68,.34), inset 0 0 0 1px rgba(124,96,150,.18);
  transition: transform .46s var(--spring);
  touch-action: pan-y;
}
.dv-pile:active .dv-dl.d0 { transform: scale(.986); }
.dv-dl.d0 svg { width: 18px; height: 18px; position: relative; z-index: 2; }
/* 没有真图时右下角留一枚极小的相角记号，不把整块当成「加载失败」的空白。
   这里必须压过 .dv-dl.d0 svg 的那条 position:relative，否则会被拉回中间 */
.dv-dl.d0 svg.dv-ip {
  position: absolute; right: 11px; bottom: 11px; z-index: 2;
  color: rgba(118,94,114,.34); width: 15px; height: 15px;
}
.dv-dimg { position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; object-fit: cover; }
/* 主图顶上一道极淡的白，纸才有厚度 */
.dv-dl.d0::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(180deg, rgba(255,255,255,.2) 0%, rgba(255,255,255,.02) 38%, rgba(255,255,255,0) 62%);
}

/* ---- 摊开态：网格 ---- */
.dv-wall {
  position: absolute; inset: 0;
  opacity: 0; transform: scale(.97);
  transition: opacity .32s ease .1s, transform .5s var(--ease);
}
.dv-pile.open .dv-wall { position: relative; opacity: 1; transform: none; }

.dv-pile .dv-ph {
  will-change: transform;
  z-index: 1;
  transition: transform .66s var(--spring), box-shadow .5s ease;
  transition-delay: calc(var(--i) * .045s);
}
/* 摊开的动作：每张从中心那一摞里散出去归位，不是整体淡入一块网格 */
.dv-pile:not(.open) .dv-ph {
  transform: translate(var(--cx, 0px), var(--cy, 0px)) scale(.8);
  transition-delay: calc((8 - var(--i)) * .04s);
}

/* ============ 心得：一道小节线带出数量 ============ */
/* ============ 心得：一张卡片，标题在卡上 ============ */
.dv-card {
  margin: 22px 14px 0;
  padding: 15px 15px 17px;
  border-radius: 16px;
  background: linear-gradient(168deg, rgba(169,139,255,.055) 0%, rgba(255,255,255,.75) 78%);
  box-shadow: inset 0 0 0 1px rgba(120,95,150,.085), 0 10px 24px -22px rgba(78,50,114,.5);
  animation: dvUp .72s var(--ease) .36s both;
}
/* 标题用衬线、墨色、比人名字大一号：这样「心得」是这一块的标题，不会被当成正文的一部分 */
.dv-card-h {
  display: flex; align-items: center; gap: 7px;
  padding: 0 1px 3px;
}
.dv-card-ic { flex: none; color: #a98bff; opacity: .85; }
.dv-card-t {
  font-family: "Noto Serif SC", "Songti SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 15px; font-weight: 600; color: var(--ink);
  letter-spacing: .01em; line-height: 1.4;
}

.dv-notes { padding: 11px 1px 0; display: flex; flex-direction: column; gap: 20px; }
.dv-note {
  animation: dvNoteIn .62s var(--ease) both;
  animation-delay: .5s;
}
.dv-note.mine { }
.dv-note.ta {
  padding-top: 17px; border-top: 1px solid var(--line);
  animation-delay: .56s;
}
.dv-note.mine.editing {
  animation: none;
  padding: 12px; margin: 0 -4px;
  background: #FFF6F9; border-radius: 14px;
  box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.22);
}

/* 名字行：名字 + 时间，不加色点不加徽章，一页只留一处粉（编辑入口） */
.dv-nhead { display: flex; align-items: baseline; gap: 9px; }
.dv-nhead b { font-size: 13px; font-weight: 600; color: var(--ink); letter-spacing: .02em; }
.dv-nhead em { font-size: 10px; font-style: normal; font-weight: 500; color: #bdb3c8; letter-spacing: .1em; }

.dv-mini {
  flex: none; height: 24px; padding: 0 8px; margin-left: auto; margin-right: -8px; border: 0; border-radius: 7px;
  display: inline-flex; align-items: center; gap: 3px;
  background: transparent; color: var(--pink);
  font-size: 11px; font-weight: 800;
  transition: transform .34s var(--spring), background .2s;
}
.dv-mini:active { transform: scale(.9); background: rgba(255,89,135,.1); }

.dv-nbody { margin-top: 9px; }
/* 长串数字、连写英文不许顶出卡片：一律按任意字符折行，压到五行，多出来的用「展开全文」放 */
.dv-nbody p {
  margin: 0; font-size: 14.5px; line-height: 1.86; font-weight: 400;
  color: #403b4a; letter-spacing: .01em;
  overflow-wrap: anywhere; word-break: break-word;
  display: -webkit-box; -webkit-box-orient: vertical;
  -webkit-line-clamp: 5; overflow: hidden;
}
.dv-nbody p.open { -webkit-line-clamp: unset; display: block; overflow: visible; }
.dv-more {
  display: inline-flex; align-items: center; gap: 3px;
  height: 24px; padding: 0; margin-top: 4px; border: 0;
  background: none; color: #a289c4;
  font-family: inherit; font-size: 11px; font-weight: 600; letter-spacing: .06em;
}
.dv-more svg { transition: transform .34s var(--spring); }
.dv-more:active { opacity: .7; }
/* 还没写的时候别用一整行灰字充当正文——那读起来像内容被截断。
   换成一块能点的「待写」卡：虚线边、浅浅一层紫底、一个笔尖，点哪儿都进编辑 */
.dv-empty {
  display: flex; align-items: center; gap: 11px;
  width: 100%; margin-top: 11px; padding: 14px 14px 14px 13px;
  border: 1px dashed rgba(140,110,190,.3); border-radius: 13px;
  background: linear-gradient(160deg, rgba(169,139,255,.055) 0%, rgba(255,255,255,.55) 100%);
  font-family: inherit; text-align: left; color: #6f6879;
  transition: transform .34s var(--spring), border-color .28s ease, background .28s ease;
}
.dv-empty:active {
  transform: scale(.982);
  border-color: rgba(140,110,190,.46);
  background: linear-gradient(160deg, rgba(169,139,255,.1) 0%, rgba(255,255,255,.6) 100%);
}
.dv-empty-ic {
  flex: none; width: 30px; height: 30px; border-radius: 50%;
  display: grid; place-items: center;
  background: rgba(169,139,255,.14); color: #a98bff;
}
.dv-empty-tx { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.dv-empty-tx b {
  font-size: 13px; font-weight: 600; color: #6f6879;
  letter-spacing: .02em; line-height: 1.3;
}
.dv-empty-tx i {
  font-style: normal; font-size: 11px; font-weight: 500;
  color: #a9a3b5; letter-spacing: .05em; line-height: 1.3;
}
.dv-empty-go { flex: none; color: #bdb4c9; display: grid; place-items: center; }

.dv-edit { margin-top: 9px; }
.dv-ta {
  width: 100%; min-height: 96px; resize: none;
  padding: 11px 12px; border-radius: 12px;
  background: #fff; color: var(--ink);
  font-size: 13.5px; line-height: 1.72; font-weight: 500;
  box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.3);
  transition: box-shadow .24s;
}
.dv-ta:focus { box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.55); }
.dv-ebar {
  display: flex; align-items: center; gap: 8px; margin-top: 9px;
}
.dv-cnt { margin-right: auto; font-size: 10.5px; font-weight: 700; color: var(--ink3); }
.dv-etxt {
  height: 32px; padding: 0 13px; border: 0; border-radius: 10px;
  background: #fff; color: var(--ink2);
  font-size: 12px; font-weight: 800;
  box-shadow: inset 0 0 0 1px var(--line);
  transition: transform .3s var(--spring);
}
.dv-etxt:active { transform: scale(.94); }
.dv-esave {
  height: 32px; padding: 0 16px; border: 0; border-radius: 10px;
  background: var(--pink); color: #fff;
  font-size: 12px; font-weight: 800;
  box-shadow: 0 8px 16px -8px rgba(240,62,114,.7);
  transition: transform .3s var(--spring);
}
.dv-esave:active { transform: scale(.94); }

.dv-wait {
  display: flex; align-items: center; gap: 8px;
  padding: 13px 11px; border-radius: 11px;
  background: rgba(169,139,255,.055);
  box-shadow: inset 0 0 0 1px rgba(120,95,150,.07);
  font-size: 11.5px; font-weight: 600; color: #a9a3b5;
  letter-spacing: .06em;
  animation: dvUp .5s var(--ease) both;
}
.dv-wait em {
  margin-left: auto; font-style: normal; font-weight: 500;
  font-size: 10.5px; color: #bdb4c9; letter-spacing: .05em;
}
.dv-wwave {
  width: 6px; height: 6px; border-radius: 50%;
  background: rgba(169,139,255,.2);
  box-shadow: inset 0 0 0 1px rgba(150,135,175,.4);
  flex: none;
}
.dv-tail { height: 64px; display: flex; align-items: center; justify-content: center; }
/* 收尾的小标记：一条极淡的短横，像杂志末页的结束符 */
.dv-fin {
  display: block; width: 24px; height: 2px; border-radius: 1px;
  background: rgba(129,105,160,.17);
}

/* ============ 大图 ============ */
.dv-view { position: fixed; inset: 0; z-index: 84; display: grid; place-items: center; }
.dv-view-bg {
  position: absolute; inset: 0;
  background: rgba(16,12,20,.975);
  backdrop-filter: blur(18px) saturate(.92);
  -webkit-backdrop-filter: blur(18px) saturate(.92);
  animation: dvViewBg .26s ease both;
}
@keyframes dvViewBg { from { opacity: 0; } to { opacity: 1; } }
.dv-view-ph {
  position: relative; z-index: 2;
  border-radius: 14px; overflow: hidden;
  max-width: 92vw; max-height: 74vh;
  box-shadow: 0 34px 80px -20px rgba(0,0,0,.7);
  animation: dvViewIn .38s var(--spring) both;
  cursor: zoom-out;
}
.dv-view-ph img { display: block; max-width: 92vw; max-height: 74vh; object-fit: contain; }
.dv-view-tint { display: block; width: 80vw; aspect-ratio: 4 / 3; }
@keyframes dvViewIn { from { opacity: 0; transform: scale(.88); } to { opacity: 1; transform: none; } }
.dv-view-top {
  /* 要落在顶栏下面，否则 1/5 会跟日期叠在一起 */
  position: absolute; top: calc(72px + env(safe-area-inset-top, 0px)); left: 20px; right: 18px; z-index: 3;
  display: flex; align-items: center; justify-content: space-between;
  color: rgba(255,255,255,.78); font-size: 12.5px; font-weight: 800; letter-spacing: .03em;
}
.dv-view-x {
  width: 31px; height: 31px; border: 0; border-radius: 50%;
  display: grid; place-items: center;
  background: rgba(255,255,255,.14); color: #fff;
  transition: transform .3s var(--spring), background .26s;
}
.dv-view-x:active { transform: scale(.86); background: rgba(255,255,255,.24); }
.dv-view-step {
  position: absolute; top: 50%; margin-top: -22px; z-index: 3;
  width: 34px; height: 34px; border: 0; border-radius: 50%;
  display: grid; place-items: center;
  background: rgba(255,255,255,.12); color: rgba(255,255,255,.86);
  transition: transform .3s var(--spring), background .26s;
}
.dv-view-step:active { transform: scale(.86); }
.dv-view-step.prev { left: 10px; }
.dv-view-step.next { right: 10px; }

/* ============ 顶部雾 ============ */
/* 只铺到顶栏正下方一小段：作用是让滚上来的内容从顶栏边缘轻轻浮出，
   铺太高会把下面卡片的上沿染成紫色，看着像脏了 */
.dv-fog {
  position: absolute; top: 0; left: 0; right: 0; height: 96px; z-index: 4;
  pointer-events: none; opacity: 0;
  background:
    linear-gradient(180deg, rgba(216,207,246,.98) 0%, rgba(216,207,246,.98) 60px,
                    rgba(219,206,243,.62) 80px, rgba(220,207,242,0) 96px);
  transition: opacity .28s ease;
}

/* ============ 动效 ============ */
@keyframes dvSheet {
  from { opacity: 0; transform: translate3d(0,44px,0); }
  to   { opacity: 1; transform: none; }
}
/* 照片整块自上而下揭开：不写 transform，把 transform 留给滚动视差 */
@keyframes dvMediaIn {
  from { opacity: 0; clip-path: inset(0 0 92% 0); }
  to   { opacity: 1; clip-path: inset(0 0 0 0); }
}
@keyframes dvUp {
  from { opacity: 0; transform: translate3d(0,12px,0); }
  to   { opacity: 1; transform: none; }
}
@keyframes dvPop {
  from { opacity: 0; transform: scale(.82); }
  to   { opacity: 1; transform: scale(1); }
}
@keyframes dvFade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes dvCard {
  from { opacity: 0; transform: translate3d(0,16px,0) scale(.88); }
  to   { opacity: 1; transform: none; }
}
@keyframes dvNoteIn {
  from { opacity: 0; transform: translate3d(0,14px,0); }
  to   { opacity: 1; transform: none; }
}
@keyframes dvFold {
  from { opacity: 0; transform: translate3d(0,-6px,0) scaleY(.94); }
  to   { opacity: 1; transform: none; }
}
@keyframes dvDrift1 {
  0%,100% { transform: translate3d(0,0,0) scale(1); }
  50%     { transform: translate3d(22px,18px,0) scale(1.12); }
}
@keyframes dvDrift2 {
  0%,100% { transform: translate3d(0,0,0) scale(1.04); }
  50%     { transform: translate3d(-26px,14px,0) scale(.92); }
}
@keyframes dvSheen {
  0%   { transform: translate3d(-90%,0,0) rotate(16deg); opacity: 0; }
  18%  { opacity: .5; }
  46%  { opacity: .5; }
  70%,100% { transform: translate3d(280%,0,0) rotate(16deg); opacity: 0; }
}
@keyframes dvPulse {
  0%,100% { opacity: .32; transform: scale(.82); }
  50%     { opacity: 1; transform: scale(1); }
}

@media (prefers-reduced-motion: reduce) {
  .dv-sheet, .dv-head, .dv-media, .dv-tblock, .dv-bar2, .dv-note, .dv-wait,
  .dv-pile .dv-wall { animation: none !important; }
  .dv-wwave { animation: none !important; }
  .dv-pile { transition: none !important; }
  .dv-pile .dv-ph { transition: none !important; }
}
</style>
