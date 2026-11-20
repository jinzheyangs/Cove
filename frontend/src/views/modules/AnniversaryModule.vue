<template>
<div class="an-page">
  <!-- 深色页头：借 Welcome 屏的深蓝灰 + 手撕波浪 -->
  <article class="an-hero">
    <span class="an-hero__glow" aria-hidden="true"></span>
    <svg class="an-hero__sky" viewBox="0 0 40 40" aria-hidden="true">
      <path d="M12 8 l2 4.4 4.4 2 -4.4 2 -2 4.4 -2 -4.4 -4.4 -2 4.4 -2 Z" fill="rgba(255,255,255,.5)" />
      <path d="M29 21 l1.3 2.9 2.9 1.3 -2.9 1.3 -1.3 2.9 -1.3 -2.9 -2.9 -1.3 2.9 -1.3 Z" fill="rgba(255,255,255,.26)" />
    </svg>

    <div class="an-hero__top">
      <span class="an-eb">{{ isPhantom(nextOne) ? '还没有纪念日' : (heroIsElapsed ? '我们已经走过' : '下一个值得期待的日子') }}</span>
      <span v-if="nextOne && !isPhantom(nextOne)" class="an-pill" :data-s="nextOne.source" :data-m="nextOne.mode">{{ sourceLabel(nextOne) }}</span>
    </div>

    <template v-if="nextOne && !isPhantom(nextOne)">
      <span class="an-big__lb">{{ heroIsElapsed ? '已经' : '还有' }}</span>
      <div class="an-big" :class="{ today: nextOne.is_today }">
        <b v-if="!nextOne.is_today">{{ shownDays }}</b>
        <b v-else>今天</b>
        <i v-if="!nextOne.is_today">天</i>
      </div>

      <h3 class="an-hero__title">{{ nextOne.title }}</h3>
      <p class="an-hero__date">
        <template v-if="heroIsDoneTarget">{{ fmtDate(nextOne.date) }} · 那天已经过去了</template>
        <template v-else-if="heroIsElapsed">
          {{ fmtDate(nextOne.date) }} 起 · {{ heldText(nextOne) || '刚开始' }}
        </template>
        <template v-else>
          {{ fmtDate(nextOne.next_date) }}
          <template v-if="nextOne.years"> · 那天满 {{ yearsText(nextOne) }}</template>
          <template v-if="nextOne.note"> · {{ nextOne.note }}</template>
          <template v-if="!nextOne.repeat_yearly"> · 只过一次</template>
        </template>
      </p>

      <!-- 只有「按年循环」的日子才有一年一度的周期，一次性节点（第 1000 天、某一天）没有进度可言 -->
      <div v-if="!heroIsDoneTarget && pctFor(nextOne) !== null" class="an-hero__bar">
        <i :style="{ width: (pctFor(nextOne) * 100).toFixed(1) + '%', background: ringColor(nextOne) }"></i>
      </div>
      <div
        v-if="!heroIsDoneTarget"
        class="an-hero__meta" :class="{ 'an-hero__meta--solo': true }"
      >
        <span v-if="pctFor(nextOne) !== null">这一年走过 {{ Math.round(pctFor(nextOne) * 100) }}%</span>
        <!-- 大字已经把「还有 N 天」说完了，这一行别再复读一遍，
             换成那天是周几；只有「已经走过多少天」那种口径才需要补下一个周年 -->
        <span v-if="heroIsElapsed">还差 {{ nextOne.days_left || 0 }} 天到下一个周年</span>
        <span v-else-if="nextOne.is_today">好好过今天</span>
        <span v-else>那天是{{ weekdayText(nextOne.next_date) }}</span>
      </div>
    </template>

    <!-- 在一起那天没填：最上面这块不该摆一个假的「今天 / 100%」，
         直接说清楚缺什么，让人去补 -->
    <template v-else-if="nextOne">
      <span class="an-big__lb">纪念日</span>
      <div class="an-big an-big--todo"><b>待填</b></div>
      <p class="an-hero__date">还没填你们在一起的那天</p>
      <div class="an-hero__meta">
        <span>填上之后，这里开始数天数</span>
        <span>100 天、一周年也会跟着长出来</span>
      </div>
    </template>

    <div v-else class="an-hero__empty">
      <b>—</b>
      <h3 class="an-hero__title">还没有日子</h3>
      <p class="an-hero__date">加一个日子，让它有个盼头</p>
    </div>

    <svg class="an-wave" viewBox="0 0 240 34" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0 9 C 26 -1, 50 15, 78 11 C 104 7, 116 1, 142 6 C 168 11, 184 17, 210 11 C 224 8, 232 4, 240 8 L 240 34 L 0 34 Z" />
    </svg>
  </article>

  <!-- 概览：三块色卡，借 What-you-need 的色板 -->
  <div v-if="items.length" class="an-stats">
    <div class="an-stat" data-c="violet" style="--si:0ms">
      <b>{{ items.length }}</b>
      <span>个日子</span>
    </div>
    <button type="button" class="an-stat an-stat--tap" data-c="peach" style="--si:55ms" @click="openYearSheet">
      <b>{{ thisYearCount }}</b>
      <span>今年还有<em class="an-stat__go" aria-hidden="true">›</em></span>
    </button>
    <div class="an-stat" data-c="blush" style="--si:110ms">
      <b>{{ todayCount }}</b>
      <span>就在今天</span>
    </div>
  </div>

  <!-- 「今年还有」点开：看看今年剩下的日子都是哪些 -->
  <Transition name="ys">
    <div v-if="yearSheet" class="an-year__mask" @click.self="yearSheet = false">
      <section class="an-year">
        <i class="an-year__bar" aria-hidden="true"></i>
        <h4>今年还有 <b class="an-year__n">{{ thisYearCount }}</b> 个日子</h4>
        <p class="an-year__sub">今天之后 · {{ TODAY0.getFullYear() }} 年 12 月 31 日之前</p>

        <div v-if="!thisYearItems.length" class="an-year__empty">
          <b>今年剩下的日子里没有要等的了</b>
          <span>明年的日子照旧会提前冒出来</span>
        </div>
        <ul v-else class="an-year__list">
          <li v-for="it in thisYearItems" :key="it.title + it.next_date">
            <i class="an-year__dot" :style="{ background: ringColor(it) }" aria-hidden="true"></i>
            <div class="an-year__body">
              <b>{{ it.title }}</b>
              <span>{{ fmtDate(it.next_date) }}</span>
            </div>
            <em>还有 {{ it.days_left }} 天</em>
          </li>
        </ul>

        <button type="button" class="an-year__close" @click="yearSheet = false">知道了</button>
      </section>
    </div>
  </Transition>

  <!-- 筛选 -->
  <div class="an-chips">
    <button
      v-for="f in FILTERS" :key="f.key"
      class="an-chip" :class="{ on: filter === f.key }"
      @click="filter = f.key"
    >{{ f.label }}</button>
  </div>

  <!-- 新建 / 编辑 -->
  <button v-if="!form.open" class="an-add" @click="openForm()">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
    添加一个日子
  </button>

  <form v-else class="an-form" @submit.prevent="submit">
    <div class="an-form__head">
      <h4>{{ form.id ? '改一下这个日子' : '新的日子' }}</h4>
      <button type="button" class="an-x" @click="closeForm" aria-label="关闭">×</button>
    </div>

    <label class="an-field">
      <span>叫什么</span>
      <input class="an-input" v-model="form.title" maxlength="50" placeholder="第一次旅行 / 搬进新家…" />
    </label>

    <!-- 节日不是自动上页头的：想让它出现，点这里一键变成你的目标日 -->
    <div v-if="!form.id && holidays.length" class="an-quick">
      <span class="an-quick__lb">最近的节日</span>
      <button
        v-for="h in holidays.slice(0, 5)" :key="h.key + h.iso"
        type="button" class="an-quick__c" @click="pickHoliday(h)"
      >
        {{ h.name }}
        <i>{{ h.gap === 0 ? '就是今天' : '还有 ' + h.gap + ' 天' }}</i>
      </button>
    </div>

    <div class="an-field">
      <span>哪种日子</span>
      <div class="an-kinds">
        <button
          type="button" class="an-kind" :class="{ on: form.mode === 'countdown' }"
          @click="pickMode('countdown')"
        >目标日</button>
        <button
          type="button" class="an-kind" :class="{ on: form.mode === 'elapsed' }"
          @click="pickMode('elapsed')"
        >纪念日</button>
      </div>
      <p class="an-hint">
        {{ form.mode === 'elapsed'
          ? '从那天算起，显示「已经 N 天」，还会长出 100 天、200 天、一周年这些节点——在一起、结婚、搬进新家'
          : '等那一天到来，显示「还有 N 天」；那天过了之后，就改成「已经 N 天」——生日、要一起去做的事' }}
      </p>
    </div>

    <div class="an-field an-field--date">
      <span>哪一天</span>
      <button type="button" class="an-date" :class="{ on: calOpen }" @click="toggleCal">
        <span class="an-date__txt" :class="{ ph: !form.date }">{{ form.date ? prettyDate(form.date) : '选一个日子' }}</span>
        <svg class="an-date__ico" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="4" y="5.5" width="16" height="13.5" rx="3.5" />
          <path d="M7 3v3M17 3v3M4 9.6h16" />
        </svg>
      </button>
      <p v-if="form.mode === 'elapsed'" class="an-hint">纪念日从那天算起，只能选今天或更早</p>

      <Transition :css="false" @enter="onCalEnter" @leave="onCalLeave">
        <div v-if="calOpen" class="an-cal">
          <CalendarBoard
            :model-value="form.date"
            :max="form.mode === 'elapsed' ? TODAY_ISO : ''"
            @update:model-value="onCalPick"
          />
        </div>
      </Transition>
    </div>

    <div class="an-switch-row" @click="form.repeat = !form.repeat">
      <i class="an-switch" :class="{ on: form.repeat }"><i></i></i>
      <span>每年都要过一次（关掉就是只过一次的事）</span>
    </div>

    <div class="an-form__btns">
      <button type="button" class="an-btn an-btn--ghost" @click="closeForm">取消</button>
      <button type="submit" class="an-btn" :disabled="!canSubmit || saving">
        {{ saving ? '保存中…' : '存下' }}
      </button>
    </div>

    <p v-if="formError" class="an-warn">{{ formError }}</p>
  </form>

  <p v-if="error" class="an-warn an-warn--box">{{ error }}</p>

  <!-- 列表 -->
  <div class="an-sec">
    <h4>全部日子</h4>
    <p v-if="visible.length">{{ visible.length }} 个</p>
  </div>

  <div v-if="loading" class="an-card an-loading"><i></i><i></i><i></i></div>

  <div v-else-if="!visible.length" class="an-card an-empty">
    <span class="an-empty__ico" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8c1.6-2.6 5.6-2.2 5.6 1 0 2.6-3.2 4.4-5.6 6.6C9.6 13.4 6.4 11.6 6.4 9c0-3.2 4-3.6 5.6-1Z"/></svg>
    </span>
    <b>这里还是空的</b>
    <span>先加一个对你们有意义的日子吧</span>
  </div>

  <div v-else class="an-list">
    <template v-for="g in groups" :key="g.key">
      <h5 v-if="g.label && groupCount > 1" class="an-group">{{ g.label }}</h5>

      <article
        v-for="(it, ri) in g.items"
        :key="kit(it)"
      class="an-row"
      :class="{ today: it.is_today && !isPhantom(it) }"
      :style="{ '--row': Math.min(ri * 45, 270) + 'ms' }"
    >
      <div class="an-row__main">
      <span class="an-mark" :data-s="it.source" :data-m="it.mode" aria-hidden="true">
        <svg v-if="it.source === 'relationship'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M12 8c1.6-2.6 5.6-2.2 5.6 1 0 2.6-3.2 4.4-5.6 6.6C9.6 13.4 6.4 11.6 6.4 9c0-3.2 4-3.6 5.6-1Z"/></svg>
        <svg v-else-if="it.source === 'birthday'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 12h12v7h-12Z"/><path d="M6 12c0-1.6 1.4-2.6 3-2.6s3 1 3 2.6"/><path d="M15 15v3M9 15v3"/><path d="M12 7v-2"/></svg>
        <svg v-else-if="it.mode === 'elapsed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><circle cx="9.4" cy="13.6" r="4.1"/><circle cx="14.6" cy="13.6" r="4.1"/><path d="M12 5.6 l1.9 3.4 -1.9 1.6 -1.9 -1.6 Z"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="m12 4 2.6 5.4 5.9.8-4.3 4.2 1 5.9-5.2-2.8-5.2 2.8 1-5.9-4.3-4.2 5.9-.8Z"/></svg>
      </span>

      <div class="an-row__body">
        <div class="an-row__head">
          <h4>{{ it.title }}</h4>
          <span v-if="it.is_today && !isPhantom(it)" class="an-today">今天</span>
        </div>

        <p v-if="it.source === 'relationship' && !relation.startSet" class="an-meta">
          还没填在一起那天 · 天数还不会开始数
        </p>
        <!-- 这类日子最该说「下个日子是哪天」，而不是「已经在一起多久」 -->
        <p v-else-if="it.mode === 'elapsed' && ringLeft(it)" class="an-meta an-meta--next">
          <i class="an-meta__lb">下个日子</i>
          <b class="an-meta__d">{{ fmtDate(it.next_date) }}</b>
          <span class="an-meta__n">{{ ringLabel(it) }} · 还有 {{ it.days_left }} 天</span>
        </p>
        <p v-else-if="it.mode === 'elapsed'" class="an-meta">
          {{ fmtDate(it.date) }} 起 · {{ heldText(it) || '刚开始' }}
        </p>
        <p v-else-if="it.passed" class="an-meta">{{ fmtDate(it.date) }} · 那天已经过去了</p>
        <p v-else-if="it.repeat_yearly && it.years" class="an-meta">{{ fmtDate(it.next_date) }} · 那天满 {{ yearsText(it) }}</p>
        <p v-else-if="it.repeat_yearly" class="an-meta">{{ fmtDate(it.next_date) }} · 每年这天</p>
        <p v-else class="an-meta">{{ fmtDate(it.next_date) }} · 只过一次</p>
        <!-- 已经走过的部分退到第二行，只当背景 -->
        <p v-if="it.mode === 'elapsed' && ringLeft(it)" class="an-meta an-meta--past">
          {{ fmtDate(it.date) }} 起 · {{ heldText(it) || '刚开始' }}
        </p>

        <div v-if="pctFor(it) !== null && !it.passed" class="an-bar">
          <i :style="{ width: (pctFor(it) * 100).toFixed(1) + '%', background: ringColor(it) }"></i>
        </div>

        <!-- 「在一起」这条谁都能改：引导里只问发起人，改不改得动看用户自己 -->
        <div v-if="it.source === 'relationship'" class="an-acts">
          <button class="an-act" type="button" :class="{ 'an-act--warn': !relation.startSet }" @click="openStartDate">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="5.6" width="16" height="14.4" rx="3.4"/><path d="M8 3.6v3.4M16 3.6v3.4M4 10.4h16"/></svg>
            <span>{{ relation.startSet ? '改那天' : '填上那天' }}</span>
          </button>
        </div>
        <div v-else-if="it.editable" class="an-acts">
          <button class="an-act" type="button" @click="openForm(it)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4.6 19.4h4l9.6-9.6a1.7 1.7 0 0 0 0-2.4l-1.6-1.6a1.7 1.7 0 0 0-2.4 0L4.6 15.4Z"/><path d="M13.4 7.4 16.6 10.6"/></svg>
            <span>改一下</span>
          </button>
          <button
            class="an-act an-act--del" :class="{ armed: armedId === it.id }"
            type="button" :disabled="deleting"
            @click="onDelete(it, $event)"
          >
            <svg v-if="armedId !== it.id" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M5.4 7.4h13.2"/><path d="M8.6 7.4v10.4a1.8 1.8 0 0 0 1.8 1.8h3.2a1.8 1.8 0 0 0 1.8-1.8V7.4"/><path d="M10 7.4V5.6h4v1.8"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.4 20 20.6H4Z"/><path d="M12 10v4.4"/><circle cx="12" cy="17.6" r=".9" fill="currentColor"/></svg>
            <span>{{ armedId === it.id ? '确定删？' : '删掉' }}</span>
          </button>
        </div>
      </div>

      <div class="an-days" :class="{ done: isPast(it) && !it.is_today, isToday: it.is_today }" :data-s="it.source" :data-m="it.mode">
        <template v-if="it.source === 'relationship' && !relation.startSet"><b class="mini">待填</b></template>
        <template v-else-if="it.is_today"><b class="mini">今天</b></template>
        <template v-else-if="isPast(it)">
          <i class="an-days__lb">已经</i>
          <b>{{ daysSince(it.date) }}</b><small>天</small>
        </template>
        <template v-else>
          <i class="an-days__lb">还有</i>
          <b>{{ it.days_left }}</b><small>天</small>
        </template>
      </div>
      </div>

      <!-- 节点：100 天 / 200 天 / 一周年……点一下就能单独记成一条日子 -->
      <div v-if="!isPhantom(it) && nodesFor(it).length" class="an-nodes">
        <div class="an-nodes__track">
          <button
            v-for="(n, ni) in nodesFor(it)" :key="n.key"
            class="an-nd"
            :class="{
              over: n.over, next: n.next,
              added: nodeAdded(it, n),
              busy: addingKey === it.id + '|' + n.key,
              press: pressing === it.id + ':' + n.key,
            }"
            type="button"
            :data-date="n.date"
            :style="{ '--nd': Math.min(ni * 24, 260) + 'ms' }"
            @pointerdown="pressing = it.id + ':' + n.key"
            @pointerup="pressing = ''"
            @pointercancel="pressing = ''"
            @pointerleave="pressing = ''"
            @click="addNode(it, n)"
          >
            <b>{{ n.name }}</b>
            <i>{{ nodeAdded(it, n) ? '已加入' : n.txt }}</i>
            <span class="an-nd__ico" aria-hidden="true">
              <svg v-if="nodeAdded(it, n)" class="an-ck" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4.6 12.6 9.4 17.4 19.4 6.6"/></svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5.6v12.8M5.6 12h12.8"/></svg>
            </span>
          </button>
        </div>
      </div>
      </article>
    </template>
  </div>

  <p class="an-note">
    「在一起」那天在这里就能改，首页的天数会一起变；生日在设置里维护；自己加的日子随时可以改。
  </p>

  <!-- 加入 / 删除后的轻提示 -->
  <Teleport to="body">
    <Transition name="an-flash">
      <div v-if="toastMsg" class="an-toast" role="status">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.8 12.6 9.4 17.2 19.2 7"/></svg>
        <span>{{ toastMsg }}</span>
      </div>
    </Transition>
  </Teleport>
