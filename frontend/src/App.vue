<template>
  <div class="stage" ref="stage">
    <div class="phone" id="phone">
      <div class="screen" id="screen" :class="{ 'tree-mode': view === 'tree' }">
        <canvas id="gl"></canvas>

        <div class="ui" id="ui">
          <StatusBar />

          <TodayView :active="view === 'today'" />
          <DiaryView :active="view === 'diary'" />
          <TreeView :active="view === 'tree'" />
          <MeView :active="view === 'me'" @open="openDetail" />

          <DetailShell
            :active="!!detailKey && !detailClosing"
            :seq="detailSeq"
            :origin="detailOrigin"
            :title="detailTitle"
            :variant="detailVariant"
            @back="closeDetail"
          >
            <KeepAlive>
              <component :is="detailComponent" :key="detailKey" v-if="detailKey" />
            </KeepAlive>
          </DetailShell>

          <SimtaChatView :active="simtaChat" @back="closeSimta" />
          <MallView :active="mallChat" @back="closeMall" />

          <BottomNav :current="view" :hidden="navHidden" @select="openView" />

          <div class="topscrim" :class="{ 'on-diary': view === 'diary' }"></div>
          <div class="scrim" id="scrim"></div>

          <SheetHost :panel-key="panel" />

          <WelcomeScreen v-if="showLogin" :closing="closing" @enter="requestClose" />

          <!-- 「在一起的那天」全局只有一个入口界面，首页/起始日页/设置页都调它 -->
          <StartDateSheet />

          <!-- 进入时的几步引导：缺什么补什么，跳过的不会再问 -->
          <OnboardingFlow
            v-if="introOpen"
            :steps="introSteps"
            :prefill="introPrefill"
            @done="finishIntro"
          />
        </div>
      </div>
    </div>
  </div>

  <div class="hint" id="hint">向上滑开面板 · 玻璃会从底栏长出来</div>
  <pre class="dbg" id="dbg"></pre>
  <pre class="err" id="err"></pre>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, KeepAlive } from 'vue';
import { engine } from './glass/index.js';
import { tap } from './native.js';
import { VIEW_META } from './composables/useCove.js';
import { refreshUnread } from './composables/useUnread.js';
import { useSession } from './composables/useSession.js';
import { openStartDate } from './composables/useStartDate.js';
import StatusBar from './components/StatusBar.vue';
import BottomNav from './components/BottomNav.vue';
import SheetHost from './components/SheetHost.vue';
import WelcomeScreen from './components/WelcomeScreen.vue';
import OnboardingFlow from './components/OnboardingFlow.vue';
import { resolveIntro, markIntroDone } from './composables/useOnboarding.js';
import { diarySubPage } from './composables/useDiary.js';
import TodayView from './views/TodayView.vue';
import DiaryView from './views/DiaryView.vue';
import TreeView from './views/TreeView.vue';
import MeView from './views/MeView.vue';
import SimtaChatView from './views/SimtaChatView.vue';
import MallView from './views/MallView.vue';
import DetailShell from './views/DetailShell.vue';
import AnniversaryModule from './views/modules/AnniversaryModule.vue';
import TodoModule from './views/modules/TodoModule.vue';
import BillModule from './views/modules/BillModule.vue';
import SettingsModule from './views/modules/SettingsModule.vue';
import StartDateSheet from './components/StartDateSheet.vue';

const DETAILS = {
  anniversary: { title: '纪念日', component: AnniversaryModule },
  todo: { title: '共同清单', component: TodoModule },
  bill: { title: '恋爱账本', component: BillModule },
  settings: { title: '设置', component: SettingsModule },
};
/* 详情组件必须带 :key。KeepAlive 会把上一个详情的 vnode 复用给下一个，
   退出来再点另一个详情时抛 "__vnode of null"，渲染队列中断，
   展开动画的 watcher 跟着被跳过 —— 表现就是「点了没反应」。
   注意这条注释只能写在这儿：KeepAlive 里放模板注释会被当成第二个子节点而编译失败。 */
const detailKey = ref(null);
const detailClosing = ref(false);
/* 每次点入口都加一。同一个页面被反复点开时，active 可能一直是 true，
   壳就收不到「重新展开」的信号，看起来像点了没反应。 */
