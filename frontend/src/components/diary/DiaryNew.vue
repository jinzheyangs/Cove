<template>
  <div class="dpage" :class="{ leaving: busy }">
    <!-- 顶部：和列表页同一套按钮语言，右上把「清空」做成粉底小胶囊 -->
    <div class="dv-bar">
      <button class="dv-ic" aria-label="返回" @click="emit('back')">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>
      </button>
      <span class="dv-bar-t">写日记</span>
      <button class="dv-clear" v-if="hasAny" @click="askClear">清空</button>
      <button class="dv-clear ghost" v-else disabled>清空</button>
    </div>

    <!-- 清空要问一句：写了一半的东西一键抹掉，不能点一下就没 -->
    <Teleport to="body">
      <Transition name="dc">
        <div v-if="confirmOpen" class="dc-wrap">
          <div class="dc-mask" @click="closeClear"></div>
          <div class="dc-card" role="dialog" aria-modal="true">
            <span class="dc-grab" aria-hidden="true"></span>
            <h3 class="dc-t">清空这篇日记？</h3>
            <p class="dc-sub">主题、心得和照片都会清掉，且不会保存。</p>
            <div class="dc-acts">
              <button class="dc-cancel" type="button" @click="closeClear">取消</button>
              <button class="dc-go" type="button" @click="doClear">清空</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

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
        <!-- 一行日期，和详情页顶栏同一写法 -->
        <div class="dv-today" ref="heroEl">
          <span class="dv-tday">{{ today.month }} {{ +today.num }} 日</span>
          <i class="dv-twd">· {{ today.wd }}</i>
        </div>

        <!-- ============ 名字：这一篇的标题，可以不填，空着就用正文开头 ============ -->
        <div class="dv-name">
          <input
            class="dv-title-input"
            v-model="title"
            maxlength="24"
            placeholder="写个主题吧"
          />
          <span class="dv-tcount" :class="{ show: title.length > 0 }">{{ title.length }} / 24</span>
        </div>
        <p class="dv-hint">主题写一句就能存下来，心得和照片随后补也行</p>

        <!-- ============ 照片 ============ -->
        <div class="dv-photo">
          <!-- 系统相册选择器：点入口就弹，一次可以选多张 -->
          <input
            ref="fileEl"
            class="dv-file"
            type="file"
            accept="image/*"
            multiple
            @change="onFiles"
          />

          <!-- 空态：一条细入口，不铺一块像照片的空框（没图就别占那块地方） -->
          <template v-if="!n">
          <button class="dv-open" @click="pickPhotos">
            <span class="dv-oplus">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            </span>
            <span class="dv-otx">
              <b>加照片</b>
              <i>从相册挑，最多 9 张</i>
            </span>
            <svg class="dv-ogo" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>
          </button>
          </template>

          <template v-else>
          <!-- 照片组上面只留一枚「摊开 / 叠合」，靠右，不压图；张数在格子里看得出来 -->
          <div class="dv-pbar" v-if="canFold">
            <button class="dv-pbtn" :class="{ on: open }" @click.stop="open = !open">
              <span>{{ open ? '叠合' : '摊开' }}</span>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
            </button>
          </div>

          <!-- 有图：超过三张就自己合成一摞，摊开后能左右划、点图放大 -->
          <div
            ref="deckEl"
            class="dv-deck"
            :class="{ open: !canFold || open, foldable: canFold, dragging: swiping }"
            :style="{ '--drag': drag + 'px' }"
            @pointerdown="onSwipeDown"
            @pointermove="onSwipeMove"
            @pointerup="onSwipeUp"
            @pointercancel="onSwipeUp"
            @click="onDeckClick"
          >
            <div v-if="canFold" ref="plyEl" class="dv-ply">
              <div class="dv-dl d2" :class="photos[cyc(2)]?.tint">
                <img v-if="photos[cyc(2)]?.src" class="dv-img" :src="photos[cyc(2)].src" alt="" />
                <span class="dv-glass"></span>
              </div>
              <div class="dv-dl d1" :class="photos[cyc(1)]?.tint">
                <img v-if="photos[cyc(1)]?.src" class="dv-img" :src="photos[cyc(1)].src" alt="" />
                <span class="dv-glass"></span>
              </div>
              <transition name="dvsw">
                <div class="dv-dl d0" :key="cur">
                  <img v-if="photos[cyc(0)]?.src" class="dv-img" :src="photos[cyc(0)].src" alt="" />
                  <span v-else class="dv-tint" :class="photos[cyc(0)]?.tint"></span>
                </div>
              </transition>
            </div>

            <div ref="wallEl" class="dv-grid">
              <div
                v-for="(p, i) in photos" :key="p.id"
                class="dv-frame" :class="{ shoot: p.up }"
                :style="{ '--i': i }"
                @click="openPreview(i)"
              >
                <span class="dv-tint" :class="p.tint"></span>
                <img v-if="p.src" class="dv-img" :src="p.src" alt="" />
                <button class="dv-x" @click.stop="removePhoto(i)" aria-label="去掉这张">
                  <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
                </button>
              </div>
              <button v-if="n < 9" class="dv-addcell" :class="{ wide: n % 3 === 0 }" @click.stop="pickPhotos" aria-label="再加">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
                <i>{{ n }} / 9</i>
              </button>
            </div>
          </div>
          </template>
        </div>
        <div class="dv-blk">
          <div class="dv-lab">心得<i class="dv-opt">可后补</i></div>
          <div class="dv-note" :class="{ has: note.length > 0 }">
            <textarea
              class="dv-ta"
              v-model="note"
              maxlength="600"
              placeholder="今天发生了什么，心里怎么想的…"
            ></textarea>
            <span class="dv-cnt" :class="{ show: note.length > 0 }">{{ note.length }} / 600</span>
          </div>
        </div>

        <!-- ============ 分类 ============ -->
        <div class="dv-blk">
          <div class="dv-lab">分类</div>
          <div class="dv-chips">
            <button
              v-for="(c, i) in TAGS" :key="c"
              class="dv-chip" :class="{ on: tag === c }"
              :style="{ '--i': i }"
              @click="tag = tag === c ? '' : c"
            >{{ c }}</button>
          </div>
        </div>

        <!-- ============ 心情 ============ -->
        <div class="dv-blk">
          <div class="dv-lab">那天的心情</div>
          <div class="dv-chips soft">
            <button
              v-for="(m, i) in MOODS" :key="m"
              class="dv-chip" :class="{ on: mood === m }"
              :style="{ '--i': i }"
              @click="mood = mood === m ? '' : m"
            >{{ m }}</button>
          </div>
        </div>

        <!-- ============ 在哪里 ============ -->
        <div class="dv-blk">
          <div class="dv-place" :class="{ filled: place.length > 0 }">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11Z"/><circle cx="12" cy="10" r="2.4"/></svg>
            <input v-model="place" maxlength="18" placeholder="在哪里，比如家附近的早市" />
          </div>
        </div>

        <!-- ============ 发布 ============ -->
        <div class="dv-submit">
          <button class="dv-pub" :class="{ ready: canPublish }" :disabled="busy" @click="submit">
            <span v-if="!busy" class="dv-bico">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.6 9.4 18 20 7"/></svg>
            </span>
            <span v-else class="dv-ring"></span>
            {{ busy ? '发布中' : '发布这一篇' }}
          </button>
        </div>

        <div class="dv-tail"></div>
      </div>
      </div>
    </div>

    <!-- 滚过头部、内容够发了，才浮出来的圆形发布键 -->
    <button class="dv-fab" :class="{ on: showFab }" :disabled="busy" @click="submit" aria-label="发布">
      <span v-if="!busy">
        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.6 9.4 18 20 7"/></svg>
      </span>
      <span v-else class="dv-ring"></span>
    </button>

    <div class="dv-fog" ref="fogEl"></div>

    <!-- 大图：点一下照片进来看清，左右点翻页，点背景退出 -->
    <Teleport to="body">
      <div v-if="preview >= 0 && photos[preview]" class="dv-view">
        <div class="dv-view-bg" @click="preview = -1"></div>
        <div class="dv-view-hit" @click="stepPreview(-1)"></div>
        <div class="dv-view-hit right" @click="stepPreview(1)"></div>
        <div class="dv-view-img" @click="preview = -1">
          <img v-if="photos[preview].src" :src="photos[preview].src" alt="" />
          <span v-else class="dv-tint" :class="photos[preview].tint" style="aspect-ratio:4/3;width:80vw;display:block"></span>
        </div>
        <div class="dv-view-top">
          <span>{{ preview + 1 }} / {{ n }}</span>
          <button class="dv-view-x" @click="preview = -1" aria-label="关闭">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </div>
        <button class="dv-view-step prev" @click.stop="stepPreview(-1)" aria-label="上一张">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M14 6 8 12l6 6"/></svg>
        </button>
        <button class="dv-view-step next" @click.stop="stepPreview(1)" aria-label="下一张">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m10 6 6 6-6 6"/></svg>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';

