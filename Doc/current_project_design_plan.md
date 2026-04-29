# 当前项目设计规划文档

## 1. 项目概述

### 1.1 项目名称
可进化 Coding Agent Demo

### 1.2 项目目标
构建一个以 CLI 为入口的代码型智能体系统。系统能够围绕“完成一个项目开发任务”展开工作，具备以下核心能力：

- 能基于用户目标自动生成当前项目的临时 BaseLine。
- 能调用基础 Tools、Skills、MCP 接口位完成项目开发。
- 能在开发过程中发现能力缺口，并按需生成新的 Tool 或 Skill。
- 新能力必须经过测试和人工审核后，才能注册到当前任务的 Evolution Layer。
- 项目完成后，能够生成快照、归档当前任务进化成果，并将运行环境重置回 Base Layer。

### 1.3 项目边界
本项目当前阶段是 Demo，不追求一次性做成完整平台，重点验证以下闭环：

1. 用户输入项目目标。
2. Supervisor 自动生成项目级临时 BaseLine。
3. 多 Worker 协作开发项目。
4. 发现能力缺口时生成候选能力。
5. 完成测试、人工审核、注册、继续执行。
6. 项目通过验证后生成 snapshot 并 reset。

本阶段不重点实现：

- 真正复杂的多租户系统。
- 自动生成复杂 MCP 服务。
- 完整的云端沙箱治理体系。
- 团队协作后台、权限中心、可视化控制台。

---

## 2. 产品定位

### 2.1 产品定位
这是一个“支持任务内能力进化”的 Coding Agent 系统，而不是一个永久污染环境、持续叠加能力的自治体。

### 2.2 核心理念

- Base Layer 永远保持稳定、可重置。
- 当前项目需要的能力在当前 Run 内进化。
- 进化成果先测试、再审核、再注册。
- 项目完成后保留快照与经验，不保留脏运行态。

### 2.3 典型使用场景

- 从零开发一个 RAG 系统。
- 从零开发一个小型 Web 应用。
- 从零开发一个自动化脚本/工具型项目。
- 在已有项目中自动补模块、补测试、补评估。

---

## 3. 当前阶段的总体交付目标

### 3.1 第一阶段交付目标
完成一个可运行的 Demo，支持以下能力：

- CLI 启动任务。
- 自动生成项目临时 BaseLine。
- 调用 Delivery Worker 实现项目初版。
- 调用 QA Worker 做阶段评估。
- 遇到能力缺口时调用 Capability Worker 生成候选能力。
- 候选能力进入 Sandbox 测试。
- 人工审核后注册到 Evolution Layer。
- 能对当前任务进行 snapshot 和 reset。

### 3.2 第一阶段验收标准

- 能从命令行启动一个项目任务。
- 能生成结构化 baseline.json。
- 能完成至少一种项目类型的端到端闭环，优先支持 RAG。
- 能在至少一个场景中验证“进化新工具并继续完成任务”。
- 能生成 snapshot 目录及元数据文件。
- 能 reset 回 Base Layer 状态。

---

## 4. 总体架构设计

### 4.1 架构结论
采用：

- 单 Supervisor Agent
- 多 Worker
- Supervisor-led Plan-and-Execute

### 4.2 架构说明

- 单：只有一个总控 Agent 掌握全局状态和最终决策权。
- Supervisor：负责计划、调度、审核、回退、snapshot、reset。
- 多 Worker：负责不同类型的具体执行工作。
- Plan-and-Execute：先围绕当前 Run 生成计划，再逐步执行和修正。

### 4.3 设计原因
选择该架构的原因：

- 比纯单 Agent 更不容易上下文混乱。
- 比平权多 Agent 更容易保持全局状态一致。
- 适合项目级任务，而不只是单次工具调用。
- 便于插入能力测试、人工审核、快照和重置链路。

---

## 5. 核心角色与职责

### 5.1 Supervisor Agent
职责：

- 接收用户目标。
- 自动识别项目类型。
- 自动生成当前项目的临时 BaseLine。
- 构建当前 Run 计划。
- 调度 Worker。
- 汇总 Worker 结果。
- 决定是否继续、回退、优化、结束。
- 决定是否触发能力进化。
- 发起人工审核。
- 决定是否注册新能力。
- 触发 snapshot 和 reset。

