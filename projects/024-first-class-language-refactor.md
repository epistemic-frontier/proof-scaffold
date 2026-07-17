# Project 024：将语言提升为第一类理论接口

## 状态

实施中，2026-07-16。

规范性依据：
[Reference 011：将语言作为第一类元素](../references/011-language-as-first-class.md)。

相关既有设计：

- [Reference 005：Authoring-First Architecture](../references/005-authoring.md)
- [Reference 010：Foundation Scope](../references/010-foundation-scope.md)
- [Project 008：Prelude Framework Refactor](./008-prelude_refactor.md)
- [Project 020：Foundation Scope Refactor](./020-foundation-scope-refactor.md)
- [Project 021：Authoring IR](./021-authoring-ir-for-human-and-llm-authors.md)
- [Project 022：Authoring API v0.1](./022-authoring-api-v0.1.md)

本文是针对当前 `proof-scaffold`、`metamath-prelude` 和 `metamath-logic`
实现的工程诊断与渐进改进计划，不冻结最终 Python API。

## 0.1 修订后的实施契约

初稿正确识别了语言缺失，但将 semantic language、notation、Metamath lowering 和 syntax
assertion binding 压进了一个过宽的 `LanguageSpec`。本节取代第 4、5、9 节中与其冲突的旧
分组和实施次序。

目标骨架是：

```text
LanguageSpec
  sorts + variable kinds + constructors + binders
        |
        +---- NotationSpec
        |       parse + render + aliases + precedence
        |
        +---- MetamathLanguageBinding
                typecodes + token templates + syntax assertions

CalculusSpec
  judgment kinds + primitive inference rules

LogicSpec
  language + calculus + logical axioms

TheorySpec
  base logic + language extension + definitions + non-logical axioms + theorems
```

其中 `Term` 只包含稳定 variable/constructor identity、argument tree 和 sort。Unicode spelling、
source span、`SymbolId`、Python object identity 和 provenance 均不参与其相等性。`|-` 是
`Provable(Wff)` judgment 的 Metamath realization；`wi/wn/wa/w3a` 属于 language binding；
`ax-mp/ax-gen` 属于 calculus；`ax-1/ax-2/ax-3` 属于 logical axioms。

### Source、Interface 与 Runtime

三个阶段不得折叠：

```text
LanguageSpec
  库作者编辑的有限声明源

LanguageInterface
  冲突检查、继承展开、不可变、可摘要的消费者投影

BoundLanguage / LanguageEnvironment
  绑定 notation、backend、SymbolId、resolver 和 build context 的运行时对象
```

`System` 是 runtime binding，不是理论身份。第一阶段允许新声明与 legacy globals 并存，但新
声明不得由 globals 投影生成；下一阶段必须由声明生成 legacy compatibility adapter，最终移除
import side effects。

### 分层摘要

```text
semantic_digest = sorts + variable kinds + constructors + binder behavior
notation_digest = patterns + aliases + canonical rendering
backend_digest  = typecodes + owned tokens + templates + formation assertions
calculus_digest = judgments + primitive rule signatures
```

所有摘要使用显式版本化 canonical JSON；不得使用 `repr`、Python hash、mapping iteration、
callbacks 或 `SymbolId`。

### 修订后的阶段顺序

**Phase 0.5 — Term identity hardening。** 新建 nominal `SortId`、`ConstructorId`、
`VariableRef` 和结构相等的 immutable `Term`。旧 `Expr` 只保留 compatibility role，不作为公共
ABI。

**Phase 1 — 最小语言 canary。** 实现独立的 `LanguageSpec`、`NotationSpec`、
`MetamathLanguageBinding` 与分层摘要；Prelude 声明 `Not/Imp`；prop 扩展 `And2/And3`。二元与
三元 conjunction 具有不同 `ConstructorId` 和 formation assertion，但可以共享 backend token。
`And3` 首轮使用无歧义 call notation，不复制旧 parser 的 arity collapse。

**Phase 2 — 声明成为事实源。** 从新声明派生 legacy registries/builders/parser tables；不再长期
维持由旧 globals 投影出的第二份 `LANGUAGE`。

**Phase 3 — Judgment / Calculus。** 先实现 `Provable(Wff)`，再设计 schema-aware MP 与
generalization；在 substitution 和 constraints 未稳定前不得用任意 callback 提前冻结 primitive
rule API。

