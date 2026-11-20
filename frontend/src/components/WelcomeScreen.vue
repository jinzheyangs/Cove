<template>
<div class="wl" :class="{ out: closing, shake }">
  <!-- 进入时的几步引导（沿用原来的引导流程） -->
  <OnboardingFlow
    v-if="stage === 'intro'"
    :steps="introSteps"
    :prefill="introPrefill"
    :start-at="introStartAt"
    @done="finishIntro"
  />

  <div v-else class="wl-shell">
    <div class="wl-top">
      <span class="wl-mark">cove</span>
      <span class="wl-mark-sub">两个人的地方</span>
    </div>

    <div class="wl-hero">
      <template v-if="stage === 'auth'">
        <h2 class="wl-slogan">把两个人的日子，<br />收在一个地方</h2>
        <p class="wl-slogan-sub">手机号就是账号，不用短信验证码</p>
      </template>
      <template v-else-if="partnerJoined">
        <h2 class="wl-slogan">已经连上了，<br />进去看看吧</h2>
        <p class="wl-slogan-sub">你的日子，从今天开始多一个人一起数</p>
      </template>
      <template v-else>
        <h2 class="wl-slogan">还差一步，<br />就绑在一起</h2>
        <p class="wl-slogan-sub">填 TA 的码，或者把你的发给 TA</p>
      </template>
    </div>

    <div class="wl-mid">
      <section :key="stage + mode" class="wl-card">
        <!-- ============ 登录 / 注册 ============ -->
        <div v-if="stage === 'auth'" class="pane">
          <h1 class="wl-h">{{ mode === 'login' ? 'Hi, Welcome! 👋' : 'Create account' }}</h1>
          <p class="wl-p">
            {{ mode === 'login' ? '用手机号登录，你们的时间和记录都还在。' : '先建个账号，再把 TA 拉进来。' }}
          </p>

          <div v-if="mode === 'register'" class="wl-f" :class="{ bad: errField === 'nickname' }">
            <label for="wl-nick">昵称</label>
            <div class="wl-in">
              <input id="wl-nick" v-model="nickname" maxlength="50" placeholder="给自己起个昵称" autocomplete="nickname" />
            </div>
          </div>

          <div class="wl-f" :class="{ bad: errField === 'phone' }">
            <label for="wl-phone">手机号</label>
            <div class="wl-in">
              <input
                id="wl-phone" ref="phoneInput"
                v-model="phone" inputmode="numeric" autocomplete="tel" maxlength="11"
                placeholder="11 位手机号"
                @input="phone = phone.replace(/\D/g, '').slice(0, 11)"
              />
              <button v-if="phone" type="button" class="wl-x" aria-label="清空" @click="phone = ''">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
                  <circle cx="12" cy="12" r="8.4" /><path d="m9.4 9.4 5.2 5.2M14.6 9.4l-5.2 5.2" />
                </svg>
              </button>
            </div>
          </div>

          <div class="wl-f" :class="{ bad: errField === 'password' }">
            <label for="wl-pw">密码</label>
            <div class="wl-in">
              <input
                id="wl-pw" v-model="password" :type="showPw ? 'text' : 'password'"
                :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
                placeholder="至少 6 位"
              />
              <button type="button" class="wl-eye" :class="{ open: showPw }"
                      :aria-label="showPw ? '隐藏密码' : '显示密码'" @click="showPw = !showPw">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
                  <path d="M2.6 12c2.2-3.9 5.6-5.9 9.4-5.9S19.2 8.1 21.4 12c-2.2 3.9-5.6 5.9-9.4 5.9S4.8 15.9 2.6 12Z" />
                  <circle cx="12" cy="12" r="2.6" />
                  <path v-if="!showPw" d="M4.4 19.6 19.6 4.4" stroke-width="1.8" />
                </svg>
              </button>
            </div>
          </div>

          <p v-if="error" class="wl-err">{{ error }}</p>

          <button class="wl-cta" :disabled="busy" @click="submitAuth">
            {{ busy ? '…' : (mode === 'login' ? 'Log in' : 'Sign up') }}
          </button>

          <p class="wl-alt">
            {{ mode === 'login' ? '还没有账号？' : '已经有账号？' }}
            <button type="button" class="wl-link" @click="switchMode(mode === 'login' ? 'register' : 'login')">
              {{ mode === 'login' ? 'Sign up' : 'Log in' }}
            </button>
          </p>
        </div>

        <!-- ============ 验证码（= 项目的配对码） ============ -->
        <div v-else class="pane">
          <!-- 对方已经绑上：等码的这一方不用刷新，这屏自己会发现 -->
          <template v-if="partnerJoined">
            <div class="wl-matched">
              <div class="wl-matched__badge">
                <span class="wl-matched__ring"></span>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M4.6 12.7 9.7 17.6 19.4 6.9" stroke="#fff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h1 class="wl-h">It's a match</h1>
              <p class="wl-p">TA 已经把码填上了，你们现在是一对。</p>
              <div class="wl-matched__pair">
                <span class="wl-matched__pill me">我</span>
                <span class="wl-matched__dash"><i></i><i></i><i></i></span>
                <span class="wl-matched__pill ta">TA</span>
              </div>
            </div>
            <button type="button" class="wl-cta" :disabled="busy" @click="enterNow">进入主页</button>
            <p class="wl-alt">
              不是你认识的 TA？
              <button type="button" class="wl-link" @click="switchAccount">换个账号登录</button>
            </p>
          </template>
          <template v-else>
          <h1 class="wl-h">Enter code</h1>
          <p class="wl-p">把 TA 的 6 位配对码填进来。一方绑定，两个人一起进主页。</p>

          <div class="wl-pin" :class="{ bad: errField === 'pin', filled: partnerCode.length === 6 }">
            <input
              ref="pinInput" v-model="partnerCode" class="wl-pin-in"
              inputmode="text" autocomplete="one-time-code" maxlength="6" aria-label="TA 的配对码"
              @input="onPin" @focus="pinFocus = true" @blur="pinFocus = false"
            />
            <div class="wl-pin-row" aria-hidden="true">
              <span
                v-for="n in 6" :key="n" class="cell"
                :class="{ on: pinFocus && activeIdx === n - 1, has: !!partnerCode[n - 1] }"
              >{{ partnerCode[n - 1] || '' }}</span>
            </div>
          </div>

          <p v-if="error" class="wl-err">{{ error }}</p>

          <div class="wl-mine">
            <div class="wl-mine-top">
              <span>我的配对码</span>
              <button v-if="myCode" type="button" class="wl-link" @click="copyCode">
                {{ copied ? '已复制' : '复制' }}
              </button>
            </div>
            <div v-if="myCode" class="wl-code">
              <span v-for="(c, i) in myCode.split('')" :key="i" :style="{ '--i': i }">{{ c }}</span>
            </div>
            <button v-else type="button" class="wl-ghost" :disabled="busy" @click="genCode">
              {{ busy ? '生成中…' : '生成我的配对码' }}
            </button>
            <p class="wl-hint">发给 TA，对方填进来就能绑上 · 24 小时有效</p>
          </div>

          <button class="wl-cta" :disabled="busy || partnerCode.length !== 6" @click="bind">
            {{ busy ? '绑定中…' : '绑定并进入' }}
          </button>

          <p class="wl-alt">
            绑上才能进主页 ·
            <button type="button" class="wl-link" @click="switchAccount">换个账号登录</button>
          </p>
          </template>
        </div>
        <p class="wl-foot">继续即表示同意 <u>用户协议</u> 与 <u>隐私政策</u></p>
      </section>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import OnboardingFlow from './OnboardingFlow.vue';
