/* Agent 模拟对话接口：会话管理 + 流式发消息 + 待确认动作。 */

import { get, post } from './client.js';
import { streamSse } from './sse.js';

/** 新建会话，persist=true 时服务端保存消息，返回会话详情 */
export function createConversation(title = null, persist = true) {
  return post('/agent/conversations', { title, persist });
}

/** 会话详情（含历史消息） */
export function getConversation(id) {
  return get(`/agent/conversations/${id}`);
}

/**
 * 把这次对话切成记忆块存起来（离开「模拟 Ta」页面时调用）。
 * 重复调用幂等：块内容没变不会重复入库。
 */
export function memorizeConversation(id) {
  return post(`/agent/conversations/${id}/memorize`);
}

/**
 * 流式发一条消息，异步生成器产出 SSE 事件。
 * 事件：delta / tool / confirm / done / error。
 */
export async function* streamMessage(conversationId, message, { history = [], signal } = {}) {
  yield* streamSse(
    `/agent/conversations/${conversationId}/messages/stream`,
    { message, history },
    signal,
  );
}

/** 确认 Agent 提议的写操作（幂等） */
export function confirmAction(actionId) {
  return post(`/agent/actions/${actionId}/confirm`);
}

/** 取消 Agent 提议的写操作 */
export function cancelAction(actionId) {
  return post(`/agent/actions/${actionId}/cancel`);
}
