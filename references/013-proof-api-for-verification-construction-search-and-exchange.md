# Reference 013：面向验证、证明构造、搜索与交换的 Proof API

> 状态：架构裁决稿，2026-07-18。
>
> 本文承接 [Reference 011：将语言作为第一类元素](011-language-as-first-class.md) 与
> [Reference 012：结构、公理与证明的语义化定义规范](012-defining-structures-axioms-and-proofs.md)。
> 它评估当前 `semantic-api-v2`，给出下一阶段的边界与优先级；类名和文件格式名尚未冻结。

## 0. 结论先行

当前 API 已经是一套不错的**进程内、完整证明构造 API**：typed `Term`、
`AssertionSignature`、统一 assertion application kernel、`ProofAuthor.use()/qed()`、显式
catalog/断言应用许可集（`AssertionProfile`）和 DV 检查都应保留。

它还不是验证、搜索和交换共同依赖的证明对象规范。最大的缺口不是再增加一种表达能力，
而是边界没有闭合：

```text
对象能够构造并拥有内容摘要
                  ≠
对象已在锁定的 theory、依赖与信任策略下完成验证
```

`ElaboratedProof` 构造时进行的是 proof graph 的结构检查；真正按照 calculus、catalog 和断言许可集
重新应用每一步 assertion 的检查，目前发生在 `build_semantic_replay_plan()`。与此同时，现有
内部摘要规范表示映射虽有版本标签，却没有公开且规范的证明/理论档案编解码规范、严格 decoder、
wire schema 或完整 `VerificationEnvironmentLock`。
因此它可以作为受信 Python 生成流程的内部对象，却不能直接成为接收不可信输入的交换证书。

第二个缺口是没有真正的未完成证明状态。当前 `ProofDraft` 只包含 hypotheses 和已经完全具体化、
立即检查过的 steps；它更接近 `CheckedProofPrefix`，不能表达 goal、hole、metavariable、constraint
或可持久分支。普通线性证明不受影响，但交互构造与搜索没有合适的公共状态边界。

下一阶段应采用以下裁决：

1. **先把现有完整证明提升为可独立重放、可交换的证书。** 不另造一套与
   `ElaboratedProof` 平行的 Proof DAG 类。
2. **需要交互构造和搜索时，只增加一个最小、不可变的 `ProofState`。** 不把 hole 或
   metavariable 塞进 verifier 的 hole-free `Term` 或最终 proof。
3. **三层是内部不变量边界，不是三套普通用户 API。** Execution 层先复用现有重放与后端转换
   和 Metamath 构建产物；没有性能证据前，不设计新的 Proof VM、二进制 ISA 或硬件 packet。
4. **Package / provenance 先做轻量封装和伴随数据。** 不立即引入一套庞大的、可编辑的通用
   Package IR。

每条默认用户路径至多包含三个主要概念：

```text
普通作者      Theory -> ProofAuthor -> Proof
普通消费者    Theory + Proof
IDE / 搜索器  Theory + ProofState -> Proof
```

四种能力分别是构造（`prove/refine`）、验证（`verify`）、在 `ProofState` 上进行外部搜索，以及
交换（`load/save`）。`ProofAuthor` 继续是默认简化接口，`ProofState` 只向需要它的角色渐进披露。
普通用户不应被要求理解 catalog digest、许可集锁定细节、packet、Merkle node、execution plan、
frontier 或 provenance graph。

---

## 1. 公共概念限额是架构约束

IR 分层很容易演变成对象数量的膨胀。一个层次在内部有必要，并不意味着它应该成为用户必须手动
构造、传递和序列化的公开类型。

本项目采用以下 API 预算：

### 1.1 一条默认路径

完整证明作者应继续只写数学动作：

```python
author = THEORY.prove(MP2B_SIGNATURE)
h_phi, h_phi_psi, h_psi_chi = author.hypotheses
psi = author.use(AX_MP, h_phi, h_phi_psi)
chi = author.use(AX_MP, psi, h_psi_chi)
proof = author.qed(chi)

report = THEORY.verify(proof)
```

这里的 `THEORY.prove(...)` 只是把当前 `ProofAuthor(...)` 所需的 language/calculus/catalog/断言许可集
环境绑定起来，并为普通用法派生 snapshot-local proof ID。显式 `proof_id=` 只属于 advanced/debug
用法；它不引入第二套 proof semantics。

交换路径也应保持同样直接：

