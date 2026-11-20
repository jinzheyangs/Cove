<template>
<section class="view tree-view" :class="{ on: active, 'sheet-open': sheet }" data-view="tree" data-no-mask>
  <div class="bg">
    <div class="cloud cloud1"></div>
    <div class="cloud cloud2"></div>
    <div class="cloud cloud3"></div>
    <div class="ground"></div>
    <div class="grass"></div>
  </div>

  <div class="hud-title">秘密树</div>

  <div class="hud">
    <div class="hud__chip"><div class="hud__l">我的金币</div><div class="hud__v gold">{{ balance }}</div></div>
    <div class="hud__chip"><div class="hud__l">可摘取</div><div class="hud__v green">{{ canPick }}</div></div>
    <div class="hud__chip"><div class="hud__l">我藏的</div><div class="hud__v coral">{{ mineCount }}</div></div>
  </div>

  <div class="tree-stage" ref="stageRef">
    <!-- 整树 + 叶子一起摆：摆动只作用在这一个 DOM 容器上（纯合成，raster 一次），
         不再让 SVG 里的 1000 多个节点每帧重绘。 -->
    <div class="tree-body">
      <svg viewBox="0 0 390 700" preserveAspectRatio="xMidYMax meet">
        <defs>
          <linearGradient id="barkGrad" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stop-color="#9c7250"/><stop offset="55%" stop-color="#c49a70"/><stop offset="100%" stop-color="#b0845e"/>
          </linearGradient>
          <radialGradient id="g0" cx="34%" cy="30%"><stop offset="0%" stop-color="#8fe3c2"/><stop offset="100%" stop-color="#27a87d"/></radialGradient>
          <radialGradient id="goldLeaf" cx="34%" cy="30%"><stop offset="0%" stop-color="#ffe1a0"/><stop offset="100%" stop-color="#e8a01e"/></radialGradient>
          <radialGradient id="coralLeaf" cx="34%" cy="30%"><stop offset="0%" stop-color="#ff9dbb"/><stop offset="100%" stop-color="#ef2864"/></radialGradient>
        </defs>
        <ellipse cx="172" cy="688" rx="60" ry="8" fill="#2f6b22" opacity=".25"/>
        <g class="leafDotGroup">
          <circle v-for="(d,i) in leafDots" :key="'d'+i" class="leaf-dot"
            :cx="d.x.toFixed(1)" :cy="d.y.toFixed(1)" :r="d.r.toFixed(1)"
            :fill="d.shade < 0.5 ? '#9ec63a' : '#b8d94a'"/>
        </g>
        <g class="branchGroup">
          <line v-for="(b,i) in branches" :key="'b'+i" class="branch-line"
            :x1="b.x1.toFixed(1)" :y1="b.y1.toFixed(1)" :x2="b.x2.toFixed(1)" :y2="b.y2.toFixed(1)"
            :stroke="b.depth >= 3 ? '#6b4a30' : (b.depth >= 1 ? '#7d5a3c' : '#8f6a48')"
            :stroke-width="b.w.toFixed(1)" stroke-linecap="round"/>
        </g>
      </svg>
      <div class="leaf-layer">
        <div v-for="leaf in onTree" :key="leaf.id"
          class="leaf" :class="leafClass(leaf) + (flownIds.includes(leaf.id) ? ' leaf--flyin' : '')"
          :style="leafStyle(leaf)"
          @click="tapLeaf(leaf)">
          <span v-if="leafClass(leaf) === 'leaf--can'" class="leaf__halo"></span>
          <svg viewBox="-15 -12 30 24" style="width:100%">
            <path :fill="leafFill(leaf)" d="M-13.5 0C-10.5-7.2 3.2-9.4 13.8 0C3.2 9.4-10.5 7.2-13.5 0Z"/>
            <path d="M-11.8-1.2C-5-2.4 4.2-2 11.4-.6" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="1.1" stroke-linecap="round"/>
            <path d="M-11.5 0C-4.5-.5 4.5-.5 11.8 0" fill="none" stroke="rgba(255,255,255,.7)" stroke-width=".85" stroke-linecap="round"/>
            <path d="M-6 0l-2.6-3.2M-1 0l-2.4-3.6M4 0l-2-3.4M-6 0l-2.6 3.2M-1 0l-2.4 3.6M4 0l-2 3.4" fill="none" stroke="rgba(255,255,255,.32)" stroke-width=".6" stroke-linecap="round"/>
          </svg>
          <div v-if="leaf.mine" class="leaf__mine">我</div>
          <div class="leaf__tag">{{ leafTag(leaf) }}</div>
        </div>
      </div>
    </div>
    <div v-for="i in 6" :key="'m'+i" class="mote" :style="moteStyle(i)"></div>
  </div>

  <button class="write-fab" :class="{ 'write-fab--full': leafFull }" @click="openWrite">
    <svg class="fab-leaf" viewBox="0 0 150 70" preserveAspectRatio="none">
      <defs><linearGradient id="fabGrad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#8fd45a"/><stop offset="55%" stop-color="#4cae5f"/><stop offset="100%" stop-color="#2f8a52"/>
      </linearGradient></defs>
      <path d="M6 35C20 8 96 2 144 35C96 68 20 62 6 35Z" fill="url(#fabGrad)" stroke="rgba(255,255,255,.75)" stroke-width="2"/>
      <path d="M14 35C50 30 100 30 136 35" fill="none" stroke="rgba(255,255,255,.45)" stroke-width="1.4"/>
      <path d="M40 35l-10-12M66 35l-9-13M92 35l-8-12M40 35l-10 12M66 35l-9 13M92 35l-8 12" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1.1"/>
    </svg>
    <span class="fab-txt">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M12 2C7 7 4 11 4 15a8 8 0 0 0 16 0c0-4-3-8-8-13z" fill="#fff"/><path d="M12 8v9M12 17l-3-3M12 17l3-3" stroke="#3f8a54" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      {{ leafFull ? '树上放不下了' : '藏一片叶子' }}
    </span>
  </button>

  <div class="mask" :class="{ show: sheet }" @click="closeSheet"></div>

  <!-- 写叶子 -->
  <div class="sheet" :class="{ show: sheet === 'write' }">
    <div class="sheet__grip"></div>
    <h2>藏一片叶子</h2>
    <div class="sub">写下来，这片叶子就替你守着，等 TA 摘下</div>
    <div class="field"><label>秘密内容</label><textarea v-model="wContent" maxlength="5000" placeholder="只有摘下它的人能看到"></textarea></div>
    <div class="group-card">
      <div class="group-card__title">秘密等级</div>
      <div class="seg2">
        <button :class="{on: wLevel==='normal'}" @click="setLevel('normal')">普通心事</button>
        <button :class="{on: wLevel==='deep'}" @click="setLevel('deep')">深度秘密</button>
      </div>
    </div>
    <div class="group-card">
      <div class="group-card__title">摘取价格</div>
      <div class="chips">
        <button v-for="p in costPresets" :key="p" :class="{on: wCost===p}" @click="wCost=p">{{ p }}</button>
      </div>
      <div class="amount-wrap"><input v-model.number="wCost" inputmode="numeric"/><span class="unit">枚</span></div>
    </div>
    <div class="hint-row">TA 读完就销毁，只能看一次</div>
    <button class="cta-main coral" @click="submitWrite">挂到树上</button>
  </div>

  <!-- 摘取确认 -->
  <div class="sheet" :class="{ show: sheet === 'detail' }">
    <div class="sheet__grip"></div>
    <div class="detail-ic"><svg viewBox="-15 -12 30 24" style="width:42px"><path fill="url(#goldLeaf)" d="M-13.5 0C-10.5-7.2 3.2-9.4 13.8 0C3.2 9.4-10.5 7.2-13.5 0Z"/></svg></div>
    <h2>对方的一片叶子</h2>
    <div class="sub">摘下来才能看到内容，读完这片就销毁，只能看这一次</div>
    <div class="kvlist">
      <div class="kv"><span class="k">秘密等级</span><span class="level-badge" :class="cur.level">{{ cur.level === 'deep' ? '深度秘密' : '普通心事' }}</span></div>
      <div class="kv"><span class="k">摘取消耗</span><span class="v gold">{{ cur.cost }} 枚</span></div>
    </div>
    <div class="cta-row">
      <button class="cta-ghost" @click="closeSheet">留在这里</button>
      <button class="cta-main green" style="flex:1" @click="confirmPick">花 {{ cur.cost }} 枚摘取</button>
    </div>
  </div>

  <!-- 揭示 -->
  <div class="sheet" :class="{ show: sheet === 'reveal' }">
    <div class="sheet__grip"></div>
    <h2>叶子的秘密</h2>
    <div class="sub">{{ reveal.who }}</div>
    <div class="secret-reveal">
      <div class="qmark">“</div>
      <p>{{ reveal.content }}</p>
    </div>
    <button class="cta-main green" @click="closeSheet">收好这片叶子</button>
  </div>

  <!-- 我的叶子 -->
  <div class="sheet" :class="{ show: sheet === 'mine' }">
    <div class="sheet__grip"></div>
    <h2>我藏的叶子</h2>
    <div class="sub">对方花金币摘取后，金币会销毁</div>
    <div class="kvlist">
      <div class="kv"><span class="k">当前状态</span><span class="v">{{ mineStatus }}</span></div>
      <div class="kv"><span class="k">摘取价格</span><span class="v gold">{{ cur.cost }} 枚</span></div>
    </div>
    <div class="cta-row">
      <button class="cta-ghost" @click="closeSheet">返回</button>
      <button class="cta-ghost danger" v-if="cur.status === 'active'" @click="destroySecret">销毁叶子</button>
    </div>
  </div>

  <div class="toast" :class="{ show: toastMsg }">{{ toastMsg }}</div>