**Phase 4 — Binder / DV canary。** 以 `All`、`ax-gen` 和一个 mandatory-DV assertion 验证
真实 sorts、free-variable、capture、alpha-renaming、DV substitution 与 relocation。

**Phase 5 — Proof API 与 combinators。** 到此再冻结 `AssertionSignature`、`ProofDraft`、
`ApplyAssertion` 和 `ElaboratedProof`。Project 023 的 family/combinator 必须展开为普通 concrete
assertion applications。

### 当前第一切片的完成边界

本轮实现：

- ProofScaffold 中并行的 Term v2 和稳定 nominal IDs；
- conflict-checked immutable `LanguageInterface`；
- finite prefix/infix/call `NotationSpec`；
- symbolic、无 `SymbolId` 的 `MetamathLanguageBinding`；
- judgment-only 的最小 `CalculusSpec`，不提前实现 MP/Gen；
- Prelude `Not/Imp` 与 prop `And2/And3` canary；
- semantic/notation/backend/calculus 独立摘要；
- legacy build、proof constructors、BuilderV2 和 verifier 行为不变。

本轮明确不迁移 FOL、binder、substitution、DV、primitive rules 或现有 2,675 个 proof
constructors。为避免冻结一个只有打印形状和 binder 参数检查、却没有自由变量与捕获规避语义的
残缺契约，Phase 1 的 `ConstructorDecl` 暂不公开 binding 字段；该字段必须在 Phase 4 与完整的
free-variable、substitution、capture rejection 和 alpha-renaming 行为一起进入接口。

Phase 2A 已在 Prelude `Not/Imp` 上完成第一轮事实源反转：legacy token interning、token-level
constructors、shape matchers、authoring symbol specs、formation rule signatures 和 `wn/wi` emission
均由 resolved language/notation/backend declarations 投影；兼容层仍保留旧 Python API。该迁移
前后 `metamath-prelude_full.mm` 的 SHA-256 完全一致。

Phase 2B 已将同一机制推进到 prop 的 `And2/And3`：legacy builder registry 以完整
`Constructor(name, arity)` 为精确键，同名二元、三元构造子可以共存，字符串查询仅保留为兼容
fallback；authoring parser 也通过公开的 name/arity 查询，不再读写 registry 私有映射。Logic
侧已删除 conjunction/disjunction 的 `_by_name` pop/restore 和按参数个数 dispatch，并由 prop
language/notation/backend declarations 派生 `And2/And3` 的 authoring specs、token template、
formation label、legacy lowering 与 `wa/w3a` emission。迁移前后
`metamath-logic_full.mm` 的 SHA-256 均为
`0e857f13fe8c82d406f3b730f8dcc2aade8a94a031f38152a295f0be00ba75b8`，三套 verifier 均通过。
这仍是 compatibility migration：全局 registry 与 legacy `Expr` 尚未移除，完整 Phase 2 尚未结束。

Phase 2C 进一步删除了 prop 对 Prelude `Imp/Not` 的重复 authoring 声明：原导入路径现为 Prelude
constructor 的兼容 re-export。Prelude token lowering 改用只读结构协议接收下游 builtins，因此
prop 与 FOL 无需继承具体 runtime 类即可复用同一 constructor builder；Logic artifact 仍保持上述
SHA-256 不变。

Phase 3A 已将 `CalculusSpec` 从 judgment vocabulary 扩展为包含有限、不可变、可摘要的
`PrimitiveRuleDecl`。每条 primitive rule 显式声明 schema variables、judgment premises 与
conclusion；resolver 校验 variable kind、constructor tree、sort、judgment kind，并规范化无位置
语义的 schema-variable 顺序。Prop 的 modus ponens 现在正式表示为
`Provable(φ), Provable(Imp(φ, ψ)) -> Provable(ψ)`，公开 `RULES["ax-mp"]` 只是 set.mm label 到该
语义声明的兼容视图，不再以字符串 `"mp"` 冒充规则元数据。`ax-gen` 刻意留到 Phase 4：在
setvar sort、`All` binder、substitution 和 DV 契约进入 semantic language 前，不创建残缺的
generalization 声明。该阶段不改变 proof execution 或 emission，Logic artifact SHA-256 继续不变。

