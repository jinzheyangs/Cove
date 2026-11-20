<template>
<div class="mod">
  <p v-if="error" class="st-toast st-toast--err">{{ error }}</p>
  <p v-if="notice" class="st-toast st-toast--ok">{{ notice }}</p>

  <!-- 个人资料 -->
  <h4 class="st-sec">Profile</h4>
  <section class="st-grp">
    <!-- 头像行：整行可点，直接换图 -->
    <div class="st-row st-row--hero" @click="pickAvatar">
      <span class="st-ava">
        <img v-if="profile.avatar_url" :src="profile.avatar_url" alt="" />
        <span v-else class="st-ava__t">{{ (profile.nickname || '我').slice(0, 1) }}</span>
        <span class="st-ava__plus">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
            <path d="M12 6v12M6 12h12" />
          </svg>
        </span>
      </span>
      <span class="st-hero__txt">
        <b>{{ profile.nickname || (profile.phone ? '还没有昵称' : '还没有登录') }}</b>
        <span>{{ profile.phone ? '点击更换头像' : '先回登录页登录再看资料' }}</span>
      </span>
      <span class="st-chev" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
      <input ref="avatarInput" type="file" accept="image/png,image/jpeg,image/webp" @change="onPickAvatar" hidden />
    </div>

    <!-- 昵称：内联输入，点整行也能直接开始改 -->
    <div class="st-row" @click="focusNick">
      <span class="st-ic">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="8" r="3.6" /><path d="M4.6 20c0-3.9 3.3-5.8 7.4-5.8s7.4 1.9 7.4 5.8" />
        </svg>
      </span>
      <span class="st-lb">昵称</span>
      <input ref="nickInput" v-model="profile.nickname" class="st-inp" maxlength="50" placeholder="怎么叫你" />
    </div>

    <!-- 生日：点行展开日期抽屉 -->
    <button class="st-row" type="button" @click="toggleBirthday">
      <span class="st-ic">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3.4" y="9" width="17.2" height="11.2" rx="2.6" /><path d="M3.4 13.4h17.2M12 9v11.2" />
          <path d="M8.6 9c-1.7 0-2.7-1-2.7-2.1 0-1 .9-1.7 2-1.4 1.4.4 2.5 1.9 3.7 3.5M15.4 9c1.7 0 2.7-1 2.7-2.1 0-1-.9-1.7-2-1.4-1.4.4-2.5 1.9-3.7 3.5" />
        </svg>
      </span>
      <span class="st-lb">生日</span>
      <span class="st-val" :class="{ 'st-val--mute': !birthdayInput }">{{ birthdayText }}</span>
      <span class="st-chev" :class="{ 'st-chev--down': openBirthday }" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
    </button>
    <div class="st-drawer" :class="{ 'st-drawer--open': openBirthday }">
      <div class="st-drawer__in">
        <FancyDatePicker v-model="birthdayInput" :max="todayStr" compact simple
                         :auto-open="walkDate"
                         placeholder="选择生日" class="st-dp" />
        <button v-if="birthdayInput" class="st-mini" type="button" @click="birthdayInput = ''">清除</button>
      </div>
    </div>

    <div class="st-row st-row--static">
      <span class="st-ic">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 3.6h2.6l1.5 3.8-1.9 1.3a11.4 11.4 0 0 0 5.1 5.1l1.3-1.9 3.8 1.5v2.6c0 1-.8 1.8-1.8 1.7C11.4 18.2 5.8 12.6 5.3 6.4 5.2 5.4 6 4.6 7 4.6Z" />
        </svg>
      </span>
      <span class="st-lb">手机号</span>
      <span class="st-val">{{ maskPhone(profile.phone) || '—' }}</span>
    </div>
  </section>

  <!-- 我们的关系：纪念日（不是生日，生日在上面「我的资料」里） -->
  <h4 class="st-sec">Relationship</h4>
  <section class="st-grp">
    <!-- 起始日：打开的是首页那张卡同一个弹窗，改完四处一起变。
         引导里只问发起人；填完之后两个人谁都能改 -->
    <button class="st-row" type="button" @click="openStartDate">
      <span class="st-ic">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 20.2s-7-4.6-7-9.4A4.1 4.1 0 0 1 12 7a4.1 4.1 0 0 1 7 3.8c0 4.8-7 9.4-7 9.4Z" />
        </svg>
      </span>
      <span class="st-lb">恋爱纪念日</span>
      <span class="st-val" :class="{ 'st-val--todo': !relation.startSet }">
        {{ relation.startSet ? fmtDate(relation.startDate) : '未填' }}
      </span>
      <span class="st-chev" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
    </button>
  </section>

  <p class="st-foot">生日只属于你自己，提醒也只发给你；纪念日算的是你们两个人的日子。</p>

  <!-- 没改任何东西就不摆这个按钮：一改就从下面长出来，保存成功露一下「已保存」再收回去 -->
  <div class="st-cta-slot" :class="{ on: showCta }" aria-hidden="false">
    <button
      class="st-cta"
      :class="{ 'st-cta--done': saved }"
      :disabled="saving || !profile.phone"
      @click="saveProfile"
    >
      <span v-if="saved" class="st-cta__tick">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <path d="m5 12.5 4.5 4.5L19 7.5" />
        </svg>
      </span>
      <span>{{ saved ? '已保存' : (saving ? '保存中…' : '保存资料') }}</span>
    </button>
  </div>

  <!-- 账号安全 -->
  <h4 class="st-sec">Account</h4>
  <section class="st-grp">
    <button class="st-row" type="button" @click="showPwd = !showPwd">
      <span class="st-ic">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <rect x="4.5" y="10" width="15" height="10.4" rx="3" /><path d="M8 10V7.6a4 4 0 0 1 8 0V10" />
        </svg>
      </span>
      <span class="st-lb">修改密码</span>
      <span class="st-chev" :class="{ 'st-chev--down': showPwd }" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
    </button>
    <div class="st-drawer" :class="{ 'st-drawer--open': showPwd }">
      <div class="st-drawer__in st-drawer__in--col">
        <input v-model="pwd.old_password" class="st-fld" type="password" placeholder="当前密码" autocomplete="current-password" />
        <input v-model="pwd.new_password" class="st-fld" type="password" placeholder="新密码（至少 6 位）" autocomplete="new-password" />
        <button class="st-mini st-mini--dark st-mini--wide" type="button" :disabled="saving || !pwdCanSubmit" @click="savePassword">
          确认修改
        </button>
      </div>
    </div>

    <button v-if="couple" class="st-row" type="button" @click="openUnbind">
      <span class="st-ic st-ic--danger">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9.8 7.2 7.4 9.6a3.6 3.6 0 0 0 5.1 5.1l1.1-1.1" /><path d="M14.2 16.8l2.4-2.4a3.6 3.6 0 0 0-5.1-5.1L10.4 10.4" />
        </svg>
      </span>
      <span class="st-lb st-lb--danger">解除绑定</span>
      <span class="st-chev" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
    </button>
    <button class="st-row" type="button" @click="doLogout">
      <span class="st-ic">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14.2 5.4h3.2a1.8 1.8 0 0 1 1.8 1.8v9.6a1.8 1.8 0 0 1-1.8 1.8h-3.2" /><path d="M10.4 8.2 6.6 12l3.8 3.8M6.6 12h8.2" />
        </svg>
      </span>
      <span class="st-lb">退出登录</span>
      <span class="st-chev" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
    </button>
    <button class="st-row" type="button" @click="doLogoutAll">
      <span class="st-ic">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3.2" y="5.2" width="8.6" height="12.4" rx="1.8" /><rect x="14.2" y="8.4" width="6.6" height="9.6" rx="1.6" /><path d="M6.1 15.4h3" />
        </svg>
      </span>
      <span class="st-lb">退出所有设备</span>
      <span class="st-chev" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
    </button>

    <button class="st-row st-row--last" type="button" @click="openDelete">
      <span class="st-ic st-ic--danger">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6.6 7.4h10.8M9.6 7.4V5.9a1.3 1.3 0 0 1 1.3-1.3h2.2a1.3 1.3 0 0 1 1.3 1.3v1.5" /><path d="M8.4 7.4l.6 10.4a1.6 1.6 0 0 0 1.6 1.5h2.8a1.6 1.6 0 0 0 1.6-1.5L15.6 7.4" />
        </svg>
      </span>
      <span class="st-lb st-lb--danger">注销账号</span>
      <span class="st-chev" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m9 5.5 7 6.5-7 6.5" />
        </svg>
      </span>
    </button>
  </section>

  <!-- 解绑确认：先把「这段关系里攒下了什么」摆出来，再让人点确认 -->
  <Teleport to="body">
    <Transition name="ub">
      <div v-if="unbindOpen" class="ub-wrap">
        <div class="ub-mask" @click="closeUnbind"></div>
        <section class="ub-card">
          <span class="ub-grab" aria-hidden="true"></span>
          <h3 class="ub-t">解除绑定</h3>
          <p v-if="unbindStats" class="ub-sub">
            和 {{ unbindStats.partner_nickname || 'TA' }} 在一起
            <b>{{ unbindStats.days_together }}</b> 天
          </p>
          <p v-else class="ub-sub">正在数你们攒下的东西…</p>

          <div v-if="statRows.length" class="ub-items">
            <span v-for="r in statRows" :key="r.k" class="ub-item">
              <b>{{ r.v }}</b>{{ r.k }}
            </span>
          </div>
          <p v-else-if="unbindStats" class="ub-empty">这段关系里还没有记录</p>

          <p v-if="unbindErr" class="ub-err">{{ unbindErr }}</p>

          <div class="ub-acts">
            <button class="ub-close" type="button" :disabled="unbinding" @click="closeUnbind">再想想</button>
            <button class="ub-danger" type="button" :disabled="unbinding" @click="doUnbind">
              {{ unbinding ? '正在解除…' : '确认解除' }}
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>

  <!-- 注销确认：不可逆，所以要求重新输一次密码 -->
  <Teleport to="body">
    <Transition name="ub">
      <div v-if="deleteOpen" class="ub-wrap">
        <div class="ub-mask" @click="closeDelete"></div>
        <section class="ub-card">
          <span class="ub-grab" aria-hidden="true"></span>
          <h3 class="ub-t">注销账号</h3>
          <p class="ub-sub">
            账号会被匿名化，日记、秘密、清单这些个人内容会删除；
            金币流水和兑换记录保留，免得对方账目对不上。这一步不能撤回。
          </p>
          <input
            v-model="deletePwd"
            class="st-fld ub-fld"
            type="password"
            placeholder="输入登录密码确认"
            autocomplete="current-password"
          />
          <p v-if="deleteErr" class="ub-err">{{ deleteErr }}</p>
          <div class="ub-acts">
            <button class="ub-close" type="button" :disabled="deleting" @click="closeDelete">再想想</button>
            <button class="ub-danger" type="button" :disabled="deleting || !deletePwd" @click="doDeleteAccount">
              {{ deleting ? '正在注销…' : '确认注销' }}
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import {
  getMe, updateProfile, uploadAvatar, changePassword,
  getCouple, unbindCouple, getUsStats,
  deleteAccount, logout, logoutAll,
} from '../../api/settings.js';
import { useSession } from '../../composables/useSession.js';
import { relation, loadRelation, loadMe } from '../../composables/useCove.js';
import { openStartDate } from '../../composables/useStartDate.js';
import FancyDatePicker from '../../components/FancyDatePicker.vue';

