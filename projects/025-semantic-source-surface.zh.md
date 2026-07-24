# Project 025：语义包的生成源码表面与惰性详化

> 状态：Phase 0–2 与 Phase 5 已完成；Phase 3/4 的语义、往返、跨包与确定性门已通过
> （2026-07-19）；G2/G3 曾因既有后端转换缺少通用发射契约而按纪律停止。
> **该阻塞已由第 10 节裁决闭合（2026-07-19）**：采用通用发射契约
> `emit_semantic_metamath_theory`，否决 legacy sidecar 发射路径，G2 重定义为
> 帧等价门；待执行 Phase 0E / 3E / 4E（见 10.5）。
> Phase 0E / 3E 发射接通后，G2a 曾因基线含派生语法定理 `weq`/`wel` 而再次
> 停止上报（§11.3）。**该阻塞已由第 12 节裁决闭合（2026-07-19）**：G2a 携带
> 由比较器机械派生的派生语法定理排除集；否决为其新增语义表示，否决改动
> 验收区间；发射层零特例。Phase 3E（续）已全门通过（§13）。
> Phase 4E 曾因默认 replay pipeline 生成包的依赖元数据非法（裸路径写入
> `project.dependencies`）无法构建基线而停止（§13.3）。
> **该阻塞已由第 14 节裁决闭合（2026-07-19）**：基线权威在 `.mm` 发射产物，
> 不在打包元数据；许可免安装执行基线 build 或修复元数据写出 bug，
> 二者均不得触及发射内容代码路径。
> Phase 4E（续）又因免安装执行的依赖导出接线缺陷产生 `0` 后缀符号分叉基线
> 而停止（§15.2）。**该阻塞已由第 16 节裁决闭合（2026-07-19）**：分叉产物
> 不是合格基线；修复接线重取基线，不得在比较器做 token 归一化。
> Phase 4E（再续）以合格基线推进后，G2a 又在 `df-cleq` 命中 primitive rule
> 发射表面的 mandatory `$f` 顺序差异而停止（§17）。
> **该阻塞已由第 18 节裁决闭合（2026-07-19）**：发射绑定工件增记源序
> floating 数据（§10.3 声明级发射数据范畴），calculus canonical 顺序契约
> 不变。
> **Phase 0F / 3F 回归 / 4E（三续）已全部完成（§19，2026-07-19）：
> logic 与 set-theory 两切片的 G2a/G2b/G3/G4/G6 全部通过，Phase 4E 闭合，
> 本项目全部验收门已过。**
>
> **工具链边界更新（[Project 029](029-catalog-compiler-boundaries.zh.md)，
> 2026-07-21）：**本项目继续规范生成语义源码表面、惰性详化、frame
> equivalence 与 backend 行为。Project 029 取代“partition 结果决定公共
> ownership”的解释，并把 Transpiler 完整原始历史迁入
> `catalog-compiler`，作为注入 backend。下文命令与测量继续作为历史实施记录。
>
> 规范性依据：[Reference 011](../references/011-language-as-first-class.zh.md)、
> [Reference 012](../references/012-defining-structures-axioms-and-proofs.zh.md)、
> [Reference 013](../references/013-proof-api-for-verification-construction-search-and-exchange.zh.md)、
> [术语规范 000](../references/000-terminology.zh.md)。
>
> 上游项目：[Project 024](024-first-class-language-refactor.zh.md)（语义内核，已到 Phase 5E）。
> transpiler 的 semantic-profile pipeline（`mm_transpiler.semantic` /
> `semantic_codegen` / `semantic_package`）是本项目的直接改造对象。
>
> 本文中的"必须（MUST）""不得（MUST NOT）""应当（SHOULD）"具有规范性含义。
> **本项目所有设计决策均已闭合。执行者遇到本文未覆盖的决策点时，必须停止并上报，
> 不得自行发明。**

---

## 0. 目标与动机

当前 semantic-v2 codegen 生成的源码表面存在四个问题：

1. 断言引用是字符串索引（`ASSERTIONS_BY_LABEL['mulcomd']`），IDE 无法跳转、补全、检查；
2. 假设按位置访问（`proof.hypotheses[0]`），中间步骤结论不可见；
3. 全部证明在 import 时详化（`PROOFS = {label: prove_x(), ...}`），四领域 import 需 91 秒；
4. 断言签名以嵌套构造子调用渲染，不符合数学传统写法。

本项目只改**生成源码表面**（codegen 输出的公共写作形态）与其所需的薄简化接口，
不改断言应用内核、BuilderV2、linker 与验证器。

成功判据：同一 set.mm 区间，新表面生成的包通过第 6 节全部验收门，
且 import 成本显著低于急切详化基线。

---

## 1. 核心裁决（全部已闭合）

### 1.1 断言即模块级绑定，import 图即依赖图

- 每条公理、定义、定理在其归属模块中必须是一个模块级 Python 绑定，
  绑定名 = 消毒后的 canonical label。
- 跨模块引用一律使用 Python import。字符串索引视图（`SIGNATURES` 等）保留，
  但降级为由模块绑定**派生**的只读索引，不再是事实源。
- 模块归属由 partition 决定；partition 的拓扑序校验（消费者不得先于依赖）
  保证模块级 import 无环。
- 同模块引用直接使用模块级名字，不写 import。
- 每个生成模块必须生成 `__all__`：只含断言句柄绑定名，按声明顺序排列。
  `prove_*` 证明函数保留为模块级绑定（利于 traceback / coverage / 调试），
  但不入 `__all__`，按 Python 惯例视为非公开细节；句柄是证明体的唯一权威通道。
- 字符串索引派生视图按**类型**（断言句柄）过滤模块属性，与命名无关。

### 1.2 头部导入与局部导入规则

- **文件头只允许**：`from __future__ import annotations`、框架公共物
  （`THEORY`、`Provable`、类型注解所需的 `ProofAuthor`/`CompleteProof` 等）、
  标准库。
- **所有跨模块断言引用一律在 proof 函数体内局部 import**（含同包跨模块与跨包）。
- 不做基于引用频次的头部提升（明确排除，见第 7 节）。
- 生成文件头部必须包含固定注释，说明局部 import 是配合惰性详化的刻意选择。
- ruff 规则 PLC0415 对生成包关闭（写入生成包的 ruff 配置）。

### 1.3 Theory 简化接口与注册语义

- 在 `skfd.authoring` 新增只读 `Theory` 简化接口（新模块，**只增不改**既有内核模块），
  绑定 language / calculus / catalog / 断言应用许可集 / 上游接口摘要。
- 生成包的 `_theory.py` 实例化 `THEORY`，并固定上游包接口摘要（出错即拒绝）。
- `THEORY.theorem(...)` / `THEORY.axiom(...)` / `THEORY.definition(...)`
  在模块顶层调用即声明并注册进包级断言目录：
  - 重复 label 或断言标识符必须出错即拒绝；
  - 注册顺序 = build 导入顺序 = partition 顺序；
  - 这是显式声明调用，不是隐式 import 副作用（Reference 011 不变量 L1 的边界内）。
- `proof_id` 由 label 确定性派生，不在生成源码中显式书写。
- `ProofAuthor` 的构造参数（calculus/catalog/profile/active_distinct）由
  `THEORY` 与签名派生，证明体不重复书写。

### 1.4 惰性详化

- `@<assertion>.proof` 装饰器只登记证明体 callable，**不执行**。
- 详化触发点仅限三处：首次访问 `<assertion>.implementation`、
  `THEORY.verify_all()`（或既有验证入口）、构建发射 `.mm` 时。
- **import 永远不详化**。证明体错误因此从 import 时移到验证/构建时，
  这是有意的行为变化，必须写进生成包 README。
- `PROOFS` 字典替换为惰性只读映射视图（按需详化并缓存 `CompleteProof`）。

### 1.5 签名的 Unicode 字符串表面与编解码往返门

- premises / conclusion 的默认生成表面是**裸 Unicode 记法字符串**
  （`premises=("φ → A ∈ ℂ", ...)`），由 NotationSpec 驱动的解析器
  在声明边界转换为项（`Term`）。
- **同一性永远在项**：摘要、相等性、断言目录只认项；字符串是 concrete syntax。
- 字符串中不含判断记号 `⊢`；provable 判断由参数位置（premises/conclusion）表达。
- 底层 API 同时接受 `str | Term | Judgment`：`Provable(...)` 构造子保留在
  `notation.py` 中供手写与 facade 回退使用，但默认生成表面不使用它。
- 文法采用最小括号 + 版本化优先级表；优先级/结合性属于生成的 `notation.py`
  （NotationSpec 政策），不是散落约定。
- **编解码往返门**：transpiler 从权威项 `render()` 出字符串写入源码，
  同时校验 `parse(render(term)) == term`。往返失败的构造子出错即拒绝，
  该断言的签名退回 typed facade（构造子调用）形式并记录到生成报告。
- typed facade 构造函数保持可用；`Provable` 同时接受 `str | Term`。

### 1.6 模式变量的保序声明

- 模式变量以 `schema=("φ:wff", "A:class", "B:class", "C:class")` 形式
  在 `THEORY.theorem/axiom/definition` 中声明：
  - 位置顺序 = set.mm floating 顺序，是 ABI，不得按 kind 分组重排；
  - 每项格式为 `"<显示名>:<变量种类名>"`；变量种类名映射到语言的
    variable kind（`wff` / `setvar` / `class`）；
  - 所有者为该断言（Reference 012 §2.1 的归属纪律）。
- 字符串签名的解析作用域即这组已声明变量；未声明变量出现即出错拒绝。
- 需要显式代入时，`subst` 的键为被应用断言的模式变量显示名（字符串），
  值为记法字符串或项；简化接口负责转换为内核的
  `Mapping[VariableRef, Term]`。
- Python 绑定标识符只用 ASCII（如需解包写 `ph, A, B, C = x.schema_variables`）；
  Unicode 只出现在字符串与注释中（`ℂ` 等字符经 NFKC 归一会与 ASCII 撞名）。

