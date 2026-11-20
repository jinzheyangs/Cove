/* 恋爱账本接口。对应后端 app/modules/bills。
 *
 * type: money / time / energy / emotion；scope: shared / personal。
 * 读取接口由后端自动过滤对方的隐私支出。
 * stats 只给共同视角，不提供个人对比。
 */

import { get, post, put, del } from './client.js';

/** 列出可见账目，可按 type/scope 过滤 */
export function listBills(params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  ).toString();
  return get(`/bills${qs ? `?${qs}` : ''}`);
}

/** 统计汇总（共同视角） */
export function getBillStats() {
  return get('/bills/stats');
}

/** 记一笔。body: { amount?, category, type?, scope?, is_private?, remark?, idempotency_key? } */
export function createBill(body) {
  return post('/bills', body);
}

/** 更新自己记的账，body 结构同 create */
export function updateBill(id, body) {
  return put(`/bills/${id}`, body);
}

/** 删除自己记的账 */
export function deleteBill(id) {
  return del(`/bills/${id}`);
}
