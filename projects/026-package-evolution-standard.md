# Project 026：包演化标准（Package Evolution Standard）

> 2026-07-19 更名：原名"划分演化标准（Partition Evolution
> Standard）"。000 §13 术语冻结后，本文的规范对象是**发布包**
> 及其领域/模块结构的演化，而非一次性的"划分"；文件名同步改为
> `026-package-evolution-standard.md`。

> 状态：Phase 0 进行中（2026-07-19 立项）。
>
> 规范性依据：[Reference 014](../references/014-module-partition-and-knowledge-classification.md)
> （跨领域治理调研）、[Reference 015](../references/015-setmm-linearization-empirics.md)
> （set.mm 线索化实证）、[Reference 016](../references/016-mathbox-community-practice.md)
> （mathbox 社群实践）、[术语规范 000](../references/000-terminology.zh.md)。
>
> 上游项目：[Project 025](025-semantic-source-surface.md)（语义源码表面，已全门通过）。
> 交接对象：partition 仓（plan 生产与校验）与 transpiler 仓（plan 消费）。
>
> 本文中的"必须（MUST）""不得（MUST NOT）""应当（SHOULD）"具有规范性含义。
> **执行者遇到本文未覆盖的决策点时，必须停止并上报，不得自行发明。**

---

## 0. 目标与动机

partition 仓向 transpiler 交付划分方案。旧交付物（`proof-partition-result-v2`）
是拓扑序区间上的 cut 最优 DP 解，其命名与知识分类质量已被否决；
Reference 015 给出了结构性解释：

- **F1**：本图上 cut 目标几乎无主题信号（人工边界内部边占比仅 7–11%），
  cut 最优边界由枢纽落点驱动，与知识分类无关；
- **F3**：引用高度集中于少数胶水引理（前 500 名吸收 54% 逻辑引用），
  任何把枢纽边与主题边同权的目标函数都会被枢纽支配；
- **F5**：已定语料每年约 4% 证明重连、约 1% 语句迁移，静态最优解持续漂移。

因此本项目规定的不是"一个划分结果"，而是**划分的表示、必须满足的不变量、
与随知识生长而演化的操作**。两大支柱：

1. **分类主导**：模块边界与命名由知识分类（L1）声明，结构指标只做验证器；
2. **mathbox 机制化**：把 set.mm 已验证 25 年的前沿/核心单向膜
   （Reference 016）上升为包划分的一等机制，并提供写作工具链。

成功判据：prelude、logic、set-theory、numbers、number-theory 五区在
全语料统一图上的 plan-v3 方案通过第 3 节全部不变量校验（含跨区依赖
的 P4），且命名通过 definingness 审计。（2026-07-19 起取代早先"四域
各自独立校验"的口径。）

## 1. 规范模型

### 1.1 学科是命名空间，层是快照（2026-07-19 裁决）

成熟数学中，学科商图**有环**：数、组合学、数论两两之间都有双向
知识流动（necklace 计数证 Fermat 小定理方向、生成函数用分析、
Ramsey 数构造性下界用数论）。数学社区对此的承认方式是给桥领域
起专名：*arithmetic combinatorics*、*combinatorial number theory*、
*analytic number theory*、*additive combinatorics*。无环的只有
语句图，以及（划得好时）模块图。因此：

术语已冻结进 [000 §13（第九层：知识组织与发布）](../references/000-terminology.zh.md)：
**发布包**（release package）是发布与安装单元，可包含多个领域；
**数学领域**（mathematical domain）是发布包的一级子包，对应一个
学科（含**桥领域**）的命名空间与社区边界。由此：

- **数学领域 = 命名空间与社区边界**，不是依赖层；
- **领域间依赖必须是 DAG**（P7，见 §3）——这是不变量；但领域的
  **具体分层顺序**（谁在谁下游）是当前语料的快照属性，随知识
  生长改变，不得写死；
- DAG 在知识缠绕下仍可满足的机制是**桥领域**：学科名完整保留，
  工程分层在发布包视图内成立，跨领域缠绕被逼入显式桥领域；
  同一约束递归适用于领域内部的子包层级。

设计权责（用户裁决，2026-07-19）：**发布包尊重数学的知识传统**
——学科以领域名义完整聚合，缠绕的知识共同发布，无须为发布被
拆散或强行分层；**领域间无环要求尊重工程实践**——构建、lazy
加载、版本化需要可分层的依赖结构。妥协是双向各让一次：工程
单元（发布包）在内部结构上容纳知识传统，知识单元（领域）在
依赖纪律上服从工程约束。