Phase 4A 已加入可摘要的 `BinderDecl`，并从 binder contract 统一推导 free-variable、
alpha-renaming 与 capture-avoiding substitution；nested shadowing 只屏蔽内层 binder 的 scoped
arguments，未受内层 binder 约束的参数仍服从外层作用域。Binder notation 支持 precedence-aware
parse/render，语言扩展也禁止为继承构造子补加或改变 binder 语义。FOL semantic language 现在
显式扩展 prop，声明独立 `SETVAR` sort、`All : SETVAR × WFF -> WFF` 及其 binder contract；
`wal` 只存在于 Metamath formation binding，`ax-gen` 则表示为
`Provable(φ) -> Provable(All(x, φ))` 的 primitive inference rule。

Phase 4B 用 `ax-5` 完成 mandatory-DV canary。`DistinctPair` 的两个端点直接引用 assertion 的
typed `VariableRef`，resolver 验证端点属于同一 schema-variable 集合、去向无关地规范化 pair，
并把约束纳入 assertion digest。`ax-5` 因此同时表达 WFF schema variable `φ`、SETVAR schema
variable `x` 以及 mandatory pair `(φ, x)`；`ax-gen` 没有被错误附加该约束。当前 legacy
`ACTIVE_DV_PAIRS` 仍是 emission 权威输入，semantic `ax-5` 是迁移 canary，不另行改写 corpus 或
公开 `prove_*` API。下一步应把该 typed assertion contract 接入 Phase 5 的统一
`AssertionSignature/apply_assertion`，再逐步消除 label-keyed side table，而不是长期维护两份事实源。

Phase 5A 已建立最小 semantic assertion-application kernel。`AssertionSignature` 统一承载
axiom 与 primitive rule 的稳定 assertion identity、kind、有序 schema variables、有序 judgment
premises、conclusion 和 mandatory-DV；primitive `RuleId` 到 backend assertion identity 的绑定必须
显式给出，不做隐式类型转换。不可变 `ProofDraft` 以 occurrence-based `StepId` 保存 hypotheses 与
fully reified steps，构造时检查连续 ID、无重复、无 forward/foreign premise，并规范化完整 active-DV
环境。`apply_assertion` 只接受一个确定 signature 与有序 prior steps，执行局部结构 unification，
把 partial substitution/target 作为约束，要求所有 mandatory variables 唯一确定，再通过独立的
one-pass schema instantiation 计算结果；它不调用 capture-avoiding object substitution，也不信任
调用者提供的结果。DV 检查与 Metamath 一致地使用两端 substitution 中所有语法出现变量的笛卡尔
积，包括 binder 下的出现，并要求 consumer active-DV relation 覆盖每一对。失败抛出结构化
`AssertionApplicationError`，原 draft 不变。

这一切片已用真实 `ax-mp` 与 `ax-5` metadata 验证 ordered-premise inference、binder-variable
instantiation、missing/overlapping DV rejection 和 reified substitution/evidence。它尚不声称完成
完整 Phase 5：theory/profile lookup、goals/holes、finalization、replay context、semantic digest、
legacy lowering 以及 family/combinator expansion 仍明确留在后续切片。

Phase 5A.5 在 kernel 与 finalization 之间补入 scoped Source IR，而不重写 `$d` 系统。
`SourceBlock` 的 statement 可以是 `DistinctStatement`、`AssertionSource` 或 nested block；一个
distinct group 精确展开为组内无向 pair，不做传递闭包。纯 elaborator 从 parent relation 复制
active-DV，按 source order 累加 `$d`，在 assertion 声明点快照完整 relation，并把 relation 限制到
assertion schema variables 后形成公开 mandatory-DV；nested block 继承 parent，但退出后不向 parent
泄漏。`SourceBuilder.block()` 的 `with` façade 只构造 immutable Source IR，不调用 BuilderV2、linker
或 emission，也不修改 global registry。等价 pair grouping 具有不同 `source_digest`、相同
`semantic_digest`；两种摘要都包含完整 assertion 内容而不是只依赖 nominal ID。FOL `ax-5` canary
现在先以无 DV 的 source assertion 进入 block，由 `d(φ, x)` elaboration 重新得到与
`AX5_SIGNATURE` 完全相同的 mandatory contract；legacy `_dv_contracts.py` 仍是当前 emission 路径的
权威输入。

