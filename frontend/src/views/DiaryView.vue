<template>
<section class="view diary-view" :class="{ on: active }" data-view="diary" data-no-mask>
  <!-- 出错别静默：接口失败一闪而过说一句 -->
  <div class="dv-tip" v-if="tip">{{ tip }}</div>
  <div class="dv-tip warn" v-else-if="diaryError && !loading">{{ diaryError }}</div>
  <!-- ============ 列表页 ============ -->
  <div class="dlist" v-show="subPage === 'list'" ref="dlistEl">
    <div class="top-fixed">
      <div class="title-row">
        <h2>日记</h2>
        <div class="head-right">
          <button class="iconbtn" aria-label="打开日历快速跳转" @click="openMonth">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M8 3v4M16 3v4M3.5 10.5h17"/></svg>
          </button>
        </div>
      </div>

      <div
        class="cal"
        ref="calEl"
        @click="(e) => onTrackClick(e, scrollEl)"
      >
        <div class="cal-track" :style="{ width: trackWidth + 'px', transform: trackTransform }">
          <div
            v-for="d in DAYS"
            :key="keyOf(d)"
            class="dcell"
            :class="{ has: !!DIARY[keyOf(d)], 'is-today': keyOf(d) === keyOf(TODAY) }"
            :data-date="keyOf(d)"
            :style="{ width: cellW + 'px' }"
          >
            <span class="dnum">{{ d.getDate() }}</span>
            <span class="dwd">{{ WD[(d.getDay() + 6) % 7] }}</span>
          </div>
        </div>
        <div class="cal-pill" :style="{ left: pillLeft + 'px' }">
          <b>{{ pillNum }}</b>
          <small>{{ pillWd }}</small>
        </div>
      </div>
    </div>

    <div class="sheet-wrap">
      <div class="sheet-scroll" ref="scrollEl" @scroll="() => onListScroll(scrollEl)" @pointerdown="onListDown">
        <div v-if="!groups.length && !loading" class="dempty">
          <b>还没有日记</b>
          <span>点右下角那个 + ，写第一篇</span>
        </div>
        <div
          v-for="g in groups"
          :key="g.key"
          class="grp"
          :class="{ 'grp--more': !g.first }"
          :data-date="g.key"
        >
          <div v-if="g.first" class="grp__h">{{ g.groupTitle }}</div>
          <!-- 左滑露出删除：卡片跟着手指走，松手吸到 -84 或弹回 0 -->
          <div
            class="swipe"
            :class="{ 'swipe--open': openSwipe === g.key }"
            :data-own="g.info.mineId ? '1' : '0'"
            @pointerdown="onPtrDown($event, g.key, g.info)"
            @pointermove="onPtrMove($event, g.key)"
            @pointerup="onPtrUp($event, g.key)"
            @pointercancel="onPtrUp($event, g.key)"
          >
            <button
              class="swipe__del"
              type="button"
              tabindex="-1"
              aria-label="删除这篇日记"
              @click.stop="askDelete(g)"
            >删除</button>
            <button class="dcard" :style="cardStyle(g.key)" @click="onCardClick(g)">
              <!-- 没传照片就不留色块占位：整张卡变成纯文字 -->
              <span class="thumb" v-if="g.info.shots && g.info.shots.length">
                <img class="thumb__img" :src="g.info.shots[0]" alt="" />
              </span>
              <span class="dcard__b">
                <span class="dcard__t">{{ g.info.title }}</span>
                <span v-if="metaText(g.info)" class="dcard__m">{{ metaText(g.info) }}</span>
                <span class="tagrow">
                  <span class="ptag" :class="`ptag--${g.info.c}`">{{ g.info.tag }}</span>
                  <span class="avatars">
                    <!-- 头像要跟真正写这篇的人对上：对方写的就先挂对方，两边都写才并排 -->
                    <span class="mini-av av-lin">{{ g.info.both || g.info.writer === 'me' ? diaryInitials.me : diaryInitials.ta }}</span>
                    <span v-if="g.info.both" class="mini-av av-yu">{{ diaryInitials.ta }}</span>
                  </span>
                </span>
              </span>
            </button>
          </div>
        </div>
        <div class="list-end"></div>
      </div>
    </div>

    <button class="fab" aria-label="新建日记" @click="openNew">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
    </button>

    <!-- 月历快速跳转 -->
    <div class="m-overlay" :class="{ show: monthOpen }" @click.self="closeMonth">
      <div class="m-card">
        <div class="m-head">
          <button class="m-arrow" :aria-label="ymOpen ? '上一年' : '上个月'" @click="monthPrev">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>
          </button>
          <button v-if="!ymOpen" class="m-title" @click="openYm">
            {{ monthTitle }}
            <span class="m-caret" aria-hidden="true">▾</span>
          </button>
          <span v-else class="m-title static">{{ ymTitle }}</span>
          <button class="m-arrow" :aria-label="ymOpen ? '下一年' : '下个月'" :disabled="!canNext" @click="monthNext">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>
          </button>
        </div>

        <div v-if="ymOpen" class="m-ym">
          <button
            v-for="mm in ymMonths"
            :key="mm.m"
            class="m-ymcell"
            :class="{ on: mm.m === mViewMonth && ymYear === mViewYear, off: mm.future }"
            :disabled="mm.future"
            @click="pickYm(mm.m)"
          >{{ mm.label }} 月</button>
        </div>

        <template v-else>
          <div class="m-wd"><span v-for="w in weekDays" :key="w">{{ w }}</span></div>
          <div class="m-grid">
            <button
              v-for="c in monthCells"
              :key="c.key"
              class="m-cell"
              :class="c.classes"
              :disabled="!c.enabled"
              @click="pickMonth(c, scrollEl)"
            >
              {{ c.label }}
              <i v-if="c.hasDiary" class="m-dot"></i>
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>

  <!-- ============ 详情页 ============ -->
  <DiaryDetail
    v-if="subPage === 'detail'"
    :entry="detail"
    :ph-class="detail?.ph || 'ph1'"
    @back="backToList"
    @edit="onSaveNote"
  />
  <!-- ============ 新建页 ============ -->
  <DiaryNew v-if="subPage === 'new'" :busy="publishing" @back="backToList" @publish="onPublish" />

  <!-- 删一篇要问一句：左滑只是手势，手滑到位就没了不合适 -->
  <Teleport to="body">
    <Transition name="dd">
      <div v-if="delTarget" class="dd-wrap">
        <div class="dd-mask" @click="delTarget = null"></div>
        <div class="dd-sheet" role="dialog" aria-modal="true">
          <span class="dd-grab" aria-hidden="true"></span>
          <h3 class="dd-t">删掉这篇日记？</h3>
          <p class="dd-sub">{{ delTarget.info.title }}</p>
          <div class="dd-acts">
            <button class="dd-cancel" type="button" @click="delTarget = null">留着</button>
            <button class="dd-go" type="button" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? '删除中…' : '删除' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</section>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import { useDiary } from '../composables/useDiary.js';