/* busy 由父级传入：真正把图上传 + 创建日记的那段时间由父级管，
   组件只负责「点下去就立即进入发布中」。sending 自己做会让复位时机错，
   要么点完还能再点一次造出两条，要么失败后按钮卡死。 */
const props = defineProps({ busy: { type: Boolean, default: false } });
const emit = defineEmits(['back', 'publish']);

const bodyEl = ref(null);
const pullEl = ref(null);
const heroEl = ref(null);
const fogEl = ref(null);
const fileEl = ref(null);
const deckEl = ref(null);
const plyEl = ref(null);
const wallEl = ref(null);

const title = ref('');
const tag = ref('');
const mood = ref('');
const note = ref('');
const place = ref('');
const loading = ref(0);
const fabOn = ref(false);

let pid = 0;
const photos = ref([]);           // [{ id, tint, up, src }]
const n = computed(() => photos.value.length);

/* 超过三张就先叠成一摞：只留一张的高度，别把整页撑成一面墙 */
const canFold = computed(() => n.value > 3);
const open = ref(false);

function measureDeck() {
  const d = deckEl.value;
  if (!d) return;
  if (!canFold.value) {
    d.style.removeProperty('--oh');
    d.style.removeProperty('--full');
    return;
  }
  nextTick(() => {
    if (plyEl.value) d.style.setProperty('--oh', plyEl.value.offsetHeight + 13 + 'px');
    if (wallEl.value) d.style.setProperty('--full', wallEl.value.scrollHeight + 'px');
  });
}

function onDeck() {
  if (!canFold.value) return;
  open.value = !open.value;
}

/* 大图：摊开后点某一张能看清，左右可以翻 */
const preview = ref(-1);
function openPreview(i) {
  if (!photos.value[i]) return;
  preview.value = i;
}
function stepPreview(d) {
  const len = photos.value.length;
  if (!len) return;
  preview.value = (preview.value + d + len) % len;
}