const { forceLogout } = useSession();

/* 「在一起」这一行打开的是全站同一个「填起始日」弹窗（StartDateSheet），
   这里不再自己维护一套内联抽屉，免得两处逻辑漂移。 */

const profile = ref({ nickname: '', phone: '', avatar: '', avatar_url: '', birthday: null });
const couple = ref(null);
const birthdayInput = ref('');
const showPwd = ref(false);
const pwd = ref({ old_password: '', new_password: '' });
const saving = ref(false);
const error = ref('');
const notice = ref('');

/* 解绑二次确认（关系本身不需要在设置里维护：没绑定的人进不来） */
/* 解绑二次确认（弹层里先把这段关系的存量摆出来）
   原来走的是行内确认；改成弹层是因为要显示统计，行内塞不下 */
const unbindOpen = ref(false);
const unbinding = ref(false);
const unbindStats = ref(null);
const unbindErr = ref('');
/* 只列有内容的项：全是 0 的一排数字只会让人更困惑 */
const statRows = computed(() => {
  const s = unbindStats.value;
  if (!s) return [];
  const rows = [];
  if (s.diaries) rows.push({ k: ' 篇日记', v: s.diaries });
  if (s.secrets) rows.push({ k: ' 个秘密', v: s.secrets });
  if (s.todos_pending || s.todos_done) rows.push({ k: ' 件清单', v: s.todos_pending + s.todos_done });
  if (s.bills) rows.push({ k: ' 笔账', v: s.bills });
  if (s.anniversaries) rows.push({ k: ' 个纪念日', v: s.anniversaries });
  if (s.coins) rows.push({ k: ' 枚金币', v: s.coins });
  return rows;
});
const openBirthday = ref(false);