import { removeDiary } from '../api/diaries.js';
import DiaryDetail from '../components/diary/DiaryDetail.vue';
import DiaryNew from '../components/diary/DiaryNew.vue';

const props = defineProps({ active: Boolean });

const {
  DAYS, DIARY, groups, TODAY,
  loading, error: diaryError, loadDiaries, diaryInitials,
  subPage, selectedKey, detail, openDetail, openNew, backToList, addDiary, updateNote,
  cellW, pos, trackX, trackWidth, trackTransform, pillLeft, pillNum, pillWd,
  measure, reanchor, init, resize,
  onListScroll, onTrackClick,
  monthOpen, monthTitle, monthCells,
  openMonth, closeMonth, monthPrev, monthNext, pickMonth,
  canNext,
  ymOpen, ymYear, ymTitle, ymMonths, openYm, closeYm, pickYm,
  mViewYear, mViewMonth,
  applyNavMask,
} = useDiary();

const keyOf = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const weekDays = ['日', '一', '二', '三', '四', '五', '六'];

const calEl = ref(null);
const scrollEl = ref(null);
const dlistEl = ref(null);

function onCardClick(g) {
  /* 拖动刚结束时别把这次抬起当成点击；卡片已经滑开时先收回去，不急着进详情 */
  if (suppressTap) return;
  if (openSwipe.value) { openSwipe.value = null; return; }
  openDetail(g.key);
}

