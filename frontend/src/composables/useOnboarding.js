/* 引导页的步骤编排：进入时「缺什么补什么」，不重复打扰。
 *
 * 步骤来源：
 * - nickname：这台设备上第一次进主页时确认一下称呼（只问一次）
 * - birthday：users.birthday 为空
 * - start：已绑定但 couples.start_date 为空，且当前用户是发起绑定的人
 *
 * 标记（已完成 / 某一步被跳过）都按「用户 id」分开存：
 * 同一台电脑上换账号后，上一个账号的跳过记录不会把新账号的引导吞掉。
 */

import { getMe, getCouple } from '../api/settings.js';

/* 当前正在走引导的账号；buildIntroSteps 每次都会刷新它 */
let currentUid = 0;

function lsGet(key) {
  try { return localStorage.getItem(key); } catch (_) { return null; }
}
function lsSet(key, value) {
  try { localStorage.setItem(key, value); } catch (_) { /* 存不了就下次再问 */ }
}

function key(name) {
  return `cove.intro.${currentUid}.${name}`;
}

export function markIntroDone() {
  lsSet(key('done'), '1');
}

export function markStepSkipped(step) {
  lsSet(key('skip.' + step), '1');
}

function isSkipped(step) {
  return !!lsGet(key('skip.' + step));
}

function isIntroDone() {
  return !!lsGet(key('done'));
}

/** 根据当前资料算出还要走哪几步 */
export function buildIntroSteps(me, couple) {
  currentUid = me?.id || 0;
  const steps = [];
  if (!isIntroDone()) steps.push('nickname');
  if (!me?.birthday && !isSkipped('birthday')) steps.push('birthday');
  /* 「在一起那天」两个人共享同一个日期，只该问一次：问发起人。
     被邀请的一方（拿码绑进来的）不再被问 —— 对方填的日期就是他看到的日期。
     created_by 为空的是老数据，按原行为处理（谁缺就谁被问）。 */
  const isInvitee = !!(couple?.created_by && me?.id && couple.created_by !== me.id);
  if (couple && !couple.start_date && !isSkipped('start') && !isInvitee) {
    steps.push('start');
  }
  return steps;
}

/** 拉一次资料，给出步骤与预填值。没登录 / 读不到资料时返回空步骤。 */
export async function resolveIntro() {
  let me = null;
  let couple = null;
  try { me = await getMe(); } catch (_) { return { steps: [], me: null, couple: null }; }
  try { couple = await getCouple(); } catch (_) { /* 未绑定就是 null */ }
  return {
    steps: buildIntroSteps(me, couple),
    me,
    couple,
    prefill: { nickname: me?.nickname || '', birthday: me?.birthday || '' },
  };
}