</section>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import * as api from '../api/secrets.js';
import { getBalance } from '../api/coins.js';

const props = defineProps({ active: Boolean });

/* ---- 确定性随机，保证每次树形一致 ---- */
function mulberry32(seed){ return function(){
  seed |= 0; seed = seed + 0x6D2B79F5 | 0;
  let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296;
};}
const rnd = mulberry32(20261112);

/* ---- 递归生成树枝 + 枝头新叶 ---- */
const branches = [];
const leafDots = [];
function grow(x, y, ang, len, w, depth){
  const x2 = x + Math.cos(ang)*len, y2 = y + Math.sin(ang)*len;
  branches.push({x1:x, y1:y, x2:x2, y2:y2, w:w, depth:depth});
  const lc = depth<=0 ? 6 : (depth===1 ? 3 : (depth===2 ? 2 : 0));
  for(let k=0;k<lc;k++) leafDots.push({x:x2+(rnd()-.5)*22, y:y2+(rnd()-.5)*22, r:3.5+rnd()*4.5, shade:rnd()});
  if(depth<=0) return;
  if(depth===5){
    grow(x2,y2,ang-0.28,len*0.95,w*0.78,depth-1);
    grow(x2,y2,ang+0.28,len*0.95,w*0.78,depth-1);
    return;
  }
  const n = 2 + Math.floor(rnd()*2);
  for(let i=0;i<n;i++) grow(x2,y2,ang+(rnd()-.5)*1.5,len*(0.55+rnd()*0.35),w*0.66,depth-1);
}
grow(172, 685, -Math.PI/2, 165, 28, 5);