/* ---------- 左滑删除 ---------- */
const DEL_W = 84;
const openSwipe = ref(null);   // 已经滑开、露出删除的那张卡
const dragKey = ref(null);
const dragDx = ref(0);
let sx = 0, sy = 0, baseDx = 0, axis = '', moved = false, suppressTap = false;

function cardStyle(key) {
  const dragging = dragKey.value === key;
  const dx = dragging ? dragDx.value : (openSwipe.value === key ? -DEL_W : 0);
  const cut = -dx;   // 右侧让出多少给删除按钮
  return {
    /* 不收宽卡片本身，只把右侧裁掉：标题这类贴在左边缘的内容不会被推出屏幕，
       也不会因为缩放变形 */
    clipPath: cut > 0
      ? `inset(0px ${cut}px 0px 0px round 15px)`
      : 'inset(0px 0px 0px 0px round 15px)',
    /* 跟手时不要过渡，松手才让吸附有动画 */
    transition: dragging ? 'none' : 'clip-path .26s cubic-bezier(.2,.8,.2,1)',
  };
}

function onPtrDown(e, key, info) {
  if (e.pointerType === 'mouse' && e.button !== 0) return;
  /* 只有自己写的那篇能删；只有对方那份时滑不动，也别把滑动收起来碍事 */
  if (!info || !info.mineId) return;
  if (openSwipe.value && openSwipe.value !== key) openSwipe.value = null;
  dragKey.value = key;
  sx = e.clientX; sy = e.clientY;
  baseDx = openSwipe.value === key ? -DEL_W : 0;
  dragDx.value = baseDx;
  axis = '';
  moved = false;
}

function onPtrMove(e, key) {
  if (dragKey.value !== key) return;
  const dx = e.clientX - sx, dy = e.clientY - sy;
  if (!axis) {
    if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
    axis = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
    /* 判定成竖向：手在滚列表，交还给滚动，别再跟着横着走 */
    if (axis === 'y') { dragKey.value = null; return; }
    /* 确认是横划之后才捕获指针：在 pointerdown 里就捕获的话，
       后面这次抬起产生的 click 会被重定向到外层容器，删除按钮就点不动了 */
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* 不支持就算了 */ }
  }
  if (axis !== 'x') return;
  moved = true;
  dragDx.value = Math.min(0, Math.max(-DEL_W, baseDx + dx));
}

function onPtrUp(e, key) {
  if (dragKey.value !== key) return;
  const dx = dragDx.value;
  const wasX = axis === 'x';
  dragKey.value = null;
  axis = '';
  if (!wasX) return;
  if (moved) {
    suppressTap = true;
    setTimeout(() => { suppressTap = false; }, 0);
  }
  openSwipe.value = dx < -DEL_W / 2 ? key : null;
  dragDx.value = 0;
}

/* 点列表空白处把滑开的卡片收回去 */
function onListDown(e) {
  if (!openSwipe.value) return;
  if (e.target && e.target.closest && e.target.closest('.swipe')) return;
  openSwipe.value = null;
}

/* 删除：左滑再点，已经算两次确认了，但删掉就找不回，还是问一句 */
const delTarget = ref(null);
const deleting = ref(false);
function askDelete(g) {
  if (!g || !g.info || !g.info.mineId) return;
  delTarget.value = g;
}
async function confirmDelete() {
  const g = delTarget.value;
  if (!g || deleting.value) return;
  deleting.value = true;
  try {
    await removeDiary(g.info.mineId);
    delTarget.value = null;
    openSwipe.value = null;
    await loadDiaries();
    await nextTick();
    await init(calEl.value, scrollEl.value);
    applyNavMask(dlistEl.value);
    toast('这篇删掉了');
  } catch (e) {
    toast((e && e.message) || '删除失败，稍后再试');
  } finally {
    deleting.value = false;
  }
}

/* 详情页里改完心得回写（后端 PUT） */
async function onSaveNote(text) {
  if (!selectedKey.value) return;
  try {
    await updateNote(selectedKey.value, text);
  } catch (e) {
    toast(e?.message || '保存失败，稍后再试');
    throw e;
  }
}

/* 发布：传图 + 建日记，再重建锚点把列表停在这篇上。
   publishing 同步置位（emit 是同步调用，父级在同帧就拿到 true），
   按钮立刻变「发布中」，不用再等计时器兜底。 */
