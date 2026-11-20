/* 共同清单接口。对应后端 app/modules/todos。
 *
 * type: shared(共同) / personal(单人)；
 * status: pending / completed / cancelled。
 * complete 会额外返回一张纪念卡片 card。
 */

import { get, post, put, del } from './client.js';

/** 列出清单，可按 type/category/status 过滤 */
export function listTodos(params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  ).toString();
  return get(`/todos${qs ? `?${qs}` : ''}`);
}

/** 新建清单项。body: { type?, category, title, description?, idempotency_key? } */
export function createTodo(body) {
  return post('/todos', body);
}

/** 修改清单项。body: { category?, title?, description?, status? } */
export function updateTodo(id, body) {
  return put(`/todos/${id}`, body);
}

/** 完成清单项，返回 { todo, card } */
export function completeTodo(id) {
  return post(`/todos/${id}/complete`);
}

/** 删除清单项 */
export function deleteTodo(id) {
  return del(`/todos/${id}`);
}