Phase 5B 已把 scoped assertion snapshot 接到固定 theorem draft 与 finalization。由 snapshot 启动的
draft 固定 theorem signature、有序 hypotheses 和完整 active-DV；构造时要求公开 mandatory-DV
恰好等于 active relation 对 schema variables 的限制。Finalization 只接受 theorem，禁止 self
reference，要求 root 精确等于声明 conclusion，并拒绝任何不能从 root 反向到达的 dead step。
`AssertionReplayContext` 原样保存完整规范化 active-DV，而不是只保留公开 mandatory pairs。
`ElaboratedProof` 的 dependency closure 作为集合按稳定 assertion ID 排序；semantic digest 是只读
派生值，包含 calculus digest、完整 signature、位置化 proof DAG、substitution、constraint evidence
和 replay relation，但排除 display label、nominal `ProofId` 与具体 `StepId` spelling。因此同一证明
换用不同 source display label 或 proof-local occurrence namespace 不改变数学摘要，改变 calculus
contract 则必然改变摘要。Theory/profile lookup、assumption closure、legacy lowering 与公开 snapshot
codec 仍留待后续切片。

---

## 1. 问题陈述

当前公开逻辑 API 已经围绕以下三类元数据形成相对清楚的结构：

```text
AXIOMS
RULES
THEOREMS
```

但它没有把这些对象共同依赖的 `LANGUAGE` 作为公开的一等元素。语言事实仍散落在：

- `metamath-prelude/src/prelude/formula.py` 的 builtin token 身份、token constructors 和 shape
  parsing；
- `metamath-prelude/src/prelude/structures.py` 的作者层变量、`Imp` 与 `Not`；
- `metamath-prelude/src/prelude/hilbert_rules.py` 的 syntax assertion wrappers；
- `metamath-prelude/src/prelude/build.py` 的实际 constants、variables、`$f`、`wn` 和 `wi`
  发射；
- `metamath-logic/src/logic/prop/_builtins.py` 与 `fol/_builtins.py` 的词汇、lowering 和 shape
  matching；
- `prop/_structures.py` 与 `fol/_structures.py` 的构造子、aliases、precedence 和全局 DSL
  registry 修改；
- `_system.py` 的 builtins、authoring environment、rules 和 resolver 装配；
- `_internal.py` 的 `Expr -> Wff` 编译和规则应用桥接。

结果不是单纯的命名不整齐，而是理论接口缺少一个维度：系统能够列举公理、推理规则和定理，
却不能以同样方式回答“这些对象是用什么语言写成的”。

---

## 2. 当前混乱的具体表现

### 2.1 Prelude 与 propositional language 重复声明

Prelude 已经声明 `phi`、`psi`、`Imp` 和 `Not`，但
`logic.prop._structures` 又声明相同变量和构造子；`logic.prop._builtins` 也重新提供 `imp` 与
`wn` 的 token lowering。

这使实际关系看起来像复制：

```text
prelude language     prop language
      Imp       ≈       Imp
      Not       ≈       Not
```

而正确关系应当是显式扩展：

```text
PROP_LANGUAGE = PRELUDE_LANGUAGE.extend(And, Or, Iff, ...)
```

在没有稳定构造子身份和语言组合契约时，两份声明可能在 arity、alias、precedence、token
namespace 或 lowering 上独立漂移。

### 2.2 `_syntactic.py` 混合形成规则和推理规则

`logic.prop._syntactic` 把 `Wi`、`Wn`、`Wa` 与 `Mp` 放在同一个 registry：

- `Wi/Wn/Wa` 检查输入 sorts 并形成新公式，属于语言形成能力；
- `Mp` 消费两个已证明 hypothesis 并产生 conclusion，属于逻辑的 primitive inference rule。

Metamath 后端可以把二者都表示为 assertion application，但作者 API 必须区分“形成一个公式”与
“得到一个证明”。当前模块名和 registry 使两种职责不可见。

### 2.3 `_builtins.py` 同时是词典、编译器和 parser

当前 `_builtins.py` 至少承担：

1. intern canonical token identities；
2. 直接拼装 `Wff` token sequences；
3. 解析 implication、negation 等 token shape；
4. 为 `_structures.py` 的作者构造子提供 lowering implementation。

这些都是语言子系统的一部分，但不是同一种数据。因为没有显式 `LanguageSpec`，构造子的
signature、显示记法、token layout 和 shape matching 只能靠约定保持一致。

### 2.4 构造子注册依赖全局可变状态

`logic.prop._structures` 使用 `DEFAULT_REQUIRE` 和 `DEFAULT_BUILDERS`，并为二元/三元 conjunction
和 disjunction 临时修改 registry 的私有映射。这种实现能维持当前 corpus，但不能清楚回答：