/* 秘密锚点：
   树枝是随机长出来的，叶点会伸出画布两侧（x 甚至到 -110 或 540）。
   按 x 百分比铺 DOM 叶子会把它们送到屏幕外，所以在树冠上预设一排位置，
   每个位置吸附最近的枝头叶点 —— 而且是「两两相距够远」的枝头，否则两片
   叶子会叠在同一个点上（旧版兜底会复用已经占过的点，实测就会重叠）。 */
/* 秘密锚点：
   树枝是随机长出来的，叶点会伸出画布两侧（x 甚至到 -110 或 540）。
   叶子只能挂在真实的枝头叶点上，否则会飘在枝叶之间的空气里；
   但光「在某个叶点上」不够 —— 稀疏处的那个点周围是空的，叶子看着还是悬着。
   所以先算每个叶点的局部密度（半径 24 内还有几个叶点），
   再从「叶簇最密」的一枝开始，用最远点法挑，既贴住成簇的枝叶又铺得开；
   铺不开就少挂几片（容量随之变小）。 */
const anchors = (function(){
  const cand = leafDots
    .filter(d => d.x > 70 && d.x < 332 && d.y > 145 && d.y < 300)
    .map(d => {
      let n = 0;
      for (const o of leafDots){
        const dx = o.x - d.x, dy = o.y - d.y;
        if (dx * dx + dy * dy < 24 * 24) n++;
      }
      return {x:d.x, y:d.y, dens:n};
    });
  if (!cand.length) return [{x:195, y:210, rot:0, wi:0}];
  const GAP = 54;              // viewBox 单位，换算到屏幕约 37px，正好放得下一片叶子
  const CAP = 6;
  const seed = cand.reduce((a, b) => {
    const sa = a.dens - (Math.abs(a.x - 195) + Math.abs(a.y - 196)) / 40;
    const sb = b.dens - (Math.abs(b.x - 195) + Math.abs(b.y - 196)) / 40;
    return sb > sa ? b : a;
  });
  const picked = [seed];
  while (picked.length < CAP){
    let best = null, bs = -1e9;
    for (const d of cand){
      let minD = Infinity;
      for (const p of picked){
        const dd = Math.hypot(d.x - p.x, d.y - p.y);
        if (dd < minD) minD = dd;
      }
      if (minD < GAP) continue;
      const sc = minD + d.dens * 6;      // 又远、又长在密处
      if (sc > bs){ bs = sc; best = d; }
    }
    if (!best) break;          // 剩下的枝头都离得太近，宁可少挂一片
    picked.push(best);
  }
  return picked.map((p, i) => ({x:p.x, y:p.y, rot:(i % 3 - 1) * 9 + (rnd()-.5)*6, wi:i}));
})();
/* 树冠上就这么多枝头能各挂一片叶子，再多就只能叠在一起了 —— 满了就收工 */
const LEAF_CAP = anchors.length;
/* 锚点跟着叶子 id 走，不跟下标走：
   以前用 i 索引锚点，销毁一片后列表变短、后面每片都前移一位，
   整树的叶子集体跳到别的枝头，看着像"点了这片、消失的是另一片"。
   现在每片叶子认一个固定锚点，谁走了只空出它自己那格，别人不动。 */
const anchorMap = ref({});

