# ProofScaffold 技术白皮书（草案）

**状态**：Draft  
**范围**：ProofScaffold（proof-scaffold/）构建与链接工具链；Python 作为 builder，Metamath 作为 verifier  
**读者**：希望构建/维护可验证形式化证明工件的工程师与研究者  

---

## 摘要

ProofScaffold 是一个面向“证明工程（proof engineering）”的实验性框架：以**编译器/链接器**的方式组织证明构件，以**可诊断、可追溯、可确定性复现**为硬约束，把 Python 视为不可信的构建工具，把 Metamath 验证器视为唯一的语义权威。

项目的核心观点是：在大规模形式化中，许多真实痛点并非“如何找到证明”，而是“如何把证明以模块化、可维护的方式组织起来，并且当失败时能快速定位”。因此，ProofScaffold 优先解决：

- 依赖闭包与拓扑排序（像链接器一样处理依赖 DAG）
- 全局符号表与 token 级重定位（Metamath 扁平命名空间上的命名冲突与可复现输出）
- 显式作用域规划与两段式发射（确定性布局，便于后续 SourceMap）
- 结构化诊断、Debug Slice 与 SourceMap（把 verifier 的“偏移量错误”还原成生成器的文件/行号/步骤）

---

## 1. 背景与定位

ProofScaffold 面向的不是传统意义上的“交互式证明助手 UI”，也不是“自动定理证明/证明搜索”。它将形式化证明的构建视为一个**工具链问题**：

```
Python 证明包（模块化）
  -> IR（中间表示：HIR 可选，LIR 必需）
  -> Linker（闭包/作用域/重定位/发射）
  -> .mm（Metamath 工件，线性“二进制”）
  -> Verifier（语义权威）接受/拒绝
  -> 诊断/SourceMap 回流到 Python 源码与生成步骤
```

这一定位直接带来三项工程准则：

- **三层分离**：文档层（人类意图）/ Python 层（构建工具链）/ Metamath 层（权威工件）
- **信任边界明确**：只有 verifier 在 TCB 中；生成器与链接器必须被视为不可信
- **确定性优先**：同一输入 IR 必须产出相同顺序、同名、同输出、同诊断

参见：references/001_arch-design.md、references/003_roadmap-methodology_v2.md、references/002_link-model_v4.md。

---

## 2. 目标与非目标

### 2.1 目标（North Star）

- 把由 Python 包组织的证明构件 DAG，构建为**单一、确定性的** Metamath 线性流，并由 verifier 接受
- 提供“链接器级”的纪律：依赖闭包显式可检查、命名重定位可复现、作用域与绑定点显式化
- 形成“开发者级”的调试面：能定位到 origin module / proof unit / statement / proof step（并可扩展到 SourceMap）
- 保持可扩展的信任模型：builder 与 linker 不进入 TCB，失败必须变得可诊断而不是变得“更可信”

### 2.2 非目标

- 不做证明搜索、回溯、自动化求解（不是 ATP）
- 不做 Lean/Coq 风格的交互式 UI/UX 替代品
- 不尝试把 Metamath 自动翻译回自然语言

---

## 3. 三层架构与信任模型

### 3.1 文档层（Document Layer）

- 载体：Markdown/LaTeX
- 作用：表达数学意图、动机、策略与解释
- 不追求：形式化严谨与机器可检查（这是下游的任务）

### 3.2 Python 层（Compiler & Linker Layer）

- 作用：构建 IR、计算依赖闭包、进行重定位、规划作用域、发射 `.mm`，并生成诊断/SourceMap
- 地位：**不可信 builder**。它构建证明，但它不是证明本身

### 3.3 Metamath 层（Binary Artifact Layer）

- 作用：线性、机器可检查的“对象代码”
- 地位：**语义权威由 verifier 裁决**。如果 builder/linker 产生垃圾，verifier 必须拒绝

TCB（Trusted Computing Base）包含：Metamath verifier 与其规范；不包含：任何 Python 生成/链接逻辑。参见 references/001_arch-design.md、references/002_link-model_v4.md。

---

## 4. 核心抽象与数据模型（Link Model v4）

本节总结 references/002_link-model_v4.md 的关键抽象，作为实现与扩展的“共同语言”。

### 4.1 Origin：可追溯的溯源记录

- `OriginTable[OriginRef] -> OriginRecord`
- 最小字段：module_id、file、line；可选字段：function、callsite_digest
- 约束：必须可确定性去重；任何诊断必须能引用至少一个 OriginRef

Origin 是整个“可诊断性”与 SourceMap 的根：没有 Origin，就无法把 verifier 失败映射回生成器源代码。

### 4.2 SymbolId / Token / TokenSeq：以 int 为核心的布局无关 token 体系

- `SymbolId = int`：运行期 token 身份必须是 int，不是对象引用
- `Token = int`：math string 与 proof token 都是 int（SymbolId）
- `TokenSeq`：连续、可索引、布局无关（list/array/memoryview/自定义 buffer 均可）