两个实证锚点（2026-07-19，set.mm `e514bf2`）：

1. **叶子会变成基础设施**。语料截至 `cstr` 时词论簇（16 模块
   ~300 条）零消费者、零 number_theory 依赖，是纯叶子；但完整
   set.mm 中图论把闭途径直接定义为词（`clwwlk` 系列 600+ 处），
   necklace 引理 `cshwshash` 被 `hashecclwwlkn1`（闭途径等价类
   计数）消费，链条通向友谊定理。"层"是语料截断点的函数。
2. **同一学科名跨越多个层**。完整 set.mm 已有 `pnt`（素数定理）、
   `dirith`（Dirichlet）、`bpos`（Bertrand）——解析数论坐落在
   复分析之后，与初等数论（divides/gcd/primes，紧邻 numbers）
   相距一整个分析栈。number_theory 必然分叉为 `elementary` 与
   `analytic` 两个一级子包，由 P7 保证二者无环。

静态最优布局不存在；架构优化的目标是**让重新分层便宜**：模块
粒度足够细 + 桥包吸收缠绕 + split/promote 低成本。

### 1.2 归属与分类的两条编辑规则

1. **归属跟随证明依赖**。Metamath 依赖是证明依赖，存在"初等
   陈述、解析证明"的定理（`bpos` 即是）。定理的物理归属不得
   低于其证明所需的层；其传统分类身份记入 taxonomy 元数据供
   检索呈现。否则会制造 `elementary → analytic` 上行边。
2. **桥子包是一等公民**。A⊗B 内容不摊派给任一核心包，进显式
   桥包（沿用数学传统命名）。核心包边界保持窄且稳定，缠绕全部
   显式化。mathbox 膜（016）的晋升路径与此衔接：前沿内容孵化
   成熟后晋升为桥包或核心包成员。

案例裁决（2026-07-19，边数为语句级实测）：

- `number_theory` 区重开的 `decimal_arithmetic` section **不得**
  并入 numbers 同名模块：它有 14 条边依赖 gcd/divides/除法算法/
  素数性质，消费者是 `specific_prime_numbers`(20 边) 与
  `very_large_primes`(37 边)——它是大素数认证的十进制引理库，
  与 numbers 的同名 section **同名不同知**。留在 number_theory，
  按定义性改名（如 `primes.decimal_certificates`）。
- `cyclical_shifts_of_words`（nt 区重开 section）：纯移位引理归
  `combinatorics.words.shifts`；necklace 引理（`cshwshash` 系列，
  9 条边依赖素数谓词）属算术组合学桥内容。
- Ramsey / van der Waerden：零消费者叶子，归组合学。Ramsey 对
  nt 的唯一依赖 `ramcl → sumhash` 是错误归档（`sumhash` 是一般
  有限求和引理，被归在素数计数 section），重分类后零依赖。
- 词论簇整体抽出为 `combinatorics` 包，当前语料下分层
  `numbers → combinatorics → number_theory` 干净成立。

### 1.3 三层解耦（继承 Reference 014 §0）

- **L1 分类骨架**：分类树给出模块**路径与名字**（如
  `logic.implication`）。分类树是命名空间，不是依赖图。
- **L2 模块 ABI**：模块间依赖是显式声明的 **import DAG**。
  L1 树形与 L2 DAG 相互独立，不得由一方推导另一方（015 F2：
  72% 的 section 对无依赖先后，文件顺序属 L3 渲染）。
- **L3 物理分片**：文件布局、.mm 线索化顺序均为派生物，无规范内容。

两区一层（继承 Reference 016）：

- **prelude 层**：被全域引用的胶水引理集合，全局可见，
  豁免 import 记账与 cut 类指标（015 F3）。
- **core 区**：分类主导的主题模块，严格评审，ABI 稳定。
- **frontier 区**：按作者/agent 组织的前沿模块（mathbox 的等价物），
  宽松评审；**单向膜**：frontier 只能 import core 与 prelude，
  core 不得 import frontier，frontier 之间不得互相 import。

## 2. 交付物：`proof-partition-plan-v3`

partition 向 transpiler 的交接工件。规范形态：