function syncAnchors(){
  const used = new Set();
  const keep = {};
  const live = onTree.value;
  for (const s of live){
    const a = anchorMap.value[s.id];
    if (a !== undefined && a < anchors.length && !used.has(a)) { keep[s.id] = a; used.add(a); }
  }
  for (const s of live){
    if (keep[s.id] !== undefined) continue;
    let a = 0;
    while (used.has(a) && a < anchors.length) a++;
    keep[s.id] = a; used.add(a);
  }
  anchorMap.value = keep;
}

/* ---- 状态 ---- */
const secrets = ref([]);
const balance = ref(0);
const sheet = ref(null);
const cur = ref({});
const flyId = ref(null);
const flyFrom = ref(null);   // 按钮中心 → 新叶子落点的偏移，交给 flyin 当起点
/* 已经飞上树的叶子一直留着 flyin 类：动画 forwards 停在终态，
   如果到时把它去掉，.leaf 的入场动画会重新从头播一遍（叶子当众重生一下） */
const flownIds = ref([]);
const toastMsg = ref('');
const wContent = ref('');
const wLevel = ref('normal');
const wCost = ref(10);
const reveal = ref({content:'', who:''});
let toastTimer = null;

/* ---- 叶子坐标系：跟 <svg> 的 preserveAspectRatio="xMidYMax meet" 对齐
   SVG 按宽度/高度里较小的比例整体缩放，水平居中、底边贴齐；
   DOM 叶子是绝对定位的，只能用同样的换算把 viewBox 坐标搬到屏幕上，
   否则树叶和枝头会各走各的（叶子会飞出画布）。 ---- */
const stageRef = ref(null);
const stageBox = ref({ w: 390, h: 480 });
const fit = computed(() => {
  const { w, h } = stageBox.value;
  const s = Math.min(w / 390, h / 700) || 1;
  return { s, ox: (w - 390 * s) / 2, oy: h - 700 * s };
});
function measureStage(){
  const el = stageRef.value;
  if (!el) return;
  const w = el.clientWidth, h = el.clientHeight;
  if (w && h && (w !== stageBox.value.w || h !== stageBox.value.h)) stageBox.value = { w, h };
}

const costPreset = { normal:[10,20,30,60], deep:[30,50,80,120] };
const costPresets = computed(() => costPreset[wLevel.value]);

const onTree = computed(() => secrets.value.filter(s => s.status !== 'destroyed'));
watch(onTree, syncAnchors, { immediate: true });
const leafFull = computed(() => onTree.value.length >= LEAF_CAP);
const canPick = computed(() => secrets.value.filter(s => !s.mine && s.status === 'active' && !s.viewed).length);
const mineCount = computed(() => secrets.value.filter(s => s.mine && s.status !== 'destroyed').length);
const mineStatus = computed(() => {
  const s = cur.value;
  if(s.status === 'destroyed') return s.viewed ? '已被摘走（已销毁）' : '已销毁';
  return '等待摘取';
});

/* ---- 叶子视觉 ---- */
function leafFill(s){
  if(s.mine) return 'url(#coralLeaf)';
  if(s.viewed) return 'url(#g0)';
  return 'url(#goldLeaf)';
}
function leafClass(s){
  if(s.mine) return 'leaf--mine2';
  if(s.viewed) return 'leaf--read';
  return 'leaf--can';
}
function leafTag(s){
  if(s.mine) return s.status === 'destroyed' ? (s.viewed ? '已被摘走' : '已销毁') : '等待摘取';
  if(s.viewed) return '已读';
  return s.cost + ' 枚';
}
function leafStyle(s){
  const ai = anchorMap.value[s.id] ?? 0;
  const a = anchors[ai % anchors.length];
  // 叶子比锚点多时，第二圈轻轻错开，避免完全叠成一片
  const ring = Math.floor(ai / anchors.length);
  const jx = ring ? (ring % 2 ? -11 : 11) : 0;
  const jy = ring ? -13 * Math.ceil(ring / 2) : 0;
  const { s: k, ox, oy } = fit.value;
  const st = {
    left: (ox + (a.x + jx) * k) + 'px',
    top: (oy + (a.y + jy) * k) + 'px',
    width: Math.round(38 * Math.max(k, .82)) + 'px',
    '--rot': a.rot + 'deg',
    '--li': (ai * .07).toFixed(2) + 's',
  };
  if (flyFrom.value && s.id === flyId.value) {
    st['--fx'] = flyFrom.value.fx + 'px';
    st['--fy'] = flyFrom.value.fy + 'px';
  }
  return st;
}
function moteStyle(i){
  return { left: (8 + rnd()*84) + '%', '--dur': (9 + rnd()*6) + 's', animationDelay: (rnd()*10) + 's' };
}

