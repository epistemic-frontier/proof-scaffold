# ProofScaffold 生成器设计（补充文档 04，Rev. 2）

**Status**: Draft  
**Scope**: Python 侧“生成器（Generator）/ DSL / import-export”设计；作为以下文档的补充与落地化说明：

- `001_arch-design.md`（三层架构与信任边界）
- `002_link-model_v3.md`（Link Model v3：IR / Contracts / ScopeFrames / Relocation / SourceMap）
- `003_roadmap-methodology_v2.md`（Roadmap 与工程方法学）

本文件的目标是：在不改变 v3 Link Model 不变量的前提下，把现有 DSL + manifest + toy linker 的优势“升级为正式前端”，并明确它如何为 Linker 提供 **可链接、可重定位、可诊断** 的 IR 输入。

---

## 0. 设计动机：从“解释器式构造”走向“编译器式工具链”

当前 DSL 的使用体验更接近“解释器”：

- 写一段 Python，逐句“执行”构造：声明、入栈/出栈作用域、插入 `$f/$e/$a/$p`。
- 在构造过程中做保守检查（未声明 token、作用域不平衡、标签可见性等）。

而 v3 Link Model 的整体视角更像“编译器工具链”：

- 前端输出结构化 IR（LIR 必选，HIR 可选），
- 后端 Linker 做闭包、ScopeFrames、token-level relocation、两阶段 emission 和 SourceMap。

**关键结论**：二者并不矛盾。  
本设计把 DSL 明确定位为 **Stage 0（Front-end IR construction）** 的实现方式：它可以“解释器式”地帮助你构造 IR，但产物必须是符合 v3 的 IR（SymbolRef tokens），而不是提前固化为 `.mm` 字符串。

---

## 1. 现有版本的优势（应保留并放大）

现有 `MMBuilder` / `export` / `Linker.resolve` 提供了很好的起点：

1. **保守语义检查前移**：在生成期就能发现大量结构性错误（token 未声明、label 冲突、scope 不平衡等）。
2. **作用域显式化**：`strict` 模式禁止顶层 `$e`，逼迫使用 `${ ... $}`，更接近 v3 的 ScopeFrames 精神。
3. **跨模块依赖显式化**：proof step 支持 `Theorem` 句柄；在 builder 中收集 `requires()`，将可链接依赖作为显式数据。
4. **export manifest 机制**：用轻量 JSON 做“接口数据库（mmdb）”，便于做 import/export 实验。

本补充设计要做的不是推翻它，而是把这些优势从“字符串生成器”升级成“IR 生成器”。

---

## 2. 设计目标与非目标

### 2.1 目标

- **G1：与 v3 Link Model 完全兼容**
  - proof tokens 与 math-string tokens 必须是 `SymbolRef[]`（非 raw strings）。
  - 单元边界以 `ProofUnit` 为中心：仅允许跨单元引用他人 exports（`$a/$p`）。
  - 允许 Linker 在 Stage 6 对 *所有 token* 做 relocation。
- **G2：保持 DSL 的“早失败”体验**
  - 生成阶段尽可能早地拒绝：声明顺序错误、作用域错误、非法引用、明显的 contract 缺失等。
- **G3：可诊断**
  - 每个 Statement / ProofStep 都携带 `origin`（模块 + 文件:行号 + 可选的调用栈摘要），使 SourceMap 能提供“未改名视图”。
- **G4：可渐进落地**
  - 支持一个明确的 COMPAT 过渡期，但必须默认关闭，并有迁移计划。

### 2.2 非目标

- 不做证明搜索与回溯（生成器不变成 prover）。
- 不规定 proof compression、缓存策略、增量验证实现细节（保持与 v3 的非目标一致）。
- 不把 Metamath 变成面向人类的主编写语言（人类写 DSL/文档；Metamath 是目标工件）。

---

## 3. 总体结构：生成器（DSL）提供 IR，Linker 完成链接与发射

### 3.1 数据流（建议）

```
Python proof packages (DSL code)
  └─ Generator Front-end (this doc)
       ├─ Symbol registrations (SymbolDef)
       ├─ ProofUnitIR(s)
       ├─ LIR graph (required)
       └─ HIR graph (optional)
  └─ Linker (v3)
       ├─ resolve + lint
       ├─ contract extraction
       ├─ $d modes A/B/C
       ├─ closure + topo sort
       ├─ scope planning (ScopeFrames)
       ├─ relocation (token-level)
       ├─ emission (header + body)
       └─ SourceMap + diagnostics
  └─ Metamath verifier (authoritative)
```

### 3.2 责任边界（Generator vs Linker）

Generator（前端）保证：

- 结构良构：scope 平衡、token 在 IR 层面可解析（SymbolId/Ref）、禁止明显的跨单元 `$f/$e` 泄露路径。
- 依赖显式：每个 ProofUnit 的外部依赖可显式列出（最少是 hints；更理想由 proof tokens 直接得出）。
- 溯源可用：每个 IR 节点有 origin 元信息。

