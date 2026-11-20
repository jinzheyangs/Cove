/* 最小 HTTP 客户端：所有普通（非流式）接口都从这里走。

职责：
1. 拼地址、自动带 Authorization
2. 解析统一外壳 {code, message, data}
3. 把业务错误（code !== 0）和网络错误统一抛成 ApiError，组件里好判断
*/

import { API_BASE } from './config.js';
import { getToken, setToken, getRefreshToken, setRefreshToken, clearToken } from './token.js';

export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

/* access token 只有 30 分钟，过期时先用 refresh 换新的再重放这次请求。
   并发请求会同时拿到 401，所以刷新做单飞：同一时间只有一个在换。 */
let refreshing = null;

/* 多个窗口/多个标签页同时过期时会互相踩：A 刷新成功后后端立刻吊销旧 refresh token，
   B 拿着同一个旧 token 去换就必然 401、被登出。所以失败后先看 localStorage 有没有被
   别的窗口换掉，换掉了就直接复用它的 access token。 */
async function waitForOtherWindow(before) {
  for (let i = 0; i < 3; i += 1) {
    if (getRefreshToken() !== before) {
      const access = getToken();
      if (access) return access;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  return null;
}

async function refreshAccessToken() {
  const refresh_token = getRefreshToken();
  if (!refresh_token) return null;
  if (refreshing) return refreshing;

  refreshing = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token }),
      });
      const text = await res.text();
      const payload = text ? JSON.parse(text) : null;
      if (!res.ok || !payload || payload.code !== 0 || !payload.data?.access_token) {
        return waitForOtherWindow(refresh_token);
      }
      setToken(payload.data.access_token);
      // 后端轮换 refresh，必须保存新值，否则下一次刷新会失败
      if (payload.data.refresh_token) setRefreshToken(payload.data.refresh_token);
      return payload.data.access_token;
    } catch (_) {
      return waitForOtherWindow(refresh_token);
    } finally {
      refreshing = null;
    }
  })();

  return refreshing;
}

async function request(path, { method = 'GET', body, headers = {}, auth = true, retried = false, timeoutMs = 0 } = {}) {
  const finalHeaders = { ...headers };
  // FormData 交给浏览器自动带 multipart boundary，不能手动设 Content-Type
  const isForm = body instanceof FormData;
  if (body !== undefined && !isForm) finalHeaders['Content-Type'] = 'application/json';
  if (auth) {
    const token = getToken();
    if (token) finalHeaders.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: finalHeaders,
      body: body !== undefined ? (isForm ? body : JSON.stringify(body)) : undefined,
      /* 只有明确给了 timeoutMs 的接口才上超时：解绑、注销这类「点下去就锁住按钮」的操作，
         一旦请求真的挂住，界面上就没有任何退路了。普通接口保持原来的无超时行为。 */
      ...(timeoutMs > 0 ? { signal: AbortSignal.timeout(timeoutMs) } : {}),
    });
  } catch (cause) {
    if (cause && (cause.name === 'TimeoutError' || cause.name === 'AbortError')) {
      throw new ApiError('请求超时了，请刷新后确认结果', -2, 0);
    }
    // 网络断了 / 后端没起 / CORS，fetch 会直接 reject
    throw new ApiError('网络连接失败，请检查后端是否启动', -1, 0);
  }

  // 后端即使出错也返回统一外壳，尝试解析；解析不了再按 HTTP 状态兜底
  let payload = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (_) {
      payload = null;
    }
  }

  /* 401：说明 access 过期（或已被吊销）。先尝试用 refresh 续一次并重放，
     续不上才清空登录态，让守卫把用户带回登录页。 */
  if (response.status === 401 && auth && !retried) {
    const fresh = await refreshAccessToken();
    if (fresh) {
      return request(path, { method, body, headers, auth, retried: true, timeoutMs });
    }
    clearToken();
  }

  if (!response.ok) {
    const code = payload?.code ?? response.status;
    const message = payload?.message ?? `请求失败（${response.status}）`;
    throw new ApiError(message, code, response.status);
  }

  // 2xx 但外壳 code 非 0，同样当业务错误
  if (payload && payload.code !== 0) {
    if (payload.code === 401) clearToken();
    throw new ApiError(payload.message || '业务处理失败', payload.code, response.status);
  }

  return payload ? payload.data : null;
}

export const get = (path, options) => request(path, { ...options, method: 'GET' });
export const post = (path, body, options) => request(path, { ...options, method: 'POST', body });
export const postForm = (path, formData, options) => request(path, { ...options, method: 'POST', body: formData });
export const put = (path, body, options) => request(path, { ...options, method: 'PUT', body });
export const del = (path, options) => request(path, { ...options, method: 'DELETE' });