/* ---- 交互 ---- */
function norm(item){
  return {
    id: item.id,
    mine: item.authored_by_me,
    cost: item.cost_coins,
    status: item.status,
    viewed: item.viewed,
    level: item.level,
    content: '',
  };
}
async function load(silent = false){
  try {
    const [av, mine, bal] = await Promise.all([api.listAvailable(), api.listMine(), getBalance()]);
    const map = new Map();
    [...av, ...mine].forEach(it => map.set(it.id, norm(it)));
    const next = [...map.values()];
    /* 静默刷新时，树没变就一个字段都不动：
       叶子位置是按数组序号算的，无意义地换一遍数组会让整树叶子瞬移 */
    if (silent && sameTree(secrets.value, next)) {
      balance.value = bal?.balance ?? bal ?? 0;
      return;
    }
    secrets.value = next;
    balance.value = bal?.balance ?? bal ?? 0;
  } catch(e){ toast(e.message || '加载失败'); }
}

function sameTree(a, b){
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (a[i].id !== b[i].id || a[i].status !== b[i].status || a[i].viewed !== b[i].viewed) return false;
  }
  return true;
}

function openWrite(){
  if (leafFull.value){ toast('树上已经放不下了，等 TA 摘走一片再藏'); return; }
  wContent.value=''; setLevel('normal'); sheet.value='write';
}
function setLevel(lv){ wLevel.value = lv; wCost.value = costPreset[lv][0]; }

async function submitWrite(){
  const content = wContent.value.trim();
  if(!content){ toast('先写点什么吧'); return; }
  const cost = wCost.value;
  if(!cost || cost < 1){ toast('给叶子定个价格吧'); return; }
  try {
    const created = await api.publishSecret({
      content, level: wLevel.value, cost_coins: cost,
    });
    secrets.value.push(norm(created));
    sheet.value = null;
    /* 先把这片叶子摆到枝头上（此时还没开始飞），量出按钮中心与它的差，
       再打开 flyin，叶子才会真的从按钮那飞过来，而不是凭空出现在树里 */
    await nextTick();
    const stage = stageRef.value;
    const fab = document.querySelector('.write-fab');
    const leafEl = stage && stage.querySelector('.leaf-layer .leaf:last-child');
    if (stage && fab && leafEl) {
      const sr = stage.getBoundingClientRect();
      const fr = fab.getBoundingClientRect();
      flyFrom.value = {
        fx: Math.round(fr.left + fr.width / 2 - sr.left - leafEl.offsetLeft),
        fy: Math.round(fr.top + fr.height / 2 - sr.top - leafEl.offsetTop),
      };
    }
    flyId.value = created.id;
    flownIds.value = [...flownIds.value, created.id];
    setTimeout(() => { flyId.value = null; flyFrom.value = null; }, 1500);
    toast('叶子已挂上树');
  } catch(e){ toast(e.message || '发布失败'); }
}

function tapLeaf(s){
  cur.value = s;
  if(s.mine){ sheet.value='mine'; return; }
  if(s.viewed){ openReveal(s); return; }
  sheet.value='detail';
}

async function confirmPick(){
  const s = cur.value;
  try {
    const detail = await api.unlockSecret(s.id);
    s.viewed = true;
    s.status = detail.status || 'destroyed';
    balance.value -= s.cost;
    sheet.value = null;
    openReveal({...s, content: detail.content});
  } catch(e){ toast(e.message || '摘取失败'); }
}
function openReveal(s){
  reveal.value = { content: s.content || '（这片叶子已经销毁了）', who: s.mine ? '你写下的内容' : '你摘下的秘密' };
  sheet.value = 'reveal';
}

async function destroySecret(){
  try {
    await api.destroySecret(cur.value.id);
    cur.value.status = 'destroyed';
    sheet.value = null;
    toast('叶子已销毁');
  } catch(e){ toast(e.message || '销毁失败'); }
}

function closeSheet(){ sheet.value = null; }

function toast(msg){
  toastMsg.value = msg;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastMsg.value = '', 1800);
}

/* 树上要能看见对方刚藏的那片叶子：切回这一页、或每 20 秒的静默广播时重拉一次。
   2 秒节流只为挡快速来回切页，不挡真正的「切回来」 */
let lastSyncAt = 0;
function refreshTree(){
  if (Date.now() - lastSyncAt < 2000) return;
  lastSyncAt = Date.now();
  load(true);
}
function onGlobalSync(ev){
  if (!props.active) return;
  const v = ev?.detail?.view;
  if (v && v !== 'tree') return;
  refreshTree();
}

onMounted(() => {
  measureStage();
  requestAnimationFrame(measureStage);
  window.addEventListener('resize', measureStage);
  window.addEventListener('cove:sync', onGlobalSync);
  load();
  lastSyncAt = Date.now();
});
onBeforeUnmount(() => {
  window.removeEventListener('resize', measureStage);
  window.removeEventListener('cove:sync', onGlobalSync);
});
// 视图从隐藏切回来时尺寸才可用，切进来的那一刻重新量一次，顺便把树上的叶子对一遍
watch(() => props.active, (v) => {
  if (!v) return;
  requestAnimationFrame(() => { measureStage(); setTimeout(measureStage, 240); });
  refreshTree();
});
</script>

