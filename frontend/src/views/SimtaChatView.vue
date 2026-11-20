<template>
<section ref="chatRoot" class="simta-chat" :class="{ on: active }" data-view="simta-chat">
  <StatusBar />

  <!-- 顶部导航（iOS push 风格） -->
  <div class="nav">
    <button class="nav__back" @click="goBack">
      <svg width="11" height="18" viewBox="0 0 11 18" fill="none"><path d="M9.5 1.5L2 9l7.5 7.5" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" /></svg>
      今天
    </button>
    <div class="nav__center">
      <span class="nav__title">模拟 Ta</span>
      <span class="nav__sub">TA 的数字分身</span>
    </div>
    <button class="nav__info" title="授权与设置" @click="panelOpen = true">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8" /><circle cx="12" cy="8.4" r="1.25" fill="currentColor" /><path d="M12 11.4v4.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></svg>
    </button>
  </div>

  <!-- 授权面板：谁都能随时开、随时撤，撤了立刻停 -->
  <Teleport to="body">
    <Transition name="au">
      <div v-if="panelOpen" class="au-wrap">
        <div class="au-mask" @click="panelOpen = false"></div>
        <section class="au-card">
          <span class="au-grab" aria-hidden="true"></span>
          <h3 class="au-t">模拟 Ta 的授权</h3>
          <p class="au-sub">只有你们都授权，分身才会说话；任何一方撤销，下一次就立刻停。</p>

          <div class="au-state">
            <span class="au-row">
              <i class="au-av au-av--me">我</i>
              <b>我</b>
              <em :class="{ on: mine }">{{ mine ? '已授权' : '未授权' }}</em>
            </span>
            <span class="au-row">
              <i class="au-av">TA</i>
              <b>TA</b>
              <em :class="{ on: theirs }">{{ theirs ? '已授权' : '还没授权' }}</em>
            </span>
          </div>

          <p class="au-hint">
            {{ mine && theirs
              ? '双方都授权了，可以开始聊。'
              : (mine ? '你已经授权了，等 TA 也授权之后就能开始。' : '授权后，我会用你俩的聊天和记录来学 TA 的语气，只在这个页面里用。') }}
          </p>

          <p v-if="consentErr" class="au-err">{{ consentErr }}</p>

          <div class="au-acts">
            <button
              class="au-main" :class="{ revoke: mine }"
              type="button" :disabled="consenting" @click="toggleConsent"
            >{{ mine ? '撤销我的授权' : '授权 Ta 用我的数据模拟我' }}</button>
            <button class="au-close" type="button" @click="panelOpen = false">关闭</button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>

  <!-- 消息流（独立滚动） -->
  <div class="chat" ref="chatEl">
    <div class="chat__time">{{ timeLabel }}</div>

    <div class="msg-list">
      <!-- 还没有任何消息：说清楚这里是干什么的，别留一整屏空白 -->
      <div v-if="!messages.length" class="empty">
        <i class="empty__ico" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4.6 11.4a7.4 7.4 0 0 1 14.8 0c0 4.4-3.4 6.4-3.4 6.4l-1.6 3-2.4-3H4.6Z" />
            <path d="M9.4 10.6h.01M14.6 10.6h.01" stroke-width="2.4" />
          </svg>
        </i>
        <b>分身还没开口</b>
        <span>{{ bothOn ? '说第一句话，它会按 TA 的语气回你' : '它不是本人 —— 只是用你们的记录学出来的 TA' }}</span>
      </div>
      <template v-for="m in messages" :key="m.id">
        <div v-if="m.role === 'sys'" class="msg--sys">{{ m.text }}</div>
        <div v-else class="msg" :class="m.role === 'ta' ? 'msg--ta' : 'msg--me'">
          <div v-if="m.role === 'ta'" class="msg__av">屿</div>
          <div class="bubble">
            {{ m.text }}<span v-if="m.streaming" class="cursor"></span>
          </div>
        </div>
        <div v-if="m.disc" class="disc">{{ DISCLAIMER }}</div>
      </template>
    </div>

    <!-- 写操作不会自己执行：后端把它挂起成「待确认」，这里必须给一个确认口，
         否则说「帮我记一笔」之后界面什么都不出，看着像没反应 -->
    <div v-if="pendingConfirm" class="cfm">
      <div class="cfm__t">
        <b>{{ pendingConfirm.summary || pendingConfirm.title || '这一步要我帮你做吗' }}</b>
        <span>确认之后才会真的写进去</span>
      </div>
      <div class="cfm__btns">
        <button class="cfm__no" type="button" :disabled="confirming" @click="doCancelAction">算了</button>
        <button class="cfm__ok" type="button" :disabled="confirming" @click="doConfirmAction">
          {{ confirming ? '处理中…' : '确认' }}
        </button>
      </div>
      <p v-if="cfmErr" class="cfm__err">{{ cfmErr }}</p>
    </div>

    <!-- typing 三点指示器 -->
    <div class="typing" :class="{ show: isTyping }">
      <div class="typing__box"><i></i><i></i><i></i></div>
    </div>
  </div>

  <!-- 关系不在了：这个页面读不到任何授权状态，必须直说，别让人对着「等 TA 授权」干等 -->
  <div v-if="notBound" class="lock">
    <span class="lock__txt">你俩现在还没有绑定，先绑上才能用模拟 Ta</span>
    <button class="lock__go" type="button" @click="emit('back')">返回</button>
  </div>

  <!-- 还没双方授权：把「为什么不能聊」摆在输入框上面，别让人发出去才撞报错 -->
  <div v-else-if="!bothOn" class="lock">
    <span class="lock__txt">
      {{ mine ? '你已授权，等 TA 也授权就能开始' : '双方都授权之后，分身才会开口' }}
    </span>
    <button class="lock__go" type="button" @click="panelOpen = true">
      {{ mine ? '看授权状态' : '去授权' }}
    </button>
  </div>

  <!-- 底部输入区 -->
  <div class="composer">
    <div class="composer__field">
      <input
        ref="inputEl"
        v-model="draft"
        type="text"
        maxlength="2000"
        :placeholder="bothOn ? '对 TA 的分身说点什么…' : '先授权，才能聊'"
        :disabled="!bothOn"
        autocomplete="off"
        @keydown.enter="send"
      />
    </div>
    <button class="send" :class="{ ready: canSend }" :disabled="!canSend" @click="send">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 19V5M5.5 11.5L12 5l6.5 6.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
  </div>
