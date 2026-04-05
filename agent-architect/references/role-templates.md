# Agent 角色模板参考

## 通用角色

### 1. Planner（规划器）
- **职责**：理解用户意图，拆解任务，分配子任务
- **输入**：用户自然语言指令
- **输出**：结构化任务列表
- **失败处理**：无法解析时回退到追问澄清
- **超时**：5 秒

### 2. Executor（执行器）
- **职责**：执行具体操作（调用 API、写文件、发消息等）
- **输入**：结构化指令
- **输出**：操作结果
- **失败处理**：停止并告警
- **超时**：10 秒（关键操作）

### 3. Reviewer（审查器）
- **职责**：验证 Executor 的输出是否符合预期
- **输入**：执行结果 + 验收标准
- **输出**：PASS/FAIL + 修改建议
- **失败处理**：返回 FAIL 后由 Planner 决定重试或放弃
- **超时**：10 秒

---

## 数据型场景角色

### 4. Fetcher（采集器）
- **职责**：从外部获取原始数据
- **输出 schema**：`{raw_data, source, timestamp, status}`
- **失败处理**：3 次重试（指数退避 1s/2s/4s）后记录错误并告警
- **超时**：30 秒

### 5. Parser（解析器）
- **职责**：清洗和解析原始数据，提取结构化信息
- **输入**：Fetcher 的 raw_data
- **输出 schema**：`{structured_data, quality_score, rejected_count}`
- **失败处理**：低质量数据标记后跳过，不阻塞流程
- **超时**：30 秒

### 6. Storage（存储器）
- **职责**：将结构化数据持久化
- **输入**：解析后的结构化数据
- **输出 schema**：`{storage_path, record_count, checksum}`
- **失败处理**：重试 2 次后切换备用存储路径
- **超时**：10 秒

### 7. Scheduler（调度器）
- **职责**：管理定时触发和运行状态
- **输出 schema**：`{next_run, schedule, status}`
- **失败处理**：保持上一次运行状态，不主动改变
- **超时**：5 秒

---

## 交易型场景角色

### 8. Analyzer（分析师）
- **职责**：基于数据给出分析结论和建议
- **输出 schema**：`{analysis, confidence, evidence[], timestamp, status}`
- **失败处理**：低置信度时升级到人工审核
- **超时**：60 秒

### 9. Risk Controller（风控器）
- **职责**：评估交易风险，一票否决权
- **输出 schema**：`{approved, risk_level, conditions[], status}`
- **失败处理**：默认拒绝（fail-safe）
- **超时**：5 秒

---

## 报告型场景角色

### 10. Formatter（格式化器）
- **职责**：将分析结果渲染成目标格式
- **输入**：Analyzer 输出 + 模板定义
- **输出 schema**：`{rendered_content, format, size_bytes}`
- **失败处理**：降级到纯文本格式
- **超时**：15 秒

### 11. Deliverer（推送器）
- **职责**：将报告送达指定渠道
- **输出 schema**：`{report, format, delivered_to[], status}`
- **失败处理**：重试 2 次后切换备用渠道（主:飞书 → 备:邮件）
- **超时**：15 秒

---

## 客服型场景角色

### 12. Intent Classifier（意图分类器）
- **职责**：识别用户问题的意图类型
- **输出 schema**：`{intent, confidence, entities{}, fallback_flag}`
- **失败处理**：fallback_flag=true 时转人工

### 13. Knowledge Retriever（知识检索器）
- **职责**：从知识库检索相关信息
- **输出 schema**：`{relevant_docs[], relevance_scores[], source}`
- **失败处理**：降级到 FAQ 兜底

### 14. Escalation（升级器）
- **职责**：管理需要人工介入的转接流程
- **输出 schema**：`{escalated_to, reason, priority, ticket_id}`
- **失败处理**：记录升级失败并告警
- **超时**：5 秒