/* 头像 input 与昵称 input 都用 ref 直接控制：
   点整行就能弹选图 / 落光标，不依赖 label 的隐式行为 */
const avatarInput = ref(null);
const nickInput = ref(null);

/* 设计走查：?open=birthday|pwd|unbind 直接把抽屉摊开看样式 */
const _open = new URLSearchParams(location.search).get('open');
if (_open === 'birthday') openBirthday.value = true;
if (_open === 'pwd') showPwd.value = true;
if (_open === 'unbind') openUnbind();
if (_open === 'start') openStartDate();
/* ?openDate=1：把生日抽屉里的日历面板直接摊开 */
const walkDate = new URLSearchParams(location.search).get('openDate') === '1';
function pickAvatar(){
  if (!profile.value.phone) { flash('还没有登录，先回登录页', true); return; }
  avatarInput.value?.click();
}
function focusNick(){ nickInput.value?.focus(); }

const todayStr = (() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
})();

/* 保存反馈：只有改动过才让按钮亮起来，成功后有一下「已保存」 */
const initial = ref({ nickname: '', birthday: '' });
const saved = ref(false);
let savedTimer = 0;

const dirty = computed(() => (
  (profile.value.nickname || '') !== initial.value.nickname ||
  birthdayInput.value !== initial.value.birthday
));

