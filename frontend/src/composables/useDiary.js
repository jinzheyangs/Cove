/* ============================================================
   日记功能的数据与交互逻辑
   - 目前用 mock（与 MoodDeck / QuestionPanel 一致），后端改造后
     只需替换这里的数据源与请求，视图组件不动。
   - 日历交互 1:1 对齐 diary-journal-demo.html：
     按天分页、拖拽跟手、0.4 格阈值、一次只走一天、没到回弹、
     选中胶囊在可见 7 天内逐格移动，到边界才贴边带动轨道。
   ============================================================ */

import { ref, computed, nextTick, reactive } from 'vue';
import { getMe, getCouple } from '../api/settings.js';
import { fileUrl } from '../api/config.js';
import { listDiaries, createDiary, updateDiary, uploadDiaryImage } from '../api/diaries.js';

/* ---------- 日期工具 ---------- */
const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const CN = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

const keyOf = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
function addDays(d, n) {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}
/* 没写标题时，拿正文的头一行当这篇的名字（列表和详情都用它） */
function firstLine(text) {
  const s = String(text || '').replace(/\s+/g, ' ').trim();
  return s ? s.slice(0, 18) : '';
}
function mondayOf(d) {
  const x = new Date(d);
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  x.setHours(0, 0, 0, 0);
  return x;
}

/* ---------- 35 天连续日期（mock 基准固定为 2026-11-08） ---------- */
const THIS = new Date();
const TODAY = new Date(THIS.getFullYear(), THIS.getMonth(), THIS.getDate());
/* 35 天窗口：今天是最右一格，往前数 34 天。
   日记只往回写，右边不留未来空格——否则顶部胶囊右半屏全是灰的"还没到"。 */
const DAYS = [];
for (let i = 0; i < 35; i += 1) DAYS.push(addDays(TODAY, i - 34));
const dateIndex = {};
DAYS.forEach((d, i) => {
  dateIndex[keyOf(d)] = i;
});

/* ============ 数据源：后端 app/modules/diaries + app/modules/uploads ============

   后端一篇 diary 只有一个作者和一段正文；两个人写同一件事靠 event_id 关联
   （同一 event_id 的两条 personal，按 author_id 分出「我的」和「TA 的」）。
   UI 要的是「一天一篇、两边各一段心得」，所以这里把 event 聚合成一篇，
   顺便把 mood_tags 里约定的 [分类, 心情] 拆回列表标签。

   日期：后端没有单独的日期字段，用 created_at 的本地日期做分组键。
*/

const ME = ref(0);              // 当前用户 id，用来分「我写的 / TA 写的」
const loading = ref(false);
const error = ref('');

const hmOf = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};
const uuid = () => {
  if (globalThis.crypto && globalThis.crypto.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/x/g, () =>
    Math.floor(Math.random() * 16).toString(16));
};
const dayKeyOf = (iso) => keyOf(new Date(iso));

/* 一篇后端 diary 的图片 → 能直接给 <img> 用的地址。
   images 存的是存储 key（couples/../xx.png），统一用 fileUrl 拼；
   image_urls 是后端拼好的 /uploads/xx，去掉重复前缀再交给 fileUrl，
   免得原生壳里拼成 /uploads/uploads/... */
const toSrc = (k) => {
  if (!k) return '';
  if (/^http(s)?:/.test(k)) return k;
  const clean = k.startsWith('/uploads/') ? k.slice('/uploads'.length) : k;
  return fileUrl(clean);
};
const imgList = (row) => {
  /* 优先用后端生成的可访问地址：OSS 模式下它是签名 URL，
     而 images 里的 key 在本地存储之外是取不到的。
     只有在后端没给 image_urls 时才退回用 key 拼本地路径。 */
  const urls = (row.image_urls || []).filter(Boolean).map(toSrc);
  if (urls.length) return urls;
  return (row.images || []).filter(Boolean).map(toSrc);
};

