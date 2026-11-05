"""从 FastAPI 的 OpenAPI 生成前端接口文档。

用法：
    uv run python scripts/generate_api_doc.py

输出：
    docs/API.md        给前端看的接口表
    docs/openapi.json  可导入 Apifox / Postman

接口定义直接从代码生成，不手写，避免文档和实现漂移。
"""

import json
import re
import sys
from pathlib import Path

# 让脚本直接运行时也能 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

spec = app.openapi()
components = spec.get("components", {}).get("schemas", {})
paths = spec.get("paths", {})

METHOD_ORDER = ["get", "post", "put", "patch", "delete"]


def ref_name(schema: dict) -> str | None:
    ref = schema.get("$ref")
    return ref.split("/")[-1] if ref else None


def render_type(schema: dict) -> str:
    """把 OpenAPI 的类型描述转成前端好读的字符串。"""
    if not schema:
        return "any"
    if "$ref" in schema:
        return ref_name(schema) or "object"

    if "anyOf" in schema:
        parts = [render_type(x) for x in schema["anyOf"] if x.get("type") != "null"]
        nullable = any(x.get("type") == "null" for x in schema["anyOf"])
        base = " | ".join(parts) or "null"
        return f"{base}?" if nullable else base

    t = schema.get("type")
    if t == "array":
        return f"{render_type(schema.get('items', {}))}[]"
    if t == "string":
        if schema.get("format") == "date-time":
            return "datetime"
        if schema.get("format") == "date":
            return "date"
        if schema.get("enum"):
            return " | ".join(f'"{v}"' for v in schema["enum"])
        return "string"
    if t == "integer":
        return "int"
    if t == "number":
        return "number"
    if t == "boolean":
        return "bool"
    if t == "object":
        return "object"
    return t or "any"


def unwrap_envelope(schema: dict) -> dict:
    """把 Envelope[T] 拆成 T，前端只关心 data 里的字段。"""
    if not schema:
        return {}
    if "$ref" in schema:
        resolved = components.get(ref_name(schema) or "", {})
        props = resolved.get("properties", {})
        if "data" in props:
            return props["data"]
        return schema
    props = schema.get("properties", {})
    if "data" in props:
        return props["data"]
    return schema


def field_rows(schema: dict) -> list[tuple[str, str, str]]:
    """把一个对象 schema 展开成 (字段, 类型, 必填) 列表。"""
    if "$ref" in schema:
        schema = components.get(ref_name(schema) or "", {})
    # data 字段是 T | None，OpenAPI 会生成 anyOf，取非 null 的分支
    if "anyOf" in schema:
        candidates = [x for x in schema["anyOf"] if x.get("type") != "null"]
        return field_rows(candidates[0]) if candidates else []
    if schema.get("type") == "array":
        item = schema.get("items", {})
        if "$ref" in item:
            return field_rows(item)
        return []
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    return [
        (name, render_type(prop), "是" if name in required else "否")
        for name, prop in props.items()
    ]


def first_line(text: str | None) -> str:
    if not text:
        return ""
    return text.strip().splitlines()[0].strip()


def cell(value: object) -> str:
    """转义 Markdown 表格里的竖线，避免枚举类型把表格拆坏。"""
    return str(value).replace("|", "\\|")


# ---------------------------------------------------------------- 错误码
APPERROR_RE = re.compile(
    r'AppError\(\s*"([^"]+)"\s*,\s*code=(\d+)\s*,\s*status_code=(\d+)',
    re.DOTALL,
)


