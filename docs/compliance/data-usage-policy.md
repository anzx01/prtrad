# 数据使用政策

最后更新：2026-05-23

本文件说明本项目对 Polymarket 公共数据的使用方式与合规边界，**不构成法律意见**。

## 数据来源

本项目通过以下 Polymarket 公共 API 获取行情与市场元数据：

- **Gamma API**：`https://gamma-api.polymarket.com` —— 市场列表、事件元数据
- **CLOB API**：`https://clob.polymarket.com` —— 订单簿快照、成交、价格

接入参数集中在 `.env` 中通过 `POLYMARKET_GAMMA_API_URL`、`POLYMARKET_CLOB_API_URL`、`INGEST_HTTP_TIMEOUT_SECONDS`、`INGEST_GAMMA_PAGE_SIZE`、`INGEST_CLOB_BATCH_SIZE` 等配置控制。

## 使用方式

- **用途**：本项目仅用于个人研究、教育、风险监控、回测与影子验证。
- **不进行**：数据公开转售、面向第三方的实时行情分发、爬取受认证保护的非公开端点、规避 API 速率限制。
- **速率与缓存**：通过 `INGEST_MARKET_SYNC_INTERVAL_SECONDS`、`INGEST_SNAPSHOT_INTERVAL_SECONDS` 等配置控制采集频率，使用本地 SQLite/PostgreSQL 缓存避免重复请求。
- **采集范围**：仅采集 Polymarket 公开 API 返回的字段；不主动采集用户钱包地址、交易者身份、社交账号等可能涉及第三方个人信息的数据。

## 合规边界

使用者在部署或运行本项目时，需自行承担以下合规义务：

1. **遵守 Polymarket 服务条款**：参考 Polymarket 官方 ToS（`https://polymarket.com/tos`）与 API 使用政策。若官方政策更新，使用者应及时调整本项目的采集频率、字段范围与使用目的。
2. **地域限制**：Polymarket 对部分司法辖区的用户（包括但不限于美国用户）禁止访问与交易。使用者应自行确认所在地区的合法性。
3. **数据再分发限制**：若使用者要将本项目采集的数据公开发布（论文、博客、可视化、报告），应核查 Polymarket 的数据再分发条款；本项目作者不对使用者的再分发行为承担责任。
4. **个人信息保护**：若使用者在本项目基础上接入额外数据源（如社交媒体、链上地址聚类），应自行评估 GDPR / CCPA / 《个人信息保护法》等适用法律的合规义务。
5. **金融监管合规**：参与 Polymarket 是否构成证券交易、衍生品交易或博彩，因司法辖区而异。使用者应自行咨询本地法律意见。

## 撤回与删除

- 本项目仅在本地存储数据，未将数据上传至任何作者控制的第三方服务。
- 如需删除本地数据，删除 `.env` 中 `DATABASE_URL` 指向的数据库文件即可。
- 若 Polymarket 官方要求停止采集或删除特定字段，使用者应立即调整本地部署。

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-05-23 | 初始版本 |