```python
THEORY.save(proof, "mp2b.skir")
proof = THEORY.load("mp2b.skir")  # decode + verify，默认出错即拒绝
```

以上名称是说明性的，尚未冻结；关键是普通用户只操作 `Theory` 和 `Proof`。未验证 packet、codec
limits、dependency lock 和 replay plan 都是内部或 advanced API。默认流程中的 `save` 在写出前验证，
`load` 在返回前验证。load 时的验证只是返回 `Proof` 的门槛，不会把“已验证”状态写进 proof
内容标识；需要审计证据时另取 `VerificationReport` 或 certificate。

### 1.2 渐进披露

只有交互式证明、IDE 或搜索器才需要看到 `ProofState`：

```python
state = THEORY.start(MP2B_SIGNATURE)
goal = state.goals[0]
outcome = state.refine(goal.id, assertion=AX_MP)
proof = outcome.state.finish()
```

普通的 forward proof 继续使用 `ProofAuthor.use()`。搜索器直接复用 `ProofState`；不得再引入一套
独立 `SearchState`。frontier、beam score、MCTS visit count、parent edge 和模型分数属于搜索器，
不是数学状态。

### 1.3 每个公开抽象必须偿还成本

一个新公开类型至少应满足下列一项，否则保留为内部实现：

- 它拥有与相邻类型冲突、无法合并的不变量；
- 两个以上独立消费者必须跨进程或跨实现理解它；
- 隐藏它会迫使用户重复填写无法可靠推导的信息。

仅仅“未来可能用于硬件、AI、协作或分析”不足以冻结一个 v1 类型。

### 1.4 一个事实只出现一次

若 verifier 能从 assertion、premises 和 substitution 推导 result、DV evidence 与 direct
dependencies，新的档案内容标识不应把这些派生值当作第二份权威输入。实现可以缓存或
展示它们，但必须重新计算；缓存不得改变新的 proof 内容标识。当前 v2 `semantic_digest` 尚未遵循
这一新的规范表示映射，兼容处理见 6.3 节。

---

## 2. 当前 API 已经解决了什么

当前路径可概括为：

```text
LanguageInterface + CalculusInterface + AssertionCatalog/断言应用许可集
                              │
                              v
                         ProofAuthor
                              │ use()
                              v
                 unified assertion application
                              │ qed()
                              v
                      ElaboratedProof
                              │
                              v
                build_semantic_replay_plan
                              │
                              v
                 legacy 后端转换 / Metamath
```

以下部分已经形成良好基础，不应重写：

1. `Term` 是不含 construction hole/metavariable、typed、backend-neutral 的 `Var | App`；它可以
   包含 schema/local/free variables，constructor、sort 和变量有稳定的名称标识符。
2. `AssertionSignature` 清楚区分 ordered premises、conclusion、schema variables 和 mandatory
   distinct contract，是验证、构造与搜索共同需要的 theorem ABI。
3. `ProofAuthor.use()` 走统一 application kernel，完成 unification、完整 substitution、结果计算
   与 DV 检查。显式 `target=` 和 `subst=` 只是约束，不是第二套语义。
4. `ElaboratedProof` immutable、root-reachable、无 hole，只包含 concrete assertion applications；
   family/combinator 已在详化前消失。
5. `build_semantic_replay_plan()` 已经能够在断言许可集约束下逐步从 catalog 解析 assertion，再以记录的
   premises、target 和 substitution 重新调用 public application kernel。
6. language、calculus、catalog 和 proof 已有带版本的摘要规范表示映射，为规范档案奠定了基础。
7. 四领域 transpilation 已证明这条完整证明默认流程能处理真实规模语料，并已有生成与
   生成产物导入/重新详化基线；逐 assertion replay、transitive closure 和独立
   Metamath verifier 仍须按第 7 节分项建立基线。

因此，下一步不是推翻证明写作 API，而是把已经存在的语义内核放到正确的公开边界后面。

---

## 3. 当前最大的断层

### 3.1 验证状态与内容标识混在一起

`ElaboratedProof.__post_init__()` 会先调用 `_validate_elaborated_proof()`，然后立即生成
`semantic_digest`。这项检查保证：

- theorem signature 和 hypotheses 对齐；
- step ID 不重复，premises 只向后引用；
- root 等于 theorem conclusion；
- 所有 application 对 root 可达；
- direct dependency 集合和 theorem-level DV scope 具有规范形态。