import { login, register } from '../api/auth.js';
import { getToken, clearToken } from '../api/token.js';
import { createInvite, bindCouple, getCouple } from '../api/settings.js';
import { buildIntroSteps, markIntroDone, resolveIntro } from '../composables/useOnboarding.js';

defineProps({ closing: { type: Boolean, default: false } });
const emit = defineEmits(['enter']);

const stage = ref('auth');      // auth | match | intro
const mode = ref('login');      // login | register
const phone = ref('');
const password = ref('');
const nickname = ref('');
const showPw = ref(false);
const myCode = ref('');
const copied = ref(false);
const partnerCode = ref('');
const busy = ref(false);
const error = ref('');
const errField = ref('');
const shake = ref(false);
const pinFocus = ref(false);
const phoneInput = ref(null);
const pinInput = ref(null);
/* 等码的一方：把码发出去之后就一直停在这屏，
   所以这里得自己盯着关系有没有绑上，绑上了立刻给出「进入」出口，
   别让 TA 以为卡住了、还要手动刷新。 */
const partnerJoined = ref(false);
let pairPoll = null;
const PAIR_POLL_MS = 4000;

/* 引导页 */
const currentCouple = ref(null);
const introSteps = ref(['nickname', 'birthday', 'start']);
const introPrefill = ref({});
const introStartAt = ref(0);

