# SPEC-0001：Debug Slice MVP（Python → HIR → LIR → Emit 的最短可读链）

## 0. 目标与非目标

### 0.1 目标（MVP）

当 verifier 报错（例如 “Step 50 failed”）时，开发者能在本地一条命令得到：

1. **对应的 HIR Apply（宏展开后的高层步骤）**：用了哪个 assertion、subst 摘要、step_id
2. **对应的 LIR proof token window**：在 relocation 前后各是什么
3. **相关上下文摘要**：unit_id、stmt_id、pass/stage、以及关键 origin 链
4. **最小重现片段（slice）**：足以复现该失败的缩减输入（先文本化/JSON 化即可）

### 0.2 非目标（MVP 不做）

* 不做完整 SourceMap（byte offset ↔ 多段 span 的精准反查）
* 不做 GUI；先做 CLI 与结构化 JSON 输出
* 不做 proof 搜索/自动修复；只做定位与剖面

## 1. 核心数据结构（MVP 必需字段）

### 1.1 StepId（稳定步骤标识）

* `step_id: int`
  由 generator 在 HIR 生成时分配，要求：

  * unit 内唯一
  * 稳定（同一生成逻辑、同一输入应一致）
* 目的：把 verifier 的 step index 归位到 HIR/LIR 的语义步骤，而不是仅仅指向 Python 行号。

### 1.2 HIR Step Record（可序列化）

对每个 `Apply` 记录：

* `step_id`
* `assertion_label_id`（int）
* `subst_digest`（短 hash 或结构化摘要：`(var_id -> expr_digest)`）
* `origin_ref`（指向 OriginTable 的 int）
* （可选）`free_vars_digest`（为未来 `$d`/contract 预留）

### 1.3 LIR Proof Span Map

为每个 theorem `T`：

* `proof_tokens: TokenSeq`
* `step_to_span: dict[step_id -> (start_idx, end_idx)]`
  其中 span 是 LIR proof token 的半开区间 `[start, end)`。

> 生成规则：lowering（HIR→LIR）时，每个 Apply 展开生成的一段 proof tokens，必须登记其 span。

### 1.4 Emit Span Map（可选，MVP 可先弱化）

* `lir_token_idx -> emitted_token_offset`（或 emitted step index）
  MVP 允许先做“按 token 序号”的定位，不强求 byte offset 精准。

### 1.5 OriginTable + Diagnostic（继承 M1.2a）

* `OriginTable[id] -> {module,file,line,...}`
* `Diagnostic` 输出必须含：

  * `error_code`
  * `primary_origin_ref`
  * `related_origin_refs[]`
  * `origin_chain[]`（stage/unit/stmt/step）

## 2. CLI 规格（最小命令集）

### 2.1 `psdebug slice`

输入：

* `--mm-error-step N`（来自 verifier 的 step index，1-based 或 0-based 要写死）
* `--unit UNIT_ID`
* `--theorem LABEL_ID`（可选；如果 unit 内唯一可省略）
* `--format json|text`（默认 text）

输出（text 版建议结构）：

1. Header

* unit_id / theorem_label / verifier_step
* stage/pass（若已知）
* primary origin（file:line）+ origin chain 摘要

2. HIR View

* step_id
* assertion label
* subst digest（展开为 3–10 行，避免过长）

3. LIR View

* proof span `[s,e)`
* relocation 前后对照（若 M1.5 未做则只显示一种）
* 显示一个 window：`tokens[s-8 : e+8]`（越界裁剪）

4. Minimal Reproducer（可选）

* 输出一个 JSON：只包含必要的 units（依赖闭包）+ theorem + 对应 span 的 proof tokens（或完整 proof tokens）
* 目标是“能交给 CI 或别人复现同一错误”。

### 2.2 `psdebug explain`（可选，但很有用）

输入：同 slice
输出：用短句解释“你看到的失败大概率来自哪里”，例如：

* substitution 中某 var 的 expr digest 与期望不一致（仅基于结构信号，不做证明搜索）
* hint：下一步该查看哪个 step_id 的前后文

## 3. 关键映射算法（MVP 版本）

### 3.1 verifier step → step_id（两种路径）

**路径 A（优先）**：在 emission 时保持 “step_id 边界”

* emit 时插入不可见标记或 sidecar map（不污染 mm）：
  `emitted_step_index -> step_id`

**路径 B（兜底）**：由 LIR span 累积反推

* 若每个 step 有 span，且 verifier step index 近似对应 proof token 位置，可用二分定位落在哪个 span（不保证 100% 精准，但足够 MVP）。

建议：先实现 B（最省工），尽快上 A（最可靠）。

### 3.2 slice 依赖闭包（与 M1.3 协同）

* 利用 `uses_assertions(T)` 与 unit DAG 抽取最小依赖集合
* 输出 slice 时按 topo order 排列 units，保证可复现

## 4. 验收（MVP 完成定义）

* [ ] 能从一个 verifier 报错 step 输出对应的 HIR Apply（assertion + subst 摘要）
* [ ] 能输出对应的 LIR proof token span 与窗口
* [ ] 输出包含 origin chain（至少 stage/unit/step）
* [ ] 同一输入/同一错误，两次输出 JSON byte-identical（或字段一致）
* [ ] 至少一个 “最小复现 slice” 在 CI 上可复现同样的 verifier 失败（允许只覆盖一个典型案例）

## 5. 与后续里程碑的接口

* 与 M1.4（scope frames）：Debug Slice 应能打印 active scope frame digest（先预留字段）
* 与 M1.5（relocation）：Debug Slice 增加 relocation 前后对照输出
* 与 SourceMap MVP：把 `Emit Span Map` 从 token-index 级升级到 byte-offset 级，但不改变 step_id/step_to_span 的主链结构