### 1.7 装饰器族

首批只有三项，均为**接口政策/元数据，不进语义摘要**：

- `@<assertion>.proof`：唯一的装饰器，登记证明体（见 1.4）；
  装饰器语法只用于此处（它装饰的是真函数）；
- `deprecated="<reason>"`：`THEORY.theorem/axiom/definition` 的关键字参数
  （断言句柄是实例绑定，PEP 702 的 `@deprecated` 对其不生效，故不用装饰器）。
  数据源为 set.mm 的 `(New usage is discouraged.)` 标记（见 Phase 2 的兜底）；
  被 `proof.use()` 引用时产生 warning 级诊断，并写入目录元数据；
- `internal=True`：关键字参数，不进入公开 manifest。

不得增加其他装饰器或政策关键字。

### 1.8 步骤结论注释

- 生成器把内核算出的每步结论渲染为行尾注释；premises/conclusion
  为字符串表面时不再重复注释。
- 注释是派生的非语义工件：再生成时重算、永不 parse 回、不进摘要。
- 截断规则确定性：行宽上限 100 列，超出以 `…` 截断。
- codegen 提供 `--no-step-comments` 开关；默认开启。

### 1.9 假设与证明函数命名

- 假设解包名固定为 `h1..hN`，行尾附渲染注释。不做语义化派生命名。
- 证明函数名固定为 `prove_<消毒后 label>`，不使用匿名 `_`
  （便于 traceback、profiling 与命名一致性审计）。

### 1.10 命名消毒与碰撞

- 沿用现有消毒政策（如数字开头加 `mm_` 前缀），补充 Python 关键字与
  软关键字全表检查。
- 碰撞检查范围：消毒后 label 之间、断言句柄名与任何 `prove_*` 证明函数名
  之间（如 label `prove-x` 消毒后撞上 `prove_x`）、与框架公共名
  （`THEORY`、`Provable` 等头部 import）、与 `__all__` 及 dunder 名。
  任何碰撞必须生成失败，不得静默改名。

### 1.11 manifest v2

- 文件名沿用 `transpiler-manifest.json`；新 schema `mm-transpiler-manifest-v2`，
  在 v1 基础上新增：
  - `semantic_interface_digests`：language / binding / calculus / catalog 摘要；
  - `notation_version`：记法政策版本与摘要；
  - `ownership`：label → dotted 模块路径的显式映射（v1 `modules` 的正式化）。
- 下游包生成时通过上游 manifest 的 `ownership` 解析跨包 import 路径；
  缺失即出错拒绝。

### 1.12 术语与命名一致性

- 本项目全部文档、代码标识符、文件名必须与
  [术语规范 000](../references/000-terminology.zh.md) 一致。
- 本项目引入的新术语（见第 8 节）必须在实施结束前登记进术语规范
  （中英两版），或改名归并到既有术语。
- 发现既有代码名与术语表冲突时不擅自改名，记录到实施报告。

### 1.13 definition 分类政策显式化

- 现行"无前提且 label 以 `df-` 开头即 definition"的启发式必须从 pipeline
  代码移入 semantic profile，成为显式、版本化的政策字段。
- 行为保持不变；仅事实源位置改变。

---

## 2. 黄金样张

以下样张是验收参照。类名与函数名如与实施时的 skfd 实际拼写冲突，
以 skfd 为准并更新本节，但结构与分工不得改变。

### 2.1 定理与证明

```python
# metamath_numbers/complex/field_and_order.py
# GENERATED by mm-transpiler (semantic).
# Function-local imports are intentional: proof bodies elaborate lazily.
from __future__ import annotations

from skfd.authoring.proof_author import ProofAuthor
from skfd.authoring.assertion import CompleteProof

from metamath_numbers._theory import THEORY

__all__ = ["mulcan2d"]   # 断言句柄，按声明顺序；prove_* 不入 __all__

# ── mulcan2d ─────────────────────────────────────────────────────────

mulcan2d = THEORY.theorem(
    "mulcan2d",
    schema=("φ:wff", "A:class", "B:class", "C:class"),
    premises=(
        "φ → A ∈ ℂ",
        "φ → B ∈ ℂ",
        "φ → C ∈ ℂ",
        "φ → C ≠ 0",
    ),
    conclusion="φ → ((A · C) = (B · C) ↔ A = B)",
    doc="Cancellation law for right-multiplication by a nonzero complex number.",
)

@mulcan2d.proof
def prove_mulcan2d(proof: ProofAuthor) -> CompleteProof:
    from metamath_logic.prop.equivalence import bitrd
    from metamath_numbers.complex.core import mulcand, mulcomd
    from metamath_set_theory.classes.equality import eqeq12d

    h1, h2, h3, h4 = proof.hypotheses      # h1: ⊢ φ → A ∈ ℂ …
    s1 = proof.use(mulcomd, h1, h3)        # ⊢ φ → (A · C) = (C · A)
    s2 = proof.use(mulcomd, h2, h3)        # ⊢ φ → (B · C) = (C · B)
    s3 = proof.use(eqeq12d, s1, s2)        # ⊢ φ → ((A·C) = (B·C) ↔ (C·A) = (C·…
    s4 = proof.use(mulcand, h1, h2, h3, h4)
    s5 = proof.use(bitrd, s3, s4)          # ⊢ φ → ((A · C) = (B · C) ↔ A = B)
    return proof.qed(s5)
```

要点：无 `REPLAYS`；无字符串 label；无位置假设访问；import 时不详化。

### 2.2 公理与定义

```python
ax_ext = THEORY.axiom(
    "ax-ext",
    schema=("x:setvar", "y:setvar", "z:setvar"),
    conclusion="∀z (z ∈ x ↔ z ∈ y) → x = y",
    distinct=(("x", "z"), ("y", "z")),
    doc="Axiom of Extensionality.",
)

df_tr = THEORY.definition(
    "df-tr",
    schema=("A:class",),
    conclusion="Tr A ↔ ∪ A ⊆ A",
    doc="Define the transitive class predicate.",
)

# deprecated / internal 是政策关键字，不是装饰器：
syl5eq = THEORY.theorem(
    "syl5eq",
    ...,
    deprecated="Use eqtrid instead.",
)
```

`distinct` 端点为模式变量显示名；简化接口转换为 typed `DistinctPair`。

### 2.3 `_theory.py`（骨架）

```python
# metamath_numbers/_theory.py
# GENERATED by mm-transpiler (semantic).
from skfd.authoring.theory import Theory

from metamath_set_theory._theory import THEORY as _UPSTREAM

THEORY = Theory.extend(
    _UPSTREAM,
    theory_id="metamath-numbers#theory:main",
    language=LANGUAGE,            # 本包语言扩展
    binding=BINDING,
    calculus=CALCULUS,
    expected_upstream_digests={...},   # 出错即拒绝
)
```

---

## 3. 实施阶段

每个阶段完成后必须运行第 6 节对应验收门，全部通过才能进入下一阶段。
proof-scaffold 仓遵守其 `AGENT.md`（uv / ruff / mypy strict / pytest）；
transpiler 仓遵守其 `README.md` 记载的工具链与验证流程。

分工：**Phase 0（skfd 框架与 API 形态）由高能力模型/人工完成并冻结接口**；
Phase 1–5 交低成本执行模型，以 Phase 0 冻结的接口为契约，不得修改
`skfd.authoring.theory` 的公开签名。

### Phase 0：skfd 侧简化接口（仓库：proof-scaffold）

新增 `src/skfd/authoring/theory.py`（只增不改既有模块）：

1. `Theory`：绑定 language/calculus/catalog/许可集/上游摘要的只读简化接口；
   `Theory.extend()` 校验上游摘要，不符即出错拒绝。
2. `Theory.theorem/axiom/definition`：按 1.3、1.6 的契约构造并注册
   `AssertionSignature`（内部复用既有 `resolve_axiom` / `resolve_definition` /
   `AssertionSignature`），返回带 `.proof` 装饰器与 `.implementation`
   惰性属性的断言句柄对象。
3. 字符串签名解析：复用 `skfd.authoring.parsing` 的 NotationSpec 驱动解析；
   若缺少 judgment 级入口，新增薄封装（parse 到 `Term` 后包装 `Judgment`），
   不新建第二套解析器。
4. `deprecated` / `internal` 政策关键字挂接（1.7）。
5. 单元测试：注册冲突拒绝、上游摘要不符拒绝、惰性详化只触发一次、
   `schema` 顺序保持、未声明变量出错拒绝、`subst` 字符串键转换。

验收：`ruff check .`、`mypy .`、`python3 -m pytest` 全绿；
既有测试零回归。

### Phase 1：transpiler 记法与 profile 扩展（仓库：transpiler）

1. semantic profile 增加可选 `notation` 表：每个构造子的 Unicode 词元、
   优先级、结合性；缺失条目出错拒绝并回退 ASCII 词元（1.5）。
   初稿可从 set.mm `$t` 排版块派生，但写入 profile 后 profile 是事实源。
2. `df-` 分类启发式移入 profile 显式字段（1.13），行为不变。
3. 渲染器：从项渲染最小括号 Unicode 字符串；实现
   `parse(render(term)) == term` 校验；失败构造子记录并回退 facade。
4. 单元测试：往返性质测试（覆盖全部 profile 构造子 + 随机项）、
   歧义文法拒绝测试。

验收：transpiler 测试全绿；对 logic profile 的全部构造子往返通过率报告。

### Phase 2：codegen 新源码表面（仓库：transpiler）

改造 `semantic_codegen.py`：

1. 断言渲染为模块级绑定（1.1）+ `THEORY.theorem/axiom/definition` 表面
   （2.1/2.2 样张形态）；
2. 局部 import 块：由每条证明的步骤断言集合导出，路径查本包 partition
   与上游 manifest `ownership`（1.11）；同模块引用不生成 import；
   import 块内按模块路径字典序排序（再生成确定性）；