关键约束：

- Stage 1 之后，所有 token 必须进入**单一全局 SymbolId 空间**
- token 不允许携带 debug/provenance 字段；调试信息必须在 side tables（OriginTable、StepMap、SpanMap）

该设计使后续 pass（如重定位、发射、SourceMap）不依赖具体存储布局，降低技术债。

### 4.3 ProofUnitIR：可链接边界

ProofUnit 是链接纪律的边界，核心约束是：

- 跨单元引用只允许通过对方导出的 `$a/$p` 断言（exports）
- 禁止窥探对方内部 `$f/$e` 标签
- 单元内部作用域必须平衡（ScopeEnter/ScopeExit）

---

## 5. 链接器流水线（Stages 0–8）

Link Model v4 将工具链拆分为可验证、可测试的阶段性 pass。其重要性在于：每一阶段都能定义明确的输入/输出契约与失败模式，从而满足“增量可验证”和“确定性输出”的工程要求。

### Stage 0：前端 IR 构建

- 输入：Python 生成器/DSL
- 输出：ProofUnitIR（LIR 必需、HIR 可选）+ OriginTable 种子
- 要求：每条 statement（以及可选 HIR step）必须附带 origin_ref

### Stage 1：全局符号解析 + 早期 lint

目的：建立单一全局 SymbolId 空间，并尽早拒绝不可链接模式，例如：

- 禁止 raw-string token（除非显式 COMPAT）
- 禁止 `$` 前缀保留命名
- proof tokens 必须是 Label kind；math tokens 必须是 Const/Var kind
- 禁止跨单元引用非导出标签；禁止引用对方 `$f/$e` 标签

### Stage 2：契约提取（Contracts）

输出（示意）：

- 对每个导出断言 A：mandatory_hyps / mandatory_vars / dv_contract（可为空）
- 对每个定理 T：uses_assertions(T)（依赖闭包的基础）

### Stage 3：`$d` 处理模式（可配置）

支持从“显式传递”到“HIR 辅助传播”的多种模式，用于管理 disjointness 约束的工程化演进。

### Stage 4：依赖闭包 + 拓扑排序

- 基于 uses_assertions 图计算闭包并 topo-sort
- 要求：对输入顺序不敏感；检测环并给出结构化诊断

### Stage 5：作用域规划（Scope Planning）

把“发射什么/发射到哪里”的决策从文本打印中剥离，生成 `LinearPlan`：

- preamble（可选注释）
- header（全局 `$c/$v`）
- frames（`${ ... $}` 的 body）

该分离是实现 SourceMap 的前置条件。参见 projects/011-scope_planning.md。

### Stage 6：token 级重定位（Relocation）

为所有 SymbolId 计算确定性的 emitted_name，并对：

- labels
- math strings（常量/变量 token）
- proof tokens（标签 token）

进行统一重写。要求：冲突解决策略必须稳定可复现。

### Stage 7：两段式发射（Two-phase emission）

输出结构被固定为三段：

1) Preamble（注释）  
2) Global header（`$c` + `$v`）  
3) Body（ScopeFrames 与 `$d/$f/$e/$a/$p`）  

约束：body 不得包含 `$c/$v`，header 的排序必须确定性。

### Stage 8：Debug/诊断/SourceMap 工件

最低要求：

- 结构化 Diagnostic（稳定字段与排序）
- Debug Slice（对 proof step 的局部定位）

可选增强：

- SourceMap（emitted spans -> origin/unit/stmt/step）

参见 projects/020-source_map.md。

---

## 6. 构建与验证工作流：Driver 与 “Transient Monolith”

ProofScaffold 通过 `skfd.driver` 管理 Python 证明包的构建生命周期，并采用 “Transient Monolith” 验证策略（参见 README 与 projects/009-logic_driver.md）：

- 证明包以 Python 模块组织，并暴露 `build(mm, **deps)` hook
- 依赖必须显式声明（manifest），由 driver 注入 `deps`
- 构建时收集各包的 LIR/IR，在验证时拼接为一次性 `.mm` 文件（例如 `target/logic_full.mm`）
- 避免使用 Metamath `$[ ... $]` include 机制，从而规避跨文件作用域污染与复杂性

该策略的工程价值在于：

- **隔离**：验证工件是封闭单元，作用域与声明更可控
- **简单**：链接器不需要处理“增量差分发射”即可验证
- **鲁棒**：依赖变更自然反映到验证结果，避免隐藏的“旧 include 引用”

### 6.1 代码结构（当前实现映射）

ProofScaffold 将“规格/阶段划分”落实为可读的目录边界，便于把白皮书中的概念对应到实现：