/* 设计走查：?stage=register / ?stage=match / ?stage=intro&step=N 直接看各屏 */
const _sp = new URLSearchParams(location.search).get('stage');
if (_sp === 'register') mode.value = 'register';
if (_sp === 'match') { myCode.value = 'C0VE24'; stage.value = 'match'; }
/* 走查「对方已经绑上」这一屏 */
if (_sp === 'matched') { myCode.value = 'C0VE24'; stage.value = 'match'; partnerJoined.value = true; }
if (_sp === 'intro') {
  introSteps.value = ['nickname', 'birthday', 'start'];
  const filled = new URLSearchParams(location.search).get('fill') === '1';
  introPrefill.value = filled
    ? { nickname: '小野', birthday: '2000-05-20', start_date: '2024-06-01' }
    : { nickname: '小野' };
  introStartAt.value = Math.max(0, parseInt(new URLSearchParams(location.search).get('step') || '1', 10) - 1);
  stage.value = 'intro';
}

const PHONE_RE = /^1[3-9]\d{9}$/;
/* 试用 / 走查：?code=XXXXXX 把对方的配对码预填进 6 格，省得手抄 */
const _preCode = new URLSearchParams(location.search).get('code');
if (_preCode) partnerCode.value = _preCode.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 6);
/* 已经登录、但还没绑定的：一打开就落在配对屏，别再让 TA 走一遍登录 */
if (!_sp && getToken()) stage.value = 'match';
const activeIdx = computed(() => Math.min(partnerCode.value.length, 5));

function setError(msg, field = ''){
  error.value = msg;
  errField.value = field;
  shake.value = false;
  requestAnimationFrame(() => { shake.value = true; setTimeout(() => { shake.value = false; }, 420); });
}

function switchMode(m){
  if (mode.value === m) return;
  mode.value = m;
  error.value = ''; errField.value = '';
}

async function submitAuth() {
  error.value = ''; errField.value = '';
  if (!PHONE_RE.test(phone.value)) {
    setError('请输入正确的 11 位手机号', 'phone');
    phoneInput.value?.focus({ preventScroll: true });
    return;
  }
  if (password.value.length < 6) {
    setError('密码至少 6 位', 'password');
    return;
  }
  if (mode.value === 'register' && !nickname.value.trim()) {
    setError('请填写昵称', 'nickname');
    return;
  }

  busy.value = true;
  try {
    if (mode.value === 'login') await login(phone.value, password.value);
    else await register(phone.value, password.value, nickname.value.trim());
    await routeAfterAuth();
  } catch (e) {
    setError(e.message || '操作失败，请重试');
  } finally {
    busy.value = false;
  }
}

/* 登录 / 注册成功后：
   已绑定的直接进主页（资料引导等真正进去之后再弹）；
   还没绑定的先看配对码这一屏 —— 绑上了才算进入，之后才轮到引导页 */
async function routeAfterAuth() {
  const info = await resolveIntro();
  currentCouple.value = info.couple;

  if (info.couple) { emit('enter'); return; }

  enterMatch();
}

function finishIntro() {
  markIntroDone();
  if (currentCouple.value) { emit('enter'); return; }
  enterMatch();
}

