# llm_api · 个人 LLM 网关

一个 OpenAI 兼容的本地大模型网关：用一个统一端点接入多家模型（国产直连 + OpenRouter 等），
做多 key 轮询、故障转移、用量记录。**首要目标：解决自己"低成本用 AI 编码"的痛点。**

> 说明：开源生态里 [new-api](https://github.com/Calcium-Ion/new-api)（Go，~29k★）已是开箱即用的成熟方案。
> 本仓是**自研最小版**，用于自用 + 练手 + 作为将来"加密货币充值的合法增值网关"的底子。
> 只想立刻能用、功能全 → 直接部署 new-api 即可。

## 能力
- OpenAI 兼容 `POST /v1/chat/completions`（流式 + 非流式）
- 配置驱动多渠道：按模型名路由（精确 / 前缀 `claude-*` / 通配 `*` 兜底）
- 同渠道多 key 轮询 + 失败自动重试（429/5xx 换 key、换渠道）
- `model_map` 别名：把好记的短名（如 `claude`）映射到上游真实 slug
- **多用户**：在后台为每个朋友创建独立令牌，可设 token 配额、随时启停
- **后台管理**：`/admin` 网页面板 + REST 接口，管理令牌、查看按人/按渠道用量
- 用量写入 SQLite

## 角色与密钥
| 角色 | 用什么 | 能做什么 |
|---|---|---|
| 管理员(你) | `ADMIN_KEY` | 进 `/admin` 后台，增删/启停令牌、看用量 |
| owner(你自己调用) | `GATEWAY_KEY` | 调用网关，免配额 |
| 朋友 | 后台生成的 `sk-...` 令牌 | 调用网关，受启停 + 配额限制 |

## 快速开始（本地自用）
```bash
cp .env.example .env          # 填 GATEWAY_KEY 和你有的上游 key
cp config.example.yaml config.yaml
bash run.sh                   # 首次会自动建 venv、装依赖
```
默认监听 `http://127.0.0.1:8080`。健康检查：`curl localhost:8080/healthz`

## 在 Cursor / Cline / Aider 里使用
把工具的 OpenAI 配置改成：
- Base URL: `http://127.0.0.1:8080/v1`
- API Key: 你在 `.env` 里设的 `GATEWAY_KEY`
- Model: `deepseek-chat`（日常）/ `claude`（攻坚，经 OpenRouter）等

调用示例：
```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Authorization: Bearer $GATEWAY_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hello"}]}'
```

## 配置说明（config.yaml）
- 每个 `channel`：`base_url` + `api_keys`（支持多个，轮询）+ `models`（该渠道支持的模型）。
- `api_keys` 为空的渠道**自动禁用**，所以只填你有 key 的即可。
- `${VAR}` 从环境变量 / `.env` 读取，密钥不写进文件、不进 git。
- 路由优先级：精确匹配 → 前缀匹配 → 通配 `*` 兜底。

## 文档
- [docs/本地部署与使用全流程.md](docs/本地部署与使用全流程.md) — 从零到用上，7 步完整流程（先看这个）
- [docs/对接使用.md](docs/对接使用.md) — 发给朋友的对接说明（Cursor/Cline/curl/Python）
- [docs/准备清单.md](docs/准备清单.md) — 本地 / 上服务器分别要准备什么
- [FEATURES.md](FEATURES.md) — 功能清单与市场对比

## 给朋友一起用（多用户 + 后台）
1. 启动后打开后台：`http://127.0.0.1:8080/admin`
2. 输入 `ADMIN_KEY`，点"保存并刷新"
3. 在"新增朋友令牌"里填名称（可选配额，单位 token），点创建
4. 把生成的 `sk-...` 发给朋友，让他们在自己的 Cursor/Cline 里：
   - Base URL: `http://你的服务器:8080/v1`
   - API Key: 你发的那个 `sk-...`
5. 后台可随时：启停某人、查看每个人用了多少 token、按渠道统计

后台接口（也可直接用 API）：
```
GET    /admin/tokens          列出令牌
POST   /admin/tokens          创建 {name, quota_tokens?, note?}
PATCH  /admin/tokens/{id}     {enabled?, quota_tokens?}
DELETE /admin/tokens/{id}     删除
GET    /admin/usage           按人/按渠道用量 + 最近记录
```
全部需 `Authorization: Bearer <ADMIN_KEY>`。

## 测试
```bash
.venv/bin/python -m pytest -q
```
测试用内置的假上游做端到端验证（无需真实 key/网络），覆盖：路由、鉴权、流式、故障转移、model_map、模型列表。

## 部署到服务器（如阿里云）
```bash
# 服务器上
cp .env.example .env && vi .env          # 务必设置强随机 GATEWAY_KEY
cp config.example.yaml config.yaml
docker compose up -d --build
```
⚠️ **安全红线**：给朋友用 / 上服务器，**必须**设置 `ADMIN_KEY` 和 `GATEWAY_KEY`（强随机值），否则后台和上游 key 等于对全网裸奔。
建议再加：Nginx + HTTPS + 限流；后台 `/admin` 加 IP 白名单；不要公开转售（涉及备案、上游授权、税务等合规义务）。

## 路线图（孵化方向，见 frank-ai-sidehustle/library）
- [ ] prompt 缓存命中统计 / 成本估算
- [ ] 加密货币充值与按量计费（合法差异化的核心）
- [ ] Anthropic 原生协议转换（当前 Claude 走 OpenRouter 的 OpenAI 兼容口）
- [ ] 简单 Web 面板