- 某个 `System` 精确采用哪一份语言；
- 两个 language profile 是否可以在同一进程隔离存在；
- 导入顺序是否改变 constructor registry；
- 同 token 的多 arity 是一个构造族还是多个稳定构造子。

语言成为显式对象后，registry 应当由语言声明构建，并由 `System` 显式持有；模块导入不应成为
语义操作。

### 2.5 一阶语言的 sort 与 binder 契约尚不完整

`logic.fol._structures` 当前主要复用 `WFF` sort 表示公式变量、量词变量、class 相关构造和
关系参数。例如 `All` 的签名暂时表现为 `(WFF, WFF) -> WFF`。这便于兼容已有 lowering，但会
掩盖数学上的区别：

- 量词绑定的是哪一类变量；
- `Eq` 与 `Elem` 的参数属于 setvar、class 还是 term；
- substitution 的源、目标与公式参数分别是什么 sort；
- free-variable 与 capture-avoidance 如何由构造声明推出。

只声明 `All` 的打印形状不足以构成一阶语言定义。binder、作用域、自由变量与 substitution
必须进入语言契约，并与 DV obligations 对齐。

### 2.6 `fol` 与集合论语言边界被历史布局掩盖

当前 `logic.fol` 提供 `Elem/∈`、`Cv` 等与 `set.mm` 前缀布局密切相关的构造。这可以是兼容
构建的现实选择，但 `∈` 并非一般一阶逻辑的固有符号。由于没有 `LANGUAGE` 及其 extension
关系，使用者无法分辨：

- 哪些是纯一阶逻辑词汇；
- 哪些是带 equality 的 profile；
- 哪些已经是 set-theoretic vocabulary；
- 哪些仅为 `set.mm` emission order 所需。

### 2.7 公共 `RULES` 暴露了语言缺失带来的分类问题

当前 `logic.prop.RULES` 和 `logic.fol.RULES` 都是 `Mapping[str, str]`，且都只列出
`{"ax-mp": "mp"}`。这一形状不能表达 premises、conclusion、sorts、binder/DV side
conditions 或规则所属 calculus；同时 `fol` 的 generalization primitive `ax-gen` 没有出现在
公共 registry 中。

本项目不应把语言重构扩大成一次完整 `Rule` API 重写，但在建立 binder-aware language 后必须
复核 `RULES`：形成规则应移入 `LANGUAGE` 契约，`mp` 和 `gen` 等 primitive inference rules
应获得足以表达其判断签名与 side conditions 的元数据。

### 2.8 构建产物知道语言，公共接口却不知道

`prelude.build` 和 `logic._build` 最终能够发射正确 `.mm`，说明构建路径实际上掌握了所需的
constants、variables、syntax assertions 和 token layouts。但是这些事实只在过程式 build
代码、私有 builtins 和 registry 中汇合，没有形成可供 parser、formatter、proof author、agent
和下游包共同读取的 `LanguageInterface`。

这正是“语言缺失”的实质：并非系统没有语法，而是语法没有成为唯一、显式、可复用的理论事实。

---

## 3. Prelude 的基础地位

### 3.1 两种基础必须分开

当前栈中有两种不同意义的基础：

| 层 | 职责 | 典型对象 |
| --- | --- | --- |
| ProofScaffold | 构造任意语言的通用元工具 | `Sort`、`Var`、`Constructor`、`Expr`、registry、parser/lowering algorithms |
| metamath-prelude | 标准包共享的最小具体语言和 Foundation Frame | `wff`、`|-`、`(`、`)`、`-.`、`->`、schema variables、`wn`、`wi` |

因此，Prelude 在语言构造中具有基础地位，但不应重新吸收已经由 `skfd.authoring` 提供的通用
框架。Project 008 将通用 authoring machinery 从 Prelude 移入 ProofScaffold 的方向仍然正确；
本项目是在此基础上补齐“具体语言也必须成为一等对象”。

### 3.2 Prelude 应公开什么

Prelude 应当公开一个最小、不可变、可摘要的 `LANGUAGE` 或 `LanguageInterface`，使下游能够
显式扩展：

```text
PRELUDE_LANGUAGE
  sorts: wff, provable judgment marker as appropriate
  variables: standard schema-variable families
  constructors: Not, Imp
  token layouts: -., ( _ -> _ )
  syntax assertions: wn, wi
```