Generator 不保证：

- 逻辑正确性（证明对不对）。一切以 verifier 接受/拒绝为准。

Linker（后端）保证：

- v3 中间端不变量：deterministic emission、token-level relocation、contract/binding 正确、ScopeFrames 正确等。
- `.mm` 发射的语法良构与可被 verifier 解析执行。

---

## 4. 核心工件与数据结构

本节给出“可实现”的最小数据模型；并刻意保持与 v3 名词一致。

### 4.1 Symbol 系统（v3 对齐）

- `SymbolId`: 内部稳定 ID，不直接发射。
- `SymbolDef`: `{origin, local_name, kind(Const|Var|Label), scope_class}`。
- `SymbolRef`: 对 `SymbolId` 的引用；所有 token 载荷最终必须是 `SymbolRef[]`。

> 设计决策：Generator 端允许使用“局部 SymbolId 占位”（local-only），但必须在 Stage 1 被全局解析到可重定位的 SymbolId 空间。

### 4.2 ProofUnitIR（Generator 的核心输出）

最小字段：

- `unit_id`: 稳定 ID（建议：`<module_id>:<local_unit_name>` 或 deterministic hash）
- `origin`: 生成 callsite（模块 + file:line）
- `decls_local`: unit 内声明（$f/$e/$d）与必要的内部 helper label（若策略允许）
- `exports`: 一个或多个 exported assertions（通常先限制为 1）
- `proof_body`:
  - LIR：Metamath-shaped statements，其 token payload 为 `SymbolRef[]`
  - 可选 HIR：`Apply(assertion, subst, step_id)` 等结构化轨迹

### 4.3 Export DB（mmdb）与接口记录

现有 `export.py` 的 JSON manifest 很适合做 mmdb 的“最小实现”。本设计建议把它版本化扩展为：

- `module`: module_id
- `format_version`: e.g. `"mmdb@2"`
- `exports[name]`:
  - `label_ref`: **不要直接固化最终 label 字符串**；记录可重定位的 label SymbolId（或“origin+local_name+kind”的引用键）
  - `typecode_ref`
  - `expr_refs: SymbolRef[]`
  - `interface_contract`（可选但推荐）：
    - `mandatory_hyps`
    - `mandatory_vars`
    - `dv_contract`（interface pairs）
    - `public_symbols`（仅 exports 的 `$a/$p`）
  - `closure_contract`（可选）：
    - `uses_assertions`（由 proof tokens/HIR 提取）
  - `requires`（允许作为 bootstrap hint，但最终应能被 `uses_assertions` 覆盖）

> 备注：在 bootstrap 阶段，`label_ref` 可以临时降级为字符串 label（兼容模式），但必须在 doc 中明确为 COMPAT。

### 4.4 Python 侧句柄：TheoremRef / ImportedTheorem

当前 `Theorem` 句柄携带 `label` 字符串，便于直接写进 proof steps。为了 v3 token-level relocation，不再建议把 “label 字符串”作为长期真值。

建议引入：

- `TheoremRef`：
  - `fqname`
  - `symbol_key` / `label_id`（可重定位引用）
  - （可选）`debug_label_hint`：仅用于开发显示
  - （可选）`interface_contract_digest`：用于早期 lint 与 IDE 反馈

Generator 的 proof step 应尽量使用 `TheoremRef` 而非 raw string label。

---

## 5. DSL（MMBuilder）升级：从字符串发射改为 IR 构造

### 5.1 核心改造：Builder 的内部缓冲不再是 `_lines: list[str]`

现有 builder 直接累积 `.mm` 字符串行。新的目标是：

- `_stmts: list[LIRStmt]`（必选）
- `_hir_ops: list[HIROp]`（可选）
- `_symbols: LocalSymbolTable`（维护 local_name → local SymbolId）
- `origin` 捕获：每条 stmt 附带源位置

同时保留一个**调试用** `render_mm_compat()`，用于将 LIR 以“未重定位视图”渲染成易读 mm 片段（仅调试，不作为最终工件）。

### 5.2 状态机与限制（建议作为“Profile”）

在现有 strict 规则基础上，扩展为三个 profile：

- `PROFILE_BOOTSTRAP`（最小可用）
  - 允许少量 raw string token（需显式开关）
  - 允许 `requires` 作为 closure hint
- `PROFILE_V3_LIR`（默认）
  - 禁止 raw string token（除非 allowlist）
  - proof steps 必须是 `LabelRef/TheoremRef`（不再接受裸字符串 label）
- `PROFILE_V3_HIR`（高级）
  - 需要记录 substitution 元信息（为 `$d` mode C 与 MVP_STRICT 提供基础）