/* 保存键只在「有改动 / 正在存 / 刚存好」时出现，平时根本不占地方 */
const showCta = computed(() => dirty.value || saving.value || saved.value);

const birthdayText = computed(() => {
  const v = birthdayInput.value;
  if (!v) return '未填写';
  const [y, m, d] = v.split('-');
  return `${y}年${Number(m)}月${Number(d)}日`;
});

const pwdCanSubmit = computed(() => pwd.value.old_password && pwd.value.new_password.length >= 6);

function maskPhone(p){
  if (!p) return '';
  return p.length === 11 ? `${p.slice(0,3)}****${p.slice(7)}` : p;
}
function flash(msg, isError){
  if (isError) { error.value = msg; notice.value = ''; }
  else { notice.value = msg; error.value = ''; }
  setTimeout(() => { error.value = ''; notice.value = ''; }, 2600);
}

async function load(){
  try {
    const [me, cp] = await Promise.all([getMe(), getCouple()]);
    profile.value = { ...profile.value, ...me };
    birthdayInput.value = me.birthday ? String(me.birthday) : '';
    initial.value = { nickname: profile.value.nickname || '', birthday: birthdayInput.value };
    couple.value = cp;
    // 天数、周年、进度都取自同一份真源，改起始日后全站同步
    if (cp) await loadRelation();
  } catch (e) {
    flash(e.message || '加载失败', true);
  }
}

async function onPickAvatar(e){
  const file = e.target.files?.[0];
  if (!file) return;
  saving.value = true;
  try {
    const up = await uploadAvatar(file);
    await updateProfile({ avatar: up.key });
    await load();
    await syncProfileEverywhere();
    flash('头像已更新');
  } catch (err) {
    flash(err.message || '头像上传失败', true);
  } finally {
    saving.value = false;
    e.target.value = '';
  }
}

/* 改完资料要让常驻页跟着变：生日会改写「我们」页与纪念日卡上的岁数/日期，
   昵称会改写首页问候 —— 所以重算全局 relation / me，再广播一次数据变更 */
async function syncProfileEverywhere(){
  try { await Promise.all([loadRelation(), loadMe()]); } catch (_) { /* 拉不到就等下一次 */ }
  window.dispatchEvent(new Event('cove:data'));
}

async function saveProfile(){
  if (!profile.value.phone) { flash('还没有登录，先回登录页', true); return; }
  if (!dirty.value) { flash('资料没有改动'); return; }
  saving.value = true;
  try {
    await updateProfile({ nickname: profile.value.nickname.trim(), birthday: birthdayInput.value || null });
    await load();
    await syncProfileEverywhere();
    flash('资料已保存');
    saved.value = true;
    clearTimeout(savedTimer);
    savedTimer = setTimeout(() => { saved.value = false; }, 2200);
  } catch (e) {
    flash(e.message || '保存失败', true);
  } finally {
    saving.value = false;
  }
}

async function savePassword(){
  if (!pwdCanSubmit.value) return;
  saving.value = true;
  try {
    await changePassword({ ...pwd.value });
    pwd.value = { old_password: '', new_password: '' };
    showPwd.value = false;
    flash('密码已修改');
  } catch (e) {
    flash(e.message || '修改失败', true);
  } finally {
    saving.value = false;
  }
}

/* ---- 抽屉：一次只开一个，收起来才有干净的行 ---- */
function toggleBirthday(){
  openBirthday.value = !openBirthday.value;
}

function fmtDate(d){
  if (!d) return '—';
  const [y, m, day] = String(d).split('-');
  return `${y}.${String(Number(m)).padStart(2, '0')}.${String(Number(day)).padStart(2, '0')}`;
}

