/* 设置相关接口。对应后端 app/modules/users、couples、privacy、notifications。
 *
 * 收口账号资料、绑定关系、注销、通知与改密。
 */

import { get, post, put, postForm } from './client.js';
import { setToken, setRefreshToken, getRefreshToken, clearToken } from './token.js';

/* ---- 账号资料 ---- */

/** 当前登录用户信息 */
export function getMe() {
  return get('/users/me');
}

/** 更新昵称 / 头像(avatar 为 object key) / 生日(birthday 传 null 可清除) */
export function updateProfile(body) {
  return put('/users/me', body);
}

/** 上传头像文件，返回 { key, url }；拿到 key 后再调 updateProfile 设置 */
export function uploadAvatar(file) {
  const form = new FormData();
  form.append('file', file);
  return postForm('/uploads/avatar', form);
}

/** 修改密码。body: { old_password, new_password }
 *  后端改密后会吊销全部 refresh token 并返回新的一对，必须存下来，
 *  否则当前设备 30 分钟后会掉线。 */
export async function changePassword(body) {
  const data = await post('/auth/change-password', body);
  if (data?.access_token) setToken(data.access_token);
  if (data?.refresh_token) setRefreshToken(data.refresh_token);
  return data;
}

/** 退出当前设备登录：带上本地 refresh token，并清空本地登录态 */
export async function logout(refresh_token) {
  const token = refresh_token || getRefreshToken();
  try {
    await post('/auth/logout', { refresh_token: token });
  } finally {
    clearToken();
  }
}

/** 退出所有设备：吊销该账号全部 refresh token，并清空本地登录态 */
export async function logoutAll() {
  try {
    const data = await post('/auth/logout-all');
    return data;
  } finally {
    clearToken();
  }
}

/* ---- 绑定关系 ---- */

/** 我的情侣关系（未绑定时返回 null） */
export function getCouple() {
  return get('/couples/me');
}

/** 生成邀请码 */
export function createInvite() {
  return post('/couples/invite');
}

/** 更新关系资料。body: { start_date: 'YYYY-MM-DD' | null } */
export function updateCouple(body) {
  return put('/couples/me', body);
}

/** 用邀请码绑定。body: { code }（以实际后端字段为准） */
export function bindCouple(body) {
  return post('/couples/bind', body);
}

/** 解除绑定。后端要求显式 confirm=true，reason 可选。
 *  给 15s 超时：解绑成功后要清向量库，万一那一步挂住，前端不能永远停在「正在解除…」。 */
export function unbindCouple(reason) {
  return post('/couples/unbind', { confirm: true, reason: reason || null }, { timeoutMs: 15000 });
}

/** 解绑前那张「你们攒下了什么」：相恋天数 + 各类记录条数，只读 */
export function getUsStats() {
  return get('/couples/us/stats');
}

/* ---- 隐私 ---- */

/** 注销账号。同样加超时：后端要删数据 + 清向量，挂住时前端得能恢复按钮。 */
export function deleteAccount(body) {
  return post('/privacy/delete', body, { timeoutMs: 20000 });
}

/* ---- 通知 ---- */

export function listNotifications() {
  return get('/notifications');
}
export function getUnreadCount() {
  return get('/notifications/unread-count');
}
export function markNotificationRead(id) {
  return post(`/notifications/${id}/read`);
}
export function markAllNotificationsRead() {
  return post('/notifications/read-all');
}
