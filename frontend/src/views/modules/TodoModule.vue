<template>
<div class="tpage">
  <!-- 深青主卡：件数 + 进度环 -->
  <article class="t-hero">
    <span class="t-hero__shine" aria-hidden="true"></span>
    <span class="t-hero__diamond" aria-hidden="true"></span>

    <div class="t-hero__l">
      <span class="t-eb">一起做的事</span>
      <h2>{{ !items.length ? '先添一件' : (pendingCount ? pendingCount + ' 件待做' : '都做完了') }}</h2>
      <p v-if="!items.length">清单还是空的，从一件小事开始</p>
      <!-- 大字已经说过「都做完了 / N 件待做」，这一行不再复读同一句，只说进度 -->
      <p v-else-if="pendingCount">{{ doneCount }} / {{ items.length }} 件做完了</p>
      <p v-else>共 {{ items.length }} 件</p>
    </div>

    <div class="t-ring">
      <svg viewBox="0 0 96 96" aria-hidden="true">
        <circle class="t-rg-track" cx="48" cy="48" r="38" />
        <circle
          class="t-rg-fill" cx="48" cy="48" r="38"
          :style="{ strokeDashoffset: ringOffset, opacity: pct ? 1 : 0 }"
        />
      </svg>
      <div class="t-ring__in"><b>{{ pct }}</b><em>%</em></div>
    </div>
  </article>

  <!-- 完成时后端给的那张纪念卡 -->
  <transition name="mem">
    <article v-if="memory" class="t-mem">
      <span class="t-mem__spark" aria-hidden="true"></span>
      <span class="t-eb t-eb--gold">又完成了一件</span>
      <h4>{{ memory.title }}</h4>
      <p>{{ memory.note }}</p>
      <div class="t-mem__foot">
        <span>{{ fmtWhen(memory.completed_at) }}</span>
        <button @click="memory = null">收下</button>
      </div>
    </article>
  </transition>

  <!-- 筛选 -->
  <div class="t-tabs">
    <button
      v-for="f in STATUS" :key="f.key"
      class="t-tab" :class="{ on: status === f.key }"
      @click="status = f.key"
    >{{ f.label }}<em>{{ statusCount(f.key) }}</em></button>
  </div>

  <!-- 新建 / 编辑 -->
  <button v-if="!form.open" class="t-add" @click="openForm()">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.1" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
    添一件一起做的事
  </button>

  <form v-else class="t-form" @submit.prevent="submit">
    <div class="t-form__head">
      <h4>{{ form.id ? '改一下' : '新的清单' }}</h4>
      <button type="button" class="t-x" @click="closeForm" aria-label="关闭">×</button>
    </div>

    <label class="t-field">
      <span>要做什么</span>
      <input class="t-input" v-model="form.title" maxlength="200" placeholder="一起去看海 / 把阳台种满薄荷…" />
    </label>

    <div class="t-field">
      <span>归在哪一类</span>
      <div class="t-cats">
        <button
          v-for="c in catOptions" :key="c" type="button"
          class="t-cat" :class="{ on: form.category === c && !customOpen }"
          @click="pickCat(c)"
        >{{ c }}</button>
        <button
          v-if="!customOpen" type="button"
          class="t-cat t-cat--add"
          @click="openCustom"
        >＋ 自定义</button>
        <input
          v-else
          ref="customInput"
          class="t-cat-in"
          v-model="customCat"
          maxlength="50"
          placeholder="写一类新的，比如「周末」"
        />
      </div>
    </div>

    <label class="t-field">
      <span>备注（可以不写）</span>
      <textarea class="t-area" v-model="form.description" maxlength="1000" placeholder="想做的时候是什么样子…"></textarea>
    </label>

    <div class="t-form__btns">
      <button type="button" class="t-btn t-btn--ghost" @click="closeForm">取消</button>
      <button type="submit" class="t-btn" :disabled="!canSubmit || saving">{{ saving ? '保存中…' : '存下' }}</button>
    </div>

    <button v-if="form.id" type="button" class="t-del" @click="askDelete(form.id)">删掉这件事</button>
    <p v-if="formError" class="t-warn">{{ formError }}</p>
  </form>

  <p v-if="error" class="t-warn t-warn--box">{{ error }}</p>

  <!-- 列表 -->
  <div v-if="loading" class="t-card t-loading"><i></i><i></i><i></i></div>

  <div v-else-if="!groups.length" class="t-card t-empty">
    <span class="t-empty__ico" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6h11M9 12h11M9 18h11"/><path d="m4 6 1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2"/></svg>
    </span>
    <!-- 空态只说自己这一格的事：上面大卡已经写了「都做完了」、按钮也已经写了「添一件」，
         这里再复读一遍就成了同一句话出现三次 -->
    <b>{{ status === 'completed' ? '还没有做完的事' : (items.length ? '没有待办了' : '这里空着') }}</b>
    <span>{{ status === 'completed'
      ? '做完一件，就会在这里留下痕迹'
      : (items.length ? '已经做完的都收在「已完成」里' : '加一件小事，一起慢慢做') }}</span>
  </div>

  <template v-else>
    <section v-for="g in groups" :key="g.category" class="t-group">
      <div class="t-sec">
        <h4>{{ g.category }}</h4>
        <p>{{ g.items.length }} 件</p>
      </div>

      <div class="t-rows">
        <article
          v-for="it in g.items" :key="it.id"
          class="t-row"
          :class="{ done: it.status === 'completed' }"
        >
          <button
            class="t-check"
            :class="{ on: it.status === 'completed', burst: burstId === it.id }"
            @click="toggle(it)"
            :aria-label="it.status === 'completed' ? '已完成' : '完成'"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.6 10 17.4 19 7.6" /></svg>
            <span v-if="burstId === it.id" class="t-dots">
              <i v-for="d in sparks" :key="d.k" :style="{ '--dx': d.x + 'px', '--dy': d.y + 'px', background: d.c }"></i>
            </span>
          </button>

          <div class="t-row__body">
            <div class="t-row__head">
              <h4>{{ it.title }}</h4>
            </div>
            <p v-if="it.description" class="t-desc">{{ it.description }}</p>
            <div class="t-row__foot">
              <span class="t-tag">{{ it.category }}</span>
              <span v-if="it.status === 'completed' && it.completed_at" class="t-when">{{ fmtWhen(it.completed_at) }} 做完</span>
            </div>

            <div v-if="confirmId === it.id" class="t-confirm">
              <span>删掉「{{ it.title }}」？</span>
              <button @click="confirmId = null">算了</button>
              <button class="t-danger" :disabled="deleting" @click="doDelete(it)">{{ deleting ? '删除中…' : '删掉' }}</button>
            </div>
          </div>

          <div class="t-acts">
            <button class="t-act" @click="openForm(it)" aria-label="编辑">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4l10-10-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/></svg>
            </button>
            <button class="t-act" @click="askDelete(it.id)" aria-label="删除">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 7h14M9 7V5h6v2m-8 0 1 13h8l1-13"/></svg>
            </button>
          </div>
        </article>
      </div>
    </section>
  </template>

  <section v-if="donePreview.length" class="t-group">
    <div class="t-sec">
      <h4>已经做完的</h4>
      <p>{{ doneCount }} 件</p>
    </div>
    <div class="t-done-row">
      <div v-for="it in donePreview" :key="it.id" class="t-done-card">
        <span class="t-done-check">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.6 10 17.4 19 7.6"/></svg>
        </span>
        <b>{{ it.title }}</b>
        <small>{{ fmtWhen(it.completed_at) }}</small>
      </div>
    </div>
  </section>

  <p class="t-note">
    完成后会得到一张纪念卡；清单不催人，想什么时候做都行。
  </p>