3. `@x.proof` 惰性登记 + 惰性 `PROOFS` 视图（1.4）；
4. 步骤结论注释与截断（1.8）、假设命名（1.9）、消毒与碰撞检查（1.10）、
   `__all__` 生成（1.1）；
5. manifest v2 写出（1.11）；
6. `deprecated` 元数据：若上游解析器（metamath-replay Database）未暴露
   set.mm discouraged 标记，则本项以空集接线并在报告中注明，机制仍须落地。

验收：codegen 单元测试；同一输入两次 clean 生成 byte-identical。

### Phase 3：logic 域纵向切片

1. 用新表面生成 logic 域：semantic profile 用
   `transpiler/benchmarks/semantic-profile-setmm-logic-v2.json`，
   source / `--graph` / `--partition` / `--start` / `--end` 参数**复用**
   `transpiler/benchmarks/benchmark_four_domains_semantic_v2.py` 中
   logic 域的现有配置，不得另行选择；命令形态：

   ```bash
   uv run mm-transpiler <source.mm> <输出目录> \
     --package-name metamath-logic-sem \
     --semantic-profile benchmarks/semantic-profile-setmm-logic-v2.json \
     --graph <同基准脚本> --partition <同基准脚本> \
     --start <同基准脚本> --end ax-ext
   ```
2. 若生成包尚无 `.mm` 发射路径，接通既有
   `build_semantic_replay_plan → legacy 后端转换 → BuilderV2` 路径生成
   `build.py`（skfd 侧参照 024 Phase 5D 的 mp2b 先例；
   `skfd.authoring.legacy_replay` / `metamath_lowering`）。
   这是既有内核能力的接线，不是新语义；若发现需要改动内核语义，停止上报。
3. 跑第 6 节全部验收门。

### Phase 4：跨包金丝雀（两包链）

1. logic 包（Phase 3 产物）作为上游；
2. 生成 set-theory **前缀区间**：`--start ax-ext --end wne`
   （`wne` 是现有 `metamath-set-theory/transpiler-manifest.json` 中第二个
   partition 模块的首个 label；`--end` 为 exclusive，故只生成第一个模块，
   即 extensionality 块，约 208 条）。set.mm 顺序的前缀区间天然依赖闭合。
   `--dependency` 指向 Phase 3 的 logic 包；graph/partition 复用基准脚本中
   set-theory 域的配置；
3. 验证跨包局部 import 解析、上游摘要 pin、同区间字节对比
   （基线：默认 replay pipeline 对同一区间生成的包所发射的 `.mm`）；
4. 跑第 6 节全部验收门。

### Phase 5：报告与术语登记

1. 实施报告：各阶段结果、往返通过率、回退 facade 的构造子清单、
   性能数据（第 6 节 G5）、遇到的未闭合决策；
2. 新术语登记进 `references/000-terminology.zh.md` 与 `.en.md`（第 8 节）；
3. 向 Project 021/022/023 反馈表面形态对其计划的影响（只记录，不改动）。

---

## 4. 与既有工作的边界

- 本项目不动断言应用内核、`ProofAuthor.use()/qed()` 语义、BuilderV2、
  linker、三套验证器。
- **边界澄清（2026-07-19，见 10.2）**：`skfd.authoring.metamath_lowering`
  （及 `legacy_replay` 别名）是后端适配层，**不在**上一条保护清单内；
  按 10.2 的约束对其做行为扩展属于本项目范围。
- Reference 013 §8.1 的 `verify_proof()` 公开入口不在本项目范围，
  但 Phase 0 的 `Theory` 简化接口是其地基，接口设计不得与 013 冲突。
- 现有磁盘上的过渡格式包（metamath-set-theory / numbers / number-theory）
  不迁移、不删除。

---

## 5. 执行纪律（对执行模型）

1. 遇到本文未闭合的决策：停止该项，记录到报告，继续其余无依赖项。
2. 不得为通过验收门弱化检查（跳测试、`--no-verify`、放宽比较）。
3. 每个阶段结束提交阶段报告：完成项、验收命令与输出摘要、偏离与原因。
4. 不修改 references / 其他 projects 文档（Phase 5 的术语登记除外）。

---

## 6. 验收门

- **G1 往返门**：切片内全部签名满足 `parse(render(term)) == term`；
  回退 facade 的构造子列入报告。
- **G2 帧等价门**（2026-07-19 重定义，理由与细则见 10.4；
  基线不变——logic 域基线：既有 pipeline 的 logic `.mm` 产物；
  Phase 4 基线：同区间默认 replay pipeline 产物）：
  - **G2a（硬门）**：新表面包发射的 `.mm` 与基线经独立 parser 解析后
    逐断言帧等价（label 序列、typecode+表达式、mandatory 假设、
    distinct 约束全部相等；假设 label 按位归一化后比较）。
    label 集合/序列条款按第 12 节修订：比较在剔除**机械派生的
    派生语法定理排除集**后进行（细则见 12.2）；
  - **G2b（只报告）**：对基线逐字节 diff 并分类汇总差异写入生成报告，
    字节等同不再是门槛。
- **G3 验证器门**：发射的 `.mm` 通过可用的独立验证器
  （mmverify / reference Metamath / metamath-knife，按 transpiler README
  的验证流程；实际运行了哪些必须在报告中列明）。
- **G4 确定性门**：两次 clean 生成 byte-identical（含 manifest）。
- **G5 性能报告**（只报告不设硬预算）：签名字符串解析总耗时、
  单模块 import 耗时、包 import 总耗时（新表面惰性 vs 急切详化基线对比）、
  全量生成耗时。
- **G6 工具链门**：proof-scaffold 与 transpiler 两仓 `ruff check .`、
  `mypy .`、`python3 -m pytest` 全绿。

---

## 7. 明确不做

- 不动内核与验证器权威（第 4 节）；
- 不迁移过渡格式包，不做四领域全量重生成（另立项目）；
- 不做交换档案格式（Reference 013 轨道 A3）；
- 不做 `ProofState` / goals / holes（轨道 B）；
- 不做引用频次的头部 import 提升（K 规则）；
- 不做语义化假设命名；
- 不做 family/combinator（Project 023 职责）；
- 不新增 1.7 之外的装饰器；
- 不做 Unicode 之外的第二套显示记法（LaTeX 等）。

---

## 8. 新增术语（待登记）

| 英文 | 中文 | 定义 |
| --- | --- | --- |
| Generated source surface | 生成源码表面 | 生成的 Python 源代码所呈现的公共写作形态；它是 concrete syntax，不是语义事实源。 |
| Lazy elaboration | 惰性详化 | 证明体登记后延迟到首次访问实现、验证或构建发射时才执行的详化策略；import 不触发详化。 |
| Step-result comment | 步骤结论注释 | 生成器由内核重算结果渲染的行尾注释；派生、非语义、再生成时重算、不进摘要。 |
| Header/local import rule | 头部/局部导入规则 | 文件头只含框架公共物、跨模块断言引用一律函数内局部 import 的确定性生成规则。 |
| Assertion handle | 断言句柄 | `THEORY.theorem/axiom/definition` 返回的模块级绑定对象，承载签名、`.proof` 登记与惰性 `.implementation`。 |
| Emission binding | 发射绑定 | 由 profile 与源数据库在生成时派生的版本化声明级发射数据（`$c`/`$v` 表、formation `$a` 条目、混排发射序列、假设标签政策版本）；只含语言事实的 concrete syntax，不含证明内容。 |
| Frame-equivalence gate | 帧等价门 | 以独立 parser 解析两份 `.mm` 后逐断言比较 label、typecode+表达式、mandatory 假设与 distinct 约束的验收门；假设 label 按位归一化，字节序不参与判定。 |
| Derived syntax theorem | 派生语法定理 | 结果 typecode 属于语言 sort 的 term typecode、而非任何 judgment typecode 的源 `$p` 断言（如 set.mm 的 `weq`/`wel`）；属 concrete syntax 层的缩写便利，可由 formation 声明组合完全重放，不承载 judgment 级数学内容。 |

---

## 9. 实施报告（2026-07-19）

### 9.1 Phase 1–2

- semantic profile v2 已加入显式 `notation` 政策；logic profile 的 24 个构造子全部使用
  Unicode token，并保留 ASCII alias。`definition_prefixes=("df-",)` 成为显式分类政策。
- 生成包以 `_theory.py` 建立 language / binding / calculus / notation / `THEORY`；
  partition topic 模块声明模块级断言句柄及 `@handle.proof` 函数。
- 跨模块与跨包断言只在证明函数体内导入；`__all__` 只含句柄；`SIGNATURES`、
  `ASSERTIONS_BY_LABEL` 和惰性 `PROOFS` 均由句柄目录派生。
- manifest 已升级为 `mm-transpiler-manifest-v2`，记录四项接口摘要、notation 版本与摘要、
  `ownership` 和生成报告。下游缺失 v2 ownership 时出错即拒绝。
- 默认生成步骤结论注释并确定性截断到 100 列；`--no-step-comments` 已接通。
- set.mm discouraged 标记仍未由 `metamath-replay.Database` 暴露；`deprecated` 机制按空集接线，
  manifest 明确记录 `deprecated_parser_support: false`。

### 9.2 Phase 3：logic 纵向切片

输入复用四领域 benchmark 的 logic graph、K=14 named partition 与 profile；范围为
`--start wi --end ax-ext`。

| 项目 | 结果 |
| --- | --- |
| 模块 | 14 |
| 断言句柄 | 2,710 |
| 惰性证明 | 2,677 |
| 签名编解码往返 | 5,246 / 5,246，0.0799 s |
| ASCII / typed facade 回退 | 0 / 0 |
| 全量生成 | 约 4.6 s |
| 包 import | 约 0.40 s |
| `THEORY.verify_all()` | 约 0.92 s，全部通过 |
| 急切 import 基线 | 1.4489 s（2026-07-18 固定 benchmark） |
| 两次 clean 生成 | byte-identical（排除 import 产生的 `__pycache__`） |

