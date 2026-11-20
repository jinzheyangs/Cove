<template>
  <div class="qpanel">
    <div class="qpanel__q">
      <span class="qpanel__label">今日问题</span>
      <p class="qpanel__text">{{ question }}</p>
    </div>

    <div class="qpanel__line"></div>

    <div
      v-for="a in answers"
      :key="a.key"
      class="ab"
      :class="`ab--${a.variant}`"
    >
      <div class="ab__head">
        <span class="ab__av" :class="`ab__av--${a.variant}`">{{ a.initial }}</span>
        <span class="ab__name">{{ a.name }}</span>
        <span class="ab__tag">{{ a.tag }}</span>
      </div>

      <template v-if="a.state === 'locked'">
        <div class="ab__state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="10" width="14" height="10" rx="2.4" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg>
          回答后可见
        </div>
      </template>

      <template v-else-if="a.state === 'pending'">
        <div class="ab__state ab__state--pending">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 8v4l2.5 2" /></svg>
          {{ a.key === 'me' ? '待回答' : 'TA 待回答' }}
        </div>
        <button v-if="a.key === 'me'" class="ab__cta" @click="openAnswer">去回答</button>
      </template>

      <template v-else>
        <p
          :ref="(el) => { a.el = el; }"
          class="ab__text"
          :class="{ 'is-clamp': !a.open }"
        >{{ a.text }}</p>
        <button
          v-if="a.overflow"
          class="ab__toggle"
          :class="{ 'is-open': a.open }"
          @click="toggle(a)"
        >
          {{ a.open ? '收起' : '展开' }}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
        </button>
        <button v-if="a.key === 'me'" class="ab__edit" @click="openAnswer">改一下</button>
      </template>
    </div>

    <AnswerSheet
      v-model:open="answerOpen"
      :question="question"
      :my-answer="myText"
      :partner-answer="theirText"
      @saved="pull"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { get } from '../api/client.js';
import AnswerSheet from './AnswerSheet.vue';

/* 数据来自 GET /daily：question / my_answer / partner_answer，
   两者都可能为 null —— 那就是「待回答」和「回答后可见」两种空态。 */
const question = ref('今天的问题还没出题');
const answers = ref([]);
const answerOpen = ref(false);

const myText = computed(() => answers.value.find((a) => a.key === 'me')?.text || '');
const theirText = computed(() => answers.value.find((a) => a.key === 'ta')?.text || '');

function openAnswer() {
  answerOpen.value = true;
}

function build(daily) {
  const q = daily?.question || '今天的问题还没出题';
  const mine = (daily?.my_answer || '').trim();
  const theirs = (daily?.partner_answer || '').trim();
  question.value = q;
  answers.value = [
    { key: 'me', variant: 'me', name: '这是我', initial: '我', tag: '我', text: mine, state: mine ? null : 'pending', open: false, overflow: false, el: null },
    { key: 'ta', variant: 'ta', name: '我的 TA', initial: 'TA', tag: '对方', text: theirs, state: !mine ? 'locked' : (theirs ? null : 'pending'), open: false, overflow: false, el: null },
  ];
  nextTick(measure);
}

async function pull() {
  try {
    build(await get('/daily'));
  } catch (_) {
    build(null);
  }
}

function measure() {
  answers.value.forEach((a) => {
    if (a.state || !a.el || a.open) return;
    a.overflow = a.el.scrollHeight > a.el.clientHeight + 2;
  });
}

function toggle(a) {
  a.open = !a.open;
  nextTick(measure);
}

onMounted(() => {
  pull();
  window.addEventListener('cove:auth', pull);
  window.addEventListener('cove:daily', pull);
  /* 首页被切回来 / 每 20 秒静默刷新时，对方刚答的那条也要出现 */
  window.addEventListener('cove:home', pull);
});

onBeforeUnmount(() => {
  window.removeEventListener('cove:auth', pull);
  window.removeEventListener('cove:daily', pull);
  window.removeEventListener('cove:home', pull);
});
</script>

