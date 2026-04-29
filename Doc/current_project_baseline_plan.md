# 当前项目 BaseLine 规划文档

## 1. BaseLine 的定位

BaseLine 不是 Base Layer。

- Base Layer：系统通用底座，长期稳定存在。
- BaseLine：当前项目在当前 Run 中的临时目标、验收标准、评估计划和优化优先级。

BaseLine 的作用是让系统在不需要用户手工写项目基线的前提下，仍然能够明确：

- 当前项目要做什么
- 当前项目最少做到什么程度算完成
- 当前项目先做什么、后做什么
- 当前项目如何判断优化是否有效

因此，本项目需要实现的是：

**自动生成项目级临时 BaseLine。**

---

## 2. 为什么需要 BaseLine

如果没有 BaseLine，系统会出现三个问题：

1. 不知道什么叫完成。
2. 不知道现在是变好了还是变差了。
3. 不知道什么时候该优化，什么时候该停止。

所以本项目不采用“完全无基线”模式，而采用：

**通用 Base Layer + 自动生成项目 BaseLine**

---

## 3. BaseLine 的目标

当前项目的 BaseLine 需要完成以下功能：

1. 自动识别项目类型。
2. 自动拆出核心模块。
3. 自动生成最小验收标准。
4. 自动生成第一轮评估计划。
5. 自动生成优化优先级。
6. 自动生成推荐技术路线。
7. 作为当前 Run 的执行依据。

---

## 4. BaseLine 由谁生成

由 Supervisor 调用 `Baseline Generator` 自动生成。

输入：

- 用户项目目标
- 当前工作区状态
- 当前可用 Base tools / skills / mcp adapters
- 可选历史经验

输出：

- `baseline.json`

Supervisor 在生成 BaseLine 后，再开始调度 Delivery Worker 和 QA Worker。

---

## 5. BaseLine 应该包含什么

第一版 BaseLine 不宜过重，建议包含以下字段：

### 5.1 基本信息

- run_id
- project_name
- project_type
- goal
- scope

### 5.2 模块拆分

- core_modules
- optional_modules

### 5.3 最小验收标准

- minimum_acceptance

### 5.4 评估计划

- evaluation_plan

### 5.5 优化优先级

- optimization_priority

### 5.6 推荐实现路线

- suggested_stack
- suggested_execution_order

### 5.7 停止条件

- stop_conditions

---

## 6. BaseLine 的第一版结构建议

```json
{
  "run_id": "run_001",
  "project_name": "demo_rag_system",
  "project_type": "rag",
  "goal": "Build a usable RAG system from scratch",
  "scope": "Demo-first, end-to-end runnable",
  "core_modules": [
    "document_ingestion",
    "parsing",
    "chunking",
    "indexing",
    "retrieval",
    "generation",
    "evaluation"
  ],
  "optional_modules": [
    "reranking",
    "multi-query retrieval",
    "feedback loop"
  ],
  "minimum_acceptance": [
    "documents can be ingested",
    "text can be parsed",
    "chunks can be created",
    "index can be built",
    "retrieval returns relevant context",
    "generation uses retrieved context",
    "end-to-end pipeline runs successfully"
  ],
  "evaluation_plan": {
    "parse": [
      "parse_success_rate",
      "content_loss_check"
    ],
    "chunk": [
      "chunk_length_distribution",
      "coverage_check"
    ],
    "retrieval": [
      "hit_rate_at_k",
      "recall_at_k"
    ],
    "generation": [
      "groundedness_check",
      "citation_presence"
    ]
  },
  "optimization_priority": [
    "make the pipeline runnable",
    "improve retrieval quality",
    "improve answer faithfulness",
    "improve efficiency"
  ],
  "suggested_stack": {
    "language": "Python",
    "embedding": "configurable",
    "vector_store": "adapter-based",
    "llm": "adapter-based"
  },
  "suggested_execution_order": [
    "ingestion",
    "parsing",
    "chunking",
    "indexing",
    "retrieval",
    "generation",
    "evaluation"
  ],
  "stop_conditions": [
    "minimum acceptance passed",
    "two optimization rounds with no meaningful gain",
    "manual stop"
  ]
}
```

---

## 7. 当前项目中 BaseLine 应该实现什么功能

### 7.1 任务识别功能
作用：

- 识别当前任务属于哪类项目。
- 将项目映射到合适的模块集合。

第一版建议支持：

- rag
- web_app
- script_or_tooling

当前项目优先支持：

- rag

### 7.2 模块识别功能
作用：

- 自动识别该项目需要哪些核心模块。

对于 RAG，建议输出：

- ingestion
- parsing
- chunking
- indexing
- retrieval
- generation
- evaluation

### 7.3 最小验收标准生成功能
作用：

- 告诉系统先做到什么程度算“第一版完成”。

例如 RAG：

- 能导入文档
- 能解析文本
- 能完成 chunk
- 能建索引
- 能检索相关内容
- 能基于检索结果回答
- 能跑通端到端链路