</div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { listTodos, createTodo, updateTodo, completeTodo, deleteTodo } from '../../api/todos.js';
import { tap } from '../../native.js';

const DEMO = new URLSearchParams(location.search).has('demo');

const status = ref('pending');
const items = ref([]);
const loading = ref(!DEMO);
const error = ref('');
const saving = ref(false);
const confirmId = ref(null);
const deleting = ref(false);
const memory = ref(null);
const burstId = ref(null);
const sparks = ref([]);

const STATUS = [
  { key: 'pending', label: '待办' },
  { key: 'completed', label: '已完成' },
  { key: 'all', label: '全部' },
];

const CATEGORIES = ['旅行', '居家', '日常', '美食', '纪念'];

/* ---------- 派生 ---------- */
/* 「全部」里也只列没做的：做完的整块退到底部「已经做完的」，不在分组里重复 */
const listItems = computed(() => {
  if (status.value === 'completed') {
    return items.value
      .filter(i => i.status === 'completed')
      .slice()
      .sort((a, b) => new Date(b.completed_at || 0) - new Date(a.completed_at || 0));
  }
  return items.value.filter(i => i.status !== 'completed');
});

const groups = computed(() => {
  const map = new Map();
  for (const it of listItems.value) {
    if (!map.has(it.category)) map.set(it.category, []);
    map.get(it.category).push(it);
  }
  return [...map.entries()].map(([category, list]) => ({ category, items: list }));
});