它不拥有 calculus/catalog context，因此不会重新解析每个 assertion，也不会重算 substitution、
result 或 satisfied DV。当前真正的语义重放在 `build_semantic_replay_plan()`。

这意味着：

- `semantic_digest` 是被声明内容的 hash，不是 validity certificate；
- 一个结构合法但 assertion application 错误的对象仍可拥有 digest；
- 函数名 `build_semantic_replay_plan` 把最重要的验证边界隐藏成了后端转换准备步骤。

应当把验证提升为唯一、明确、纯数据的公开入口：

```python
report = verify_proof(theory, proof)
# 或：report = theory.verify(proof)
```

`report` 至少区分 `ok`、稳定 error code、step/path、assertion、expected/actual 与 DV witness。
是否在内部使用 `VerifiedProof` wrapper 不应增加普通用户的必需名词；公开 `VerificationReport`
已经足够表达状态。

### 3.2 proof 没有闭合其依赖语义

当前 proof 规范表示映射记录 `calculus_digest` 和 assertion 名称标识符，但没有逐 assertion interface digest，
也没有精确 theory/import lock。名称标识符说明“它叫什么”，不能单独说明“这个名字对应哪份
signature 和哪份已验证 implementation”。

更重要的是，catalog 可以包含 theorem signatures。局部 replay 能证明“当前 step 相对于该
signature 合法”，却不能证明被引用 theorem 自己已有合法 implementation。若 whole-theory
verifier 不检查依赖 DAG，任意 theorem signature 都可能被误当成 oracle。

当前字段 `dependency_closure` 实际由当前 proof 的 step assertion 集合构造，只是 direct
dependencies，不是传递闭包。名称会误导增量验证、公理审计和 package 发布。

最小改进是：

1. 把该语义明确为 `direct_dependencies`；传递 closure 由 theory verifier 推导。
2. 给 assertion signature 提供稳定 `interface_digest`，与 theorem proof 的
   `implementation_digest` 分开。
3. 引入只读 `Theory` / `VerificationEnvironmentLock`：前者组织 language、calculus、assertion
   interfaces 和 imports，后者记录验证时选定的精确 language、calculus、interfaces、imports、
   断言应用许可集、`TrustPolicy` 和验证协议版本。断言许可集只限制“哪些 assertion 可以应用”；
   它不能授予 theorem 无证明可信性。
4. `Theory.verify_all()` 按 dependency DAG 验证所有 theorem implementations。默认 trust roots
   仅是 `TrustPolicy` 显式批准的 primitive declarations；本地 theorem 必须有 verified
   implementation。外部 theorem 只能来自 digest 匹配的已验证依赖档案，或被高级
   policy 明确标成 oracle 并进入 trust report。缺实现、digest mismatch 和 cycle 必须拒绝。
5. verification result 报告实际 direct dependencies、transitive theorem closure 与最终 assumption
   / trust closure。

当前 `DefinitionDecl` 只是被单独分类的无 premise assertion；`kind="definition"` 本身不证明
conservativity。它若被 policy 接受，仍必须作为显式假设出现在 trust closure，除非将来另有
conservativity protocol 给出证书。

proof 的数学实现内容标识与验证政策应分离：

```text
implementation_digest
  = H(theorem interface + concrete proof DAG + replay context
      + exact referenced assertion interface requirements)

verification_digest
  = H(implementation_digest + verification_environment_lock_digest)
```

同一个 proof DAG 在不同审计策略下仍是同一实现，但不是同一份验证结论。
`verification_digest` 只是验证结果标识符/缓存键，不等于验证过程本身、数字签名或可脱离 report
使用的 certificate。

### 3.3 现有交换物是可执行 Python，不是证明档案

当前 canonical helper 只做 `Mapping -> JSON bytes -> SHA-256`。内部规范表示映射虽有 version 字段，仍没有
公开的档案规范字节、严格 decoder、wire schema 或 accept/reject vectors。
生成包通过 import Python 模块执行 `prove_*()` 来重建 `PROOFS`；这对受信构建流程可用，却不是
跨组织、不可信输入或长期存档的边界。

第一版交换格式不需要通用二进制。严格 canonical JSON 足够作为第一版规范编码：

下面的 `VerificationEnvironmentLock` 和 `ProofArtifactV1` 是 advanced wire concepts，不计入普通作者的概念预算：

```text
ProofArtifactV1
  schema version
  VerificationEnvironmentLock
  theorem interface/ref
  active DV / replay context
  ordered applications:
    assertion interface ref
    premise positions
    complete substitution
  root position
  optional non-semantic provenance 伴随数据
```