/* ---- 配对屏：等对方填码时自己盯关系 ---- */
function stopPairPoll(){
  if (pairPoll) { clearInterval(pairPoll); pairPoll = null; }
}
function startPairPoll(){
  stopPairPoll();
  pairPoll = setInterval(async () => {
    if (stage.value !== 'match' || partnerJoined.value) { stopPairPoll(); return; }
    if (typeof document !== 'undefined' && document.hidden) return; // 切后台就先别打扰后端
    try {
      const couple = await getCouple();
      if (couple) {
        partnerJoined.value = true;
        stopPairPoll();
      }
    } catch (_) { /* 网络抖动：下一轮再试 */ }
  }, PAIR_POLL_MS);
}
/* 进配对屏的唯一入口：补「我的码」+ 开始盯关系 */
function enterMatch(){
  stage.value = 'match';
  error.value = '';
  partnerJoined.value = false;
  if (!myCode.value) genCode();
  startPairPoll();
}
/* 对方已经绑上，用户点「进入主页」 */
function enterNow(){
  stopPairPoll();
  emit('enter');
}

async function genCode() {
  error.value = '';
  busy.value = true;
  try {
    const invite = await createInvite();
    myCode.value = String(invite.code || '');
  } catch (e) {
    setError(e.message || '生成失败，请重试');
  } finally {
    busy.value = false;
  }
}

async function copyCode(){
  try {
    await navigator.clipboard?.writeText(myCode.value);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 1600);
  } catch (_) { /* 复制失败不影响流程，用户可手动抄写 */ }
}

function onPin(e){
  partnerCode.value = e.target.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 6);
  error.value = ''; errField.value = '';
}

async function bind() {
  error.value = '';
  busy.value = true;
  try {
    await bindCouple({ code: partnerCode.value });
    /* 绑上了 = 进主页；缺的昵称 / 生日 / 在一起日期由主页那一层接着问，
       绑完直接交给它，别在这里多绕一圈 */
    stopPairPoll();
    emit('enter');
  } catch (e) {
    setError(e.message || '配对码不对，再核一遍', 'pin');
  } finally {
    busy.value = false;
  }
}

/* 配对屏的出口：不绑就不进主页，但允许换个账号重来（否则会锁死在这屏） */
function switchAccount(){
  stopPairPoll();
  partnerJoined.value = false;
  clearToken();
  myCode.value = '';
  partnerCode.value = '';
  phone.value = '';
  password.value = '';
  nickname.value = '';
  error.value = '';
  errField.value = '';
  stage.value = 'auth';
  mode.value = 'login';
}

/* 打开这一屏时如果已经是登录态：读一下关系，没绑就补上「我的码」 */
onMounted(async () => {
  if (_sp || !getToken()) return;
  try {
    const info = await resolveIntro();
    currentCouple.value = info.couple;
    if (info.couple) return;
    enterMatch();
  } catch (_) {
    /* 令牌失效之类：留在登录屏，让 TA 重新登 */
  }
});

onBeforeUnmount(() => stopPairPoll());
</script>

<style scoped>
/* ============================================================
   登录 / 注册 / 验证码
   参照稿的语言：深色底 + 白色大圆角卡、Inter 超粗标题、
   1px 细边输入框、纯黑主按钮、6 格验证码；错误态红边 + 红字。
   ============================================================ */