</section>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue';
import StatusBar from '../components/StatusBar.vue';
import { createConversation, getConversation, streamMessage, confirmAction, cancelAction, memorizeConversation } from '../api/agent.js';
import { getSimtaState, setConsent } from '../api/simta.js';

const props = defineProps({ active: Boolean });
const emit = defineEmits(['back']);

/* 与后端 simta service DISCLAIMER 常量保持一致 */
const DISCLAIMER = '这是基于历史数据模拟的 TA，不是本人。真实的想法，还是要问 TA。';

const chatEl = ref(null);
const inputEl = ref(null);

const messages = ref([]);
const draft = ref('');
const isTyping = ref(false);
const busy = ref(false);
const conversationId = ref(null);
const pendingConfirm = ref(null);
const toolLabel = ref('');
/* 最后一条消息的时间：历史拉回来时用它，不然时间栏永远写「今天 现在」 */
const lastAt = ref(null);

/* 授权：只有双方都授权，分身才会真的开口。
   这是同意权，不能靠"打开页面即视为同意"，所以做成显式开关。 */
const mine = ref(false);        // 我是否授权对方用我的数据
const theirs = ref(false);      // 对方是否授权我用 TA 的数据
const panelOpen = ref(false);
const consenting = ref(false);
const consentErr = ref('');
/* 关系被解除 / 还没绑定（后端 409·3001）：这一页什么状态都读不到，得说明白 */
const notBound = ref(false);

/* 双方都授权了才真的能对话 —— 后端 agent 接口也会再校验一次 */
const bothOn = computed(() => mine.value && theirs.value);