`result`、`satisfied_distinct` 和 direct dependencies 由 verifier 产生，不是 packet 的权威事实。
若为调试或速度携带缓存值，verifier 必须重算并核对，且缓存不进入 implementation 内容标识。

wire data 到公开对象的边界必须是：

```text
strict decoder
  -> private unchecked packet
  -> replay 重算 result、DV evidence 与 dependencies
  -> 成功后才产生公开 Proof
```

这不是第二套公开 Proof DAG。unchecked packet 只是 decoder 的短命内部结果，永远不能冒充
`ElaboratedProof`。

codec 必须满足：

- versioned schema 与 domain-separated digest；
- unknown version、unknown/missing field、duplicate key 和 malformed ID 均出错即拒绝；
- 无 Python repr、pickle、callback、`SymbolId` 或绝对 workspace path；
- 确定性 map/array ordering 与 byte-identical round trip；
- term depth、step count、string/collection size 和总 bytes 的资源限制；
- 正反 golden vectors，供第二个最小 verifier 实现复现。

`VerificationEnvironmentLock` 只记录内容与政策要求，不会凭空提供依赖内容，也不表示验证已经
成功。自包含档案必须嵌入验证所需的 interface/implementation closure；轻量档案必须通过
content-addressed resolver 取得精确内容。
resolver 缺项或 digest 不符时一律出错即拒绝。

完整 theory 交换可用同一封套携带 interfaces、import locks、trust-root declarations 和 theorem
implementations。单定理档案是对 dependency closure 的切片，不需要发明另一种 proof
semantics。provenance、source map、narrative、signature 和 build record 通过 subject digest 连接，
不污染 proof 内容标识。

### 3.4 `ProofDraft` 不是 partial construction state

当前 `ProofDraft` 要求：

- 每一步已经有 concrete assertion、完整 premises、完整 substitution 和 result；
- premise 只能引用已有 step；
- step ID 是连续的 `<proof>/step:<index>`；
- 任意未确定 schema variable 立即失败。

它没有 goal、hole、metavariable 或 constraint，也没有可供搜索使用的稳定状态摘要。对同一个 immutable
`ProofDraft` 多次调用 public `apply_assertion()` 可以形成函数式分支，但每次会复制 tuple 并重扫
prefix，且没有 goal、完整 environment lock 或 state digest，因此不适合作为搜索边界。
`ProofAuthor` 另外用 Python 对象同一性判断 step 是否属于当前编写器；这是简洁、安全的线性
简化接口，但它本身不能持久化或跨进程分支。

改进方式不是把所有未完成对象塞进 `ProofDraft`，而是新增一个薄的 `ProofState`：

- immutable snapshot；
- 公开 `goals`、`is_complete` 与保守的 exact `snapshot_digest`；
- value-based `GoalId` / `StepRef`；
- 内部锁定 Theory/断言许可集引用，并保存 metavariables 与 equality/sort/DV constraints；
- `finish()` 只有在 goals 和 constraints 全部关闭后才产生现有 complete proof；
- 旧 `ProofDraft` 可逐步内化为 `_CheckedProofPrefix`，兼容期保留别名。

verifier 使用的 hole-free `Term` 必须继续只有 `Var | App`。construction-only 的 `MetaTerm`、
`MetaStore` 和 `ConstraintStore` 绝不能泄漏进最终 proof 或 verifier term union。公开 `Goal` 只是
read-only/opaque view：首版只需能取得 `GoalId`、rendered target 与有限的 kind/head 查询，再把 ID
传回 `refine()`；它不承诺暴露一个含 `MetaTerm` 的 public `Judgment` union。

immutable 是 observable contract；内部是否复制容器、使用 structural sharing 或 arena，由 branch
benchmark 决定，不在 v1 API 中承诺。

### 3.5 当前 application failure 不适合搜索

现有 assertion application 主要抛出带文本的 `AssertionApplicationError`。人可以阅读，但搜索、
批量候选、repair 和训练数据需要稳定分类，例如：

```text
unknown_assertion
profile_forbidden
premise_arity_mismatch
unification_conflict
underdetermined_substitution
sort_mismatch
target_mismatch
missing_distinct_pair
dependency_unverified
```

