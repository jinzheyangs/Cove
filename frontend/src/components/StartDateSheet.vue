<template>
  <Teleport to="body">
    <Transition name="sd">
      <div v-if="startDateOpen" class="sd-wrap">
        <div class="sd-mask" @click="close"></div>

        <section class="sd-card" role="dialog" aria-modal="true" aria-labelledby="sd-title">
          <span class="sd-grab" aria-hidden="true"></span>

          <h3 id="sd-title" class="sd-t">恋爱纪念日</h3>
          <p class="sd-sub">你们恋爱的起点：在一起多少天、100 天和一周年都从这一天算。</p>

          <div class="sd-pick">
            <WheelDatePicker v-model="date" :max="todayStr" />
          </div>

          <!-- 选完立刻给出这句话，用户能确认这一下点对了 -->
          <div class="sd-read" :class="{ bad: !daysCount }">
            <template v-if="daysCount">
              <span class="sd-read__lb">从这天起</span>
              <b class="sd-read__n">{{ daysCount }}</b>
              <span class="sd-read__lb">天</span>
            </template>
            <template v-else>
              <span class="sd-read__lb">这天还没到，不能选未来的日子</span>
            </template>
          </div>

          <p v-if="error" class="sd-err">{{ error }}</p>

          <div class="sd-acts">
            <button class="sd-save" type="button" :disabled="saving || !daysCount" @click="save">
              {{ saving ? '保存中…' : '保存' }}
            </button>
            <button class="sd-cancel" type="button" @click="close">取消</button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
/* 填「在一起的那天」的底部弹窗。
 *
 * 为什么是弹窗而不是跳到设置：
 * 点这张待填卡的时候人就在首页，想看的是「填完这里立刻变成天数」；
 * 跳去设置是个账号资料页，还得再找一行、再展开一次 —— 两步多余的动作。
 * 弹窗上来、滚一下、保存，当场回到卡上看见数字，闭环最短。
 *
 * 三处入口（首页待填卡 / 起始日页 / 设置页）共用这一个弹窗，
 * 都写 couples.start_date 这一个真源，谁都不会存副本。
 */
import { ref, computed, watch, nextTick } from 'vue';
import WheelDatePicker from './WheelDatePicker.vue';
import { updateCouple } from '../api/settings.js';
import { relation, loadRelation } from '../composables/useCove.js';
import { startDateOpen, closeStartDate } from '../composables/useStartDate.js';

const date = ref('');
const saving = ref(false);
const error = ref('');

const now = new Date();
const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

/* 打开时预填：已经填过就用原值，没填就落在今天（多数人就是今天或最近） */
const seed = ref(todayStr);

function daysBetween(ymd) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd || '');
  if (!m) return 0;
  const d = new Date(`${ymd}T00:00:00`);
  if (Number.isNaN(d.getTime())) return 0;
  const t = new Date();
  t.setHours(0, 0, 0, 0);
  return Math.floor((t - d) / 86400000) + 1;
}

const daysCount = computed(() => (date.value && date.value <= todayStr ? daysBetween(date.value) : 0));

watch(startDateOpen, async (open) => {
  if (!open) return;
  error.value = '';
  saving.value = false;
  /* 弹窗每次打开都重新取一次当前值，避免上次的临时选择残留 */
  seed.value = relation.startDate || todayStr;
  date.value = seed.value;
});

function close() {
  if (saving.value) return;
  closeStartDate();
}

