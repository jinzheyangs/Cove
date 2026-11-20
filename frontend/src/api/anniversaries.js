/* 纪念日接口。对应后端 app/modules/anniversaries。
 *
 * 列表统一包含：在一起(relationship)、双方生日(birthday)、自定义(custom)，
 * 按剩余天数从近到远排序。只有 custom 且 editable=true 的条目可改/删。
 */

import { get, post, put, del } from './client.js';

/** 全部倒计时条目 */
export function listAnniversaries() {
  return get('/anniversaries');
}

/** 新建自定义纪念日。body: { title, date, repeat_yearly?, idempotency_key? } */
export function createAnniversary(body) {
  return post('/anniversaries', body);
}

/** 修改自定义纪念日。body: { title?, date?, repeat_yearly? } */
export function updateAnniversary(id, body) {
  return put(`/anniversaries/${id}`, body);
}

/** 删除自定义纪念日 */
export function deleteAnniversary(id) {
  return del(`/anniversaries/${id}`);
}
