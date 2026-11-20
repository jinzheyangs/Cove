/* 面板的登记表：key → 组件。
   同步导入而不是异步：面板高度参与玻璃几何计算，异步 chunk 会让第一帧量到空内容，
   面板会先按 268px 弹出来再跳高。

   现在只剩「通知」一个。原来那 12 个（金币/清单/账本/商城/纪念日/模拟Ta/设置/回答/
   秘密/新建秘密/日记/新建日记）都是写死示例文案的空壳，界面上的真入口早就换成了
   views/modules 下的真实模块，这些壳已经删掉。 */

import NotifPanel from './NotifPanel.vue';

export const PANELS = {
  notif: NotifPanel,
};
