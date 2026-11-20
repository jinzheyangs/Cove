<template>
<section class="detail-shell" :class="[phase, 'v-' + variant]">
  <div class="ds-backdrop" @click="$emit('back')"></div>

  <div class="ds-card" ref="cardEl" :style="geom">
    <div class="detail-nav">
      <button class="detail-back" @click="$emit('back')">
        <svg width="9" height="16" viewBox="0 0 11 18" fill="none" aria-hidden="true">
          <path d="M9.5 1.5 2 9l7.5 7.5" stroke="currentColor" stroke-width="2.1"
                stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span class="detail-back__label">我们</span>
      </button>
      <h2 class="detail-title">{{ title }}</h2>
      <span class="detail-right"><slot name="actions" /></span>
    </div>

    <div class="detail-scroll" ref="scrollEl">
      <slot />
    </div>
  </div>
</section>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';

const props = defineProps({
  active: Boolean,
  /* 每点一次入口加一：同一个页面重复点开时 active 不变，靠它重放展开动画 */
  seq: { type: Number, default: 0 },
  origin: { type: Object, default: null },
  title: { type: String, default: '' },
  // paper：原来的纸张风（设置页还在用）；cream：全息奶油（纪念日 / 清单 / 账本）
  variant: { type: String, default: 'paper' },
});
defineEmits(['back']);

const phase = ref('idle');   // idle | from | open | close
const DURATION = 420;
const CLOSE_MS = 190;
const scrollEl = ref(null);
const cardEl = ref(null);
/* 展开 / 收起：卡片按全屏尺寸布局，等比缩放 + 高度裁剪两件事同时插值。
   只用 transform + clip-path（合成与遮罩），内容从头到尾都在画，不重排、不重算；
   等比缩放意味着文字只放大 8% 左右、不变形 —— 不需要再把内容藏起来。 */
const box = ref({ w: 0, h: 0 });
function measure() {
  const p = cardEl.value?.parentElement;
  if (p && p.clientWidth && p.clientHeight) box.value = { w: p.clientWidth, h: p.clientHeight };
}

/* 设计走查：?dscroll=NNN 直接把详情滚到某个位置（不影响正常使用） */
const walkScroll = Number(new URLSearchParams(location.search).get('dscroll') || 0);
watch(phase, (p) => {
  if (p !== 'open' || !walkScroll) return;
  setTimeout(() => { if (scrollEl.value) scrollEl.value.scrollTop = walkScroll; }, 260);
});

const geom = computed(() => {
  const o = props.origin;
  const BW = box.value.w || 390;
  const BH = box.value.h || 844;
  /* 退出不再做几何动画：保持全屏原地淡出，缩回去那套只在打开时用 */
  if (phase.value === 'open' || phase.value === 'close') {
    return { '--tx': '0px', '--ty': '0px', '--s': '1', '--cb': '0px', '--r': '0px' };
  }
  if (o) {
    /* 用宽度比做等比缩放：缩放后卡片宽度正好是缩略卡片的宽度，
       高度方向多出来的部分用 clip 裁掉，于是起点恰好是那张卡片的大小 */
    const s = Math.min(1, o.w / BW) || 1;
    const vis = BH * s;                       // 缩放后的可视高度
    const cb = Math.max(0, vis - o.h) / s;    // 要裁掉多少（卡片本地坐标）
    return {
      '--tx': `${o.x}px`,
      '--ty': `${o.y}px`,
      '--s': String(s),
      '--cb': `${cb}px`,
      '--r': '12px',
    };
  }
  // 无 origin 兜底：从屏幕中心展开
  const s = 0.9;
  return {
    '--tx': '24px', '--ty': '300px', '--s': String(s),
    '--cb': `${(BH * s - 240) / s}px`, '--r': '12px',
  };
});

function nextFrame(){
  return new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res)));
}

async function playOpen(){
  measure();
  phase.value = 'from';
  /* 两帧等的是「先画出起点、再过渡到全屏」；万一 rAF 被节流（切后台 / 隐藏窗口）
     就一直停在 from、内容还是 visibility:hidden —— 加个兜底自己进 open */
  const guard = setTimeout(() => { if (phase.value === 'from') phase.value = 'open'; }, 260);
  await nextFrame();
  clearTimeout(guard);
  phase.value = 'open';
}

watch(() => props.active, async (on) => {
  if (on) {
    await playOpen();
  } else if (phase.value === 'open' || phase.value === 'close') {
    phase.value = 'close';
    await nextTick();
    /* 退出只做一次淡出，200ms 就干净地落回首页 */
    setTimeout(() => { if (phase.value === 'close') phase.value = 'idle'; }, CLOSE_MS + 30);
  }
}, { flush: 'post', immediate: true });