### 9.3 Phase 4：跨包金丝雀

- 以上 logic 包作为上游；set-theory 使用既有 graph/partition 的
  `--start ax-ext --end wne`，只生成 `classes.extensionality`（当前 partition 为
  223 个 graph label、221 个断言句柄、216 个证明）。
- 上游摘要 pin、manifest ownership 路径、跨包函数内 import 与 Unicode notation 继承均通过；
  无 ASCII / facade 回退。
- 包 import 约 0.37 s；全部本地证明详化约 0.07 s；两次 clean 生成 byte-identical。

### 9.4 未闭合的 G2/G3 阻塞

未生成或验证 `.mm`，因此 **G2 与 G3 未通过**。调查确认这不是 topic codegen 接线即可解决：

1. `lower_replay_to_metamath_proof()` 要求 proof root 是最后位置；logic 起始定理 `a1ii`
   直接以第一个假设为 root，现有公开 lowering 会拒绝该合法证明；
2. 当前没有从 semantic theory / `MetamathProofBinding` 到 BuilderV2 的通用公开适配器；
   现有 `mp2b` 是手工绑定 token、变量、sort 和 assertion 的单例；
3. semantic catalog 不含必须发射的 formation 声明，默认 replay pipeline 的全局 `$f` label
   分配与精确 proof token 顺序也不在现有语义包契约内。

直接生成 legacy replay sidecar 可以保持字节，但违反本项目规定的语义重放发射路径；修改
lowering / BuilderV2 又越过第 4 节边界。依第 5 节第 1 条，本项停止并上报。后续必须先裁决：
新增通用 `emit_semantic_metamath_theory` 契约，或明确许可 byte-preserving legacy emission sidecar。

**已裁决（2026-07-19）**：见第 10 节。三项障碍分别由 10.2（hypothesis-root
属 lowering 适配层的行为扩展，非内核改动）、10.3（通用发射契约 + 发射绑定工件）、
10.4（G2 重定义为帧等价门，`$f` 全局分配与 proof token 顺序不再是验收对象）闭合。

### 9.5 Phase 5 反馈

- 术语已登记进中英双语术语规范。
- 对 Project 021：生成表面证明了 Assertion IR 可隐藏在句柄后，作者表面无需暴露内部 ID。
- 对 Project 022：`AssertionHandle`、字符串签名和惰性 `PROOFS` 应成为 v0.1 facade 的直接输入，
  不应恢复字符串 label 调用。
- 对 Project 023：family/combinator 必须先展开为普通句柄声明和 `proof.use()`，生成表面不新增装饰器。
- 既有命名与术语规范未发现需要跨项目重命名的冲突。

### 9.6 最终工具链

| 仓库 | Ruff | mypy strict | pytest |
| --- | --- | --- | --- |
| proof-scaffold | 通过 | 93 个源码文件通过 | 259 passed，89.31% coverage |
| transpiler | 通过 | 17 个源码文件通过 | 50 passed |

独立验证器未运行，因为 G2 阻塞导致没有可交给 mmverify / metamath-knife 的新 `.mm` 产物；
不得把 `THEORY.verify_all()` 的语义重放描述为 G3 的独立验证器结果。

---

## 10. G2/G3 阻塞裁决（2026-07-19，全部已闭合）

本节针对 §9.4 上报的三项障碍给出规范性裁决，与第 1 节同级：
**执行者遇到本节未覆盖的决策点时，必须停止并上报，不得自行发明。**
本节公开接口形态视为 Phase 0 同等级的冻结契约。

### 10.1 路径裁决：采用通用发射契约，否决 legacy sidecar

- **必须**新增通用公开契约 `emit_semantic_metamath_theory`
  （名称沿用 §9.4 提案，落点见 10.3）。
- **不得**以 legacy replay sidecar 作为 `.mm` 发射来源。理由：sidecar 会让
  证明拥有第二事实源，语义证明体退化为装饰，违反单一事实源纪律。
  `.mm` 的全部 `$p` 证明**必须**经
  惰性详化 `CompleteProof` → `replay_proof` → `lower_replay_to_metamath_proof`
  → BuilderV2 路径产生。
- 声明级发射数据（`$c`/`$v`、floating `$f`、formation `$a`）不是证明内容，
  **允许**由 transpiler 在生成时从 semantic profile 与源数据库派生，
  固化为版本化的**发射绑定**工件（见 10.3）。这与 notation 表同类，
  是语言事实的 concrete syntax，不构成对上一条的违反。

### 10.2 边界澄清与 hypothesis-root 支持

第 4 节保护清单为：断言应用内核、`ProofAuthor.use()/qed()` 语义、BuilderV2、
linker、三套验证器。`skfd.authoring.metamath_lowering`（及其 `legacy_replay`
再导出别名）是后端**适配层**，不在该清单内，属于本项目可改造对象。约束：

1. 只做**行为扩展**（接受更多合法输入）；既有合法输入的输出不得改变。
2. hypothesis-root 支持：`plan.root_position` 落在假设位置时，
   `lower_replay_to_metamath_proof` **必须**产出合法 `Proof`，
   其发射的 `.mm` 证明 token 序列为**该假设 label 的单元素序列**
   （对应 set.mm `a1ii` 的原生证明形态：`a1ii $p |- ph $= a1ii.1 $.`）。
3. 既有的 hypothesis-root 拒绝测试
   （`tests/feature/test_assertion_application.py` 中
   `match="root to be the final"` 一处）由本裁决**明确许可**改写为正向断言；
   这是唯一许可修改的既有测试，其余测试零回归。

### 10.3 发射绑定工件与 `emit_semantic_metamath_theory` 契约

**skfd 侧**（仓库 proof-scaffold，只增不改，新模块
`src/skfd/authoring/metamath_emission.py`）：

1. `MetamathEmissionBinding`（新只读数据类），承载声明级发射数据：
   - 常量/变量 token 表（含 token → 发射符号名）；
   - formation `$a` 条目：label、typecode、表达式 token 序列、
     mandatory floating（sort, 变量）序列；
   - **混排发射序列**：formation 与断言 label 按源顺序混排的完整有序列表；
     其中断言 label 必须构成与目录注册顺序一致的子序列，否则出错即拒绝；
   - sort → typecode 映射；
   - 假设标签政策版本字段（见第 3 条）。
2. `emit_semantic_metamath_theory(theory, binding, ctx)`：按混排发射序列
   发射声明与断言；每条 `$p` 的证明经 10.1 规定的语义重放路径产出。
   `MetamathProofBinding` 的逐断言字段（`backend_label` 等）**必须**由
   theory 与 binding **机械派生**；任何断言、token、变量、sort 缺少
   可派生映射时**出错即拒绝**，不得启发式补齐。
3. 假设标签分配政策沿用默认 pipeline：全局计数器 `mmtranspiler.hN`、
   每断言 floating（schema 顺序）先于 essential（premise 顺序）、
   跳过保留 label。该政策以版本化字段写进发射绑定工件。

**transpiler 侧**（仓库 transpiler）：

4. `semantic_package` 生成 `_emission.py`（固化 `MetamathEmissionBinding`
   数据）与 `build.py`（调用 `emit_semantic_metamath_theory`）。
5. formation 条目的 label 来源为 profile `formations` 列表；typecode、
   表达式与 floating 在生成时从源数据库派生。profile `formations` 中
   缺失源数据库对应声明、或源区间内存在 profile 未覆盖的 formation，
   均出错即拒绝。
6. manifest v2 增记 `emission_policy_version` 与发射绑定摘要；
   G4 确定性门覆盖 `_emission.py` 与 `build.py`。

### 10.4 G2 重定义的理由与细则

基线 `.mm` 的 `$f` label 全局计数（`mmtranspiler.hN` 跨模块共享计数器）与
proof token 精确顺序是默认 pipeline 的**偶然实现细节**，不是数学内容；
从语义包复现这些字节等于重新实现 legacy 偶然性，是错误的抽象目标。
故 G2 改为（已写入第 6 节）：

- **G2a 帧等价门（硬门）**：以 metamath-replay `Database` 作为独立 parser
  解析基线与新产物，要求：
  - `$a`/`$p` 的 label 序列相等；且新产物 label 集必须等于基线 label 集；
  - 每条断言的 typecode + 表达式 token 序列相等；
  - mandatory `$e` 表达式序列（按序）相等；
  - mandatory `$f`（sort, 变量）序列（按序）相等；
  - distinct 约束对集合相等；
  - 假设 label 经逐断言按位归一化后比较（`$e`/`$f` 的具体 label 文本
    不参与判定）；
  - `$c` 与 `$v` 集合相等。
- **G2b 字节对照报告（只报告）**：逐字节 diff 分类汇总写入生成报告；
  预期残余差异仅为假设 label 文本与 proof token 顺序类。
- 比较工具落点：transpiler 仓（脚本或测试），不得为通过而放宽任何一项。

G3 不变：正确性权威仍是独立验证器（mmverify / metamath-knife，
按 transpiler README 流程，实际运行者列入报告）。

### 10.5 阶段任务

- **Phase 0E**（proof-scaffold）：实施 10.2 与 10.3 第 1–3 条；单元测试
  必须覆盖：hypothesis-root 正向 lowering、映射缺失拒绝、混排序列与
  注册顺序不一致拒绝、同输入两次发射确定性。验收同 Phase 0 工具链门。
- **Phase 3E**（transpiler + logic 切片）：实施 10.3 第 4–6 条；对 Phase 3
  的 logic 包接通 `build.py` 发射，跑 G2a/G2b/G3/G4；G5 增记发射耗时。
- **Phase 4E**（跨包金丝雀）：对 Phase 4 两包链同样发射并过门；
  G2a 基线为同区间默认 replay pipeline 产物。