```json
{
  "schema": "proof-partition-plan-v3",
  "domain": "logic",
  "source_hash": "…",
  "graph_schema": "proof-partition-metadata-v2",
  "draft": true,
  "prelude": {"path": "logic.prelude", "labels": ["idi", "…"]},
  "modules": [
    {
      "path": "logic.implication",
      "title": "Logical implication",
      "definingness": "一句话成员判据",
      "kind": "core",
      "sections": [3],
      "labels": [],
      "imports": ["logic.negation"]
    }
  ]
}
```

- `path`：小写点分路径，即生成包的子包路径（L1 投影）。
- `definingness`：一句话成员判据（Reference 014 §5.2 的存在性检验）。
  `draft: true` 时允许为占位文本；正式方案必须通过人工审计。
- `kind`：`core` 或 `frontier`；prelude 单列。
- 成员：`sections`（引用图工件 section id）与 `labels`（显式标签）取并集。
- `imports`：L2 声明；**prelude 不出现在 imports 中**（全局隐式可见）。

### 2.1 prelude 内容标准（待裁决，2026-07-19 提出）

用户方向性意见：**prelude 只放数学构造（语法构造子），不放定理；
公理或许也不需要**。当前实证 prelude（215 标签 = 90 构造子/公理
+ 125 胶水引理）由单一"引用吸收率"指标选出，混入了大量高频
定理，与该方向冲突。待专门讨论裁决的问题：

- prelude 的角色定位：全局**词汇表**（构造子 only，回答"能说
  什么"）vs 全局**基础层**（含高频推理胶水，回答"怎么说得省"）；
- 若构造子 only：125 条胶水引理（`idi`、`syl` 类）落回各自
  物理归属模块后，吸收率指标失效，P6 需要新的报告口径；
  高频胶水的可见性改由 import 或分层机制解决；
- 公理是否入 prelude：公理是知识声明而非词汇，倾向随其学科
  模块（`set_theory.axioms.*`）；但 `ax-mp`/`ax-gen` 类推理
  规则与语法构造子的边界需要明确判据；
- 该裁决直接影响 `--prelude-floor` 定标机制的存废。

裁决前，实证 prelude（吸收率定标）仅作压力测试基线使用。

## 3. 不变量（校验器 MUST 全部执行）

| # | 不变量 | 依据 |
|---|--------|------|
| P1 | 覆盖且不重：每个目标节点恰属一个模块（或 prelude） | 划分定义 |
| P2 | 路径合法且唯一；`title`、`definingness` 非空 | L1 命名 |
| P3 | 声明 imports 构成 DAG；被引用路径存在 | L2 无环 |
| P4 | 每条依赖边 u→v：同模块，或 v∈prelude，或 module(u) 直接声明 import module(v) | L2 完备 |
| P5 | 膜：core 不得 import frontier；frontier 不得 import frontier | 016 §6.1 |
| P6 | （报告项）模块规模、prelude 吸收率、枢纽过滤后模块内边占比 | 015 F3 |
| P7 | 领域 DAG：同一发布包内数学领域（一级子包）之间的依赖商图必须是 DAG；同一约束递归适用于领域内部各级子包（只计两端都在同一父节点内部的边） | §1.1 裁决；000 §13 |

P6 为报告项不阻塞：容量约束由 L3 分片处理（同一分类节点内
split-only），不得为满足规模而跨主题合并。

P7 说明：

- **DAG 性质是不变量，具体分层顺序不是**：领域的排序快照（如
  `numbers → combinatorics → number_theory`）仅输出为报告，供
  审计参考；把某个顺序写死会被解析数论一类内容击穿（§1.1）；
- 结构性保证：mm 源是线性的、语句依赖恒指向物理前方，故**只要
  成员归属是区间，任何商图自动无环**——当前区间式五区 draft
  平凡满足 P7。P7 真正的约束力出现在引入**非连续的分类式归属**
  （如把词论从 numbers 区间抽入 combinatorics）之后：分类可以
  偏离物理顺序，每偏离一步，校验器在正确的层级上报告是否成环；
- P7 永远可通过重新分组满足（极端情形子包退化为单模块，商图
  退化为模块 DAG 诱导子图），问题只在分组是否仍有知识意义——
  桥子包（§1.2）是有意义的分组方式；
- 校验实现：沿路径树逐层商图环检测，O(E × 深度)。**validator
  实现待落地**（当前实现覆盖 P1–P6）。

