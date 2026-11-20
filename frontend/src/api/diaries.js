/* 日记接口：列表、创建、更新、删除、图片上传。
   后端见 app/modules/diaries/router.py 与 app/modules/uploads/router.py。 */

import { get, post, put, del, postForm } from './client.js';

/* 后端没有「日期」字段，删改都靠 id；一次多取一些（后端上限 100） */
export const listDiaries = (params = {}) => {
  const qs = new URLSearchParams();
  qs.set('limit', String(params.limit ?? 100));
  if (params.offset) qs.set('offset', String(params.offset));
  if (params.mode) qs.set('mode', params.mode);
  if (params.event_id) qs.set('event_id', params.event_id);
  return get(`/diaries?${qs.toString()}`);
};

export const createDiary = (body) => post('/diaries', body);

export const updateDiary = (id, body) => put(`/diaries/${id}`, body);

export const removeDiary = (id) => del(`/diaries/${id}`);

/* 返回 { key, url }：key 存进日记的 images，url 只用于预览 */
export const uploadDiaryImage = (file) => {
  const form = new FormData();
  form.append('file', file);
  return postForm('/uploads/diary-image', form);
};