/* 自己写过的类别以后也变成一枚快捷 chip，不用每次再打一遍 */
const catOptions = computed(() => {
  const seen = new Set(CATEGORIES);
  for (const it of items.value) if (it.category) seen.add(it.category);
  return [...seen];
});

const pendingCount = computed(() => items.value.filter(i => i.status === 'pending').length);
const doneCount = computed(() => items.value.filter(i => i.status === 'completed').length);
const donePreview = computed(() => (
  /* 「待办」只看没做的，别把做完的又摊回来；「全部」才给一条完成记录 */
  status.value === 'completed' || status.value === 'pending'
    ? []
    : items.value
      .filter(i => i.status === 'completed')
      .slice()
      .sort((a, b) => new Date(b.completed_at || 0) - new Date(a.completed_at || 0))
      .slice(0, 6)
));
const pct = computed(() => {
  const total = items.value.length;
  return total ? Math.round((doneCount.value / total) * 100) : 0;
});
const R = 38;
const ringOffset = computed(() => 2 * Math.PI * R * (1 - pct.value / 100));

function statusCount(key){
  return key === 'all' ? items.value.length : items.value.filter(i => i.status === key).length;
}

function fmtWhen(s){
  if (!s) return '';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return '';
  const now = new Date();
  const sameDay = d.getFullYear() === now.getFullYear()
    && d.getMonth() === now.getMonth()
    && d.getDate() === now.getDate();
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  return sameDay ? `今天 ${hm}` : `${d.getMonth() + 1}.${d.getDate()}`;
}

/* ---------- 完成 ---------- */
function makeSparks(){
  const colors = ['#F6DF5D', '#7FC9C6', '#FFFFFF', '#527676', '#CFE9E7', '#F6A96B'];
  sparks.value = Array.from({ length: 9 }, (_, i) => {
    const a = (i / 9) * Math.PI * 2 + Math.random() * .4;
    const d = 16 + Math.random() * 18;
    return {
      k: i,
      x: Math.round(Math.cos(a) * d),
      y: Math.round(Math.sin(a) * d),
      c: colors[i % colors.length],
    };
  });
}

/* 数据变了：通知「我」页那几张卡重拉 */
function notifyData(){
  window.dispatchEvent(new Event('cove:data'));
}

async function toggle(it){
  if (it.status === 'completed') return;   // 后端只有 complete，没有反悔接口
  tap();
  burstId.value = it.id;
  makeSparks();
  setTimeout(() => { burstId.value = null; }, 700);

  if (DEMO) {
    it.status = 'completed';
    it.completed_at = new Date().toISOString();
    memory.value = { title: it.title, note: '这件小事，被两个人都记下了。', completed_at: it.completed_at };
    return;
  }

  try {
    const res = await completeTodo(it.id);
    const idx = items.value.findIndex(x => x.id === it.id);
    if (idx >= 0) items.value[idx] = res.todo;
    memory.value = res.card;
    notifyData();
  } catch (e) {
    error.value = e.message || '完成失败';
  }
}

/* ---------- 表单 ---------- */
const form = ref({ open: false, id: null, title: '', category: '日常', description: '' });
const formError = ref('');
const customCat = ref('');            // 自定义分类：和 form.category 双向对齐
const customOpen = ref(false);        // 点「自定义」才把输入框放出来
const customInput = ref(null);
const canSubmit = computed(() => {
  if (!form.value.title.trim()) return false;
  /* 点了「自定义」就必须真写一类，不能拿原来那枚 chip 蒙过去 */
  if (customOpen.value && !customCat.value.trim()) return false;
  return !!form.value.category.trim();
});
watch(customCat, (v) => {
  const t = (v || '').trim();
  if (t) form.value.category = t;
});
function pickCat(c){
  tap();
  form.value.category = c;
  customCat.value = '';
  customOpen.value = false;
}
function openCustom(){
  tap();
  customOpen.value = true;
  customCat.value = '';
  nextTick(() => customInput.value?.focus());
}

