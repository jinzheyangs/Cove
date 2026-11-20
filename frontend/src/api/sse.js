/* SSE 流式解析。

为什么不用 EventSource：EventSource 只能发 GET、不能带自定义 Authorization 头，
而这个接口是 POST + Bearer 鉴权，所以用 fetch + ReadableStream 自己解析。

后端一帧的样子（空行分隔一条消息）：
  event: delta
  data: {"delta": "你好"}

本模块对外是一个异步生成器，yield 解析后的普通对象：
  { event: 'delta', data: { delta: '你好' } }
*/

import { API_BASE } from './config.js';
import { getToken, clearToken } from './token.js';
import { ApiError } from './client.js';

/** 解析一条完整 SSE 消息（不含结尾空行），返回 {event, data} */
function parseSseMessage(raw) {
  let event = 'message';
  const dataLines = [];
  for (const line of raw.split('\n')) {
    // SSE 行以冒号开头是注释，忽略
    if (!line || line.startsWith(':')) continue;
    const idx = line.indexOf(':');
    const field = idx === -1 ? line : line.slice(0, idx);
    // 规范要求去掉值前面的一个空格（如果有）
    let value = idx === -1 ? '' : line.slice(idx + 1);
    if (value.startsWith(' ')) value = value.slice(1);

    if (field === 'event') event = value;
    else if (field === 'data') dataLines.push(value);
  }
  let data = null;
  const dataStr = dataLines.join('\n');
  if (dataStr) {
    try {
      data = JSON.parse(dataStr);
    } catch (_) {
      data = dataStr; // 不是 JSON 就原样返回
    }
  }
  return { event, data };
}

/**
 * 发起一次 SSE 请求，异步生成器逐条产出事件。
 * 支持 AbortSignal 中断（用户离开页面 / 主动停止）。
 */
export async function* streamSse(path, body, signal) {
  const token = getToken();
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
  } catch (cause) {
    if (cause?.name === 'AbortError') return;
    throw new ApiError('网络连接失败，请检查后端是否启动', -1, 0);
  }

  // 进入事件流之前的校验错误（401/403/404 等）以普通 HTTP 状态返回
  if (!response.ok || !response.body) {
    let payload = null;
    const text = await response.text();
    try {
      payload = JSON.parse(text);
    } catch (_) {
      payload = null;
    }
    if (response.status === 401) clearToken();
    throw new ApiError(
      payload?.message ?? `请求失败（${response.status}）`,
      payload?.code ?? response.status,
      response.status,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      // stream:true 让多字节字符跨 chunk 时不会乱码
      buffer += decoder.decode(value, { stream: true });

      // SSE 以空行分隔消息；兼容 \n\n 和 \r\n\r\n
      let sep;
      while ((sep = findSeparator(buffer)) !== -1) {
        const raw = buffer.slice(0, sep.index);
        buffer = buffer.slice(sep.after);
        const trimmed = raw.replace(/\r/g, '');
        if (trimmed) yield parseSseMessage(trimmed);
      }
    }
    // 流结束后 buffer 里可能还剩最后一条没带空行的消息
    const tail = buffer.replace(/\r/g, '').trim();
    if (tail) yield parseSseMessage(tail);
  } finally {
    // 无论正常结束还是异常/中断，都释放 reader
    try {
      reader.releaseLock();
    } catch (_) {
      /* 已释放则忽略 */
    }
  }
}

function findSeparator(str) {
  const lf = str.indexOf('\n\n');
  const crlf = str.indexOf('\r\n\r\n');
  if (lf === -1 && crlf === -1) return -1;
  if (lf === -1) return { index: crlf, after: crlf + 4 };
  if (crlf === -1) return { index: lf, after: lf + 2 };
  // 两种都在，取靠前的
  return lf < crlf
    ? { index: lf, after: lf + 2 }
    : { index: crlf, after: crlf + 4 };
}