这里的 `wn`、`wi` 是语言形成的后端证明关联，不应进入逻辑 `AXIOMS`。Prelude 仍然是标准
build closure 中唯一 foundation unit，其 ambient `$f` 和 symbol namespace 规则继续服从
Reference 010；`LanguageSpec` 不能绕过 linker export 或 foundation scope。

### 3.3 Prelude 不应公开什么

Prelude 不应成为：

- 所有逻辑 connective 的收容包；
- Hilbert 逻辑公理和普通定理的收容包；
- 一阶 binder 或集合论关系的隐式来源；
- 通用 parser、unifier 和 proof builder 的第二实现；
- 通过 Python import 自动注入全局语言 registry 的机制。

其最小性既降低下游 ABI 风险，也允许未来清楚定义不同 foundation/profile，而不假装所有逻辑
天然共享同一对象语言。

---

## 4. 历史目标概述

> 本节保留初稿诊断；对象分组以第 0.1 节修订契约为准。

### 4.1 理论接口的公共投影

每个逻辑或领域理论应提供：

```text
LANGUAGE
CALCULUS
AXIOMS
RULES
THEOREMS
```

其中：

- `LANGUAGE` 只包含 sorts、variable kinds、constructors 与 binders；
- `CALCULUS` 包含 judgment kinds 与 primitive inference rules；
- `AXIOMS` 是在该语言中的 primitive provable schemas；
- `RULES` 是 `CALCULUS` primitive rules 的简单公共投影；
- `THEOREMS` 是经过证明并命名的 assertions。

`prove_*`、`Imp`、`All` 等直接 Python API 继续存在。聚合元数据服务于 build、catalogue、agent
query、documentation 和 interface digest，不取代低心智负担的直接导入。

### 4.2 显式语言扩展

目标关系为：

```text
PRELUDE_LANGUAGE
    |
    +-- PROP_LANGUAGE
            |
            +-- FOL_LANGUAGE
                    |
                    +-- SET_LANGUAGE
```

“扩展”必须保留继承构造子的稳定身份和 lowering。一个 package 可以公布多个明确 profile，
例如纯 FOL、FOL with equality、set.mm-compatible logic prefix；不得让额外词汇因 import 顺序
悄然进入所有 profile。

### 4.3 单一语言事实源

一个 constructor semantic declaration 应唯一确定：

- typed author constructor；
- abstract `Term` application；
- binder/free-variable traversal。

Parser aliases、formatter、precedence 属于 `NotationSpec`；token lowering 和 syntax assertion
属于 `MetamathLanguageBinding`。它们通过稳定 `ConstructorId` 关联，不能复制 semantic
signature。Legacy projection 只可用于 inventory，不能被命名为稳定 `LANGUAGE`。

### 4.4 System 的职责收缩

目标 `System` 应组合而不是发明理论事实：

```text
System
  language environment  <- LANGUAGE
  axiom applications    <- AXIOMS
  inference applications<- RULES
  name/token binding     <- build context + lowering adapter
```

`System` 可以持有进程内 `SymbolId`、`NameResolver` 和 rule implementations，但这些运行时对象
应由稳定接口绑定而来。`_internal` 只负责受控 bridge，不再是语言定义的隐蔽事实源。

---

## 5. 历史阶段清单

> 本节中的长期迁移目标仍然有效；实际执行次序由第 0.1 节的 Phase 0.5–5 取代。

### Phase 0：建立分类清单和兼容基线

交付物：

- 为 Prelude、prop、fol 当前所有 sorts、variables、constructors、syntax assertions、logical
  axioms 和 primitive inference rules 建立机器可检查清单；
- 记录当前 2,675 个声明证明、三套 verifier 结果、catalogue 和 public import smoke tests；
- 给每个当前构造标注目标 owner：prelude、prop、fol、equality profile 或 set-domain。

验收：

- 每个当前发射的 syntax label 都有唯一分类；
- `wn/wi/wa/...` 与 `ax-1/ax-mp/ax-gen` 不再在设计记录中混称；
- 本阶段不改变 `.mm` 输出和公开导入。

### Phase 1：在 ProofScaffold 中完成最小 `LanguageSpec` 投影

交付物：

- 落实 Project 021/022 已提出的稳定 IDs、sort signatures、constructor signatures 和
  `LanguageInterface`；