</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { listAnniversaries, createAnniversary, updateAnniversary, deleteAnniversary } from '../../api/anniversaries.js';
import { relation } from '../../composables/useCove.js';
import { openStartDate } from '../../composables/useStartDate.js';
import { tap } from '../../native.js';
import CalendarBoard from '../../components/CalendarBoard.vue';
import { FIXED_HOLIDAYS, LUNAR_HOLIDAYS } from '../../data/holidays.js';

const DEMO = new URLSearchParams(location.search).has('demo');

const items = ref([]);
const loading = ref(!DEMO);
const error = ref('');
const filter = ref('all');
const deleting = ref(false);
/* 删除改成「按钮上二次确认」：第一次点先红起来问一句，2.6 秒不动就复原 */
const armedId = ref(null);
let armedTimer = 0;
/* 触摸设备上 :active 不一定触发，按下态自己管，手指按住那一刻就有实感 */
const pressing = ref('');
/* 正在加入的节点（源条目 + 节点 key），用来给那颗卡片一个按下去的反应 */
const addingKey = ref('');
const toastMsg = ref('');
let toastTimer = 0;

/* 筛选按「日子的性质」走，生日单独一档：
   纪念日 = 从那天起算（在一起 / 起始日类），生日 = 你们两个人的生日，
   目标日 = 等那一天到来。生日不再混进「目标日」。 */
const FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'elapsed', label: '纪念日' },
  { key: 'birthday', label: '生日' },
  { key: 'countdown', label: '目标日' },
];

const SOURCE = { relationship: '恋爱纪念日', birthday: '生日', holiday: '节日' };
/* 系统条目用它们自己的名字，自己加的日子按性质叫纪念日 / 目标日 */
function sourceLabel(it){
  if (!it) return '';
  if (SOURCE[it.source]) return SOURCE[it.source];
  return it.mode === 'elapsed' ? '纪念日' : '目标日';
}

/* ---------- 日期工具 ---------- */
function parseD(s){
  const [y, m, d] = String(s).split('-').map(Number);
  return new Date(y, m - 1, d);
}
/* 正计时：从那个日子到今天一共多少天 */
const TODAY0 = (() => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
})();
function daysSince(iso){
  if (!iso) return null;
  // 含起始日：那天算第 1 天，和关系资料里的「在一起 N 天」口径一致
  return Math.round((TODAY0 - parseD(iso)) / 86400000) + 1;
}
/* 今天的 YYYY-MM-DD：起算日期只能选到今天为止 */
const TODAY_ISO = `${TODAY0.getFullYear()}-${String(TODAY0.getMonth() + 1).padStart(2, '0')}-${String(TODAY0.getDate()).padStart(2, '0')}`;

function isoOf(d){
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function addDays(iso, n){
  const d = parseD(iso);
  d.setDate(d.getDate() + n);
  return isoOf(d);
}

/* ---------- 读数：两类日子最后都落到同一个口径 ----------
 *   起始日（elapsed）      → 已经 N 天
 *   目标日没过            → 还有 N 天
 *   目标日已经翻过去       → 已经 N 天（和起始日完全一样，不再特殊对待）
 */
function readOf(it){
  if (!it) return { dir: 'past', days: 0 };
  if (it.mode === 'elapsed') return { dir: 'past', days: daysSince(it.date) || 0 };
  if (it.passed) return { dir: 'past', days: daysSince(it.date) || 0 };
  return { dir: 'future', days: it.days_left || 0 };
}
function isPast(it){ return readOf(it).dir === 'past'; }

/* ---------- 节点：起始日往后的 100 天节点、周年 ----------
 * 只往前看：已经走过的节点没有「盼头」，摆一排「第 100 天 已 718 天」纯占地方。
 * 所以从下一个还没到的 100 天节点开始，往后三个；周年同理，列下一个和再下一个。
 */
function nodesOf(it){
  if (!it || !it.date) return [];
  const start = it.date;
  const days = daysSince(start);                 // 起始日当天就是第 1 天
  if (days == null || days < 1) return [];       // 还没到来的日子没有「已经走过」
  const list = [];

  const walk = Math.floor(days / 100) * 100;     // 最近一个已经走完的百天
  for (let i = 1; i <= 3; i++) {
    const n = walk + i * 100;
    list.push({ key: 'd' + n, name: '第 ' + n + ' 天', date: addDays(start, n - 1) });
  }

  const yearAt = (n) => {
    const d = parseD(start);
    d.setFullYear(d.getFullYear() + n);
    return isoOf(d);
  };
  let k = 1;                                     // 第一个还没到的周年
  while (yearAt(k) <= TODAY_ISO) k++;
  for (let i = 0; i < 2; i++) {
    const y = k + i;
    list.push({ key: 'y' + y, name: y + ' 周年', date: yearAt(y) });
  }

  list.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  let picked = false;
  for (const n of list) {
    const gap = daysSince(n.date);               // 节点那天到今天（含节点日）
    n.over = n.date <= TODAY_ISO;
    n.txt = n.over ? `已 ${gap} 天` : `还有 ${1 - gap} 天`;
    if (!n.over && !picked) { n.next = true; picked = true; }
  }
  return list;
}

const nodeMap = computed(() => {
  const m = {};
  for (const it of items.value) m[kit(it)] = isPast(it) ? nodesOf(it) : [];
  return m;
});
function nodesFor(it){ return nodeMap.value[kit(it)] || []; }
function kit(it){ return it.source + '-' + (it.id ?? it.title); }

/* ---------- 节点一键加入 ----------
 * 点一颗节点 = 把它单独记成一条日子：
 *   已经走过的节点 → 起始日（已经 N 天）
 *   还没到的节点   → 目标日（还有 N 天）
 * 标题跟父条走走：「在一起 · 第 900 天」
 */
function nodeTitle(it, n){ return it.title + ' · ' + n.name; }
const addedSet = computed(() => {
  const s = new Set();
  for (const x of items.value) s.add(x.date + '|' + x.title);
  return s;
});
function nodeAdded(it, n){ return addedSet.value.has(n.date + '|' + nodeTitle(it, n)); }

function toast(t){
  toastMsg.value = t;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => { toastMsg.value = ''; }, 2400);
}

async function addNode(it, n){
  if (!n || addingKey.value) return;
  if (nodeAdded(it, n)) { toast('「' + nodeTitle(it, n) + '」已经在列表里了'); return; }
  const mode = n.over ? 'elapsed' : 'countdown';
  const body = { title: nodeTitle(it, n), date: n.date, repeat_yearly: false, mode };
  addingKey.value = it.id + '|' + n.key;
  tap();
  try {
    if (DEMO) {
      const left = Math.round((parseD(n.date) - TODAY0) / 86400000);
      items.value = [...items.value, {
        id: 'demo-' + n.key + '-' + Date.now(), source: 'custom',
        title: body.title, date: body.date, next_date: body.date,
        days_left: left, years: null, is_today: false, passed: left < 0,
        repeat_yearly: false, mode, editable: true,
      }];
    } else {
      await createAnniversary(body);
      await load();
    }
    tap();
    toast('已加入「' + body.title + '」');
  } catch (e) {
    toast(e.message || '没加成，再试一次');
  } finally {
    addingKey.value = '';
  }
}

/* ---------- 派生 ----------
 * 两类日子分开排：
 *   0 还要等到的（还有 N 天）—— 由近到远
 *   1 已经走过的（已经 N 天）—— 走得最久的在前
 */
function rankOf(it){ return isPast(it) ? 1 : 0; }

const sorted = computed(() => [...items.value].sort((a, b) => {
  const ra = rankOf(a), rb = rankOf(b);
  if (ra !== rb) return ra - rb;
  const da = readOf(a).days, db = readOf(b).days;
  return ra === 1 ? db - da : da - db;
}));

/* ---------- 节日：一年里最近的那几个 ----------
 * 阳历的按年份拼日期，农历的查表；只留还没过（含今天）的一年内。
 * 页头不直接拿节日顶位置 —— 那里只放你亲手加的目标日；
 * 这份数据留给「添加日子」里的节日快捷（点一下就是一项目标日）。
 */
const holidays = computed(() => {
  const out = [];
  const thisYear = TODAY0.getFullYear();
  for (const h of FIXED_HOLIDAYS) {
    for (let yy = thisYear; yy <= thisYear + 1; yy++) {
      const iso = yy + '-' + h.md;
      const gap = Math.round((parseD(iso) - TODAY0) / 86400000);
      if (gap >= 0 && gap <= 400) out.push({ key: h.key, name: h.name, iso, gap, note: '' });
    }
  }
  for (const [key, name, iso, note] of LUNAR_HOLIDAYS) {
    const gap = Math.round((parseD(iso) - TODAY0) / 86400000);
    if (gap >= 0 && gap <= 400) out.push({ key, name, iso, gap, note });
  }
  return out.sort((a, b) => a.gap - b.gap);
});

/* 页头只从「你添加的目标日」里挑：还没到的、最近的第一个。
   起始日那类不算目标日 —— 它不是要去等的一天，是已经在过的日子。 */
const myTargets = computed(() => (
  sorted.value.filter(i => (
    i.source === 'custom' && i.mode !== 'elapsed' && !i.passed && !isPhantom(i)
  ))
));

/* 一个目标日都没有，就退到「下个周年」：页头不该空着，也不该退成「已经多少天」 */
const nextRing = computed(() => {
  /* 起始日还没填：后端那条「在一起」是拿绑定日兜底的，next_date 就是今天 ——
     不能拿它算成「第 1 周年 · 今天」 */
  if (!relation.startSet) return null;
  const rel = sorted.value.find(i => i.source === 'relationship');
  if (!rel || rel.passed || !rel.next_date || rel.days_left == null || rel.days_left < 0) return null;
  return {
    ...rel,
    title: rel.title + ' · ' + rel.years + ' 周年',
    date: rel.next_date,
    next_date: rel.next_date,
    mode: 'countdown',
    years: null,
    repeat_yearly: true,
    editable: false,
    is_today: rel.days_left === 0,
  };
});

/* 页头：今天 → 最近的目标日 → 没有目标日就下周年 */
const nextOne = computed(() => {
  const today = sorted.value.find(i => i.is_today);
  if (today) return today;
  if (myTargets.value.length) return myTargets.value[0];
  return nextRing.value || sorted.value.find(i => i.source === 'relationship') || sorted.value[0] || null;
});
const heroIsElapsed = computed(() => (nextOne.value ? isPast(nextOne.value) : false));
const heroDays = computed(() => (nextOne.value ? readOf(nextOne.value).days : 0));
/* 页头这条是一次性的、已经翻过去的目标日 */
const heroIsDoneTarget = computed(() => (
  !!nextOne.value && nextOne.value.mode !== 'elapsed' && isPast(nextOne.value)
));

const visible = computed(() => {
  const f = filter.value;
  if (f === 'all') return sorted.value;
  if (f === 'birthday') return sorted.value.filter(i => i.source === 'birthday');
  if (f === 'elapsed') return sorted.value.filter(
    i => i.mode === 'elapsed' && i.source !== 'birthday',
  );
  return sorted.value.filter(i => i.mode !== 'elapsed' && i.source !== 'birthday');
});