/* ---- 解绑：弹层里先摆统计，再确认 ---- */
async function openUnbind(){
  unbindOpen.value = true;
  unbindErr.value = '';
  unbindStats.value = null;
  try {
    unbindStats.value = await getUsStats();
  } catch (e) {
    // 拉不到也要能解绑，只是把统计那一块留空并说明一句
    unbindErr.value = e?.message || '没能读到这段关系的记录数，仍然可以解除绑定';
  }
}
function closeUnbind(){
  if (unbinding.value) return;
  unbindOpen.value = false;
}
async function doUnbind(){
  if (unbinding.value) return;
  unbinding.value = true;
  unbindErr.value = '';
  try {
    await unbindCouple();
    /* 解绑成功：先把弹层收掉、按钮状态复位，再退登录。
       顺序反过来的话，这个 Teleport 到 body 上的弹层会盖在登录页上面，
       而且 unbinding 一直是 true，两个按钮全禁用 —— 界面上就成了「关不掉」。 */
    unbindOpen.value = false;
    unbinding.value = false;
    forceLogout('你们已经解除绑定，请重新登录');
  } catch (e) {
    unbinding.value = false;
    unbindErr.value = e.code === -2
      ? '请求超时了，解绑可能已经生效 —— 刷新一下页面确认'
      : (e.message || '操作失败');
  }
}

/* ---- 登录与注销 ---- */

/* 退出只退本机：带 refresh token 去后端吊销，然后清本地登录态 */
async function doLogout(){
  try {
    await logout();
  } catch (_) {
    /* 后端不通也要把人退出去，logout() 的 finally 已经清了令牌 */
  }
  forceLogout('已退出登录');
}

/* 退出所有设备：吊销这个账号的全部 refresh token，别的设备也被踢下线 */
async function doLogoutAll(){
  try {
    await logoutAll();
  } catch (_) {
    /* 同样：后端不通也要把本机退出去 */
  }
  forceLogout('已退出所有设备');
}

/* 注销：密码是后端硬要求（DeleteAccountRequest.password） */
const deleteOpen = ref(false);
const deletePwd = ref('');
const deleteErr = ref('');
const deleting = ref(false);

function openDelete(){
  deleteOpen.value = true;
  deletePwd.value = '';
  deleteErr.value = '';
}
function closeDelete(){
  if (deleting.value) return;
  deleteOpen.value = false;
}
async function doDeleteAccount(){
  if (deleting.value || !deletePwd.value) return;
  deleting.value = true;
  deleteErr.value = '';
  let ok = false;
  try {
    await deleteAccount({ password: deletePwd.value });
    ok = true;
    /* 同解绑：先把弹层收掉再退登录，不然它会盖在登录页上面 */
    deleteOpen.value = false;
    deletePwd.value = '';
  } catch (e) {
    deleteErr.value = e.code === -2
      ? '请求超时了，注销可能已经生效 —— 刷新一下页面确认'
      : (e.message || '注销失败');
  } finally {
    deleting.value = false;
  }
  if (ok) forceLogout('账号已注销');
}

/* 被强制登出（解绑 / 注销 / 别处踢下线）时把这些挂在 body 上的弹层一起收掉，
   并把按钮的忙碌态复位，免得下次进来还停在「正在…」 */
function onForcedLogout(){
  unbindOpen.value = false;
  unbinding.value = false;
  unbindErr.value = '';
  deleteOpen.value = false;
  deleting.value = false;
  deletePwd.value = '';
  deleteErr.value = '';
}

onMounted(() => {
  load();
  window.addEventListener('cove:logout', onForcedLogout);
  /* 走查：?open=delete 直接把注销弹层摊开（ref 都已初始化，放这儿最稳） */
  if (_open === 'delete') openDelete();
});
onBeforeUnmount(() => {
  clearTimeout(savedTimer);
  window.removeEventListener('cove:logout', onForcedLogout);
});
</script>

<style scoped>
/* ============================================================
   设置 · 与登录/注册同一套稿的语言
   浅灰底 + 纯白卡（1px 细边、20 圆角）、黑色线性图标、
   行高 56、发丝分隔线、纯黑主按钮、英文小节标；只有「危险」用红。
   类名统一 st- 前缀，避免和全局 app.css 撞名。
   ============================================================ */
.mod{
  --st-k:#111114;
  --st-k2:#8A8A92;
  --st-k3:#A8A8B0;
  --st-line:#EFEFF3;
  --st-line2:#F3F3F6;
  --st-red:#FF4D4F;
  --st-out:cubic-bezier(.16,1,.3,1);
  --st-spring:cubic-bezier(.34,1.4,.64,1);

  box-sizing:border-box; width:100%;
  padding:2px 16px 44px;
  background:#F4F4F6;
  color:var(--st-k);
  font-family:'Inter','PingFang SC','Microsoft YaHei',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
}