### 5.2 Delivery Worker
职责：

- 初始化项目结构。
- 写代码、改代码、连通模块。
- 运行当前步骤。
- 在无法继续时输出结构化 Gap Report。

### 5.3 QA Worker
职责：

- 执行项目测试。
- 执行模块评估。
- 输出质量报告。
- 比较优化前后差异。
- 判断当前阶段是否达标。

### 5.4 Capability Worker
职责：

- 根据 Gap Report 生成新的 Tool 或 Skill 候选能力。
- 生成 manifest、实现文件、测试样例、使用说明。
- 不直接注册。

### 5.5 Research Worker
职责：

- 调研外部资料。
- 阅读文档。
- 输出技术建议、方案比较、问题说明。

说明：Research Worker 可作为第二阶段增强项，第一版不是必须。

---

## 6. 分层设计

### 6.1 Base Layer
作用：

- 提供稳定的基础 Tools。
- 提供稳定的基础 Skills。
- 预留 MCP 接口能力。
- 提供可重置的基础执行环境。

特点：

- 不随当前任务变化。
- 不允许被任务运行态直接污染。

### 6.2 Project Baseline Layer
作用：

- 由 Supervisor 为当前项目自动生成临时基线。
- 明确本次项目的核心模块、最小验收标准、评估计划、优化优先级。

特点：

- 属于当前 Run。
- 会进入 snapshot。
- 不等同于 Base Layer。

### 6.3 Evolution Layer
作用：

- 存放当前 Run 内新生成并审核通过的 Tools、Skills、MCP Adapters。

特点：

- 当前任务临时生效。
- 任务结束后 reset。
- 快照保留，但运行态不继承到下次任务。

### 6.4 System Services Layer
作用：

- Registry Service
- Sandbox Service
- Snapshot Service
- Reset Service
- State Service
- Approval Service
- Memory Service

特点：

- 这层是确定性服务，不做成 Agent。

---

## 7. 功能设计

### 7.1 项目立项与任务接收
输入：

- 用户目标描述。
- 目标仓库路径或空工作区。
- 项目类型提示，可选。

输出：

- 新的 Run ID。
- 当前任务目录。
- 初始化状态文件。

### 7.2 自动生成 Project Baseline
输入：

- 用户目标
- 当前可用 Base capabilities
- 现有项目上下文
- 可选历史经验

输出：

- 项目类型
- 核心模块拆分
- 最小验收标准
- 第一轮评估计划
- 优化优先级
- 推荐技术路线

### 7.3 项目开发执行
包括：

- 项目目录初始化
- 依赖文件初始化
- 业务代码开发
- 测试文件创建
- 配置文件补齐
- 命令入口封装

### 7.4 项目评估与优化
包括：

- 阶段性测试
- 关键指标记录
- 质量报告输出
- 问题优先级排序
- 优化轮次推进

### 7.5 能力进化
流程：

1. Delivery Worker 卡住。
2. Supervisor 判断是 Bug、策略问题还是能力缺口。
3. 如果是能力缺口，生成 Gap Report。
4. Capability Worker 生成候选能力。
5. Sandbox 测试能力。
6. QA 输出测试结论。
7. 人工审核。
8. Registry 注册到 Evolution Layer。
9. Delivery Worker 继续执行。

### 7.6 快照与重置
项目完成后：

- 生成当前 Run 的 snapshot。
- 打包当前业务代码、baseline、reports、evolution。
- 记录 snapshot manifest。
- 清空 Evolution Layer。
- 恢复到 Base Layer。

---

## 8. 技术选型

### 8.1 编程语言
选择 Python 3.11+

原因：

- 生态成熟。
- 适合快速构建 Agent 系统和工具系统。
- 便于处理脚本执行、文件、测试、模板、schema。

### 8.2 CLI
选择 Typer

原因：

- 开发效率高。
- 命令结构清晰。
- 与 Python 工程兼容性好。

### 8.3 数据结构与校验
选择 Pydantic v2

原因：

- 非常适合定义 baseline、manifest、gap report、run state。
- 便于结构化输出校验。

### 8.4 测试框架
选择 pytest

原因：

