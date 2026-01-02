下面给出一个**整合的重构方案**，目标是：在不牺牲你们 M1.1 已建立的确定性与可诊断性前提下，把 `LinkerV0` 的技术债（重复、耦合、隐式约定、未来扩展阻力）在 M1.2a/M1.2 阶段**一次性“钉死底座”**。

我会按：**现状问题 → 目标形态 → 目录结构 → 关键抽象 → 迁移步骤 → 质量闸门** 来写。

---

## 1) 这个阶段的“技术债清单”（你现在最该还的）

### 1.1 诊断样板泛滥、规范不统一

* `Diagnostic(...)` 构造分散在 Stage1/Stage4，`origin_chain` 形式随手写
* `fmt_origin` 在多个函数里重复
* Stage4 有时 `LinkerError`，有时 `LinkerDiagError`，风格不一致

**风险**：未来新增规则/阶段时，错误信息会碎裂，golden test 难维护，定位质量下降。

### 1.2 Stage1 “收集 + 推理 + lint” 混在一起

* `_stage1` 既在建符号事实表，又在跨 unit 推理（owners/exports/leakage），又在做 scope balance guard

**风险**：Stage1 会继续膨胀；任何小改动都可能破坏别处。

### 1.3 中间态没有被显式建模

* Stage 间传递多个返回值（infos/global_consts/...），容易丢字段/重算/出现不一致

**风险**：重构困难；新增阶段不敢动；测试难以覆盖“Stage 后产物”。

### 1.4 决定性策略未被“集中定义”

* 排序策略、owner 选择策略、suffix mangling 在不同地方写死

**风险**：输出不稳定的 bug 难找；策略更改需要全局 grep。

---

## 2) 目标形态（还债后的“工程骨架”）

### 2.1 LinkerV0 只做 orchestrator（≤200 行）

* 负责：组装上下文、按固定 pass 顺序运行、统一异常包装
* 不负责：业务规则细节

### 2.2 用 LinkContext 显式承载所有中间态

* 每个 pass 只读写 `ctx` 的某一组字段
* 所有跨 pass 的共享状态都挂在 ctx 上（禁止“临时 dict 漫游”）

### 2.3 诊断统一语法：`raise_link_error(...)`

* 所有错误都走一个统一 helper（自动补齐 origin_chain、保证 message/details 格式稳定）
* `LinkerDiagError.__str__` 统一格式化 origin（与 JSON 输出一致）

### 2.4 Stage 0.5：Origin sealing 单点入口（M1.2a 的地基）

* 缺 origin 必须在最早阶段抛 `E_MISSING_ORIGIN`
* details 可快照、可断言

---

## 3) 推荐目录结构（每文件 <300 行的自然切法）

```
proof_scaffold/
  diag.py                      # 你已有 Diagnostic（基本不动）
  linker_v0.py                 # orchestrator（短）
  linker/
    context.py                 # LinkContext + UnitInfo + small helpers
    errors.py                  # LinkerError / LinkerDiagError
    diag_helpers.py            # fmt_origin / mk_diag / raise_link_error / push_chain
    policy.py                  # 决定性策略：排序、owner选择、suffix mangling
    passes/
      origin_seal.py           # Stage 0.5
      stage1_collect.py        # Stage 1a: 收集事实（含 unit 内 scope guard、raw token 禁止）
      stage1_lint.py           # Stage 1b: 跨 unit lint（unresolved/export/leakage）
      stage4_deps.py           # Stage 4: dep graph + topo + cycle diag
      stage6_reloc.py          # Stage 6: relocation map
      stage7_emit.py           # Stage 7: emission
```

> 这套结构把“横切关注点”（diag/policy/context）与“阶段 pass”彻底分离，是降低技术债的关键。

---

## 4) 关键抽象：四个“小而硬”的底层模块

### 4.1 `LinkContext`（context.py）

把你现在 stage 间返回的所有东西集中管理：

* `units: list[ProofUnitIR]`
* Stage1 outputs：

  * `infos: list[UnitInfo]`
  * `global_consts/global_vars`
  * `label_owners`
  * `label_kind_by_unit`
  * `exports_by_unit`
* Stage4 outputs：

  * `ordered_infos`
* Stage6 outputs：

  * `relabel`

**好处**：每个 pass 的输入输出变得明确，不会“隐式依赖局部变量”。

### 4.2 `diag_helpers`（统一错误语法）

提供这些函数即可（不需要复杂框架）：

* `fmt_origin(o) -> str`
* `mk_diag(code, message, primary, related=..., chain=..., details=...) -> Diagnostic`
* `raise_link_error(code, message, *, primary, related=..., chain=..., details=...) -> NoReturn`

  * 内部 `raise LinkerDiagError(mk_diag(...))`