async function save() {
  if (!daysCount.value) return;
  error.value = '';
  saving.value = true;
  try {
    await updateCouple({ start_date: date.value });
    /* 先刷全局关系，再通知各页重新拉自己的数据：
       首页那张卡会当场从「待填」切成天数，起始日页的「在一起」也跟着变 */
    await loadRelation();
    window.dispatchEvent(new Event('cove:couple'));
    closeStartDate();
  } catch (e) {
    error.value = e?.message || '保存失败，再试一次';
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
/* ============================================================
   与登录 / 设置同一套黑白语言：浅灰遮罩、纯白圆角卡、黑色主按钮。
   只有「天数预览」用一点珊瑚，因为它是这一屏的结果。
   ============================================================ */
.sd-wrap {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.sd-mask {
  position: absolute;
  inset: 0;
  background: rgba(18, 16, 20, .34);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}
.sd-card {
  position: relative;
  width: 100%;
  max-width: 400px;
  padding: 10px 16px calc(14px + env(safe-area-inset-bottom, 0px));
  border-radius: 24px 24px 0 0;
  background: #fff;
  box-shadow: 0 -18px 44px -26px rgba(17, 17, 19, .38);
  transform-origin: 50% 100%;
}
/* 窗口比手机宽（桌面浏览器、平板）时，别再贴底铺满一条，
   收成一块居中的小浮卡，尺寸就是手机上的尺寸 */
@media (min-width: 520px) {
  .sd-wrap { padding-bottom: 30px; }
  .sd-card { border-radius: 24px; max-width: 372px; }
}
.sd-grab {
  display: block;
  width: 38px; height: 4px;
  margin: 0 auto 8px;
  border-radius: 999px;
  background: #E4E4E9;
}
.sd-t {
  margin: 0;
  font-size: 16.5px; font-weight: 800; letter-spacing: -.02em; color: #111114;
}
.sd-sub {
  margin: 4px 0 10px;
  font-size: 11.5px; line-height: 1.5; color: #7A7A84;
}
.sd-pick { margin: 0 -2px; }

.sd-read {
  display: flex; align-items: baseline; justify-content: center; gap: 3px;
  margin: 10px 0 0;
  padding: 8px;
  border-radius: 13px;
  background: #FCF6F8;
  box-shadow: inset 0 0 0 1px rgba(217, 35, 90, .12);
}
.sd-read__lb { font-size: 11px; font-weight: 600; color: #A26477; }
.sd-read__n {
  font-size: 22px; font-weight: 800; letter-spacing: -.03em; color: #D9235A;
  font-variant-numeric: tabular-nums; line-height: 1;
}
.sd-read.bad { background: #FAFAFB; box-shadow: inset 0 0 0 1px #ECECF0; }
.sd-read.bad .sd-read__lb { color: #8C8C96; }

.sd-acts {
  display: flex; align-items: center; gap: 9px;
  margin-top: 10px;
}
.sd-err {
  margin: 8px 0 0; font-size: 11.5px; color: #D9235A; text-align: center;
}
.sd-save {
  flex: 1; height: 46px;
  border: 0; border-radius: 14px;
  background: #111114; color: #fff;
  font: inherit; font-size: 14.5px; font-weight: 700;
  letter-spacing: -.01em;
  transition: transform .16s cubic-bezier(.22, 1, .36, 1), background .16s ease;
}
.sd-save:active:not(:disabled) { transform: scale(.985); background: #000; }
.sd-save:disabled { background: #EFEFF3; color: #B6B6BE; }
.sd-cancel {
  flex: none; height: 46px; padding: 0 15px;
  border: 0; border-radius: 14px;
  background: #F5F5F7; color: #52525B;
  font: inherit; font-size: 13.5px; font-weight: 600;
  transition: transform .16s cubic-bezier(.22, 1, .36, 1), background .16s ease;
}
.sd-cancel:active { transform: scale(.985); background: #ECECF0; }

/* 上滑 + 遮罩淡入；关闭反向，卡片先往下走一点再消失 */
.sd-enter-active { transition: opacity .26s ease; }
.sd-leave-active { transition: opacity .2s ease; }
.sd-enter-from, .sd-leave-to { opacity: 0; }
.sd-enter-active .sd-card { transition: transform .34s cubic-bezier(.22, 1, .36, 1); }
.sd-leave-active .sd-card { transition: transform .2s cubic-bezier(.4, 0, .7, .2); }
.sd-enter-from .sd-card { transform: translateY(100%); }
.sd-leave-to .sd-card { transform: translateY(38%); }

@media (prefers-reduced-motion: reduce) {
  .sd-enter-active, .sd-leave-active,
  .sd-enter-active .sd-card, .sd-leave-active .sd-card { transition-duration: .01s !important; }
}
</style>
