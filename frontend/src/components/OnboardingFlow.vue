<template>
<div class="onb">
  <!-- 深色上半：进度 / 跳过 / 实时预览，和登录页的 slogan 位同一个位置 -->
  <div class="onb-dark">
    <div class="onb-top">
      <div class="onb-dots" aria-hidden="true">
        <span v-for="(s, i) in steps" :key="s" :class="{ on: i <= idx, cur: i === idx }"></span>
      </div>
      <button class="onb-skip" @click="skip">跳过</button>
    </div>

    <div class="onb-brand">
      <b>cove</b>
      <span>两个人的地方</span>
    </div>

    <Transition name="onb-fade" mode="out-in">
      <div class="onb-hero" :key="step">
        <span class="onb-hero-label">{{ previewLabel }}</span>

        <div class="onb-hero-main">
          <template v-if="step === 'nickname'">
            <span class="onb-ava" :style="{ opacity: previewReady ? 1 : .3 }">{{ initial }}</span>
            <b class="onb-hero-name" :class="{ dim: !previewReady }">{{ nick.trim() || '你的名字' }}</b>
          </template>
          <template v-else-if="previewReady">
            <Transition name="onb-num" mode="out-in">
              <b class="onb-hero-num" :key="previewNum">{{ previewNum }}</b>
            </Transition>
            <u>天</u>
          </template>
          <template v-else>
            <b class="onb-hero-num dim">—</b>
            <u>天</u>
          </template>
        </div>

        <span class="onb-hero-foot">{{ previewFoot }}</span>
      </div>
    </Transition>
  </div>

  <!-- 白色大圆角卡：标题、字段、主按钮 -->
  <section class="onb-card">
    <Transition name="onb-step" mode="out-in">
      <div class="onb-mid" :key="step">
        <span class="onb-eyebrow">Step {{ idx + 1 }} / {{ steps.length }}</span>
        <h1 class="onb-title">{{ title }}</h1>
        <p class="onb-desc">{{ desc }}</p>

        <div class="onb-body">
          <!-- 昵称 -->
          <div v-if="step === 'nickname'" class="onb-field">
            <label class="onb-lb" for="onb-nick">昵称</label>
            <div class="onb-in">
              <input id="onb-nick" v-model="nick" maxlength="50" placeholder="怎么称呼你" autocomplete="nickname" />
            </div>
            <p class="onb-hint">TA 的界面里会显示这个名字，随时能改</p>
          </div>

          <!-- 生日：年 / 月 / 日 三列滚轮（只属于你自己） -->
          <div v-else-if="step === 'birthday'" class="onb-field">
            <span class="onb-lb">生日 <i class="onb-tag">我的</i></span>
            <WheelDatePicker v-model="birth" :max="todayStr" />
            <p class="onb-hint">你自己的生日，每年只提醒你一次；它不是「纪念日」，也不算在一起的天数</p>
          </div>

          <!-- 恋爱纪念日：同一套三列滚轮（属于你们两个人） -->
          <div v-else class="onb-field">
            <span class="onb-lb">恋爱纪念日 <i class="onb-tag">我们的</i></span>
            <WheelDatePicker v-model="start" :max="todayStr" />
            <p class="onb-hint">你们认定的那一天，在一起多少天、第几个周年都从这儿算</p>
          </div>

          <Transition name="onb-grow">
            <p v-if="err" class="onb-err">{{ err }}</p>
          </Transition>
        </div>
      </div>
    </Transition>

    <div class="onb-bottom">
      <button class="onb-cta" :disabled="busy || !canNext" @click="next">
        {{ busy ? '保存中…' : (idx === steps.length - 1 ? 'Done' : 'Next') }}
      </button>
      <p class="onb-foot">之后都能在设置里改</p>
    </div>
  </section>
</div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { updateProfile, updateCouple, getMe, getCouple } from '../api/settings.js';
import { markStepSkipped } from '../composables/useOnboarding.js';
import WheelDatePicker from './WheelDatePicker.vue';

/* 设计走查：?openDate=1 时把日期面板直接摊开 */
const walkDate = new URLSearchParams(location.search).get('openDate') === '1';

const props = defineProps({
  steps: { type: Array, default: () => ['nickname', 'birthday', 'start'] },
  /* 从登录/绑定回来的已知值，用来预填 */
  prefill: { type: Object, default: () => ({}) },
  /* 设计走查用：直接从第几步开始 */
  startAt: { type: Number, default: 0 },
});
const emit = defineEmits(['done', 'skip']);

const idx = ref(Math.min(Math.max(0, props.startAt), props.steps.length - 1));
const nick = ref(props.prefill.nickname || '');
const birth = ref(props.prefill.birthday || '2000-01-01');
const start = ref(props.prefill.start_date || '');
const busy = ref(false);
const err = ref('');