/* 一批同 event 的 rows → 一天里的那篇 */
function toDay(rows) {
  const sorted = rows.slice().sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  const first = sorted[0];
  const mine = sorted.find((r) => r.author_id === ME.value) || null;
  const ta = sorted.find((r) => r.author_id !== ME.value) || null;
  const tags = (first.mood_tags || []).filter(Boolean);
  const shots = imgList(first);
  return {
    id: mine ? mine.id : first.id,
    /* 只有自己那篇才删得掉：列表左滑删除用这个 id，别把对方写的删了 */
    mineId: mine ? mine.id : null,
    taId: ta ? ta.id : null,
    eventId: first.event_id || null,
    title: first.title || firstLine(first.content) || '那天',
    photos: shots.length,
    shots,
    tag: tags[0] || '日常',
    c: TAG_C[tags[0]] || 'blue',
    /* 「两个人的心得」得两边都真的写了；只有对方写的时候不能算 */
    both: !!(mine && ta),
    place: first.location || '',
    mood: tags[1] || '',
    note: mine ? mine.content || '' : '',
    noteAt: mine ? hmOf(mine.created_at) : '',
    tnote: ta ? ta.content || '' : '',
    tnoteAt: ta ? hmOf(ta.created_at) : '',
    /* 这一篇是谁写的：有人只写了对方那份时，署名得署真正写的那个，不能一律写「我」 */
    writer: first.author_id === ME.value ? 'me' : 'ta',
    wroteAt: hmOf(first.created_at),
  };
}

const DIARY = reactive({});

async function loadDiaries() {
  loading.value = true;
  error.value = '';
  try {
    if (!ME.value) {
      const me = await getMe();
      ME.value = (me && me.id) || 0;
    }
    if (diaryNames.me === '我') await loadNames();
    const rows = await listDiaries({ limit: 100 });
    const byEvent = new Map();
    for (const r of rows || []) {
      if (!r) continue;
      const ek = r.event_id || `one:${r.id}`;
      if (!byEvent.has(ek)) byEvent.set(ek, []);
      byEvent.get(ek).push(r);
    }
    const next = {};
    /* 同一天可以写好几篇：一天的第一篇占日期键本身（日历和锚点靠它判断"这天有日记"），
       其余按时间倒序挂成 `${日期}#1`、`${日期}#2` …… 以前这里只留写得最晚的一篇，
       同一天发第二篇时，前一篇就被顶掉了。 */
    const perDay = new Map();
    for (const group of byEvent.values()) {
      const day = toDay(group);
      const k = dayKeyOf(group[0].created_at);
      if (!perDay.has(k)) perDay.set(k, []);
      perDay.get(k).push({ ...day, at: group[0].created_at });
    }
    for (const [k, items] of perDay) {
      items.sort((a, b) => new Date(b.at) - new Date(a.at));
      items.forEach((item, i) => {
        const { at, ...info } = item;
        next[i === 0 ? k : `${k}#${i}`] = info;
      });
    }
    /* 先清掉已经不在后端的键，避免删掉的那篇还留在索引里 */
    Object.keys(DIARY).forEach((k) => {
      if (!(k in next)) delete DIARY[k];
    });
    Object.entries(next).forEach(([k, v]) => {
      const { at, ...info } = v;
      DIARY[k] = info;
    });
  } catch (e) {
    error.value = (e && e.message) || '日记没加载出来';
  } finally {
    loading.value = false;
  }
}

/* dataURL → File：后端上传接口收 multipart */
async function dataUrlToFile(src, name) {
  const blob = await (await fetch(src)).blob();
  return new File([blob], name || 'diary.jpg', { type: blob.type || 'image/jpeg' });
}

/* 两个人的昵称：详情页署名、列表头像、心得落款都读这里，
   不再写死「林深 / 阿屿」。ta 没绑定时退回 TA。 */
export const diaryNames = reactive({ me: '我', ta: 'TA' });
const initial = (s) => (s || '?').trim().slice(0, 1) || '?';
export const diaryInitials = computed(() => ({
  me: initial(diaryNames.me),
  ta: initial(diaryNames.ta),
}));

/* 拉一下两个人的昵称（失败不致命，界面退回「我 / TA」） */
async function loadNames() {
  try {
    const me = await getMe();
    if (me) {
      ME.value = me.id || ME.value;
      diaryNames.me = me.nickname || '我';
    }
  } catch (_) { /* 未登录 */ }
  try {
    const couple = await getCouple();
    if (couple && couple.partner) diaryNames.ta = couple.partner.nickname || 'TA';
  } catch (_) { /* 没绑定 */ }
}

