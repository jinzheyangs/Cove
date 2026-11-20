/* 模拟Ta 的授权状态接口。 */

import { get, put } from './client.js';

/** 查看双方授权状态 */
export function getSimtaState() {
  return get('/sim-ta');
}

/** 开启 / 撤销授权 */
export function setConsent(authorized) {
  return put('/sim-ta/consent', { authorized });
}