const detailSeq = ref(0);
/* 退出动画跑完才真正卸载内容的定时器；打开时要能提前清掉它 */
let closeTimer = 0;
/* 卸载改在浏览器空闲时做，并用 token 防止它误杀后打开的详情 */
let idleToken = 0;
const detailOrigin = ref(null);
const detailTitle = computed(() => DETAILS[detailKey.value]?.title || '');
const detailComponent = computed(() => DETAILS[detailKey.value]?.component || null);
/* 纪念日/清单走奶油视觉；账本走紫调账页；设置页走 iOS 分组灰底 */
const VARIANTS = { settings: 'ios', bill: 'bill', todo: 'todo', anniversary: 'anniv' };
const detailVariant = computed(() => {
  if (!detailKey.value) return 'paper';
  return VARIANTS[detailKey.value] || 'cream';
});

function openDetail(payload) {
  if (!payload || !DETAILS[payload.key]) return;
  tap();
  /* 上一次的关闭定时器要收掉：不然刚打开就会被它把 detailKey 清成 null */
  clearTimeout(closeTimer);
  idleToken += 1;
  detailClosing.value = false;
  detailOrigin.value = payload.rect || null;
  detailKey.value = payload.key;
  detailSeq.value += 1;
}
/* 退出时别立刻把内容卸掉：先让壳缩回去，缩完再销毁详情组件。
   以前是 detailKey 一置空、页面内容当场消失，剩下白卡在那儿缩 —— 看着就是「卡一下」。 */
function closeDetail() {
  if (!detailKey.value || detailClosing.value) return;
  detailClosing.value = true;
  clearTimeout(closeTimer);
  const tk = ++idleToken;
  closeTimer = setTimeout(() => {
    /* 卸载账本要几十毫秒，别卡在「首页刚回来、用户正要点东西」那一帧：
       丢到空闲回调里做（超时兜底 600ms）。 */
    const fin = () => {
      if (tk !== idleToken) return;
      detailKey.value = null;
      detailClosing.value = false;
    };
    if (window.requestIdleCallback) requestIdleCallback(fin, { timeout: 600 });
    else fin();
  }, 240);
}

const stage = ref(null);
const panel = ref(null);
const { showLogin, closing, startGuard, requestClose } = useSession();
// 退回登录页时一并关闭已打开的详情，避免登录页被详情盖住、状态残留
watch(showLogin, (open) => {
  if (open) detailKey.value = null;
});
const simtaChat = ref(false);
const mallChat = ref(false);

/* 进入时的引导 */
const introOpen = ref(false);
const introSteps = ref([]);
const introPrefill = ref({});

/* 走查参数会跳过引导，免得挡住截图（?noIntro 不再生效：它只该是一次性的调试开关，
   留在地址栏里会让人以为引导坏了） */
function debugJump() {
  return !!qs.get('login') || !!qs.get('detail') || !!qs.get('view') || qs.has('shot');
}

async function maybeShowIntro() {
  /* 登录页 / 配对屏开着时不叠引导，否则会盖在配对码上，做完还退回配对屏 */
  if (showLogin.value) return;
  const info = await resolveIntro();
  if (!info.couple) return;   // 还没配对：先绑上，进了主页再补资料
  if (!info.steps.length) return;
  introSteps.value = info.steps;
  introPrefill.value = info.prefill;
  introOpen.value = true;
}

function finishIntro() {
  markIntroDone();
  introOpen.value = false;
}

const qs = new URLSearchParams(location.search);
/* 设计走查：?login=1 直接停到登录页 */
if (qs.get('login')) showLogin.value = true;
/* 设计走查 / 直接分享：?detail=anniversary|todo|bill|settings 可以一进来就打开对应详情 */
if (qs.get('detail') && DETAILS[qs.get('detail')]) detailKey.value = qs.get('detail');
const view = ref(VIEW_META[qs.get('view')] ? qs.get('view') : 'today');

/* 日记的详情/发布是二级页，整屏都归内容，底栏滑下去让位 */
const navHidden = computed(() => view.value === 'diary' && diarySubPage.value !== 'list');

function openView(name) {
  if (!VIEW_META[name] || name === view.value) { engine.closeSheet(); return; }
  tap();
  view.value = name;
  engine.afterViewChange(name);
}

/* 两个人在两个窗口（或两台手机）里各写各的：切页时广播一次「静默重拉」，
   停在同一页时每 20 秒再来一次，对方刚写的东西不用手动刷浏览器就能看见。
   各页按自己的节奏接住 —— 秘密树只在切回来时刷新，
   免得正盯着树看的时候整排叶子跳位置。 */