let msgSeq = 0;
let abortController = null;
/* 会话 id 存在本机：下次进来接着上次那条聊，历史才接得上。
   （后端 persist=true，历史本来就在库里，缺的只是「记住是哪一条」） */
const CONV_KEY = 'cove.simta_conv';

const canSend = computed(() => bothOn.value && draft.value.trim().length > 0 && !busy.value);
const timeLabel = computed(() => {
  const d = lastAt.value ? new Date(lastAt.value) : new Date();
  if (Number.isNaN(d.getTime())) return '今天';
  const hm = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return `今天 ${hm}`;
  const yest = new Date(today);
  yest.setDate(today.getDate() - 1);
  if (d.toDateString() === yest.toDateString()) return `昨天 ${hm}`;
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 ${hm}`;
});

function pushMsg(role, text) {
  const msg = { id: ++msgSeq, role, text, disc: false, streaming: false };
  messages.value.push(msg);
  // 必须返回数组里的响应式代理，而不是原始对象：
  // 后续流式累加要改这个代理，视图才会更新
  return messages.value[messages.value.length - 1];
}

function scrollToBottom() {
  const el = chatEl.value;
  if (el) el.scrollTop = el.scrollHeight;
}

/* 免责提示只挂在最新一条分身消息下面：
   历史里每条都挂，翻起来就是一屏小字，反而没人看 */
function markDisc(msg) {
  for (const m of messages.value) if (m.role === 'ta') m.disc = false;
  if (msg) msg.disc = true;
}

/* ---- 会话：一条对话一直续着 ---- */

/* 进页面先试着接上上次那条会话，把历史灌进消息流 */
let restored = false;
async function restoreSession() {
  if (restored) return;
  restored = true;
  const id = Number(localStorage.getItem(CONV_KEY) || 0);
  if (!id) return;
  try {
    const conv = await getConversation(id);
    conversationId.value = conv.id;
    const rows = (conv.messages || []).slice(-40);
    messages.value = [];
    for (const m of rows) {
      pushMsg(m.role === 'user' ? 'me' : 'ta', m.content || '');
    }
    /* 免责只在最后一句话下面显示一次，历史里每条都挂会糊成一团 */
    const lastTa = [...messages.value].reverse().find((x) => x.role === 'ta');
    if (lastTa) markDisc(lastTa);
    if (rows.length) lastAt.value = rows[rows.length - 1].created_at;
    await nextTick();
    scrollToBottom();
  } catch (e) {
    /* 会话被删 / 过期 / 换了账号：清掉这条记录，下次发消息自动新开 */
    localStorage.removeItem(CONV_KEY);
    conversationId.value = null;
    messages.value = [];
  }
}

async function ensureConversation() {
  if (!conversationId.value) {
    const conv = await createConversation(null, true);
    conversationId.value = conv.id;
    localStorage.setItem(CONV_KEY, String(conv.id));
  }
  return conversationId.value;
}

/* 离开页面时把这次对话切成记忆块交给后端（失败也不打扰用户） */
function saveMemory() {
  const id = conversationId.value;
  if (!id) return;
  memorizeConversation(id).catch(() => {});
}

/* ---- 发送一轮：真实 SSE 流式 ---- */
async function send() {
  const text = draft.value.trim();
  if (!text || busy.value) return;

  pushMsg('me', text);
  draft.value = '';
  busy.value = true;
  isTyping.value = true;
  await nextTick();
  scrollToBottom();

  let taMsg = null;
  try {
    const cid = await ensureConversation();
    abortController = new AbortController();

    for await (const ev of streamMessage(cid, text, { signal: abortController.signal })) {
      if (ev.event === 'delta') {
        if (isTyping.value) isTyping.value = false;
        if (!taMsg) {
          taMsg = pushMsg('ta', '');
          taMsg.streaming = true;
        }
        taMsg.text += ev.data.delta;
        await nextTick();
        scrollToBottom();
      } else if (ev.event === 'tool') {
        // 工具状态：running 时给个轻提示，done 清掉，不打断对话
        toolLabel.value = ev.data.status === 'running' ? (ev.data.label || '正在查询') : '';
      } else if (ev.event === 'confirm') {
        // 写操作待确认，先挂起；确认/取消面板在后续迭代补
        pendingConfirm.value = ev.data;
      } else if (ev.event === 'done') {
        if (taMsg) {
          taMsg.streaming = false;
          markDisc(taMsg);
        }
      } else if (ev.event === 'error') {
        isTyping.value = false;
        if (taMsg) taMsg.streaming = false;
        const err = pushMsg('ta', '（暂时连不上，等会儿再试）');
        markDisc(err);
      }
    }
    // 兜底：后端正常结束但没显式 done 时，也补上免责提示
    if (taMsg) {
      taMsg.streaming = false;
      markDisc(taMsg);
    }
  } catch (e) {
    isTyping.value = false;
    if (taMsg) taMsg.streaming = false;
    const err = pushMsg('ta', `（${e.message}）`);
    markDisc(err);
  } finally {
    busy.value = false;
    lastAt.value = new Date().toISOString();
    await nextTick();
    scrollToBottom();
  }
}

function goBack() {
  emit('back');
}

/* ---------- 待确认的写操作 ---------- */
const confirming = ref(false);
const cfmErr = ref('');
async function doConfirmAction() {
  const a = pendingConfirm.value;
  if (!a || confirming.value) return;
  confirming.value = true;
  cfmErr.value = '';
  try {
    await confirmAction(a.action_id);
    pendingConfirm.value = null;
    pushMsg('ta', '已经办好了');
  } catch (e) {
    cfmErr.value = e.message || '没有确认成功，再试一次';
  } finally {
    confirming.value = false;
    await nextTick();
    scrollToBottom();
  }
}
async function doCancelAction() {
  const a = pendingConfirm.value;
  if (!a || confirming.value) return;
  confirming.value = true;
  cfmErr.value = '';
  try {
    await cancelAction(a.action_id);
    pendingConfirm.value = null;
  } catch (e) {
    cfmErr.value = e.message || '取消失败，再试一次';
  } finally {
    confirming.value = false;
    await nextTick();
    scrollToBottom();
  }
}

/* iOS 键盘：Safari 在输入框聚焦时会把可视视口整体上移，可这一页是 fixed 布局，
   容器不跟着走，结果输入框被顶到屏幕中间、底下露出一大片底色，看着很别扭。
   解法是让容器直接贴住 visualViewport：键盘弹起时高度缩到可视高度，同时跟随
   offsetTop 的位移，输入框就始终停在键盘上沿。桌面预览（宽 > 560）不启用。 */
const chatRoot = ref(null);
const vv = typeof window !== 'undefined' ? window.visualViewport : null;

function syncViewport() {
  const el = chatRoot.value;
  if (!el || !vv) return;
  const keyboard = window.innerHeight - vv.height;
  if (window.innerWidth > 560 || keyboard < 40) {
    el.style.top = '';
    el.style.height = '';
    el.style.bottom = '';
    el.classList.remove('kb');
    return;
  }
  el.style.top = Math.max(0, vv.offsetTop) + 'px';
  el.style.height = vv.height + 'px';
  el.style.bottom = 'auto';
  el.classList.add('kb');
}

onMounted(async () => {
  loadState();
  window.addEventListener('cove:sync', onGlobalSync);
  if (vv) {
    vv.addEventListener('resize', syncViewport);
    vv.addEventListener('scroll', syncViewport);
    syncViewport();
  }
});

/* 授权是两个人的事：TA 在自己的窗口里点了授权，这边必须能自己发现，
   否则页面会一直停在「等 TA 授权」，看着像对方点了没反应。
   所以——切进这一页拉一次、每 8 秒轮询一次（这一页开着才轮询）、
   全局静默广播时也拉一次。 */
let pollTimer = 0;
let stateLoadedOnce = false;

/* 拉真实授权状态；离线/未登录时静默用默认值 */
async function loadState() {
  try {
    const state = await getSimtaState();
    const nextMine = !!state.my_consent;
    const nextTheirs = !!state.partner_consent;
    /* 对方刚刚从不授权变成授权：在聊天流里说一句，别让页面悄悄变化 */
    const justGranted = stateLoadedOnce && nextTheirs && !theirs.value && nextMine;
    mine.value = nextMine;
    theirs.value = nextTheirs;
    notBound.value = false;
    stateLoadedOnce = true;
    if (justGranted) {
      pushMsg('sys', 'TA 已经同意你用 TA 的数据了，现在可以开始聊');
      scrollToBottom();
    }
  } catch (e) {
    /* 没有生效的关系（409·3001）不是「还没授权」，是两个完全不同的状况 */
    if (e?.code === 3001) {
      notBound.value = true;
      mine.value = false;
      theirs.value = false;
      return;
    }
    /* 未登录或后端不可达：保持默认 */
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(() => { if (props.active) loadState(); }, 8000);
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = 0; }
}
/* 页面滑进来就拉一次授权、接上上次的对话，并开始轮询；滑走就停 */
watch(() => props.active, (on) => {
  if (on) {
    loadState();
    restoreSession();
    startPolling();
  } else {
    stopPolling();
    saveMemory();
  }
});
/* 全局静默广播（每 20 秒一次）也接住，双保险 */
function onGlobalSync() {
  if (props.active) loadState();
}


async function toggleConsent() {
  if (consenting.value) return;
  consenting.value = true;
  consentErr.value = '';

  /* 乐观更新：授权是本地状态，先在界面上翻过来，别让按钮挂着「处理中」。
     请求失败再回滚，并用服务端真值校正。 */
  const prev = mine.value;
  const next = !prev;
  mine.value = next;

  try {
    await setConsent(next);
    await loadState();
    /* 首页那枚小卡要跟着从「未开启」变「我等 TA 授权 / 双方已授权」 */
    window.dispatchEvent(new Event('cove:simta'));
  } catch (e) {
    mine.value = prev;
    consentErr.value = e?.message || '没能改授权，稍后再试';
  } finally {
    consenting.value = false;
  }
}

onBeforeUnmount(() => {
  // 离开页面中断未完成的流，避免后台继续写
  abortController?.abort();
  stopPolling();
  saveMemory();
  window.removeEventListener('cove:sync', onGlobalSync);
  if (vv) {
    vv.removeEventListener('resize', syncViewport);
    vv.removeEventListener('scroll', syncViewport);
  }
});
</script>

<style scoped>
.simta-chat {
  position: absolute;
  inset: 0;
  z-index: 40;
  overflow: hidden;
  background: linear-gradient(180deg, #fdeef4 0%, #f7e9f1 30%, #f3eef4 100%);
  transform: translateX(100%);
  transition: transform .5s cubic-bezier(.16, 1, .3, 1);
}
.simta-chat.on {
  transform: none;
}
/* 装饰粉雾，模拟玻璃背景的氛围，不抢内容 */
.simta-chat::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(60% 30% at 80% 8%, rgba(255, 180, 205, .55), transparent 70%),
    radial-gradient(50% 34% at 12% 4%, rgba(255, 200, 215, .5), transparent 72%);
}

/* ============ 顶部导航 ============ */
.nav {
  position: absolute;
  top: 44px;
  left: 0;
  right: 0;
  height: 52px;
  z-index: 7;
  display: flex;
  align-items: center;
  padding: 0 10px;
}
.nav__back {
  display: flex;
  align-items: center;
  gap: 1px;
  border: 0;
  background: none;
  font-family: inherit;
  font-size: 16px;
  font-weight: 600;
  color: var(--coral, #ff5987);
  padding: 8px 8px 8px 6px;
  border-radius: 12px;
  transition: transform .18s, background .2s;
}
.nav__back:active {
  transform: scale(.94);
  background: rgba(255, 93, 135, .1);
}
.nav__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  pointer-events: none;
}
.nav__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink, #2c121f);
  letter-spacing: -.01em;
  line-height: 1.1;
}
.nav__sub {
  font-size: 10.5px;
  font-weight: 600;
  color: rgba(44, 18, 31, .46);
}
.nav__info {
  margin-left: auto;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 0;
  display: grid;
  place-items: center;
  color: var(--coral, #ff5987);
  background: rgba(255, 255, 255, .6);
  backdrop-filter: blur(10px);
  transition: transform .18s;
}
.nav__info:active { transform: scale(.9); }

/* ============ 消息流 ============ */
.chat {
  position: absolute;
  top: 104px;
  left: 0;
  right: 0;
  bottom: 78px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 16px 14px;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.chat::-webkit-scrollbar { display: none; }
.chat__time {
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  color: rgba(44, 18, 31, .4);
  margin: 10px 0 16px;
}
.msg {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  animation: msgIn .46s cubic-bezier(.32, 1.24, .36, 1) both;
}
@keyframes msgIn {
  from { opacity: 0; transform: translateY(14px) scale(.9); }
  to { opacity: 1; transform: none; }
}
.msg__av {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  align-self: flex-end;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(180deg, #ff8fb0, #f0457a);
  box-shadow: 0 4px 10px -4px rgba(240, 69, 122, .6);
}
.bubble {
  max-width: 76%;
  padding: 10px 13px;
  font-size: 14.5px;
  line-height: 1.5;
  letter-spacing: -.005em;
  word-break: break-word;
}
.msg--ta { justify-content: flex-start; }
.msg--ta .bubble {
  color: var(--ink, #2c121f);
  background: rgba(255, 255, 255, .94);
  border-radius: 20px 20px 20px 6px;
  box-shadow: 0 8px 20px -12px rgba(120, 60, 90, .4), inset 0 0 0 .5px rgba(255, 255, 255, .95);
}
.msg--me { justify-content: flex-end; }
/* 不是谁说的话，是「事情变了」的提示：居中一条小胶囊，别做成气泡 */
.msg--sys {
  margin: 2px auto 12px;
  max-width: 82%;
  padding: 6px 13px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .74);
  box-shadow: inset 0 0 0 .5px rgba(255, 255, 255, .9), 0 6px 16px -12px rgba(120, 60, 90, .45);
  font-size: 11.5px;
  line-height: 1.45;
  font-weight: 600;
  color: #8A6E7C;
  text-align: center;
  animation: msgIn .46s cubic-bezier(.32, 1.24, .36, 1) both;
}.msg--me .bubble {
  color: #fff;
  background: linear-gradient(165deg, #ff7aa6 0%, #ff5987 48%, #f02a66 100%);
  border-radius: 20px 20px 6px 20px;
  box-shadow: 0 10px 22px -10px rgba(240, 42, 102, .55), inset 0 1px 0 rgba(255, 255, 255, .28);
}
.cursor {
  display: inline-block;
  width: 2px;
  height: 15px;
  margin-left: 1px;
  vertical-align: -2px;
  border-radius: 1px;
  background: currentColor;
  animation: blink .9s steps(1) infinite;
}
@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}
.disc {
  margin: 2px 0 14px 38px;
  font-size: 10px;
  line-height: 1.45;
  color: rgba(44, 18, 31, .38);
  animation: fadeIn .5s cubic-bezier(.16, 1, .3, 1) both;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* typing 指示器 */
.typing {
  display: flex;
  gap: 8px;
  margin: 4px 0 12px 38px;
  opacity: 0;
  height: 0;
  transition: opacity .3s;
}
.typing.show {
  opacity: 1;
  height: auto;
}
.typing__box {
  display: flex;
  gap: 5px;
  padding: 12px 14px;
  border-radius: 20px 20px 20px 6px;
  background: rgba(255, 255, 255, .94);
  box-shadow: 0 8px 20px -12px rgba(120, 60, 90, .4);
}
.typing__box i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(240, 69, 122, .55);
  animation: bounce 1.2s infinite ease-in-out;
}
.typing__box i:nth-child(2) { animation-delay: .16s; }
.typing__box i:nth-child(3) { animation-delay: .32s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: .5; }
  30% { transform: translateY(-5px); opacity: 1; }
}

/* ============ 底部输入区 ============ */
/* 空态：没消息时的一小段引导 */
.empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 54px 34px 0;
  text-align: center;
}
.empty__ico {
  display: grid; place-items: center;
  width: 44px; height: 44px; margin-bottom: 2px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .72);
  color: #E0407A;
  box-shadow: 0 10px 24px -18px rgba(200, 60, 110, .8);
}
.empty b { font-size: 13px; font-weight: 700; color: #4A2A3A; }
.empty span { font-size: 11.5px; line-height: 1.55; color: #8A6E7C; }

/* 未授权时的说明条：贴在输入区上沿，不遮内容 */
.lock {
  position: absolute;
  left: 14px; right: 14px; bottom: 84px;
  z-index: 9;
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, .86);
  box-shadow: 0 10px 26px -18px rgba(60, 20, 40, .5), inset 0 0 0 1px rgba(255, 255, 255, .7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
.lock__txt {
  flex: 1; font-size: 11.5px; line-height: 1.4; color: #6C6C76;
}
.lock__go {
  flex: none; height: 28px; padding: 0 11px;
  border: 0; border-radius: 999px;
  background: #111114; color: #fff;
  font: inherit; font-size: 11.5px; font-weight: 700;
  transition: transform .16s cubic-bezier(.22, 1, .36, 1);
}
.lock__go:active { transform: scale(.96); }

/* 待确认的动作卡：白底、两个按钮，放在消息流末尾 */
.cfm {
  margin: 10px 0 2px;
  padding: 12px 13px;
  border-radius: 16px;
  background: rgba(255,255,255,.96);
  box-shadow: 0 10px 24px -18px rgba(40,44,60,.6), inset 0 0 0 .5px rgba(20,20,30,.06);
}
.cfm__t { display: flex; flex-direction: column; gap: 3px; }
.cfm__t b { font-size: 13px; font-weight: 700; color: #1E1E24; line-height: 1.4; }
.cfm__t span { font-size: 11px; color: #8C8C96; }
.cfm__btns { display: flex; gap: 8px; margin-top: 10px; }
.cfm__btns button {
  flex: 1; height: 34px; border: 0; border-radius: 11px;
  font: inherit; font-size: 12.5px; font-weight: 700;
  transition: transform .16s cubic-bezier(.22, 1, .36, 1);
}
.cfm__btns button:active { transform: scale(.97); }
.cfm__no { background: #F1F1F4; color: #55555F; }
.cfm__ok { background: #111114; color: #fff; }
.cfm__btns button:disabled { opacity: .55; }
.cfm__err { margin: 8px 0 0; font-size: 11px; color: #D8384C; }

.composer {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 8;
  padding: 10px 14px 26px;
  background: linear-gradient(180deg, rgba(247, 233, 241, 0), rgba(247, 233, 241, .92) 32%, rgba(247, 233, 241, .98));
  display: flex;
  align-items: center;
  gap: 9px;
}
.composer__field {
  flex: 1;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, .95);
  border-radius: 22px;
  padding: 0 15px;
  height: 44px;
  box-shadow: inset 0 0 0 .5px rgba(255, 255, 255, .95), 0 8px 20px -12px rgba(120, 60, 90, .4);
  transition: box-shadow .25s;
}
.composer__field:focus-within {
  box-shadow: inset 0 0 0 1.4px rgba(255, 93, 135, .55), 0 10px 22px -12px rgba(120, 60, 90, .45);
}
.composer input {
  flex: 1;
  border: 0;
  outline: 0;
  background: none;
  font-family: inherit;
  font-size: 15px;
  color: var(--ink, #2c121f);
}
.composer input::placeholder { color: rgba(44, 18, 31, .38); }

/* 键盘弹起时下面那 26px 的呼吸位没有意义（Home 条已被键盘盖住），贴着键盘更自然 */
.simta-chat.kb .composer { padding-bottom: 10px; }
.send {
  flex: none;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: rgba(200, 150, 170, .55);
  transition: transform .22s cubic-bezier(.32, 1.24, .36, 1), background .25s, box-shadow .25s;
}
.send.ready {
  background: linear-gradient(160deg, #ff7aa6, #f02a66);
  box-shadow: 0 8px 18px -6px rgba(240, 42, 102, .6);
}
.send:active { transform: scale(.86); }
.send.ready:active { transform: scale(.8); }

/* ============ 授权面板（黑白，只有「已授权」用一点珊瑚） ============ */
.au-wrap {
  position: fixed; inset: 0; z-index: 90;
  display: flex; align-items: flex-end; justify-content: center;
}
.au-mask { position: absolute; inset: 0; background: rgba(18, 16, 20, .34); }
.au-card {
  position: relative;
  width: 100%; max-width: 400px;
  padding: 10px 16px calc(14px + env(safe-area-inset-bottom, 0px));
  border-radius: 24px 24px 0 0;
  background: #fff;
  box-shadow: 0 -18px 44px -26px rgba(17, 17, 19, .38);
}
@media (min-width: 520px) {
  .au-wrap { padding-bottom: 30px; }
  .au-card { border-radius: 24px; max-width: 372px; }
}
.au-grab { display: block; width: 38px; height: 4px; margin: 0 auto 8px; border-radius: 999px; background: #E4E4E9; }
.au-t { margin: 0; font-size: 16.5px; font-weight: 800; letter-spacing: -.02em; color: #111114; }
.au-sub { margin: 4px 0 10px; font-size: 11.5px; line-height: 1.5; color: #7A7A84; }

.au-state {
  display: flex; flex-direction: column; gap: 1px;
  border-radius: 14px; background: #F5F5F7; overflow: hidden;
}
.au-row {
  display: flex; align-items: center; gap: 9px;
  padding: 11px 12px; background: #fff;
}
.au-av {
  flex: none; width: 24px; height: 24px; border-radius: 50%;
  display: grid; place-items: center;
  font-size: 9.5px; font-weight: 800; font-style: normal;
  background: #F1F1F4; color: #7A7A84;
}
.au-av--me { background: #111114; color: #fff; }
.au-row b { font-size: 13px; font-weight: 700; color: #111114; }
.au-row em {
  margin-left: auto; font-style: normal;
  font-size: 11.5px; font-weight: 600; color: #B6B6BE;
}
.au-row em.on { color: #D9235A; }

.au-hint { margin: 9px 0 0; font-size: 11px; line-height: 1.55; color: #8C8C96; }
.au-err { margin: 8px 0 0; font-size: 11.5px; color: #D9235A; }

.au-acts { display: flex; align-items: center; gap: 9px; margin-top: 12px; }
.au-main {
  flex: 1; height: 46px;
  border: 0; border-radius: 14px;
  background: #111114; color: #fff;
  font: inherit; font-size: 14px; font-weight: 700;
  transition: transform .16s cubic-bezier(.22, 1, .36, 1), background .16s ease;
}
.au-main.revoke { background: #F5F5F7; color: #52525B; }
.au-main:active:not(:disabled) { transform: scale(.985); }
/* 状态已经乐观翻转，请求期间的 disabled 不该让按钮变淡闪一下 */
.au-main:disabled { cursor: default; }
.au-close {
  flex: none; height: 46px; padding: 0 15px;
  border: 0; border-radius: 14px;
  background: #F5F5F7; color: #52525B;
  font: inherit; font-size: 13.5px; font-weight: 600;
}
.au-close:active { transform: scale(.985); }

.au-enter-active { transition: opacity .24s ease; }
.au-leave-active { transition: opacity .18s ease; }
.au-enter-from, .au-leave-to { opacity: 0; }
.au-enter-active .au-card { transition: transform .32s cubic-bezier(.22, 1, .36, 1); }
.au-enter-from .au-card { transform: translateY(100%); }

@media (prefers-reduced-motion: reduce) {
  .au-enter-active, .au-leave-active, .au-enter-active .au-card { transition-duration: .01s !important; }
}
</style>