/* 已经开着的页面上再点一次同一个入口：active 不会变，单独靠 seq 重放一次展开，
   否则界面停在原样，用户会以为点了没反应。
   只在「已经完全展开」时重放：刚打开那一次 active 已经负责了，别播两遍。 */
watch(() => props.seq, async () => {
  if (!props.active || phase.value !== 'open') return;
  await playOpen();
});
</script>

<style scoped>
.detail-shell{
  position:absolute; inset:0; z-index:40;
  visibility:hidden; pointer-events:none;
}
.detail-shell.from,.detail-shell.open,.detail-shell.close{ visibility:visible; }
/* from 阶段就给上点击：万一动画被打断停在首帧，返回键至少还点得动 */
.detail-shell.from,.detail-shell.open{ pointer-events:auto; }

.ds-backdrop{
  position:absolute; inset:0;
  background:rgba(27,27,24,.22);
  opacity:0; transition:opacity .4s ease;
}
.open .ds-backdrop{ opacity:1; }
.close .ds-backdrop{ transition:opacity .19s ease-out; }

/* 从缩略卡片长到全屏：等比缩放 + 高度裁剪同时插值。
   内容全程都在，所以没有「内容闪一下才出来」的断层；transform / clip-path
   都不改布局，卡片里的图表和列表一次都不用重排。 */
.ds-card{
  position:absolute; inset:0; overflow:hidden;
  background:#F9F8F6;
  border:1px solid #E6E5E0;
  transform-origin:0 0;
  transform:translate3d(var(--tx,0px), var(--ty,0px), 0) scale(var(--s,1));
  clip-path:inset(0 0 var(--cb,0px) 0 round var(--r,0px));
  transition:none;
  opacity:1;
  contain:layout paint;
}
.open .ds-card{
  /* 曲线别太陡：起步太猛的话头 60ms 就跑掉大半，看起来像「闪一下」而不是展开 */
  transition:transform .42s cubic-bezier(.25,.46,.45,.94),
             clip-path .42s cubic-bezier(.25,.46,.45,.94);
  border-color:transparent;
  will-change:transform, clip-path;
}
/* 退出就走默认：原地淡出，不缩、不裁，纯 opacity 合成 */
.close .ds-card{
  opacity:0;
  transition:opacity .19s ease-out;
}
/* 动画途中别做背景模糊：气泡按钮的 backdrop-filter 每帧都要重新采样一次背景，
   展开这 0.42s 里是纯浪费，最容易被看成「顿」 */
.from .detail-back, .close .detail-back{
  backdrop-filter:none; -webkit-backdrop-filter:none;
  background:rgba(255,255,255,.92);
}

/* 页头整体再让 8px：贴边太紧时，刘海 / 灵动岛下方会显得被压住 */
.detail-nav{
  position:absolute; top:calc(env(safe-area-inset-top,0px) + 8px); left:0; right:0;
  height:52px; z-index:7; display:flex; align-items:center; padding:0 14px;
}
/* 返回键：气泡圆按钮，只有箭头没有文字（和日记等二级页同一套） */
.detail-back{
  width:40px; height:40px; padding:0; flex:0 0 auto;
  border-radius:50%; display:grid; place-items:center;
  background:rgba(255,255,255,.78);
  backdrop-filter:blur(14px) saturate(160%);
  -webkit-backdrop-filter:blur(14px) saturate(160%);
  box-shadow:0 6px 16px -8px rgba(30,26,40,.35), inset 0 0 0 1px rgba(255,255,255,.72);
  color:#1B1B18; cursor:pointer;
  transition:transform .18s cubic-bezier(.34,1.4,.64,1), background .2s ease;
}
.detail-back svg{ width:10px; height:17px; }
.detail-back__label{ display:none; }
.detail-back:active{ transform:scale(.94); background:rgba(255,255,255,.94); opacity:1; }
.detail-title{
  position:absolute; left:50%; transform:translateX(-50%);
  margin:0; font-size:16px; font-weight:700; letter-spacing:-.01em; color:#1B1B18;
}
.detail-right{ margin-left:auto; display:flex; align-items:center; min-width:50px; justify-content:flex-end; }

.detail-scroll{
  position:absolute; top:calc(env(safe-area-inset-top,0px) + 60px); left:0; right:0; bottom:0;
  overflow-y:auto; overflow-x:hidden; -webkit-overflow-scrolling:touch;
  scrollbar-width:none; padding:6px 16px 40px;
}
/* 内容全程都在：等比缩放下文字只是跟着放大约 8%，不需要藏起来再淡入 */
.detail-scroll::-webkit-scrollbar{ display:none; }