/* 两组：还要等到的 / 已经走过的（起始日 + 已经翻过去的目标日都在这一组） */
const groups = computed(() => {
  const list = visible.value;
  const wait = list.filter(i => !isPast(i));
  const gone = list.filter(i => isPast(i));
  return [
    { key: 'wait', label: '还要等到的', items: wait },
    { key: 'keep', label: '已经走过的', items: gone },
  ].filter(g => g.items.length);
});
/* 只有一组时不必显示分组标题 */
const groupCount = computed(() => groups.value.length);

/* 起始日没填时，后端那条「在一起」是拿绑定日兜底的，
   它会被算成「今天 / 已走过 100%」，看着像填好了 —— 统计上先把它摘出去 */
function isPhantom(it){
  return it?.source === 'relationship' && !relation.startSet;
}
const todayCount = computed(() => items.value.filter(i => i.is_today && !isPhantom(i)).length);
/* 「今年还有」只算落在今年 12.31 之前的（今天另算），
   别把明年的日子当成「今年还有」 */
const thisYearItems = computed(() => {
  const y = TODAY0.getFullYear();
  const from = new Date(y, TODAY0.getMonth(), TODAY0.getDate());
  const end = new Date(y, 11, 31, 23, 59, 59);
  return items.value
    .filter((i) => {
      if (!i?.next_date || i.passed || isPhantom(i)) return false;
      const d = parseD(i.next_date);
      return d > from && d <= end;
    })
    .slice()
    .sort((a, b) => parseD(a.next_date) - parseD(b.next_date));
});
const thisYearCount = computed(() => thisYearItems.value.length);