### 5.3 单元边界：显式 `unit(...)` 构造 ProofUnit

建议在 DSL 中引入：

```python
with mm.unit("sqrt2irr") as u:
    u.f(...)
    u.e(...)
    u.p(...)
    export(u, name="sqrt2_irrational", ...)
```

规则：

- 一个 `unit()` 对应一个 ProofUnitIR；
- unit 默认自带一个 ScopeFrame（与 v3 Stage 5 baseline emission 一致）；
- 禁止在 unit 外声明 `$e/$f` 影响 unit 内（避免隐式上下文）。

---

## 6. Import / Export 机制：把 “接口” 做成可链接 API

### 6.1 export 的语义（建议）

`export(...)` 不直接假定输出 `.mm` 中的最终 label 名字。它应该：

- 记录 `label_id` 或 `symbol_key`（origin+local_name+kind）
- 记录 expr/typecode 的 SymbolRef 列表
- 记录 interface contract（如果可得）
- 返回 `TheoremRef`（供其他模块 import/use）

### 6.2 import 的语义（建议）

提供 `import_theorem("a.b.c.thm") -> TheoremRef`：

- 从 mmdb 读取该 theorem 的 record，
- 返回可重定位引用句柄，
- 允许 Generator 在 proof steps 中引用它，并记录依赖。

---

### 6.3 “定义（definition）”也必须可导出：在 Metamath 中它本质是“符号 + 断言”的导出包

从 Metamath 的角度，“定义”并不是一类独立的语句；它通常由以下内容组合表达：

- **新符号声明**：`$c`（必要时也包含 `$v` 的公共变量约定）
- **一组断言**：`$a` / `$p`  
  - 形成/类型相关断言（如果你们采用“语法公理”风格）
  - 定义等价/定义方程（`df-*`）
  - 常见的 existence/uniqueness 或可用的 rewrite 引理（可选）

因此，从 Link Model v3 的视角，“定义”最自然的模型不是一个新 primitive，
而是一个 **Definition Package（定义包）**：

- `provides_symbols`: 新的 `Const`/`Var` `SymbolDef`（供 Stage 1/6/7 解析、重定位与 hoist）
- `exports_assertions`: 一个或多个导出的 `$a/$p`（v3 允许一个 ProofUnit 导出多个断言）
- `definition_meta`（非 TCB）：可选的 unfold/rewrite/pretty-print 信息，仅用于生成器与 IDE

**关键点**：Linker 的语义边界不变——定义“是否正确”仍由 verifier 对最终流的接受/拒绝决定；
定义包只是让跨模块复用与依赖闭包变得可计算、可链接、可诊断。

### 6.4 mmdb（Export DB）建议扩展：不仅记录 theorem，也记录 symbol 与 definition bundle

当前 toy `export.py` 的 `ExportRecord` 仅覆盖 theorem 的最小接口（label/typecode/expr/requires）。
为了支持“定义可导出”，建议把 mmdb schema 扩展成统一的 `ExportItem`，至少覆盖三类：

1. **Assertion export（断言导出：定理/公理）**
   - `kind: "assertion"`
   - `label_ref` / `symbol_key`（可重定位引用，避免固化最终 label 字符串）
   - `typecode_ref`
   - `expr_refs: SymbolRef[]`
   - `interface_contract`（可选）：`mandatory_hyps/vars/dv_contract`
   - `closure_contract`（可选）：`uses_assertions`

2. **Symbol export（符号导出：常量/公共变量）**
   - `kind: "symbol"`
   - `symbol_key: (origin, local_name, kind)` 或 `symbol_id`（若已经稳定化）
   - `decl_class: Const | Var`
   - （可选）`scope_class` / `visibility`（public/private_v 约定）

3. **Definition export（定义包导出）**
   - `kind: "definition"`
   - `provides_symbols: [symbol_key...]`
   - `exports_assertions: [fqname...]`（指向本 manifest 内的 assertion exports）
   - `meta`（可选）：`unfold_label`、rewrite hints、pretty-print 信息等

并相应引入对称 API：

- `export_symbol(...) -> SymbolRefHandle`
- `export_assertion(...) -> AssertionRef`
- `export_definition(...) -> DefinitionRef`

以及 import：

- `import_symbol("a.b.c.sym")`
- `import_assertion("a.b.c.thm")`
- `import_definition("a.b.c.def")`

使得“在 theorem 的 statement 中使用定义出的新符号”也能通过句柄追踪依赖（不仅靠 proof tokens）。

---



## 7. 合约与 `$d`：生成器应如何配合 v3 三种模式

### 7.1 Mode A（Pass-through）

Generator 提供：

- `dv_contract`（接口 `$d`）
- 以及可选的 local `$d`（仅用于本 unit proof 安全）

Linker 只负责把它们放在正确 binding 点。

### 7.2 Mode B（Linter-driven）