<style scoped>
.tree-view{overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:#243029;padding:0 !important;}
.tree-view > *:not(.tree-stage){animation:none !important;}
.bg{position:absolute;inset:0;background:none;}
.cloud{position:absolute;background:#fff;border-radius:50%;filter:blur(2px);opacity:.9;pointer-events:none;}
.cloud::after{content:"";position:absolute;background:#fff;border-radius:50%;}
.cloud1{top:70px;left:30px;width:70px;height:26px;}
.cloud1::after{width:36px;height:36px;top:-16px;left:12px;}
.cloud2{top:120px;right:30px;width:80px;height:28px;opacity:.8;}
.cloud2::after{width:40px;height:40px;top:-18px;right:14px;}
.cloud3{top:180px;left:90px;width:50px;height:18px;opacity:.6;}
.ground{position:absolute;left:0;right:0;bottom:68px;height:110px;background:none;}
.grass{position:absolute;bottom:150px;left:0;right:0;height:40px;opacity:.5;pointer-events:none;background:none;}

.hud-title{position:absolute;top:60px;left:0;right:0;text-align:center;font-size:20px;font-weight:800;color:#243029 !important;letter-spacing:1px;z-index:20;}
.hud{position:absolute;top:104px;left:14px;right:14px;display:flex;gap:10px;z-index:20;}
/* HUD 原来用 backdrop-filter 实时磨砂：它下面正好是每帧都在变化的玻璃画布和摆动的树，
   等于每帧为三个 chip 各重采样一次背景，手机上极重。改成接近实心的白 + 细高光：
   透明度留太高（.78）时天上的白云会透到卡片里，看着像没擦干净，.94 还留着一点通透。 */
.hud__chip{flex:1;background:rgba(255,255,255,.94);border-radius:16px;padding:10px 12px;box-shadow:0 4px 14px rgba(40,60,48,.08),inset 0 0 0 .5px rgba(255,255,255,.9);}
.hud__l{font-size:11px;color:#93a298 !important;margin-bottom:4px;}
.hud__v{font-size:22px;font-weight:800;line-height:1;}
.hud__v.gold{color:#d98200 !important;}
.hud__v.coral{color:#e02060 !important;}
.hud__v.green{color:#0e8a5e !important;}

.tree-stage{position:absolute;left:0;right:0;top:224px;bottom:138px;z-index:5;}
/* 全局 .view.on > * 会给这个直接子元素套一层带 blur(6px) 的 rise：
   对 1000 多个节点的整树做模糊滤镜入场，首帧就要命。这里换成本视图自己的纯淡入。
   特异性要压过 .view.on > *，所以带上 .tree-view.on。 */
.tree-view.on > .tree-stage{animation:stageIn .85s cubic-bezier(.16,1,.3,1) both;}
/* 整树的摆动挂在 DOM 容器上：内容 raster 一次，之后每帧只做合成，
   而挂在 SVG 组里时（.branchGroup/.leafDotGroup）1000 多个节点会逐帧重绘。 */
.tree-body{position:absolute;inset:0;transform-origin:50% 100%;will-change:transform;
  animation:treeSway 6s ease-in-out infinite;}
.tree-stage svg{width:100%;height:100%;display:block;}
/* 枝干与叶点不再各自跑入场动画（835 + 181 个同时动会把首帧拖死），改由整树一次淡入 */
.branch-line{opacity:1;}
.leaf-dot{opacity:1;}
.leaf-layer{position:absolute;inset:0;}
/* 叶子定位靠 translate(-50%,-50%) 把中心压到枝头锚点上。
   入场动画必须把这个位移一起写进每一帧，否则动画的终态 transform 会把它吃掉，
   整片叶子就往右下偏半个叶子大小（app.css 里还有一份 .leaf 的 leafIn/float）。
   摆动只留一层：叶身的 sway 和整树的 treeSway 用同一个 6s 周期，
   一阵风过去整棵树和叶子一起摆，不会各晃各的。 */
.leaf{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;cursor:pointer;
  opacity:0;
  animation:leafPop .62s var(--spring) var(--li, 0s) forwards;}
@keyframes leafPop{
  from{opacity:0;transform:translate(-50%,-50%) scale(.5);}
  60%{opacity:1;}
  to{opacity:1;transform:translate(-50%,-50%) scale(1);}
}
.leaf svg{transform-origin:50% 80%;animation:sway 6s ease-in-out infinite;will-change:transform;}
/* 可摘叶子的呼吸光：用一层径向渐变的 opacity/scale（纯合成），
   不再 animate filter:drop-shadow —— 那会让浏览器每帧重建阴影，手机上极卡。 */
.leaf__halo{position:absolute;left:50%;top:13px;width:52px;height:30px;margin:-15px 0 0 -26px;border-radius:50%;
  pointer-events:none;z-index:-1;
  background:radial-gradient(ellipse at 50% 50%,rgba(255,198,70,.28),rgba(255,198,70,.09) 56%,rgba(255,198,70,0) 72%);
  animation:halo 2.2s ease-in-out infinite;will-change:transform,opacity;}
.leaf--flyin{animation:flyin 1.4s cubic-bezier(.22,1,.36,1) forwards;}
.leaf__tag{margin-top:2px;font-size:10px;font-weight:800;line-height:1;padding:3px 7px;border-radius:20px;white-space:nowrap;}
.leaf__mine{position:absolute;top:-5px;right:-6px;width:15px;height:15px;border-radius:50%;background:#ff5987;color:#fff;font-size:9px;font-weight:800;display:grid;place-items:center;border:2px solid #fff;z-index:2;}
.leaf--can svg{animation:sway 6s ease-in-out infinite;}
.leaf--can .leaf__tag{background:#f4b23c;color:#fff;box-shadow:0 4px 10px rgba(224,150,23,.4);}
.leaf--mine2 .leaf__tag{background:#ffe9f0;color:#f02a66;}
.leaf--read{opacity:.85;}
.leaf--read .leaf__tag{background:#eef1ee;color:#93a298;}
.mote{position:absolute;bottom:0;width:7px;height:7px;border-radius:50%;background:radial-gradient(circle,#fff,rgba(255,236,170,.5));box-shadow:0 0 8px rgba(255,225,150,.8);animation:rise var(--dur,11s) linear infinite;opacity:0;z-index:6;pointer-events:none;}

.write-fab{position:absolute;right:14px;bottom:124px;z-index:25;width:158px;height:74px;border:0;background:transparent;padding:0;display:grid;place-items:center;filter:drop-shadow(0 12px 22px rgba(38,100,55,.42));}
.fab-leaf{position:absolute;inset:0;width:100%;height:100%;}
.fab-txt{position:relative;display:flex;align-items:center;gap:6px;color:#fff;font-size:14.5px;font-weight:800;letter-spacing:.3px;text-shadow:0 1px 3px rgba(20,70,40,.4);}
.write-fab:active{transform:scale(.94);}
.write-fab--full{filter:drop-shadow(0 8px 14px rgba(38,100,55,.22)) grayscale(.6) opacity(.7);cursor:default;}
.write-fab--full:active{transform:none;}

.mask{position:absolute;inset:0;background:rgba(28,38,32,.42);opacity:0;pointer-events:none;transition:opacity .35s ease;z-index:50;}
.mask.show{opacity:1;pointer-events:auto;}
.sheet{position:absolute;left:0;right:0;bottom:0;background:#fff;border-radius:30px 30px 0 0;padding:10px 22px 30px;max-height:84%;overflow-y:auto;transform:translateY(105%);opacity:1;transition:transform .48s cubic-bezier(.16,1,.3,1);z-index:51;}
.sheet.show{transform:translateY(0);}
.sheet::-webkit-scrollbar{display:none;}
.sheet__grip{width:38px;height:5px;border-radius:3px;background:#e2e7e1;margin:4px auto 14px;}
.sheet h2{font-size:19px;font-weight:800;text-align:center;}
.sheet .sub{font-size:12px;color:#93a298;text-align:center;margin:5px 0 18px;line-height:1.6;}
.hint-row{font-size:11.5px;color:#93a298;line-height:1.6;text-align:center;margin:-6px 0 16px;}
.field{margin-bottom:16px;}
.group-card{background:#fafcf9;border:1.5px solid #e6ece6;border-radius:18px;padding:14px 14px 12px;margin-bottom:16px;}
.group-card__title{font-size:12.5px;font-weight:700;color:#5a6b60;margin-bottom:11px;}
.group-card .seg2{margin-bottom:0;}
.group-card .chips{margin-bottom:10px;}
.group-card .amount-wrap{margin-bottom:0;}
.field.lbl{margin-bottom:10px;font-size:12.5px;font-weight:700;color:#5a6b60;}
.field label{display:block;font-size:12.5px;font-weight:700;color:#5a6b60;margin-bottom:8px;}
.field textarea{width:100%;border:1.5px solid #e6ece6;border-radius:16px;padding:13px 14px;font-size:14px;font-family:inherit;resize:none;outline:none;background:#fafcf9;min-height:100px;line-height:1.6;}
.field textarea:focus{border-color:#33c08f;}
.seg2{display:flex;background:#f1f4f0;border-radius:15px;padding:4px;gap:4px;margin-bottom:16px;}
.seg2 button{flex:1;border:0;background:transparent;border-radius:12px;padding:10px;font-size:13px;font-weight:700;color:#5a6b60;}
.seg2 button.on{background:#fff;color:#243029;box-shadow:0 3px 8px rgba(40,60,48,.08);}
.chips{display:flex;gap:8px;margin-bottom:10px;}
.chips button{flex:1;border:1.5px solid #e6ece6;background:#fafcf9;border-radius:13px;padding:10px 0;font-size:14px;font-weight:800;color:#5a6b60;}
.chips button.on{border-color:#f4b23c;background:#fdf3dd;color:#e09617;}
.amount-wrap{position:relative;margin-bottom:16px;}
.amount-wrap input{width:100%;border:1.5px solid #e6ece6;border-radius:16px;padding:13px 40px 13px 14px;font-size:15px;font-weight:800;outline:none;background:#fafcf9;}
.amount-wrap .unit{position:absolute;right:15px;top:50%;transform:translateY(-50%);font-size:13px;color:#93a298;font-weight:700;}
.cta-main{width:100%;border:0;border-radius:18px;padding:15px;font-size:15.5px;font-weight:800;color:#fff;}
.cta-main.green{background:linear-gradient(135deg,#3fce99,#159b6f);box-shadow:0 10px 22px rgba(21,155,111,.3);}
.cta-main.coral{background:linear-gradient(135deg,#ff5987,#f02a66);box-shadow:0 10px 22px rgba(240,42,102,.3);}
.cta-row{display:flex;gap:10px;}
.cta-ghost{flex:1;border:1.5px solid #e6ece6;background:#fff;border-radius:18px;padding:14px;font-size:14.5px;font-weight:800;color:#5a6b60;}
.cta-ghost.danger{color:#d63a52;border-color:#f6d4db;background:#fdf3f5;}
.detail-ic{width:64px;height:64px;border-radius:20px;margin:0 auto 12px;display:grid;place-items:center;background:#e3f6ee;}
.kvlist{background:#fafcf9;border-radius:18px;padding:4px 16px;margin-bottom:18px;}
.kv{display:flex;justify-content:space-between;align-items:center;padding:12px 0;font-size:13px;border-bottom:1px solid #e6ece6;}
.kv:last-child{border-bottom:0;}
.kv .k{color:#5a6b60;}
.kv .v{font-weight:800;}
.kv .v.gold{color:#e09617;}
.level-badge{font-size:11px;font-weight:800;padding:4px 10px;border-radius:20px;}
.level-badge.normal{background:#e3f6ee;color:#159b6f;}
.level-badge.deep{background:#ffe9f0;color:#f02a66;}
.secret-reveal{background:linear-gradient(160deg,#e3f6ee,#f4fbf8);border-radius:20px;padding:22px 20px;margin-bottom:18px;}
.secret-reveal .qmark{font-size:30px;color:#33c08f;line-height:1;}
.secret-reveal p{font-size:16px;line-height:1.8;margin-top:8px;color:#243029;}
.toast{position:absolute;left:50%;bottom:110px;transform:translateX(-50%) translateY(20px);background:rgba(42,48,44,.92);color:#fff;font-size:13px;font-weight:600;padding:12px 20px;border-radius:16px;opacity:0;pointer-events:none;transition:.3s ease;z-index:70;max-width:80%;text-align:center;}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}

@keyframes stageIn{from{opacity:0;transform:scale(.965);}to{opacity:1;transform:none;}}
@keyframes treeSway{0%,100%{transform:rotate(-.5deg);}50%{transform:rotate(.5deg);}}
@keyframes sway{0%,100%{transform:rotate(-3deg);}50%{transform:rotate(3.5deg);}}
@keyframes halo{0%,100%{opacity:.5;transform:scale(.94);}50%{opacity:1;transform:scale(1.06);}}
/* 从「藏一片叶子」那颗按钮飞上枝头：
   --fx / --fy 是按钮中心相对这片叶子落点的偏移（提交后按真实位置算出来），
   每一帧都用 calc(-50% + …) 保持同一个基准，叶子才不会在收尾时甩一下。 */
@keyframes flyin{
  0%{transform:translate(calc(-50% + var(--fx, 150px)), calc(-50% + var(--fy, 320px))) scale(.14) rotate(-96deg);opacity:0;filter:drop-shadow(0 0 0 rgba(255,220,120,0));}
  18%{opacity:1;transform:translate(calc(-50% + var(--fx, 150px) * .84), calc(-50% + var(--fy, 320px) * .82)) scale(1.12) rotate(-58deg);filter:drop-shadow(0 0 18px rgba(255,225,130,.95));}
  62%{transform:translate(calc(-50% + var(--fx, 150px) * .18), calc(-50% + var(--fy, 320px) * .2)) scale(1.06) rotate(-8deg);filter:drop-shadow(0 0 12px rgba(255,225,130,.7));opacity:1;}
  82%{transform:translate(calc(-50% - 5px), calc(-50% - 7px)) scale(1.03) rotate(calc(var(--rot, 0deg) + 5deg));filter:drop-shadow(0 0 7px rgba(255,225,130,.45));opacity:1;}
  92%{transform:translate(calc(-50% + 2px), calc(-50% + 3px)) scale(1.01) rotate(calc(var(--rot, 0deg) - 2deg));opacity:1;}
  100%{transform:translate(-50%,-50%) scale(1) rotate(var(--rot, 0deg));opacity:1;filter:drop-shadow(0 0 0 rgba(255,220,120,0));}
}
@keyframes rise{0%{transform:translateY(0);opacity:0;}12%{opacity:.9;}88%{opacity:.7;}100%{transform:translateY(-620px);opacity:0;}}
</style>