内部应抽出不依赖 `ProofDraft`/`StepId` 的 concrete application checker。`ProofAuthor.use()`、
verifier replay 和 `ProofState.finish()` 的最终统一合法性判定必须共享它。backward `refine()` 另由
约束生成型详化器产生 metas 与 residual constraints；partial application 闭合后必须
reify，并通过同一 concrete checker 才能进入最终 proof。两者可共享 term matching、substitution 和
DV primitives，但不能假装 incomplete refinement 与 concrete validity decision 是同一条执行路径。

---

## 4. 四类需求的最小 API

| 需求 | 当前可复用部分 | 最大不足 | 最小公开改进 |
|---|---|---|---|
| 验证 | application kernel、replay、calculus/catalog digest 与许可集检查 | 构造/digest 与 verified 状态混淆；theorem dependency closure 未验证 | `Theory.verify()`、`verify_all()`、结构化 report、精确 lock |
| 证明构造 | `ProofAuthor.use()/qed()` 调用简洁的默认流程 | 环境参数过多；无真正 partial state | `Theory.prove()` 绑定环境；高级用户才使用 `ProofState` |
| 搜索 | typed signature、函数式 draft branch、共享最终合法性判定 | 分支复制/重扫成本高；无 goal/refine、锁定状态内容标识和机器可读失败信息 | 复用 `ProofState.refine()`；frontier/score 留给搜索器 |
| 交换 | 稳定名称标识符、带版本的内部摘要规范表示映射 | 无公开 wire schema/codec/decoder 和完整验证环境锁定清单；必须执行 producer Python | `Theory.load/save` + 严格规范的档案格式，load 必须验证 |

### 4.1 验证

验证有两个层次，但普通 API 可以只提供一个入口：

```text
local replay
  检查 proof 的每一步相对于精确 assertion interfaces 合法

theory closure verification
  递归检查所有引用 theorem 的 implementation，最终落到声明的 trust roots
```

`Theory.verify(proof)` 默认完成所需 closure 检查。advanced options 可以请求 full trace、只验证
已缓存依赖后的增量 closure，或输出后端转换/Metamath evidence；默认行为必须安全且无需用户组装
calculus、catalog 和断言许可集。

### 4.2 证明构造

完整 forward proof 不需要 goal/hole API。保留：

```python
mid = author.use(assertion, *premises, target=None, subst=None)
proof = author.qed(mid)
```

只有 underdetermined 或 backward construction 才进入：

```python
state = THEORY.start(signature)
goal = state.goals[0]
outcome = state.refine(goal.id, assertion, subst=None)
```

`refine()` 从 assertion conclusion 匹配目标；assertion premises 产生 ordered subgoals，尚未确定的
schema variables 留在内部 constraint store。失败只返回 structured diagnostic；输入 state 已经
immutable，调用方不需要接收一份重复的“unchanged state”。

### 4.3 搜索

核心库只负责确定性状态转移，不负责搜索算法：

```text
ProofState + RefineRequest
        -> RefineSuccess(new state, created/closed goals)
         | RefineFailure(code, details)
```

从同一个 immutable state 调用多次 `refine()` 就是分支；保留旧 state 就是 undo，因此首版不需要
`fork()` 或 `undo()` 方法。最终 proof 只提取 root-reachable closure；失败探索留在外部 search
arena。

首版只承诺 canonical snapshot bytes 相同就有相同 `snapshot_digest`。它是保守的状态快照内容标识，
不承诺跨 lineage 的数学状态等价或 search dedup；等价状态完全可以有不同摘要。alpha-equivalence、
proof equivalence 和 aggressive normalization 在真实 corpus 数据证明收益前，不进入公共同一性契约。

第一阶段只需从 Theory 派生按 conclusion judgment kind、head constructor 和 premise count 的只读
候选索引。它是可重建的内部索引或搜索伴随数据，不进入 semantic catalog/digest。embedding、
历史频率和 model ranking 同样只是由摘要关联、仅供参考的伴随数据。

### 4.4 交换

交换应区分：

- `Proof`：完整的数学 proof DAG；
- `VerificationEnvironmentLock`：解释并验证它所需的精确内容与政策要求；
- 档案封装：schema、可选 dependency payload 与非语义 metadata。

三者可以装入一个文件，但不能因此混成一个 semantic digest。默认 loader 必须先 decode、检查
limits、解析 lock、验证 closure，再返回普通 `Proof`。只有 advanced API 才能取得 unchecked
packet。

自包含档案随文件提供 closure；轻量档案则要求调用方的 resolver 按 digest 提供
closure。仅有 `VerificationEnvironmentLock` 但无法解析其内容时，loader 必须拒绝。

