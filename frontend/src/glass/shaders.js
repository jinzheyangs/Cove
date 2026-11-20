/* Cove · 着色器
   Pass 1（FS_BG）：纸白底 + 粉雾带 + 硬边几何 → 画进 FBO 纹理
   Pass 2（FS_GLASS）：SDF 圆角矩形 → 高度场 → 法线 → 双界面折射采样那张纹理

   浅色玻璃与深色玻璃是两套物理：
   深色靠吸收 exp(-vec3(...)*path)，浅色 absorb 恒为 1，靠「提亮 + 低去饱和」
   + 外侧 1px 灰发丝 + 内侧纸边白光 + 接触阴影 来定义厚度。 */

export const VS = `attribute vec2 aPos; void main(){ gl_Position = vec4(aPos,0.0,1.0); }`;

/* ---------------- 背景 ---------------- */
export const FS_BG = `
precision highp float;
uniform vec2  uRes;
uniform vec2  uCss;
uniform float uTime;
uniform float uPulse;
uniform float uBright;
uniform float uTree;

float hash(vec2 p){ p=fract(p*vec2(123.34,456.21)); p+=dot(p,p+45.32); return fract(p.x*p.y); }
mat2 rot(float a){ float c=cos(a),s=sin(a); return mat2(c,-s,s,c); }

float sdC(vec2 p, vec2 c, float r){ return length(p-c)-r; }
float sdBox(vec2 p, vec2 b, float r){
  vec2 d = abs(p)-b+vec2(r);
  return length(max(d,0.0)) + min(max(d.x,d.y),0.0) - r;
}
/* 硬边抗锯齿：只给 0.5px，不做软化 —— 软边在玻璃下面折射不出来
   （写成显式 clamp，不用反向 smoothstep，那个在部分驱动上行为未定义） */
float aa(float d){ return clamp(0.5 - d/0.0014, 0.0, 1.0); }

void main(){
  vec2 uv = gl_FragCoord.xy/uRes;

  /* ---- 秘密树页：蓝天 + 草地，与 DOM 背景逐段对齐，让挖洞边界不可见 ---- */
  if (uTree > 0.5){
    float sy = uv.y;  // 0 = 屏幕底，1 = 屏幕顶
    vec3 cTop = vec3(0.302,0.624,0.902);  // #4d9fe6
    vec3 c30  = vec3(0.490,0.725,0.933);  // #7db9ee
    vec3 c62  = vec3(0.749,0.878,0.969);  // #bfe0f7
    vec3 c82  = vec3(0.902,0.953,0.984);  // #e6f3fb
    vec3 c100 = vec3(0.847,0.933,0.812);  // #d8eecf
    vec3 sky;
    if (sy > 0.70)      sky = mix(c30, cTop, (sy-0.70)/0.30);
    else if (sy > 0.38) sky = mix(c62, c30, (sy-0.38)/0.32);
    else if (sy > 0.18) sky = mix(c82, c62, (sy-0.18)/0.20);
    else                sky = mix(c100, c82, sy/0.18);
    vec3 col = sky;
    // 草地：ground 顶 sy=0.229，底 sy=0.087
    vec3 gTop = vec3(0.549,0.788,0.353);  // #8cc95a
    vec3 gMid = vec3(0.435,0.722,0.267);  // #6fb844
    vec3 gBot = vec3(0.353,0.635,0.216);  // #5aa237
    float gt = clamp((0.229-sy)/(0.229-0.087), 0.0, 1.0);  // 0=草地顶，1=底
    vec3 gCol = gt < 0.4 ? mix(gTop,gMid,gt/0.4) : mix(gMid,gBot,(gt-0.4)/0.6);
    // 草地是硬矩形：仅在 sy 0.087(底)~0.229(顶) 之间，边缘留 1px 抗锯齿
    float gMask = smoothstep(0.085,0.090,sy) * (1.0 - smoothstep(0.226,0.231,sy));
    col = mix(col, gCol, gMask);
    gl_FragColor = vec4(col,1.0);
    return;
  }

  float asp = uCss.x/uCss.y;
  vec2 p = (uv-0.5)*vec2(asp,1.0);

  /* ---- 纸底 + 顶部粉雾带（底边大圆角，模拟一张压在纸上的色卡）---- */
  vec3 hazeTop = vec3(1.000, 0.933, 0.953);   /* #FFEEF3 */
  vec3 hazeBot = vec3(1.000, 0.969, 0.980);   /* #FFF7FA */
  float dBand  = sdBox(p - vec2(0.0, 0.370), vec2(0.258, 0.333), 0.048);
  float inBand = aa(dBand);   /* aa 返回 1 表示在形内 */

  vec3 col  = vec3(1.0);
  vec3 haze = mix(hazeTop, hazeBot, 1.0 - smoothstep(0.13, 0.47, p.y));
  haze *= 1.0 - 0.032*smoothstep(-0.05,0.30,p.x)*smoothstep(0.14,0.44,p.y);
  col = mix(col, haze, inBand);

  /* ---- 硬边几何：同一支玫红 7%，两层叠加到约 12% ----
     它们不是装饰，是给液态玻璃折射用的"光学内容" */
  float m = 0.0;
  m = max(m, aa(sdC(p, vec2( 0.250, 0.170), 0.142)));
  m = max(m, aa(sdC(p, vec2(-0.285, 0.430), 0.108)));
  m = max(m, aa(sdBox(rot(0.38)*(p - vec2(-0.020, 0.300)), vec2(0.126), 0.044)));
  m *= inBand;
  col = mix(col, vec3(1.0, 0.349, 0.529), m*0.072);

  float m2 = 0.0;
  m2 = max(m2, aa(sdC(p, vec2(-0.120, 0.120), 0.092)));
  m2 = max(m2, aa(sdBox(rot(-0.22)*(p - vec2(0.180, 0.470)), vec2(0.150), 0.052)));
  m2 *= inBand;
  col = mix(col, vec3(1.0, 0.349, 0.529), m2*0.048);

  /* ---- 内容区两团极淡柔光：冷紫 / 暖粉，让白纸不至于死平 ---- */
  float g1 = smoothstep(0.46, 0.0, length(p - vec2( 0.235, -0.245)));
  col = mix(col, vec3(0.905, 0.884, 1.000), g1*0.070);
  float g2 = smoothstep(0.40, 0.0, length(p - vec2(-0.250, -0.400)));
  col = mix(col, vec3(1.000, 0.898, 0.906), g2*0.070);

  col = mix(col, vec3(1.0,0.62,0.72), uPulse*0.04*smoothstep(0.55,0.0,length(p)));

  /* 纸纹：极轻，只为消掉渐变的带状 */
  col += (hash(uv*uRes*0.71)-0.5)*0.005;

  gl_FragColor = vec4(clamp(col,0.0,1.0)*uBright,1.0);
}
`;

