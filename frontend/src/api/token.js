/* 令牌存取，集中一处。

访问令牌（access，30 分钟）与刷新令牌（refresh，30 天）都要存：
- access 过期后由 client.js 自动用 refresh 换一对新的再重放请求，
  用户不会在半小时后被莫名其妙踢回登录页。
- 后端 refresh 是「旋转式」的：旧 refresh 用过即失效，必须保存返回的新值。

存在 localStorage 里，刷新页面不丢。隐私模式下 localStorage 可能抛异常，
统一吞掉，退化成内存态，保证业务不崩。
*/

const ACCESS_KEY = 'cove.access_token';
const REFRESH_KEY = 'cove.refresh_token';

let memoryToken = '';
let memoryRefresh = '';

function read(key, fallback) {
  try {
    return localStorage.getItem(key) || fallback;
  } catch (_) {
    return fallback;
  }
}

function write(key, value) {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch (_) {
    /* 隐私模式：只保留内存值 */
  }
}

export function getToken() {
  return read(ACCESS_KEY, memoryToken);
}

export function setToken(token) {
  memoryToken = token || '';
  write(ACCESS_KEY, memoryToken);
}

export function getRefreshToken() {
  return read(REFRESH_KEY, memoryRefresh);
}

export function setRefreshToken(token) {
  memoryRefresh = token || '';
  write(REFRESH_KEY, memoryRefresh);
}

/** 登录态整体清空：access 与 refresh 一起清，避免残留的 refresh 被复用 */
export function clearToken() {
  setToken('');
  setRefreshToken('');
}

/* 换号时还要清「设备级」缓存。
   这些键不按用户区分，一台设备上 A 退出、B 登录时，
   B 会看到 A 设的本月基金预算、上次的金额，以及 A 的模拟 TA 会话 id。
   引导标记是按 uid 分键的（cove.intro.<uid>.*），不能清，否则换个号又从头问一遍。 */
const ACCOUNT_SCOPED_PREFIXES = ['cove.bill.', 'cove.simta_conv'];

export function purgeAccountCache() {
  try {
    const doomed = [];
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i) || '';
      if (ACCOUNT_SCOPED_PREFIXES.some((p) => key === p || key.startsWith(p))) {
        doomed.push(key);
      }
    }
    doomed.forEach((key) => localStorage.removeItem(key));
  } catch (_) {
    /* 隐私模式：本来就没写进去，没东西可清 */
  }
}