- 简单稳定。
- 易于集成到 QA 和 Sandbox 流程。

### 8.5 CLI 展示
选择 rich

原因：

- 方便输出状态、审核摘要、进度和报告。

### 8.6 模板能力
选择 jinja2

原因：

- 适合生成 Tool/Skill 模板文件。

### 8.7 工作流编排
第一版采用手写状态机，不强依赖 LangGraph。

原因：

- 更容易调试。
- 更容易控制状态落盘。
- 更适合先验证进化闭环。

### 8.8 沙箱
第一版采用受控本地子进程执行。

第二阶段再考虑：

- Docker
- e2b

---

## 9. 工程目录设计

```text
project_root/
  app/
    cli/
      main.py
    core/
      supervisor.py
      baseline_generator.py
      planner.py
      dispatcher.py
    workers/
      delivery_worker.py
      qa_worker.py
      capability_worker.py
      research_worker.py
    services/
      registry_service.py
      sandbox_service.py
      snapshot_service.py
      reset_service.py
      state_service.py
      memory_service.py
      approval_service.py
    tools/
      tool_runtime.py
      tool_loader.py
      builtins/
    skills/
      skill_loader.py
      prompts/
    schemas/
      capability_manifest.py
      skill_manifest.py
      baseline_schema.py
      gap_report.py
      test_report.py
      run_state.py
      approval_record.py
      snapshot_manifest.py
    utils/
      fs.py
      json_io.py
      hashing.py
      logger.py
      subprocess_runner.py
  base/
    tools/
    skills/
    mcp/
    registry/
  runs/
    run_001/
      baseline.json
      state.json
      workspace/
      evolution/
        tools/
        skills/
        mcp/
        registry/
      reports/
      snapshots/
      logs/
  templates/
    capability_tool/
    capability_skill/
  tests/
    unit/
    integration/
    fixtures/
  docs/
  pyproject.toml
  README.md
```

---

## 10. Base Layer 设计

### 10.1 Base Tools
第一版建议至少具备：

- 文件读写与修改
- 目录扫描
- 代码搜索
- shell 执行
- 测试运行
- CSV / JSON 读写
- HTTP 请求
- 压缩打包
- 日志记录
- schema 校验
- LLM 调用适配
- 向量索引适配接口

### 10.2 Base Skills
第一版建议具备：

- 任务拆解
- Baseline 生成
- Debug / 排错
- 测试优先检查
- 缺口分析
- 评估报告总结
- 新能力生成提示模板
- 新能力测试提示模板
- 人工审核摘要模板
- snapshot 总结模板

### 10.3 Base MCP
第一版策略：

- 保留接口位
- 允许接已有 MCP
- 不把核心闭环依赖压在 MCP 上
- 暂不做 MCP 自进化

---

## 11. 项目级执行设计

### 11.1 Run 生命周期

1. 创建 Run。
2. 生成 baseline.json。
3. 生成当前计划。
4. 执行当前阶段。
5. 评估结果。
6. 必要时触发能力进化。
7. 重复执行与优化。
8. 达标后 snapshot。
9. reset。
10. 结束 Run。

### 11.2 计划与状态
建议状态字段至少包括：

- run_id
- mission_goal
- current_phase
- current_step
- baseline_path
- available_capabilities
- pending_approvals
- snapshots
- evaluation_summary
- completion_status

### 11.3 能力治理规则

- Worker 不直接写全局 registry。
- 所有能力注册必须经 Supervisor 驱动。
- 所有新能力必须先测试。
- 所有新能力必须人工审核。
- 所有新能力默认只在当前 Run 生效。

---

## 12. RAG 作为首个 Demo 的设计建议

### 12.1 为什么选择 RAG

- 链路完整，适合验证系统规划能力。
- 包含解析、分块、召回、生成、评估多个模块。
- 容易暴露“能力缺口”，适合验证能力进化闭环。

### 12.2 第一版 RAG 的最小功能

- 文档导入
- 文本解析
- 文本分块
- 建立索引
- 问题检索
- 基于检索结果生成回答
- 最小评估脚本

### 12.3 RAG 第一版验收目标

- 能跑通端到端链路。
- 能在简单测试数据上完成检索问答。
- 能产生结构化评估输出。
- 能在至少一个模块中触发能力进化。