* `push_chain(diag, *segs) -> Diagnostic`（偶尔需要）

**原则**：pass 里禁止手写 `Diagnostic(...)`，全部走 helper。

### 4.3 `policy.py`（决定性策略集中）

把以下策略集中，避免散落：

* `stable_sorted(iterable, key=...)`
* `pick_owner(owners: set[str]) -> str`（你现在是 `sorted(owners)[0]`）
* `mangle_suffix(unit_id) -> str`
* （可选）`stable_unit_order(units)`、`stable_label_order(labels)`

**好处**：未来你改策略，只改一个文件；golden tests 更稳定。

### 4.4 `origin_seal`（Stage 0.5）

统一检查（并可规范化）：

* `ProofUnitIR.origin`
* 每个 `LIRStmt.origin`
* 如果你们规定某些字段必须带 origin（例如 symbol def），也在这里检查

缺失则：

* `E_MISSING_ORIGIN`
* `primary_origin=None`
* `details` 必须含：`unit_id`, `node_kind`, `where`

---

## 5) Pass 拆分规则（防止 Stage1 再次膨胀）

### Stage1_collect：只建表，不跨 unit 推理

做：

* scope imbalance guard（unit 内）
* raw token forbid（strict 模式）
* 收集：globals、labels、label_origin、owners、kind_by_unit、exports_by_unit
* 生成 `UnitInfo`

不做：

* unresolved/leakage/export 检查

### Stage1_lint：只应用规则

只读 `ctx.*` 表，做：

* `E_UNRESOLVED_LABEL`
* `E_CROSS_UNIT_HYP_LEAKAGE`
* `E_NON_EXPORTED_LABEL_REF`

**好处**：lint 增长只会涨在 lint 文件，不会污染 collect。

---

## 6) 迁移步骤（一次性降低技术债，但不破 CI）

这是一条“每步都可提交 PR、每步可被现有测试保护”的路径：

### PR1：引入横切基础设施（不改业务）

1. 新增 `linker/errors.py`，把 `LinkerError/LinkerDiagError` 移过去
2. 新增 `linker/diag_helpers.py`，并把 `LinkerDiagError.__str__` 的 origin 格式化统一到 `fmt_origin`
3. 在现有 `linker_v0.py` 里，把所有 `Diagnostic(...)` 改成 `raise_link_error(...)`（纯机械替换）

**收益**：重复大幅减少，错误风格统一。

### PR2：引入 LinkContext（仍不拆 pass）

1. 新增 `linker/context.py`
2. `LinkerV0.link()` 里先创建 ctx，但仍调用原 `_stage1/_stage4/_emit`
3. 逐步把 `_stage1` 的返回值改为写 ctx 字段（先写不删）

**收益**：中间态显式化，为拆 pass 铺路。

### PR3：拆最独立的后端（风险最低）

1. 拆 `_emit` → `passes/stage7_emit.py`
2. 拆 relocation → `passes/stage6_reloc.py`

### PR4：拆 Stage4

1. `_stage4` → `passes/stage4_deps.py`
2. 统一 unresolved 处理到 Stage1（Stage4 不再抛裸 `LinkerError`）

### PR5：拆 Stage1（最大块，最后做）

1. `_stage1` 拆成：

   * `passes/stage1_collect.py`
   * `passes/stage1_lint.py`
2. 引入 `exports_by_unit` 到 ctx，lint 只读它

### PR6：加入 Stage0.5 origin seal（M1.2a 完成标志）

1. 新增 `passes/origin_seal.py`
2. orchestrator 把它放在最前
3. 加 `adv_m12_missing_origin_rejected_stage0` 测试

---

## 7) 质量闸门（还债必须“有硬约束”）

为了防止重构变成“整理代码但技术债继续长”，建议加三条 CI 闸门：

1. **行数闸门（软硬结合）**

* 例如：`linker_v0.py` ≤ 250 行
* `passes/*.py` ≤ 300 行
  （用一个简单的 test 或 pre-commit 检查即可）

2. **诊断稳定闸门**

* `golden_m12_diagnostic_stable_snapshot`：同输入两次，diag JSON 完全一致

3. **确定性策略集中闸门**

* 禁止在 pass 内部直接 `sorted(x)` 决定策略（允许，但要用 `policy.stable_sorted` 或 `policy.pick_owner`）
* 用一次轻量 grep/lint 或 code review 规则即可

---

## 8) 最终你会得到的“低债务 LinkerV0”形态

* 入口很短：阶段顺序一目了然
* 每个 pass 可单测：给 ctx，跑函数，断言 ctx 字段或 diag
* diag 统一：错误码/链条/origin/详情格式稳定
* 决定性集中：排序、owner、suffix 策略一处定义
* Stage1 不再膨胀：collect 与 lint 分离
