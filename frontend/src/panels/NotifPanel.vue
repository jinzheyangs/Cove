<template>
  <h3>通知</h3>

  <p v-if="loading" class="nt-tip">正在读…</p>
  <p v-else-if="error" class="nt-tip nt-tip--err">{{ error }}</p>
  <p v-else-if="!items.length" class="nt-tip">还没有新消息。</p>

  <template v-else>
    <div
      v-for="n in items"
      :key="n.id"
      class="nt-row"
      :class="{ 'nt-row--unread': !n.is_read }"
      @click="readOne(n)"
    >
      <span class="nt-main">
        <span class="nt-title">{{ n.title }}</span>
        <span class="nt-time">
          <template v-if="n.content">{{ n.content }} · </template>{{ rel(n.created_at) }}
        </span>
      </span>
      <span v-if="!n.is_read" class="nt-badge" aria-label="未读"></span>
    </div>

    <div v-if="unreadCount" class="cta">
      <button class="btn btn--p" type="button" :disabled="busy" @click="readAll">
        {{ busy ? '正在标记…' : '全部标为已读' }}
      </button>
    </div>
  </template>
</template>

<script setup>
/* 通知面板：接 /notifications 真数据，不再有写死的示例文案。
   行点一下就标已读；有未读时才出现「全部标为已读」。 */
import { ref, computed, nextTick, onMounted } from 'vue';
import { listNotifications, markNotificationRead, markAllNotificationsRead } from '../api/settings.js';
import { engine } from '../glass/index.js';

const items = ref([]);
const loading = ref(true);
const busy = ref(false);
const error = ref('');
const unreadCount = computed(() => items.value.filter((n) => !n.is_read).length);

/* 面板高度是跟着内容量的：内容一多一少都得重新量一次，否则底部按钮会露不出来 */
async function remeasure() {
  await nextTick();
  engine.measureSheetHeight();
}

function rel(iso) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const mins = Math.floor((Date.now() - t) / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days === 1) return '昨天';
  if (days < 7) return `${days} 天前`;
  const d = new Date(t);
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日`;
}

function pingBadge() {
  window.dispatchEvent(new Event('cove:notif'));
}

async function readOne(n) {
  if (n.is_read || busy.value) return;
  try {
    await markNotificationRead(n.id);
    n.is_read = true;
    pingBadge();
    remeasure();
  } catch (_) {
    /* 标不上就把红点留着，不打断阅读 */
  }
}

async function readAll() {
  if (busy.value || !unreadCount.value) return;
  busy.value = true;
  try {
    await markAllNotificationsRead();
    for (const n of items.value) n.is_read = true;
    pingBadge();
  } catch (e) {
    error.value = e?.message || '没能标记为已读';
  } finally {
    busy.value = false;
    remeasure();
  }
}

onMounted(async () => {
  try {
    items.value = (await listNotifications()) || [];
  } catch (e) {
    error.value = e?.message || '通知读取失败';
  } finally {
    loading.value = false;
    remeasure();
  }
});
</script>

<style scoped>
/* sheet 里只留一套发丝行：标题 13、时间 10.5，
   未读靠右侧一个 6px 的珊瑚点，不写「未读」两个字。 */
.nt-tip {
  font-size: 12px;
  color: var(--ink-3);
  padding: 14px 0 6px;
}
.nt-tip--err { color: #e0526b; }

.nt-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 0;
  border-bottom: 0.5px solid var(--line);
}
.nt-row:last-of-type { border-bottom: 0; }
.nt-row--unread { cursor: pointer; }

.nt-main { display: flex; flex-direction: column; min-width: 0; gap: 3px; }
.nt-title {
  font-size: 13px;
  color: var(--ink);
  line-height: 1.45;
}
.nt-row--unread .nt-title { font-weight: 620; }
.nt-time {
  font-size: 10.5px;
  color: var(--ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nt-badge {
  flex: 0 0 auto;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--coral);
}
</style>