function openForm(it){
  tap();
  formError.value = '';
  form.value = it
    ? { open: true, id: it.id, title: it.title, category: it.category, description: it.description || '' }
    : { open: true, id: null, title: '', category: '日常', description: '' };
  const known = !!form.value.category && catOptions.value.includes(form.value.category);
  customCat.value = known ? '' : (form.value.category || '');
  customOpen.value = !known;
}
function closeForm(){ form.value = { ...form.value, open: false }; }

async function submit(){
  if (!canSubmit.value || saving.value) return;
  saving.value = true; formError.value = '';
  const body = {
    title: form.value.title.trim(),
    category: form.value.category.trim(),
    description: form.value.description.trim() || null,
  };
  try {
    if (form.value.id) await updateTodo(form.value.id, body);
    else await createTodo({ ...body, type: 'shared' });
    closeForm();
    await load();
    status.value = 'pending';
    notifyData();
  } catch (e) {
    formError.value = e.message || '保存失败';
  } finally {
    saving.value = false;
  }
}

function askDelete(id){ confirmId.value = id; }
async function doDelete(it){
  deleting.value = true;
  try {
    await deleteTodo(it.id);
    items.value = items.value.filter(x => x.id !== it.id);
    confirmId.value = null;
    if (form.value.id === it.id) closeForm();
    notifyData();
  } catch (e) {
    error.value = e.message || '删除失败';
  } finally {
    deleting.value = false;
  }
}

/* ---------- 取数（这一页只做「一起做」的清单） ---------- */
function seedDemo(){
  items.value = [
    { id: 1, type: 'shared', category: '旅行', title: '一起去看海', description: '挑一个不用赶路的周末，住到海边，看一次日出。', status: 'pending', completed_at: null },
    { id: 2, type: 'shared', category: '旅行', title: '坐一次夜里的火车', description: null, status: 'pending', completed_at: null },
    { id: 3, type: 'shared', category: '居家', title: '把阳台种满薄荷', description: '买六个陶盆，窗台那一排。', status: 'pending', completed_at: null },
    { id: 4, type: 'shared', category: '居家', title: '换一盏暖光的落地灯', description: null, status: 'completed', completed_at: '2026-10-21T12:20:00' },
    { id: 5, type: 'shared', category: '美食', title: '学会做那道番茄牛腩', description: '按那个方子，失败两次也算数。', status: 'completed', completed_at: '2026-10-02T19:10:00' },
  ];
  loading.value = false;
}

async function load(){
  if (DEMO) { seedDemo(); return; }
  loading.value = true; error.value = '';
  try {
    items.value = await listTodos({ type: 'shared' });
  } catch (e) {
    error.value = e.message || '加载失败';
    items.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
  const q = new URLSearchParams(location.search);
  // 走查用：?form=1 直接把新建表单铺开，?mem=1 预置一张纪念卡
  if (q.has('form')) openForm();
  if (q.has('mem')) {
    memory.value = { title: '换一盏暖光的落地灯', note: '这件小事，被两个人都记下了。', completed_at: new Date().toISOString() };
  }
});
</script>

<style scoped>
/* ============================================================
   共同清单 · 青绿白卡
   取自共享单车稿的配色（浅青底 / 深青卡 / 黄强调 / 大圆角白卡），
   版式按清单内容重排
   ============================================================ */
.tpage{
  --ink:#22403E;
  --ink2:#5E7C7A;
  --ink3:#93ACAB;
  --teal:#527676;
  --teal-deep:#436463;
  --mint:#A9D8D8;
  --mint-soft:#EAF4F3;
  --mint-line:#DCEBE9;
  --gold:#F6DF5D;
  --gold-deep:#E4C93F;
  --white:#FFFFFF;
  padding-top:2px;
  display:flex;
  flex-direction:column;
  gap:12px;
  color:var(--ink);
}