const SYNC_EVERY = 20000;
let syncTimer = 0;
function broadcastSync(force = false) {
  /* 后台标签页不发请求：手机切走 / 锁屏后不该还在每 20 秒轮询一次后端 */
  if (!force && document.hidden) return;
  window.dispatchEvent(new CustomEvent('cove:sync', { detail: { view: view.value } }));
}
watch(view, () => broadcastSync(true));

/* 从后台切回来：立刻补一次，不用等下一个 20 秒 */
function onVisibleSync() {
  if (document.hidden) return;
  broadcastSync(true);
  refreshUnread();
}

/* 模拟Ta：从底部 sheet 改为独立全屏页（iOS push） */
function openSimta() {
  engine.closeSheet();
  simtaChat.value = true;
}

function closeSimta() {
  simtaChat.value = false;
}

/* 商城：独立全屏页（iOS push） */
function openMall() {
  engine.closeSheet();
  mallChat.value = true;
}

function closeMall() {
  mallChat.value = false;
}

function showWelcome() {
  engine.closeSheet();
  showLogin.value = true;
}

/* 点一次就够：卡片上的 data-sheet、面板里的 data-close 都在这里统一收口，
   这样视图与面板的标记能保持和设计稿一一对应，不必给每个按钮都绑 @click。 */
function onStageClick(e) {
  if (e.target.closest('[data-relogin]')) { showWelcome(); return; }
  const push = e.target.closest('[data-push]');
  if (push) {
    if (push.dataset.push === 'simta') openSimta();
    if (push.dataset.push === 'mall') openMall();
    /* 首页那张还没填起始日的卡：就地弹「在一起的那天」，不跳走，
       保存完卡片当场变成天数 */
    if (push.dataset.push === 'start') openStartDate();
    /* 首页的恋爱账本入口：跟「我们」页一样走详情页转场，起点用这张卡的位置 */
    if (push.dataset.push === 'bill') {
      const host = (stage.value || document.getElementById('screen') || document.body).getBoundingClientRect();
      const r = push.getBoundingClientRect();
      openDetail({ key: 'bill', rect: { x: r.x - host.x, y: r.y - host.y, w: r.width, h: r.height } });
    }
    return;
  }
  const trig = e.target.closest('[data-sheet]');
  if (trig) { engine.openSheet(trig.dataset.sheet); return; }
  if (e.target.closest('[data-close]')) engine.closeSheet();
}

onMounted(() => {
  engine.bind({
    onViewChange: (name) => { view.value = name; },
    onOpenSheet: (key) => { panel.value = key; },
  });
  engine.mount(stage.value);
  stage.value.addEventListener('click', onStageClick);

  // 截图 / 调试直达：?view=diary&sheet=coins
  if (qs.get('view') && VIEW_META[qs.get('view')]) { view.value = qs.get('view'); engine.afterViewChange(view.value); }
  if (qs.get('sheet')) {
    engine.openSheet(qs.get('sheet'));
    // openSheet 认不出的 key 会直接返回；只有真的开了才把几何推到打开态
    if (engine.state.cur) {
      engine.state.sheet = 1;
      engine.state.sheetT = 1;
    }
  }

  // 关系守卫：被解绑时自动退回登录页
  startGuard();
  if (qs.has('welcome')) showLogin.value = true;

  // 已登录的人：资料还缺什么就先走几步引导
  // （走查参数 ?login / ?detail / ?view 会跳过它，免得挡住截图）
  window.addEventListener('cove:auth', onAuthClosed);
  window.addEventListener('cove:notif', refreshUnread);
  document.addEventListener('visibilitychange', onVisibleSync);
  syncTimer = setInterval(() => {
    if (document.hidden) return;
    broadcastSync();
    refreshUnread();
  }, SYNC_EVERY);
  refreshUnread();
  if (!debugJump()) setTimeout(maybeShowIntro, 600);
});

/* 登录页 / 配对码页关掉那一刻 = 真正进了主页：
   引导放到这一步之后弹，注册 → 配对码 → 绑定 → 引导，顺序不会倒 */
function onAuthClosed() {
  setTimeout(() => {
    if (!debugJump()) maybeShowIntro();
  }, 700);
}

onBeforeUnmount(() => {
  stage.value?.removeEventListener('click', onStageClick);
  window.removeEventListener('cove:auth', onAuthClosed);
  window.removeEventListener('cove:notif', refreshUnread);
  document.removeEventListener('visibilitychange', onVisibleSync);
  if (syncTimer) clearInterval(syncTimer);
  engine.unmount();
});
</script>
