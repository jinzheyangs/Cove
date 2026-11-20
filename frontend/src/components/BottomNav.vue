<template>
  <nav class="tabs glass" :class="{ off: hidden }" id="tabs" aria-label="主导航">
    <button
      v-for="t in tabs"
      :key="t.key"
      class="tab"
      :class="{ on: current === t.key }"
      :data-tab="t.key"
      :aria-label="t.label"
      :title="t.label"
      @click="$emit('select', t.key)"
    >
      <!-- 实心图标：挖空处走 fill-rule，缩到 26px 也不糊 -->
      <svg v-if="t.key === 'today'" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 3.06c.45 0 .89.15 1.25.42l7.12 5.3c.45.34.71.87.71 1.43v9.19A2.6 2.6 0 0 1 18.48 22H5.52A2.6 2.6 0 0 1 2.92 19.4v-9.19c0-.56.26-1.09.71-1.43l7.12-5.3c.36-.27.8-.42 1.25-.42ZM9.2 18.55c0-.66.54-1.2 1.2-1.2h3.2c.66 0 1.2.54 1.2 1.2V22H9.2v-3.45Z" /></svg>
      <svg v-else-if="t.key === 'diary'" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" clip-rule="evenodd" d="M6.2 2.5h11.6c1.44 0 2.6 1.16 2.6 2.6v13.8c0 1.44-1.16 2.6-2.6 2.6H6.2c-1.44 0-2.6-1.16-2.6-2.6V5.1c0-1.44 1.16-2.6 2.6-2.6ZM7.4 7a.85.85 0 0 0 0 1.7h9.2a.85.85 0 0 0 0-1.7H7.4Zm0 3.7a.85.85 0 0 0 0 1.7h9.2a.85.85 0 0 0 0-1.7H7.4Zm0 3.7a.85.85 0 0 0 0 1.7h5.2a.85.85 0 0 0 0-1.7H7.4Z" /></svg>
      <svg v-else-if="t.key === 'tree'" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.2c-1.5 0-2.9.7-3.8 1.9-1.9.2-3.4 1.8-3.4 3.8 0 .9.3 1.7.8 2.4-1.3.7-2.1 2-2.1 3.5 0 2.2 1.8 4 4 4h1.4v3.2c0 .5.4.9.9.9h4.4c.5 0 .9-.4.9-.9v-3.2h1.4c2.2 0 4-1.8 4-4 0-1.5-.8-2.8-2.1-3.5.5-.7.8-1.5.8-2.4 0-2-1.5-3.6-3.4-3.8-.9-1.2-2.3-1.9-3.8-1.9Z"/></svg>
      <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><g fill-opacity=".5"><circle cx="16.3" cy="10.9" r="2.6" /><path d="M12 20.6v-2a4.6 4.6 0 0 1 4.6-4.6h0a4.6 4.6 0 0 1 4.6 4.6v2c0 .52-.43.95-.95.95h-7.3c-.52 0-.95-.43-.95-.95Z" /></g><circle cx="9.3" cy="8.1" r="3.45" /><path d="M3 20.6v-2.4a6.3 6.3 0 0 1 6.3-6.3h0a6.3 6.3 0 0 1 6.3 6.3v2.4c0 .55-.45 1-1 1H4c-.55 0-1-.45-1-1Z" /></svg>
    </button>
  </nav>
</template>

<script setup>
defineProps({
  current: { type: String, default: 'today' },
  hidden: Boolean,
});
defineEmits(['select']);

const tabs = [
  { key: 'today', label: '今天' },
  { key: 'diary', label: '日记' },
  { key: 'tree', label: '秘密树' },
  { key: 'me', label: '我们' },
];
</script>

<style scoped>
/* 进二级页（日记详情 / 发布）时整条底栏滑下去，不再压着内容的最后一行。
   这里只做位移：opacity 每帧被玻璃引擎写 inline，写 CSS 也管不住 */
.tabs { transition: transform .44s cubic-bezier(.32,1.02,.36,1), visibility 0s linear 0s; }
.tabs.off {
  transform: translateY(160%);
  pointer-events: none;
  /* 位移结束再藏起来：万一位移被别的布局吃掉，也不会留半条在屏幕里 */
  visibility: hidden;
  transition: transform .44s cubic-bezier(.32,1.02,.36,1), visibility 0s linear .44s;
}
@media (prefers-reduced-motion: reduce) {
  .tabs { transition: none; }
}
</style>