- 支持显式 `extends`/composition 和冲突诊断；
- 由现有 DSL declarations 生成只读语言投影；
- 语言接口摘要排除 `SymbolId`、文件布局和导入顺序。

非目标：

- 一次实现所有 mixfix/binder/LaTeX 功能；
- 替换 BuilderV2、linker 或 verifier；
- 创建第二套 proof semantics。

验收：

- 两个独立 language environments 可在同一进程构建而不依赖全局导入顺序；
- constructor signature 冲突得到确定性错误；
- 现有 `Expr -> Wff` lowering 仍可通过 compatibility adapter 工作。

### Phase 2：Prelude 成为第一个语言事实源

交付物：

- Prelude 公开 `LANGUAGE`；
- `Builtins`、`structures`、`hilbert_rules` 与 `build` 从同一声明派生或通过稳定 IDs 绑定；
- Prelude 的 `__init__` 暴露语言接口，而不暴露后端可变 registry；
- `wn`、`wi` 明确分类为 syntax assertions。

验收：

- Prelude emitted symbols、`$f`、`wn`、`wi` 与当前输出兼容；
- Foundation Scope 的单 foundation、ambient `$f`、零 `$d` 不变量保持；
- 下游可以读取 Prelude language，而无需导入其私有 formula internals。

### Phase 3：prop 显式扩展 Prelude

交付物：

- `logic.prop.LANGUAGE` 显式 extends Prelude；
- 删除 `Imp/Not` 的独立重复事实源，保留兼容 re-export；
- 将 `Wi/Wn/Wa` 等形成能力从 `Mp` 的推理 registry 中分离；
- 用显式 constructor family 取代对 registry 私有映射的临时修改；
- `_builtins` 逐步拆为 vocabulary binding、lowering 和 shape adapter，而不是一个含义宽泛的模块。

验收：

- 当前 `Imp`、`Not`、`And` 等 authoring 调用方式通过兼容 re-export 继续工作，并获得非私有的
  正式导入路径；
- `logic.prop` 公开 `LANGUAGE/AXIOMS/RULES/THEOREMS`；
- generated corpus、catalogue、mypy、pytest 和三套 verifier 通过；
- 模块导入顺序不改变 language interface digest。

### Phase 4：fol 获得真实 sorts 与 binder 契约

交付物：

- `logic.fol.LANGUAGE` 显式 extends prop；
- 建立 setvar/term/class/wff 等当前 corpus 实际需要的 sort model；
- 为 `All`、`Exists` 和 substitution 声明 binder、scope、free-variable 与 capture behavior；
- 把 DV contracts 与 semantic variables 使用同一身份和 substitution map；
- 区分纯 FOL、equality 与 set.mm-compatible vocabulary profile。

验收：

- binder-aware tests 覆盖自由出现、shadowing、capture rejection 和 alpha-renaming；
- 不合法的跨 sort 构造在 authoring boundary 被拒绝，而非等到 token verifier；
- 现有 corpus 可以通过明确 compatibility profile 降低，不要求一次性改变全部生成证明。

### Phase 5：复核 primitive `RULES`

交付物：

- `RULES` 元数据表达 premises、conclusion、judgment sorts 和必要 side conditions；
- prop 明确包含 modus ponens；
- fol 明确决定并表达 `ax-gen`；
- syntax assertions 只通过 `LANGUAGE` 的 lowering metadata 出现；
- derived rules 继续作为可证明 theorem/API，而不是扩大 trusted primitive set。

验收：

- `logic.fol.RULES` 与实际 `.mm` primitive rule usage 一致；
- builder 可以从规则元数据和 implementation 绑定生成正确应用；
- 规则分类变化不改变已经验证的数学结论。

### Phase 6：迁移领域边界并移除兼容层

交付物：

- 把 `Elem/∈`、`Cv` 等明确归属到 set-domain language 或显式兼容 profile；
- 下游 set/number-theory packages 声明语言 extension 和 theory profile；
- 在至少一个发布周期后移除重复 declarations、全局 registry hacks 和过时 aliases；
- 生成 language catalogue 和 interface digest artifact。

验收：

- 纯 FOL consumer 不会隐式获得集合论词汇；
- set-domain consumer 通过显式 extension 获得稳定的相同构造身份；
- 不再有第二份可独立修改的 `Imp/Not` 或 constructor lowering 声明。

---

## 6. 迁移原则

### 6.1 先投影，后收敛