const phClass = ['ph1', 'ph2', 'ph3', 'ph4', 'ph5', 'ph6'];

/* 列表分组：只含有日记的天，供 v-for 渲染。
   按时间倒序（新的在最上面）——日记这类内容用户先看最近写的，
   所以列表顺序和顶部日历的从左到右顺序是相反的，联动逻辑按 DOM 顺序走，不受影响。
   同一天有多篇时，这一天会产出多张卡，但日期标题只在第一张上说一次。 */
const groups = computed(() => {
  /* 先按天收集，再把「天」这个层级整体倒序 ——
     不能把所有卡摊平后整体 reverse，那样同一天里的两篇会前后调个个儿，
     日期标题就会跑到第二张卡头上。 */
  const days = [];
  DAYS.forEach((d, i) => {
    const base = keyOf(d);
    const title = `${d.getMonth() + 1} 月 ${d.getDate()} 日 · ${CN[(d.getDay() + 6) % 7]}`;
    const entries = [];
    let key = base;
    let n = 0;
    while (DIARY[key]) {
      entries.push({
        date: d,
        key,
        idx: i,
        info: DIARY[key],
        ph: phClass[i % phClass.length],
        first: n === 0,
        groupTitle: title,
        sameDay: n,
      });
      n += 1;
      key = `${base}#${n}`;
    }
    if (entries.length) days.push(entries);
  });
  return days.reverse().flat();
});

/* ---------- 日历布局常量 ---------- */
const SLOT = 1;        // 初始选中胶囊在左起第 2 格
const MAXSLOT = 6;     // 可见最右格
const PILLW = 41;
const TOTAL = 35;

/* 标签 → 列表标签配色（列表只定义了 pink / green / blue 三档） */
const TAG_C = { 约会: 'pink', 运动: 'green', 日常: 'blue', 美食: 'pink', 旅行: 'green' };
const NOW_HM = () => {
  const n = new Date();
  return `${String(n.getHours()).padStart(2, '0')}:${String(n.getMinutes()).padStart(2, '0')}`;
};

/* 子页面：list / detail / new。
   放在模块级单例上，App 外壳也要读它（详情/发布是二级页，底栏要让位） */
export const diarySubPage = ref('list');

