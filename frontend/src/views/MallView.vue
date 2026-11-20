<template>
<section class="mall" :class="{ on: active }" data-view="mall">
  <StatusBar />

  <!-- 顶部导航（iOS push 风格） -->
  <div class="nav">
    <button class="nav__back" @click="goBack">
      <svg width="11" height="18" viewBox="0 0 11 18" fill="none"><path d="M9.5 1.5L2 9l7.5 7.5" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" /></svg>
      今天
    </button>
    <div class="nav__center">
      <span class="nav__title">商城</span>
      <span class="nav__sub">我们的金币小铺</span>
    </div>
    <button class="nav__right" :class="{ clear: !pendingApplies.length }" @click="openMessages">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M18 9a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /><path d="M10.3 21a2 2 0 0 0 3.4 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></svg>
      <span class="red-dot"></span>
    </button>
  </div>

  <div class="scroll" ref="scrollEl">
    <!-- 金币余额白卡 -->
    <div class="wallet">
      <div class="wallet__top">
        <span class="coin-ic">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 6.5c2.2 0 4 1.1 4 2.6M12 6.5c-2.2 0-4 1.1-4 2.6M12 6.5V5m0 12.5c-2.2 0-4-1.1-4-2.6m4 2.6c2.2 0 4-1.1 4-2.6M12 17.5V19M8.5 9.1c0 1.5 1.6 2.4 3.5 2.4s3.5.9 3.5 2.4-1.6 2.6-3.5 2.6-3.5-1.1-3.5-2.6" stroke="#8a5a12" stroke-width="1.8" stroke-linecap="round" /></svg>
        </span>
        <span class="wallet__label">我的金币</span>
      </div>
      <div class="wallet__balance"><span>{{ balanceDisplay }}</span><small>枚</small></div>
      <div class="wallet__quota">今日还可赠 <b>{{ quotaLeft }}</b> 枚 · 赠送不扣自己余额</div>
      <div class="wallet__actions">
        <button class="wbtn wbtn--give" @click="openSheet('gift')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M20 12v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v8" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" /><path d="M2 7h20v5H2zM12 22V7" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round" /></svg>
          赠送金币
        </button>
        <button class="wbtn wbtn--ask" @click="openRequest">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 17v5M9 20h6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" /><path d="M7 3h10a2 2 0 0 1 2 2v8a5 5 0 0 1-5 5h-4a5 5 0 0 1-5-5V5a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /></svg>
          索要金币
        </button>
      </div>
    </div>

    <!-- 分段 -->
    <div class="mtabs" :class="{ 'on-orders': tab === 'orders' }">
      <span class="mtabs__thumb"></span>
      <button :class="{ on: tab === 'items' }" @click="tab = 'items'">商品</button>
      <button :class="{ on: tab === 'orders' }" @click="tab = 'orders'">
        订单<span v-if="redeemOrders.length" class="badge">{{ redeemOrders.length }}</span>
      </button>
    </div>

    <!-- 商品面板 -->
    <div v-show="tab === 'items'">
      <div class="sec-h">对方上架 · 我可兑换<span class="count">价格为最终认可价</span></div>
      <div class="grid">
        <div v-for="it in buyItems" :key="it.id" class="tile">
          <div class="tile__ic tile__ic--buy">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M20 12v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-8" stroke="#f02a66" stroke-width="1.7" stroke-linecap="round" /><path d="M2 7h20v5H2zM12 22V7" stroke="#f02a66" stroke-width="1.7" stroke-linejoin="round" /><path d="M12 7S10.5 3 7.5 3 5 5.5 5.5 7H12zm0 0s1.5-4 4.5-4S19 5.5 18.5 7H12z" stroke="#f02a66" stroke-width="1.5" stroke-linejoin="round" /></svg>
          </div>
          <div class="tile__title">{{ it.title }}</div>
          <div class="tile__meta">对方上架</div>
          <div class="tile__price">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none"><circle cx="12" cy="12" r="9" fill="url(#coinG)" /><path d="M12 8v8M9.5 10h4a1.8 1.8 0 0 1 0 3.6h-3" stroke="#8a5a12" stroke-width="1.6" stroke-linecap="round" /></svg>
            {{ it.price_coins }}
          </div>
          <button class="buy" :disabled="balance < it.price_coins" @click="openSheet('buy', it)">
            {{ balance < it.price_coins ? '币不足' : '兑换' }}
          </button>
        </div>
        <div v-if="!buyItems.length" class="empty grid-empty">暂无可兑换商品</div>
      </div>

      <div class="sec-h">
        <span>我上架 · 服务提供方</span>
        <button class="add-item" @click="openCreate">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" /></svg>
          上架商品
        </button>
      </div>
      <div class="sec-note">别人买后由我核销 · 上架即可兑换</div>
      <div class="grid">
        <div v-for="it in myGridItems" :key="it.id" class="tile">
          <span class="tile__mineflag">我上架</span>
          <div class="tile__ic tile__ic--mine">
            <svg width="27" height="27" viewBox="0 0 24 24" fill="none"><path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 14.4l-4.8 2.5.9-5.4L4.2 7.7l5.4-.8L12 2z" stroke="#e09617" stroke-width="1.6" stroke-linejoin="round" /></svg>
          </div>
          <div class="tile__title">{{ it.title }}</div>
          <div class="tile__meta">价格 {{ it.price_coins }} 枚</div>
          <div class="tile__price">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none"><circle cx="12" cy="12" r="9" fill="url(#coinG)" /><path d="M12 8v8M9.5 10h4a1.8 1.8 0 0 1 0 3.6h-3" stroke="#8a5a12" stroke-width="1.6" stroke-linecap="round" /></svg>
            {{ it.price_coins }}
          </div>
          <button class="manage" @click="openSheet('manage', it)">管理</button>
        </div>
        <div v-if="!myGridItems.length" class="empty grid-empty">你还没有已上架的商品</div>
      </div>
    </div>

    <!-- 订单面板 -->
    <div v-show="tab === 'orders'">
      <div class="sec-h">待我核销<span class="count">我提供的服务，确认兑现</span></div>
      <div v-for="o in redeemOrders" :key="o.id" class="order">
        <div class="order__top">
          <div>
            <div class="order__title">{{ itemTitle(o.item_id) }}</div>
            <div class="order__who">对方兑换 · {{ fmtTime(o.created_at) }}</div>
          </div>
          <div class="order__price">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none"><circle cx="12" cy="12" r="9" fill="url(#coinG)" /><path d="M12 8v8M9.5 10h4a1.8 1.8 0 0 1 0 3.6h-3" stroke="#8a5a12" stroke-width="1.6" stroke-linecap="round" /></svg>
            {{ o.price }}
          </div>
        </div>
        <div class="order__foot">
          <span class="status-pill st-pending"><span class="dot"></span>待核销</span>
          <button class="redeem" @click="openSheet('redeem', o)">确认核销</button>
        </div>
      </div>
      <div v-if="!redeemOrders.length" class="empty">暂无待核销订单</div>

      <div class="sec-h">待 TA 兑现<span class="count">我已花币，等对方核销</span></div>
      <div v-for="o in waitOrders" :key="o.id" class="order">
        <div class="order__top">
          <div>
            <div class="order__title">{{ itemTitle(o.item_id) }}</div>
            <div class="order__who">{{ fmtTime(o.created_at) }}</div>
          </div>
          <div class="order__price">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none"><circle cx="12" cy="12" r="9" fill="url(#coinG)" /><path d="M12 8v8M9.5 10h4a1.8 1.8 0 0 1 0 3.6h-3" stroke="#8a5a12" stroke-width="1.6" stroke-linecap="round" /></svg>
            {{ o.price }}
          </div>
        </div>
        <div class="order__foot">
          <span class="status-pill st-wait"><span class="dot"></span>待 TA 兑现</span>
          <button class="cancel-btn" @click="openSheet('cancel', o)">取消订单</button>
        </div>
      </div>
      <div v-if="!waitOrders.length" class="empty">没有待兑现的订单</div>

      <div class="sec-h">已完成<span class="count">最近的兑换记录</span></div>
      <div v-for="o in doneOrders" :key="o.id" class="order">
        <div class="order__top">
          <div>
            <div class="order__title">{{ itemTitle(o.item_id) }}</div>
            <div class="order__who">{{ fmtTime(o.completed_at || o.created_at) }}</div>
          </div>
          <div class="order__price">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none"><circle cx="12" cy="12" r="9" fill="url(#coinG)" /><path d="M12 8v8M9.5 10h4a1.8 1.8 0 0 1 0 3.6h-3" stroke="#8a5a12" stroke-width="1.6" stroke-linecap="round" /></svg>
            {{ o.price }}
          </div>
        </div>
        <div class="order__foot">
          <span class="status-pill st-done"><span class="dot"></span>已完成</span>
        </div>
      </div>
      <div v-if="!doneOrders.length" class="empty">暂无已完成记录</div>
    </div>
  </div>

  <!-- 消息中心独立页（push 同源） -->
  <div class="msg-page" :class="{ on: msgPage }">
    <div class="nav">
      <button class="nav__back" @click="closeMessages">
        <svg width="11" height="18" viewBox="0 0 11 18" fill="none"><path d="M9.5 1.5L2 9l7.5 7.5" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" /></svg>
        商城
      </button>
      <div class="nav__center"><span class="nav__title">消息中心</span></div>
      <span class="nav__ph"></span>
    </div>

    <div class="msg-page__scroll">
      <div class="seg" :class="{ 'on-all': msgTab === 'all' }">
        <span class="seg__thumb"></span>
        <button :class="{ on: msgTab === 'todo' }" @click="msgTab = 'todo'">
          待处理<span v-if="pendingApplies.length" class="mini-badge">{{ pendingApplies.length }}</span>
        </button>
        <button :class="{ on: msgTab === 'all' }" @click="msgTab = 'all'">全部消息</button>
      </div>

      <!-- 待处理：等我审批的索要 -->
      <div v-show="msgTab === 'todo'">
        <div v-for="a in pendingApplies" :key="'todo' + a.id" class="msg">
          <div class="msg__top">
            <span class="msg__ic msg__ic--ask">
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none"><path d="M7 3h10a2 2 0 0 1 2 2v8a5 5 0 0 1-5 5h-4a5 5 0 0 1-5-5V5a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /></svg>
            </span>
            <div class="msg__head">
              <div class="msg__title">索要金币</div>
              <div class="msg__who">对方发起 · {{ fmtTime(a.created_at) }}</div>
            </div>
            <span class="msg__amount">{{ a.amount }}</span>
          </div>
          <div class="msg__reason">{{ a.reason }}</div>
          <img v-if="a.evidence_url || a.evidence_key" class="msg__photo" :src="a.evidence_url || fileUrl(a.evidence_key)" alt="证明照片" @click="openReview(a)" />
          <div class="msg__foot">
            <button class="msg__btn msg__btn--ok" @click="openReview(a)">查看并同意</button>
            <button class="msg__btn msg__btn--no" @click="doReject(a)">拒绝</button>
          </div>
        </div>
        <div v-if="!pendingApplies.length" class="empty">没有待处理的消息啦</div>
      </div>

      <!-- 全部消息：我发起的索要 + 赠送记录 -->
      <div v-show="msgTab === 'all'">
        <div v-for="m in allMessages" :key="m.uid" class="msg">
          <div class="msg__top">
            <span class="msg__ic" :class="m.icon === 'ask' ? 'msg__ic--ask' : 'msg__ic--give'">
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none">
                <template v-if="m.icon === 'ask'"><path d="M7 3h10a2 2 0 0 1 2 2v8a5 5 0 0 1-5 5h-4a5 5 0 0 1-5-5V5a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /></template>
                <template v-else><path d="M20 12v8H4v-8M2 7h20v5H2z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /></template>
              </svg>
            </span>
            <div class="msg__head">
              <div class="msg__title">{{ m.title }}</div>
              <div class="msg__who">{{ m.who }} · {{ fmtTime(m.time) }}</div>
            </div>
            <span class="msg__amount">{{ m.amount }}</span>
          </div>
          <div v-if="m.reason" class="msg__reason">{{ m.reason }}</div>
          <img v-if="m.photoUrl" class="msg__photo" :src="m.photoUrl" alt="证明照片" />
          <div class="msg__state-row"><span class="msg__state" :class="m.stateClass">{{ m.stateLabel }}</span></div>
        </div>
        <div v-if="!allMessages.length" class="empty">暂无消息</div>
      </div>
    </div>
  </div>

  <!-- 遮罩 -->
  <div class="mask" :class="{ show: sheet !== null }" @click="closeSheet"></div>

  <!-- 赠送 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'gift' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">赠送金币</div>
    <div class="sheet__sub">金币由系统发行给对方，不扣你的余额</div>
    <div class="custom-amount">
      <span class="coin-ic">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 6.5c2.2 0 4 1.1 4 2.6M12 6.5c-2.2 0-4 1.1-4 2.6M12 6.5V5m0 12.5c-2.2 0-4-1.1-4-2.6m4 2.6c2.2 0 4-1.1 4-2.6M12 17.5V19M8.5 9.1c0 1.5 1.6 2.4 3.5 2.4s3.5.9 3.5 2.4-1.6 2.6-3.5 2.6-3.5-1.1-3.5-2.6" stroke="#8a5a12" stroke-width="1.8" stroke-linecap="round" /></svg>
      </span>
      <input v-model.number="giftAmount" type="number" inputmode="numeric" min="1" max="100000" placeholder="输入数量" />
      <span class="custom-amount__unit">枚</span>
    </div>
    <div class="chips">
      <button v-for="v in [10, 20, 50, 100]" :key="v" class="chip" :class="{ on: giftAmount === v }" @click="giftAmount = v">{{ v }}</button>
    </div>
    <input v-model="giftRemark" class="remark" maxlength="200" placeholder="留句话（可选）…" />
    <button class="sheet__cta" :disabled="busy" @click="doGift">确认赠送</button>
    <div class="hint-line">单日最多赠 500 枚 · 重复提交自动幂等不重复发币</div>
  </div>

  <!-- 索要金币 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'request' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">索要金币</div>
    <div class="sheet__sub">说明你做了什么，对方确认后由系统发币给你</div>

    <label class="field-label">事由</label>
    <input v-model="reqReason" class="field" maxlength="500" placeholder="比如：今天我主动扫地了" />

    <label class="field-label">索要金额</label>
    <div class="custom-amount">
      <span class="coin-ic">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" fill="#fff" opacity=".5" /><path d="M12 8v8M9.5 10h4" stroke="#8a5a12" stroke-width="1.8" stroke-linecap="round" /></svg>
      </span>
      <input v-model.number="reqAmount" type="number" inputmode="numeric" min="1" max="100000" placeholder="输入数量" />
      <span class="custom-amount__unit">枚</span>
    </div>
    <div class="chips">
      <button v-for="v in [10, 20, 50, 100]" :key="v" class="chip" :class="{ on: reqAmount === v }" @click="reqAmount = v">{{ v }}</button>
    </div>

    <label class="field-label">照片证明（可选）</label>
    <div class="photo-upload" @click="pickPhoto">
      <span class="photo-upload__icon">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none"><path d="M4 16l4.5-4.5a2 2 0 0 1 2.8 0L18 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /><rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" stroke-width="1.8" /><circle cx="9" cy="10" r="1.6" stroke="currentColor" stroke-width="1.6" /></svg>
      </span>
      <div class="photo-upload__t">{{ reqUploading ? '正在上传…' : '上传照片证明' }}</div>
      <div class="photo-upload__s">JPEG / PNG / WebP，可拍照，仅对方可见</div>
    </div>
    <input ref="photoInput" type="file" accept="image/*" style="display:none" @change="onPickPhoto" />
    <div v-if="reqPhotoUrl" class="photo-preview show">
      <img :src="reqPhotoUrl" alt="证明照片" />
      <button class="photo-preview__remove" @click.stop="removePhoto">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" /></svg>
      </button>
    </div>

    <button class="sheet__cta sheet__cta--gold" :disabled="busy || reqUploading" @click="doRequest">提交索要</button>
    <div class="hint-line">提交后进入待对方处理；通过后金币才会到账</div>
  </div>

  <!-- 索要审批 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'review' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">索要审批</div>
    <div class="sheet__sub">对方发起的索要</div>
    <img v-if="reviewItem?.evidence_url || reviewItem?.evidence_key" class="review-photo" :src="reviewItem.evidence_url || fileUrl(reviewItem.evidence_key)" alt="证明照片" />
    <div class="field review-reason">{{ reviewItem?.reason }}</div>
    <div class="review-amount-row">
      <span>索要金额</span><b>{{ reviewItem?.amount }} 枚</b>
    </div>
    <label class="field-label">拒绝理由（可选，仅拒绝时生效）</label>
    <input v-model="reviewRejectRemark" class="field" maxlength="200" placeholder="比如：这次先不发哦" />
    <div class="review-actions">
      <button class="sheet__cta review-ok" :disabled="busy" @click="doApprove">同意</button>
      <button class="sheet__cta review-no" :disabled="busy" @click="doReject(reviewItem)">拒绝</button>
    </div>
    <div class="hint-line">同意后系统把金币发行给对方；拒绝不发币并通知对方</div>
  </div>

  <!-- 兑换确认 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'buy' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">确认兑换</div>
    <div class="sheet__sub">金币将被销毁，生成待兑现订单</div>
    <div class="confirm-box">
      <div class="confirm-row"><span>商品</span><b>{{ target?.title }}</b></div>
      <div class="confirm-row"><span>提供方</span><b>对方</b></div>
      <div class="confirm-row"><span>花费</span><b class="gold-text">{{ target ? target.price_coins : '—' }}</b></div>
    </div>
    <button class="sheet__cta" :disabled="busy" @click="doBuy">确认兑换</button>
    <div class="hint-line">兑换后由对方核销，订单才算完成</div>
  </div>

  <!-- 核销确认 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'redeem' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">确认核销</div>
    <div class="sheet__sub">请确认你已经兑现了这项服务</div>
    <div class="confirm-box">
      <div class="confirm-row"><span>商品</span><b>{{ target ? itemTitle(target.item_id) : '—' }}</b></div>
      <div class="confirm-row"><span>兑换人</span><b>对方</b></div>
      <div class="confirm-row"><span>金额</span><b class="gold-text">{{ target?.price ?? '—' }}</b></div>
    </div>
    <button class="sheet__cta" :disabled="busy" @click="doRedeem">确认核销</button>
    <div class="hint-line">核销后订单关闭并通知对方，不可撤销</div>
  </div>

  <!-- 商品管理 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'manage' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">商品管理</div>
    <div class="sheet__sub">管理你上架的这项服务</div>
    <div class="confirm-box">
      <div class="confirm-row"><span>商品</span><b>{{ target?.title }}</b></div>
      <div class="confirm-row"><span>价格</span><b class="gold-text">{{ target ? target.price_coins : '—' }}</b></div>
      <div class="confirm-row"><span>状态</span><b :class="target?.status === 'approved' ? 'green-text' : 'muted-text'">{{ statusText(target?.status) }}</b></div>
    </div>
    <button class="sheet__cta" @click="openEdit">编辑商品</button>
    <button class="sheet__danger" style="margin-top:11px" :disabled="busy || target?.status !== 'approved'" @click="doOffline">
      {{ target?.status === 'approved' ? '下架商品' : '已下架' }}
    </button>
    <div class="hint-line">编辑改价保存后直接生效；下架后对方无法再兑换，已有订单仍需正常核销</div>
  </div>

  <!-- 取消订单确认 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'cancel' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">取消订单</div>
    <div class="sheet__sub">取消后金币将原路退回你的账户</div>
    <div class="confirm-box">
      <div class="confirm-row"><span>商品</span><b>{{ target ? itemTitle(target.item_id) : '—' }}</b></div>
      <div class="confirm-row"><span>退款</span><b class="gold-text">{{ target?.price ?? '—' }}</b></div>
    </div>
    <button class="sheet__danger" :disabled="busy" @click="doCancel">确认取消并退款</button>
    <div class="hint-line">仅待兑现订单可取消；已完成的订单不能取消</div>
  </div>

  <!-- 编辑商品 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'edit' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">编辑商品</div>
    <div class="sheet__sub">保存后直接生效，无需重新审批</div>
    <label class="field-label">商品名称</label>
    <input v-model="editForm.title" class="field" maxlength="100" />
    <label class="field-label">价格（枚）</label>
    <input v-model.number="editForm.price" class="field" type="number" inputmode="numeric" min="1" max="100000" />
    <label class="field-label">商品描述</label>
    <textarea v-model="editForm.desc" class="field field--area" maxlength="1000" rows="3"></textarea>
    <button class="sheet__cta" :disabled="busy" @click="saveEdit">保存修改</button>
    <div class="hint-line">进行中的订单不受影响，保存后按新内容展示</div>
  </div>

  <!-- 上架商品 Sheet -->
  <div class="sheet" :class="{ show: sheet === 'create' }">
    <div class="sheet__grab"></div>
    <div class="sheet__title">上架商品</div>
    <div class="sheet__sub">提交后直接上架，无需对方审批</div>
    <label class="field-label">商品名称</label>
    <input v-model="createForm.title" class="field" maxlength="100" placeholder="比如：今晚我洗碗" />
    <label class="field-label">价格（枚）</label>
    <input v-model.number="createForm.price" class="field" type="number" inputmode="numeric" min="1" max="100000" placeholder="这件商品兑换所需的金币" />
    <label class="field-label">商品描述（可选）</label>
    <textarea v-model="createForm.desc" class="field field--area" maxlength="1000" rows="3" placeholder="具体怎么兑现、有什么约定…"></textarea>
    <label class="field-label">可兑换次数（可选）</label>
    <input v-model.number="createForm.maxOrders" class="field" type="number" inputmode="numeric" min="1" max="1000" placeholder="留空表示不限次数" />
    <button class="sheet__cta" :disabled="busy" @click="doCreate">确认上架</button>
    <div class="hint-line">上架不扣金币；提交后立即出现在可兑换列表</div>
  </div>

  <!-- 成功弹层 -->
  <div class="success" :class="{ show: success.show }">
    <div class="check-ring">
      <svg width="38" height="38" viewBox="0 0 24 24" fill="none"><path d="M5 12.5l4.5 4.5L19 7.5" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </div>
    <div class="success__t">{{ success.title }}</div>
    <div class="success__s">{{ success.sub }}</div>
  </div>

  <!-- 全局错误提示 -->
  <div v-if="errorMsg" class="toast-error">{{ errorMsg }}</div>
</section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import StatusBar from '../components/StatusBar.vue';
import { get } from '../api/client.js';
import { fileUrl } from '../api/config.js';
import {
  listItems, listMyItems, listOrders, buyItem, completeOrder,
  cancelOrder, offlineItem, editItem, createItem,
} from '../api/mall.js';
import {
  getBalance, giftCoins, listTransactions,
  createApply, listMyApplies, listPendingApplies,
  approveApply, rejectApply, uploadEvidence,
} from '../api/coins.js';

const DAILY_LIMIT = 500;

const props = defineProps({ active: { type: Boolean, default: false } });
const emit = defineEmits(['back']);

/* ---------------- 基础数据 ---------------- */
const me = ref(null);
const couple = ref(null);
const balance = ref(0);
const balanceDisplay = ref(0);
const tab = ref('items');
const approvedItems = ref([]);
const myItems = ref([]);
const orders = ref([]);
const txns = ref([]);
const myApplies = ref([]);
const pendingApplies = ref([]);
const loading = ref(true);
const errorMsg = ref('');
const busy = ref(false);

/* ---------------- 消息中心 ---------------- */
const msgPage = ref(false);
const msgTab = ref('todo');

/* ---------------- 索要 / 审批 ---------------- */
const reqReason = ref('');
const reqAmount = ref(20);
const reqPhotoUrl = ref('');
const reqEvidenceKey = ref('');
const reqUploading = ref(false);
const photoInput = ref(null);
const reviewItem = ref(null);
const reviewRejectRemark = ref('');

/* ---------------- 弹层 ---------------- */
const sheet = ref(null);
const target = ref(null);
const giftAmount = ref(20);
const giftRemark = ref('');
const editForm = ref({ title: '', price: null, desc: '' });
const createForm = ref({ title: '', price: null, desc: '', maxOrders: null });
const success = ref({ show: false, title: '', sub: '' });
const scrollEl = ref(null);

/* ---------------- 派生 ---------------- */
const itemMap = computed(() => {
  const m = new Map();
  for (const it of [...approvedItems.value, ...myItems.value]) m.set(it.id, it);
  return m;
});

const buyItems = computed(() =>
  approvedItems.value.filter((it) => it.creator_id !== me.value?.id),
);

const myGridItems = computed(() =>
  myItems.value.filter((it) => it.status === 'approved'),
);

const redeemOrders = computed(() =>
  orders.value.filter((o) => {
    if (o.status !== 'pending') return false;
    return itemMap.value.get(o.item_id)?.creator_id === me.value?.id;
  }),
);

const waitOrders = computed(() =>
  orders.value.filter((o) => o.status === 'pending' && o.buyer_id === me.value?.id),
);

const doneOrders = computed(() =>
  orders.value.filter((o) => o.status === 'completed'),
);

const giftSentToday = computed(() => {
  const now = new Date();
  let total = 0;
  for (const t of txns.value) {
    if (t.type !== 'gift' || t.direction !== 'out') continue;
    const d = new Date(t.created_at);
    if (d.toDateString() === now.toDateString()) total += t.amount;
  }
  return total;
});

const quotaLeft = computed(() => Math.max(0, DAILY_LIMIT - giftSentToday.value));

/* 全部消息：我发起的索要 + 赠送金币流水，统一成消息卡结构，按时间倒序 */
const allMessages = computed(() => {
  const list = [];
  for (const a of myApplies.value) {
    const stateMap = {
      pending: ['ms-wait', '待对方处理'],
      approved: ['ms-done', '已完成'],
      rejected: ['ms-no', '已拒绝'],
    };
    const [stateClass, stateLabel] = stateMap[a.status] || stateMap.pending;
    list.push({
      uid: `apply-${a.id}`,
      icon: 'ask',
      title: '我发起的索要',
      who: '我 → 对方',
      amount: a.approved_amount ?? a.amount,
      reason: a.reason,
      photoUrl: a.evidence_url || fileUrl(a.evidence_key),
      stateClass,
      stateLabel,
      time: a.created_at,
    });
  }
  for (const t of txns.value) {
    if (t.type !== 'gift') continue;
    const isIn = t.direction === 'in';
    list.push({
      uid: `gift-${t.id}`,
      icon: 'give',
      title: isIn ? '收到的赠送' : '我赠送的金币',
      who: isIn ? '对方 → 我' : '我 → 对方',
      amount: t.amount,
      reason: t.remark || '',
      photoUrl: '',
      stateClass: 'ms-done',
      stateLabel: '已完成',
      time: t.created_at,
    });
  }
  return list.sort((x, y) => new Date(y.time) - new Date(x.time));
});

/* ---------------- 工具函数 ---------------- */
function itemTitle(id) {
  return itemMap.value.get(id)?.title ?? '已下架商品';
}

function statusText(s) {
  return { approved: '已上架', offline: '已下架' }[s] || s;
}

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const datePart =
    d.getFullYear() === now.getFullYear()
      ? `${d.getMonth() + 1}月${d.getDate()}日`
      : `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
  return `${datePart} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function uuid() {
  return crypto?.randomUUID?.() || `k-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function showError(msg) {
  errorMsg.value = msg;
  setTimeout(() => { errorMsg.value = ''; }, 2600);
}

function showSuccess(title, sub) {
  success.value = { show: true, title, sub };
  setTimeout(() => { success.value.show = false; }, 1500);
}

/* 两次余额变化挨得很近时（连续兑换 / 退款），上一段动画还没跑完就开新的，
   两个 interval 会同时往 balanceDisplay 里写，数字来回跳。开新的先把旧的停掉。 */
let balTimer = 0;
function animateBalance(to) {
  const from = balanceDisplay.value;
  if (from === to) return;
  clearInterval(balTimer);
  const steps = 14;
  let i = 0;
  balTimer = setInterval(() => {
    i += 1;
    balanceDisplay.value = Math.round(from + (to - from) * (i / steps));
    if (i === steps) clearInterval(balTimer);
  }, 16);
}

/* ---------------- 数据加载 ---------------- */
async function loadAll(animate = true) {
  const [
    meData, coupleData, bal, items, mine, ords, txList,
    myApplyList, pendingList,
  ] = await Promise.all([
    get('/users/me'),
    get('/couples/me'),
    getBalance(),
    listItems(),
    listMyItems(),
    listOrders(),
    listTransactions(100, 0),
    listMyApplies(),
    listPendingApplies(),
  ]);
  me.value = meData;
  couple.value = coupleData;
  balance.value = bal.balance;
  approvedItems.value = items;
  myItems.value = mine;
  orders.value = ords;
  txns.value = txList;
  myApplies.value = myApplyList;
  pendingApplies.value = pendingList;
  if (animate) animateBalance(bal.balance);
  else balanceDisplay.value = bal.balance;
}

/* ---------------- 弹层控制 ---------------- */
function openSheet(name, obj = null) {
  target.value = obj;
  sheet.value = name;
}

function closeSheet() {
  sheet.value = null;
  target.value = null;
}

function goBack() {
  emit('back');
}

/* ---------------- 消息中心 ---------------- */
function openMessages() {
  msgTab.value = 'todo';
  msgPage.value = true;
}

function closeMessages() {
  msgPage.value = false;
}

/* ---------------- 索要 ---------------- */
function openRequest() {
  reqReason.value = '';
  reqAmount.value = 20;
  removePhoto();
  target.value = null;
  sheet.value = 'request';
}

function pickPhoto() {
  photoInput.value?.click();
}

async function onPickPhoto(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  if (reqPhotoUrl.value) URL.revokeObjectURL(reqPhotoUrl.value);
  reqPhotoUrl.value = URL.createObjectURL(file);
  reqEvidenceKey.value = '';
  reqUploading.value = true;
  try {
    const up = await uploadEvidence(file);
    reqEvidenceKey.value = up.key;
  } catch (err) {
    showError(err.message || '照片上传失败');
    removePhoto();
  } finally {
    reqUploading.value = false;
  }
}

function removePhoto() {
  if (reqPhotoUrl.value) URL.revokeObjectURL(reqPhotoUrl.value);
  reqPhotoUrl.value = '';
  reqEvidenceKey.value = '';
  reqUploading.value = false;
  if (photoInput.value) photoInput.value.value = '';
}

/* ---------------- 审批 ---------------- */
function openReview(a) {
  reviewItem.value = a;
  reviewRejectRemark.value = '';
  sheet.value = 'review';
}

function openEdit() {
  if (!target.value) return;
  const it = target.value;
  editForm.value = { title: it.title, price: it.price_coins, desc: it.description || '' };
  sheet.value = 'edit';
}

function openCreate() {
  createForm.value = { title: '', price: null, desc: '', maxOrders: null };
  target.value = null;
  sheet.value = 'create';
}

/* ---------------- 业务操作 ---------------- */
async function runWithBusy(fn) {
  if (busy.value) return;
  busy.value = true;
  try {
    await fn();
  } catch (e) {
    showError(e.message || '操作失败，请稍后再试');
  } finally {
    busy.value = false;
  }
}

async function refreshAfter() {
  await loadAll(true);
}

function doGift() {
  const amount = Number(giftAmount.value);
  if (!amount || amount <= 0) { showError('请输入正确的赠送数量'); return; }
  if (amount > quotaLeft.value) { showError('今日赠送将超过 500 枚上限'); return; }
  runWithBusy(async () => {
    await giftCoins(amount, giftRemark.value || null, uuid());
    closeSheet();
    await refreshAfter();
    showSuccess('赠送成功', `已为对方发行 ${amount} 枚金币`);
  });
}

function doRequest() {
  const reason = reqReason.value.trim();
  const amount = Number(reqAmount.value);
  if (!reason) { showError('请填写事由'); return; }
  if (!amount || amount <= 0) { showError('请输入正确的索要金额'); return; }
  if (reqUploading.value) { showError('照片还在上传，请稍等'); return; }
  runWithBusy(async () => {
    await createApply(amount, reason, reqEvidenceKey.value || null);
    closeSheet();
    await refreshAfter();
    showSuccess('已提交索要', '等对方确认后金币到账');
  });
}

function doApprove() {
  const a = reviewItem.value;
  if (!a) return;
  runWithBusy(async () => {
    await approveApply(a.id, null, null);
    closeSheet();
    await refreshAfter();
    showSuccess('已同意索要', `系统已发行 ${a.amount} 枚给对方`);
  });
}

function doReject(item) {
  const a = item || reviewItem.value;
  if (!a) return;
  const remark = reviewRejectRemark.value?.trim() || null;
  runWithBusy(async () => {
    await rejectApply(a.id, remark);
    closeSheet();
    await refreshAfter();
    showSuccess('已拒绝', '对方会看到拒绝结果');
  });
}

function doBuy() {
  const it = target.value;
  if (!it) return;
  const price = it.price_coins;
  if (balance.value < price) { showError('金币不足'); return; }
  runWithBusy(async () => {
    await buyItem(it.id, uuid());
    closeSheet();
    await refreshAfter();
    showSuccess('兑换成功', '金币已销毁，等对方核销兑现');
  });
}

function doRedeem() {
  const o = target.value;
  if (!o) return;
  runWithBusy(async () => {
    await completeOrder(o.id);
    closeSheet();
    await refreshAfter();
    showSuccess('核销成功', '订单已关闭，已通知对方');
  });
}

function doCancel() {
  const o = target.value;
  if (!o) return;
  runWithBusy(async () => {
    await cancelOrder(o.id);
    closeSheet();
    await refreshAfter();
    showSuccess('已取消', `${o.price} 枚金币已退回你的账户`);
  });
}

function doOffline() {
  const it = target.value;
  if (!it || it.status !== 'approved') return;
  runWithBusy(async () => {
    await offlineItem(it.id);
    closeSheet();
    await refreshAfter();
    showSuccess('已下架', `「${it.title}」对方将无法再兑换`);
  });
}

function saveEdit() {
  const it = target.value;
  const title = editForm.value.title?.trim();
  const price = Number(editForm.value.price);
  if (!title) { showError('商品名称不能为空'); return; }
  if (!price || price <= 0) { showError('价格必须大于 0'); return; }
  runWithBusy(async () => {
    await editItem(it.id, {
      title,
      description: editForm.value.desc?.trim() || null,
      price_coins: price,
      max_orders: it.max_orders,
    });
    closeSheet();
    await refreshAfter();
    showSuccess('修改已保存', `「${title}」已更新`);
  });
}

function doCreate() {
  const title = createForm.value.title?.trim();
  const price = Number(createForm.value.price);
  const rawMax = createForm.value.maxOrders;
  const maxOrders = rawMax === null || rawMax === '' ? null : Number(rawMax);
  if (!title) { showError('商品名称不能为空'); return; }
  if (!price || price <= 0) { showError('价格必须大于 0'); return; }
  if (maxOrders !== null && (!Number.isInteger(maxOrders) || maxOrders < 1)) {
    showError('可兑换次数必须是正整数，或留空不限');
    return;
  }
  runWithBusy(async () => {
    await createItem({
      title,
      description: createForm.value.desc?.trim() || null,
      price_coins: price,
      max_orders: maxOrders,
    });
    closeSheet();
    await refreshAfter();
    showSuccess('上架成功', `「${title}」已可兑换`);
  });
}

onMounted(async () => {
  try {
    await loadAll(false);
  } catch (e) {
    showError(e.message || '数据加载失败，请确认后端已启动');
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.mall {
  --ink: #2c121f;
  --coral: #ff5987;
  --coral-deep: #f02a66;
  --gold: #f4b23c;
  --gold-deep: #e09617;
  --mint: #33c08f;
  --ease: cubic-bezier(.16, 1, .3, 1);
  --spring: cubic-bezier(.32, 1.24, .36, 1);

  position: absolute;
  inset: 0;
  z-index: 40;
  overflow: hidden;
  background: linear-gradient(180deg, #fbfbfe 0%, #f8f8fd 45%, #f6f6fb 100%);
  transform: translateX(100%);
  transition: transform .5s var(--ease);
}
.mall.on {
  transform: none;
}
.mall::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(58% 28% at 82% 6%, rgba(255, 205, 222, .32), transparent 70%),
    radial-gradient(48% 30% at 10% 3%, rgba(214, 220, 255, .3), transparent 72%);
}
.mall * {
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}

/* 顶部导航 */
.nav {
  position: absolute;
  top: 44px;
  left: 0;
  right: 0;
  height: 52px;
  z-index: 7;
  display: flex;
  align-items: center;
  padding: 0 10px;
}
.nav__back {
  display: flex;
  align-items: center;
  gap: 1px;
  border: 0;
  background: none;
  font-family: inherit;
  font-size: 16px;
  font-weight: 600;
  color: var(--coral);
  padding: 8px 8px 8px 6px;
  border-radius: 12px;
  transition: transform .18s var(--ease), background .2s;
}
.nav__back:active {
  transform: scale(.94);
  background: rgba(255, 93, 135, .1);
}
.nav__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  pointer-events: none;
}
.nav__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -.01em;
  line-height: 1.1;
}
.nav__sub {
  font-size: 10.5px;
  font-weight: 600;
  color: rgba(44, 18, 31, .46);
}
.nav__right {
  margin-left: auto;
  position: relative;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 0;
  display: grid;
  place-items: center;
  color: var(--coral);
  background: rgba(255, 255, 255, .65);
  backdrop-filter: blur(10px);
  transition: transform .18s var(--ease);
}
.nav__right:active {
  transform: scale(.9);
}
.nav__right .red-dot {
  position: absolute;
  top: 5px;
  right: 6px;
  min-width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--coral-deep);
  border: 1.6px solid #fff;
}
.nav__right.clear .red-dot {
  display: none;
}
.nav__ph {
  width: 34px;
  flex: none;
}

/* 可滚动主体 */
.scroll {
  position: absolute;
  top: 96px;
  left: 0;
  right: 0;
  bottom: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 16px 40px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.scroll::-webkit-scrollbar {
  display: none;
}

/* 金币余额白卡 */
.wallet {
  position: relative;
  border-radius: 26px;
  padding: 20px 20px 18px;
  color: var(--ink);
  overflow: hidden;
  background: linear-gradient(180deg, #ffffff, #fcfcfe);
  box-shadow: 0 16px 34px -20px rgba(50, 45, 75, .35), inset 0 0 0 .5px rgba(255, 255, 255, .95);
}
.wallet::after {
  content: "";
  position: absolute;
  right: -46px;
  top: -54px;
  width: 168px;
  height: 168px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(244, 178, 60, .2), transparent 70%);
}
.wallet__top {
  display: flex;
  align-items: center;
  gap: 9px;
  position: relative;
  z-index: 1;
}
.coin-ic {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex: none;
  display: grid;
  place-items: center;
  background: linear-gradient(180deg, #ffd98a, var(--gold-deep));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .6), 0 4px 10px -3px rgba(150, 90, 20, .45);
}
.wallet__label {
  font-size: 13px;
  font-weight: 700;
  color: rgba(44, 18, 31, .55);
}
.wallet__balance {
  font-size: 44px;
  font-weight: 800;
  letter-spacing: -1.5px;
  line-height: 1.05;
  margin: 10px 0 2px;
  position: relative;
  z-index: 1;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
.wallet__balance small {
  font-size: 15px;
  font-weight: 700;
  color: rgba(44, 18, 31, .5);
  margin-left: 4px;
}
.wallet__quota {
  font-size: 11.5px;
  font-weight: 600;
  color: rgba(44, 18, 31, .5);
  position: relative;
  z-index: 1;
}
.wallet__quota b {
  font-weight: 800;
  color: var(--gold-deep);
}
.wallet__actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  position: relative;
  z-index: 1;
}
.wbtn {
  flex: 1;
  border: 0;
  height: 42px;
  border-radius: 15px;
  font-family: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  transition: transform .18s var(--spring), filter .2s;
}
.wbtn:active {
  transform: scale(.95);
}
.wbtn--give {
  color: #fff;
  background: linear-gradient(160deg, #ff7aa6, var(--coral-deep));
  box-shadow: 0 9px 18px -9px rgba(240, 42, 102, .6);
}
.wbtn--ask {
  color: var(--gold-deep);
  background: linear-gradient(180deg, #fff6e2, #ffedc4);
  box-shadow: inset 0 0 0 1px rgba(224, 150, 23, .35);
}

/* 分段 Tab：类名不能叫 .tabs —— 全局 app.css 里 .tabs 是底栏导航（absolute 定位），
   同名会被带成 absolute、左右贴 --pad，看起来就整条偏右 */
.mtabs {
  display: flex;
  margin: 18px 0 14px;
  padding: 4px;
  border-radius: 999px;
  background: #efeff5;
  box-shadow: inset 0 0 0 .5px rgba(255, 255, 255, .7);
  position: relative;
}
.mtabs__thumb {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 4px;
  width: calc(50% - 4px);
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 3px 9px -3px rgba(60, 55, 85, .35);
  transition: transform .34s var(--spring);
}
.mtabs.on-orders .mtabs__thumb {
  transform: translateX(100%);
}
.mtabs button {
  position: relative;
  z-index: 1;
  flex: 1;
  border: 0;
  background: none;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  padding: 9px 0;
  color: rgba(44, 18, 31, .45);
  transition: color .28s;
}
.mtabs button.on {
  color: var(--ink);
}
.mtabs .badge {
  display: inline-grid;
  place-items: center;
  min-width: 17px;
  height: 17px;
  padding: 0 5px;
  margin-left: 5px;
  border-radius: 9px;
  font-size: 10.5px;
  font-weight: 800;
  color: #fff;
  background: var(--coral);
  vertical-align: 1px;
}

/* 区块标题 */
.sec-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 800;
  color: rgba(44, 18, 31, .55);
  margin: 18px 2px 10px;
  letter-spacing: .2px;
}
.sec-h .count {
  font-size: 11px;
  font-weight: 700;
  color: rgba(44, 18, 31, .4);
}
.add-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 0;
  padding: 6px 12px;
  border-radius: 999px;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(160deg, #ff7aa6, var(--coral-deep));
  box-shadow: 0 6px 13px -7px rgba(240, 42, 102, .6);
  transition: transform .18s var(--spring);
}
.add-item:active {
  transform: scale(.93);
}
.sec-note {
  font-size: 10.5px;
  font-weight: 600;
  color: rgba(44, 18, 31, .4);
  margin: -4px 2px 10px;
}

/* 商品网格方块 */
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 11px;
}
.tile {
  display: flex;
  flex-direction: column;
  padding: 14px;
  border-radius: 22px;
  background: #fff;
  position: relative;
  overflow: hidden;
  box-shadow: 0 12px 26px -18px rgba(50, 45, 75, .4), inset 0 0 0 .5px rgba(255, 252, 255, .95);
}
.tile__ic {
  width: 54px;
  height: 54px;
  border-radius: 17px;
  margin-bottom: 12px;
  display: grid;
  place-items: center;
}
.tile__ic--buy {
  background: linear-gradient(160deg, #fff0f6, #ffe4ee);
}
.tile__ic--mine {
  background: linear-gradient(160deg, #fff6e2, #ffedc4);
}
.tile__title {
  font-size: 14px;
  font-weight: 800;
  color: var(--ink);
  line-height: 1.3;
  min-height: 36px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tile__meta {
  font-size: 10.5px;
  font-weight: 600;
  color: rgba(44, 18, 31, .42);
  margin-top: 5px;
}
.tile__price {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 11px;
  font-size: 15px;
  font-weight: 800;
  color: var(--gold-deep);
  font-variant-numeric: tabular-nums;
}
.tile .buy,
.tile .manage {
  width: 100%;
  margin-top: 9px;
  height: 34px;
  padding: 0;
}
.tile__mineflag {
  position: absolute;
  top: 11px;
  right: 11px;
  font-size: 9px;
  font-weight: 800;
  color: var(--gold-deep);
  background: #fff3d6;
  padding: 2px 7px;
  border-radius: 8px;
}
.buy {
  border: 0;
  border-radius: 11px;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(160deg, #ff7aa6, var(--coral-deep));
  box-shadow: 0 7px 15px -7px rgba(240, 42, 102, .6);
  transition: transform .18s var(--spring), filter .2s;
}
.buy:active {
  transform: scale(.92);
}
.buy:disabled {
  background: rgba(200, 170, 185, .6);
  box-shadow: none;
}
.manage {
  border: 0;
  border-radius: 11px;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 800;
  color: var(--gold-deep);
  background: linear-gradient(180deg, #fff3d6, #ffe7ae);
}
.manage:active {
  transform: scale(.94);
}

/* 订单卡 */
.order {
  padding: 14px 15px;
  margin-bottom: 11px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: 0 12px 26px -18px rgba(50, 45, 75, .4), inset 0 0 0 .5px rgba(255, 255, 255, .95);
}
.order__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.order__title {
  font-size: 14.5px;
  font-weight: 800;
  color: var(--ink);
}
.order__who {
  font-size: 11px;
  font-weight: 600;
  color: rgba(44, 18, 31, .48);
  margin-top: 3px;
}
.order__price {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  font-weight: 800;
  color: var(--gold-deep);
  flex: none;
}
.order__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 800;
  padding: 5px 11px;
  border-radius: 10px;
}
.status-pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.st-pending {
  color: var(--coral-deep);
  background: #ffe1ec;
}
.st-pending .dot {
  background: var(--coral);
  animation: pulse 1.3s infinite;
}
.st-wait {
  color: #b97a1e;
  background: #fdf0d6;
}
.st-wait .dot {
  background: var(--gold);
}
.st-done {
  color: #159b6f;
  background: #dcf6ec;
}
.st-done .dot {
  background: var(--mint);
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}
.redeem {
  border: 0;
  height: 34px;
  padding: 0 18px;
  border-radius: 12px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(160deg, #ff7aa6, var(--coral-deep));
  box-shadow: 0 8px 16px -7px rgba(240, 42, 102, .6);
  transition: transform .18s var(--spring);
}
.redeem:active {
  transform: scale(.93);
}
.cancel-btn {
  border: 0;
  height: 34px;
  padding: 0 16px;
  border-radius: 12px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  color: #d63a52;
  background: #fde8ec;
  box-shadow: inset 0 0 0 1px rgba(214, 58, 82, .22);
  transition: transform .18s var(--spring);
}
.cancel-btn:active {
  transform: scale(.93);
}

/* 空状态 */
.empty {
  text-align: center;
  padding: 34px 20px;
  color: rgba(44, 18, 31, .4);
  font-size: 12.5px;
  font-weight: 600;
}
.grid-empty {
  grid-column: 1 / -1;
}

/* 底部弹层 */
.mask {
  position: absolute;
  inset: 0;
  z-index: 50;
  background: rgba(45, 18, 32, .4);
  backdrop-filter: blur(3px);
  opacity: 0;
  pointer-events: none;
  transition: opacity .32s var(--ease);
}
.mask.show {
  opacity: 1;
  pointer-events: auto;
}
.sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 51;
  background: linear-gradient(180deg, #fffafd, #fff7fb);
  border-radius: 28px 28px 0 0;
  padding: 10px 20px 30px;
  opacity: 1; /* 覆盖全局 app.css 的 .sheet{opacity:0}，本页用 transform 控制显隐 */
  transform: translateY(102%);
  transition: transform .46s var(--spring);
  box-shadow: 0 -20px 44px -20px rgba(120, 40, 70, .4);
  max-height: 88%;
  overflow-y: auto;
}
.sheet.show {
  transform: translateY(0);
}
.sheet__grab {
  width: 40px;
  height: 5px;
  border-radius: 3px;
  background: rgba(120, 60, 90, .18);
  margin: 4px auto 16px;
}
.sheet__title {
  font-size: 18px;
  font-weight: 800;
  color: var(--ink);
  text-align: center;
}
.sheet__sub {
  font-size: 12px;
  font-weight: 600;
  color: rgba(44, 18, 31, .45);
  text-align: center;
  margin-top: 4px;
}
.custom-amount {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 20px 0 14px;
  background: #fff;
  border-radius: 16px;
  padding: 10px 14px;
  box-shadow: inset 0 0 0 1.5px rgba(255, 150, 180, .55);
}
.custom-amount .coin-ic {
  width: 32px;
  height: 32px;
  flex: none;
}
.custom-amount input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  font-family: inherit;
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
  background: none;
  font-variant-numeric: tabular-nums;
}
.custom-amount input::placeholder {
  color: rgba(44, 18, 31, .3);
  font-weight: 700;
}
.custom-amount__unit {
  font-size: 14px;
  font-weight: 800;
  color: rgba(44, 18, 31, .5);
  flex: none;
}
.custom-amount input::-webkit-outer-spin-button,
.custom-amount input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.chips {
  display: flex;
  gap: 9px;
  justify-content: center;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.chip {
  border: 0;
  padding: 9px 17px;
  border-radius: 13px;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 800;
  color: var(--ink);
  background: rgba(255, 225, 236, .8);
  transition: transform .16s var(--spring), background .2s;
}
.chip:active {
  transform: scale(.93);
}
.chip.on {
  color: #fff;
  background: linear-gradient(160deg, #ff7aa6, var(--coral-deep));
}
.remark {
  width: 100%;
  border: 0;
  outline: 0;
  font-family: inherit;
  font-size: 14px;
  background: rgba(255, 240, 246, .9);
  border-radius: 15px;
  padding: 13px 15px;
  color: var(--ink);
  margin-bottom: 20px;
}
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 800;
  color: rgba(44, 18, 31, .5);
  margin: 14px 0 7px;
}
.field {
  width: 100%;
  border: 0;
  outline: 0;
  font-family: inherit;
  font-size: 14px;
  background: #f6f5f9;
  border-radius: 14px;
  padding: 13px 14px;
  color: var(--ink);
  box-shadow: inset 0 0 0 1px rgba(80, 70, 95, .08);
}
.field:focus {
  box-shadow: inset 0 0 0 1.5px rgba(255, 150, 180, .7);
}
.field--area {
  resize: none;
  line-height: 1.5;
}
.sheet__cta {
  width: 100%;
  border: 0;
  height: 50px;
  border-radius: 17px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(160deg, #ff7aa6, var(--coral-deep));
  box-shadow: 0 12px 24px -12px rgba(240, 42, 102, .65);
  transition: transform .18s var(--spring), filter .2s;
}
.sheet__cta:active {
  transform: scale(.97);
}
.sheet__cta:disabled {
  background: rgba(200, 170, 185, .7);
  box-shadow: none;
}
.sheet__danger {
  width: 100%;
  border: 0;
  height: 50px;
  border-radius: 17px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 800;
  color: #d63a52;
  background: #fde8ec;
  box-shadow: inset 0 0 0 1px rgba(214, 58, 82, .25);
  transition: transform .18s var(--spring), background .2s;
}
.sheet__danger:active {
  transform: scale(.97);
}
.sheet__danger:disabled {
  color: rgba(120, 90, 100, .5);
  background: #f3eef0;
  box-shadow: none;
}
.hint-line {
  font-size: 11px;
  font-weight: 600;
  color: rgba(44, 18, 31, .4);
  text-align: center;
  margin-top: 11px;
}
.confirm-box {
  background: rgba(255, 240, 246, .85);
  border-radius: 18px;
  padding: 16px;
  margin: 20px 0;
}
.confirm-row {
  display: flex;
  justify-content: space-between;
  font-size: 13.5px;
  font-weight: 700;
  color: rgba(44, 18, 31, .65);
  padding: 6px 0;
}
.confirm-row b {
  color: var(--ink);
  font-weight: 800;
}
.gold-text {
  color: var(--gold-deep);
}
.green-text {
  color: #159b6f;
}
.muted-text {
  color: #9a949c;
}

/* 成功弹层 */
.success {
  position: absolute;
  left: 50%;
  top: 50%;
  z-index: 60;
  transform: translate(-50%, -46%) scale(.9);
  background: rgba(255, 255, 255, .97);
  border-radius: 26px;
  padding: 28px 34px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  opacity: 0;
  pointer-events: none;
  transition: opacity .3s, transform .4s var(--spring);
  box-shadow: 0 26px 60px -20px rgba(120, 40, 70, .5);
}
.success.show {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
  pointer-events: auto;
}
.check-ring {
  width: 74px;
  height: 74px;
  border-radius: 50%;
  background: linear-gradient(160deg, #54d4a4, #22b57f);
  display: grid;
  place-items: center;
  box-shadow: 0 14px 28px -10px rgba(34, 181, 127, .6);
}

/* 错误 toast */
.toast-error {
  position: absolute;
  left: 24px;
  right: 24px;
  bottom: 36px;
  z-index: 50;
  background: rgba(45, 18, 32, .92);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  padding: 13px 16px;
  border-radius: 15px;
  text-align: center;
  backdrop-filter: blur(8px);
}

/* ================= 消息中心独立页 ================= */
.mall .statusbar { z-index: 65; }
.msg-page {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #fbfbfe, #f6f6fb);
  transform: translateX(100%);
  transition: transform .52s var(--ease);
}
.msg-page.on { transform: none; }
.msg-page .nav {
  position: static;
  flex: none;
  margin-top: 44px;
}
.msg-page .nav__center {
  position: static;
  transform: none;
  pointer-events: auto;
  margin: 0 auto;
}
.msg-page__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 16px 40px;
  scrollbar-width: none;
}
.msg-page__scroll::-webkit-scrollbar { display: none; }

/* 分段控件 */
.seg {
  display: flex;
  position: relative;
  padding: 4px;
  border-radius: 999px;
  background: #efeff5;
  margin: 6px 0 14px;
}
.seg__thumb {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 4px;
  width: calc(50% - 4px);
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 3px 9px -3px rgba(60, 55, 85, .35);
  transition: transform .34s var(--spring);
}
.seg.on-all .seg__thumb { transform: translateX(100%); }
.seg button {
  position: relative;
  z-index: 1;
  flex: 1;
  border: 0;
  background: none;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 700;
  padding: 9px 0;
  color: rgba(44, 18, 31, .45);
  transition: color .28s;
}
.seg button.on { color: var(--ink); }
.mini-badge {
  display: inline-grid;
  place-items: center;
  min-width: 17px;
  height: 17px;
  padding: 0 5px;
  margin-left: 4px;
  border-radius: 9px;
  font-size: 10.5px;
  font-weight: 800;
  color: #fff;
  background: var(--coral);
}

/* 消息卡 */
.msg {
  background: #fff;
  border-radius: 20px;
  padding: 14px;
  margin-bottom: 11px;
  box-shadow: 0 12px 26px -18px rgba(50, 45, 75, .4), inset 0 0 0 .5px rgba(255, 255, 255, .95);
  animation: msgRise .45s var(--ease) both;
}
@keyframes msgRise {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: none; }
}
.msg__top { display: flex; align-items: center; gap: 10px; }
.msg__ic {
  width: 38px;
  height: 38px;
  border-radius: 13px;
  flex: none;
  display: grid;
  place-items: center;
}
.msg__ic--ask {
  background: linear-gradient(160deg, #fff6e2, #ffedc4);
  color: var(--gold-deep);
}
.msg__ic--give {
  background: linear-gradient(160deg, #fff0f6, #ffe4ee);
  color: var(--coral-deep);
}
.msg__head { flex: 1; min-width: 0; }
.msg__title {
  font-size: 14px;
  font-weight: 800;
  color: var(--ink);
}
.msg__who {
  font-size: 11px;
  font-weight: 600;
  color: rgba(44, 18, 31, .45);
  margin-top: 2px;
}
.msg__amount {
  font-size: 16px;
  font-weight: 800;
  color: var(--gold-deep);
  font-variant-numeric: tabular-nums;
  flex: none;
}
.msg__reason {
  font-size: 12.5px;
  font-weight: 600;
  color: rgba(44, 18, 31, .6);
  margin-top: 10px;
  line-height: 1.45;
}
.msg__photo {
  margin-top: 10px;
  width: 88px;
  height: 88px;
  border-radius: 14px;
  object-fit: cover;
  box-shadow: inset 0 0 0 1px rgba(80, 70, 95, .1);
}
.msg__foot { display: flex; gap: 9px; margin-top: 12px; }
.msg__btn {
  flex: 1;
  border: 0;
  height: 38px;
  border-radius: 13px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  transition: transform .16s var(--spring);
}
.msg__btn:active { transform: scale(.95); }
.msg__btn--ok {
  color: #fff;
  background: linear-gradient(160deg, #54d4a4, #22b57f);
  box-shadow: 0 8px 16px -8px rgba(34, 181, 127, .6);
}
.msg__btn--no {
  color: #d63a52;
  background: #fde8ec;
  box-shadow: inset 0 0 0 1px rgba(214, 58, 82, .22);
}
.msg__state-row {
  margin-top: 11px;
  display: flex;
  justify-content: flex-end;
}
.msg__state {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 800;
  padding: 5px 11px;
  border-radius: 10px;
}
.ms-wait { color: #b97a1e; background: #fdf0d6; }
.ms-done { color: #159b6f; background: #dcf6ec; }
.ms-no { color: #d63a52; background: #fde8ec; }

/* ================= 照片上传 ================= */
.photo-upload {
  margin-top: 6px;
  border: 1.6px dashed rgba(224, 150, 23, .5);
  border-radius: 16px;
  background: rgba(255, 246, 226, .55);
  padding: 16px;
  text-align: center;
  transition: background .2s, border-color .2s;
}
.photo-upload:active { background: rgba(255, 237, 196, .7); }
.photo-upload__icon {
  color: var(--gold-deep);
  display: grid;
  place-items: center;
  margin-bottom: 7px;
}
.photo-upload__t { font-size: 13.5px; font-weight: 800; color: var(--gold-deep); }
.photo-upload__s {
  font-size: 11px;
  font-weight: 600;
  color: rgba(44, 18, 31, .45);
  margin-top: 3px;
}
.photo-preview { position: relative; margin-top: 12px; }
.photo-preview img {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px rgba(80, 70, 95, .1);
  animation: msgRise .35s var(--ease) both;
}
.photo-preview__remove {
  position: absolute;
  top: 9px;
  right: 9px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 0;
  background: rgba(40, 20, 30, .55);
  color: #fff;
  display: grid;
  place-items: center;
  backdrop-filter: blur(6px);
}

/* 金色提交按钮 */
.sheet__cta--gold {
  background: linear-gradient(160deg, #ffd98a, var(--gold-deep));
  box-shadow: 0 12px 24px -12px rgba(224, 150, 23, .6);
}

/* ================= 审批详情 ================= */
.review-photo {
  width: 100%;
  height: 210px;
  object-fit: cover;
  border-radius: 18px;
  margin: 16px 0 4px;
  box-shadow: inset 0 0 0 1px rgba(80, 70, 95, .1);
}
.review-reason { line-height: 1.5; }
.review-amount-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 4px 0;
  font-weight: 800;
  color: rgba(44, 18, 31, .55);
}
.review-amount-row b {
  color: var(--gold-deep);
  font-size: 18px;
}
.review-actions { display: flex; gap: 10px; margin-top: 14px; }
.review-actions .sheet__cta { margin-top: 0; flex: 1; }
.review-ok {
  background: linear-gradient(160deg, #54d4a4, #22b57f);
  box-shadow: 0 12px 24px -12px rgba(34, 181, 127, .65);
}
.review-no {
  background: #fde8ec;
  color: #d63a52;
  box-shadow: inset 0 0 0 1px rgba(214, 58, 82, .25);
}
</style>