/* 叠合态左右划：拨过 44px 换下一张，后面的纸边跟着递补 */
const cur = ref(0);
const drag = ref(0);
const swiping = ref(false);
const cyc = (k) => (n.value ? (cur.value + k) % n.value : 0);
let sx = 0, sy = 0, holding = false, horiz = false, lastDx = 0, lastDragAt = 0;
function onSwipeDown(e) {
  if (!canFold.value || open.value) return;
  holding = true; horiz = false; lastDx = 0;
  sx = e.clientX; sy = e.clientY;
}
function onSwipeMove(e) {
  if (!holding) return;
  const dx = e.clientX - sx, dy = e.clientY - sy;
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
  lastDragAt = Date.now();
  if (lastDx <= -44) cur.value = (cur.value + 1) % n.value;
  else if (lastDx >= 44) cur.value = (cur.value - 1 + n.value) % n.value;
}
/* 叠合态轻点：放大看当前这张 */
function onDeckClick() {
  if (!canFold.value || open.value) return;
  if (Date.now() - lastDragAt < 260) return;
  openPreview(cyc(0));
}

watch(n, (v) => {
  /* 一多就自动收起来：新加的那张先落在「一摞」上，想看全部再点开 */
  if (v > 3) open.value = false;
  if (cur.value >= v) cur.value = 0;
  measureDeck();
});

/* 摊开/收起换了排法（网格 <-> 横滑），高度得按当前那套重算，不然会留一大截空白 */
watch(open, () => measureDeck());

const TAGS = ['约会', '日常', '运动', '旅行', '美食'];
const MOODS = ['开心', '平静', '放松', '温柔', '慵懒'];

const WD = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
const now = new Date();
const today = {
  num: String(now.getDate()).padStart(2, '0'),
  wd: WD[now.getDay()],
  month: `${now.getMonth() + 1} 月`,
};

const hasAny = computed(
  () => !!title.value.trim() || !!tag.value || !!mood.value || !!note.value.trim() || !!place.value.trim() || n.value > 0
);
/* 主题必填：这一篇得有个名字，列表里才认得出是哪天哪件事。
   心得和后补的照片都允许先空着，回头再写。 */
const canPublish = computed(() => title.value.trim().length > 0);
const showFab = computed(() => fabOn.value && canPublish.value);

const TINTS = ['t1', 't2', 't3', 't4', 't5', 't6'];

function pickPhotos() {
  if (props.busy) return;
  fileEl.value?.click();
}

/* 选进来的原图先缩到 1280 长边、压成 JPEG dataURL：
   预览快、发布也能直接带着走，不用再挂 objectURL 去管释放 */
function shrink(file) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const max = 1280;
      const s = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.max(1, Math.round(img.width * s));
      c.height = Math.max(1, Math.round(img.height * s));
      const g = c.getContext('2d');
      g.drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      resolve(c.toDataURL('image/jpeg', 0.82));
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(''); };
    img.src = url;
  });
}

function onFiles(e) {
  const files = Array.from(e.target.files || []);
  /* 清空 value，否则再选同一张不会再触发 change */
  e.target.value = '';
  if (props.busy) return;
  for (const f of files) {
    if (n.value >= 9) break;
    if (!f.type.startsWith('image/')) continue;
    const id = ++pid;
    /* 先占一个格子（tint 当底色），图压好了再淡进去 */
    photos.value.push({ id, tint: TINTS[(id - 1) % TINTS.length], up: true, src: '' });
    loading.value += 1;
    shrink(f)
      .then((dataUrl) => {
        const it = photos.value.find((p) => p.id === id);
        if (it && dataUrl) it.src = dataUrl;
      })
      .finally(() => { loading.value -= 1; });
    setTimeout(() => {
      const it = photos.value.find((p) => p.id === id);
      if (it) it.up = false;
    }, 620);
  }
}
function removePhoto(i) {
  photos.value.splice(i, 1);
}

/* 清空先弹确认：这一步不可撤销，不能手滑就没 */
const confirmOpen = ref(false);
function askClear(){
  if (!hasAny.value) return;
  confirmOpen.value = true;
}
function closeClear(){
  confirmOpen.value = false;
}
function doClear(){
  clearAll();
  confirmOpen.value = false;
}

function clearAll() {
  title.value = '';
  tag.value = '';
  mood.value = '';
  note.value = '';
  place.value = '';
  photos.value = [];
}

function submit() {
  if (!canPublish.value || props.busy) return;
  const go = () => {
    emit('publish', {
      title: title.value.trim(),
      tag: tag.value,
      mood: mood.value,
      note: note.value.trim(),
      place: place.value.trim(),
      photos: n.value,
      /* 预览图一起带走：发布后列表和详情显示的就是刚选的这几张 */
      shots: photos.value.map((p) => p.src).filter(Boolean),
    });
  };
  /* 只有真还有图在压缩时才等（否则会把没压完的图丢掉）；
     没有在压缩就立刻发 —— 之前这里无条件等 620ms，就是「点发布卡一下」的来源 */
  if (loading.value > 0) {
    const t0 = performance.now();
    const tick = () => {
      if (loading.value === 0 || performance.now() - t0 > 2500) go();
      else setTimeout(tick, 90);
    };
    tick();
  } else {
    go();
  }
}

/* 划的时候跟手、松手弹回去：内容不满一屏、顶上还往下拉、到底还往上推，都接管；
   其余交给原生滚动 */
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