export function useDiary() {
  const subPage = diarySubPage;

  /* 当前打开的那一篇（详情页 / 发布后回到详情都靠它） */
  const selectedKey = ref('');
  const detail = computed(() => {
    const k = selectedKey.value;
    const info = DIARY[k];
    if (!info) return null;
    /* 键可能是 `2026-11-19#1`：日期部分取 # 前面那段 */
    const base = k.split('#')[0];
    const idx = dateIndex[base] ?? 0;
    const d = new Date(`${base}T00:00:00`);
    return {
      key: k,
      info,
      idx,
      ph: phClass[idx % phClass.length],
      dayNum: String(d.getDate()).padStart(2, '0'),
      monthLabel: `${d.getMonth() + 1} 月`,
      weekCN: CN[(d.getDay() + 6) % 7],
      year: d.getFullYear(),
    };
  });

  function openDetail(key) {
    selectedKey.value = key;
    subPage.value = 'detail';
  }
  function openNew() {
    subPage.value = 'new';
  }
  function backToList() {
    subPage.value = 'list';
  }
  /* 发布一篇：先把刚选的照片传到后端换 key，再建日记。
     上传要并发——串行 6 张各等一次往返，点发布后会明显停顿。 */
  async function addDiary(payload) {
    const shots = Array.isArray(payload.shots) ? payload.shots.slice(0, 9) : [];
    const uploaded = await Promise.all(
      shots.map(async (src, i) => {
        if (!src) return null;
        /* 已经是 http 的说明这条早就在存储里了，别再传一次 */
        if (/^https?:/.test(src)) return src;
        try {
          const file = await dataUrlToFile(src, `diary-${i}.jpg`);
          const up = await uploadDiaryImage(file);
          return (up && up.key) || null;
        } catch (_) {
          /* 单张传失败就跳过，别让整篇发不出去 */
          return null;
        }
      })
    );
    const keys = uploaded.filter(Boolean);

    const body = {
      mode: 'personal',
      title: (payload.title || '').trim() || null,
      /* 只发照片不写心得也行，后端 content 允许空串 */
      content: (payload.note || '').trim(),
      mood_tags: [payload.tag, payload.mood].filter(Boolean),
      location: (payload.place || '').trim() || null,
      images: keys,
      event_id: uuid(),
      idempotency_key: uuid(),
    };
    const created = await createDiary(body);
    ME.value = ME.value || (created && created.author_id) || 0;

    /* 新的一篇排到今天的第一个位置，同一天之前写过的往后顺延 ——
       既不覆盖别人 / 自己的旧记录，又跟刷新后 loadDiaries 的顺序一致（新的在上）。 */
    const base = keyOf(TODAY);
    const fresh = {
      id: created.id,
      taId: null,
      eventId: created.event_id,
      title: created.title || (payload.title || '').trim() || firstLine(created.content) || '那天',
      photos: (created.image_urls || created.images || []).length,
      shots: imgList(created),
      tag: payload.tag || '日常',
      c: TAG_C[payload.tag] || 'blue',
      both: false,
      place: created.location || '',
      mood: payload.mood || '',
      note: created.content || '',
      noteAt: hmOf(created.created_at),
      tnote: '',
      tnoteAt: '',
    };
    const older = [];
    let i = 0;
    while (true) {
      const kk = i === 0 ? base : `${base}#${i}`;
      if (!DIARY[kk]) break;
      older.push(DIARY[kk]);
      i += 1;
    }
    [fresh, ...older].forEach((info, n) => {
      DIARY[n === 0 ? base : `${base}#${n}`] = info;
    });
    selectedKey.value = base;
    return base;
  }
  /* 改心得：有 id 就 PUT 到后端，没有（理论上不会）就只改本地 */
  async function updateNote(key, text) {
    const info = DIARY[key];
    if (!info) return;
    const next = String(text || '');
    if (info.id) {
      try {
        const saved = await updateDiary(info.id, { content: next });
        info.note = saved.content || '';
        info.noteAt = hmOf(saved.created_at);
        return;
      } catch (e) {
        throw e;
      }
    }
    info.note = next;
    info.noteAt = hmOf(new Date().toISOString());
  }

  const cellW = ref(0);
  const pos = ref(0);          // 整数：当前选中的日期索引
  const renderPos = ref(0);    // 浮点：布局渲染用的临时位置（拖拽跟手不污染 pos）
  const trackX = ref(0);       // 轨道向左平移量

  /* 锚点：每个分组对应的日期索引与在滚动容器内的 top */
  let anchors = [];

  /* 轨道与胶囊的样式（响应式绑定） */
  const trackWidth = computed(() => cellW.value * TOTAL);
  const trackTransform = computed(() => `translateX(${-trackX.value}px)`);
  const pillLeft = computed(
    () => renderPos.value * cellW.value - trackX.value + (cellW.value - PILLW) / 2
  );
  const nearestIdx = computed(() => Math.round(renderPos.value));
  const pillNum = computed(() => DAYS[nearestIdx.value].getDate());
  const pillWd = computed(() => WD[(DAYS[nearestIdx.value].getDay() + 6) % 7]);

  /* 布局：胶囊在可见窗口内移动，到边界才带动轨道滚动 */
  function layout(p) {
    let cellLeft = p * cellW.value - trackX.value;
    if (cellLeft > MAXSLOT * cellW.value) {
      trackX.value = p * cellW.value - MAXSLOT * cellW.value;
    } else if (cellLeft < 0) {
      trackX.value = p * cellW.value;
    }
    renderPos.value = p;
  }

  /* 测量日历宽度（mount 后调用） */
  function measure(calEl) {
    if (!calEl) return;
    cellW.value = calEl.clientWidth / 7;
  }

  /* 重新测量分组锚点（列表渲染后调用）。按 top 升序排，屏幕从上到下就是这个顺序
     （列表是倒序的，所以 top 越小日期越新）。 */
  function reanchor(scrollEl) {
    if (!scrollEl) return;
    const nodes = scrollEl.querySelectorAll('.grp');
    anchors = groups.value
      .map((g) => {
        const el = Array.from(nodes).find((n) => n.dataset.date === g.key);
        return el ? { key: g.key, idx: g.idx, el, top: el.offsetTop - 6 } : null;
      })
      .filter(Boolean)
      .sort((a, b) => a.top - b.top);
  }

  /* 滚动 → 日历：直接跟手，每帧一次，不做缓动。
     停靠点只取"当前最靠近顶部的那一篇"，中间没有日记的日子不落子，
     否则胶囊会停在 11-09 这种列表里根本没有的日期上。 */
  function syncFromScroll(scrollEl) {
    if (!anchors.length || !scrollEl) return;
    const st = scrollEl.scrollTop + 8;
    let i = 0;
    for (let k = 0; k < anchors.length; k += 1) {
      if (anchors[k].top <= st) i = k; else break;
    }
    const p = anchors[i].idx;
    layout(p);
    if (p !== pos.value) pos.value = p;
  }

  function nearestAnchor(idx) {
    return anchors.reduce(
      (best, a) => (Math.abs(a.idx - idx) < Math.abs(best.idx - idx) ? a : best),
      anchors[0]
    );
  }

  /* 只有写过日记的日子才允许被选中 / 点击 */
  function hasEntry(i) {
    const d = DAYS[i];
    return !!d && !!DIARY[keyOf(d)];
  }

  /* rAF 动画：easeOutCubic 到整数天；moveList 时列表同步滚动 */
  let suppress = false;
  let rafId = 0;
  function animateToIdx(idx, moveList, scrollEl) {
    const target = Math.max(0, Math.min(TOTAL - 1, idx));
    suppress = true;
    const from = renderPos.value;
    const t0 = performance.now();
    const dur = 460;
    cancelAnimationFrame(rafId);
    function tick(now) {
      let t = Math.min(1, (now - t0) / dur);
      t = 1 - Math.pow(1 - t, 3);
      layout(from + (target - from) * t);
      if (t < 1) {
        rafId = requestAnimationFrame(tick);
      } else {
        pos.value = target;
      }
    }
    rafId = requestAnimationFrame(tick);
    if (moveList && scrollEl) {
      const a = nearestAnchor(target);
      if (a) scrollEl.scrollTo({ top: a.top, behavior: 'smooth' });
    }
    setTimeout(() => {
      suppress = false;
    }, 820);
  }

  /* 列表滚动联动：直接跟手（每帧一次，不做缓动） */
  let scrollRaf = 0;
  function onListScroll(scrollEl) {
    if (suppress || !scrollEl || scrollRaf) return;
    scrollRaf = requestAnimationFrame(() => {
      scrollRaf = 0;
      syncFromScroll(scrollEl);
    });
  }

  /* ---------- 点日期 ----------
     这排日期不给手指划：位置只由"列表滚动"和"点某一格"决定。
     划到空格子容易把胶囊停在一条没有内容的日期上，干脆不做拖拽。 */
  function onTrackClick(e, scrollEl) {
    const cell = e.target.closest('.dcell');
    if (!cell) return;
    const idx = dateIndex[cell.dataset.date];
    if (idx === undefined || !hasEntry(idx)) return;
    animateToIdx(idx, true, scrollEl);
  }

  /* ---------- 月历快速跳转 ---------- */
  const monthOpen = ref(false);
  const mView = ref(new Date(TODAY.getFullYear(), TODAY.getMonth(), 1));
  const dayStart = DAYS[0];
  const dayEnd = DAYS[TOTAL - 1];
  /* 可选范围：窗口起点 ~ 今天。日记是往回记的，未来的日子还没有内容可看，
     所以日历上今天之后一律置灰（原来跟着 35 天窗口走到 11/22，看着像随便截断的）。
     顶部胶囊仍是完整 5 周窗口，右边那几格只是"还没到"，不动。 */
  const lastPickable = TODAY < dayEnd ? TODAY : dayEnd;
  const inRange = (d) => d >= dayStart && d <= lastPickable;

  const monthCells = computed(() => {
    const y = mView.value.getFullYear();
    const m = mView.value.getMonth();
    const firstDow = new Date(y, m, 1).getDay();
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const prevDays = new Date(y, m, 0).getDate();
    const selKey = keyOf(DAYS[nearestIdx.value]);
    const todayKey = keyOf(TODAY);
    const cells = [];

    for (let i = firstDow - 1; i >= 0; i -= 1) {
      const d = new Date(y, m - 1, prevDays - i);
      cells.push(buildCell(d, true, selKey, todayKey));
    }
    for (let dd = 1; dd <= daysInMonth; dd += 1) {
      cells.push(buildCell(new Date(y, m, dd), false, selKey, todayKey));
    }
    let n = 1;
    while (cells.length % 7 !== 0) {
      cells.push(buildCell(new Date(y, m + 1, n), true, selKey, todayKey));
      n += 1;
    }
    return cells;
  });

  function buildCell(d, other, selKey, todayKey) {
    const k = keyOf(d);
    const classes = ['m-cell'];
    if (other) classes.push('other');
    if (k === todayKey) classes.push('today');
    if (k === selKey) classes.push('sel');
    const hasDiary = !!DIARY[k];
    /* 没写日记的日子不给点：点进去也没有内容，只会把胶囊停在一条空格子上 */
    const ok = inRange(d) && hasDiary;
    if (!ok) classes.push('off');
    return { key: k, label: d.getDate(), classes, enabled: ok, hasDiary };
  }

  const monthTitle = computed(
    () => `${mView.value.getFullYear()} 年 ${mView.value.getMonth() + 1} 月`
  );

  /* ---------- 年月选择：点标题切到"年 + 12 个月"面板 ---------- */
  const ymOpen = ref(false);
  const ymYear = ref(TODAY.getFullYear());
  /* 未来月份不给选（还没到的月份里不会有日记） */
  const monthFloor = new Date(TODAY.getFullYear(), TODAY.getMonth(), 1);
  const ymMonths = computed(() => {
    const out = [];
    for (let m = 0; m < 12; m += 1) {
      const first = new Date(ymYear.value, m, 1);
      out.push({ m, label: m + 1, future: first > monthFloor });
    }
    return out;
  });
  const ymTitle = computed(() => `${ymYear.value} 年`);
  function openYm() {
    if (monthOpen.value === false) return;
    ymYear.value = mView.value.getFullYear();
    ymOpen.value = true;
  }
  function closeYm() {
    ymOpen.value = false;
  }
  function ymPrevYear() {
    ymYear.value -= 1;
  }
  function ymNextYear() {
    if (ymYear.value < TODAY.getFullYear()) ymYear.value += 1;
  }
  function pickYm(m) {
    mView.value = new Date(ymYear.value, m, 1);
    ymOpen.value = false;
  }

  function openMonth() {
    const cur = DAYS[nearestIdx.value];
    mView.value = new Date(cur.getFullYear(), cur.getMonth(), 1);
    ymOpen.value = false;
    monthOpen.value = true;
  }
  function closeMonth() {
    monthOpen.value = false;
    ymOpen.value = false;
  }
  function monthPrev() {
    if (ymOpen.value) {
      ymPrevYear();
      return;
    }
    mView.value = new Date(mView.value.getFullYear(), mView.value.getMonth() - 1, 1);
  }
  function monthNext() {
    if (ymOpen.value) {
      ymNextYear();
      return;
    }
    const next = new Date(mView.value.getFullYear(), mView.value.getMonth() + 1, 1);
    if (next > monthFloor) return;
    mView.value = next;
  }
  /* 到顶了就把右箭头置灰，别让用户一直点一个没反应 */
  const canNext = computed(() =>
    ymOpen.value ? ymYear.value < TODAY.getFullYear() : mView.value < monthFloor
  );
  const mViewYear = computed(() => mView.value.getFullYear());
  const mViewMonth = computed(() => mView.value.getMonth());
  function pickMonth(cell, scrollEl) {
    if (!cell.enabled) return;
    const idx = dateIndex[cell.key];
    closeMonth();
    if (idx !== undefined) animateToIdx(idx, true, scrollEl);
  }

  /* ---------- 初始化：停在最上面（也就是最新的一篇）；一篇都没有就停在今天 ---------- */
  async function init(calEl, scrollEl) {
    measure(calEl);
    await nextTick();
    reanchor(scrollEl);
    const first = groups.value[0];
    /* 空列表时以前兜底成 0，等于把日历开在 35 天前那一格，看着像日期错了。
       今天就是这串日期的最后一格，空着就对准它。 */
    const idx = first ? first.idx : TOTAL - 1;
    suppress = true;
    requestAnimationFrame(() => {
      scrollEl.scrollTop = 0;
      /* 最新一篇落在窗口最右时，轨道最多只能滑到最后一屏，别把空白露出来 */
      const maxTrack = Math.max(0, (TOTAL - (MAXSLOT + 1)) * cellW.value);
      trackX.value = Math.max(0, Math.min(maxTrack, (idx - SLOT) * cellW.value));
      pos.value = idx;
      layout(idx);
      setTimeout(() => {
        suppress = false;
      }, 300);
    });
  }

  /* resize：重新测量并锚定 */
  function resize(calEl, scrollEl) {
    measure(calEl);
    reanchor(scrollEl);
    layout(pos.value);
  }

  /* ============================================================
     导航同源玻璃：dlist 是不透明全屏紫渐变，会盖住 canvas 上画的
     底栏玻璃。这里按 #tabs 的真实位置，用 evenodd 圆角 path 挖洞，
     让 canvas 玻璃（与其他页同一套渲染）透出来，而不是另起 CSS 磨砂。
     几何按实际 rect 动态计算，设备尺寸变化时重新调用即可对齐。
     挖洞要比 #tabs 再外扩 MASK_PAD：shader 里玻璃边缘的抗锯齿与
     发丝光会溢出 rect 外约 3px（d>3 才不绘制），不扩的话这圈柔和
     过渡会被硬切成紫边，看着像 bug。
     ============================================================ */
  const MASK_PAD = 6;   // 略大于 shader 的 3px 外溢，保证边缘完整
  const GLASS_R = 28;   // 与 canvas 里 tabs 的 SDF 圆角一致

  function applyNavMask(dlistEl) {
    if (!dlistEl) return;
    const tabs = document.getElementById('tabs');
    if (!tabs) return;
    const W = dlistEl.clientWidth;
    const H = dlistEl.clientHeight;
    const dRect = dlistEl.getBoundingClientRect();
    const tRect = tabs.getBoundingClientRect();
    // 胶囊相对 dlist 坐标，再均匀外扩；圆角随外扩一起加大，保持等距
    const x = tRect.left - dRect.left - MASK_PAD;
    const y = tRect.top - dRect.top - MASK_PAD;
    const w = tRect.width + MASK_PAD * 2;
    const h = tRect.height + MASK_PAD * 2;
    const r = GLASS_R + MASK_PAD;
    const x2 = x + w;
    const y2 = y + h;
    // 外层全屏矩形 + 内层圆角矩形，evenodd 让内层变透明
    const outer = `M0,0 L${W},0 L${W},${H} L0,${H} Z`;
    const hole =
      `M${x},${y} L${x2 - r},${y} ` +
      `A${r},${r} 0 0 1 ${x2},${y + r} L${x2},${y2 - r} ` +
      `A${r},${r} 0 0 1 ${x2 - r},${y2} L${x + r},${y2} ` +
      `A${r},${r} 0 0 1 ${x},${y2 - r} L${x},${y + r} ` +
      `A${r},${r} 0 0 1 ${x + r},${y} Z`;
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">` +
      `<path fill-rule="evenodd" fill="white" d="${outer} ${hole}"/></svg>`;
    const url = 'data:image/svg+xml,' + encodeURIComponent(svg);
    // 单独属性设置：该 WebView 解析带 /size 的 mask 简写会失败
    dlistEl.style.webkitMaskImage = `url('${url}')`;
    dlistEl.style.webkitMaskSize = '100% 100%';
    dlistEl.style.webkitMaskRepeat = 'no-repeat';
  }

  return {
    // 数据
    TODAY, DAYS, DIARY, groups, phClass,
    loadDiaries, loading, error, diaryNames, diaryInitials,
    // 子页面
    subPage, selectedKey, detail, openDetail, openNew, backToList, addDiary, updateNote,
    // 日历状态
    cellW, pos, trackX,
    trackWidth, trackTransform, pillLeft, pillNum, pillWd, nearestIdx,
    // 测量与动画
    measure, reanchor, init, resize,
    applyNavMask,
    onListScroll, onTrackClick, animateToIdx,
    // 月历
    monthOpen, monthTitle, monthCells,
    openMonth, closeMonth, monthPrev, monthNext, pickMonth,
    canNext,
    // 年月面板
    ymOpen, ymYear, ymTitle, ymMonths, openYm, closeYm, pickYm,
    mViewYear, mViewMonth,
  };
}