成员归属模型升级（待实现）：zone 的区间声明降级为 **bootstrap
默认值**；正式归属由分类声明（模块 → 包路径的显式映射）给出，
允许非连续。combinatorics 包（词论簇 + Ramsey/vdW + 桥内容）是
第一个非连续归属用例。

## 4. 演化操作（Phase 2/3 落地）

所有操作必须保持 P1–P5、P7 不变量，并在方案工件中留下可审计记录：

- **create**：新建 frontier 模块（作者/agent 命名空间）。
- **promote**：frontier → core。触发条件为需求拉动（出现第二个消费者，
  016 §6.2）。操作 = 移动 + 按命名标准改名 + 原路径留 shim/alias
  进入弃用窗口（016 §6.3 的 `*OLD` 协议等价物）。
- **split**：core 模块按分类细化（diffusion）。只分裂不合并；
  子模块路径为父路径的细化，旧路径保留 re-export shim。
- **rename**：路径改名必须伴随 shim 与弃用窗口；模块身份与路径解耦。
- **sync**：core 改名/重构后机械更新全部 frontier 模块。

下游引用规则：**frontier 中的语句在 promote 之前不得被其它模块正式
引用**（set.mm 规则照抄；工具必须让 promote 足够低摩擦）。

## 5. 命名标准（Phase 1 审计口径）

- **叶子名收敛为单名词**（或最短名词短语）；**共享前缀映射为
  子包**。当前 draft 路径是 section 标题的自动 slug，仅为占位；
  正式路径为策展产物，authored 标题保留在 `title` 元数据。实例
  （2026-07-19，来自五区 draft 审阅）：
  - `logic.axiom_scheme_ax_4_quantified_implication` … `ax_13`
    （10 个）→ `logic.axiom_schemes.ax04` … `ax13`；
  - `logic.derive_the_lukasiewicz_axioms_from_*`（9 个历史叙事
    模块）→ `logic.derivations.*`；
  - `logic.logical_*` → `logic.connectives.{implication, negation,
    conjunction, …}`；
  - `set_theory.introduce_the_axiom_of_*`（7 个）→
    `set_theory.axioms.{extensionality, replacement, …}`；
  - 词论 16 模块 → `combinatorics.words.{concatenation, subwords,
    prefixes, shifts, …}`。
- 路径唯一性（P2）按父包作用域检查；跨包同名叶子合法（但注意
  §1.2 案例：同名 section 未必同一知识单元，归属以依赖实证为准）。
- 模块名必须是成员的**定义性特征**：能写出一句"凡满足 X 者属之"。
- 反模式（拒收）：非定义性聚合（"misc"、"other"、"additional"）；
  多主题交叉筐（除非有独立 definingness）；容量驱动的语义碎片
  （为凑规模发明不存在的子学科）。
- 名字冲突或含混时，遵循 [术语规范 000](../references/000-terminology.zh.md)
  流程登记裁决。

## 6. Phases 与验收门

- **Phase 0（本轮）**：`plan-v3` schema + 草案生成器 + 校验器落地
  partition 仓；logic 域生成 draft 方案。
  - G0a：校验器对 logic draft 方案 P1–P5 全绿；
  - G0b：partition 仓 ruff / mypy strict / pytest 全绿。
- **Phase 1**：logic 域人工 definingness 审计（与用户合作），
  产出 `draft: false` 正式方案；对 DP 基线的对比报告
  （命名可解释性 + P6 指标）。
  - G1：审计后方案全绿且每个模块 definingness 经人工确认。
- **Phase 2**：frontier 机制与写作工具（scaffold / verify）。
  - G2：膜校验（P5）有正反用例；scaffold 生成的前沿包可本地 verify。
- **Phase 3**：promote / split / rename / sync 操作与 shim 登记。
  - G3：每个操作有前后方案对 + 不变量保持的回归用例。
- **Phase 4**：五区（prelude + logic + set-theory + numbers +
  number-theory）在全语料统一图上的压力验证。
  - G4：五区统一方案全绿（含跨区 P4 与逐区 P6 报告）；发现的
    规范缺口回写本文档。

## 7. 与 transpiler 的接口

plan-v3 取代 naming-profile 的 `module_paths` 作为模块路径来源；
transpiler 消费 `modules[].path` 生成子包结构，消费 `imports`
生成包内依赖声明。prelude 模块生成为全局 re-export 包。
本项目不改 transpiler 的发射内核（025 的契约不动）。