const publishing = ref(false);
async function onPublish(payload) {
  publishing.value = true;
  try {
    await addDiary(payload);
    subPage.value = 'list';
    await nextTick();
    await init(calEl.value, scrollEl.value);
    applyNavMask(dlistEl.value);
  } catch (e) {
    toast(e?.message || '发布失败，稍后再试');
  } finally {
    publishing.value = false;
  }
}

/* 极简提示：失败别静默 */
const tip = ref('');
let tipTimer = null;
function toast(msg) {
  tip.value = msg;
  clearTimeout(tipTimer);
  tipTimer = setTimeout(() => { tip.value = ''; }, 2600);
}

function onResize() {
  resize(calEl.value, scrollEl.value);
  applyNavMask(dlistEl.value);
}

/* 列表卡第二行：写了心得就露出开头一小段（一行就截住），
   两端都写了才说「两个人的心得」；有照片带上张数；什么都没有就整行不显示。
   以前没内容时会退成「只有一句话 / 还没写」，等于把"没写"这件事又念了一遍；
   只有对方写了的时候又会误报「两个人的心得」。 */
function metaText(info) {
  const own = String(info.note || '').replace(/\s+/g, ' ').trim();
  const ta = String(info.tnote || '').replace(/\s+/g, ' ').trim();
  const cut = (s) => (s.length > 24 ? `${s.slice(0, 24)}…` : s);
  const bits = [];
  if (own && ta) bits.push('两个人的心得');
  else if (own || ta) bits.push(cut(own || ta));
  if (info.photos) bits.push(`${info.photos} 张照片`);
  return bits.join(' · ');
}

/* 每次切回日记页、以及每 20 秒的静默广播都重新拉一遍：两个人各写各的，
   对方补了心得要能看见。2 秒内的连续切换不重复请求；
   只重锚不重置滚动，别把用户正在看的位置顶掉。 */
let lastLoadAt = 0;
async function refreshDiary() {
  if (Date.now() - lastLoadAt < 2000) return;
  lastLoadAt = Date.now();
  await loadDiaries();
  await nextTick();
  reanchor(scrollEl.value);
}
watch(() => props.active, (on) => { if (on) refreshDiary(); });
function onGlobalSync(ev) {
  if (!props.active) return;
  const v = ev?.detail?.view;
  if (v && v !== 'diary') return;
  refreshDiary();
}

onMounted(async () => {
  await nextTick();
  await loadDiaries();
  lastLoadAt = Date.now();
  await nextTick();
  await init(calEl.value, scrollEl.value);
  applyNavMask(dlistEl.value);
  window.addEventListener('resize', onResize);
  window.addEventListener('cove:sync', onGlobalSync);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  window.removeEventListener('cove:sync', onGlobalSync);
});
</script>

<style scoped>
/* 覆盖工程默认 .view：日记页自己用 flex 列布局，不在外层滚动 */
.diary-view {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  /* 不要淡入淡出：这一页底色是紫色，和首页的粉色叠着做 0.4s 交叉淡入时，
     会先混成粉、再慢慢变紫，看着像"切换时底色闪粉"。直接瞬时切换，底色一次到位。 */
  transition: none;
}

/* 接口出错 / 保存失败的提示条 */
.dv-tip {
  position: absolute; left: 50%; bottom: 104px; z-index: 90;
  transform: translateX(-50%);
  max-width: 300px; padding: 9px 15px;
  border-radius: 12px;
  background: rgba(34,28,40,.9);
  color: #fff; font-size: 12.5px; font-weight: 600; line-height: 1.5;
  text-align: center;
  box-shadow: 0 12px 26px -14px rgba(40,20,60,.7);
  animation: dvTipIn .34s cubic-bezier(.16,1,.3,1) both;
}
.dv-tip.warn { background: rgba(140,60,90,.92); }
@keyframes dvTipIn {
  from { opacity: 0; transform: translate(-50%, 8px) scale(.96); }
  to { opacity: 1; transform: translate(-50%, 0) scale(1); }
}