/* ---------- 主卡 ---------- */
.t-hero{
  position:relative;
  display:flex;
  align-items:center;
  gap:14px;
  padding:18px 18px 18px 20px;
  border-radius:26px;
  overflow:hidden;
  background:linear-gradient(148deg, #5C8281 0%, #527676 46%, #466766 100%);
  box-shadow:0 22px 34px -26px rgba(36, 70, 70, .95);
}
.t-hero__shine{
  position:absolute; right:-40px; top:-70px; width:200px; height:200px; border-radius:50%;
  background:radial-gradient(circle at 50% 50%, rgba(255,255,255,.18), rgba(255,255,255,0) 66%);
  pointer-events:none;
}
/* 稿里左上角那块白色菱形切角 */
.t-hero__diamond{
  position:absolute; left:-26px; top:-26px; width:72px; height:72px;
  transform:rotate(45deg);
  background:rgba(255,255,255,.06);
  pointer-events:none;
}
.t-hero__l{ flex:1; min-width:0; position:relative; z-index:1; }
.t-eb{
  display:block;
  font-size:10.5px; font-weight:700; letter-spacing:.16em;
  color:rgba(255,255,255,.62); text-transform:uppercase;
}
.t-eb--gold{ color:var(--gold-deep); }
.t-hero h2{
  margin:8px 0 0;
  font-size:24px; font-weight:860; letter-spacing:-.02em;
  color:#FFFFFF;
}
.t-hero p{
  margin:6px 0 0;
  font-size:10.5px; letter-spacing:.01em;
  color:rgba(255,255,255,.56);
}

.t-ring{ position:relative; width:84px; height:84px; flex:0 0 auto; z-index:1; }
.t-ring svg{ position:absolute; inset:0; width:100%; height:100%; }
.t-rg-track{ fill:none; stroke:rgba(255,255,255,.22); stroke-width:5.5; }
.t-rg-fill{
  fill:none; stroke:var(--gold); stroke-width:5.5; stroke-linecap:round;
  stroke-dasharray:238.8;
  transform:rotate(-90deg); transform-origin:50% 50%;
  transition:stroke-dashoffset 1s var(--out);
  filter:drop-shadow(0 2px 6px rgba(246,223,93,.55));
}
.t-ring__in{
  position:absolute; inset:0; display:flex; align-items:baseline; justify-content:center;
  padding-top:30px;
}
.t-ring__in b{ font-size:20px; font-weight:850; color:#FFFFFF; font-variant-numeric:tabular-nums; }
.t-ring__in em{ font-size:10px; font-style:normal; margin-left:1px; color:rgba(255,255,255,.66); }

/* ---------- 纪念卡 ---------- */
.t-mem{
  position:relative; padding:16px 18px 14px; border-radius:24px; overflow:hidden;
  background:linear-gradient(150deg,#FFFFFF,#F6FBFA 60%,#FFF9DE);
  box-shadow:0 18px 34px -26px rgba(30, 70, 70, .55), inset 0 0 0 1px rgba(255,255,255,.9);
}
.t-mem__spark{
  position:absolute; right:-34px; top:-34px; width:130px; height:130px; border-radius:50%;
  background:radial-gradient(circle at 40% 40%, rgba(246,223,93,.55), rgba(246,223,93,0) 68%);
  animation:glow 4s ease-in-out infinite;
}
@keyframes glow{ 0%,100%{ opacity:.45; transform:scale(1); } 50%{ opacity:.85; transform:scale(1.1); } }
.t-mem h4{ margin:8px 0 0; font-size:16.5px; font-weight:820; color:var(--ink); letter-spacing:-.01em; }
.t-mem p{ margin:7px 0 0; font-size:11.5px; line-height:1.7; color:var(--ink2); }
.t-mem__foot{ display:flex; align-items:center; justify-content:space-between; margin-top:12px; }
.t-mem__foot span{ font-size:9.5px; color:var(--ink3); }
.t-mem__foot button{
  height:30px; padding:0 15px; border-radius:10px; cursor:pointer;
  font-size:11.5px; font-weight:780; color:#2A3B3B;
  background:var(--gold);
  box-shadow:0 10px 18px -12px rgba(220,200,60,.9);
}
.mem-enter-active{ animation:memIn .72s cubic-bezier(.34,1.56,.64,1) both; }
.mem-leave-active{ animation:memOut .3s ease both; }
@keyframes memIn{
  0%{ opacity:0; transform:translateY(-14px) rotateX(-24deg) scale(.94); }
  100%{ opacity:1; transform:none; }
}
@keyframes memOut{ to{ opacity:0; transform:translateY(-10px) scale(.97); } }

/* ---------- 筛选胶囊 ---------- */
.t-tabs{
  display:flex; gap:4px; padding:4px;
  border-radius:999px;
  background:rgba(255,255,255,.78);
  box-shadow:0 14px 26px -22px rgba(30,70,70,.7), inset 0 0 0 1px rgba(255,255,255,.9);
}
.t-tab{
  flex:1; height:38px; border-radius:999px; cursor:pointer;
  display:flex; align-items:center; justify-content:center; gap:5px;
  font-size:12.5px; font-weight:750; color:var(--ink2);
  background:transparent;
  transition:background .22s var(--out), color .22s var(--out), transform .2s var(--spring);
}
.t-tab em{
  font-style:normal; font-size:9.5px; font-weight:700;
  padding:1px 5px; border-radius:999px;
  background:rgba(82,118,118,.10); color:var(--ink2);
  font-variant-numeric:tabular-nums;
}
.t-tab.on{ background:var(--teal); color:#FFFFFF; box-shadow:0 10px 18px -14px rgba(52,90,90,.95); }
.t-tab.on em{ background:rgba(255,255,255,.18); color:#FFFFFF; }
.t-tab:active{ transform:scale(.98); }

/* ---------- 添加 ---------- */
.t-add{
  display:flex; align-items:center; justify-content:center; gap:7px;
  width:100%; height:50px; border-radius:18px; cursor:pointer;
  color:#2A3B3B; font-size:13px; font-weight:820; letter-spacing:.01em;
  background:var(--gold);
  box-shadow:0 18px 28px -20px rgba(210,190,50,.95), inset 0 -2px 0 rgba(0,0,0,.05);
  transition:transform .2s var(--spring), background .2s var(--out);
}
.t-add svg{ flex:0 0 auto; }
.t-add:active{ transform:scale(.975); background:var(--gold-deep); }

/* ---------- 表单 ---------- */
.t-form{
  padding:16px; border-radius:24px;
  background:#FFFFFF;
  box-shadow:0 20px 36px -28px rgba(30,70,70,.6), inset 0 0 0 1px rgba(255,255,255,.9);
  animation:pop .5s var(--spring) both;
}
@keyframes pop{ from{ opacity:0; transform:translateY(-8px) scale(.985); } to{ opacity:1; transform:none; } }
.t-form__head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.t-form__head h4{ margin:0; font-size:14.5px; font-weight:820; color:var(--ink); }
.t-x{ font-size:19px; line-height:1; color:var(--ink3); padding:2px 6px; cursor:pointer; background:none; }
.t-field{ display:flex; flex-direction:column; gap:7px; margin-bottom:13px; }
.t-field > span{ font-size:11px; font-weight:700; letter-spacing:.06em; color:var(--ink3); text-transform:uppercase; }
.t-input, .t-area{
  width:100%; font:inherit; font-size:13px; color:var(--ink);
  padding:11px 13px; border-radius:14px;
  background:#FBFDFD;
  border:1.5px solid var(--mint-line);
  transition:border-color .18s var(--out), box-shadow .18s var(--out);
}
.t-area{ min-height:78px; resize:vertical; line-height:1.6; }
.t-input:focus, .t-area:focus{ outline:none; border-color:#9CC7C3; box-shadow:0 0 0 4px rgba(169,216,216,.28); }
.t-cats{ display:flex; gap:7px; flex-wrap:wrap; }
.t-cat{
  height:31px; padding:0 13px; border-radius:999px; cursor:pointer;
  font-size:11.5px; font-weight:720; color:var(--ink2);
  background:var(--mint-soft);
  transition:background .2s var(--out), color .2s var(--out), transform .2s var(--spring);
}
.t-cat.on{ background:var(--teal); color:#fff; }
.t-cat:active{ transform:scale(.97); }
/* 「自定义」做成和类别同一排的一枚 chip，点开才变输入框 */
.t-cat--add{
  color:#4E7A79; background:transparent;
  box-shadow:inset 0 0 0 1.5px var(--mint-line);
}
.t-cat--add:active{ transform:scale(.97); }
.t-cat-in{
  height:31px; width:100%; margin-top:1px; padding:0 13px; border-radius:999px;
  font:inherit; font-size:11.5px;
  color:var(--ink); background:#FBFDFD; border:1.5px solid var(--mint-line);
}
.t-cat-in:focus{ outline:none; border-color:#9CC7C3; }
.t-form__btns{ display:flex; gap:9px; margin-top:4px; }
.t-btn{
  flex:1; height:44px; border-radius:14px; cursor:pointer;
  font-size:13px; font-weight:800; color:#2A3B3B; background:var(--gold);
  transition:transform .18s var(--spring), opacity .2s;
}
.t-btn:active{ transform:scale(.98); }
.t-btn:disabled{ opacity:.5; cursor:default; transform:none; }
.t-btn--ghost{
  color:var(--ink2); background:var(--mint-soft);
  box-shadow:inset 0 0 0 1px rgba(82,118,118,.10);
}
.t-del{
  width:100%; margin-top:11px; height:38px; border-radius:12px; cursor:pointer;
  font-size:11.5px; font-weight:720; color:#B26A5C;
  background:rgba(210,120,100,.08);
}
.t-warn{ margin:9px 0 0; font-size:11px; color:#B26A5C; }
.t-warn--box{
  margin:0; padding:11px 14px; border-radius:14px;
  background:rgba(210,120,100,.10); color:#A85B4D;
}

/* ---------- 列表 ---------- */
.t-card{
  padding:22px 18px; border-radius:22px; background:#FFFFFF;
  box-shadow:0 16px 30px -26px rgba(30,70,70,.55);
}
.t-loading{ display:flex; flex-direction:column; gap:10px; }
.t-loading i{
  display:block; height:14px; border-radius:8px;
  background:linear-gradient(90deg,#EEF6F5,#E3EFEE,#EEF6F5);
  background-size:200% 100%;
  animation:shim 1.4s linear infinite;
}
.t-loading i:nth-child(2){ width:72%; }
.t-loading i:nth-child(3){ width:48%; }
@keyframes shim{ from{ background-position:0 0; } to{ background-position:200% 0; } }

.t-empty{ display:flex; flex-direction:column; align-items:center; gap:8px; text-align:center; padding:38px 18px 40px; }
.t-empty__ico{
  display:grid; place-items:center; width:48px; height:48px; margin-bottom:4px;
  border-radius:50%; background:var(--mint-soft); color:#5D8A87;
}
.t-empty b{ font-size:14px; font-weight:800; color:var(--ink); }
.t-empty > span:last-child{ font-size:11.5px; color:var(--ink3); }

.t-group{ display:flex; flex-direction:column; gap:9px; }
.t-sec{
  display:flex; align-items:center; justify-content:space-between;
  padding:2px 4px 0;
}
.t-sec h4{
  margin:0; font-size:11.5px; font-weight:800; letter-spacing:.13em;
  text-transform:uppercase; color:#2C5351;
}
.t-sec p{ margin:0; font-size:10px; color:#4A7573; font-variant-numeric:tabular-nums; }

.t-rows{ display:flex; flex-direction:column; gap:9px; }
.t-row{
  display:flex; align-items:flex-start; gap:12px;
  padding:14px 14px 13px 15px; border-radius:22px;
  background:#FFFFFF;
  box-shadow:0 16px 30px -26px rgba(30,70,70,.55), inset 0 0 0 1px rgba(255,255,255,.9);
  transition:transform .22s var(--spring), background .24s var(--out);
}
.t-row.done{ background:#F7FBFA; }
.t-row.done h4{ color:var(--ink3); text-decoration:line-through; text-decoration-thickness:1px; }
.t-row.done .t-tag{ opacity:.7; }

.t-check{
  position:relative; flex:0 0 auto; width:27px; height:27px; margin-top:2px;
  border-radius:50%; cursor:pointer;
  background:#FFFFFF; box-shadow:inset 0 0 0 1.6px #B9D6D3;
  transition:background .2s var(--out), box-shadow .2s var(--out), transform .2s var(--spring);
}
.t-check svg{
  position:absolute; inset:0; width:100%; height:100%; padding:5px;
  fill:none; stroke:#FFFFFF; stroke-width:2.4; stroke-linecap:round; stroke-linejoin:round;
  opacity:0; transition:opacity .18s var(--out);
}
.t-check.on{ background:var(--teal); box-shadow:0 8px 16px -12px rgba(50,90,90,.95); }
.t-check.on svg{ opacity:1; }
.t-check:active{ transform:scale(.9); }
.t-check.burst{ animation:burst .6s cubic-bezier(.34,1.56,.64,1); }
@keyframes burst{
  0%{ transform:scale(1); }
  36%{ transform:scale(1.24); }
  100%{ transform:scale(1); }
}
.t-dots{ position:absolute; left:50%; top:50%; pointer-events:none; }
.t-dots i{
  position:absolute; width:5px; height:5px; border-radius:50%;
  animation:fly .62s cubic-bezier(.22,.9,.3,1) forwards;
}
@keyframes fly{
  from{ opacity:1; transform:translate(0,0) scale(1); }
  to{ opacity:0; transform:translate(var(--dx),var(--dy)) scale(.4); }
}

.t-row__body{ flex:1; min-width:0; }
.t-row__head h4{
  margin:0; font-size:14.5px; font-weight:780; letter-spacing:-.01em; color:var(--ink);
  line-height:1.35;
}
.t-desc{
  margin:5px 0 0; font-size:11.5px; line-height:1.6; color:var(--ink2);
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.t-row__foot{ display:flex; align-items:center; gap:8px; margin-top:9px; flex-wrap:wrap; }
.t-tag{
  font-size:9.5px; font-weight:700; letter-spacing:.04em;
  padding:3px 9px; border-radius:999px;
  background:var(--mint-soft); color:#5D8A87;
}
.t-when{ font-size:9.5px; color:var(--ink3); }

.t-confirm{
  display:flex; align-items:center; gap:9px; flex-wrap:wrap;
  margin-top:11px; padding:10px 12px; border-radius:14px;
  background:rgba(210,120,100,.08);
}
.t-confirm span{ flex:1 1 100%; font-size:11px; color:#A85B4D; }
.t-confirm button{
  height:28px; padding:0 12px; border-radius:9px; cursor:pointer;
  font-size:11px; font-weight:720; color:var(--ink2); background:#FFFFFF;
}
.t-danger{ color:#B2554A !important; background:rgba(210,120,100,.16) !important; }
.t-danger:disabled{ opacity:.55; }

.t-acts{ display:flex; flex-direction:column; gap:7px; flex:0 0 auto; }
.t-act{
  width:30px; height:30px; border-radius:50%; cursor:pointer;
  display:grid; place-items:center;
  color:#6E8F8D; background:var(--mint-soft);
  transition:background .18s var(--out), color .18s var(--out), transform .18s var(--spring);
}
.t-act:active{ transform:scale(.94); background:#DFEDEC; }

/* 已完成横滑小卡 */
.t-done-row{
  display:flex; gap:9px; overflow-x:auto; padding:2px 2px 4px;
  scrollbar-width:none; -webkit-overflow-scrolling:touch;
}
.t-done-row::-webkit-scrollbar{ display:none; }
.t-done-card{
  flex:0 0 auto; min-width:132px; max-width:172px;
  padding:13px 14px; border-radius:18px;
  background:#FFFFFF;
  box-shadow:0 14px 26px -24px rgba(30,70,70,.5);
}
.t-done-check{
  display:inline-grid; place-items:center; width:20px; height:20px; border-radius:50%;
  background:var(--mint-soft); color:#5D8A87; margin-bottom:7px;
}
.t-done-card b{
  display:block; font-size:12px; font-weight:750; color:var(--ink);
  line-height:1.4; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.t-done-card small{ display:block; margin-top:4px; font-size:9.5px; color:var(--ink3); }

.t-note{
  margin:4px 0 0; padding:0 8px 8px;
  text-align:center; font-size:10.5px; line-height:1.7; color:var(--ink3);
}

@media (prefers-reduced-motion: reduce){
  .t-row, .t-check, .t-act, .t-btn, .t-add{ transition-duration:.01s !important; }
  .t-loading i, .t-mem__spark, .t-dots i{ animation-duration:.01s !important; }
}
</style>
