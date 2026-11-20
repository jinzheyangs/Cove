/* 商城接口：商品上下架、订单购买/核销/取消。

对应后端 app/modules/mall，统一外壳已由 client.js 解包，这里只返回 data。
*/

import { get, post } from './client.js';

/* ---------------- 商品 ---------------- */

/** 已上架（approved）商品，双方看到同一份 */
export function listItems() {
  return get('/mall/items');
}

/** 我上架的全部商品（含已上架/已下架） */
export function listMyItems() {
  return get('/mall/items/mine');
}

/** 上架商品，提交后直接上架；body: { title, description, price_coins, max_orders } */
export function createItem(body) {
  return post('/mall/items', body);
}

/** 下架自己上架的商品 */
export function offlineItem(itemId) {
  return post(`/mall/items/${itemId}/offline`);
}

/** 编辑商品，保存后直接生效；body: { title, description, price_coins, max_orders } */
export function editItem(itemId, body) {
  return post(`/mall/items/${itemId}/edit`, body);
}

/* ---------------- 订单 ---------------- */

/** 关系内全部订单 */
export function listOrders() {
  return get('/mall/orders');
}

/** 购买：扣币并生成待兑现订单；idempotencyKey 防重复扣币 */
export function buyItem(itemId, idempotencyKey) {
  return post('/mall/orders', { item_id: itemId, idempotency_key: idempotencyKey });
}

/** 核销：商品创建者确认订单已兑现 */
export function completeOrder(orderId) {
  return post(`/mall/orders/${orderId}/complete`);
}

/** 取消：买家取消待兑现订单，金币原路退回 */
export function cancelOrder(orderId) {
  return post(`/mall/orders/${orderId}/cancel`);
}