第一版只承诺 ProofScaffold semantic model 与 Metamath 后端转换的无损 round trip。Lean、Coq、
Isabelle 或 SMT adapter 必须声明保真级别和 reconstruction 要求；不得先设计一个所有证明系统的
语义并集。

---

## 5. 必要的内部层次，但不是三套用户 API

三种对象具有互相冲突的不变量，因此内部边界仍然必要：

| 内部层 | 核心不变量 | 普通用户是否看见 |
|---|---|---|
| Construction / `ProofState` | 允许 goals、metavariables 和 constraints；动作原子化；可持久分支 | 只在交互与搜索时渐进披露 |
| Complete Proof / DAG | complete、typed、resolved、acyclic、root-reachable；只有 concrete assertion applications | 是，公开为 `Proof`；当前由 `ElaboratedProof` 演进 |
| 执行表示 | 无推断、引用已解析、线性；`SemanticReplayPlan` 仍 backend-neutral，binding 后的 legacy proof / `.mm` 才 backend-specific | 否；先复用现有两段路径 |

与三者正交的也不是一个庞大的第四 IR，而是两个薄对象：

```text
TheoryInterface / VerificationEnvironmentLock
  提供 semantic environment 与精确内容、政策要求

伴随数据
  source map、provenance、narrative、search score、embedding、timing
```

一个推荐的数据流是：

```text
                 普通作者
                    │
              ProofAuthor 简化接口
                    │
                    v
Theory ────────> complete Proof ────────> verify / save
   │                  │
   │                  v
   │          internal replay/后端转换 ─────> .mm / verifiers
   │
   └────> ProofState ── refine ──> ProofState
              ^                         │
              └──── search engine ──────┘
```

这里没有用户手工执行“Construction IR 转换到 Proof DAG，再转换到 Execution IR”的
工作流。`finish()`、`verify()` 和 backend 工具自动完成边界转换。

---

## 6. 标识、同一性、摘要与缓存

### 6.1 分开名称标识符与内容兼容性

- language、sort、constructor、assertion、theory 使用稳定、可读的名称标识符；
- interface digest 表示同一名称标识符的精确内容要求；
- theorem signature 的 `interface_digest` 与 proof body 的 `implementation_digest` 分开；
- 断言应用许可集与 trust policy 进入 `VerificationEnvironmentLock`，并通过其摘要进入
  verification digest，不改变相同 proof DAG 的实现内容标识；
- source path、作者、模型、时间、note、rendering 和 backend token 不进入 proof 内容标识。

### 6.2 StepRef 与 snapshot 不是全局数学标识符

proof-local canonical positions 足以作为 v1 档案中的引用。当前没有必要把每个 step 变成全局
Merkle object。若未来增量验证数据显示 node-level cache 是主要收益，再增加 domain-separated
node digest；不要提前承诺跨 proof 的子图等价。

construction state 中的 `GoalId`、`MetaId` 与 `StepRef` 只需在 snapshot lineage 内 value-stable，
不需要永久全局唯一。`snapshot_digest` 只摘要 exact canonical snapshot，不承担跨 lineage dedup。

### 6.3 摘要只能证明内容相同

任何内容摘要都不能代替 verifier result。API 与文档不得用 `semantic_digest` 暗示“已经
验证”。兼容期保留 legacy `semantic_digest`；新的 versioned `implementation_digest` 使用不同的
摘要域/规范表示映射，加入精确 assertion interface requirements，并可排除可推导缓存。因此它不承诺
等于旧值，也不能只是旧字段的 alias。迁移期 verification report 可以同时携带二者，并明确
`verification_environment_lock_digest` 与 `verification_digest`。

---

## 7. 性能必须按真实边界测量

现有四领域 benchmark 很重要，但下一阶段必须把以下时间分开，不能都称为 validation：

1. Python/生成产物导入或 JSON decode；
2. theory interface/lock resolution；
3. proof object 的结构检查与 digest；
4. assertion-by-assertion semantic replay；
5. transitive theorem closure verification；
6. 后端转换与独立 Metamath verifier；
7. warm incremental verification；
8. scalar `refine` throughput，以及 batch API 引入后的 batch throughput；
9. 档案编解码 throughput、bytes 和 peak RSS。