- **报告与术语**：第 8 节新增的 Emission binding / Frame-equivalence gate
  两条术语登记进中英术语规范；实施报告补记 G2a/G2b/G3 结果。

### 10.6 仍须停止上报的条件

1. 发射需要改动 BuilderV2、linker 或任一验证器的语义；
2. `CompleteProof` → `replay_proof` 在任一切片断言上失败；
3. G2a 出现**表达式级**差异——这意味着语义导入或渲染有错，
   不是发射政策问题，不得在发射侧打补丁掩盖。

---

## 11. Phase 0E / 3E 续实施报告（2026-07-19）

### 11.1 Phase 0E 已完成

- 新增通用 `MetamathEmissionBinding`、`MetamathEmissionContext` 与
  `emit_semantic_metamath_theory`；所有 `$p` 均走
  `CompleteProof` → `replay_proof` → `lower_replay_to_metamath_proof`
  → BuilderV2，未引入 legacy sidecar。
- hypothesis-root lowering 已支持明确的最终结果 step；实际发射 token 为对应假设 label。
- 发射器支持 formation/断言源序混排、跨包 SymbolId 复用、局部 dummy 与 proof-only
  distinct scope，并对缺失映射和注册顺序不一致 fail closed。
- hypothesis label policy 固定为 `mm-transpiler-hypotheses-v1`。
- proof-scaffold 全仓门：Ruff 通过，mypy strict 94 个源码文件通过，
  pytest 263 passed，89.54% coverage。

### 11.2 Phase 3E 已接通真实 logic 发射

semantic package 现生成 `_emission.py`、`build.py`，manifest v2 记录
`emission_policy_version` 与 `emission_binding_digest`。tiny fixture 会实际 import
生成包、发射并 link `.mm`，再由 subprocess 调用独立 mmverify。

真实 logic 范围仍为 `--start wi --end ax-ext`：

| 项目 | 结果 |
| --- | --- |
| semantic assertions / proofs / modules | 2,710 / 2,677 / 14 |
| 语义发射产物 | 2,281,737 bytes，2,734 条 `$a`/`$p` |
| 发射 / link | 约 9.16 s / 0.09 s |
| G3 | proof-scaffold `skfd.verifier.mmverify` 独立验证通过 |
| transpiler 全仓门 | Ruff 通过；mypy strict 17 个源码文件通过；52 passed |

### 11.3 G2a 调查修正与当前唯一差异

首次 G2a 比较在 `df-sb` 发现 mandatory `$f` 顺序被 semantic axiom/definition
resolution 的 canonical variable order 改写。源与 baseline 为
`ph, x, y, z, t`，semantic 产物曾为 `ph, t, x, y, z`。这不是 emitter policy：
显式 schema 顺序也是 `Theory` authoring facade 的既有契约。因此现已在
axiom/definition 签名边界恢复声明顺序，并新增逆 occurrence / canonical 顺序回归测试；
standalone `write_semantic_theory()` round-trip 同样恢复该顺序；primitive rule 继续遵守
calculus canonical 顺序的既有契约。

修正后以 metamath-replay `Database` 重新解析两份产物：

- baseline 2,736 条断言，semantic 2,734 条；
- 全部 2,734 个共同 label 的 statement、mandatory `$f`、mandatory `$e` 与
  mandatory distinct **零差异**；
- semantic 无额外 label；baseline 唯一多出 `weq`、`wel`。

`weq`、`wel` 是结果 typecode 为 `wff` 的源 `$p`（分别由 `cv` + `wceq`、
`cv` + `wcel` 导出），不是 profile 选中的 formation `$a`，也不是当前 profile
声明的 `|-` judgment assertion。现有 semantic import 因而没有可承载其签名与
`CompleteProof` 的语义对象。由 emitter 虚构 `$p`、把它们伪装成 formation `$a`、
或从 legacy proof sidecar 补出，都会违反 §10.1/§10.3。

因此 **G2a 尚未通过，Phase 3E 在此停止上报**；G2b、Phase 4E 不应在硬门失败时
宣称闭合。后续需要规范裁决以下二者之一：

1. 为 derived syntax `$p` 增加可重放的 semantic judgment / assertion 表示，并明确
   它与 language formation 的关系；或
2. 明确修改 logic 验收区间/基线，排除这类 syntax theorem。

在该裁决前不得在发射层增加 `weq`/`wel` 特例。

**已裁决（2026-07-19）**：见第 12 节。G2a 改为携带机械派生的派生语法定理
排除集；否决语义表示（越界）与区间改动（不可行）；发射层零特例的禁令继续有效。

---

## 12. G2a 派生语法定理阻塞裁决（2026-07-19，全部已闭合）

本节针对 §11.3 上报的 `weq`/`wel` 差异给出规范性裁决，与第 1、10 节同级：
**执行者遇到本节未覆盖的决策点时，必须停止并上报，不得自行发明。**

### 12.1 裁决：机械排除派生语法定理，否决语义表示与区间改动

- **定义（派生语法定理）**：源数据库中结果 typecode 属于 semantic profile
  `term_typecodes`（语言 sort 的 typecode）、且不属于任何
  `judgments[].typecode` 的 `$p` 断言。它是 concrete syntax 层的缩写便利：
  其全部内容可由 formation `$a` 组合重放（logic 切片中 `weq` = `cv`+`wceq`、
  `wel` = `cv`+`wcel`，set.mm 注释亦明言其为 syntax proof），不承载
  judgment 级数学内容。
- **否决** §11.3 方案 1（为其新增可重放的语义 judgment/assertion 表示）：
  这需要在 calculus 中引入第二类 judgment，波及断言应用内核、catalog 与
  三套验证器的语义边界，超出第 4 节保护清单允许的改造范围；且对帧等价
  已零差异的 `|-` 级内容无任何数学增益。该方向另立候选项目（见 12.4）。
- **否决** §11.3 方案 2 中"修改验收区间/基线"的形态：`weq`/`wel` 位于
  区间中部，`--start/--end` 无法排除；手工编辑基线内容等于篡改基线。
- **裁决**：G2a 的 label 集合/序列条款改为携带**机械派生的排除集**（12.2）。
  排除集由比较器从基线与 profile 自动计算，**不得**手工维护 label 名单，
  **不得**在发射层为任何 label 增加特例（§11.3 末条禁令继续有效）。

### 12.2 G2a label 条款修订细则

G2a 其余条款（表达式、mandatory `$e`/`$f`、distinct、`$c`/`$v`、
假设 label 按位归一化）全部不变。

1. 比较器必须从 semantic profile 读取 judgment typecode 集
   （`judgments[].typecode`）与 term typecode 集（`term_typecodes`）；
   判类政策的事实源是 profile（版本化），不得在比较器中硬编码 typecode 名。
2. **排除集** := 基线中结果 typecode ∈ term typecodes 且 ∉ judgment
   typecodes 的全部 `$p` label。空排除集是合法结果。
3. 门槛（全部 fail-closed）：
   - `semantic 产物 label 集 == 基线 label 集 − 排除集`；
   - `$a`/`$p` label 序列在从基线序列中剔除排除集后逐位相等；
   - semantic 产物**不得**含排除集中的 label（发射层没有对应语义对象，
     出现即说明加了特例）；
   - 基线中任何 `$p` 的结果 typecode 既不属于 term typecodes 也不属于
     judgment typecodes 时，比较失败（未知 typecode 不得静默归类）。
4. 排除集及每条的 label、typecode、判类依据必须写入生成报告
   （并入 G2b 报告）；排除集之外的任何 baseline-only 或 semantic-only
   label 仍为硬失败。

### 12.3 比较器落点与实现约束

- 落点沿用 10.4：transpiler 仓，以脚本或测试形式**提交入库**
  （§11.3 的 ad hoc 比较不算数）；输入为基线 `.mm`、semantic `.mm` 与
  semantic profile 三个路径，输出机器可读结论与报告段落。
- 解析器沿用 metamath-replay `Database` 作为独立 parser。
- 任何一项不满足即非零退出；不得为通过放宽任何比较项。

### 12.4 延后轨道

为派生语法定理提供一等语义表示（syntax 级 judgment、其与 language
formation 的关系、可重放的 syntax proof）记录为独立候选项目，归属
Reference 011 语言一等化轨道；本项目**不实施、不得部分实施**。

### 12.5 阶段任务

- **Phase 3E（续）**（transpiler）：按 12.2/12.3 落地比较器；对 Phase 3E
  的 logic 产物重跑 G2a（预期排除集恰为 `{weq, wel}`，若不同即停止上报）、
  产出 G2b 分类报告，补记 G3/G4/G5 结果。
- **Phase 4E**：按 10.5 执行；同一比较器与同一机械规则适用于 set-theory
  区间基线，不得另写第二套判类逻辑。
- **报告与术语**：第 8 节新增的 Derived syntax theorem / 派生语法定理
  登记进中英术语规范；实施报告补记排除集与各门结果。

### 12.6 仍须停止上报的条件

1. 排除集中出现结果 typecode 不属于 term typecodes 的 label，
   或基线出现 12.2 第 3 条无法判类的 `$p`；
2. 剔除排除集后仍存在任何 label 集合/序列差异，或出现 §10.6 第 3 条的
   表达式级差异；
3. Phase 4E 基线中出现本节机械规则无法判类的断言形态。

## 13. Phase 3E（续）/ 4E 实施报告（2026-07-19）

### 13.1 比较器

比较器落在 transpiler 的 `src/mm_transpiler/frame_equivalence.py`，命令为
`uv run mm-frame-equivalence BASELINE.mm SEMANTIC.mm PROFILE.json`。它以
`metamath_replay.mm_engine.Database` 解析断言，从 profile 的
`term_typecodes` 与 `judgments[].typecode` 机械判类，输出 JSON（内含可直接并入报告的
Markdown G2a/G2b 段落），任一硬门不满足即非零退出。三项 fail-closed 回归测试覆盖
机械排除、未知 `$p` typecode 拒绝及 semantic 产物含排除 label 拒绝。