/* 在一起日期没填过时，滚轮默认停在今天（大多数人的绑定日就是今天或最近） */
const todayKey = (() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
})();

const step = computed(() => props.steps[idx.value] || 'nickname');

/* 标题用英文超粗标题（和注册页 Create account 同一套字形），说明用中文 */
const COPY = {
  nickname: {
    title: 'Your name',
    desc: '给自己起个喜欢的名字，TA 那边会看到它。',
  },
  birthday: {
    title: 'Your birthday',
    desc: '这是你自己的生日，每年提前提醒你一次；它不等于你们的纪念日。',
  },
  start: {
    title: 'Your anniversary',
    desc: '这是你们恋爱的纪念日：在一起多少天、第几个周年都从这天算。',
  },
};

const title = computed(() => COPY[step.value].title);
const desc = computed(() => COPY[step.value].desc);

const todayStr = computed(() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
});

const canNext = computed(() => (step.value === 'nickname' ? nick.value.trim().length > 0 : true));

const diffDays = (from, to) => Math.round((to - from) / 86400000);

const daysToBirthday = computed(() => {
  if (!birth.value) return 0;
  const d = new Date(birth.value + 'T00:00:00');
  const now = new Date(todayStr.value + 'T00:00:00');
  const next = new Date(now.getFullYear(), d.getMonth(), d.getDate());
  if (next < now) next.setFullYear(now.getFullYear() + 1);
  return diffDays(now, next);
});

const daysTogether = computed(() => {
  if (!start.value) return 0;
  return Math.max(0, diffDays(new Date(start.value + 'T00:00:00'), new Date(todayStr.value + 'T00:00:00')));
});

/* ---- 上半屏的实时预览 ---- */
const initial = computed(() => {
  const name = nick.value.trim();
  return name ? [...name][0].toUpperCase() : '你';
});
const previewReady = computed(() => {
  if (step.value === 'nickname') return !!nick.value.trim();
  if (step.value === 'birthday') return !!birth.value;
  return !!start.value;
});
const previewNum = computed(() => {
  if (!previewReady.value) return '—';
  const n = step.value === 'birthday' ? daysToBirthday.value : daysTogether.value;
  return n.toLocaleString('en-US');
});
const previewLabel = computed(
  () => ({ nickname: 'TA WILL SEE', birthday: 'NEXT BIRTHDAY', start: 'DAYS SINCE' })[step.value]
);
const previewFoot = computed(() => {
  if (step.value === 'nickname') return '之后在设置里也能改';
  if (step.value === 'birthday') {
    if (!birth.value) return '每年只提醒你自己的生日';
    const d = new Date(birth.value + 'T00:00:00');
    return `每年 ${d.getMonth() + 1} 月 ${d.getDate()} 日提醒你`;
  }
  return start.value ? '从这天起，在一起的天数和周年都跟着变' : '按你们认定的那天填';
});

/* 预填：昵称/生日从后端拿，起始日从关系里拿 */
onMounted(async () => {
  try {
    const me = await getMe();
    if (me) {
      if (!nick.value && me.nickname) nick.value = me.nickname;
      if (!birth.value && me.birthday) birth.value = me.birthday;
    }
  } catch (_) { /* 拿不到就留空，用户自己填 */ }
  if (step.value === 'start' && !start.value) {
    try {
      const couple = await getCouple();
      if (couple?.start_date) start.value = couple.start_date;
    } catch (_) { /* 未绑定或接口失败，留空即可 */ }
  }
});

async function save(){
  const s = step.value;
  if (s === 'nickname') {
    const name = nick.value.trim();
    if (!name) return;
    if (name !== (props.prefill.nickname || '')) await updateProfile({ nickname: name });
  } else if (s === 'birthday') {
    if (birth.value) await updateProfile({ birthday: birth.value });
  } else if (s === 'start') {
    if (start.value) await updateCouple({ start_date: start.value });
  }
}

async function next(){
  err.value = '';
  busy.value = true;
  try {
    await save();
    if (idx.value < props.steps.length - 1) idx.value += 1;
    else emit('done');
  } catch (e) {
    err.value = e.message || '保存失败，稍后再试';
  } finally {
    busy.value = false;
  }
}

function skip(){
  err.value = '';
  // 记下这一步被跳过，下次登录就不再重复问
  markStepSkipped(step.value);
  if (idx.value < props.steps.length - 1) idx.value += 1;
  else emit('done');
}
</script>

<style scoped>
/* ============================================================
   引导 · 与登录/注册同一套黑白稿
   深色上半（进度 / 跳过 / 实时预览）→ 白色大圆角卡（超粗英文
   标题、1px 细边输入框、纯黑主按钮）
   ============================================================ */