每次基准必须记录：source commit、ProofScaffold/transpiler commit、档案摘要、Python/runtime、
冷/热缓存状态、wall/user/sys time、峰值内存和至少三次运行的中位数。import 后只比较 object count
或 digest 不得标成完整 proof verification。

当前 public `apply_assertion()` 每次产生新 tuple，并由 `ProofDraft` 重扫 prefix，长证明的朴素累积
成本可能达到 O(n²)；`ProofAuthor` 的 mutable fast path 已经避免了单线生成的主要成本。未来
`ProofState` 只承诺 immutable observable behavior；是否使用 structural sharing 或 arena，必须由
branch benchmark 决定。

紧凑 Execution IR、batch packet 或 binary codec 只有在以上测量确认 JSON decode、replay 或 `.mm`
后端转换是主瓶颈后才进入设计。性能目标先由数据给出，不以“硬件未来可能需要”为理由冻结 ISA。

---

## 8. 最小迁移顺序

迁移应由小的纵向切片组成，而不是一次实现完整 IR 蓝图。

### 8.1 共同前置：稳定统一合法性判定

1. 增加只读 `Theory` 简化接口，并配套验证环境锁定清单，统一绑定 language、calculus、catalog、断言应用许可集、
   `TrustPolicy` 和 theorem registry；现有低层对象继续可用。
2. 从当前 application 代码抽出不依赖 `ProofDraft` 和位置 StepId 的 concrete checker，并定义稳定
   diagnostic codes。它成为 `ProofAuthor.use()`、proof replay 与未来 `ProofState.finish()` 的共同
   统一合法性判定。
3. 从 `build_semantic_replay_plan()` 提升出 public `verify_proof()`；后端转换消费已验证 replay，
   不再让 replay-plan builder 兼任唯一验证入口。

这三项稳定后，验证/交换与 construction/search 可以并行推进；后者不必等待整个档案交换工作完成。

### 8.2 轨道 A：验证与交换

1. **A1，local replay：** 返回 structured `VerificationReport`，提供可关闭的 step trace，并建立
   assertion-by-assertion 性能基线。
2. **A2，theory closure：** 区分 assertion `interface_digest`、proof
   `implementation_digest`、direct dependencies、transitive theorem closure 和 trust closure；实现
   `Theory.verify_all()`，对 missing implementation、cycle、unverified dependency、oracle 与 policy
   violation 时出错即拒绝。
3. **A3，数据档案：** 统一 Term/Judgment/Signature/Proof 规范表示映射，实现 strict
   decoder、wire schema、resource limits 和 golden accept/reject vectors；通过 private unchecked
   packet adapter 重放为现有 complete proof，不创建第二套 public DAG。
4. 首个 canary 只要求在新进程、不 import producer package 的情况下 round trip 与 replay。第二个
   最小 codec/verifier implementation 是 schema 冻结前的发布门，不阻塞 A1 的 API 落地。

### 8.3 轨道 B：construction 与 search

1. 在共同 checker 周围增加约束生成型详化器，以及最小 `ProofState`、opaque
   `Goal`、`start/refine/finish` 和 exact `snapshot_digest`。
2. 首批 constraints 只包括 typed term equality/unification、sort 和当前已有 DV contract；不提前
   加入 freshness 或通用 plugin framework。
3. `ProofState` 使用 lineage-scoped value refs；`finish/save` 时把 root-reachable steps 规范化为
   proof-local canonical positions，档案只保存这些位置引用。`ProofAuthor` 可以继续用 Python
   object handle 做安全、调用简洁的简化接口所有权检查；现有默认流程不必接受任意
   外部 `StepRef`。
4. 让 `ProofAuthor` 的最终统一合法性判定复用共同 checker，保证生成代码无需改写。
5. 从 Theory 派生最小 conclusion-head query index；确认 scalar branch benchmark 后再决定
   structural sharing、arena 和 `refine_many()`。

### 8.4 后续：由测量驱动的优化与生态能力

只有在上述 correctness 和 performance 数据稳定后，才按证据选择：

- node-level hashes 与增量 verification cache；
- proof repair 与 semantic diff；
- streaming/NDJSON 或紧凑二进制档案；
- batch candidate packet 与专用 Execution IR；
- dependency-closure slicing 和签名证书；
- 更完整的 module/package publication envelope。

---

## 9. 验收标准

### 验证与交换

- 修改 assertion ref、premise、substitution、DV context 或 root 时，public verifier 以稳定 code
  拒绝；拥有 digest 不影响结果。缺 theorem implementation、digest mismatch、dependency cycle 和
  未声明 oracle 同样拒绝，report 区分 direct、transitive 与 trust closure。