---

## 13. 开发阶段规划

### Phase 1：项目骨架

- 初始化仓库
- 建目录结构
- 建 CLI
- 建 schemas
- 建 run 初始化逻辑

### Phase 2：Supervisor 闭环

- 实现 Supervisor 状态机
- 实现 Baseline Generator
- 实现 Delivery Worker
- 实现 QA Worker

### Phase 3：能力进化闭环

- 实现 Registry Service
- 实现 Capability Worker
- 实现 Sandbox Service
- 实现 Approval 流程

### Phase 4：生命周期治理

- 实现 Snapshot Service
- 实现 Reset Service
- 实现报告与状态归档

### Phase 5：RAG Demo 验证

- 用系统从零搭一个最小 RAG
- 触发至少一次能力进化
- 生成 snapshot
- reset 后确认回归 Base Layer

---

## 14. 测试设计

### 14.1 单元测试

- schema 校验
- registry 合并逻辑
- baseline 解析
- snapshot manifest 生成
- reset 逻辑

### 14.2 集成测试

- 启动 run
- 生成 baseline
- 执行 delivery
- 评估结果
- 新能力生成与测试
- 审核后注册
- snapshot 与 reset

### 14.3 Demo 验证测试

- RAG 端到端跑通
- 触发能力缺口
- 生成新 tool
- 注册成功
- 使用新 tool 完成优化

---

## 15. 部署设计

### 15.1 第一版部署方式
本地部署优先。

部署内容：

- Python 运行环境
- 项目源代码
- 本地模型/远程模型配置
- 向量库适配
- 测试环境

### 15.2 运行方式
通过 CLI 启动：

- 创建 run
- 执行项目任务
- 查看状态
- 人工审核
- 生成 snapshot
- 执行 reset

### 15.3 配置管理
建议使用：

- `.env`
- `config.yaml` 或 `config.json`

管理：

- LLM 配置
- 路径配置
- 超时配置
- 审核配置
- 测试配置

---

## 16. 项目交付设计

### 16.1 代码交付

- 完整项目代码
- 核心模块注释
- CLI 启动命令
- 安装说明

### 16.2 文档交付

- 架构设计文档
- BaseLine 文档
- 配置说明
- 运行说明
- RAG Demo 说明

### 16.3 运行交付

- 示例命令
- 示例任务
- 示例 snapshot
- 示例 baseline

### 16.4 验收交付

- 至少一个成功 Run 的演示
- 至少一个成功进化的新 Tool
- 至少一个 snapshot 文件夹
- reset 后状态验证记录

---

## 17. 风险与注意点

### 17.1 容易过度设计
风险：

- 一开始就做太多 Agent。
- 一开始就做太复杂 MCP。
- 一开始就做完整长期记忆和向量检索。

控制策略：

- 第一版只验证闭环。
- 先支持 Tool/Skill 进化。
- 先本地运行，后云化。

### 17.2 进化能力滥用
风险：

- 什么问题都去生成新能力。

控制策略：

- 先判断是 Bug、策略问题还是能力缺口。
- 只有能力缺口才进入 Capability Worker。

### 17.3 评估标准漂移
风险：

- 动态评估过多，导致前后版本不可比。

控制策略：

- 验收评估尽量固定。
- 诊断评估允许进化。

### 17.4 Base Layer 被污染
风险：

- 当前 Run 直接改动 Base registry 或 Base assets。

控制策略：

- Base 只读。
- 所有进化能力仅写入 Evolution Layer。

---

## 18. 最终建议

当前项目最合理的落地方向是：

- 以 Python 为主技术栈。
- 以 CLI 为主入口。
- 以单 Supervisor Agent + 多 Worker 为架构。
- 以 Base Layer + Project Baseline + Evolution Layer 为能力层次。
- 以 RAG 作为首个验证型 Demo。
- 以“先跑通闭环，再逐步增强”为建设原则。

这份设计的目标不是一次性做完所有未来能力，而是把当前最重要的闭环做稳：  
**自动生成项目临时基线 -> 开发 -> 评估 -> 缺口进化 -> 测试审核 -> 注册 -> snapshot -> reset。**