<style scoped>
.qpanel {
  margin-top: 12px; border-radius: 24px; padding: 17px 16px 14px;
  background: rgba(255, 255, 255, .92);
  box-shadow:
    0 2px 10px -4px rgba(255, 90, 130, .22),
    0 22px 44px -24px rgba(196, 26, 74, .32),
    inset 0 0 0 .5px rgba(255, 255, 255, .9);
}

.qpanel__label { font-size: 11px; font-weight: 800; letter-spacing: .5px; color: #e0407a; }
.qpanel__text { margin: 7px 0 0; font-size: 16px; line-height: 1.5; font-weight: 800; letter-spacing: -.015em; color: #2c121f; }

.qpanel__line { height: 1px; margin: 15px 0 13px; background: rgba(220, 120, 150, .18); }

.ab { border-radius: 18px; padding: 13px 14px; margin-bottom: 10px; }
.ab:last-child { margin-bottom: 0; }
.ab--me { background: linear-gradient(180deg, #fff0f6, #fde7f0); }
.ab--ta { background: linear-gradient(180deg, #fff3ee, #fdece4); }

.ab__head { display: flex; align-items: center; gap: 9px; }
.ab__av {
  width: 30px; height: 30px; border-radius: 50%; flex: none;
  display: grid; place-items: center;
  font-size: 11.5px; font-weight: 800; color: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .55), 0 5px 12px -5px rgba(190, 25, 72, .5);
}
.ab__av--me { background: linear-gradient(180deg, #ff6f9e, #f02a66); }
.ab__av--ta { background: linear-gradient(180deg, #ff9a86, #f0765a); }
.ab__name { font-size: 13.5px; font-weight: 800; color: #3a1526; }
.ab__tag {
  margin-left: auto; font-size: 10px; font-weight: 800; padding: 3px 9px; border-radius: 999px;
  color: #c71f53; background: rgba(255, 255, 255, .7);
}

.ab__text { margin: 9px 0 0; font-size: 13px; line-height: 1.6; color: rgba(58, 21, 38, .82); }
.ab__text.is-clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.ab__state {
  margin-top: 9px; font-size: 13px; font-weight: 700; color: rgba(120, 60, 85, .55);
  display: flex; align-items: center; gap: 7px;
}
.ab__state svg { width: 15px; height: 15px; }
.ab__state--pending { color: #d6225e; }

.ab__toggle {
  margin-top: 8px; width: 100%; background: transparent;
  display: flex; align-items: center; justify-content: center; gap: 4px;
  font-size: 12.5px; font-weight: 800; color: #e0407a; font-family: inherit; padding: 4px 0;
}
.ab__toggle svg { width: 14px; height: 14px; transition: transform .28s cubic-bezier(.22, 1, .36, 1); }
.ab__toggle.is-open svg { transform: rotate(180deg); }

.ab__cta {
  margin-top: 10px; height: 34px; border-radius: 999px; width: 100%;
  background: linear-gradient(180deg, #ff5d8f, #f02a66); color: #fff;
  font-size: 12.5px; font-weight: 800;
  box-shadow: 0 8px 16px -8px rgba(190, 25, 72, .6), inset 0 1px 0 rgba(255, 255, 255, .3);
  transition: transform .16s cubic-bezier(.22, 1, .36, 1);
}
.ab__cta:active { transform: scale(.97); }

.ab__edit {
  margin-top: 9px; height: 30px; padding: 0 14px;
  border-radius: 999px; background: rgba(255, 255, 255, .78);
  color: #c71f53; font: inherit; font-size: 11.5px; font-weight: 800;
  box-shadow: inset 0 0 0 .5px rgba(214, 34, 94, .22);
  transition: transform .16s cubic-bezier(.22, 1, .36, 1), background .16s;
}
.ab__edit:active { transform: scale(.94); background: #fff; }
</style>