- verifier 能在新进程中不 import producer Python package 而检查档案。自包含档案
  自带 closure；轻量档案的 resolver 缺项或摘要不符时拒绝。
- unknown/missing field、duplicate key、unknown schema、malformed ID 和 resource bomb 均拒绝。
  schema 冻结前，第二个最小实现必须复现 canonical bytes 与 golden vectors。
- provenance/source map 改变不影响 implementation digest；proof body 改变不影响 theorem
  interface digest；断言应用许可集、trust policy 与 verification result 不混入 proof 内容标识。

### 构造、搜索与易用性

- 现有 `ProofAuthor.use()/qed()` 代码保持可用。普通作者只面对 `Theory -> ProofAuthor -> Proof`，
  consumer 只需 `Theory.verify/load/save`，unchecked packet 默认不可见。
- `ProofState` 能表达 open goal 和 underdetermined substitution；`Goal` 是 opaque view，最终 `Proof`
  不含 hole/meta。同一完整 action sequence 经 `ProofAuthor` 与 `ProofState.finish()` 得到相同
  implementation digest。
- 从同一 immutable state 可无副作用地产生多个分支；失败只返回 diagnostic。相同 canonical
  snapshot bytes 有相同摘要，但不承诺跨 lineage 等价去重。frontier、cost 与模型分数不进入 state
  内容标识。
- 若以后增加 batch transition，其逐项结果必须与 scalar transition 一致；在此之前 batch 不是
  v1 验收前置。

### 性能

- import/decode、structure/digest、semantic replay、theory closure、后端转换、independent verifier 和
  incremental path 分别计时；轻量 object/digest check 不得标作完整 verification。
- 新增抽象不得增加默认 proof ceremony；structural sharing、binary codec 和 execution packet 必须由
  benchmark 证明必要。

---

## 10. 明确不做

为防止 IR inflation，近期不得把以下内容列为 P0/P1 前置条件：

- 在 `Term` 或最终 `Proof` 中加入 `Hole | MetaVar`；
- 同时公开 Construction IR、Search IR、Proof DAG IR、Execution IR 四套对象图；
- 新建一套与 `ElaboratedProof` 平行、字段重复的 Proof DAG；
- 把 frontier、ranking、embedding、cost-to-go 或模型状态放进 semantic core；
- 现在冻结 Proof VM、binary ISA、FPGA packet、CBOR/Protobuf schema；
- 现在部署全局 Merkle store 或承诺 proof/alpha equivalence 的规范同一性；
- 设计所有 constraint 类型都可插拔的通用 framework；
- 设计 Lean/Coq/Isabelle/SMT 全部语义的最小公倍数；
- 把 source map、作者、模型、时间和 narrative 混入 proof semantic digest；
- 把 generated Python import 当作交换、验证或长期存档协议；
- 为了统一名称而把现有 legacy `skfd.proof.ir` 扩肥成新的 semantic IR；
- 在真实性能数据表明必要前，建立可编辑的通用 Package/Module/Provenance IR。

---

## 11. 对更广场景的回答

验证、构造、搜索与交换四类边界一旦成立，其余场景应作为派生能力，而不是反过来塑造 v1 核心：

- normalization、compression、diff、repair 和 dependency minimization 从 complete Proof DAG 与
  dependency data 派生；
- IDE、LLM trajectory、candidate validation 和 curriculum 从 `ProofState` transition 与 structured
  diagnostics 派生；
- publication、citation、provenance、narrative 和 source map 从档案伴随数据派生；
- distributed frontier、GPU/FPGA packet 和 hardware execution 从已验证 Proof 的后端转换派生；
- knowledge graph、proof mining 和历史分析从证明/理论档案的只读视图派生。

最终的架构原则不是“用一个扁平 IR 做所有事情”，也不是“为每个场景建立一套 IR”，而是：

> 用一个具体断言应用内核和一个约束生成型详化器，维护
> partial state、complete proof 与执行表示三种互不混淆的不变量；再用一个极小
> 简化接口，让每类用户只看到自己需要的入口。

近期最有价值的工作不是增加更多 IR 名词，而是让下面这条路径第一次真正闭合：

```text
简单地写出 proof
    -> 在精确 theory 下确定性验证
    -> 保存为不执行 producer Python 的版本化纯数据档案
    -> 在另一个进程或实现中加载并重新验证
```