Generator 不推断 `$d`，但必须提供：

- 可定位的 origin 信息，
- 可重现的最小 unit 片段渲染（debug slice），
以便 verifier 报错能回传到 “哪个 Apply/哪个 substitution” 或至少哪个 proof step。

### 7.3 Mode C（HIR-assisted）

Generator 需要记录 HIR：

- `Apply(assertion, subst, step_id)`，
- `SubstMap` 里记录表达式的 free var 集合或 digest，

使 Linker 能做约束传播（不做 proof search）。

---

## 8. 构建模式：避免“伪证明污染”CI

我们明确区分两类产物：

1. **Interface build（接口构建）**
   - 产出：mmdb（exports + contracts），以及可选的 debug mm 片段
   - 不要求 verifier 通过（甚至不生成 `$p`）
2. **Verifiable build（可验证构建）**
   - 产出：完整链接后的 `.mm` stream
   - 必须通过 verifier（进入 CI 的默认路径）

对于 toy 示例里 “随便填 proof token” 的场景，建议用接口构建表达“存在一个 theorem API”，而不是输出一个注定失败的 `$p`。

---

## 9. SourceMap：在生成阶段就捕获 origin，避免事后补救

设计要点：

- builder 每生成一个 stmt / proof step，都携带 `origin`：
  - module id
  - python file path
  - line number（建议用 `inspect` 捕获 callsite）
  - 可选：builder 逻辑片段名（函数名/局部 unit 名）
- linker Stage 8 以此为基础产出：
  - `stream_span -> (origin, unit_id, stmt_id, label?, proof_step_idx?)`
  - 可选增强：active context snapshot digest、used assertion id、substitution digest

---

## 10. 测试与验收：对齐 Roadmap 的三类测试

- **Sanity tests**：最小 DAG → link → emit → verify（必须快且稳定）。
- **Golden tests**：固定 IR 输入 → 固定发射输出（尤其 relocation 的稳定性）。
- **Adversarial tests**：
  - scope imbalance、
  - label/token collision、
  - forbidden cross-unit `$f/$e` 引用、
  - missing `$d`（在不同 mode 下的预期行为）、
  - 依赖循环与缺失导出。

---

## 11. 迁移计划（建议）

### 11.1 Step 0：双轨输出（保留 render，同时产出 IR）

- 保留现有 `MMBuilder.render()` 以便继续跑 toy demo。
- 同时让 builder 在内部构造 LIR（哪怕只是“字符串 token + 标记 compat”）。

### 11.2 Step 1：把 export manifest 版本化并引入 label 引用键

- 增加 `format_version`
- 增加 `symbol_key`/`label_id` 字段
- 在 compat 期允许 `label` 字符串作为 fallback

### 11.3 Step 2：引入 `import_theorem()` 与 TheoremRef

- 让跨模块 proof steps 彻底摆脱“手写字符串 label”
- 依赖收集从 `requires` 过渡到 `uses_assertions`（由 proof token 提取）

### 11.4 Step 3：默认关闭 raw-string tokens（CI shock therapy）

- 以 Roadmap 的 COMPAT 政策为准：compat 必须显式标记，且有 allowlist 与逐步清零计划。

---

## 12. 附录：更新后的 toy 示例（示意）

> 这是“接口构建”风格：只表达 theorem API 与 export 记录；不输出假 `$p`。

```python
from proof_scaffold.dsl import MMBuilder, expr
from proof_scaffold.imports import import_theorem
from proof_scaffold.export import export

mm = MMBuilder(profile="PROFILE_V3_LIR")  # 默认禁止 raw string token

with mm.unit("sqrt2") as u:
    u.comment("Toy sqrt2 module (interface only)")
    u.c("|-","sqrt2","irrational")
    u.v("ph")
    u.f("wph","|-","ph")

    # 只声明接口：不在 verifiable build 输出 $p
    sqrt2irr = u.declare_theorem(
        label="sqrt2irr",
        typecode="|-",
        expr=expr("sqrt2","irrational"),
        interface_only=True,
    )

export(
    module_id="number_theory.sqrt2",
    name="sqrt2_irrational",
    theorem=sqrt2irr,
    build_dir="build/mmdb",
)
```

---

## 13. 设计决策摘要（便于 code review）

1. DSL 产物必须是 IR（LIR/HIR），`.mm` 字符串仅用于 debug/compat。
2. import/export 的 API 以可重定位引用为中心（TheoremRef/label_id），不以最终 label 字符串为中心。
3. 通过 Profile 把“保守检查”与“能力等级（conformance）”结构化：LIR-only → MVP_STRICT → FOL-ready。
4. 接口构建与可验证构建分离，避免伪证明污染 CI。
5. origin 追踪从 Stage 0 就开始做，SourceMap 不是事后补丁。

---

**End of document.**