/* ---------- 天数滚动 ---------- */
const shownDays = ref(0);
let raf = 0;
function rollTo(to){
  cancelAnimationFrame(raf);
  const from = shownDays.value;
  const t0 = performance.now();
  const DUR = 1100;
  const step = (t) => {
    const p = Math.min(1, (t - t0) / DUR);
    const e = 1 - Math.pow(1 - p, 4);
    shownDays.value = Math.round(from + (to - from) * e);
    if (p < 1) raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
}
const REDUCE_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
/* 页头大数字：跟着当前这条的读数走（还有 N 天 / 已经 N 天） */
watch(heroDays, (v) => {
  if (v == null) return;
  if (REDUCE_MOTION) { shownDays.value = v; return; }   // 系统要求减少动态时直接落值
  rollTo(v);
}, { immediate: true });

/* ---------- 周期进度 ---------- */
/* 已满几个周年：后端 years 指的是「下一个日期是第几个周年」，今天就是那天时不再减 */
function heldText(it){
  if (!it || !it.repeat_yearly || !it.years) return '';
  const held = it.is_today ? it.years : it.years - 1;
  if (held <= 0) return '';
  return it.source === 'birthday' ? `已满 ${held} 岁` : `已经走过 ${held} 个周年`;
}

function pctFor(it){
  if (!it) return 0;
  if (isPhantom(it)) return null;               // 起始日没填：进度条没有意义
  if (!it.repeat_yearly) return null;          // 一次性的没有「周期」可言，不画进度
  if (it.passed) return 1;
  if (it.is_today) return 1;
  const next = parseD(it.next_date);
  const prev = new Date(next);
  prev.setFullYear(next.getFullYear() - 1);    // 2/29 会自动落到 2/28，够用
  const cycle = Math.max(1, Math.round((next - prev) / 86400000));
  const left = Math.max(0, Math.min(cycle, it.days_left));
  return (cycle - left) / cycle;
}
function ringColor(it){
  if (!it) return '#FA9490';
  if (it.passed) return 'rgba(64,71,86,.28)';
  if (it.source === 'relationship') return '#FA9490';
  if (it.source === 'wedding') return '#D99B6C';
  if (it.source === 'holiday') return '#EFB03C';
  return it.source === 'birthday' ? '#8B8FD6' : '#FFB27A';
}

/* ---------- 文案 ---------- */
function fmtDate(d){
  const [y, m, day] = String(d).split('-');
  return `${y}.${String(m).padStart(2, '0')}.${String(day).padStart(2, '0')}`;
}
/* 那天是周几：把 hero 里被「还有 N 天」占满的那一行换成有用的信息 */
const WEEK_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
function weekdayText(ymd){
  if (!ymd) return '';
  const d = new Date(`${ymd}T00:00:00`);
  return Number.isNaN(d.getTime()) ? '' : WEEK_NAMES[d.getDay()];
}
function yearsText(it){
  if (!it.years) return '';
  return it.source === 'birthday' ? `${it.years} 岁` : `第 ${it.years} 个周年`;
}
/* 窄行里「第 N 个个周年」太占地方，缩成「第 N 周年」 */
function ringLabel(it){
  if (!it || !it.years) return '';
  return it.source === 'birthday' ? `${it.years} 岁` : `第 ${it.years} 周年`;
}
/* 起始日这类日子：除了「已经多少天」，下一个周年还有多少天也值得摆在明面上 */
function ringLeft(it){
  return !!(it && it.repeat_yearly && it.years && !it.passed && it.days_left > 0);
}

/* ---------- 表单 ---------- */
const form = ref({ open: false, id: null, title: '', date: '', repeat: true, mode: 'countdown' });
const saving = ref(false);
const formError = ref('');
const calOpen = ref(false);
const yearSheet = ref(false);
function openYearSheet(){
  tap();
  yearSheet.value = true;
}
const canSubmit = computed(() => form.value.title.trim() && form.value.date);

/* 只分两种日子：目标日（等那一天） / 纪念日（从那天起算） */
function pickMode(m){
  tap();
  form.value.mode = m;
  /* 切换类型不能把已经填好的日子弄丢：这里只给提示，不动 date。
     真当「纪念日」存下去时，submit 会再拦一次 */
  formError.value = (m === 'elapsed' && form.value.date && form.value.date > TODAY_ISO)
    ? '这一天还没到，当「纪念日」存不下；切回目标日，或重选一个已经过的日子'
    : '';
}

function prettyDate(s){
  if (!s) return '';
  const [y, m, d] = String(s).split('-').map(Number);
  return `${y} 年 ${m} 月 ${d} 日`;
}

function openForm(it){
  tap();
  formError.value = '';
  calOpen.value = false;
  form.value = it
    ? {
        open: true,
        id: it.id,
        title: it.title,
        date: String(it.date),
        repeat: it.repeat_yearly,
        mode: it.mode === 'elapsed' ? 'elapsed' : 'countdown',
      }
    : { open: true, id: null, title: '', date: '', repeat: true, mode: 'countdown' };
}
function closeForm(){
  calOpen.value = false;
  form.value = { ...form.value, open: false };
}

/* 点一个节日 = 把它填成一项「目标日」，之后页头就会跟着它走 */
function pickHoliday(h){
  tap();
  formError.value = '';
  calOpen.value = false;
  form.value.title = h.name;
  form.value.date = h.iso;
  form.value.mode = 'countdown';
  form.value.repeat = true;
}

/* 选完一天：先让选中那颗"弹"一下、日期栏填好，再让日历收起来，别在点击瞬间就抽走 */
let calCloseTimer = 0;
function onCalPick(iso){
  form.value.date = iso;
  formError.value = '';
  tap();
  window.clearTimeout(calCloseTimer);
  calCloseTimer = window.setTimeout(() => { calOpen.value = false; }, 170);
}

/* 点日期栏开合日历；手动开合时取消"选完自动收起"的尾巴 */
function toggleCal(){
  window.clearTimeout(calCloseTimer);
  calOpen.value = !calOpen.value;
  tap();
}

/* 日历展开 / 收起：让高度真的长出来、缩回去，而不是一下子跳出来 */
const CAL_EASE = 'cubic-bezier(.32,.72,0,1)';
const calReduced = typeof window !== 'undefined'
  && window.matchMedia
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function onCalEnter(el, done){
  if (calReduced) { done(); return; }
  el.style.transform = '';
  el.style.overflow = 'hidden';
  el.style.visibility = 'hidden';
  el.style.height = 'auto';
  const h = el.getBoundingClientRect().height;
  el.style.height = '0px';
  el.style.opacity = '0';
  requestAnimationFrame(() => {
    el.style.visibility = 'visible';
    el.style.transition = `height .2s ${CAL_EASE}, opacity .16s ease`;
    el.style.height = `${h}px`;
    el.style.opacity = '1';
  });
  setTimeout(() => {
    el.style.transition = '';
    el.style.height = '';
    el.style.overflow = '';
    el.style.opacity = '';
    el.style.visibility = '';
    el.style.transform = '';
    done();
  }, 250);
}

/* 收起：先让日历内容在合成层上淡出并轻轻上收，再收容器高度。
   收缩期间内容已隐藏，只剩一张空卡在变矮，不重绘 42 个格子 */
function onCalLeave(el, done){
  if (calReduced) { done(); return; }
  const h = el.getBoundingClientRect().height;
  el.style.overflow = 'hidden';
  el.style.height = `${h}px`;
  el.style.transition = 'opacity .13s ease, transform .13s ease';
  el.style.opacity = '0';
  el.style.transform = 'translateY(-6px) scale(.985)';
  setTimeout(() => {
    el.style.visibility = 'hidden';
    el.style.transition = `height .13s ${CAL_EASE}`;
    el.style.height = '0px';
  }, 130);
  setTimeout(done, 280);
}

async function submit(){
  if (!canSubmit.value || saving.value) return;
  // 起始日从那天起算，日期不能晚于今天（后端也会拦，这里先给即时提示）
  if (form.value.mode === 'elapsed' && form.value.date > TODAY_ISO) {
    formError.value = '纪念日是已经发生的日子，请选今天或更早的一天';
    return;
  }
  saving.value = true; formError.value = '';
  const body = {
    title: form.value.title.trim(),
    date: form.value.date,
    repeat_yearly: form.value.repeat,
    mode: form.value.mode,
  };
  try {
    if (form.value.id) await updateAnniversary(form.value.id, body);
    else await createAnniversary(body);
    closeForm();
    await load();
    notifyData();
  } catch (e) {
    formError.value = e.message || '保存失败';
  } finally {
    saving.value = false;
  }
}

/* ---------- 删除 ----------
 * 按钮上二次确认：先红一下问「确定删？」，再点才真删；
 * 真删时让这张卡先塌下去、往左淡出，等动画走完再从数据里拿掉
 */
function onDelete(it, ev){
  if (deleting.value) return;
  if (armedId.value !== it.id) {
    armedId.value = it.id;
    tap();
    window.clearTimeout(armedTimer);
    armedTimer = window.setTimeout(() => { armedId.value = null; }, 2600);
    return;
  }
  window.clearTimeout(armedTimer);
  armedId.value = null;
  collapseAndDelete(it, ev);
}

async function collapseAndDelete(it, ev){
  deleting.value = true;
  const row = ev && ev.currentTarget ? ev.currentTarget.closest('.an-row') : null;
  if (row && !REDUCE_MOTION) {
    row.style.animation = 'none';   // 入场动画的终态会压住下面的位移，先摘掉
    const h = row.getBoundingClientRect().height;
    row.style.height = h + 'px';
    row.style.overflow = 'hidden';
    row.style.transition = 'height .32s cubic-bezier(.32,.72,0,1), opacity .24s ease, '
      + 'padding .32s cubic-bezier(.32,.72,0,1), margin-top .32s cubic-bezier(.32,.72,0,1), '
      + 'transform .32s cubic-bezier(.32,.72,0,1)';
    requestAnimationFrame(() => {
      row.style.height = '0px';
      row.style.paddingTop = '0px';
      row.style.paddingBottom = '0px';
      row.style.marginTop = '-9px';
      row.style.opacity = '0';
      row.style.transform = 'translateX(-14px) scale(.985)';
    });
    await new Promise((r) => setTimeout(r, 340));
  }
  try {
    if (DEMO) {
      items.value = items.value.filter(x => x.id !== it.id);
    } else {
      await deleteAnniversary(it.id);
      items.value = items.value.filter(x => x.id !== it.id);
    }
    notifyData();
    toast('已删掉「' + it.title + '」');
  } catch (e) {
    error.value = e.message || '删除失败';
  } finally {
    deleting.value = false;
  }
}

/* ---------- 取数 ---------- */
function seedDemo(){
  items.value = [
    { id: 1, source: 'relationship', title: '在一起', date: '2023-06-18', next_date: '2027-06-18', days_left: 221, years: 4, is_today: false, passed: false, repeat_yearly: true, mode: 'elapsed', editable: false },
    { id: 6, source: 'birthday', title: '林深生日', date: '2002-03-09', next_date: '2027-03-09', days_left: 120, years: 25, is_today: false, passed: false, repeat_yearly: true, mode: 'countdown', editable: false },
    { id: 7, source: 'custom', title: '第一次旅行', date: '2024-05-02', next_date: '2027-05-02', days_left: 174, years: 3, is_today: false, passed: false, repeat_yearly: true, mode: 'countdown', editable: true },
    { id: 8, source: 'custom', title: '搬进新家', date: '2025-09-01', next_date: '2025-09-01', days_left: -434, years: null, is_today: false, passed: true, repeat_yearly: false, mode: 'countdown', editable: true },
    { id: 9, source: 'custom', title: '一起去看极光', date: '2028-01-20', next_date: '2028-01-20', days_left: 437, years: null, is_today: false, passed: false, repeat_yearly: false, mode: 'countdown', editable: true },
    { id: 10, source: 'custom', title: '婚礼那天', date: '2021-10-01', next_date: '2027-10-01', days_left: 325, years: 6, is_today: false, passed: false, repeat_yearly: true, mode: 'elapsed', editable: true },
  ];
  loading.value = false;
}

/* 数据变了：通知「我」页那几张卡重拉，不然删完回来还显示旧的那条 */
function notifyData(){
  window.dispatchEvent(new Event('cove:data'));
}

async function load(){
  if (DEMO) { seedDemo(); return; }
  loading.value = true; error.value = '';
  try {
    items.value = alignRelationNodes(await listAnniversaries());
  } catch (e) {
    error.value = e.message || '加载失败';
    items.value = [];
  } finally {
    loading.value = false;
  }
}

/* 「在一起 · 第 N 天 / N 周年」是点节点收藏出来的独立条目：日期当时就写死在库里。
   起始日一改，它们还挂着旧日期，看着就像没刷新 —— 这里按新的起始日重算一遍。
   只动展示，不写库；用户点「改一下」时看到的还是原值，保存后才会被新值覆盖。 */
function alignRelationNodes(list){
  const rel = list.find(i => i.source === 'relationship');
  if (!rel || !rel.date) return list;
  const start = rel.date;
  const DAY = /^(.*?)\s*·\s*第\s*(\d+)\s*天$/;
  const YR = /^(.*?)\s*·\s*(\d+)\s*周年$/;
  return list.map(it => {
    if (it.source !== 'custom' || !it.title) return it;
    const mDay = DAY.exec(it.title);
    const mYr = YR.exec(it.title);
    let iso = null;
    if (mDay && mDay[1].trim() === rel.title) {
      iso = addDays(start, Number(mDay[2]) - 1);
    } else if (mYr && mYr[1].trim() === rel.title) {
      const d = parseD(start);
      d.setFullYear(d.getFullYear() + Number(mYr[2]));
      iso = isoOf(d);
    }
    if (!iso || iso === it.date) return it;
    const gap = Math.round((parseD(iso) - TODAY0) / 86400000);
    return { ...it, date: iso, next_date: iso, days_left: gap, is_today: gap === 0, passed: gap < 0 };
  });
}

/* 节点轨道默认从最早的那个节点开始（第 100 天……一路走过来），
   想看后面就往右滑；两端的渐隐负责提示「还有更多」 */

onMounted(() => {
  load();
  /* 起始日在别处（首页弹窗 / 设置页）被改过：这一页的「在一起」要跟着换日期 */
  window.addEventListener('cove:couple', load);
  // 走查用：?form=1 直接把新建表单铺开，?cal=1 顺带把日历也铺开
  const q = new URLSearchParams(location.search);
  if (q.has('form')) openForm();
  if (q.get('mode') === 'elapsed' || q.get('mode') === 'countdown') form.value.mode = q.get('mode');
  if (q.get('date')) form.value.date = q.get('date');
  if (q.has('cal')) calOpen.value = true;
});

onBeforeUnmount(() => window.removeEventListener('cove:couple', load));
</script>

<style scoped>
/* ============================================================
   纪念日 · NoSleep 那套语言
   深蓝灰 #404756 页头 + 手撕波浪、紫蓝 #5A6799、珊瑚 #FA9490、
   蜜桃 #FFCD94、淡粉 #F2C4C2、奶油 #F1DBC1、浅蓝白 #E9EFFF
   ============================================================ */
.an-page{
  --night:#404756;
  --night-soft:#4A5262;
  --ink:#3A4152;
  --ink2:#6B7488;
  --ink3:#9AA2B4;
  --iris:#5A6799;
  --iris-deep:#4E5A88;
  --coral:#FA9490;
  --coral-deep:#EF7C77;
  --peach:#FFCD94;
  --blush:#F2C4C2;
  --cream:#F1DBC1;
  --paper:#F0F2FB;
  --line:#E1E5F2;
  font-family:'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  padding-top:2px;
  display:flex;
  flex-direction:column;
  gap:12px;
  color:var(--ink);
}

/* ---------- 深色页头 ---------- */
.an-hero{
  position:relative;
  padding:18px 20px 46px;
  border-radius:26px;
  overflow:hidden;
  background:
    radial-gradient(120% 90% at 82% -12%, #4C5465 0%, rgba(76,84,101,0) 62%),
    linear-gradient(168deg, #474E5E 0%, #404756 52%, #3A4152 100%);
  box-shadow:0 26px 40px -32px rgba(32,36,48,.95);
}
.an-hero__glow{
  position:absolute; left:-50px; bottom:-70px; width:220px; height:220px; border-radius:50%;
  background:radial-gradient(circle at 50% 50%, rgba(90,103,153,.42), rgba(90,103,153,0) 68%);
  pointer-events:none;
}
.an-hero__sky{
  position:absolute; right:14px; top:44px; width:44px; height:44px;
  pointer-events:none;
}
.an-hero__top{
  position:relative; z-index:1;
  display:flex; align-items:center; justify-content:space-between;
}
.an-eb{
  font-size:10px; font-weight:500; letter-spacing:.1em;
  color:rgba(255,255,255,.5); text-transform:uppercase;
}
.an-pill{
  font-size:9.5px; font-weight:600; letter-spacing:.02em;
  padding:4px 10px; border-radius:999px;
  color:#FFFFFF; background:rgba(250,148,144,.85);
}
.an-pill[data-s="birthday"]{ background:rgba(139,143,214,.85); }
.an-pill[data-s="custom"]{ background:rgba(255,178,122,.9); }
.an-pill[data-s="custom"][data-m="elapsed"]{ background:rgba(217,155,108,.9); }
.an-pill[data-s="holiday"]{ background:rgba(239,176,60,.92); }

/* 大数字上方的小标签：还有 / 已经 */
.an-big__lb{
  position:relative; z-index:1; display:block;
  margin-top:14px;
  font-style:normal; font-size:10.5px; font-weight:700;
  letter-spacing:.18em; color:rgba(255,255,255,.8);
}
.an-big{
  position:relative; z-index:1;
  display:flex; align-items:baseline; gap:6px;
  margin-top:6px;
}
.an-big b{
  font-size:58px; font-weight:700; line-height:.94; letter-spacing:-.03em;
  color:#FFFFFF; font-variant-numeric:tabular-nums;
  text-shadow:0 10px 30px rgba(0,0,0,.16);
}
/* 起始日没填：这个位置要说的不是数字，是一句状态 */
.an-big--todo b{
  font-size:30px; letter-spacing:-.02em; opacity:.92;
  text-shadow:0 6px 18px rgba(0,0,0,.18);
}
.an-big i{
  font-style:normal; font-size:12px; font-weight:500;
  color:rgba(255,255,255,.62);
}
.an-big.today b{ font-size:34px; letter-spacing:.02em; }

.an-hero__title{
  position:relative; z-index:1;
  margin:12px 0 0; font-size:13.5px; font-weight:600;
  color:#FFFFFF; letter-spacing:-.01em;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.an-hero__date{
  margin:5px 0 0; font-size:10.5px; font-weight:400;
  color:rgba(255,255,255,.46); font-variant-numeric:tabular-nums;
}
/* 另一面读数：从起始日到今天的累计 */
.an-hero__since{
  position:relative; z-index:1;
  margin:6px 0 0; font-size:10.5px; font-weight:500;
  color:rgba(255,255,255,.72); font-variant-numeric:tabular-nums;
  letter-spacing:.01em;
}
.an-hero__since i{ font-style:normal; color:rgba(255,255,255,.4); }

.an-hero__bar{
  position:relative; z-index:1;
  height:4px; margin-top:16px; border-radius:99px;
  background:rgba(255,255,255,.16); overflow:hidden;
}
.an-hero__bar i{
  display:block; height:100%; border-radius:99px;
  transition:width 1.1s cubic-bezier(.22,.9,.3,1), background .4s ease;
}
.an-hero__meta{
  position:relative; z-index:1;
  display:flex; justify-content:space-between; margin-top:8px;
  font-size:9.5px; font-weight:400; color:rgba(255,255,255,.44);
}
/* 没有周期进度时只剩右边一句，别让它掉到左边显得空一半 */
.an-hero__meta--solo{ justify-content:flex-end; }
.an-hero__empty{ position:relative; z-index:1; padding:6px 0 4px; }
.an-hero__empty b{ font-size:34px; font-weight:600; color:rgba(255,255,255,.4); }

/* 手撕波浪：浅色内容从卡底涌上来 */
.an-wave{
  position:absolute; left:0; right:0; bottom:-1px; width:100%; height:34px;
  display:block; pointer-events:none;
}
.an-wave path{ fill:var(--paper); }

/* ---------- 三格色卡 ---------- */
.an-stats{ display:flex; gap:9px; }
.an-stat{
  flex:1; padding:13px 12px 12px; border-radius:18px;
  display:flex; flex-direction:column; gap:3px;
  box-shadow:0 14px 26px -24px rgba(48,54,78,.7);
  animation:statIn .52s backwards cubic-bezier(.32,.72,0,1) var(--si, 0ms);
}
/* 「今年还有」这张能点开，需要把 button 的原生样式清掉 */
.an-stat--tap{
  font:inherit; text-align:left; border:0; cursor:pointer;
  transition:transform .16s cubic-bezier(.32,1.4,.5,1), box-shadow .2s ease;
}
.an-stat--tap:active{ transform:scale(.97); }
.an-stat__go{ font-style:normal; margin-left:3px; font-size:11px; opacity:.85; }
/* 三格小卡依次浮起来 */
@keyframes statIn{
  from{ opacity:0; transform:translateY(14px) scale(.94); }
}
.an-stat[data-c="violet"]{ background:linear-gradient(150deg,#9598DE,#7C81D0); color:#FFFFFF; }
.an-stat[data-c="peach"]{ background:linear-gradient(150deg,#FFD6A6,#FFC785); color:#3A4152; }
.an-stat[data-c="blush"]{ background:linear-gradient(150deg,#F6CFCD,#EFB8B6); color:#3A4152; }
.an-stat b{
  font-size:19px; font-weight:600; line-height:1.1;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em;
}
.an-stat span{ font-size:9.5px; font-weight:400; opacity:.78; }

/* ---------- 「今年还有」弹层 ---------- */
.an-year__mask{
  position:fixed; inset:0; z-index:60;
  display:flex; align-items:flex-end;
  background:rgba(28,32,46,.42);
  -webkit-tap-highlight-color:transparent;
}
.an-year{
  width:100%; padding:9px 18px calc(14px + env(safe-area-inset-bottom,0px));
  background:#FFFFFF; border-radius:24px 24px 0 0;
  box-shadow:0 -22px 46px -30px rgba(28,32,46,.7);
}
.an-year__bar{ display:block; width:36px; height:4px; margin:3px auto 12px; border-radius:99px; background:#E4E7F0; }
.an-year h4{ margin:0; font-size:16.5px; font-weight:760; letter-spacing:-.02em; color:#3A4152; }
.an-year__n{ font-size:19px; font-weight:820; color:#E8837E; margin:0 1px; }
.an-year__sub{ margin:5px 0 0; font-size:10px; color:#98A0B4; }
.an-year__list{
  list-style:none; margin:12px 0 0; padding:0;
  max-height:46vh; overflow-y:auto;
  display:flex; flex-direction:column;
}
.an-year__list li{
  display:flex; align-items:center; gap:10px;
  padding:11px 2px; border-bottom:1px solid #F1F2F7;
}
.an-year__list li:last-child{ border-bottom:0; }
.an-year__dot{ width:7px; height:7px; border-radius:99px; flex:0 0 auto; }
.an-year__body{ flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; }
.an-year__body b{ font-size:13px; font-weight:700; color:#3A4152; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.an-year__body span{ font-size:10px; color:#98A0B4; font-variant-numeric:tabular-nums; }
.an-year__list em{ flex:0 0 auto; font-style:normal; font-size:10px; font-weight:600; color:#8E7CA6; }
.an-year__empty{ margin:14px 0 2px; display:flex; flex-direction:column; gap:5px; }
.an-year__empty b{ font-size:12.5px; font-weight:600; color:#3A4152; }
.an-year__empty span{ font-size:10px; color:#98A0B4; }
.an-year__close{
  width:100%; height:44px; margin-top:14px; border:0; border-radius:14px;
  font:inherit; font-size:13px; font-weight:700; color:#3A4152;
  background:#F1F3F8; cursor:pointer;
}
.an-year__close:active{ background:#E7EAF2; }
.ys-enter-active, .ys-leave-active{ transition:opacity .2s ease; }
.ys-enter-active .an-year, .ys-leave-active .an-year{ transition:transform .32s cubic-bezier(.32,.72,0,1); }
.ys-enter-from, .ys-leave-to{ opacity:0; }
.ys-enter-from .an-year, .ys-leave-to .an-year{ transform:translateY(100%); }

/* ---------- 筛选 ---------- */
.an-chips{ display:flex; gap:7px; overflow-x:auto; scrollbar-width:none; padding:1px 0; }
.an-chips::-webkit-scrollbar{ display:none; }
.an-chip{
  flex:0 0 auto; height:34px; padding:0 13px; border-radius:999px; cursor:pointer;
  display:flex; align-items:center; gap:5px;
  font-family:inherit; font-size:12px; font-weight:500;
  color:var(--ink2); background:#FFFFFF;
  box-shadow:0 8px 18px -16px rgba(48,54,78,.75), inset 0 0 0 1px rgba(255,255,255,.9);
  transition:background .2s ease, color .2s ease, transform .2s cubic-bezier(.34,1.4,.64,1);
}
.an-chip em{
  font-style:normal; font-size:9.5px; font-weight:600;
  padding:1px 5px; border-radius:999px; background:rgba(90,103,153,.1); color:var(--ink2);
}
.an-chip.on{ background:var(--coral); color:#FFFFFF; box-shadow:0 12px 20px -16px rgba(239,124,119,.95); }
.an-chip.on em{ background:rgba(255,255,255,.22); color:#FFFFFF; }
.an-chip:active{ transform:scale(.94); background:#F3F5FB; transition-duration:.07s; }
.an-chip.on{ animation:chipOn .34s cubic-bezier(.34,1.5,.64,1); }
@keyframes chipOn{ 0%{ transform:scale(1); } 42%{ transform:scale(1.06); } 100%{ transform:scale(1); } }

/* ---------- 添加 ---------- */
.an-add{
  display:flex; align-items:center; justify-content:center; gap:7px;
  width:100%; height:50px; border-radius:16px; cursor:pointer;
  font-family:inherit; font-size:13px; font-weight:600;
  color:#FFFFFF; background:var(--night);
  box-shadow:0 18px 30px -22px rgba(46,52,68,.95);
  transition:transform .2s cubic-bezier(.34,1.4,.64,1), background .2s ease;
  -webkit-tap-highlight-color:transparent;
}
.an-add:active{ transform:scale(.975); background:#4B5364; }

/* ---------- 表单 ---------- */
.an-form{
  padding:16px; border-radius:20px; background:#FFFFFF;
  box-shadow:0 20px 34px -28px rgba(48,54,78,.6), inset 0 0 0 1px rgba(255,255,255,.9);
  animation:anPop .45s cubic-bezier(.34,1.4,.64,1) both;
}
@keyframes anPop{ from{ opacity:0; transform:translateY(-8px) scale(.985); } to{ opacity:1; transform:none; } }
.an-form__head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.an-form__head h4{ margin:0; font-size:14.5px; font-weight:600; color:var(--ink); }
.an-x{ font-size:19px; line-height:1; color:var(--ink3); padding:2px 6px; cursor:pointer; background:none; }

/* 节日快捷：一排小卡，点一下就把名字和日期填进去 */
.an-quick{ display:flex; flex-wrap:wrap; gap:6px; margin:-3px 0 13px; }
.an-quick__lb{
  width:100%; font-size:10px; font-weight:600; letter-spacing:.12em;
  color:#A6A6B2; text-transform:uppercase;
}
.an-quick__c{
  display:flex; flex-direction:column; align-items:flex-start; gap:1px;
  padding:7px 11px; border:0; border-radius:12px;
  background:#F6F5FA; color:#3A3A46;
  font:inherit; font-size:12px; font-weight:600; line-height:1.2;
  transition:transform .16s cubic-bezier(.22,1,.36,1), background .16s ease;
  -webkit-tap-highlight-color:transparent;
}
.an-quick__c:active{ transform:scale(.96); background:#EDEBF4; }
.an-quick__c i{ font-style:normal; font-size:9.5px; font-weight:500; color:#8C8C96; }
.an-field{ display:flex; flex-direction:column; gap:7px; margin-bottom:13px; }
.an-field > span{
  font-size:10.5px; font-weight:500; letter-spacing:.06em; color:var(--ink3);
  text-transform:uppercase;
}
.an-input{
  width:100%; font-family:inherit; font-size:13px; color:var(--ink);
  padding:11px 13px; border-radius:10px; background:#FBFBFE;
  border:1.6px solid var(--line);
  transition:border-color .18s ease, box-shadow .18s ease;
}
.an-input:focus{ outline:none; border-color:#B9BEE2; box-shadow:0 0 0 4px rgba(139,143,214,.16); }
/* 类型选择：目标日 / 起始日 */
.an-kinds{ display:flex; gap:7px; }
.an-kind{
  flex:1; font-family:inherit; font-size:11.5px; font-weight:500;
  padding:9px 10px; border-radius:10px; cursor:pointer;
  color:var(--ink2); background:#FBFBFE; border:1.6px solid var(--line);
  transition:background .18s ease, border-color .18s ease, color .18s ease, transform .18s ease;
}
.an-kind:active{ transform:scale(.97); }
.an-kind.on{ color:#FFFFFF; background:var(--night); border-color:var(--night); font-weight:600; }
.an-hint{ margin:0; font-size:10px; line-height:1.5; color:var(--ink3); }

/* 日期：触发器 + 内联日历（骨架借「互动日历」稿，配色回到本页的深蓝灰 / 珊瑚） */
.an-field--date{ display:flex; flex-direction:column; gap:7px; }
.an-date{
  width:100%; display:flex; align-items:center; justify-content:space-between; gap:10px;
  padding:11px 13px; border-radius:10px; background:#FBFBFE;
  border:1.6px solid var(--line);
  font-family:inherit; font-size:13px; color:var(--ink); text-align:left;
  cursor:pointer;
  transition:border-color .18s ease, box-shadow .18s ease;
}
.an-date:hover{ border-color:#CBD0E4; }
.an-date.on{ border-color:#5A6799; box-shadow:0 0 0 3px rgba(90,103,153,.12); }
.an-date__txt.ph{ color:#A9AFC2; }
.an-date__ico{ width:17px; height:17px; flex:0 0 auto; stroke:#5A6799; stroke-width:1.6; fill:none; opacity:.8; }

/* 展开/收起由 Transition 的 JS 钩子做高度动画，这里只留 8px 呼吸距，
   用 padding 而不是 margin，高度归零时才不会有残余空隙 */
.an-cal{ padding-top:8px; will-change:opacity; contain:layout; }

.an-switch-row{ display:flex; align-items:center; gap:10px; margin:2px 0 4px; cursor:pointer; }
.an-switch-row span{ font-size:11.5px; color:var(--ink2); line-height:1.5; }
.an-switch{
  flex:0 0 auto; position:relative; width:40px; height:24px; border-radius:99px;
  background:#E4E7F2; transition:background .24s ease;
}
.an-switch i{
  position:absolute; left:3px; top:3px; width:18px; height:18px; border-radius:50%;
  background:#FFFFFF; box-shadow:0 2px 6px rgba(48,54,78,.2);
  transition:transform .26s cubic-bezier(.34,1.4,.64,1);
}
.an-switch.on{ background:var(--coral); }
.an-switch.on i{ transform:translateX(16px); }

.an-form__btns{ display:flex; gap:9px; margin-top:12px; }
.an-btn{
  flex:1; height:44px; border-radius:12px; cursor:pointer;
  font-family:inherit; font-size:13px; font-weight:600; color:#FFFFFF;
  background:var(--night);
  transition:transform .18s cubic-bezier(.34,1.4,.64,1), opacity .2s ease;
}
.an-btn:active{ transform:scale(.98); }
.an-btn:disabled{ opacity:1; background:#C4C8D6; color:#FFFFFF; cursor:default; transform:none; }
.an-btn--ghost{ color:var(--ink2); background:#F0F2FA; box-shadow:inset 0 0 0 1.4px var(--line); }

.an-warn{ margin:9px 2px 0; font-size:11px; color:#C9625C; }
.an-warn--box{
  margin:0; padding:11px 14px; border-radius:14px;
  background:rgba(250,148,144,.14); color:#B95751;
}

/* ---------- 列表 ---------- */
.an-sec{ display:flex; align-items:center; justify-content:space-between; padding:2px 4px 0; }
.an-sec h4{
  margin:0; font-size:11px; font-weight:600; letter-spacing:.12em;
  text-transform:uppercase; color:#7C849B;
}
.an-sec p{ margin:0; font-size:10px; color:var(--ink3); font-variant-numeric:tabular-nums; }

.an-card{ padding:22px 18px; border-radius:20px; background:#FFFFFF; box-shadow:0 16px 30px -28px rgba(48,54,78,.55); }
.an-loading{ display:flex; flex-direction:column; gap:10px; }
.an-loading i{
  display:block; height:13px; border-radius:8px;
  background:linear-gradient(90deg,#EFF1F8,#E4E7F2,#EFF1F8);
  background-size:200% 100%;
  animation:anShim 1.4s linear infinite;
}
.an-loading i:nth-child(2){ width:70%; }
.an-loading i:nth-child(3){ width:46%; }
@keyframes anShim{ from{ background-position:0 0; } to{ background-position:200% 0; } }

.an-empty{ display:flex; flex-direction:column; align-items:center; gap:8px; text-align:center; padding:36px 18px 38px; }
.an-empty__ico{
  display:grid; place-items:center; width:48px; height:48px; margin-bottom:4px;
  border-radius:50%; background:#F2F4FB; color:var(--iris);
}
.an-empty b{ font-size:14px; font-weight:600; color:var(--ink); }
.an-empty > span:last-child{ font-size:11.5px; color:var(--ink3); }

.an-list{ display:flex; flex-direction:column; gap:9px; }
/* 手指长按不该弹系统选字菜单，整块交互物都关掉选择 */
.an-row, .an-nd, .an-act, .an-chip, .an-add, .an-btn{
  -webkit-user-select:none; user-select:none; -webkit-touch-callout:none;
}
.an-row{
  display:block;
  padding:14px 14px 13px; border-radius:20px; background:#FFFFFF;
  box-shadow:0 16px 30px -28px rgba(48,54,78,.55), inset 0 0 0 1px rgba(255,255,255,.9);
  transition:transform .22s cubic-bezier(.34,1.4,.64,1), box-shadow .24s ease;
  animation:rowIn .46s backwards cubic-bezier(.32,.72,0,1) var(--row, 0ms);
}
/* 一进列表从下往上浮一点点，后面的卡片依次跟上 */
@keyframes rowIn{
  from{ opacity:0; transform:translateY(13px) scale(.986); }
}
.an-row__main{ display:flex; align-items:flex-start; gap:12px; }
.an-row.passed{ opacity:.66; }
.an-row.today{ background:linear-gradient(150deg,#FFFFFF,#FFF4F3 70%,#FFF9F2); }

/* 节点轨道：100 天 / 200 天 / 一周年 各自「已经走了多少天」 */
.an-nodes{ margin-top:11px; padding-top:10px; border-top:1px solid #F1F3F9; }
.an-nodes__track{
  display:flex; gap:7px; overflow-x:auto; padding-bottom:1px;
  scrollbar-width:none; -webkit-overflow-scrolling:touch;
  /* 两端渐隐：滑到边界时不会露出被硬切一半的卡片 */
  mask-image: linear-gradient(90deg, transparent 0, #000 16px, #000 calc(100% - 10px), transparent 100%);
  -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 16px, #000 calc(100% - 10px), transparent 100%);
}
.an-nodes__track::-webkit-scrollbar{ display:none; }
.an-nd{
  position:relative; flex:0 0 auto; min-width:70px;
  margin:0; padding:8px 24px 9px 10px;
  border:0; border-radius:13px;
  background:linear-gradient(158deg,#F9FAFD,#F1F4FA);
  box-shadow:inset 0 0 0 1px rgba(227,232,243,.9);
  font-family:inherit; text-align:left; cursor:pointer;
  -webkit-tap-highlight-color:transparent;
  animation:ndIn .36s backwards cubic-bezier(.32,.72,0,1) var(--nd, 0ms);
  transition:background .2s ease, box-shadow .22s ease,
             transform .3s cubic-bezier(.34,1.4,.64,1);
}
/* 手机上没有悬停，反馈全压在「按下去」这一下：缩得深一点、底色立刻变实 */
.an-nd:active{
  transform:scale(.9);
  background:#E2E8F5;
  box-shadow:inset 0 0 0 1px rgba(198,207,227,.95);
  transition-duration:.08s;
}
/* 手指按住那一瞬（pointerdown 驱动，移动端比 :active 稳） */
.an-nd.press{
  transform:scale(.9); background:#DEE5F3;
  box-shadow:inset 0 0 0 1px rgba(186,196,220,.95);
  transition-duration:.08s;
}
.an-nd.next.press{ background:#FFD2C8; }
.an-nd.added.press{ background:#D8EEDE; }
.an-nd b{
  display:block; font-size:10.5px; font-weight:600; color:#5B6274;
  line-height:1.2; letter-spacing:-.01em;
}
.an-nd i{
  display:block; margin-top:3px; font-style:normal;
  font-size:9.5px; color:#9AA1B2;
  font-variant-numeric:tabular-nums;
  transition:color .18s ease;
}
.an-nd.over b{ color:#8E95A7; }
/* 下一个：暖珊瑚，带一点微光，一眼看出「就差这一步」 */
.an-nd.next{
  background:linear-gradient(158deg,#FFF6F3,#FFE7E0);
  box-shadow:inset 0 0 0 1px rgba(233,124,116,.2), 0 9px 18px -15px rgba(233,124,116,.95);
}
.an-nd.next:active{ background:#FFD8CF; }
.an-nd.next b{ color:#D9605A; }
.an-nd.next i{ color:#E07F78; }
.an-nd.busy{ opacity:.55; }
/* 已加入：换成薄荷绿，对勾一笔画出来 */
.an-nd.added{
  background:linear-gradient(158deg,#F0FAF2,#E1F2E6);
  box-shadow:inset 0 0 0 1px rgba(94,155,114,.22);
  animation:ndAdd .46s cubic-bezier(.34,1.5,.64,1);
}
.an-nd.added b{ color:#3F7752; }
.an-nd.added i{ color:#74A583; }
.an-nd__ico{
  position:absolute; top:7px; right:7px; width:13px; height:13px;
  display:grid; place-items:center; color:#AEB5C6; opacity:.5;
  transition:color .18s ease, opacity .18s ease, transform .3s cubic-bezier(.34,1.6,.64,1);
}
.an-nd__ico svg{ width:12px; height:12px; }
.an-nd.added .an-nd__ico{ color:#4E9870; opacity:1; }
/* 对勾描边：从 22 收到 0，像笔划过去 */
.an-ck path{ stroke-dasharray:22; }
.an-nd.added .an-ck path{ animation:tickDraw .42s ease both; }
@keyframes tickDraw{ from{ stroke-dashoffset:22; } to{ stroke-dashoffset:0; } }
@keyframes ndIn{
  from{ opacity:0; transform:translateY(9px) scale(.95); }
}
@keyframes ndAdd{
  0%{ transform:scale(1); } 38%{ transform:scale(1.08); } 100%{ transform:scale(1); }
}
/* 手指设备上没有 hover，这些只在有鼠标的屏上生效 */
@media (hover:hover) and (pointer:fine){
  .an-nd:hover{
    background:#EBF0FA; transform:translateY(-1.5px);
    box-shadow:0 9px 18px -13px rgba(58,65,82,.62);
  }
  .an-nd:hover .an-nd__ico{ color:#E8837C; opacity:1; transform:scale(1.14); }
}

/* 行首色块：替参考稿的插画位 */
.an-mark{
  flex:0 0 auto; width:36px; height:36px; border-radius:12px;
  display:grid; place-items:center; color:#FFFFFF;
  background:linear-gradient(150deg,#FFA9A4,#F07C76);
  box-shadow:0 10px 18px -14px rgba(239,124,119,.9);
}
.an-mark svg{ width:19px; height:19px; }
.an-mark[data-s="birthday"]{ background:linear-gradient(150deg,#9EA2E1,#7A80CE); box-shadow:0 10px 18px -14px rgba(122,128,206,.9); }
.an-mark[data-s="custom"]{ background:linear-gradient(150deg,#FFD09E,#F7A968); box-shadow:0 10px 18px -14px rgba(247,169,104,.9); }
/* 起始日（从那天起算）用暖棕，目标日（等那一天）用橙，两类一眼分得开 */
.an-mark[data-s="custom"][data-m="elapsed"]{ background:linear-gradient(150deg,#E9C39E,#D99B6C); box-shadow:0 10px 18px -14px rgba(217,155,108,.9); }

.an-row__body{ flex:1; min-width:0; }
.an-row__head{ display:flex; align-items:center; gap:7px; flex-wrap:wrap; }
.an-row__head h4{
  margin:0; font-size:14.5px; font-weight:600; letter-spacing:-.01em; color:var(--ink);
  line-height:1.32;
}
.an-today{
  font-size:9px; font-weight:600; padding:3px 8px; border-radius:999px;
  color:#FFFFFF; background:var(--coral);
}
.an-meta{
  margin:5px 0 0; font-size:10.5px; color:var(--ink3);
  font-variant-numeric:tabular-nums;
}
/* 「下个日子 + 日期」这一行：日期加重换色，别跟「已经在一起多久」一样灰 */
.an-meta--next{
  display:flex; align-items:baseline; gap:4px; min-width:0;
  white-space:nowrap; overflow:hidden;
}
.an-meta__lb{
  flex:0 0 auto; font-style:normal; font-size:9.5px; font-weight:600;
  letter-spacing:.02em; color:#8E7CA6;
}
.an-meta__d{
  flex:0 0 auto; font-size:12.5px; font-weight:760;
  color:var(--iris); letter-spacing:-.01em;
}
.an-meta__n{
  flex:0 1 auto; min-width:0;
  font-size:9.5px; color:#A2A9B8;
  overflow:hidden; text-overflow:ellipsis;
}
/* 走过的部分：更小更淡，只当背景 */
.an-meta--past{ margin-top:3px; font-size:9.5px; color:#B6BCC9; }
/* 行卡上的累计读数：和右侧倒计时数字形成一对 */
.an-since{
  display:inline-block;
  margin:6px 0 0; padding:2px 7px; border-radius:6px;
  font-size:10px; font-weight:600; color:var(--iris);
  background:rgba(90,103,153,.09);
  font-variant-numeric:tabular-nums;
}
.an-row.passed .an-since{ display:none; }
.an-group{
  margin:6px 2px -1px; font-size:11px; font-weight:600;
  letter-spacing:.06em; color:var(--ink3);
}
.an-group:first-child{ margin-top:0; }
.an-bar{ height:3px; margin-top:9px; border-radius:99px; background:#EDEFF7; overflow:hidden; }
.an-bar i{ display:block; height:100%; border-radius:99px; transition:width 1s cubic-bezier(.22,.9,.3,1); }

.an-acts{ display:flex; gap:7px; margin-top:11px; }
.an-act{
  display:inline-flex; align-items:center; justify-content:center; gap:5px;
  min-width:74px; height:30px; padding:0 11px;
  border:1px solid #E9ECF5; border-radius:10px; background:#FFFFFF;
  font-family:inherit; font-size:10.5px; font-weight:500; color:var(--ink2);
  cursor:pointer; -webkit-tap-highlight-color:transparent;
  transition:background .16s ease, border-color .16s ease, color .16s ease,
             transform .26s cubic-bezier(.34,1.4,.64,1), box-shadow .2s ease;
}
.an-act svg{ width:12.5px; height:12.5px; flex:0 0 auto; }
/* 还没填起始日：这个按钮是「缺东西」的提示，得比普通按钮显眼 */
.an-act--warn{
  border-color:rgba(239,124,119,.42);
  background:#FFF3F2;
  color:#D9564F;
  font-weight:600;
}
.an-act:active{
  transform:scale(.9); background:#F0F3FA; border-color:#D9DFEE;
  transition-duration:.07s;
}
.an-act--del{ color:#C9625C; border-color:#F1DBD9; }
.an-act--del:active{ background:#FCE3E0; border-color:#EBBFBB; }
/* 二次确认：整颗红起来，字也换了，还轻轻呼吸，2.6 秒不点就自己复原 */
.an-act--del.armed{
  background:linear-gradient(150deg,#E9837A,#DE7268);
  border-color:transparent; color:#FFFFFF;
  animation:armedNudge .4s cubic-bezier(.34,1.4,.64,1),
            armedPulse 1.9s .4s ease-in-out infinite;
}
.an-act--del:disabled{ opacity:.55; cursor:default; transform:none; }
@keyframes armedNudge{
  0%{ transform:scale(.94); } 45%{ transform:scale(1.04); } 100%{ transform:scale(1); }
}
@keyframes armedPulse{
  0%,100%{ box-shadow:0 8px 18px -12px rgba(228,121,111,.95); }
  50%{ box-shadow:0 10px 26px -10px rgba(228,121,111,.72); }
}
@media (hover:hover) and (pointer:fine){
  .an-act:hover{
    background:#F7F8FC; border-color:#DCE1EF; color:var(--ink);
    transform:translateY(-1.5px);
    box-shadow:0 8px 14px -12px rgba(58,65,82,.7);
  }
  .an-act--del:hover{ background:#FDF1F0; border-color:#EAC5C1; color:#C0564F; }
}

/* 加入 / 删除后的轻提示 */
.an-toast{
  position:fixed; left:50%; bottom:56px; z-index:60;
  display:flex; align-items:center; gap:6px;
  max-width:76vw; padding:9px 15px 9px 12px;
  border-radius:999px; background:rgba(52,58,72,.94);
  color:#FFFFFF; font-size:11.5px; font-weight:500;
  box-shadow:0 14px 30px -16px rgba(40,46,60,.9);
  backdrop-filter:blur(8px);
  transform:translateX(-50%);
}
.an-toast svg{ width:13px; height:13px; color:#8ED3A4; flex:0 0 auto; }
.an-flash-enter-active{ transition:opacity .26s ease, transform .38s cubic-bezier(.32,.72,0,1); }
.an-flash-leave-active{ transition:opacity .2s ease, transform .24s ease; }
.an-flash-enter-from{ opacity:0; transform:translate(-50%, 16px) scale(.94); }
.an-flash-leave-to{ opacity:0; transform:translate(-50%, 8px) scale(.97); }

.an-days{
  flex:0 0 auto; display:flex; align-items:baseline; gap:2px;
}
.an-days b{
  font-size:21px; font-weight:600; letter-spacing:-.02em;
  font-variant-numeric:tabular-nums; color:var(--coral-deep);
}
.an-days[data-s="birthday"] b{ color:#6E74C6; }
.an-days[data-s="custom"] b{ color:#E8934E; }
.an-days[data-s="custom"][data-m="elapsed"] b{ color:#C4805A; }
.an-days small{ font-size:9.5px; font-weight:400; color:var(--ink3); }
/* 行卡右侧的小标签：还有 / 已经，一眼分清两类日子 */
.an-days__lb{
  font-style:normal; font-size:9px; font-weight:500;
  color:var(--ink3); letter-spacing:.04em;
  margin-right:3px;
}
.an-days.isToday b.mini{ font-size:12.5px; color:var(--coral-deep); }
.an-days.done b{ font-size:11px; font-weight:500; color:var(--ink3); }
.an-days.done small{ font-size:9.5px; }

.an-note{
  margin:4px 0 0; padding:0 8px 10px;
  text-align:center; font-size:10.5px; line-height:1.7; color:var(--ink3);
}

@media (prefers-reduced-motion: reduce){
  .an-row, .an-chip, .an-add, .an-btn, .an-switch i, .an-switch,
  .an-nd, .an-act, .an-toast{ transition-duration:.01s !important; }
  /* 入场错峰在关动效时也一并归零，否则首帧还停在 opacity:0 上 */
  .an-row, .an-stat, .an-nd, .an-chip, .an-act--del.armed, .an-ck path{
    animation-duration:.01s !important; animation-delay:0s !important;
  }
  .an-act--del.armed{ animation-iteration-count:1 !important; }
  .an-loading i{ animation-duration:.01s !important; }
}
</style>