.onb{
  --k:#111114;
  --k2:#8A8A92;
  --k3:#A8A8B0;
  --line:#EAEAEF;
  --red:#FF4D4F;
  --out:cubic-bezier(.16,1,.3,1);
  --spring:cubic-bezier(.34,1.4,.64,1);

  position:absolute; inset:0; z-index:60;
  display:flex; flex-direction:column;
  overflow:hidden;
  /* 深色底 + 恋爱感光晕：远看仍是黑，边缘透出玫瑰与淡紫 */
  background:
    radial-gradient(84% 56% at 94% -10%, rgba(255,110,164,.36) 0%, rgba(255,110,164,0) 64%),
    radial-gradient(74% 50% at -2% 4%, rgba(150,118,255,.24) 0%, rgba(150,118,255,0) 66%),
    radial-gradient(124% 58% at 50% 108%, rgba(255,168,132,.18) 0%, rgba(255,168,132,0) 68%),
    linear-gradient(180deg, #23232C 0%, #191920 40%, #151519 100%);
  color:var(--k);
  font-family:'Inter','PingFang SC','Microsoft YaHei',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
}

/* ---- 深色上半 ---- */
.onb-dark{
  flex:1 1 auto; min-height:0;
  display:flex; flex-direction:column;
  padding:calc(14px + env(safe-area-inset-top,0px)) 24px 0;
}
.onb-top{
  flex:0 0 auto;
  display:flex; align-items:center; justify-content:space-between;
  padding:2px 0 0;
}
.onb-dots{ display:flex; align-items:center; gap:6px; }
.onb-dots span{
  width:6px; height:6px; border-radius:99px;
  background:rgba(255,255,255,.22);
  transition:width .34s var(--out), background .3s var(--out);
}
.onb-dots span.on{ background:rgba(255,255,255,.55); }
.onb-dots span.cur{ width:22px; background:#fff; }
.onb-skip{
  font-size:12px; font-weight:500; letter-spacing:-.005em;
  color:rgba(255,255,255,.45);
  padding:6px 8px; border-radius:10px; cursor:pointer;
  transition:color .22s var(--out), background .22s var(--out);
}
.onb-skip:active{ color:#fff; background:rgba(255,255,255,.1); }

/* 实时预览，占的正是登录页 slogan 那块位置 */
.onb-brand{ margin-top:40px; flex:0 0 auto; }
.onb-brand b{
  display:block;
  font-size:23px; font-weight:800; letter-spacing:-.055em; color:#fff;
}
.onb-brand span{
  display:block; margin-top:5px;
  font-size:10.5px; font-weight:500; letter-spacing:.15em;
  color:rgba(255,255,255,.36);
}
.onb-hero{
  flex:1 1 auto; min-height:0;
  display:flex; flex-direction:column; justify-content:flex-end;
  padding-bottom:28px;
}
.onb-hero-label{
  display:block;
  font-size:9.5px; font-weight:700; letter-spacing:.18em;
  color:rgba(255,255,255,.38);
  text-transform:uppercase;
}
.onb-hero-main{
  display:flex; align-items:baseline; gap:9px;
  margin-top:12px; min-height:46px;
}
.onb-hero-num{
  font-size:46px; line-height:1; font-weight:900; letter-spacing:-.045em;
  font-variant-numeric:tabular-nums; color:#fff;
  transition:opacity .3s var(--out);
}
.onb-hero-num.dim{ opacity:.34; }
.onb-hero-main u{
  text-decoration:none;
  font-size:11.5px; font-weight:700; letter-spacing:.06em;
  color:rgba(255,255,255,.42);
}
.onb-hero-name{
  font-size:24px; font-weight:800; letter-spacing:-.035em; color:#fff;
  max-width:250px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
  align-self:center;
  transition:opacity .3s var(--out);
}
.onb-hero-name.dim{ opacity:.34; }
.onb-ava{
  width:40px; height:40px; border-radius:50%;
  display:grid; place-items:center;
  font-size:16px; font-weight:800; color:#17171B; background:#fff;
  align-self:center;
  transition:opacity .3s var(--out);
}
.onb-hero-foot{
  display:block; margin-top:14px;
  font-size:11px; line-height:1.55; color:rgba(255,255,255,.4);
  max-width:300px;
}

/* ---- 白卡 ---- */
.onb-card{
  flex:0 0 auto;
  display:flex; flex-direction:column;
  background:#fff; border-radius:26px 26px 0 0;
  box-shadow:0 -8px 40px -24px rgba(0,0,0,.6);
}

.onb-mid{
  padding:24px 24px 2px;
}

.onb-eyebrow{
  display:block;
  font-size:10px; font-weight:700; letter-spacing:.17em;
  color:#9A9AA2; text-transform:uppercase;
}
.onb-title{
  margin:10px 0 0;
  font-size:33px; line-height:1.06; font-weight:900;
  letter-spacing:-.042em; color:var(--k);
}
.onb-desc{
  margin:10px 0 0;
  font-size:12.5px; line-height:1.62; color:var(--k2);
}
.onb-body{ margin-top:22px; }
.onb-field{ display:flex; flex-direction:column; }

/* ---- 输入 ---- */
.onb-lb{
  display:block; margin:0 0 8px;
  font-size:12.5px; font-weight:600; color:var(--k);
}
/* 「我的 / 我们的」小标：把生日和纪念日在同一条流程里区分开 */
.onb-tag{
  display:inline-block; margin-left:6px; padding:1px 7px;
  border-radius:999px;
  font-size:10px; font-weight:700; font-style:normal; letter-spacing:.02em;
  color:#8A6A75; background:#F7EFF2;
  vertical-align:1px;
}
.onb-in{
  display:flex; align-items:center;
  height:56px; padding:0 14px;
  border:1px solid var(--line); border-radius:13px; background:#fff;
  transition:border-color .18s var(--out), box-shadow .18s var(--out);
}
.onb-in:focus-within{
  border-color:var(--k);
  box-shadow:0 0 0 3px rgba(17,17,20,.06);
}
.onb-in input{
  flex:1; min-width:0; height:100%;
  border:0; outline:none; background:none;
  font:inherit; font-size:15px; color:var(--k);
  letter-spacing:-.01em; caret-color:var(--k);
  color-scheme:light;
}
.onb-in input::placeholder{ color:var(--k3); font-weight:400; }
.onb-in input::-webkit-calendar-picker-indicator{ cursor:pointer; opacity:.45; }
.onb-hint{
  margin:9px 2px 0;
  font-size:11px; line-height:1.55; color:#9A9AA2;
}

/* ---- 错误 ---- */
.onb-err{
  margin:11px 0 0;
  font-size:12px; line-height:1.5; color:var(--red);
  animation:onbErrIn .3s var(--out) both;
}
@keyframes onbErrIn{
  from{ opacity:0; transform:translateY(-4px); }
  to{ opacity:1; transform:none; }
}

/* ---- 底部 ---- */
.onb-bottom{
  padding:16px 24px calc(14px + env(safe-area-inset-bottom,0px));
}
.onb-cta{
  width:100%; height:56px;
  border:0; border-radius:16px;
  background:var(--k); color:#fff;
  font:inherit; font-size:15px; font-weight:600; letter-spacing:-.01em;
  cursor:pointer;
  transition:transform .18s var(--spring), background .2s var(--out), color .2s var(--out);
}
.onb-cta:active:not(:disabled){ transform:scale(.982); background:#000; }
.onb-cta:disabled{ background:#EFEFF3; color:#B6B6BE; cursor:default; }
.onb-foot{
  margin:10px 0 0; text-align:center;
  font-size:11px; letter-spacing:.005em; color:#A8A8B0;
}

/* ---- 过渡：步骤之间横向推进（新的一屏从右边进来，旧的往左出去） ---- */
.onb-step-enter-active,.onb-step-leave-active{
  transition:opacity .26s var(--out), transform .38s cubic-bezier(.22,.9,.28,1);
}
.onb-step-enter-from{ opacity:0; transform:translateX(38px); }
.onb-step-leave-to{ opacity:0; transform:translateX(-30px); }

.onb-fade-enter-active,.onb-fade-leave-active{ transition:opacity .28s var(--out), transform .36s cubic-bezier(.22,.9,.28,1); }
.onb-fade-enter-from{ opacity:0; transform:translateX(30px); }
.onb-fade-leave-to{ opacity:0; transform:translateX(-24px); }

.onb-num-enter-active,.onb-num-leave-active{ transition:opacity .2s ease, transform .26s var(--out); }
.onb-num-enter-from{ opacity:0; transform:translateY(12px); }
.onb-num-leave-to{ opacity:0; transform:translateY(-12px); }

.onb-grow-enter-active,.onb-grow-leave-active{ transition:opacity .24s var(--out), transform .28s var(--out); }
.onb-grow-enter-from,.onb-grow-leave-to{ opacity:0; transform:translateY(-6px); }

@media (prefers-reduced-motion: reduce){
  .onb-step-enter-active,.onb-step-leave-active,
  .onb-fade-enter-active,.onb-fade-leave-active,
  .onb-num-enter-active,.onb-num-leave-active,
  .onb-grow-enter-active,.onb-grow-leave-active,
  .onb-cta, .onb-dots span, .onb-in{ transition-duration:.01s !important; }
}
</style>
