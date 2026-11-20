/* API 基础地址。

- 网页里（Vite 开发 / 同源托管）：用相对路径，开发期由 Vite 代理转发到 8000，
  生产同源部署天然走当前域名，不需要写死主机。
- Capacitor 原生壳里页面是本地协议（capacitor://、https://localhost），
  相对路径打不到后端，必须用绝对地址。这里集中一处，以后换成正式域名只改这里。
*/

import { isNative } from '../native.js';

// 原生壳必须打绝对地址。打包时用 VITE_API_ORIGIN 注入线上域名，
// 例如 VITE_API_ORIGIN=https://cove.yourdomain.com；
// 没注入时退回本机地址，只够真机连着本地后端联调。
// 千万别把 127.0.0.1 打包进正式 App —— 那个地址在手机上指的是手机自己。
const NATIVE_API_ORIGIN = import.meta.env.VITE_API_ORIGIN || 'http://127.0.0.1:8000';

export const API_ORIGIN = isNative ? NATIVE_API_ORIGIN : '';
export const API_PREFIX = '/api/v1';
export const API_BASE = `${API_ORIGIN}${API_PREFIX}`;

/** 把对象存储 key 拼成可访问的图片地址；完整 URL 原样返回。 */
export function fileUrl(key) {
  if (!key) return '';
  if (key.startsWith('http://') || key.startsWith('https://')) return key;
  return `${API_ORIGIN}/uploads/${key}`;
}