.st-toast{
  margin:6px 0 10px; padding:10px 14px; border-radius:12px;
  font-size:12.5px; background:#fff; border:1px solid var(--st-line);
}
.st-toast--err{ color:var(--st-red); border-color:#F5D4D5; background:#FFF8F8; }
.st-toast--ok{ color:var(--st-k); border-color:#E4E4EA; }

/* 英文小节标：细、小、宽字距，只做分区提示 */
.st-sec{
  margin:22px 4px 9px;
  font-size:10.5px; font-weight:700; letter-spacing:.17em;
  color:#9A9AA2; text-transform:uppercase;
}
.st-sec:first-of-type{ margin-top:8px; }

.st-grp{
  background:#fff; border-radius:20px; border:1px solid var(--st-line);
  overflow:hidden;
  animation:stGrpIn .5s var(--st-out) both;
}

.st-foot{
  margin:9px 6px 0; font-size:11.5px; line-height:1.55; color:var(--st-k2);
}

/* ---- 行 ---- */
.st-row{
  position:relative; display:flex; align-items:center; gap:13px;
  width:100%; min-height:56px; padding:0 18px;
  background:none; border:none; text-align:left; font:inherit; color:inherit;
  cursor:pointer;
  transition:background .16s var(--st-out);
}
.st-row:hover{ background:#FBFBFC; }
.st-row:active{ background:#F3F3F6; }
.st-row--static, .st-row--static:hover, .st-row--static:active{ background:none; cursor:default; }

/* 发丝分隔线：从图标处起，右侧顶到边 */
.st-row::before{
  content:''; position:absolute; left:18px; right:0; top:0; height:1px;
  background:var(--st-line2); transform:scaleY(.5); transform-origin:top;
}
.st-row:first-child::before{ display:none; }

/* 图标：只有黑色线条，没有任何色块 */
.st-ic{
  width:20px; height:20px; flex:0 0 auto;
  display:grid; place-items:center; color:var(--st-k); opacity:.9;
  transition:transform .24s var(--st-spring), opacity .2s var(--st-out);
}
.st-ic svg{ width:19px; height:19px; }
.st-ic--danger{ color:var(--st-red); }
.st-row:focus-within .st-ic{ transform:scale(1.08); opacity:1; }

.st-lb{ font-size:14.5px; font-weight:500; letter-spacing:-.005em; }
.st-lb--danger{ color:var(--st-red); }
.st-val{
  margin-left:auto; font-size:14.5px; color:#3B3B42; letter-spacing:-.005em;
  font-variant-numeric:tabular-nums;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.st-val--mute{ color:var(--st-k3); }
/* 起始日还没填：淡红提示词，而不是一个看着像已填好的日期 */
.st-val--todo{ color:#D9235A; font-weight:600; }

.st-chev{
  width:14px; height:14px; flex:0 0 auto; margin-left:4px; color:#C4C4CC;
  display:grid; place-items:center;
  transition:transform .3s var(--st-out), color .2s var(--st-out);
}
.st-chev svg{ width:13px; height:13px; }
.st-chev--down{ transform:rotate(90deg); color:var(--st-k); }

/* ---- 头像行 ---- */
.st-row--hero{ min-height:84px; padding:15px 18px; gap:15px; }
.st-ava{ position:relative; width:54px; height:54px; flex:0 0 auto; }
.st-ava img, .st-ava__t{
  width:54px; height:54px; border-radius:50%; object-fit:cover;
  display:grid; place-items:center; font-size:19px; font-weight:600; color:#fff;
  background:#111114;
  transition:transform .3s var(--st-spring);
}
.st-ava__plus{
  position:absolute; right:-3px; bottom:-3px; width:20px; height:20px; border-radius:50%;
  background:#fff; color:var(--st-k); display:grid; place-items:center;
  border:1px solid var(--st-line);
  box-shadow:0 1px 3px rgba(0,0,0,.1);
}
.st-ava__plus svg{ width:10px; height:10px; }
.st-row--hero:active .st-ava img,
.st-row--hero:active .st-ava__t{ transform:scale(.95); }

.st-hero__txt{ display:flex; flex-direction:column; gap:3px; min-width:0; }
.st-hero__txt b{
  font-size:16px; font-weight:600; letter-spacing:-.02em;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.st-hero__txt span{ font-size:11.5px; color:var(--st-k2); }

/* ---- 内联输入 ---- */
.st-inp{
  margin-left:auto; width:56%; min-width:0; height:38px; padding:0;
  border:none; background:none; outline:none;
  font:inherit; font-size:14.5px; color:var(--st-k); text-align:right;
  caret-color:var(--st-k);
}
.st-inp::placeholder{ color:var(--st-k3); }

/* ---- 抽屉 ---- */
.st-drawer{
  display:grid; grid-template-rows:0fr;
  transition:grid-template-rows .36s var(--st-out);
  position:relative;
}
.st-drawer--open{ grid-template-rows:1fr; }
.st-drawer__in{
  overflow:hidden;
  display:flex; align-items:center; gap:8px;
  padding:0 18px;
  background:#FAFAFB;
  transition:padding .36s var(--st-out);
}
.st-drawer--open .st-drawer__in{ padding:14px 18px; }
.st-drawer__in--col{ flex-direction:column; align-items:stretch; gap:9px; }
.st-dp{ flex:1; min-width:0; }

.st-date{
  flex:1; min-width:0; height:42px; padding:0 12px;
  border:1px solid var(--st-line); border-radius:12px;
  background:#fff; font:inherit; font-size:13.5px; color:var(--st-k);
  outline:none; caret-color:var(--st-k);
  transition:border-color .18s var(--st-out), box-shadow .18s var(--st-out);
}
.st-fld{
  height:44px; padding:0 13px; border:1px solid var(--st-line); border-radius:12px;
  background:#fff; font:inherit; font-size:14px; color:var(--st-k); outline:none;
  caret-color:var(--st-k);
  transition:border-color .18s var(--st-out), box-shadow .18s var(--st-out);
}
.st-date:focus, .st-fld:focus{
  border-color:var(--st-k);
  box-shadow:0 0 0 3px rgba(17,17,20,.06);
}

.st-mini{
  height:38px; padding:0 14px; border-radius:11px; border:1px solid #E7E7EC;
  background:#fff; font:inherit; font-size:13px; font-weight:500; color:var(--st-k);
  cursor:pointer; white-space:nowrap;
  transition:transform .16s var(--st-spring), background .18s var(--st-out), color .18s var(--st-out);
}
.st-mini:active{ transform:scale(.97); background:#F3F3F6; }
.st-mini--dark{ background:#111114; border-color:#111114; color:#fff; font-weight:600; }
.st-mini--dark:disabled{ background:#E7E7EC; border-color:#E7E7EC; color:#B4B4BC; cursor:default; }
.st-mini--danger{ background:var(--st-red); border-color:var(--st-red); color:#fff; font-weight:600; }
.st-mini--wide{ width:100%; margin-top:3px; height:44px; }

/* ---- 主按钮 ---- */
/* 收起来的槽：高度从 0 长出来，按钮跟一点点上浮，不是"啪"地蹦出来 */
.st-cta-slot{
  max-height:0; margin:0; opacity:0;
  overflow:hidden; pointer-events:none;
  transform:translateY(7px);
  transition:max-height .44s cubic-bezier(.22,.9,.3,1),
             margin .44s cubic-bezier(.22,.9,.3,1),
             opacity .3s ease,
             transform .5s var(--st-spring);
}
.st-cta-slot.on{
  max-height:110px; margin:16px 0 4px;
  opacity:1; pointer-events:auto;
  transform:none;
}

.st-cta{
  display:flex; align-items:center; justify-content:center; gap:7px;
  width:100%; height:56px; margin:0;
  border:none; border-radius:16px;
  background:#111114; color:#fff;
  font:inherit; font-size:15px; font-weight:600; letter-spacing:-.01em;
  cursor:pointer;
  transition:transform .2s var(--st-spring), background .26s var(--st-out), color .2s var(--st-out);
}
.st-cta:active:not(:disabled){ transform:scale(.982); background:#000; }
.st-cta:disabled{
  background:#EDEDF1; color:#B4B4BC; cursor:default;
}
.st-cta--done{ background:#111114; }
.st-cta__tick{ width:16px; height:16px; display:grid; place-items:center; }
.st-cta__tick svg{ width:16px; height:16px; }

/* ---- 解绑 / 注销确认弹层 ----
   从底部贴上来的 sheet：满宽、只做上圆角、阴影极淡，
   它属于这一页，不是飘在上面的另一层。
   宽度跟手机壳走 —— fixed 默认铺满浏览器窗口，桌面上会被拉成一整条全屏条。 */
.ub-wrap{
  position:fixed; top:0; bottom:0; left:0; right:0; margin:auto;
  width:var(--phone-w, 390px); height:var(--phone-h, 844px);
  max-width:100vw; max-height:100vh;
  z-index:9999;
  display:flex; align-items:flex-end; justify-content:center;
  padding:0;
  border-radius:52px; overflow:hidden;
}
@media (max-width:520px){
  .ub-wrap{ width:100%; height:100%; border-radius:0; }
}
.ub-mask{
  position:absolute; inset:0;
  background:rgba(74,40,58,.26);
  backdrop-filter:blur(10px) saturate(120%);
  -webkit-backdrop-filter:blur(10px) saturate(120%);
}
.ub-card{
  position:relative; width:100%;
  padding:8px 20px calc(20px + env(safe-area-inset-bottom, 0));
  border-radius:26px 26px 0 0;
  background:#fff;
  box-shadow:0 -6px 22px -16px rgba(150,60,110,.26);
}
.ub-grab{
  display:block; width:36px; height:4px; margin:0 auto 12px;
  border-radius:999px; background:rgba(185,125,155,.28);
}
.ub-t{
  margin:0 0 7px;
  font-size:18px; font-weight:800; letter-spacing:-.03em; color:#3A1C2C;
}
.ub-sub{
  margin:0 0 16px;
  font-size:13px; line-height:1.62; color:#8E7A88;
}
.ub-sub b{
  font-size:16px; font-weight:800; color:#3A1C2C; font-variant-numeric:tabular-nums;
}
.ub-items{
  display:flex; flex-wrap:wrap; gap:8px;
  margin:0 0 16px;
}
.ub-item{
  display:inline-flex; align-items:baseline;
  padding:7px 12px; border-radius:11px;
  background:#FFF5F8;
  font-size:12px; font-weight:600; color:#9A7A88;
  font-variant-numeric:tabular-nums;
  white-space:nowrap;
}
.ub-item b{
  margin-right:3px; font-size:14px; font-weight:800; color:#3A1C2C;
}
.ub-empty{
  margin:0 0 16px; font-size:13px; color:#C0A6B2;
}
.ub-err{
  margin:0 0 12px; font-size:12px; line-height:1.55; color:#E23B57;
}
/* 注销弹层要输密码，输入框沿用设置页那套字段样式，这里只把尺寸和配色压成 App 手感 */
.ub-fld{
  width:100%; box-sizing:border-box; margin:0 0 14px;
  height:48px; padding:0 15px; border-radius:15px;
  background:#fff;
  border:1px solid rgba(190,120,150,.28);
  box-shadow:none;
}
.ub-fld::placeholder{ color:#BBA2AC; }
.ub-fld:focus{
  border-color:rgba(255,120,165,.65);
  box-shadow:0 0 0 3px rgba(255,110,160,.14);
}
.ub-acts{ display:flex; gap:10px; }
/* 「再想想」是主按钮：手指最顺的位置留给安全选项，
   危险那个用红字白底，显眼但不诱导 */
.ub-close{
  flex:1; height:50px; border:0; border-radius:15px;
  background:linear-gradient(180deg,#FF86AB 0%,#FF4E82 100%); color:#fff;
  font:inherit; font-size:15px; font-weight:800; letter-spacing:-.01em;
  cursor:pointer;
  box-shadow:
    0 12px 22px -14px rgba(255,78,130,.75),
    inset 0 1px 0 rgba(255,255,255,.4);
  transition:transform .2s cubic-bezier(.34,1.4,.64,1), filter .26s ease;
}
.ub-close:active:not(:disabled){ transform:scale(.98); filter:brightness(.96); }
.ub-close:disabled{ background:#F2E6EB; color:#BBA7B0; box-shadow:none; cursor:default; }
.ub-danger{
  flex:1; height:50px; border-radius:15px;
  border:1px solid rgba(226,59,87,.34); background:#fff; color:#E23B57;
  font:inherit; font-size:15px; font-weight:700;
  cursor:pointer;
  box-shadow:none;
  transition:transform .2s cubic-bezier(.34,1.4,.64,1), background .2s ease, border-color .2s ease;
}
.ub-danger:active:not(:disabled){ transform:scale(.98); background:#FFF4F5; border-color:rgba(226,59,87,.5); }
.ub-danger:disabled{ color:#D9A5AE; border-color:rgba(226,59,87,.16); background:#FFFDFD; box-shadow:none; cursor:default; }

.ub-enter-active .ub-card{ animation:ubUp .38s cubic-bezier(.16,1,.3,1) both; }
.ub-enter-active .ub-mask{ animation:ubFade .28s ease both; }
.ub-leave-active .ub-card{ animation:ubUp .26s cubic-bezier(.4,0,1,1) reverse both; }
.ub-leave-active .ub-mask{ animation:ubFade .26s ease reverse both; }
@keyframes ubUp{
  from{ transform:translateY(102%); }
  to{ transform:none; }
}
@keyframes ubFade{
  from{ opacity:0; }
  to{ opacity:1; }
}

/* ---- 入场 ---- */
@keyframes stGrpIn{
  from{ opacity:0; transform:translateY(10px); }
  to{ opacity:1; transform:none; }
}
@keyframes stConfirmIn{
  from{ opacity:0; transform:translateY(-6px); }
  to{ opacity:1; transform:none; }
}

@media (prefers-reduced-motion: reduce){
  .st-grp{ animation:none; }
  .st-drawer, .st-drawer__in, .st-chev, .st-ic, .st-cta, .st-cta-slot, .st-mini,
  .st-ava img, .st-ava__t, .ub-close, .ub-danger{ transition:none; }
  .ub-enter-active .ub-card, .ub-leave-active .ub-card{ animation:none; }
}
</style>
