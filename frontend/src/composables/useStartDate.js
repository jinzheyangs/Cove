/* 「在一起的那天」只该有一个入口界面。
 *
 * 首页那张待填卡、起始日页里的「在一起」、设置页里的「在一起」，
 * 全都打开同一个底部弹窗（StartDateSheet），保存后都写 couples.start_date，
 * 于是四处看到的日期天然是同一个 —— 不存在谁存了一份副本。
 *
 * 用一个模块级 ref 当开关：不需要把弹窗挂在每个父组件的模板里。
 */
import { ref } from 'vue';

export const startDateOpen = ref(false);

export function openStartDate() {
  startDateOpen.value = true;
}

export function closeStartDate() {
  startDateOpen.value = false;
}