.dlist {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  font-family: "Baloo 2", -apple-system, BlinkMacSystemFont, "PingFang SC","HarmonyOS Sans SC","Microsoft YaHei", system-ui, sans-serif;
  /* 底色只铺到三分之二，往下渐隐成透明 —— 底部那 200px 露出的是引擎自己画的
     纸底（和首页同一张底纹），底栏玻璃就采样在同一层背景上。
     以前紫色一路铺到屏幕底，等于用 DOM 盖住了玻璃的柔和外沿，
     所以日记页底栏显得"白块 + 一圈硬灰边"，另外三页却是软的。 */
  background: linear-gradient(180deg,
    #D6CEF9 0%,
    #E2CEF0 50%,
    rgba(226,206,240,.78) 62%,
    rgba(226,206,240,.30) 72%,
    rgba(226,206,240,0) 78%);
}

/* 顶部固定区：留出刘海 / 灵动岛，再落 20px 呼吸 */
.top-fixed {
  flex: none; position: relative; overflow: hidden;
  padding: max(54px, calc(env(safe-area-inset-top, 0px) + 20px)) 20px 6px; z-index: 3;
}
.top-fixed::before {
  content: ''; position: absolute; left: -70px; top: -40px;
  width: 260px; height: 260px;
  background: repeating-radial-gradient(circle at center, rgba(255,255,255,.34) 0 1px, transparent 1px 15px);
  opacity: .5; pointer-events: none;
}
.title-row { position: relative; display: flex; align-items: center; justify-content: space-between; }
.title-row h2 { font-size: 30px; font-weight: 800; letter-spacing: -.02em; color: #221c28; margin: 0; }
.iconbtn {
  width: 40px; height: 40px; border-radius: 13px; border: 0;
  background: rgba(255,255,255,.78);
  display: grid; place-items: center; color: #ff5c8a;
}
.head-right { display: flex; align-items: center; }

/* 连续日历 */
.cal {
  position: relative; margin-top: 16px; height: 62px;
  border-radius: 14px; background: #EBE7FC; overflow: hidden;
  touch-action: pan-y;
}
.cal-track {
  position: absolute; top: 0; left: 0; height: 100%; display: flex; will-change: transform;
  /* 这排日期不能用手划：位置只由列表滚动 / 点选决定，补一点过渡让胶囊"走一格"是滑过去的 */
  transition: transform .2s var(--ease);
}
.dcell {
  position: relative;
  flex: none; height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 3px;
}
.dcell .dnum { font-size: 15px; font-weight: 800; color: #2B2A2D; line-height: 1; }
.dcell .dwd { font-size: 11px; font-weight: 700; color: #9693A0; line-height: 1; }
.dcell.has .dwd { color: #c79bb0; }
/* 没写过日记的日子：数字压灰，一眼看出"这里点不动" */
.dcell:not(.has) .dnum { color: #bab3c6; }
/* 今天那一格：数字用粉色（即使今天还没写日记也能看出是哪天）。
   粉色胶囊标的是"你正看着哪一篇"，今天可能没有那一篇，
   所以今天再多一条小横杠 —— 否则胶囊停在昨天时，今天完全看不出来 */
.dcell.is-today .dnum { color: #FF5987; }
.dcell.is-today::after {
  content: ""; position: absolute; left: 50%; bottom: 5px;
  width: 14px; height: 2.5px; margin-left: -7px;
  border-radius: 2px; background: #FF5987; opacity: .9;
}
.cal-pill {
  position: absolute; top: 8px; width: 41px; height: 47px;
  border-radius: 12px; background: #FF5987;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; will-change: transform; z-index: 2;
  transition: left .2s var(--ease);
  box-shadow: 0 10px 20px -10px rgba(255,89,135,.7), inset 0 1px 0 rgba(255,255,255,.25);
}
.cal-pill b { font-size: 15px; font-weight: 800; color: #fff; line-height: 1; }
.cal-pill small { font-size: 11px; font-weight: 700; color: rgba(255,255,255,.92); line-height: 1; }

/* 固定白色大盒子 */
.sheet-wrap {
  flex: 1; display: flex; flex-direction: column; min-height: 0;
  /* 底边让到胶囊上方一点：留 74px 时白卡会压住胶囊顶部，
     进到列表以后底栏看着像被切断。100px 刚好让整颗胶囊和它的落位都露出来。 */
  margin: 16px 4px 100px; background: #fff;
  border-radius: 18px; overflow: hidden;
  box-shadow: 0 14px 30px -18px rgba(100,75,120,.28), 0 1px 4px -1px rgba(100,75,120,.1);
}
.sheet-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 8px; position: relative; scrollbar-width: none; }
.sheet-scroll::-webkit-scrollbar { display: none; }
.list-end { height: 160px; flex: none; }

.grp { margin-bottom: 12px; }
.grp:last-child { margin-bottom: 4px; }
/* 同一天的第二篇起不再重复日期标题，卡片挨得近一点，读起来是同一天里的两段 */
.grp--more { margin-top: -6px; margin-bottom: 10px; }

/* 一篇都没有时的空态：以前这里是一整片白，看着像页面没加载出来 */
.dempty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 7px; min-height: 58vh; padding: 0 18px; text-align: center;
}
.dempty b { font-size: 15px; font-weight: 800; color: #6B5F72; }
.dempty span { font-size: 12px; color: #a89fb0; }
.grp__h { font-size: 11.5px; font-weight: 800; color: #a89fb0; letter-spacing: .04em; margin: 6px 6px 8px; }

.dcard {
  border: 0; width: 100%; text-align: left;
  background: #F7F7F8; border-radius: 15px; padding: 12px;
  display: flex; gap: 12px; align-items: center;
  box-shadow: 0 6px 14px -10px rgba(100,80,120,.22), inset 0 0 0 1px rgba(100,80,120,.04);
  transition: transform .4s var(--spring);
}
.dcard:active { transform: scale(.975); }
/* 缩略图就一张，不做叠合 */
.thumb { width: 62px; height: 62px; border-radius: 18px; flex: none; overflow: hidden; position: relative; }
.thumb i { position: absolute; inset: 0; }
.thumb__img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.dcard__b { flex: 1; min-width: 0; }
.dcard__t {
  display: block; font-size: 15.5px; font-weight: 800; letter-spacing: -.015em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #221c28;
}
.dcard__m {
  display: block; margin-top: 4px; font-size: 12px; color: #9a94a2;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tagrow { margin-top: 8px; display: flex; align-items: center; gap: 7px; }
.ptag { font-size: 10.5px; font-weight: 800; padding: 3px 9px; border-radius: 8px; }
.ptag--blue { background: #eaf1ff; color: #5b7fe0; }
.ptag--green { background: #e8f8ef; color: #34b97a; }
.ptag--pink { background: #ffeef4; color: #e8457a; }
.avatars { margin-left: auto; display: flex; }
.mini-av {
  width: 26px; height: 26px; border-radius: 50%;
  display: grid; place-items: center;
  font-size: 10px; font-weight: 800; color: #fff; border: 2px solid #fff;
}
.mini-av + .mini-av { margin-left: -9px; }
.av-lin { background: linear-gradient(150deg,#ff8fb8,#f04a82); }
.av-yu { background: linear-gradient(150deg,#ffb08f,#f07a4f); }

/* 缩略图渐变 */
.ph1 { background: linear-gradient(150deg,#ffd6a5,#ff9d76 60%,#f7c873); }
.ph2 { background: linear-gradient(150deg,#c9b8f0,#8f7fd9); }
.ph3 { background: linear-gradient(150deg,#a8e0c8,#5bb896); }
.ph4 { background: linear-gradient(150deg,#f5b8d0,#e87aa8); }
.ph5 { background: linear-gradient(150deg,#b8d8f0,#7aa8d9); }
.ph6 { background: linear-gradient(150deg,#f0d0a8,#d9a878); }

/* FAB */
.fab {
  position: absolute; right: 22px; bottom: 108px;
  width: 58px; height: 58px; border-radius: 50%; border: 0;
  background: #FF5987; color: #fff; display: grid; place-items: center;
  z-index: 5;
  box-shadow: 0 16px 30px -10px rgba(240,62,114,.5), inset 0 1px 0 rgba(255,255,255,.35);
  transition: transform .45s var(--spring);
}
.fab:active { transform: scale(.9) rotate(90deg); }

/* 月历弹层 */
.m-overlay {
  position: absolute; inset: 0; z-index: 20;
  display: flex; align-items: center; justify-content: center;
  padding: 24px; background: rgba(76,58,104,.38); backdrop-filter: blur(3px);
  opacity: 0; pointer-events: none; transition: opacity .32s var(--ease);
}
.m-overlay.show { opacity: 1; pointer-events: auto; }
.m-card {
  /* 这个弹层不在 .cr-page / .mv 这些带主题变量的子树里，var(--pink) 一直是空的：
     选中格没有底色、只留一圈粉晕，白字压在白卡上等于消失；今天的粉描边也一起丢了。
     这里把弹层自己的粉定住（和顶部胶囊、FAB 同一个 #FF5987）。 */
  --pink: #FF5987;
  width: 100%; background: #fff; border-radius: 26px; padding: 18px 16px 16px;
  box-shadow: 0 30px 60px -24px rgba(70,45,95,.5);
  transform: scale(.92) translateY(10px); transition: transform .38s var(--spring);
}
.m-overlay.show .m-card { transform: none; }
.m-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.m-title {
  display: inline-flex; align-items: center; gap: 5px;
  border: 0; background: none; font-family: inherit;
  font-size: 16px; font-weight: 800; letter-spacing: -.01em; color: #241f26;
  padding: 6px 8px; margin: 0 -8px; border-radius: 10px;
  transition: background .18s var(--ease);
}
.m-title:active { background: #F4F1FC; }
.m-title.static { padding: 6px 8px; margin: 0; }
.m-title.static:active { background: none; }
.m-caret { font-size: 10px; color: #b6afc6; line-height: 1; transform: translateY(1px); }
.m-arrow {
  width: 36px; height: 36px; border-radius: 12px; border: 0;
  background: #F1EEFA; display: grid; place-items: center; color: #5b5468;
}
.m-arrow:active { background: #E6E1F7; }
.m-arrow:disabled { opacity: .35; }
/* 年月面板：4 × 3 个月份，高度贴着日期网格，切过去卡片不跳 */
.m-ym {
  display: grid; grid-template-columns: repeat(4, 1fr);
  grid-template-rows: repeat(3, 1fr); gap: 8px;
  /* 和 5 行日期网格等高，切换时卡片高度基本不动 */
  min-height: 238px;
}
.m-ymcell {
  border: 0; border-radius: 14px; background: #F6F4FB;
  font-family: inherit; font-size: 14px; font-weight: 700; color: #3a3344;
  transition: background .18s var(--ease), color .18s, transform .18s var(--spring);
}
.m-ymcell:active { transform: scale(.95); background: #EDE9F8; }
.m-ymcell.on { background: var(--pink); color: #fff; box-shadow: 0 8px 16px -8px rgba(240,62,114,.6); }
.m-ymcell.off { opacity: .3; }
.m-wd { display: grid; grid-template-columns: repeat(7,1fr); margin-bottom: 6px; }
.m-wd span { text-align: center; font-size: 11px; font-weight: 800; color: #aaa4b4; }
.m-grid { display: grid; grid-template-columns: repeat(7,1fr); gap: 4px; }
.m-cell {
  position: relative; aspect-ratio: 1; border: 0; background: none; border-radius: 11px;
  font-size: 14px; font-weight: 700; color: #2c2730;
  display: grid; place-items: center;
  transition: background .2s var(--ease), color .2s;
}
.m-cell.other { color: #cfc9d8; }
.m-cell.off { opacity: .3; }
/* 今天即使还没写日记，也要留个能认出来的浅粉地标（比别的禁用日子略亮，但仍不可点） */
.m-cell.off.today { opacity: .66; }
/* 今天只做浅粉底，不要用粉色描边：描边和"选中"的实心粉块太像，
   看着像两个格子同时被选中。选中在后面声明，两者重叠时实心粉块胜出。 */
.m-cell.today { background: rgba(255,89,135,.12); color: #d93a68; }
.m-cell.sel { background: var(--pink); color: #fff; box-shadow: 0 8px 16px -8px rgba(240,62,114,.6); }
.m-cell:not(.sel):active { background: #F3F0FA; }
.m-dot {
  position: absolute; bottom: 4px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px; border-radius: 50%; background: var(--pink);
}
.m-cell.sel .m-dot { background: #fff; }

/* ---------- 左滑删除 ---------- */
/* 卡片自己的阴影挪到外框上：滑动时卡片要往外走，阴影留在原地更稳 */
.swipe {
  position: relative; overflow: hidden;
  border-radius: 15px;
  box-shadow: 0 6px 14px -10px rgba(100,80,120,.22);
  touch-action: pan-y;        /* 竖向滚动照常交给浏览器，横划我们自己接 */
}
.swipe__del {
  position: absolute; top: 0; right: 0; bottom: 0; width: 84px;
  border: 0; padding: 0;
  background: linear-gradient(180deg, #FF6E7C 0%, #ED4257 100%);
  color: #fff; font: inherit; font-size: 13.5px; font-weight: 800;
  letter-spacing: -.01em;
  display: grid; place-items: center;
  cursor: pointer;
}
.swipe__del:active { filter: brightness(.94); }

/* 加了 swipe 之后卡片不再自己带投影，内描边保留 */
.dcard { box-shadow: inset 0 0 0 1px rgba(100,80,120,.04); }
/* 拖动时别再有按下缩放，跟着手指走就够了 */
.dcard:active { transform: none; }

/* ---------- 删除确认：和「清空」同一套贴底 sheet ---------- */
.dd-wrap {
  position: fixed; inset: 0; margin: auto;
  width: var(--phone-w, 390px); height: var(--phone-h, 844px);
  max-width: 100vw; max-height: 100vh;
  z-index: 10000;
  display: flex; align-items: flex-end;
  border-radius: 52px; overflow: hidden;
  pointer-events: none;
}
@media (max-width: 520px) {
  .dd-wrap { width: 100%; height: 100%; border-radius: 0; }
}
.dd-mask {
  position: absolute; inset: 0;
  background: rgba(74,40,58,.26);
  backdrop-filter: blur(10px) saturate(120%);
  -webkit-backdrop-filter: blur(10px) saturate(120%);
  pointer-events: auto;
}
.dd-sheet {
  position: relative; width: 100%;
  padding: 8px 20px calc(20px + env(safe-area-inset-bottom, 0px));
  border-radius: 26px 26px 0 0;
  background: #fff;
  box-shadow: 0 -6px 22px -16px rgba(150,60,110,.26);
  pointer-events: auto;
}
.dd-grab {
  display: block; width: 36px; height: 4px; margin: 0 auto 12px;
  border-radius: 999px; background: rgba(185,125,155,.28);
}
.dd-t {
  margin: 0 0 7px;
  font-size: 18px; font-weight: 800; letter-spacing: -.03em; color: #3A1C2C;
}
.dd-sub {
  margin: 0 0 18px;
  font-size: 13px; line-height: 1.62; color: #8E7A88;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dd-acts { display: flex; gap: 10px; }
/* 主视觉仍然留给「留着」；「删除」白底红字，够显眼但不诱导 */
.dd-cancel {
  flex: 1; height: 50px; border-radius: 15px; border: 0;
  color: #fff; background: linear-gradient(180deg,#FF86AB 0%,#FF4E82 100%);
  font: inherit; font-size: 15px; font-weight: 800; cursor: pointer;
  box-shadow: 0 12px 22px -14px rgba(255,78,130,.75), inset 0 1px 0 rgba(255,255,255,.4);
  transition: transform .2s cubic-bezier(.34,1.4,.64,1), filter .22s ease;
}
.dd-cancel:active { transform: scale(.98); filter: brightness(.96); }
.dd-go {
  flex: 1; height: 50px; border-radius: 15px;
  border: 1px solid rgba(226,59,87,.34);
  background: #fff; color: #E23B57;
  font: inherit; font-size: 15px; font-weight: 700; cursor: pointer;
  transition: transform .2s cubic-bezier(.34,1.4,.64,1), background .22s ease, border-color .22s ease;
}
.dd-go:active:not(:disabled) { transform: scale(.98); background: #FFF4F5; border-color: rgba(226,59,87,.5); }
.dd-go:disabled { opacity: .6; }

.dd-enter-active .dd-sheet { animation: ddUp .36s cubic-bezier(.16,1,.3,1) both; }
.dd-enter-active .dd-mask { animation: ddFade .26s ease both; }
.dd-leave-active .dd-sheet { animation: ddUp .22s cubic-bezier(.4,0,1,1) reverse both; }
.dd-leave-active .dd-mask { animation: ddFade .22s ease reverse both; }
@keyframes ddUp { from { transform: translateY(100%); } to { transform: none; } }
@keyframes ddFade { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  .dd-enter-active .dd-sheet, .dd-leave-active .dd-sheet,
  .dd-enter-active .dd-mask, .dd-leave-active .dd-mask { animation: none; }
}
</style>
