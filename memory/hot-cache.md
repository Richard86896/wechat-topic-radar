# wechat-topic-radar · 跨会话记忆 hot-cache

> 每次执行选题前必须读取本文件。执行完毕后若有新决策/升级，追加到"决策记录"。
> 格式：`YYYY-MM-DD | 决策内容 | 来源`

---

## 当前生效决策

| 日期 | 决策 | 状态 |
|---|---|---|
| 2026-05-12 | NewsNow 过载/D1_ERROR 时，立即切换 aihot fallback：`curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&since=24h"`，必须带 UA，否则 403 | ✅ 已写入 SKILL.md |
| 2026-05-12 | 选题报告保存路径：`04.选题决策/每日选题/YYYYMMDD-每日选题.md` | ✅ 已写入 SKILL.md |
| 2026-05-12 | 最终推荐默认只输出 3 个，不是 TOP10 | ✅ 已写入 SKILL.md |

---

## 决策记录（完整历史）

### 2026-05-12
- **aihot 作为 NewsNow fallback 数据源**：用户确认，已写入 SKILL.md 并 git commit（commit: 3084ac2）
- **触发背景**：NewsNow D1_ERROR 过载，之前 session 没有正确执行写入，导致规则丢失
- **教训**：每次 session 后若有升级决策，必须写入本文件 + 确认文件已落盘

---

## 待处理 / 开放循环

- [ ] 验证 aihot fallback 在下次选题时是否被正确调用