### 7.4 评估计划生成功能
作用：

- 让 QA Worker 有固定基础尺子可用。

建议分模块输出：

- parse 评估
- chunk 评估
- retrieval 评估
- generation 评估

### 7.5 优化优先级生成功能
作用：

- 避免系统一开始乱优化。

RAG 第一版建议优先级：

1. 先跑通
2. 再提升召回
3. 再提升回答可靠性
4. 最后考虑效率

### 7.6 停止条件功能
作用：

- 防止系统无限优化。

建议默认停止条件：

- 已达到 minimum_acceptance
- 连续两轮优化无明显提升
- 人工中止

---

## 8. BaseLine 的实现方式

### 8.1 实现模块
需要新增：

- `app/core/baseline_generator.py`
- `app/schemas/baseline_schema.py`

### 8.2 生成逻辑
建议流程：

1. Supervisor 接收用户目标。
2. 读取当前可用 Base capabilities。
3. 调用 Baseline Generator。
4. 由模型输出结构化 baseline。
5. 使用 Pydantic 校验。
6. 写入 `runs/<run_id>/baseline.json`。
7. Supervisor 基于 baseline 开始计划与调度。

### 8.3 输出方式
第一版推荐：

- LLM 负责生成
- Pydantic 负责校验
- JSON 文件负责持久化

### 8.4 错误处理
如果 baseline 输出不合格：

- 自动重试一次
- 若仍不合格，则回退到默认模板

默认模板不要太复杂，只保留：

- project_type
- core_modules
- minimum_acceptance
- evaluation_plan
- optimization_priority

---

## 9. BaseLine 与 Worker 的关系

### 9.1 Supervisor 使用 BaseLine
Supervisor 根据 BaseLine：

- 生成当前 Run 计划
- 分阶段调度 Worker
- 判断当前目标是否完成
- 决定下一步是继续、优化还是触发能力进化

### 9.2 Delivery Worker 使用 BaseLine
Delivery Worker 根据 BaseLine：

- 实现当前模块
- 按建议顺序推进
- 明确当前阶段目标

### 9.3 QA Worker 使用 BaseLine
QA Worker 根据 BaseLine：

- 执行当前阶段评估
- 对照 minimum_acceptance 判断是否达标
- 对照 evaluation_plan 输出质量报告

### 9.4 Capability Worker 使用 BaseLine
Capability Worker 间接受到 BaseLine 影响：

- 当前问题若只是未达标，不一定需要新能力
- 只有 QA / Delivery 判断出现“能力缺口”时，才触发新能力生成

---

## 10. BaseLine 在 RAG Demo 中的具体落地

### 10.1 输入
用户输入：

“从零开始搭建一个 RAG 系统，支持文档导入、检索和回答，并持续优化效果。”

### 10.2 BaseLine 需要自动生成的内容

- 项目类型：rag
- 模块：解析、分块、索引、召回、生成、评估
- 最小验收：端到端链路跑通
- 第一轮评估：解析成功率、召回命中率、回答 groundedness
- 优化优先级：先可用、再召回、再生成

### 10.3 基于 BaseLine 的执行路线

第一轮：

- Delivery Worker 先实现最小链路

第二轮：

- QA Worker 评估结果

第三轮：

- 如果只是参数问题，直接改
- 如果是能力缺口，调用 Capability Worker 生成新 Tool/Skill

第四轮：

- 用新能力继续优化

第五轮：

- 达标后 snapshot 与 reset

---

## 11. BaseLine 与能力进化的关系

核心原则：

- BaseLine 先定义当前项目“做成什么样”。
- Evolution Layer 再负责补足“现有能力做不到的地方”。

也就是说：

- BaseLine 决定目标和尺子。
- Evolution 决定当前项目里是否要造新工具。

如果没有 BaseLine，进化会失去方向。  
如果没有 Evolution，BaseLine 会停留在纸面。

---

## 12. 当前项目中 BaseLine 的最小实现范围

当前阶段不要过度设计，建议只做：

1. 一个 `BaselineSchema`
2. 一个 `BaselineGenerator`
3. 一个 `baseline.json` 写入逻辑
4. 一个 Supervisor 对 baseline 的读取逻辑
5. 一个 QA 对 baseline 的使用逻辑

先不要做：

- 太复杂的 baseline 版本管理
- 太复杂的 baseline 自我修订链
- 多项目类型的大规模模板库

---

## 13. 最终建议

当前项目的 BaseLine 实现目标应当是：

**让系统在没有人工预先手写项目基线的情况下，仍然能够自动生成一个足够稳定、足够轻量、能驱动当前项目开发与评估的临时基线。**

对于第一版来说，BaseLine 最重要的不是“完整”，而是：

- 结构清晰
- 能驱动开发
- 能驱动评估
- 能限制无序优化
- 能为能力进化提供方向

因此，当前项目最合适的 BaseLine 策略是：

**轻量、结构化、自动生成、当前 Run 有效、可落盘、可进入 snapshot。**