- `src/skfd/core/`：核心数据模型与契约（origin、symbols、lir、unit、diag、contracts、source_map）
- `src/skfd/builder/`：builder API（在生成阶段提供符号 interning 与 origin 适配）
- `src/skfd/driver/`：包发现、依赖图与 runner（按 topo 顺序注入 deps 并收集 IR）
- `src/skfd/linker/passes/`：按 stage 拆分的链接 pass（stage1..stage6）
- `src/skfd/linker/emit/`：发射（消费 scope plan 与 relocation 结果，生成 `.mm` 与可选映射）
- `src/skfd/verifier/`：验证器 shim 与 `mmverify` 接口
- `tests/`：sanity/golden/adversarial/feature 的测试分层与验收

---

## 7. 诊断、Debug Slice 与 SourceMap：把失败变得可修

### 7.1 结构化诊断契约

链接器失败必须统一表现为结构化 Diagnostic，并以 `LinkerDiagError(diag)` 作为边界错误类型：

- error_code / message
- primary_origin_ref（主定位）
- related_origin_refs（稳定排序）
- details（JSON 可序列化且稳定渲染）
- origin_chain（阶段/unit/stmt/step 的 breadcrumbs）

关键要求：禁止裸异常穿透链接器边界；同一输入与失败必须得到同一诊断结构与排序（确定性）。

### 7.2 Debug Slice：proof step 级可局部化

Debug Slice 的目标是避免“50MB 输出里一个 byte offset”的不可操作错误。最低要求包括：

- proof_tokens（定理的 proof token 序列）
- step_to_span：StepId -> `[start,end)` 的半开区间映射

可选增强包括：StepRecord（assertion_label、subst_digest、origin_ref）、以及 relocation 前后 token window 的对照视图。

### 7.3 SourceMap：从 emitted spans 回到 origin

SourceMap 将输出位置（行/列、token index 或其他 span）映射到源位置（OriginRef），并进一步关联 unit_id/stmt_id/step_id，从而让 CLI 能显示“文件:行号”的人类可读错误。

参见 projects/020-source_map.md 中的设计目标与建议格式。

---

## 8. 工程方法论：Document-First + 测试分层

ProofScaffold 明确采用“文档优先”的演进方式（references/003_roadmap-methodology_v2.md）：

- 重大能力先写 spec/ADR，锁定不变量与验收测试，再实现为 pass
- 每次能力引入必须满足“增量可验证”：至少一个 sanity、一个 golden（确定性）、以及若干 adversarial（失败模式）测试

测试分层（示意）：

- Sanity：最小 build → emit → verify，确保基本闭环不破
- Golden：固定 IR -> 固定输出，锁定确定性与命名/布局策略
- Adversarial：构造边界/恶意输入，验证“最早失败阶段”“诊断质量”“顺序不敏感”等关键不变量

---

## 9. 差异化与可扩展性

### 9.1 链接器心智模型带来的收益

把证明系统当作“链接器”处理，使很多工程问题可以直接复用成熟经验：

- 依赖闭包、符号表、重定位、线性化、确定性产物
- 诊断定位（origin chain）、SourceMap、slice/repro 生成

### 9.2 Authoring-First：先凝练理论，再下沉验证

references/005-authoring.md 强调“凝练（condensation）阶段”的作者体验：作者在上游使用 Expr/Constructor/Var 的结构化语言表达意图，再通过受控桥接降到 token 级表示与 verifier。该路线使“理论形成期”不被过早的自动化/推断复杂度绑架。[Project 021](projects/021-authoring-ir-for-human-and-llm-authors.md) 进一步从首个非平凡包 `metamath-logic` 的实践中提炼共享的 typed Authoring IR、面向人类与 LLM 的双 façade，以及可恢复、可重放的 Draft Workspace。

---

## 10. 路线图（概览）

以 Linker v0 → 诊断/SourceMap → 契约纪律为主线推进（详见 references/003_roadmap-methodology_v2.md 与 projects/*）：

- Phase 1：多模块链接 + 确定性发射（LIR 基础、符号解析、闭包 topo、作用域规划、重定位、两段式发射）
- Phase 2：诊断优先（SourceMap MVP、debug slice 工具链、CLI 人类可读输出）
- Phase 3：契约纪律（接口契约 vs 闭包契约更强约束，减少 ghost dependencies）

---

## 11. 术语表（简）

- **Builder**：生成 IR 的 Python 代码；不可信
- **Linker**：对 ProofUnits 执行闭包/作用域/重定位/发射的管线；不可信但必须可诊断
- **Verifier**：Metamath 验证器；语义权威（TCB）
- **Origin / OriginTable**：溯源记录与表；诊断与 SourceMap 的根
- **SymbolId**：运行期全局符号 id（int）
- **Token / TokenSeq**：token（int）与其连续序列；布局无关
- **ProofUnit**：可链接边界；跨单元仅通过导出断言交互
- **LIR/HIR**：Metamath 形状 IR（必需）/ 结构化 proof ops（可选）
