/* 认证接口：登录、注册。拿到 token 后立刻存起来。
   access 过期后的续期在 client.js 里统一处理，这里不再维护一份。 */

import { post } from './client.js';
import { setToken, setRefreshToken } from './token.js';

function saveToken(data) {
  if (data?.access_token) setToken(data.access_token);
  if (data?.refresh_token) setRefreshToken(data.refresh_token);
  return data;
}

/** 手机号 + 密码登录 */
export async function login(phone, password) {
  const data = await post('/auth/login', { phone, password }, { auth: false });
  return saveToken(data);
}

/** 注册并自动登录 */
export async function register(phone, password, nickname) {
  const data = await post(
    '/auth/register',
    { phone, password, nickname },
    { auth: false },
  );
  return saveToken(data);
}