### 13.2 Phase 3E（续）logic 结果

- G2a 通过：baseline 2,736、semantic 2,734 条 `$a`/`$p`；机械排除集恰为
  `{weq: wff, wel: wff}`。依据为 `wff ∈ term_typecodes={wff,setvar,class}` 且
  `wff ∉ judgment typecodes={|-}`；排除后 2,734 条断言的序列、statement、mandatory
  `$f`/`$e` 和 distinct 全部相等，semantic 无排除 label。
- G2b：非字节同一；baseline 2,264,424 bytes，semantic 2,281,737 bytes，SHA-256
  分别为 `05f2367b…debda`、`6dcc048a…047a`。差异分类为假设 label、proof token 与布局等
  非语义序列化差异。
- G3：实际运行 proof-scaffold `skfd.verifier.mmverify`，2,677 个 `$p` 全部验证通过。
- G4：两次 clean 生成目录 byte-identical（含 `_emission.py`、`build.py`、manifest；
  排除运行时 `__pycache__` 与另行产生的 `.mm`）。
- G5：全量生成 7.75 s；发射 7.528 s；link 0.079 s；产物 2,281,737 bytes。
  签名解析/import 数据沿用 §9.2（5,246/5,246、0.0799 s；包 import 约 0.40 s，
  急切基线 1.4489 s）。

### 13.3 Phase 4E 停止上报

按既定 set-theory graph/partition、`[ax-ext,wne)` 与 logic dependency 已成功生成语义包：
221 个断言句柄、216 个证明、1 个模块，生成 5.66 s；profile 机械得到本区间 formations
`cab`、`wnfc`。但默认 replay pipeline 以生成目录路径作为 `--dependency` 时，把裸路径写入
生成 `pyproject.toml` 的 `project.dependencies`，setuptools 以“must be pep508”拒绝构建，
因而未得到规范要求的同区间 baseline `.mm`。§12 未裁决可改用手工切片基线或绕过默认
pipeline；依停止纪律，未宣称 Phase 4E 的 G2/G3/G4 闭合，也未提交 `.mm` 产物。

**已裁决（2026-07-19）**：见第 14 节。基线权威在 `.mm` 发射产物而非打包元数据；
许可免安装执行基线 build 或修复默认 pipeline 的依赖元数据写出 bug。

### 13.4 G6 与术语

两仓工具链全绿：proof-scaffold Ruff 通过、mypy strict 94 个源码文件通过、pytest
263 passed（89.54% coverage，2 个既有 warning）；transpiler Ruff 通过、mypy strict
19 个源码文件通过、pytest 55 passed。Emission binding、Frame-equivalence gate 与
Derived syntax theorem 已登记进中英术语规范。除上述 Phase 4E baseline 构建阻塞外，
无偏离或未闭合决策。

---

## 14. Phase 4E 基线构建阻塞裁决（2026-07-19，全部已闭合）

本节针对 §13.3 上报的基线构建失败给出规范性裁决，与第 1、10、12 节同级：
**执行者遇到本节未覆盖的决策点时，必须停止并上报，不得自行发明。**

### 14.1 裁决：基线权威在 `.mm` 发射产物，不在打包元数据

- G2a 基线的规范含义（§6、§10.5）是默认 replay pipeline 生成包**发射的
  `.mm` 数学内容**。生成包 `pyproject.toml` 的 `project.dependencies`
  是安装便利工件，不参与发射逻辑，不影响 `.mm` 的任何字节。
  因此该构建失败不构成基线内容问题，属基线**获取机制**的工程缺陷。
- **不得**因此改用手工切片基线、语义包自比较或其他替代基线来源。

### 14.2 许可的两种获取途径（任选其一，均为机械途径）

1. **免安装执行**：不经 setuptools 安装，以 `sys.path`/`PYTHONPATH` 注入
   基线生成包及其依赖包的源码目录，直接执行生成包的 build 入口取得 `.mm`。
   所用命令必须完整记入报告，保证可复现。
2. **修复元数据写出 bug**：修复默认 replay pipeline codegen，使目录形式
   `--dependency` 写出合法的依赖元数据（合法 PEP 508 直接引用，或将裸路径
   移出 `project.dependencies` 的其他合法形态）。约束：只做行为修复，
   非路径 dependency 的既有输出不得改变；必须附回归测试。

两种途径共同的硬约束：**不得触及 `.mm` 发射内容的任何代码路径**；
基线两次生成必须 byte-identical（获取机制不得引入不确定性）。

### 14.3 阶段任务：Phase 4E（续）

- 以 14.2 任一途径取得 `[ax-ext, wne)` 默认 replay pipeline 基线 `.mm`；
- 用 §12.3 的同一比较器对 §13.3 已生成的 set-theory 语义包发射产物
  过 G2a/G2b（判类规则同 §12.2，profile 为 set-theory semantic profile；
  排除集内容如与 logic 域模式不符即按 §12.6 停止上报）；
- 过 G3（独立验证器，列明实际运行者）与 G4（两次 clean 生成
  byte-identical）；
- 实施报告补记：采用的基线获取途径与命令/修复、排除集明细、各门结果。

### 14.4 仍须停止上报的条件

1. 免安装执行仍无法取得基线 `.mm`，或基线两次生成不 byte-identical；
2. 获取基线需要改动任何发射内容代码路径；
3. §12.6 全部条件继续适用。

---

## 15. Phase 4E（续）实施报告（2026-07-19）

### 15.1 基线获取（途径 1：免安装执行）

复用磁盘上的默认 pipeline logic 包 `build_out/transpiled-logic` 与 §13.3 已生成的
`build_out/phase4e-baseline`。未安装生成包、未修改生成源码或任何 `.mm` 发射路径；以
`PYTHONPATH` 注入两包源码和 proof-scaffold 源码，并用 `DriverRunner` 对生成包的两个
`build.py` 入口按依赖顺序直接构建。完整命令如下（`N=1`、`N=2` 各执行一次）：

```bash
rm -rf build_out/phase4e-baseline-run1 build_out/phase4e-baseline-run2
PYTHONPATH="/Users/mingli/MetaMath/build_out/phase4e-baseline/src:/Users/mingli/MetaMath/build_out/transpiled-logic/src:/Users/mingli/MetaMath/proof-scaffold/src" \
  /Users/mingli/MetaMath/proof-scaffold/.venv/bin/python - "$N" <<'PY'
from pathlib import Path
import sys
from skfd.api_v2 import UnitMeta
from skfd.driver.runner import DriverRunner

n = sys.argv[1]
workspace = Path("/Users/mingli/MetaMath")
dep = str(workspace / "build_out/transpiled-logic")
runner = DriverRunner(
    workspace / "build_out/phase4e-baseline/src",
    workspace / f"build_out/phase4e-baseline-run{n}",
)
runner.build_paths = {
    dep: workspace / "build_out/transpiled-logic/src/setmm_logic_transpiled/build.py",
    "set-canary-baseline": workspace / "build_out/phase4e-baseline/src/set_canary_baseline/build.py",
}
runner.metas = {
    dep: UnitMeta(dist_name=dep, module_name="setmm_logic_transpiled", build_path=runner.build_paths[dep], kind="library"),
    "set-canary-baseline": UnitMeta(dist_name="set-canary-baseline", module_name="set_canary_baseline", build_path=runner.build_paths["set-canary-baseline"], kind="library"),
}
runner.deps_graph = {dep: [], "set-canary-baseline": [dep]}
runner.build_order = [dep, "set-canary-baseline"]
for package in runner.build_order:
    runner.build_package(package)
runner.verify_package("set-canary-baseline")
PY
sha256sum build_out/phase4e-baseline-run{1,2}/set-canary-baseline_full.mm
cmp build_out/phase4e-baseline-run1/set-canary-baseline_full.mm \
    build_out/phase4e-baseline-run2/set-canary-baseline_full.mm
```

两次基线均为 2,427,254 bytes、2,959 条断言（其中 2,895 个 `$p`），SHA-256 均为
`891b47486337c42a765cec296632d1a7336588a4cbf1b9675e881fe0467b3a5c`；`cmp` 通过，
故基线获取 byte-identical。

### 15.2 G2a/G2b：按冻结契约停止上报

§13.3 语义包经既定 logic semantic 上游发射为 2,439,382 bytes、2,957 条断言
（2,893 个 `$p`），SHA-256 为
`62d4af38f4197d838a804efff02ff2b163d87ff7397aefa8fa1f9a587e8cdee4`；构建/发射约
11.34 s。实际运行：

```bash
cd /Users/mingli/MetaMath/transpiler
uv run mm-frame-equivalence \
  /Users/mingli/MetaMath/build_out/phase4e-baseline-run1/set-canary-baseline_full.mm \
  /Users/mingli/MetaMath/build_out/phase4e-semantic-run/metamath-set-theory-sem_full.mm \
  /Users/mingli/MetaMath/build_out/phase4e-set-profile.json
```

比较器在机械计算排除集之前 fail-closed：`G2a failed: $c/$v token sets differ`。
明细为 baseline-only 常量
`(0, )0, -.0, ->0, /0, /\\0, <->0, =0, A.0, E*0, E.0, F/0, T.0, [0, ]0,
class0, e.0, setvar0, wff0, |-0`，baseline-only 变量
`A0, B0, ch0, ph0, ps0, t0, u0, v0, w0, x0, y0, z0`；semantic-only 常量和变量
均为空。这些是默认 pipeline 两包链接时产生的 `0` 后缀声明，和 logic 域的
`weq`/`wel` 派生语法定理排除模式不同。由于 §6 明定 `$c`/`$v` 条款不变，且 §14.4
继续适用 §12.6，**G2a 未通过并在此停止，不修改比较器、发射层或基线掩盖差异**。

