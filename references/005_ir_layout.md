# ADR-0001：IR Token Layout 不变量（ID-based, Contiguous, Layout-agnostic）

## 0. 背景与问题

ProofScaffold 的 Linker/中端 pass 将在后续里程碑中持续扩张（closure、scope、relocation、emit、debug）。若 Phase 1–4 采用“每个 token 一个 Python 对象”的重型表示，API 与 pass 逻辑会被 OO 访问模式固化，Phase 5 再做 packed buffer/向量化将接近重写。

本 ADR 规定：**从现在开始，把“紧凑布局”定义为接口不变量，而非性能优化项**。

## 1. 决策

### 1.1 核心不变量（必须）

1. **SymbolRef 是整数 ID**

* `SymbolId`/`LabelId`/`ConstId`/`VarId` 统一为 `int`（可用 `typing.NewType` 增强类型，但运行时仍为 `int`）。
* 禁止 `class SymbolRef` 之类的对象化 token。

2. **Token payload 是 contiguous sequence**

* LIR/HIR 中所有 token 序列（math strings、proof tokens、label refs）对外表现为“连续序列”：

  * 最低要求：实现 `__len__` 与 `__getitem__`（可迭代）。
  * 允许的具体实现：`list[int]`、`array('I')/array('L')`、`memoryview`、numpy array（未来）、pyarrow buffer（未来）。
* **pass 不得依赖序列的具体类型**，也不得假设 token 可挂属性。

3. **pass API 必须 layout-agnostic**

* pass 输入输出只接受/返回：

  * `TokenSeq`（抽象序列）
  * `Span`（对 TokenSeq 的 slice 描述）
  * `IdMap`（`int -> int` 映射，如 relocation）
* 禁止 pass 读取 token 的“对象字段”。

4. **诊断与 provenance 不进入 token 对象**

* origin、step_id、span_hint 等调试信息通过：

  * `OriginRef`（int id，索引到 OriginTable）
  * `SpanMap` / `StepMap`
  * `Diagnostic.origin_chain`
    来承载，禁止把这些字段塞进 token 元素本身。

### 1.2 允许的局部对象化（允许但受限）

* `Statement`、`ProofUnit`、`SymbolDef` 等“结构节点”可以是 dataclass/对象。
* 但它们内部的 token payload 仍必须是 `TokenSeq`（contiguous, id-based）。

## 2. 影响范围（改动面）

* IR 定义：把所有 token 类型统一为 `int`，并引入 `TokenSeq` protocol。
* SymbolTable/LabelIndex：对外只暴露 `int` id，不暴露对象 ref。
* Linker passes：任何 token 处理逻辑都改为“基于整数数组”的访问模式。
* Diagnostics：需要 `OriginTable`（origin 去重与索引），并保持结构化输出。

## 3. 设计要点（可执行约束）

### 3.1 TokenSeq 协议（建议最小接口）

* `len(seq) -> int`
* `seq[i] -> int`
* `iter(seq) -> iterator[int]`
* 可选：`slice_view(seq, start, stop) -> TokenSeq`（避免复制）

### 3.2 统一的 ID 空间策略（最低限）

* 同一类别 ID（Symbol/Label/Const/Var）可以共享一个整数空间，但必须有 `kind` 信息做判定；或者分开空间并用不同 NewType。
* 规则必须稳定且可序列化（便于 golden tests）。

### 3.3 确定性要求（与 M1.2/M1.3 一致）

* 任何“集合/映射”的迭代顺序必须显式排序。
* 任何新 ID 分配必须稳定（输入同则输出同）。

## 4. 备选方案与拒绝理由

* **备选 A：token 对象化，Phase 5 再优化**
  拒绝：API/访问模式会固化 OO 假设，后续改动面爆炸。
* **备选 B：一开始就 numpy/arrow**
  暂不选：工程成本高，且会阻塞里程碑推进。我们只锁死接口形状，实现可渐进替换。

## 5. 验收（落地检查清单）

* [ ] `SymbolRef`/`LabelRef` 等运行时类型为 `int`
* [ ] IR 递归扫描无 “token 对象”
* [ ] pass 代码中无 `token.xxx` 访问
* [ ] 至少一个 golden test 验证：同输入两次运行，ID 分配与输出快照一致
* [ ] Diagnostic/Origin 使用 table + id 引用，不把 origin 粘在 token 上