第一步应从现有运行代码生成 `LANGUAGE` 只读投影，而不是先重写 parser、AST 和 builder。投影能
立即暴露重复、冲突和遗漏；在验证等价后，再逐项把事实源收敛到声明式模型。

### 6.2 先保持证明行为，再调整数学边界

结构重构与内容迁移必须分开提交：

1. 在输出和 verifier 行为不变时引入语言对象；
2. 验证；
3. 再移动 `Elem` 等领域词汇或修正 `RULES`；
4. 再验证并记录接口变化。

### 6.3 公共直接 API 不因元数据而消失

`LANGUAGE` 是聚合和反射接口，不应迫使用户写：

```python
LANGUAGE.constructors["prop.imp"].apply(...)
```

用户仍应能够直接导入和书写：

```python
from logic.prop.language import Imp
from logic.prop.core import prove_syl
```

这里的模块拼写只是目标形态示例，不在本文中冻结；关键要求是构造子具有正式的非私有入口，
而不是要求用户导入 `_structures` 或通过 registry 间接调用。

元数据服务于构建、发现、校验和工具；直接函数服务于低心智负担的数学编程。

### 6.4 不以生成分区代替语言边界

proof partition 决定实现模块和检索区域，不决定 sort、constructor identity 或 theory extension。
移动 theorem 文件不得改变 `LANGUAGE`；移动语言构造子则必须经过语言 ABI 审查。

---

## 7. 风险与控制

| 风险 | 控制 |
| --- | --- |
| 新 `LanguageSpec` 成为又一份重复元数据 | 初期只读投影；每阶段删除或派生旧 registry，禁止长期双写 |
| 过早设计大而全 API | 只实现 prop canary 与一个 binder/DV canary 所需字段 |
| Foundation ABI 无意变化 | 比较 emitted Prelude LIR、interface digest 和 verifier artifacts |
| Sort 修正导致 2,675 个证明同时重写 | 提供明确 compatibility lowering profile，分批迁移 authoring terms |
| 全局 registry 导入副作用难以移除 | 新 API 显式注入 language environment；旧默认值仅作弃用兼容层 |
| `RULES` 重构扩大项目范围 | 延后到语言和 binder 数据稳定后单独实施 Phase 5 |
| set.mm 历史顺序与数学包边界冲突 | 区分 semantic ownership 与 emission compatibility profile |

---

## 8. 总体验收标准

本项目完成时必须满足：

1. Prelude、prop、fol 和至少一个具体领域包都能公开可摘要的 `LANGUAGE`；
2. 每个公开理论都能明确回答其语言、逻辑公理、primitive rules 和 theorems；
3. Prelude 是标准最小具体语言基础，ProofScaffold 是通用语言工具，两者没有职责重复；
4. prop 通过 extension 复用 Prelude 的 `Imp/Not`，而不是复制其语义声明；
5. fol 的 binder、free-variable、substitution 和 DV 契约可被机器检查；
6. syntax assertion、logical axiom 和 inference rule 在 API 中分类明确；
7. parser、typed constructor、formatter 与 lowering 不再维护可独立漂移的语言事实；
8. 现有直接 `prove_*` 和 constructor API 在迁移期保持可用；
9. BuilderV2、linker 和 Metamath verifier 仍是 lowering、链接和最终正确性的权威；
10. 当前完整 corpus 继续通过 Proof coverage、`mmverify`、`metamath` 和 `knife` 验证。

---

## 9. 第一实现切片

本轮采用的最小且高信息量切片是：

1. 新建结构相等的 Term v2，不修改 legacy `Expr` 行为；
2. `LanguageSpec` 只包含 semantic declarations；
3. `NotationSpec` 与 `MetamathLanguageBinding` 独立并具有各自摘要；
4. `PRELUDE_LANGUAGE` 提供 `Not/Imp`；
5. `PROP_LANGUAGE` 显式扩展并提供 `And2/And3`；
6. `And2/And3` 共享 `/\\` backend token，但具有不同 identity、arity 和 formation assertion；
7. 建立 judgment-only `CalculusSpec` 与 `Provable(Wff)` canary；
8. 保持所有现有 build 和 proof APIs 不变；
9. 验证 digest determinism、notation round-trip、symbolic exact lowering 和 verifier 无回归。

该切片能验证最关键的架构判断——语言是否真的可以成为包间稳定接口——而不必先解决全部 FOL
binder、规则元数据和领域迁移问题。
