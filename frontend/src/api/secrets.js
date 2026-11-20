/* 秘密树接口。对应后端 app/modules/secrets。

约定（与后端 router.py 一致）：
- 列表接口永远不返回 content
- 只有 unlock 才返回内容并扣币，并且读完即销毁（没有阅后即焚开关）
- 销毁只能作用于自己发布的秘密
*/

import { get, post, del } from './client.js';

/** 对方发布、我还能摘的秘密（不含内容） */
export function listAvailable() {
  return get('/secrets');
}

/** 我发布的秘密（含被摘取、已销毁） */
export function listMine() {
  return get('/secrets/mine');
}

/** 发布一条秘密。body: { content, level, cost_coins? } */
export function publishSecret(body) {
  return post('/secrets', body);
}

/** 花金币摘取，返回含 content 的详情；余额不足会抛业务错误。读完这条就被销毁 */
export function unlockSecret(id) {
  return post(`/secrets/${id}/unlock`);
}

/** 销毁单条（只能销毁自己的） */
export function destroySecret(id) {
  return del(`/secrets/${id}`);
}