术语映射（000 §13）：transpiler 的产出物即**发布包**；
`modules[].path` 的首段即**数学领域**（一级子包）；其余段为
领域内子包/模块。P7 校验器工作在该路径树上。

## 8. 实施进展

- 2026-07-19：立项。依据 014/015/016 确立两支柱；plan-v3 schema、
  不变量 P1–P6、演化操作与命名标准定稿如上。
- 2026-07-19：Phase 0 完成。`mm_partition.planv3` 落地（draft 生成器 +
  校验器 + CLI `plan-draft` / `plan-validate`），logic 域 draft 方案
  生成并通过 P1–P5（G0a）；partition 仓 ruff / mypy strict / pytest
  全绿（G0b）。draft 方案 prelude 取全域引用前 48 名，49 个 section
  模块，definingness 为占位文本，待 Phase 1 人工审计。
- 2026-07-19：Phase 0 实证结果（logic 域，partition 仓提交
  `1ca0897`，基于用户 `21060ff` 四域整理后的最新 set.mm 快照
  （2740 节点）rebase 后重新生成并复验，工件
  `domains/logic/artifacts/classification-plan-v3.draft.json`）：
  - P6 指标：13380 条依赖边中 prelude（48 个标签）吸收 **49.5%**；
    过滤 prelude 后模块内边占比 **51.0%**，对照 015 F1 的 cut 最优
    区间基线 7–11%，支持"分类主导 + 枢纽单列"两支柱；
  - prelude 内容自动命中胶水引理（`syl`、`ax-mp`、`a1i`、`adantr`、
    `bitri`…）与语法构造子（`wi`、`wn`、`wa`、`wal`…），无需人工种子；
  - 模块规模 min 2 / median 19 / max 452，import 声明共 294 条，
    DAG 无环；两个 2 节点模块与 452 节点巨模块是 Phase 1 审计的
    首批对象（前者考察分类树归并，后者按 L3 split-only 处理）；
  - 名称直接采用 section 标题投影，"derive_the_*_axioms_from_*"
    一族（替代公理系统）提示应在 Phase 1 归入 `logic.systems.*`
    子树或考虑 frontier 定位（provisional，待裁决）。
- 2026-07-19：四域压力测试（Phase 4 提前执行，partition 仓提交
  `5924a1b`）。基底更新为 set.mm develop `e514bf2`（2026-07-18，
  source hash `ed3a34ef`），四域图重导，v2 流水线全量刷新，
  plan-v3 draft 四域 P1–P5 **全绿**。发现与修复：
  - **快照差分即晋升实录**：新旧快照唯一实质差异是 set.mm 顶部提交
    "Copy bj-zfauscl to Main as sepg"（mathbox→Main 晋升 +
    `zfausclOLD` 弃用 shim），Reference 016 §6.2/6.3 的协议
    在一次例行更新中直接观测到；curated 边界经标签重映射平移 +2
    即恢复，验证了"以标签为身份、序号为派生"的抗漂移设计。
  - **生成器三处硬化**（压力暴露的缺陷）：slug 需解码 HTML 实体
    并去变音符（B&eacute;zout→bezout）、域根需 slug 化
    （set-theory→set_theory）；"X (cont.)" section 并回同章节
    基础 section（线索化痕迹不是分类节点，set.mm 存在**同名
    section 分置两处**的实例）；section 粒度依赖环经 Tarjan SCC
    凝聚为合并模块并在 definingness 标记 Phase 1 语句级重分配。
  - **环普查**：logic 0 个；set-theory 2 个 2-way（等势 +
    Schröder–Bernstein、有限集 + 鸽笼原理）；number-theory 1 个
    2-way（互素/Euclid 引理 + 同余消去）；numbers 存在 **25-section
    大 SCC**（扩展实数系与序公理重述互依，1874/5475 节点）——
    set.mm 实数层在 section 粒度不可分层，为 Phase 1 首要对象。
  - **P6 四域画像**（prelude=48，吸收率 / 滤枢纽后模块内边占比）：
    logic 49.5%/51.0%，set-theory 37.1%/26.9%，numbers 47.0%/49.0%，
    number-theory 52.9%/72.8%。set-theory 双低说明全域统一
    prelude 尺寸不足，prelude 应按域标定（Phase 1 待裁决）。
  - G4 判据中"命名通过 definingness 审计"未达成（四域 definingness
    仍为占位文本），Phase 1 人工审计后方可撤销 draft 标记。
