<template>
  <div class="sheet glass" id="sheet">
    <div class="sheet__in">
      <div class="sheet__grab"></div>
      <div class="sheet__scroll" id="sheetBody">
        <component :is="PANELS[panelKey]" v-if="panelKey" :key="panelKey" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { watch, nextTick } from 'vue';
import { PANELS } from '../panels/index.js';
import { engine } from '../glass/index.js';

const props = defineProps({ panelKey: { type: String, default: null } });

// 面板内容由 Vue 渲染，渲染完再把高度交回给玻璃几何
watch(
  () => props.panelKey,
  async () => {
    await nextTick();
    engine.measureSheetHeight();
  },
);
</script>
