/* 金币与金币申请接口。

对应后端 app/modules/coins（余额/赠与/流水）
和 app/modules/coin_applies（申请/审批）。
*/

import { get, post, postForm } from './client.js';

/* ---------------- 金币 ---------------- */

/** 我的金币余额 */
export function getBalance() {
  return get('/coins/balance');
}

/** 赠与金币：系统发行给对方，不扣自己余额；带幂等键防重复发币 */
export function giftCoins(amount, remark = null, idempotencyKey = null) {
  return post('/coins/gift', {
    amount,
    remark,
    idempotency_key: idempotencyKey,
  });
}

/** 我的金币流水，分页 */
export function listTransactions(limit = 20, offset = 0) {
  return get(`/coins/transactions?limit=${limit}&offset=${offset}`);
}

/* ---------------- 金币申请 ---------------- */

/** 发起金币申请：{ amount, reason, evidenceKey }，evidenceKey 为照片证明 key，可选 */
export function createApply(amount, reason, evidenceKey = null) {
  return post('/coin-applies', {
    amount,
    reason,
    evidence_key: evidenceKey,
  });
}

/** 上传索要金币的照片证明，返回 { key, url, ... }；key 用于 createApply */
export function uploadEvidence(file) {
  const form = new FormData();
  form.append('file', file);
  return postForm('/uploads/evidence', form);
}

/** 我发起过的申请（所有状态） */
export function listMyApplies() {
  return get('/coin-applies');
}

/** 等我审批的申请 */
export function listPendingApplies() {
  return get('/coin-applies/pending');
}

/** 通过申请，amount 不传则按申请金额发放 */
export function approveApply(applyId, amount = null, remark = null) {
  return post(`/coin-applies/${applyId}/approve`, { amount, remark });
}

/** 拒绝申请 */
export function rejectApply(applyId, remark = null) {
  return post(`/coin-applies/${applyId}/reject`, { remark });
}