/* ---------------- 玻璃 ---------------- */
export const FS_GLASS = `
#extension GL_OES_standard_derivatives : enable
precision highp float;

uniform sampler2D uBg;
uniform vec2  uRes;
uniform float uDpr;
uniform vec2  uCss;
uniform float uTime;

uniform vec4  uRect[8];
uniform float uRad[8];
uniform float uMerge;
uniform float uThick;
uniform float uDisp;
uniform float uFrost;
uniform float uForm;
uniform float uPress;
uniform float uScrim;      // 面板打开时对底层的压暗量
uniform float uTabA;       // 标签栏玻璃的残留量
uniform float uViewA;      // 卡片玻璃的残留量（面板升起时归零）
uniform vec3  uLight;

float sdRound(vec2 p, vec2 c, vec2 b, float r){
  vec2 q = abs(p-c) - b + vec2(r);
  return length(max(q,0.0)) + min(max(q.x,q.y),0.0) - r;
}
float smin(float a,float b,float k){
  float h = clamp(0.5+0.5*(b-a)/k,0.0,1.0);
  return mix(b,a,h) - k*h*(1.0-h);
}
vec2 centerOf(vec4 r){ return vec2(r.x+r.z*0.5, uCss.y-r.y-r.w*0.5); }
vec2 halfOf(vec4 r){ return vec2(r.z,r.w)*0.5; }

float heightOf(float d, float edge){
  float u = clamp(-d/edge, 0.0, 1.0);
  return pow(smoothstep(0.0,1.0,u), 0.55);
}
vec2 bend(vec3 N, vec3 I, float ior){
  vec3 T1 = refract(I, N, 1.0/ior);
  vec3 T2 = refract(T1, -N, ior);
  if (dot(T2,T2) < 1e-5) T2 = T1;
  return T1.xy/max(0.22,-T1.z) + T2.xy/max(0.22,-T2.z);
}
vec3 sampleBg(vec2 p){ return texture2D(uBg, clamp(p/uCss, vec2(0.002), vec2(0.998))).rgb; }

void main(){
  vec2 p = gl_FragCoord.xy/uDpr;
  vec3 col = sampleBg(p);

  // 投影：卡片(k=1..5)和常驻件(k=0/6/7)分开算，面板升起时卡片的投影一起退场，
  // 否则底下的内容已经透明了，还会留一圈"幽灵"阴影
  float dCard = 1e9, dMain = 1e9;
  for (int i=0;i<8;i++){
    if (uRect[i].z < 1.0) continue;
    float dd = sdRound(p, centerOf(uRect[i]), halfOf(uRect[i]), uRad[i]);
    if (i >= 1 && i <= 5) dCard = min(dCard, dd);
    else                  dMain = min(dMain, dd);
  }
  float dSh = min(dMain, mix(dCard, 1e9, 1.0-uViewA));
  float sh = 1.0 - smoothstep(-2.0, 30.0, max(dSh,0.0));
  float sh2 = 1.0 - smoothstep(-2.0, 86.0, max(dSh,0.0));
  col *= 1.0 - 0.200*sh - 0.012*sh2;

  /* 底栏的接触阴影单独收一下：它常压在白色卡片上，30px / 20% 的硬壳
     在纯白底上会变成一圈灰箍，和它压在自己页面背景上看完全两回事。
     这里把底栏那圈压暗补回去大半，只留一点点托底。 */
  if (uTabA > 0.001 && uRect[7].z > 1.0){
    float dT = sdRound(p, centerOf(uRect[7]), halfOf(uRect[7]), uRad[7]);
    float sT = 1.0 - smoothstep(-2.0, 30.0, max(dT,0.0));
    col *= 1.0 + 0.262*sT;
  }

  for (int k=0;k<8;k++){
    if (uRect[k].z < 1.0) continue;

    // 面板升起时：先把已经画好的卡片玻璃整体压暗，再让面板重新折射
    // （渲染顺序：背景 → 卡片 → 压暗层 → 面板 → 高光，避免"半透明白底"的塑料感）
    if (k==6 && uScrim > 0.001){
      float dS  = sdRound(p, centerOf(uRect[6]), halfOf(uRect[6]), uRad[6]);
      float outm = smoothstep(-6.0, 78.0, dS);
      col = mix(col, col*vec3(0.600,0.560,0.600), uScrim*(0.62+0.38*outm));
      col += vec3(0.012,0.008,0.010)*uScrim*(1.0-outm)*0.30;
    }

    float d = sdRound(p, centerOf(uRect[k]), halfOf(uRect[k]), uRad[k]);
    if (k==6 && uMerge > 0.001){
      float dTab = sdRound(p, centerOf(uRect[7]), halfOf(uRect[7]), uRad[7]);
      d = smin(d, dTab, uMerge*38.0);
    }
    if (k==7 && uMerge > 0.001) continue;
    if (d > 3.0) continue;

    float cov = 1.0 - smoothstep(-1.1, 1.1, d);
    if (k==7) cov *= uTabA;
    if (k>=1 && k<=5) cov *= uViewA;
    if (cov <= 0.001) continue;

    float edge = clamp(min(uRect[k].z,uRect[k].w)*0.16, 9.0, 30.0);
    float h = heightOf(d, edge);
    float dm = max(-d/edge, 0.0);
    float wOuter  = 1.0 - smoothstep(0.0,0.13,dm);
    float wInner  = smoothstep(0.05,0.28,dm)*(1.0-smoothstep(0.30,0.55,dm));
    float wCenter = smoothstep(0.42,0.85,dm);
    float zone = wOuter*0.45 + wInner*1.0 + wCenter*0.16;

    vec2 dh = vec2(dFdx(h), dFdy(h))*uDpr;
    float thick = uThick*(1.0+uPress*0.5);
    vec3 N = normalize(vec3(-dh*thick, 1.0));
    vec3 I = normalize(vec3((p-uCss*0.5)*0.0011, -1.0));

    float path = h*thick;
    float disp = uDisp*zone*uForm;
    vec2 offG = bend(N,I,1.505)*path*disp;
    vec3 rc;
    rc.r = sampleBg(p + bend(N,I,1.442)*path*disp).r;
    rc.g = sampleBg(p + offG).g;
    rc.b = sampleBg(p + bend(N,I,1.585)*path*disp).b;

    if (uFrost > 0.01 || k==7){
      // 底栏压在滚动内容上，需要更强的磨砂才能保证图标可读；
      // 面板保持低磨砂，让"看得见背景被掰弯"这件事成立
      float fr = k==7 ? 0.50 : (k==6 ? 0.24 : uFrost);
      vec2 r2 = vec2(1.9);
      vec3 bl = sampleBg(p+offG+vec2(r2.x,0.0)) + sampleBg(p+offG-vec2(r2.x,0.0))
              + sampleBg(p+offG+vec2(0.0,r2.y)) + sampleBg(p+offG-vec2(0.0,r2.y));
      bl += sampleBg(p+offG+vec2(r2.x,r2.y)) + sampleBg(p+offG-vec2(r2.x,r2.y))
          + sampleBg(p+offG+vec2(r2.x,-r2.y)) + sampleBg(p+offG-vec2(r2.x,-r2.y));
      rc = mix(rc, bl*0.125, fr*(1.0-wOuter*0.75));
    }

    vec3 absorb = vec3(1.0);   /* 浅色玻璃不靠吸收，靠接触阴影和纸边定义厚度 */
    vec3 body = rc*absorb;
    float lum = dot(body, vec3(0.2126,0.7152,0.0722));
    body = mix(body, vec3(lum), 0.07);
    body = body*0.905 + vec3(0.090,0.085,0.089);
    body = mix(body, body*vec3(1.005,0.988,1.015), 0.45);
    if (k==7) body = mix(body, vec3(0.995,0.992,0.997), 0.86);
    /* 顶部导航胶囊留一点通透，让粉雾透上来 */
    if (k==0) body = mix(body, rc, 0.40);
    /* 面板向参考稿靠：几乎实心白 + 压暗底层，不要"半透明白雾" */
    if (k==6) body = mix(body, vec3(0.996,0.993,0.996), 0.84);
    /* 内容卡改成接近实心白：玻璃只留导航和浮层 */
    if (k>=1 && k<=5) body = mix(body, vec3(0.998,0.997,0.999), 0.92);

    float pxIn = max(-d,0.0);
    vec2 nl = normalize(N.xy + vec2(1e-5));
    float side = 0.16 + 0.84*smoothstep(-0.9,0.95,dot(nl, normalize(uLight.xy)));

    float dark = exp(-pow((pxIn-3.8)/2.8,2.0));
    float cardW = (k>=1 && k<=5) ? 0.16 : ((k==0 || k==7) ? 0.40 : 1.0);
    body *= 1.0 - dark*0.26*cardW*(1.0-side*0.80);

    /* 浅色玻璃读的是"纸边"：外侧一根 1px 灰发丝，内侧压一道白光 */
    float line  = exp(-pow((pxIn-0.9)/1.0,2.0));
    float line2 = exp(-pow((pxIn-2.6)/1.4,2.0));
    float varr  = 0.55 + 0.45*(0.5+0.5*sin(dot(p,vec2(0.031,0.067))+uTime*0.35));
    float edgeW = (k==7 || k==0) ? 0.55 : 1.0;
    body *= 1.0 - line*0.18*edgeW;
    body += vec3(1.0,0.988,0.990)*line2*pow(side,1.55)*varr*0.50;

    vec3 Hv = normalize(vec3(uLight.xy,uLight.z)+vec3(0.0,0.0,1.0));
    body += vec3(1.0) * pow(max(dot(N,Hv),0.0),150.0)*0.50;
    body += vec3(0.90,0.86,0.94) * pow(1.0-clamp(N.z,0.0,1.0),3.0) * 0.05;

    col = mix(col, body, cov);
  }

  gl_FragColor = vec4(col,1.0);
}
`;