因此比较器没有合法产出排除集；不得把预期的 `weq: wff`、`wel: wff` 冒充本次机械
结果。G2b 仅记录原始字节对照：两侧非字节同一，baseline 2,427,254 bytes
（SHA-256 `891b4748…3a5c`），semantic 2,439,382 bytes
（SHA-256 `62d4af38…dee4`）。因 G2a 提前失败，没有生成比较器认可的差异分类报告。

### 15.3 G3/G4/G6

- G3：因 15.2 命中冻结契约停止条件，未继续运行独立验证器；通过数不宣称。
- G4：在停止前已用同一绝对参数两次 clean 生成 `phase4e-set-a` / `phase4e-set-b`；
  `diff -rq --exclude=__pycache__ --exclude='*.mm'` 无输出，包含 `_emission.py`、
  `build.py`、manifest 在内 byte-identical。第二次全量生成 4.92 s；结果均为
  221 个断言句柄、216 个证明、1 个模块。
- G6：proof-scaffold `ruff check .` 通过，mypy strict 94 个源码文件通过，
  `uv run python3 -m pytest` 为 263 passed（89.54% coverage，2 个既有 warning）；
  transpiler `ruff check .` 通过，mypy strict 19 个源码文件通过，pytest 为
  55 passed。直接用未激活的系统 `python3 -m pytest` 会错误导入全局旧安装；按仓库
  uv 纪律重跑上述 venv 命令后全绿。

本续阶段只修改本实施报告；未新增代码文件，`.mm` 与其他构建产物均未提交。
唯一停止上报项是上述 `$c`/`$v` token 集差异；其处理方式不在 §14 冻结裁决内。

**已裁决（2026-07-19）**：见第 16 节。`0` 后缀是基线获取运行的依赖导出接线缺陷，
不是默认 pipeline 的发射政策；修复接线重取基线，不得在比较器做 token 归一化。

---

## 16. Phase 4E 基线符号分叉裁决（2026-07-19，全部已闭合）

本节针对 §15.2 上报的 `$c`/`$v` token 集差异给出规范性裁决，与第 1、10、12、
14 节同级：**执行者遇到本节未覆盖的决策点时，必须停止并上报，不得自行发明。**

### 16.1 事实认定：`0` 后缀不是默认 pipeline 的发射政策

基线生成包自身的生成代码已内建跨包符号复用契约：`runtime.py` 的 `token()`
在本地分配之前**必须**先在 `ctx.deps[<DEPENDENCY_PACKAGES 条目>]` 中解析
上游导出符号（token 与 label 同理）。因此，合格的默认 pipeline 两包链接产物
**不含**上游符号的重复声明；§15.2 观察到的 `wff0`/`|-0` 等 `0` 后缀分叉，
说明该次免安装执行（§15.1 的 `DriverRunner` 布线）没有让 `token()` 的
deps 查找命中上游 token 导出，符号被重复声明并在链接期被去重改名。
这是**基线获取机制的接线缺陷**（§14.1 的既定分类），不是需要在比较层
容忍的 legacy 偶然性。

### 16.2 裁决

1. 带重复符号声明（`0` 后缀分叉）的产物**不是合格基线**；G2a 不得与其比较。
2. **不得**在比较器中通过 token 归一化（后缀剥离、双射改名等启发式）适配
   分叉基线；`$c`/`$v` 集合相等条款维持原状。
3. **必须**诊断并修复基线获取运行的依赖导出接线，使 `token()` 与
   `proof_label()` 的 deps 查找按生成代码契约命中上游导出。许可范围：
   - 修正 §15.1 免安装执行脚本的 `DriverRunner` 布线（deps 键与
     `DEPENDENCY_PACKAGES` 条目对齐、导出表传递等）；
   - 若缺陷在 `skfd.driver` / `skfd.api_v2` 的跨包导出表机制，许可做
     行为修复（修正明显缺陷、接受更多合法输入；既有测试零回归）。
     `skfd.driver` 与 `api_v2` build context 不在第 4 节保护清单内。
   - BuilderV2 / linker 语义仍受第 4 节保护；若诊断显示必须改其语义，
     停止上报。
4. 合格性判据（机械）：修复后基线 `.mm` 的 `$c`/`$v` 中同一源 token 只出现
   一次；G2a 的 `$c`/`$v` 集合相等条款自身即为最终判据。

### 16.3 阶段任务：Phase 4E（再续）

- 按 16.2 第 3 条修复接线，重新执行 §14.3 全部步骤（基线两次生成
  byte-identical、G2a/G2b、G3、G4）；
- 诊断结论（缺陷位于布线脚本还是 skfd 导出表机制、修复内容）写入实施报告；
- 预期排除集为 set-theory 基线中的派生语法定理（若与 §12 机械规则冲突，
  按 §12.6 停止上报）。

### 16.4 仍须停止上报的条件

1. 正确接线后 `$c`/`$v` 仍存在排除集之外的差异（此时为真实语义或发射差异，
   不得在任何一层打补丁掩盖）；
2. 修复需要触及 BuilderV2 / linker / 三套验证器语义；
3. §12.6 与 §14.4 全部条件继续适用。

---

## 17. Phase 4E（再续）实施报告（2026-07-19）

### 17.1 依赖导出诊断与合格基线重取

诊断结论为 **(a) §15.1 获取运行的输入接线缺陷**，不是 `skfd.driver` /
`api_v2` 跨包导出机制缺陷。`DriverRunner.build_package()` 以
`deps_graph[name]` 的原始 dependency dist key 建立 `dep_exports`，上游
`mm.finish().exports` 随即按 `local_name` 写入 `exports_by_pkg`，再由
`DepsView` 以 dist key、下划线别名和 module name 暴露；§15.1 使用的绝对路径 key
与下游 `DEPENDENCY_PACKAGES` 的绝对路径串逐字相等，构建顺序也正确。实际根因是该次
手工运行复用了旧的 `build_out/transpiled-logic` 生成工件：其旧 `runtime.py` 只导出
断言 label，未包含当前默认 pipeline 已有的 `token()` 后 `mm.export(token_id)`；因此
正确的 deps key 下也没有 token 可命中。用当前默认 pipeline 以原参数重新生成该上游
包后，其 runtime 对每个 token 和导出断言 label 均导出，原 §15.1 DriverRunner 布线
即可命中。未修改 `skfd.driver`、`api_v2`、BuilderV2 或 linker，故无需新增机制测试。

上游工件刷新命令（构建产物不提交）：

```bash
cd /Users/mingli/MetaMath/transpiler
uv run mm-transpiler ../set.mm/set.mm ../build_out/transpiled-logic \
  --package-name setmm-logic-transpiled \
  --graph ../partition/domains/logic/artifacts/proof-graph.json \
  --modules 14 --force
```

随后原样重跑 §15.1 的完整 `PYTHONPATH`/`DriverRunner` here-doc 命令（`N=1`、
`N=2`），并执行：

```bash
sha256sum build_out/phase4e-baseline-run{1,2}/set-canary-baseline_full.mm
cmp build_out/phase4e-baseline-run1/set-canary-baseline_full.mm \
    build_out/phase4e-baseline-run2/set-canary-baseline_full.mm
wc -c build_out/phase4e-baseline-run1/set-canary-baseline_full.mm
rg -c '\$[ap] ' build_out/phase4e-baseline-run1/set-canary-baseline_full.mm
```

run1/run2 均为 2,420,854 bytes、2,959 条 `$a`/`$p` 断言，SHA-256 均为
`c780897f3b32bdcec76ec66352d1b3418ed7e654a22ba38b5a29371b8e075bdd`；`cmp`
通过。`$c`/`$v` 不再含 §15.2 的 `0` 后缀重复声明，比较器也通过 token 集合检查。

### 17.2 G2a/G2b：命中冻结停止条件

实际运行：

```bash
cd /Users/mingli/MetaMath/transpiler
uv run mm-frame-equivalence \
  /Users/mingli/MetaMath/build_out/phase4e-baseline-run1/set-canary-baseline_full.mm \
  /Users/mingli/MetaMath/build_out/phase4e-semantic-run/metamath-set-theory-sem_full.mm \
  /Users/mingli/MetaMath/build_out/phase4e-set-profile.json
```

比较器机械得到排除集恰为：

- `weq`，typecode `wff`；依据：基线 `$p` 结果 `wff ∈ term_typecodes =
  {class, setvar, wff}` 且 `wff ∉ judgment typecodes = {|-}`；
- `wel`，typecode `wff`；判类依据同上。

`$c`/`$v` 相等，剔除该集合后的 label 集合及序列检查亦已通过；但比较器随后
fail-closed：`G2a failed: assertion frame differs for 'df-cleq'`。独立展开显示
statement、mandatory `$e` 与 distinct 相等，差异是 mandatory `$f` 顺序：基线为
`x,y,z,v,u,t,A,B`（对应 typecode `setvar` 六项后 `class` 两项），semantic 为
`A,B,t,u,v,x,y,z`。这属于 §12.6(2)/§16.4 的排除集外帧差异，故 **G2a 未通过并
立即停止上报**；未对发射层、比较器或基线打补丁。

G2b 仅能记录原始字节对照，不能宣称比较器认可的分类报告：baseline 为
2,420,854 bytes、SHA-256 `c780897f…75bdd`；semantic 为 2,439,382 bytes、
2,957 条断言、SHA-256 `62d4af38…dee4`；两者非字节同一。

### 17.3 停止后的门与偏离

- G3：因 §12.6(2) 停止，未运行 `skfd.verifier.mmverify`，不宣称通过数。
- G4：本次没有修改 transpiler 生成路径；§15.3 两次 clean 生成（含 manifest）
  byte-identical 的结论仍有效。新基线自身 run1/run2 亦已 byte-identical。
- G5：本次停止前未以计时器采集新的可报告耗时；不虚构数据。既有语义生成耗时仍见
  §15.2，既有 clean 生成耗时见 §15.3。
- G6：依冻结契约在首个排除集外帧差异处停止，未重跑两仓全套；不以 §15.3 的既有
  全绿结果冒充本次运行。