/* 全息奶油：卡片底色换成奶油，去掉发丝边 */
.v-cream .ds-card{
  background:
    radial-gradient(120% 70% at 88% -10%, #FFE9F2 0%, rgba(255,233,242,0) 58%),
    radial-gradient(110% 60% at 4% 6%, #FFF2E4 0%, rgba(255,242,228,0) 56%),
    radial-gradient(120% 46% at 50% 112%, #E8FBF5 0%, rgba(232,251,245,0) 72%),
    radial-gradient(90% 30% at 6% 96%, #FBEEFF 0%, rgba(251,238,255,0) 70%),
    #FFF7F2;
  border-color:transparent;
  box-shadow:none;
}
.v-cream .ds-backdrop{ background:rgba(60,30,60,.26); }
.v-cream .detail-nav{ background:linear-gradient(180deg, rgba(255,247,242,.96) 0%, rgba(255,247,242,.82) 68%, rgba(255,247,242,0) 100%); }
.v-cream .detail-title{ color:#2C1B2E; }
.v-cream .detail-back{ color:#6A5570; }
.v-cream .detail-scroll{ padding:8px 16px 34px; }

/* 账本：薰衣草紫到淡蓝的浅底，白卡浮在上面 */
.v-bill .ds-card{
  background:
    radial-gradient(90% 52% at 92% -8%, #E7E2FF 0%, rgba(231,226,255,0) 62%),
    radial-gradient(86% 48% at -6% 10%, #E3EBFF 0%, rgba(227,235,255,0) 66%),
    radial-gradient(120% 52% at 50% 112%, #E6F1FF 0%, rgba(230,241,255,0) 72%),
    #F0F1FB;
  border-color:transparent;
  box-shadow:none;
}
.v-bill .ds-backdrop{ background:rgba(40,40,90,.26); }
.v-bill .detail-nav{
  background:linear-gradient(180deg, rgba(240,241,251,.97) 0%, rgba(240,241,251,.84) 68%, rgba(240,241,251,0) 100%);
}
.v-bill .detail-title{ color:#242438; font-size:17px; font-weight:750; letter-spacing:-.02em; }
.v-bill .detail-back{ color:#242438; }
.v-bill .detail-scroll{ padding:6px 16px 36px; }

/* 共同清单：浅青底（取自共享单车稿），白卡浮在上面 */
.v-todo .ds-card{
  background:
    radial-gradient(95% 55% at 92% -8%, #C7E8E6 0%, rgba(199,232,230,0) 62%),
    radial-gradient(85% 48% at -4% 6%, #B6E1DE 0%, rgba(182,225,222,0) 64%),
    radial-gradient(120% 50% at 50% 110%, #E8F5F3 0%, rgba(232,245,243,0) 72%),
    #A9D8D8;
  border-color:transparent;
  box-shadow:none;
}
.v-todo .ds-backdrop{ background:rgba(28,64,64,.28); }
.v-todo .detail-nav{
  background:linear-gradient(180deg, rgba(169,216,216,.96) 0%, rgba(169,216,216,.84) 66%, rgba(169,216,216,0) 100%);
}
.v-todo .detail-title{ color:#22403E; font-size:17px; font-weight:750; letter-spacing:-.02em; }
.v-todo .detail-back{ color:#22403E; }
.v-todo .detail-scroll{ padding:6px 16px 36px; }

/* 纪念日：浅蓝白底（取自 NoSleep 稿），深蓝灰标题 */
.v-anniv .ds-card{
  background:
    radial-gradient(80% 42% at 90% -8%, #E4E7F7 0%, rgba(228,231,247,0) 62%),
    radial-gradient(70% 40% at -4% 6%, #EEF0FA 0%, rgba(238,240,250,0) 66%),
    #F0F2FB;
  border-color:transparent;
  box-shadow:none;
}
.v-anniv .ds-backdrop{ background:rgba(30,34,48,.3); }
.v-anniv .detail-nav{
  background:linear-gradient(180deg, rgba(240,242,251,.97) 0%, rgba(240,242,251,.85) 68%, rgba(240,242,251,0) 100%);
}
.v-anniv .detail-title{ color:#3A4152; font-size:17px; font-weight:600; letter-spacing:-.01em; }
.v-anniv .detail-back{ color:#3A4152; }
.v-anniv .detail-scroll{ padding:6px 16px 36px; }

/* 黑白稿：底色哑光浅灰，导航条同色渐隐，标题与返回键都是近黑 */
.v-ios .ds-card{ background:#F4F4F6; border-color:transparent; }
.v-ios .detail-nav{
  background:linear-gradient(180deg, rgba(244,244,246,.98) 0%, rgba(244,244,246,.86) 70%, rgba(244,244,246,0) 100%);
}
.v-ios .detail-title{ color:#111114; font-size:17px; font-weight:700; letter-spacing:-.02em; }
.v-ios .detail-back{ color:#111114; }
.v-ios .detail-scroll{ padding:6px 0 0; }
</style>
