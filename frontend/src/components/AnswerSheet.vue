<template>
  <Teleport to="body">
    <Transition name="as">
      <div v-if="open" class="as-wrap">
        <div class="as-mask" @click="close"></div>
        <div class="as-card" role="dialog" aria-modal="true">
          <span class="as-grab"></span>
          <h3 class="as-t">今日问题</h3>
          <p class="as-q">{{ question || '今天的问题还没出题' }}</p>

          <label class="as-label">我的回答</label>
          <textarea
            v-model="draft"
            class="as-ta"
            rows="4"
            maxlength="2000"
            placeholder="慢慢写，TA 写完之前看不到"
          ></textarea>

          <div class="as-partner">
            <span class="as-partner__l">TA 的回答</span>
            <span class="as-partner__v" :class="{ on: !!partnerAnswer }">
              {{ partnerAnswer || (myAnswer ? 'TA 还没写' : '两边都写完才解锁') }}
            </span>
          </div>

          <p v-if="err" class="as-err">{{ err }}</p>

          <div class="as-acts">
            <button
              class="as-save"
              type="button"
              :disabled="!draft.trim() || saving"
              @click="save"
            >{{ saving ? '交上去…' : (myAnswer ? '改一下' : '交上去') }}</button>
            <button class="as-cancel" type="button" @click="close">取消</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue';
import { post } from '../api/client.js';

/* 问题和首页那张卡同源：都用 /daily 的 question，
   所以「去回答」里看到的题一定和卡片上的一致。 */
const props = defineProps({
  open: { type: Boolean, default: false },
  question: { type: String, default: '' },
  myAnswer: { type: String, default: '' },
  partnerAnswer: { type: String, default: '' },
});
const emit = defineEmits(['update:open', 'saved']);

const draft = ref('');
const saving = ref(false);
const err = ref('');

watch(
  () => props.open,
  (v) => {
    if (!v) return;
    draft.value = props.myAnswer || '';
    err.value = '';
  }
);

async function save() {
  const text = draft.value.trim();
  if (!text || saving.value) return;
  saving.value = true;
  err.value = '';
  try {
    await post('/daily', { answer: text });
    emit('saved');
    emit('update:open', false);
  } catch (e) {
    err.value = e?.message || '没交上，稍后再试';
  } finally {
    saving.value = false;
  }
}

function close() {
  emit('update:open', false);
}
</script>

<style scoped>
.as-wrap { position: fixed; inset: 0; z-index: 88; display: flex; align-items: flex-end; justify-content: center; }
.as-mask {
  position: absolute; inset: 0;
  background: rgba(18, 16, 20, .34);
  backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px);
}
.as-card {
  position: relative; width: 100%; max-width: 400px;
  padding: 10px 16px calc(14px + env(safe-area-inset-bottom, 0px));
  border-radius: 24px 24px 0 0;
  background: #fff;
  box-shadow: 0 -18px 44px -26px rgba(17, 17, 19, .38);
}
@media (min-width: 520px) {
  .as-wrap { padding-bottom: 30px; }
  .as-card { border-radius: 24px; max-width: 372px; }
}
.as-grab { display: block; width: 38px; height: 4px; margin: 0 auto 8px; border-radius: 999px; background: #E4E4E9; }
.as-t { margin: 0; font-size: 16.5px; font-weight: 800; letter-spacing: -.02em; color: #111114; }

.as-q {
  margin: 8px 0 0; padding: 11px 13px;
  border-radius: 14px; background: #FBF3F6;
  font-size: 14px; line-height: 1.55; font-weight: 700; letter-spacing: -.01em;
  color: #3A1526;
}

.as-label { display: block; margin: 12px 0 5px; font-size: 11px; font-weight: 800; letter-spacing: .3px; color: #7A7A84; }
.as-ta {
  display: block; width: 100%; padding: 10px 12px;
  border: 0; border-radius: 14px; background: #F5F5F7;
  font: inherit; font-size: 13px; line-height: 1.6; color: #111114;
  resize: none; outline: 0;
}
.as-ta::placeholder { color: #B6B6BE; }
.as-ta:focus { background: #F1F1F5; }

.as-partner {
  display: flex; align-items: center; gap: 8px;
  margin-top: 10px; padding: 9px 12px;
  border-radius: 12px; background: #FAFAFB;
}
.as-partner__l { font-size: 11px; font-weight: 800; color: #7A7A84; letter-spacing: .2px; }
.as-partner__v { margin-left: auto; font-size: 11.5px; font-weight: 700; color: #B6B6BE; text-align: right; }
.as-partner__v.on { color: #52525B; }

.as-err { margin: 8px 0 0; font-size: 11.5px; color: #D9235A; }

.as-acts { display: flex; align-items: center; gap: 9px; margin-top: 12px; }
.as-save {
  flex: 1; height: 46px; border: 0; border-radius: 14px;
  background: #111114; color: #fff;
  font: inherit; font-size: 14px; font-weight: 700;
  transition: transform .16s cubic-bezier(.22, 1, .36, 1), background .16s;
}
.as-save:disabled { background: #EFEFF3; color: #B6B6BE; }
.as-save:active:not(:disabled) { transform: scale(.985); }
.as-cancel {
  flex: none; height: 46px; padding: 0 15px;
  border: 0; border-radius: 14px;
  background: #F5F5F7; color: #52525B;
  font: inherit; font-size: 13.5px; font-weight: 600;
}
.as-cancel:active { transform: scale(.985); }

.as-enter-active { transition: opacity .24s ease; }
.as-leave-active { transition: opacity .18s ease; }
.as-enter-from, .as-leave-to { opacity: 0; }
.as-enter-active .as-card { transition: transform .32s cubic-bezier(.22, 1, .36, 1); }
.as-enter-from .as-card { transform: translateY(100%); }

@media (prefers-reduced-motion: reduce) {
  .as-save, .as-cancel, .as-ta { transition-duration: .01s !important; }
  .as-enter-active, .as-leave-active, .as-enter-active .as-card { transition-duration: .01s !important; }
}
</style>