def collect_error_codes() -> list[tuple[int, int, str, str]]:
    """从源码里扫描 AppError，生成错误码表。

    同一个 code 可能对应多条文案（例如 401），合并展示。
    """
    found: dict[int, tuple[int, set[str], str]] = {}
    for path in sorted((ROOT / "app").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for message, code, status in APPERROR_RE.findall(text):
            code_int = int(code)
            if code_int not in found:
                found[code_int] = (int(status), set(), str(path.relative_to(ROOT)))
            found[code_int][1].add(message)
    return [
        (code, status, " / ".join(sorted(messages)), source)
        for code, (status, messages, source) in sorted(found.items())
    ]


# ---------------------------------------------------------------- 生成
lines: list[str] = []
add = lines.append

add("# Cove 接口文档")
add("")
add("> 由 `scripts/generate_api_doc.py` 从代码自动生成，请勿手改。")
add("")
add("## 基础约定")
add("")
add("```")
add("Base URL: https://<你的域名>/api/v1")
add("鉴权:     Authorization: Bearer <access_token>")
add("编码:     application/json; charset=utf-8")
add("```")
add("")
add("### 统一响应结构")
add("")
add("```json")
add('{ "code": 0, "message": "success", "data": {} }')
add("```")
add("")
add("- `code = 0` 表示成功；非 0 时看 `message`")
add("- HTTP 状态码和 `code` 是两套体系：HTTP 表示传输层结果，`code` 是业务错误码")
add("")
add("### 认证流程")
add("")
add("1. `POST /auth/register` 或 `POST /auth/login` 拿到 `access_token` 和 `refresh_token`")
add("2. 之后每个请求带 `Authorization: Bearer <access_token>`")
add("3. `access_token` 默认 30 分钟过期，用 `POST /auth/refresh` 换新的一对令牌")
add("4. 刷新会轮换 `refresh_token`：旧值立即失效，客户端必须保存新值")
add("5. `POST /auth/logout` 吊销当前 refresh token；`POST /auth/logout-all` 吊销全部设备")
add("")
add("### 分页")
add("")
add("列表接口统一使用 `limit` + `offset`：")
add("")
add("- `limit` 默认 20 或 50，最大 100")
add("- `offset` 从 0 开始")
add("- 返回 `data` 是数组，没有额外的 total 字段")
add("")
add("### 权限")
add("")
add("- 除 `/auth/*` 外，全部接口都需要登录")
add("- 带「情侣」的接口还要求已绑定伴侣，否则返回 `code=3001`")
add("- 所有资源都会校验是否属于当前关系，跨关系访问返回 404")
add("")

# ---- 错误码
errors = collect_error_codes()
if errors:
    add("### 业务错误码")
    add("")
    add("| code | HTTP | 含义 |")
    add("|---:|---:|---|")
    for code, status, message, _source in errors:
        add(f"| {code} | {status} | {cell(message)} |")
    add("")
    add("> `429` 为限流；`500` 为未捕获异常，前端统一提示稍后重试。")
    add("")

# ---- 总览
add("## 接口总览")
add("")
add("| 模块 | 方法 | 路径 | 说明 | 鉴权 |")
add("|---|---|---|---|---|")
endpoint_rows = []
for path in sorted(paths):
    for method in METHOD_ORDER:
        op = paths[path].get(method)
        if not op:
            continue
        tag = (op.get("tags") or ["ops"])[0]
        # 优先用 docstring 的第一行（中文），FastAPI 自动生成的 summary 是函数名
        summary = first_line(op.get("description")) or op.get("summary") or ""
        secure = bool(op.get("security"))
        endpoint_rows.append((tag, method.upper(), path, summary, secure))

# 按模块聚合，保持首次出现的顺序
tag_order: list[str] = []
for tag, *_ in endpoint_rows:
    if tag not in tag_order:
        tag_order.append(tag)

for tag, method, path, summary, secure in endpoint_rows:
    add(
        f"| {tag} | {method} | `{path}` | {cell(summary)} | "
        f"{'是' if secure else '否'} |"
    )
add("")

# ---- 详情
add("## 接口详情")
add("")
for tag in tag_order:
    add(f"### {tag}")
    add("")
    for row in endpoint_rows:
        if row[0] != tag:
            continue
        _, method, path, summary, secure = row
        op = paths[path][method.lower()]

        add(f"#### `{method} {path}`")
        add("")
        if summary:
            add(summary)
            add("")

        # 路径 / 查询参数
        params = op.get("parameters", [])
        if params:
            add("**参数**")
            add("")
            add("| 位置 | 名称 | 类型 | 必填 |")
            add("|---|---|---|---|")
            for p in params:
                add(
                    f"| {p.get('in')} | `{p.get('name')}` | "
                    f"{cell(render_type(p.get('schema', {})))} | "
                    f"{'是' if p.get('required') else '否'} |"
                )
            add("")

        # 请求体
        body = op.get("requestBody", {}).get("content", {}).get("application/json", {})
        body_schema = body.get("schema", {})
        if body_schema:
            rows = field_rows(body_schema)
            if rows:
                add("**请求体**")
                add("")
                add("| 字段 | 类型 | 必填 |")
                add("|---|---|---|")
                for name, ftype, required in rows:
                    add(f"| `{name}` | {cell(ftype)} | {required} |")
                add("")

        # 响应 data
        ok = op.get("responses", {}).get("200", {})
        resp_schema = ok.get("content", {}).get("application/json", {}).get("schema", {})
        data_schema = unwrap_envelope(resp_schema)
        rows = field_rows(data_schema)
        if rows:
            add("**响应 data**")
            add("")
            add("| 字段 | 类型 | 必填 |")
            add("|---|---|---|")
            for name, ftype, required in rows:
                add(f"| `{name}` | {cell(ftype)} | {required} |")
            add("")
        else:
            add("**响应 data**：`null` / `object`（见实现）")
            add("")

        add("---")
        add("")

output_md = DOCS / "API.md"
output_md.write_text("\n".join(lines), encoding="utf-8")

output_json = DOCS / "openapi.json"
output_json.write_text(
    json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(f"written {output_md.relative_to(ROOT)}")
print(f"written {output_json.relative_to(ROOT)}")
print(f"endpoints: {len(endpoint_rows)}")