本续阶段仅修改本实施报告；没有代码修复或新增回归测试，刷新出的 `.mm` 和生成包均为
不提交的构建工件。唯一停止上报项为 `df-cleq` mandatory `$f` 顺序差异；该决策点已由
§12.6/§16.4 明确要求停止。

**已裁决（2026-07-19）**：见第 18 节。差异源于 primitive rule 的发射表面沿用
calculus canonical 变量顺序；发射绑定工件按 §10.3 增记源序 floating 数据，
calculus 内部顺序契约不变。

---

## 18. Primitive rule 发射 floating 顺序裁决（2026-07-19，全部已闭合）

本节针对 §17 上报的 `df-cleq` mandatory `$f` 顺序差异给出规范性裁决，与第 1、
10、12、14、16 节同级：**执行者遇到本节未覆盖的决策点时，必须停止并上报，
不得自行发明。**

### 18.1 根因认定

- set.mm 中 `df-cleq` 的 mandatory `$f` 顺序为源 floating 声明顺序
  `x, y, z, v, u, t, A, B`；语义发射产物为 calculus canonical 顺序
  `A, B, t, u, v, x, y, z`。statement、mandatory `$e`、distinct 全部相等，
  故这不是 §10.6(3) 意义上的**表达式级**语义导入错误，而是与 §11.3 已闭合的
  `df-sb` 同类的**顺序政策缺口**：§11.3 的声明顺序修复覆盖了
  axiom/definition 签名边界，并明确保留 "primitive rule 遵守 calculus
  canonical 顺序" 的既有契约；`df-cleq` 在语义包中恰为 primitive rule
  （`_theory.py` 的 `primitive_rule('df-cleq')`），其发射表面因此继承了
  canonical 顺序。logic 域未暴露该缺口，仅因其全部 primitive rule 的
  canonical 顺序与源顺序巧合一致。
- 模式变量的位置顺序 = set.mm floating 顺序是 ABI（§1.6），发射表面必须遵守。

### 18.2 裁决：源序 floating 属声明级发射数据，由发射绑定工件携带

- **不改** calculus 内部 primitive rule 的 canonical 变量顺序契约
  （§11.3 的保留继续有效；规则同一性与摘要不受影响）。
- **不得**在发射器内做启发式重排（按 kind、按字母序或任何非源序推断）。
- **必须**扩展 `MetamathEmissionBinding`（skfd 侧，§10.3 第 1 条清单增补）：
  为每条以 primitive rule 为后端的发射断言携带 mandatory floating
  （sort, 变量）的**源顺序序列**，由 transpiler 在生成时从源数据库机械派生，
  固化进 `_emission.py`。这与 formation `$a` 条目既有的 floating 序列同构，
  属 §10.1 已裁决的"声明级发射数据"，不构成证明内容的第二事实源。
- `emit_semantic_metamath_theory` 发射该类断言时按源序序列排列 floating
  `$f`；假设标签政策（§10.3 第 3 条）不变，"schema 顺序"对 primitive rule
  即该源序序列。
- **fail-closed**：源序序列缺失、或其变量集合与 calculus 规则的 mandatory
  变量集合不等时，出错即拒绝，不得启发式补齐。
- 政策版本化：发射绑定工件的政策版本字段必须递增以反映该语义
  （具体字段命名对齐既有工件；manifest v2 摘要随之更新）。

### 18.3 阶段任务：Phase 0F + 3F 回归 + 4E（三续）

- **Phase 0F**（proof-scaffold）：实施 18.2 的 binding 扩展与发射器支持；
  单元测试覆盖：源序发射、变量集合不匹配拒绝、缺失序列拒绝、
  同输入两次发射确定性。工具链门同 Phase 0。
- **Phase 3F 回归**（transpiler + logic）：重新生成并发射 logic 切片，
  重跑 G2a/G4（logic 全部 primitive rule 的 canonical 顺序与源序一致，
  预期产物不变或仍全等；若 G2a 回归失败即停止上报）。
- **Phase 4E（三续）**：重新生成 set-theory 语义包并发射，用 §16.3 的合格
  基线重跑 G2a/G2b/G3/G4/G6；报告补记（§19）。

### 18.4 仍须停止上报的条件

1. 扩展后仍存在排除集外的任何帧差异（含新的 `$f` 顺序差异——那说明存在
   本节未认定的第二种顺序改写来源）；
2. 实施需要改动 calculus 规则表示、断言应用内核、BuilderV2、linker 或
   任一验证器语义；
3. §12.6、§14.4、§16.4 全部条件继续适用。

---

## 19. Phase 0F / 3F 回归 / 4E（三续）实施报告（2026-07-19）

### 19.1 Phase 0F 与政策版本

`MetamathEmissionBinding` 新增只读 `primitive_rule_floating` 映射及
`floating_order_policy`。后者为
`mm-transpiler-primitive-floating-source-order-v1`；既有假设标签政策仍为
`mm-transpiler-hypotheses-v1`，manifest 的总发射政策递增为
`mm-transpiler-emission-v2`。primitive rule 声明与其证明应用均按同一源序消费
floating；缺失条目、额外条目、变量集合或 sort 不匹配均 fail-closed。calculus
canonical 顺序及保护清单内模块均未改动。

transpiler 从源数据库 `mandatory_f` 机械生成本包及递归上游 primitive rule 数据，
写入 `_emission.py`；该数据及两项子政策进入 emission binding 摘要。新增/更新测试覆盖
源序（测试中故意令 `mp` 源序与 canonical 顺序相反）、缺失拒绝、集合不匹配拒绝、
两次发射确定性，以及生成包 manifest/发射验证。

### 19.2 Phase 3F logic 回归

以 `[wi, ax-ext)`、logic graph/partition/profile clean 生成两次，均为 2,710 个语义
断言、2,677 个证明、14 个模块，目录逐字节相同。生成耗时分别 8.03 s、8.46 s；
发射及验证运行 11.14 s。新产物与 §13.2 合格 semantic logic 产物比较：G2a 通过，
2,734 帧零差异，排除集为空；G2b 亦 byte-identical（两侧 2,281,737 bytes，
SHA-256 均为 `6dcc048a58547957867db4ece2678adad1c0b2e1001070bad0d636ef27da047a`）。
这证明 logic primitive rule 的源序/canonical 序一致且回归产物未变。G4 通过。

### 19.3 Phase 4E（三续）各门

set-theory `[ax-ext, wne)` 以新 logic semantic 包为 dependency clean 生成两次，
均为 221 个断言、216 个证明、1 个模块，耗时 4.80 s、4.96 s；完整两包发射及
`DriverRunner.verify_package` 耗时 11.35 s。两次生成目录（含 `_emission.py`、
`build.py`、manifest）逐字节相同，G4 通过。

- **G2a：通过。**复用 SHA-256 为
  `c780897f3b32bdcec76ec66352d1b3418ed7e654a22ba38b5a29371b8e075bdd`
  的 §17 合格基线。比较器机械排除后比较 2,957 帧，statement、mandatory `$f`/`$e`、
  distinct、label 序列及 `$c`/`$v` 全部相等；不存在排除集外差异。
- **排除集明细：**`weq`（typecode `wff`）与 `wel`（typecode `wff`）。两者依据均为
  基线 `$p` 结果 typecode 属于 profile 的
  `term_typecodes={class,setvar,wff}`，且不属于 judgment typecodes `{|-}`。
- **G2b：**非字节同一，分类为假设 label、proof token 与布局等非语义序列化差异。
  baseline 为 2,420,854 bytes、SHA-256 `c780897f…75bdd`；semantic 为
  2,439,382 bytes、SHA-256
  `c3b3b93a6f0d4db9f4e0c7fec955aede95f8675a5e2798cd1db8adcecf272736`。
- **G3：通过。**实际验证器为 proof-scaffold `skfd.verifier.mmverify`（由
  `DriverRunner.verify_package` 调用），2,893 个 `$p` 全部通过。
- **G5：**本轮关键耗时如上；签名解析/import 指标未因本修复重测，沿用 §13.2，
  不虚构新数据。

### 19.4 G6、偏离与结论

proof-scaffold：`ruff check .` 通过；mypy strict 94 个源码文件通过；pytest
265 passed、89.55% coverage（2 个既有 warning）。transpiler：Ruff 通过；mypy
strict 19 个源码文件通过；pytest 55 passed。全部命令均使用各仓自己的 venv。

没有触发 §18.4 或其他冻结停止条件，没有 label 特例、基线编辑或比较项弱化；生成包
及 `.mm` 均未提交。**Phase 4E 至此闭合。**

---

## 20. 稳定上游断言同一性接缝（2026-07-24）

`Theory.theorem`、`Theory.axiom`、`Theory.definition` 与 `Theory.primitive_rule`
新增只增不改的 keyword-only 参数
`assertion_id: AssertionId | str | None = None`。

- `None` 保留既有 `<theory namespace>#assertion:<label>` 同一性政策，不改变兼容行为；
  特别是默认 primitive-rule 签名继续保留由 calculus 所有的 schema 变量。
- 显式值必须重新构造为 `AssertionId`；空值、非法值、重复值及与上游冲突的标识符均
  fail closed。canonical label 校验及本地/上游 label 冲突检查保持独立，不能通过显式
  标识符绕过。
- theorem、axiom、definition 声明的 schema 变量归属 resolved assertion identity。
  primitive rule 收到显式同一性时，其完整签名 alpha-rebind 到该同一性：
  schema 变量、premises、conclusion 与 distinct-variable 端点均采用新 owner；
  calculus rule 本身不变。
- proof identity 继续由 theory namespace 与 canonical label 派生。该接缝改变的是
  catalog/provider 的 assertion join，不改变惰性证明体注册与 proof identity 政策。

因此 generated provider 可以把 `urn:uuid:...` 等权威 catalog identity 直接用于
semantic handle，同时保持省略新参数的手写源码及既有生成源码兼容。