/* 视差 + 雾 + 浮动键 */
let raf = 0;
function onScroll() {
  if (raf) return;
  raf = requestAnimationFrame(() => {
    raf = 0;
    if (!bodyEl.value) return;
    const y = bodyEl.value.scrollTop;
    if (heroEl.value) {
      const t = Math.min(y, 220) / 220;
      heroEl.value.style.transform = `translate3d(0,${y * 0.14}px,0) scale(${1 + t * 0.03})`;
      heroEl.value.style.opacity = String(1 - t * 0.3);
    }
    if (fogEl.value) fogEl.value.style.opacity = String(Math.min(1, y / 46));
    /* 页底那颗「发布这一篇」自己就在眼前了，浮动键就该收起来，别压着它 */
    const maxY = bodyEl.value.scrollHeight - bodyEl.value.clientHeight;
    fabOn.value = y > 160 && y < maxY - 140;
  });
}

function onResize() { measureDeck(); }

onMounted(() => {
  window.addEventListener('resize', onResize);
  nextTick(measureDeck);
});
onBeforeUnmount(() => window.removeEventListener('resize', onResize));
</script>

<style scoped>
/* ============ 与列表页 / 详情页同一套底 ============ */
.dpage {
  --pink: #FF5987;
  --pink-d: #F03E72;
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
  background: linear-gradient(120deg, #D6CEF9 0%, #E2CEF0 100%);
  transition: transform .42s cubic-bezier(.32,1.1,.36,1), opacity .38s ease, filter .38s ease;
}
.dpage.leaving { transform: scale(.988) translate3d(0,-4px,0); opacity: .9; filter: blur(.6px); }

/* ============ 顶部栏 ============ */
.dv-bar {
  position: absolute; top: 0; left: 0; right: 0; z-index: 6;
  padding: max(50px, calc(env(safe-area-inset-top, 0px) + 20px)) 20px 12px;
  display: flex; align-items: center; gap: 10px;
  background: linear-gradient(120deg, #D6CEF9 0%, #E2CEF0 100%);
}
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
  flex: 1; text-align: center;
  font-size: 19px; font-weight: 800; letter-spacing: -.01em; color: var(--ink);
}
.dv-clear {
  flex: none; height: 34px; padding: 0 13px; border: 0; border-radius: 11px;
  background: rgba(255,255,255,.82); color: #ff5c8a;
  font-size: 12px; font-weight: 800;
  box-shadow: 0 6px 14px -10px rgba(240,62,114,.6);
  transition: transform .34s var(--spring), background .2s;
}
.dv-clear:active { transform: scale(.93); background: #fff; }
.dv-clear.ghost { opacity: 0; pointer-events: none; }

/* ============ 滚动区 / 白盒 ============ */
.dv-scroll {
  position: absolute; inset: 0; z-index: 2;
  overflow-y: auto; overflow-x: hidden; scrollbar-width: none;
  padding-top: max(104px, calc(env(safe-area-inset-top, 0px) + 74px));
}
.dv-scroll::-webkit-scrollbar { display: none; }
/* 橡皮筋外壳：transform 只加在这，不能加在带入场动画的 .dv-sheet 上 */
.dv-pull {
  position: relative;
  will-change: transform;
}

.dv-sheet {
  position: relative;
  /* 二级页底栏会滑走，只留一点收尾空间 */
  margin: 0 4px 34px;
  background: #fff; border-radius: 20px; overflow: hidden;
  box-shadow: 0 14px 30px -18px rgba(100,75,120,.28), 0 1px 4px -1px rgba(100,75,120,.1);
  animation: dvSheet .82s var(--ease) both;
}

/* ============ 日期：一行小字，和详情页顶栏同一写法 ============ */
.dv-today {
  position: relative;
  padding: 22px 20px 0;
  display: flex; align-items: baseline; gap: 8px;
  will-change: transform, opacity;
}
.dv-tday {
  font-size: 12.5px; font-weight: 800; color: var(--ink2); letter-spacing: .03em;
  animation: dvUp .7s var(--ease) .06s both;
}
.dv-twd {
  font-size: 12px; font-weight: 700; color: var(--ink3); font-style: normal; letter-spacing: .03em;
  animation: dvUp .7s var(--ease) .1s both;
}

/* ============ 照片：空态一条细入口，有图就是网格 ============ */
.dv-photo { padding: 16px 20px 0; animation: dvUp .76s var(--ease) .2s both; }

/* 没图时只留一条 54px 的入口，不再画一块 16:10 的空照片框 */
.dv-open {
  width: 100%; height: 54px; border: 0; border-radius: 14px;
  display: flex; align-items: center; gap: 11px; padding: 0 13px;
  background: #FBFAFD; text-align: left;
  box-shadow: inset 0 0 0 1px rgba(100,80,120,.07);
  transition: transform .42s var(--spring), box-shadow .3s, background .3s;
}
.dv-open:active { transform: scale(.984); background: #F5F2F9; box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.42); }
.dv-oplus {
  width: 32px; height: 32px; border-radius: 50%; flex: none;
  display: grid; place-items: center;
  background: #fff; color: var(--pink);
  box-shadow: 0 6px 14px -9px rgba(100,75,140,.5), inset 0 0 0 1px var(--line);
}
.dv-otx { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
.dv-ogo { color: var(--ink3); flex: none; }
.dv-open b { font-size: 13px; font-weight: 800; color: #6f677a; }
.dv-open i { font-size: 10.5px; font-weight: 700; color: var(--ink3); font-style: normal; }

/* 一摞 / 摊开：同一块地方，靠高度和透明度过渡，不换容器也不加按钮 */
.dv-deck {
  position: relative; overflow: hidden;
  border-radius: 14px;
  height: var(--full, auto);
  touch-action: pan-y;
  transition: height .64s cubic-bezier(.22,.9,.3,1);
}
.dv-deck.foldable { height: var(--oh, 200px); }
.dv-deck.foldable.open { height: var(--full, 400px); }

/* 叠起来时那一摞：第一张真图 + 两层淡紫纸边 */
.dv-ply {
  position: relative;
  padding-top: 52%;
  /* 往左让 16px，好让下面几张纸的右边缘错出来 */
  margin-right: 16px;
  transform: translate3d(var(--drag, 0px), 0, 0);
  transition: opacity .36s ease, transform .52s var(--ease);
}
/* 手指按住横划时不能有过渡，否则慢半拍追手指 */
.dv-deck.dragging .dv-ply { transition: none; }
/* 换张：旧的往左退半步淡出，新的从右边抬进来 */
.dvsw-enter-from { opacity: 0; transform: translate3d(22px, 0, 0) scale(.986) rotate(1deg); }
.dvsw-enter-active { transition: opacity .3s ease, transform .5s var(--spring, cubic-bezier(.32,1.24,.36,1)); }
.dvsw-leave-to { opacity: 0; transform: translate3d(-24px, 0, 0) scale(.99) rotate(-1deg); }
.dvsw-leave-active { transition: opacity .24s ease, transform .36s var(--ease); }
.dv-deck.open .dv-ply {
  position: absolute; top: 0; left: 0; right: 0;
  opacity: 0; transform: scale(.975);
  pointer-events: none;
  transition: opacity .24s ease, transform .5s var(--ease);
}
/* 收起时这一摞晚半步回来，让网格先退干净，别两套内容叠在一帧里 */
.dv-deck.foldable:not(.open) .dv-ply {
  transition: opacity .3s ease .12s, transform .54s var(--ease) .12s;
}
.dv-dl {
  position: absolute; inset: 0;
  border-radius: 14px; overflow: hidden;
  transition: transform .52s var(--ease);
}
.dv-dl.d0 {
  z-index: 3;
  /* 上面这张自己带一圈极细的亮边，下面的纸才读得出来是「两张」 */
  box-shadow: 0 14px 30px -22px rgba(90,60,110,.55), inset 0 0 0 1px rgba(255,255,255,.42);
}
/* 下面两层是玻璃：半透紫白 + 磨砂 + 一道斜高光，透出底下那层的边 */
.dv-dl.d1 {
  z-index: 2; transform: translate(7px, 8px);
  box-shadow: 0 10px 22px -12px rgba(72,44,106,.55), inset 0 0 0 1px rgba(255,255,255,.78);
}
/* 后面两层就是第 2、3 张本身，上面只蒙一层薄玻璃——只铺纯渐变会变成一块紫 */
.dv-glass {
  position: absolute; inset: 0; z-index: 3; pointer-events: none;
  background: linear-gradient(150deg, rgba(255,255,255,.18) 0%, rgba(214,198,240,.12) 100%);
}
.dv-dl.d2 {
  z-index: 1; transform: translate(14px, 16px);
  box-shadow: 0 14px 28px -16px rgba(72,44,106,.6), inset 0 0 0 1px rgba(255,255,255,.62);
}
.dv-dl.d1::after, .dv-dl.d2::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(135deg, rgba(255,255,255,.9) 0%, rgba(255,255,255,.24) 22%, rgba(255,255,255,0) 46%);
}
/* 展开时两层纸边同时往里收，像被抽走 */
.dv-deck.open .dv-dl.d1 { transform: none; }
.dv-deck.open .dv-dl.d2 { transform: none; }

.dv-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
  transition: opacity .34s ease, transform .52s var(--ease);
}
/* 摊开后：三列铺开，所有照片一次看全 */
.dv-deck.foldable.open .dv-grid { gap: 6px; }

/* 摊开 / 叠合站在照片右上方，不压图；这一行只有它，靠右 */
.dv-pbar {
  display: flex; align-items: center; justify-content: flex-end;
  padding: 0 0 8px;
}
.dv-pn {
  font-size: 10px; font-weight: 500; color: #b6adc0; letter-spacing: .18em;
}
.dv-pn b {
  font-family: "Poppins", "Noto Sans SC", sans-serif;
  font-size: 11.5px; font-weight: 600; color: #8a7b9c; letter-spacing: .02em;
}
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
.dv-deck.foldable:not(.open) .dv-grid {
  position: absolute; top: 0; left: 0; width: 100%;
  opacity: 0; pointer-events: none;
  transform: translateY(10px) scale(.99);
  transition: opacity .2s ease, transform .46s var(--ease);
}
/* 散开时逐张落位，别整块一起亮：只在「一摞换成网格」这一下播，收起时不播 */
.dv-deck.foldable.open .dv-grid .dv-frame,
.dv-deck.foldable.open .dv-grid .dv-addcell {
  animation: dvSpread .56s var(--spring) both;
  animation-delay: calc(var(--i, 0) * .045s + .06s);
}
@keyframes dvSpread {
  from { opacity: 0; transform: translateY(8px) scale(.94); }
  to { opacity: 1; transform: none; }
}
.dv-frame {
  position: relative; aspect-ratio: 1; border-radius: 10px;
  overflow: hidden; z-index: calc(20 - var(--i, 0));
}
/* 落位动画放在里层：动画的 transform 会压住外层的状态 */
.dv-frame.shoot .dv-tint { animation: dvShoot .62s var(--spring) both; }
.dv-file { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; z-index: -1; }
.dv-img {
  position: absolute; inset: 0; z-index: 1;
  width: 100%; height: 100%; object-fit: cover;
  animation: dvImgIn .5s ease both;
}
@keyframes dvImgIn { from { opacity: 0; transform: scale(1.04); } to { opacity: 1; transform: none; } }
.dv-tint { position: absolute; inset: 0; }
.t1 { background: linear-gradient(150deg, #F6D9BC 0%, #EEC79E 100%); }
.t2 { background: linear-gradient(150deg, #D8C8F2 0%, #BCA9E6 100%); }
.t3 { background: linear-gradient(150deg, #CDE7DB 0%, #A9D2C0 100%); }
.t4 { background: linear-gradient(150deg, #F6CFDD 0%, #E9A9C1 100%); }
.t5 { background: linear-gradient(150deg, #CFDFF3 0%, #ABBDE0 100%); }
.t6 { background: linear-gradient(150deg, #F2DDC2 0%, #DDC09A 100%); }
.dv-tint::after {
  content: ""; position: absolute; inset: 0;
  background: radial-gradient(66% 56% at 28% 20%, rgba(255,255,255,.5), rgba(255,255,255,0) 70%);
}
.dv-x {
  position: absolute; top: 5px; left: 5px; z-index: 3;
  width: 19px; height: 19px; border: 0; border-radius: 50%;
  display: grid; place-items: center;
  background: rgba(255,255,255,.86); color: #7c6a8e;
  box-shadow: 0 4px 10px -5px rgba(60,40,80,.6);
  transition: transform .3s var(--spring);
}
.dv-x:active { transform: scale(.85); }

/* ============ 大图 ============ */
.dv-view { position: fixed; inset: 0; z-index: 84; display: grid; place-items: center; }
.dv-view-bg {
  position: absolute; inset: 0;
  background: rgba(18,12,24,.95);
  animation: dvViewBg .26s ease both;
}
@keyframes dvViewBg { from { opacity: 0; } to { opacity: 1; } }
.dv-view-hit { position: absolute; top: 64px; bottom: 64px; left: 0; width: 24%; z-index: 1; }
.dv-view-hit.right { left: auto; right: 0; }
.dv-view-img {
  position: relative; z-index: 2; border-radius: 14px; overflow: hidden;
  max-width: 92vw; max-height: 74vh; width: auto;
  display: block;
  box-shadow: 0 34px 80px -20px rgba(0,0,0,.7);
  animation: dvViewIn .36s var(--spring) both;
}
.dv-view-img img { display: block; max-width: 92vw; max-height: 74vh; object-fit: contain; }
.dv-view-img .dv-tint { position: absolute; inset: 0; }
@keyframes dvViewIn { from { opacity: 0; transform: scale(.9); } to { opacity: 1; transform: none; } }
.dv-view-top {
  position: absolute; top: 54px; left: 20px; right: 18px; z-index: 3;
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

/* 最后一格永远留着「再加」：加图不需要另开按钮 */
.dv-addcell {
  aspect-ratio: 1; border: 0; border-radius: 10px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
  background: #FAF8FC; color: #a49aae;
  box-shadow: inset 0 0 0 1px rgba(100,80,120,.1);
  transition: transform .34s var(--spring), box-shadow .26s, color .26s;
  animation: dvPop .4s var(--spring) both;
}
.dv-addcell i { font-style: normal; font-size: 9.5px; font-weight: 800; color: var(--ink3); }
.dv-addcell:active { transform: scale(.94); color: var(--pink); box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.4); }
/* 张数正好占满一行时，让「再加」整行横铺，不留两个空格 */
.dv-addcell.wide {
  grid-column: 1 / -1; aspect-ratio: auto; height: 46px;
  flex-direction: row; gap: 8px;
}
.dv-addcell.wide svg { width: 15px; height: 15px; }
.dv-addcell.wide i { font-size: 11px; }

/* ============ 名字：这一篇的标题，在照片上面 ============ */
.dv-name { position: relative; padding: 10px 20px 0; animation: dvUp .7s var(--ease) .14s both; }
.dv-title-input {
  width: 100%; border: 0; background: none;
  font-family: "Noto Serif SC", "Songti SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 25px; font-weight: 600; letter-spacing: 0; color: var(--ink);
  line-height: 1.38;
  padding: 2px 46px 6px 0;
}
.dv-title-input::placeholder { color: #c2bacd; font-weight: 600; }
.dv-tcount {
  position: absolute; right: 20px; top: 16px;
  font-size: 10px; font-weight: 700; color: var(--ink3);
  opacity: 0;
  transition: opacity .22s ease;
}
.dv-tcount.show { opacity: .75; }
/* 一行说明：这三样不是都要填，于是别在每栏各标一次"可不写" */
.dv-hint {
  margin: 2px 0 0; padding: 0 20px;
  font-size: 11px; font-weight: 600; letter-spacing: .01em;
  color: #b0a4b4;
}

/* ============ 通用块 ============ */
.dv-blk { padding: 20px 20px 0; animation: dvUp .7s var(--ease) .3s both; }

.dv-lab {
  font-size: 12px; font-weight: 800; color: var(--ink);
  margin-bottom: 9px;
  display: flex; align-items: baseline; gap: 6px;
}
.dv-lab i { font-size: 10.5px; font-weight: 700; color: var(--ink3); font-style: normal; }

.dv-chips { display: flex; gap: 6px; }
.dv-chip {
  flex: 1; height: 36px; border: 0; border-radius: 11px;
  background: var(--fill); color: var(--ink2);
  font-size: 12px; font-weight: 800;
  box-shadow: inset 0 0 0 1px var(--line);
  animation: dvPop .48s var(--spring) both;
  animation-delay: calc(.5s + var(--i) * .035s);
  transition: transform .38s var(--spring), background .22s, color .22s, box-shadow .22s;
}
.dv-chip:active { transform: scale(.93); }
.dv-chip.on {
  background: var(--pink); color: #fff;
  box-shadow: 0 10px 18px -10px rgba(240,62,114,.7), inset 0 1px 0 rgba(255,255,255,.26);
}
.dv-chips.soft .dv-chip.on {
  background: #FFF0F5; color: var(--pink);
  box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.34);
}

.dv-note {
  position: relative; background: #fff; border-radius: 14px;
  box-shadow: inset 0 0 0 1px rgba(100,80,120,.13);
  transition: box-shadow .26s, background .26s, transform .42s var(--spring);
}
.dv-note:focus-within {
  background: #fff; box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.32), 0 12px 24px -18px rgba(240,62,114,.5);
}
.dv-ta {
  width: 100%; height: 70px; resize: none; display: block;
  padding: 11px 12px 24px; border-radius: 14px;
  font-size: 13.5px; line-height: 1.72; font-weight: 500; color: var(--ink);
  transition: height .5s var(--spring);
}
/* 空着、没点进来时只占一条；点进来或已经写了字，框再长开 */
.dv-note:focus-within .dv-ta,
.dv-note.has .dv-ta { height: 134px; }
.dv-ta::placeholder { color: #b8b1c1; font-weight: 500; }
.dv-cnt {
  position: absolute; right: 12px; bottom: 9px;
  font-size: 10px; font-weight: 700; color: var(--ink3);
  opacity: 0; transition: opacity .28s;
}
.dv-cnt.show { opacity: 1; }

.dv-place {
  display: flex; align-items: center; gap: 8px;
  height: 42px; padding: 0 12px; border-radius: 12px;
  background: var(--fill); color: #ada1bb;
  box-shadow: inset 0 0 0 1px var(--line);
  transition: box-shadow .24s, color .24s, background .24s;
}
.dv-place:focus-within { background: #fff; box-shadow: inset 0 0 0 1.5px rgba(255,89,135,.32); color: var(--pink); }
.dv-place.filled { color: var(--pink); }
.dv-place input { flex: 1; border: 0; background: none; font-size: 12.5px; font-weight: 600; color: var(--ink); }
.dv-place input::placeholder { color: #b8b1c1; font-weight: 500; }

/* ============ 发布 ============ */
.dv-submit { padding: 26px 20px 8px; animation: dvUp .7s var(--ease) .42s both; }
.dv-pub {
  position: relative; overflow: hidden;
  width: 100%; height: 50px; border: 0; border-radius: 16px;
  display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  font-size: 14.5px; font-weight: 800; letter-spacing: -.01em;
  background: #F2E6EC; color: #b6a6ae;
  transition: transform .4s var(--spring), background .26s, color .26s, box-shadow .3s;
}
.dv-pub.ready {
  background: linear-gradient(120deg, #FF6E97 0%, #F0437A 100%);
  color: #fff;
  box-shadow: 0 14px 26px -14px rgba(240,62,114,.8), inset 0 1px 0 rgba(255,255,255,.28);
}
.dv-pub.ready::after {
  content: ""; position: absolute; top: 0; bottom: 0; width: 42%;
  left: -60%; transform: skewX(-18deg);
  background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.42), rgba(255,255,255,0));
  animation: dvSheen 1.1s ease-out .28s both;
}
.dv-pub.ready:active { transform: scale(.972); }
.dv-bico { display: inline-flex; }
.dv-tip {
  display: flex; align-items: center; gap: 6px;
  margin-top: 10px; font-size: 10.5px; font-weight: 700; color: var(--ink3);
}
.dv-wdot {
  width: 5px; height: 5px; border-radius: 50%; background: var(--pink);
  animation: dvPulse 2.4s ease-in-out infinite;
}
.dv-tail { height: 18px; }

/* ============ 浮动发布 ============ */
.dv-fab {
  position: absolute; right: 22px; bottom: 26px; z-index: 5;
  width: 58px; height: 58px; border-radius: 50%; border: 0;
  display: grid; place-items: center;
  background: #FF5987; color: #fff;
  box-shadow: 0 16px 30px -10px rgba(240,62,114,.5), inset 0 1px 0 rgba(255,255,255,.35);
  opacity: 0; transform: translateY(14px) scale(.86); pointer-events: none;
  transition: opacity .3s ease, transform .46s var(--spring);
}
.dv-fab.on { opacity: 1; transform: none; pointer-events: auto; }
.dv-fab:active { transform: scale(.9); }
.dv-ring {
  width: 17px; height: 17px; border-radius: 50%;
  border: 2px solid rgba(255,255,255,.4); border-top-color: #fff;
  animation: dvSpin .78s linear infinite;
}

/* ============ 顶部雾 ============ */
.dv-fog {
  position: absolute; top: 0; left: 0; right: 0; height: 196px; z-index: 4;
  pointer-events: none; opacity: 0;
  background:
    linear-gradient(180deg, rgba(216,207,246,.98) 0%, rgba(216,207,246,.98) 104px,
                    rgba(219,206,243,.86) 136px, rgba(220,207,242,.42) 170px,
                    rgba(220,207,242,0) 196px);
  transition: opacity .28s ease;
}

/* ============ 动效 ============ */
@keyframes dvSheet {
  from { opacity: 0; transform: translate3d(0,44px,0); }
  to   { opacity: 1; transform: none; }
}
@keyframes dvUp {
  from { opacity: 0; transform: translate3d(0,12px,0); }
  to   { opacity: 1; transform: none; }
}
@keyframes dvPop {
  from { opacity: 0; transform: scale(.86); }
  to   { opacity: 1; transform: scale(1); }
}
/* 照片落进格子里：先虚化放大一点，再扎实落位 */
@keyframes dvShoot {
  0%   { opacity: 0; transform: scale(1.14); filter: blur(7px); }
  60%  { opacity: 1; filter: blur(0); }
  100% { opacity: 1; transform: scale(1); filter: blur(0); }
}
@keyframes dvBreath {
  0%,100% { transform: scale(1); box-shadow: 0 12px 20px -10px rgba(140,110,220,.7), inset 0 1px 0 rgba(255,255,255,.4); }
  50%     { transform: scale(1.06); box-shadow: 0 16px 26px -10px rgba(140,110,220,.5), inset 0 1px 0 rgba(255,255,255,.4); }
}
@keyframes dvSheen {
  to { left: 118%; }
}
@keyframes dvDrift1 {
  0%,100% { transform: translate3d(0,0,0) scale(1); }
  50%     { transform: translate3d(16px,10px,0) scale(1.1); }
}
@keyframes dvDrift2 {
  0%,100% { transform: translate3d(0,0,0) scale(1.04); }
  50%     { transform: translate3d(-18px,8px,0) scale(.92); }
}
@keyframes dvPulse {
  0%,100% { opacity: .32; transform: scale(.82); }
  50%     { opacity: 1; transform: scale(1); }
}
@keyframes dvSpin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .dv-sheet, .dv-tday, .dv-tcol b, .dv-tcol i, .dv-tr, .dv-photo,
  .dv-name, .dv-blk, .dv-submit, .dv-chip, .dv-pub, .dv-open, .dv-badge, .dv-frame { animation: none !important; }
  .dv-tg1, .dv-tg2, .dv-wdot, .dv-ring, .dv-oplus { animation: none !important; }
  .dv-deck, .dv-frame { transition: none !important; }
}
/* ---- 清空确认：从底部贴上来的 sheet ----
   满宽、只做上圆角、阴影极淡 —— 它是页面的一部分，不是飘在上面的另一层卡片。
   宽度必须跟手机壳走：fixed 容器默认铺满整个浏览器窗口，
   在桌面上会横跨全屏（按钮被拉成一整条），所以这里钳到 --phone-w 并居中。 */
.dc-wrap{
  position:fixed; top:0; bottom:0; left:0; right:0; margin:auto;
  width:var(--phone-w, 390px); height:var(--phone-h, 844px);
  max-width:100vw; max-height:100vh;
  z-index:10000;
  display:flex; align-items:flex-end; justify-content:center;
  padding:0;
  border-radius:52px; overflow:hidden;
}
@media (max-width:520px){
  .dc-wrap{ width:100%; height:100%; border-radius:0; }
}
.dc-mask{
  position:absolute; inset:0;
  background:rgba(74,40,58,.26);
  backdrop-filter:blur(10px) saturate(120%);
  -webkit-backdrop-filter:blur(10px) saturate(120%);
}
.dc-card{
  position:relative; width:100%;
  padding:8px 20px calc(20px + env(safe-area-inset-bottom, 0));
  border-radius:26px 26px 0 0;
  background:#fff;
  box-shadow:0 -6px 22px -16px rgba(150,60,110,.26);
  text-align:left;
}
.dc-grab{
  display:block; width:36px; height:4px; margin:0 auto 12px;
  border-radius:999px; background:rgba(185,125,155,.28);
}
.dc-t{
  margin:0 0 7px;
  font-size:18px; font-weight:800; letter-spacing:-.03em; color:#3A1C2C;
}
.dc-sub{
  margin:0 0 18px;
  font-size:13px; line-height:1.62; color:#8E7A88;
}
.dc-acts{ display:flex; gap:10px; }
/* 主视觉留给「取消」：手最顺的位置该是"别清"。
   「清空」用红字白底，够显眼但不诱导。 */
.dc-cancel{
  flex:1; height:50px; border-radius:15px;
  border:0; color:#fff;
  background:linear-gradient(180deg,#FF86AB 0%,#FF4E82 100%);
  font:inherit; font-size:15px; font-weight:800;
  cursor:pointer;
  box-shadow:
    0 12px 22px -14px rgba(255,78,130,.75),
    inset 0 1px 0 rgba(255,255,255,.4);
  transition:transform .2s cubic-bezier(.34,1.4,.64,1), filter .22s ease;
}
.dc-cancel:active{ transform:scale(.98); filter:brightness(.96); }
.dc-go{
  flex:1; height:50px; border-radius:15px;
  border:1px solid rgba(226,59,87,.34);
  background:#FFFFFF; color:#E23B57;
  font:inherit; font-size:15px; font-weight:700;
  cursor:pointer;
  box-shadow:none;
  transition:transform .2s cubic-bezier(.34,1.4,.64,1), background .22s ease, border-color .22s ease;
}
.dc-go:active{ transform:scale(.98); background:#FFF4F5; border-color:rgba(226,59,87,.5); }

.dc-enter-active .dc-card{ animation:dcUp .36s cubic-bezier(.16,1,.3,1) both; }
.dc-enter-active .dc-mask{ animation:dcFade .26s ease both; }
.dc-leave-active .dc-card{ animation:dcUp .24s cubic-bezier(.4,0,1,1) reverse both; }
.dc-leave-active .dc-mask{ animation:dcFade .24s ease reverse both; }
@keyframes dcUp{
  from{ transform:translateY(100%); }
  to{ transform:none; }
}
@keyframes dcFade{ from{ opacity:0; } to{ opacity:1; } }

@media (prefers-reduced-motion: reduce) {
  .dc-enter-active .dc-card, .dc-leave-active .dc-card,
  .dc-enter-active .dc-mask, .dc-leave-active .dc-mask { animation:none; }
  .dc-cancel, .dc-go{ transition:none; }
}
</style>