.wl{
  --ink:#111114;
  --ink2:#8A8A92;
  --ink3:#A8A8B0;
  --line:#EAEAEF;
  --line2:#F1F1F5;
  --red:#FF4D4F;
  --dark:#17171B;
  --out:cubic-bezier(.16,1,.3,1);
  --spring:cubic-bezier(.34,1.4,.64,1);

  position:absolute; inset:0; z-index:50;
  /* 深色底 + 恋爱感光晕（与引导页同一套）：远看是黑，边缘透玫瑰与淡紫 */
  background:
    radial-gradient(84% 56% at 94% -10%, rgba(255,110,164,.36) 0%, rgba(255,110,164,0) 64%),
    radial-gradient(74% 50% at -2% 4%, rgba(150,118,255,.24) 0%, rgba(150,118,255,0) 66%),
    radial-gradient(124% 58% at 50% 108%, rgba(255,168,132,.18) 0%, rgba(255,168,132,0) 68%),
    linear-gradient(180deg, #23232C 0%, #191920 40%, #151519 100%);
  color:var(--ink);
  font-family:'Inter','PingFang SC','Microsoft YaHei',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
  opacity:1; transition:opacity .5s ease, transform .5s var(--out);
}
.wl.out{ opacity:0; transform:scale(1.015); pointer-events:none; }

.wl-shell{
  height:100%; overflow-y:auto;
  display:flex; flex-direction:column;
  padding:calc(14px + env(safe-area-inset-top,0px)) 18px calc(14px + env(safe-area-inset-bottom,0px));
  scrollbar-width:none;
}
.wl-shell::-webkit-scrollbar{ display:none; }

.wl-top{ display:flex; align-items:baseline; gap:9px; padding:4px 6px 0; flex:0 0 auto; }
.wl-mark{
  font-size:19px; font-weight:800; letter-spacing:-.05em; color:#fff;
}
.wl-mark-sub{ font-size:10.5px; letter-spacing:.14em; color:rgba(255,255,255,.42); }

/* 深色上半屏：一句 slogan 压在卡片上方，把空出来的黑填得有意义 */
.wl-hero{
  flex:1 1 auto; display:flex; flex-direction:column; justify-content:flex-end;
  padding:0 8px 24px; min-height:72px;
}
.wl-slogan{
  margin:0; font-size:26px; line-height:1.32; font-weight:600;
  letter-spacing:-.01em; color:#fff;
}
.wl-slogan-sub{
  margin:10px 0 0; font-size:11.5px; letter-spacing:.01em; color:rgba(255,255,255,.4);
}

.wl-mid{ flex:0 0 auto; padding:0; }

/* ---- 白卡 ---- */
.wl-card{
  width:100%; background:#fff; border-radius:26px;
  padding:26px 20px 22px;
  box-shadow:0 -8px 40px -24px rgba(0,0,0,.6);
  animation:cardIn .62s var(--out) both;
}
@keyframes cardIn{
  from{ opacity:0; transform:translateY(18px) scale(.985); }
  to{ opacity:1; transform:none; }
}
.wl.shake .wl-card{ animation:cardShake .42s var(--spring) both; }
@keyframes cardShake{
  0%,100%{ transform:translateX(0); }
  22%{ transform:translateX(-5px); }
  46%{ transform:translateX(4px); }
  70%{ transform:translateX(-2px); }
}

.pane{ animation:paneIn .4s var(--out) both; }
@keyframes paneIn{
  from{ opacity:0; transform:translateY(10px); }
  to{ opacity:1; transform:none; }
}

/* ---- 标题 ---- */
.wl-h{
  margin:0; font-size:33px; line-height:1.06; font-weight:900;
  letter-spacing:-.042em; color:var(--ink);
}
.wl-p{
  margin:10px 0 0; font-size:13px; line-height:1.55; color:var(--ink2);
  letter-spacing:-.005em;
}

/* ---- 字段 ---- */
.wl-f{ margin-top:18px; }
.wl-f label{
  display:block; margin:0 0 8px; font-size:12.5px; font-weight:600;
  letter-spacing:-.005em; color:var(--ink);
}
.wl-in{
  position:relative; display:flex; align-items:center;
  height:56px; padding:0 14px;
  border:1px solid var(--line); border-radius:13px; background:#fff;
  transition:border-color .18s var(--out), box-shadow .18s var(--out);
}
.wl-in:focus-within{ border-color:var(--ink); box-shadow:0 0 0 3px rgba(17,17,20,.06); }
.wl-f.bad .wl-in{ border-color:var(--red); box-shadow:0 0 0 3px rgba(255,77,79,.1); }
.wl-in input{
  flex:1; min-width:0; height:100%; border:none; outline:none; background:none;
  font:inherit; font-size:15px; color:var(--ink); letter-spacing:-.01em;
  caret-color:var(--ink);
}
.wl-in input::placeholder{ color:var(--ink3); font-weight:400; }

.wl-x, .wl-eye{
  flex:0 0 auto; width:26px; height:26px; margin-left:6px;
  display:grid; place-items:center;
  border:none; background:none; padding:0; cursor:pointer;
  color:#B6B6BE;
  transition:color .18s var(--out), transform .18s var(--spring);
}
.wl-x svg, .wl-eye svg{ width:18px; height:18px; }
.wl-x:active, .wl-eye:active{ transform:scale(.9); }
.wl-eye.open{ color:var(--ink); }

/* ---- 错误 ---- */
.wl-err{
  margin:14px 0 0; font-size:12.5px; line-height:1.5; color:var(--red);
  animation:errIn .3s var(--out) both;
}
@keyframes errIn{
  from{ opacity:0; transform:translateY(-4px); }
  to{ opacity:1; transform:none; }
}

/* ---- 主按钮 ---- */
.wl-cta{
  width:100%; height:58px; margin-top:20px;
  border:none; border-radius:14px; background:var(--ink); color:#fff;
  font:inherit; font-size:15.5px; font-weight:600; letter-spacing:-.01em;
  cursor:pointer;
  transition:transform .18s var(--spring), background .2s var(--out), opacity .2s var(--out);
}
.wl-cta:active:not(:disabled){ transform:scale(.982); background:#000; }
.wl-cta:disabled{ background:#EFEFF3; color:#B6B6BE; cursor:default; }

/* ---- 切换账号 ---- */
.wl-alt{
  margin:16px 0 0; text-align:center; font-size:13px; color:var(--ink2);
}
.wl-link{
  border:none; background:none; padding:0 2px; cursor:pointer;
  font:inherit; font-size:13px; font-weight:700; color:var(--ink);
  letter-spacing:-.01em;
  transition:opacity .18s var(--out);
}
.wl-link:active{ opacity:.55; }

/* ---- 验证码 ---- */
.wl-pin{
  position:relative; margin-top:20px;
  height:52px;
}
.wl-pin-in{
  position:absolute; inset:0; width:100%; height:100%;
  border:none; outline:none; background:transparent;
  opacity:0; font-size:16px; letter-spacing:1em;
  color:transparent; caret-color:transparent;
  z-index:2;
}
.wl-pin-row{ display:flex; gap:7px; height:100%; }
.cell{
  flex:1; height:100%; display:grid; place-items:center;
  border:1px solid var(--line); border-radius:12px; background:#fff;
  font-size:21px; font-weight:600; color:var(--ink);
  font-variant-numeric:tabular-nums;
  transition:border-color .18s var(--out), transform .22s var(--spring),
              background .18s var(--out), color .18s var(--out);
}
.cell.on{ border-color:var(--ink); box-shadow:0 0 0 3px rgba(17,17,20,.06); }
.cell.has{ background:#FAFAFB; }
.wl-pin.filled .cell{ border-color:var(--ink); }
.wl-pin.bad .cell{ border-color:var(--red); background:#FFF7F7; color:var(--red); }

/* ---- 我的配对码 ---- */
.wl-mine{
  margin-top:20px; padding:16px 16px 14px;
  border:1px solid var(--line); border-radius:16px; background:#FCFCFD;
}
.wl-mine-top{
  display:flex; align-items:center; justify-content:space-between;
  font-size:12.5px; font-weight:600; color:var(--ink);
}
.wl-code{
  display:flex; align-items:baseline; justify-content:center; gap:6px;
  margin-top:14px;
  font-size:33px; font-weight:800; letter-spacing:0; color:var(--ink);
  font-variant-numeric:tabular-nums;
}
.wl-code span{
  display:inline-block;
  animation:cellIn .5s var(--out) both;
  animation-delay:calc(var(--i) * 55ms);
}
@keyframes cellIn{
  from{ opacity:0; transform:translateY(-6px) scale(.96); }
  to{ opacity:1; transform:none; }
}
.wl-ghost{
  width:100%; height:44px; margin-top:12px;
  border:1px dashed #D5D5DD; border-radius:11px; background:#fff;
  font:inherit; font-size:13px; font-weight:600; color:var(--ink);
  cursor:pointer;
  transition:background .18s var(--out), border-color .18s var(--out);
}
.wl-ghost:active{ background:#F4F4F7; }
.wl-ghost:disabled{ opacity:.5; cursor:default; }
.wl-hint{
  margin:11px 0 0; font-size:11.5px; line-height:1.5; color:var(--ink2);
}

/* ---- 对方已经绑上：It's a match ---- */
.wl-matched{
  display:flex; flex-direction:column; align-items:center; text-align:center;
  padding:2px 0 4px;
  animation:matchIn .56s var(--out) both;
}
@keyframes matchIn{
  from{ opacity:0; transform:translateY(10px); }
  to{ opacity:1; transform:none; }
}
.wl-matched__badge{
  position:relative; width:84px; height:84px; margin:2px 0 20px;
  display:grid; place-items:center; border-radius:50%;
  background:linear-gradient(158deg,#FF80AB 0%,#F13C6E 58%,#E2285C 100%);
  box-shadow:0 18px 34px -14px rgba(241,60,110,.62), inset 0 0 0 1px rgba(255,255,255,.34);
  animation:badgePop .62s var(--spring) both;
}
@keyframes badgePop{
  from{ opacity:0; transform:scale(.52); }
  62%{ transform:scale(1.07); }
  to{ opacity:1; transform:scale(1); }
}
/* 一圈慢慢扩开的光环：提示「刚刚成了」，不闪不躁 */
.wl-matched__ring{
  position:absolute; inset:-10px; border-radius:50%;
  border:1.5px solid rgba(241,60,110,.42);
  animation:matchRing 2.4s ease-out infinite;
}
@keyframes matchRing{
  0%{ transform:scale(.86); opacity:.85; }
  70%{ transform:scale(1.22); opacity:0; }
  100%{ transform:scale(1.22); opacity:0; }
}
.wl-matched__pair{
  display:flex; align-items:center; gap:9px; margin-top:18px;
}
.wl-matched__pill{
  display:inline-flex; align-items:center; justify-content:center;
  height:30px; padding:0 15px; border-radius:999px;
  font-size:12.5px; font-weight:700; letter-spacing:.4px;
}
.wl-matched__pill.me{
  background:#FCECF1; color:#D9235A; box-shadow:inset 0 0 0 1px rgba(217,35,90,.16);
}
.wl-matched__pill.ta{
  background:#F1F1F5; color:#52525B; box-shadow:inset 0 0 0 1px rgba(0,0,0,.06);
}
/* 中间三段小点：一左一右「连上」的暗示，依次亮起来 */
.wl-matched__dash{ display:flex; align-items:center; gap:5px; }
.wl-matched__dash i{
  width:5px; height:5px; border-radius:50%; background:#E4E4EA;
  animation:dotPulse 1.6s ease-in-out infinite;
  animation-delay:calc(var(--k,0) * 0ms);
}
.wl-matched__dash i:nth-child(1){ animation-delay:0s; }
.wl-matched__dash i:nth-child(2){ animation-delay:.22s; background:#F4B7C8; }
.wl-matched__dash i:nth-child(3){ animation-delay:.44s; }
@keyframes dotPulse{
  0%,100%{ opacity:.55; transform:scale(.86); }
  50%{ opacity:1; transform:scale(1); background:#F13C6E; }
}
/* 减动效：只留静态终态，别留下半透明的一帧 */
@media (prefers-reduced-motion: reduce){
  .wl-matched, .wl-matched__badge{ animation-duration:.01s !important; animation-delay:0s !important; }
  .wl-matched__ring{ display:none; }
  .wl-matched__dash i{ animation-duration:.01s !important; animation-delay:0s !important; opacity:1; }
}

/* ---- 底部 ---- */
.wl-foot{
  margin:18px 0 0; text-align:center;
  font-size:11px; line-height:1.6; color:#9A9AA2;
}
.wl-foot u{ text-decoration-color:#D5D5DD; }

@media (prefers-reduced-motion: reduce){
  .wl-card, .wl.shake .wl-card, .pane, .wl-err, .cell, .wl-code span{ animation:none; }
  .wl-cta:active, .wl-x:active, .wl-eye:active{ transform:none; }
}
</style>