- 2026-07-19：压力测试范围重划为**五区统一模型**（partition 仓提交
  `fb73bf3`，口径修正 `5565fe9`）：prelude 升格为全局第五区，与 logic / set_theory /
  numbers / number_theory 并列，在全语料 [0, cstr)（17207 节点、
  353810 边，`domains/corpus`）上统一校验，跨区依赖边纳入 P4。
  - **prelude 定标判据**（provisional）：每区引用吸收率 ≥ 50% 的
    最小规模。吸收率与 P6 同口径（prelude 节点自身发出的边不计入
    分子分母；选择器初版含这些边导致 logic 报 49.7%，已修复为增量
    精确扫描并加回归测试），精确解为 **215 个标签**（logic 99、
    set_theory 88、numbers 27、number_theory 1；90 语法构造子/公理
    + 125 胶水引理——prelude ≈ 全语料词汇表 + 推理胶水）。吸收率
    曲线为幂律尾部、无明显拐点（约 48→34%，256→59%，1024→78%），
    故用下限判据而非拐点判据。
  - **五区统一校验全绿**：274 个模块（logic 48 + set_theory 125 +
    numbers 70 + number_theory 31），7065 条 import 声明，跨区无环、
    无跨区 section；逐区吸收率 logic 50.0%、set_theory 55.8%、
    numbers 58.6%、number_theory 53.2%。
  - **跨区画像**（单域视角不可见）：非 prelude 引用中指向本区的
    比例 logic 100%、set_theory 57.7%、numbers 40.3%、number_theory
    仅 8.5%（41726 条中 3546），number_theory 是 numbers/set_theory
    的重度消费者；分区 within-module 占比 logic 51.0%、numbers
    26.7%、set_theory 21.0%、number_theory 9.3%（后三者被跨区边
    稀释，模块内聚评估应以域内边为准）。
  - 工件：`domains/corpus/artifacts/classification-plan-v3.draft.json`
    （五区）；四域单域 draft 保留作对照。zones 由 domain config 的
    `zones` 字段声明，`--prelude-floor` 触发定标。
  - 流水线耗时实测：mono 冷启动 ~2.6s；export 全图 2.9s；
    plan-draft（含定标扫描）0.31s；plan-validate 0.18s——常驻
    mono 下全程 ~3.5s，"每次 set.mm 更新 → 重导 → 重定标 →
    重校验"可作为 CI 廉价常规操作，无需缓存或增量化。
- 2026-07-19（第二轮）：五包 draft 人工审阅 + 全库视角分析，
  规范正文更新（§1.1/§1.2/§2.1/§3-P7/§5）：
  - 审阅发现：numbers 有 **1883 节点巨型模块**（section 级 SCC
    缩点产物，占该包 35%，路径为 ~20 个标题拼接），需语句粒度
    实证是否可分层；61/274 模块 ≤10 条（长尾微模块待审计裁决）；
    词论簇挂在 numbers 下、跨包同名 section 两例（见 §1.2 案例）。
  - **P7 局部分层不变量定案**（全局包级无环否决），学科=命名
    空间、层=快照的模型与实证锚点写入 §1.1；归属跟随证明依赖、
    桥子包一等公民两条编辑规则与四个案例裁决写入 §1.2。
  - 命名标准补充：单名词叶子 + 共享前缀→子包 + 策展路径覆盖
    slug（§5，含五组实例映射）。
  - prelude 内容标准立项待裁决（§2.1）：用户方向为构造子 only、
    排除定理、公理存疑；影响 P6 口径与 `--prelude-floor` 存废。
  - 待实现（下一轮 partition 仓）：P7 校验器、分类式非连续归属
    （区间降级为 bootstrap）、combinatorics 包抽取用例。
- 2026-07-19（第三轮）：**知识组织术语冻结**（用户裁决）：发布包
  / 数学领域 / 桥领域 / 模块 / 前导包（暂定）登记入 000 §13
  （第九层，中英双语，版本 v0.2）。P7 表述统一为"同一发布包内
  领域间依赖 DAG，递归适用于领域内部"；不变量是 DAG 性质，
  具体分层顺序降为报告项。§7 补充 transpiler 术语映射（产出物
  = 发布包，path 首段 = 领域）。
