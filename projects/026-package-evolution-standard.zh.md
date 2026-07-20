# Project 026：包演化标准（Package Evolution Standard）

> 2026-07-19 更名：原名"划分演化标准（Partition Evolution
> Standard）"。000 §13 术语冻结后，本文的规范对象是**发布包**
> 及其领域/模块结构的演化，而非一次性的"划分"；文件名同步改为
> `026-package-evolution-standard.zh.md`。

> 状态：Phase 0 进行中（2026-07-19 立项）。
>
> **发布拓扑取代说明（2026-07-20）：**
> [Project 028](028-top-level-knowledge-release-units.zh.md) 取代本文中如下假设：
> 由一个生成的发布 wrapper 容纳多个数学领域、由证明归属推导公共
> ownership，或把 mathbox/frontier 治理纳入 V1。历史 plan-v3 记录
> 继续作为可复现实证保留。现行 V1 语义是：十六个裸数学根各自对应
> 一个数学发布单元；Prelude 是独立基础设施发布；mathbox 是明确
> 排除、另待治理的范围。
>
> 规范性依据：[Reference 014](../references/014-module-partition-and-knowledge-classification.md)
> （跨领域治理调研）、[Reference 015](../references/015-setmm-linearization-empirics.md)
> （set.mm 线索化实证）、[Reference 016](../references/016-mathbox-community-practice.md)
> （mathbox 社群实践）、[术语规范 000](../references/000-terminology.zh.md)。
>
> 上游项目：[Project 025](025-semantic-source-surface.zh.md)（语义源码表面，已全门通过）。
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
与随知识生长而演化的操作**。在 Project 028 拓扑下，现行支柱有二：

1. **分类主导**：模块边界与命名由知识分类（L1）声明，结构指标只做验证器；
2. **一根一数学发布**：十六个裸根及其 distribution owner 由
   Project 028 固定；实现依赖保持完备、无环，但不决定公共 ownership。

五区 plan-v3 压力测试继续作为历史里程碑保留。现行成功判据是
Project 028 G0–G5。mathbox 工作仅在独立治理项目裁决后恢复。

## 1. 规范模型

### 1.1 学科是命名空间，层是快照（2026-07-19 裁决）

成熟数学中，学科商图**有环**：数、组合学、数论两两之间都有双向
知识流动（necklace 计数证 Fermat 小定理方向、生成函数用分析、
Ramsey 数构造性下界用数论）。数学社区对此的承认方式是给桥子领域
起专名：*arithmetic combinatorics*、*combinatorial number theory*、
*analytic number theory*、*additive combinatorics*。无环的只有
语句图，以及（划得好时）模块图。因此：

术语已按 Project 028 修订并冻结进
[000 §13（第九层：知识组织与发布）](../references/000-terminology.zh.md)。
在 set.mm V1 中，数学领域、裸公共 Python 根与数学发布包一一对应；
基础设施发布与无定义 profile 不拥有数学根。由此：

- **数学领域 = 公共知识 ownership 范围**，不是依赖层；
- **数学发布实现之间的依赖必须构成 DAG**（P7，见 §3），但具体
  分层顺序只是快照属性，不得写死为本体；
- **桥子领域**在一个已裁决根下有且仅有一个 canonical owner，同时
  可有复数 discovery facets；未经独立裁决不得新建顶级根；
- 同一实现无环与完备约束递归适用于模块与子包投影。

设计权责（用户修订裁决，2026-07-20）：公共根尊重数学知识传统；
显式实现与发布依赖尊重工程约束。两种投影不一致时，工具链应分离
公共 facade 与 proof provider，而不是只为修复商图就把声明移动到
另一个数学主题。

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

### 1.2 ownership 与实现的两条编辑规则

1. **公共 ownership 跟随本体，实现跟随证明依赖。** Metamath
   依赖是证明依赖，存在"初等陈述、解析证明"的定理（`bpos` 即是）。
   此类定理仍由其数学主题公开拥有，provider 则记录解析侧的
   `requires` 闭包。若现行 schema 不能表达由此得到的无环 provider
   投影，rollout 必须暂停，等待 facade/provider 分离；不得静默
   改写公共 ownership。
2. **桥子领域必须显式，但不得擅造根。** A⊗B 内容在十六根之一
   下获得一个 canonical owner，并附加跨领域 facets。独立发布的
   bridge root 需要未来裁决。mathbox 晋升不在本项目 V1 范围内。

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

原"两区一层"plan-v3 模型只为解释历史工件而保留。在 Project 028 下：

- **Prelude** 是独立且显式锁定的基础设施发布；
- **core 数学内容**归入十六根之一；
- **mathbox/frontier 内容**排除在 V1 目标来源范围之外，等待独立
  治理裁决。

## 2. 历史交付物：`proof-partition-plan-v3`

这是 partition 在 2026-07-19 压力测试中交给 transpiler 的工件。
Project 028 已以 `knowledge-release-plan-v1` 取代它，作为现行 V1
工作目标。下列形态只在复现历史 plan-v3 工件时仍具规范性：

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

### 2.1 prelude 内容标准（定位已裁决：维持 pre-logic，扩展为开放问题）

判定框架与否定性裁决见
[Project 027：Prelude 边界 RFC](027-prelude-boundary-rfc.zh.md)：

- **prelude 维持现状的极小 pre-logic 状态，暂不扩展**
  （2026-07-19 三次裁决）；是否/何时扩展到候选边界（集合/类
  基础 + 关系与函数，实证基线 1370 节点 / 18 公理）是 027 §12
  首项开放问题；
- 边界判据（若扩展）是**通用理论构造能力**（表示原语、组合
  机制），不是"常用数学内容"——**自然数（含 ω）、有限性、
  归纳、有限递归、有限序列/fold 均不入 prelude**，归
  `set_theory` 与 `number_systems` 数学发布单元（二次裁决，
  实证依据见 027 §4.1 后注）；
- 迁移单位是**能力簇**（capability slice：构造连同形成/相等/
  引入消去/归纳规则的最小可用闭包），不是单个 label，也不是
  频率排行榜前 N 名——这**取代**本节最初"只放构造子、不放
  定理"的表述：判据是能力而非句法类别；
- "只依赖 prelude"不是架构指标；应用场景经 **profile**（只含
  聚合依赖的发布包）组装；
- 对象理论 prelude 与 Python 书写层分离：语义基础归 prelude，
  书写经济性归 Python 层；
- `--prelude-floor` 吸收率定标保留但**降级**为压力测试基线
  工具；量化边界待 027 §10 实证（能力簇 × 五指标）完成。

历史五区 corpus 的 `prelude.core`（215 标签）只作为 plan-v3
压测基线保留；Prelude 的现行独立发布边界由 Project 027/028 管辖。

## 3. 不变量（校验器 MUST 全部执行）

| # | 不变量 | 依据 |
|---|--------|------|
| P1 | 覆盖且不重：每个目标节点恰属一个模块（或 prelude） | 划分定义 |
| P2 | 路径合法且唯一；`title`、`definingness` 非空 | L1 命名 |
| P3 | 声明 imports 构成 DAG；被引用路径存在 | L2 无环 |
| P4 | 每条依赖边 u→v：同模块，或 v∈prelude，或 module(u) 直接声明 import module(v) | L2 完备 |
| P5 | 旧膜校验，仅适用于另行治理的 frontier 范围；Project 028 V1 排除 mathbox/frontier，不调用 P5 | 016 §6.1；028 §3 |
| P6 | （报告项）模块规模、prelude 吸收率、枢纽过滤后模块内边占比 | 015 F3 |
| P7 | 数学发布 DAG：十六个数学发布单元之间的实现依赖图必须是 DAG；同一约束递归适用于各根内部的模块/子包投影 | §1.1（经 028 修订）；000 §13 |

P6 为报告项不阻塞：容量约束由 L3 分片处理（同一分类节点内
split-only），不得为满足规模而跨主题合并。

Project 028 拓扑下的 P7 说明：

- **DAG 性质是不变量，具体分层顺序不是**：发布排序快照（如
  `number_systems → combinatorics → number_theory`）仅输出为报告，供
  审计参考；把某个顺序写死会被解析数论一类内容击穿（§1.1）；
- 结构性保证：mm 源是线性的、语句依赖恒指向物理前方，故**只要
  成员归属是区间，任何商图自动无环**——当前区间式五区 draft
  平凡满足 P7。P7 真正的约束力出现在引入**非连续的分类式归属**
  （如把词论从 numbers 区间抽入 combinatorics）之后：分类可以
  偏离物理顺序，每偏离一步，校验器在正确的层级上报告是否成环；
- 不得只靠语义重分组满足 P7。发布层循环必须通过 facade/provider
  分离、分阶段实现分片或真正的共同接口来修复，同时保留策展的
  公共 owner；
- 历史 plan-v3 validator 按 path 首段检测商图循环；
  `knowledge-release-plan-v1` 必须改为校验 Project 028 要求的显式
  发布单元 ownership 与发布依赖。

历史 plan-v3 的成员归属模型提案：zone 的区间声明降级为
**bootstrap 默认值**；正式归属由分类声明（模块 → 包路径的显式
映射）给出，允许非连续。combinatorics 包（词论簇 + Ramsey/vdW +
桥内容）是第一个非连续归属用例；后续实现记录见 §8。该模型不是
现行 `knowledge-release-plan-v1` schema。

## 4. 历史 plan-v3 演化操作

下文涉及 frontier/mathbox 的 `create`、`promote`、`sync` 操作均已
推迟，不具有 Project 028 V1 授权。保留主题的 `split` 与 `rename`
在通过新 release plan 表达时仍然适用。

复现 plan-v3 时，所有操作必须保持 P1–P5、P7 不变量，并在方案工件
中留下可审计记录：

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
  §1.2 案例：同名 section 未必同一知识单元）。公共 ownership
  跟随策展本体；依赖实证约束 proof provider，并可触发归属复核，
  但不得直接决定公共归属。
- 模块名必须是成员的**定义性特征**：能写出一句"凡满足 X 者属之"。
- 反模式（拒收）：非定义性聚合（"misc"、"other"、"additional"）；
  多主题交叉筐（除非有独立 definingness）；容量驱动的语义碎片
  （为凑规模发明不存在的子学科）。
- 名字冲突或含混时，遵循 [术语规范 000](../references/000-terminology.zh.md)
  流程登记裁决。

## 6. 历史 plan-v3 Phases 与验收门

下列阶段与验收门记录 2026-07-19 的 plan-v3 实施计划，仅用于历史
复现。Project 028 G0–G5 是现行 V1 验收门；尤其 Phase 2/3 的
mathbox/frontier、promote 与 membrane 工作已推迟，对 Project 028
V1 不具规范权威。

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

历史 plan-v3 取代过 naming-profile 的 `module_paths`，并把 path
首段视为单一 wrapper 产出物内的领域。Project 028 已取代该映射。

现行 V1 中，一次 release emission 只拥有一个声明的 `python_root`；
所有 `modules[].path` 都位于该根下。plan 分别记录
`release_unit_id`、`python_root` 与 `distribution_name`，transpiler
不再发射覆盖全项目的内容 wrapper。Prelude 作为显式基础设施发布
依赖和 verification lock 解析，不再生成为每个数学发布的子包。
下一版 schema 是 `knowledge-release-plan-v1`（028 §6）。

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
- 2026-07-19（第四轮）：**prelude 边界裁决**，§2.1 悬置问题定案，
  规范细化为 [Project 027：Prelude 边界 RFC](027-prelude-boundary-rfc.zh.md)：
  prelude = 通用理论构造能力（到自然数/有限构造/关系函数/通用
  理论定义机制为止）；迁移单位 = 能力簇；应用场景经 profile
  组装；线性代数入一级标准库、微积分入分析库；对象理论 prelude
  与 Python 书写层分离。能力簇 / 聚合包入 000 §13，前导包词条
  撤销"暂定"改记边界原则。`--prelude-floor` 降级为压测基线工具。
  量化边界待 027 §10 实证（能力簇 × 五指标统计，partition 仓
  下一轮）。
- 2026-07-19（第五轮）：**prelude 边界二次裁决（回退）**。027
  §10 首个试点（自然数能力簇，partition 仓
  `reports/corpus/prelude-naturals-pilot.md`）显示 ω 系闭包达
  2479 节点 / 14.4% 语料，且"prelude 持 ω、数领域持 ℕ"与数学
  传统不完全一致；用户裁决自然数（含 ω）不入 prelude，§2.1
  边界改记为"到集合/类基础、关系与函数为止"。有限序列/fold
  下沉数领域。回退后实证基线 1370 节点 / 18 公理。000 前导包
  词条同步修订（v0.4）。
- 2026-07-19（第六轮）：**prelude 定位收敛（三次裁决）**：维持
  现状极小 pre-logic 状态，暂不扩展；候选边界（集合/类 + 关系
  函数）与实证基线保存于 027，"是否/何时扩展"为 027 §12 首项
  开放问题。program foundation / profile 进入方式同轮保留为
  开放问题。000 前导包词条改记现状定位（v0.5）。
- 2026-07-19（第七轮）：**标准五领域分类方案落地**（partition 仓
  提交 `21432bf`，工件
  `domains/corpus/artifacts/classification-plan-v3.standard.json`），
  供下一阶段编译压力测试。生成机制与裁决全部落进可执行配置
  （`domains/corpus/domain.json` 的 `plan_v3` 块）：
  - **显式 prelude**：`prelude_labels: [wn, wi]`（metamath-prelude
    当前真实产物），取代频率 top-N；215 标签方案降级为历史压测
    基线。频率机制保留为 fallback。
  - **P7 校验器实装**：模块 import 图按 path 首段商化为领域图做
    DAG 检查（模块级无环不蕴含领域级无环），`domain_imports`
    进入 P6 报告。
  - **combinatorics 领域抽取（实证裁决）**：词论 section 230–245、
    容斥 260、van der Waerden 299、Ramsey 300 经 section 级
    非连续归属移入；`sumhash`（被错放进素数计数 section 的纤维
    计数引理，Ramsey 闭包需要）经**label 级 override** 拆出，
    机制在 plan 双侧显式记录（策展模块 `labels` + 来源模块
    `exclude_labels`），校验器保持严格 P1。两个方向实证对比后
    取 **logic → set_theory → numbers → combinatorics →
    number_theory**（符合"数论使用组合工具"的知识传统，代价仅
    sumhash 一个标签移动；备选 nt 先于 comb 零标签移动但方向
    倒置，弃）；binomial
    theorem（259）因 numbers 侧 3 条反向引用留在 numbers，
    necklace-prime section 304 依 §1.2 桥裁决留在 number_theory
    区默认（其对 243 词论机器的依赖即 nt→comb 合法方向边）。
  - **五领域画像**：276 模块，领域间依赖严格 DAG（comb 不依赖
    nt）；logic 49 模块/2738 节点、set_theory 125/8090、numbers
    53/5013、combinatorics 20/529、number_theory 29/835；
    ruff / mypy strict / pytest（34 项）全绿；plan-draft 0.22s、
    plan-validate 0.19s。
  - **发布包映射元数据**：prelude→metamath-prelude、logic→
    metamath-logic、set_theory→metamath-set-theory、numbers→
    metamath-numbers、combinatorics→**metamath-combinatorics
    （待建仓）**、number_theory→metamath-number-theory，写入
    `plan_v3.packages`。
  - 已知遗留：numbers 的 1895 节点 SCC 巨模块（Phase 1 语句级
    重分配首要对象）；definingness 仍为占位文本，draft 标记
    未撤销；策展命名（如 `primes.decimal_certificates`）待
    Phase 1。
- 2026-07-19（第八轮）：**plan-v3 全语料编译压力测试通过**
  （transpiler 提交 `60331e1`，分支 `semantic-api-v2`；partition
  热修 `607e20e` 把凝聚 SCC 模块路径叶截断至 100 字符）。
  - **SCC 巨模块成因定性**：set.mm 语句依赖图本身是 DAG；环出现
    在按 authored section 商化之后——定义、闭包定理、运算与数系
    嵌入在相邻 section 间交错回引，23 个 section（184–194、198–206、
    208–210、212–213，扩展实数、复数初等性质、四则、完备性、
    正整数/归纳、阿基米德性质等）凝聚成
    `numbers.infinity_and_the_extended_real_number_system__scc_23`
    （1895 标签）。这不是证明循环，而是 section 粒度过粗导致的
    知识边界循环；解法是 Phase 1 的语句级 capability-slice 拆分
    （`labels` + `exclude_labels` override），不是移动整个 section。
  - **transpiler 直读 plan-v3**：`--plan` 模式取代连续边界分区，
    支持非连续模块归属、显式 prelude 首模块、精确 ownership 校验
    （17,207 标签不重不漏）与模块路径冲突检查；`--partition`
    兼容模式保留。
  - **表面渲染缺陷修复（首次全语料暴露）**：set.mm 结构变量
    （`.x.`、`.+.` 等带点变量名）无法通过 notation 文本 round-trip
    （tokenizer 拆散点号），触发从未被覆盖的 facade fallback 路径
    且该路径崩溃。修复为渲染显式 `Judgment`/`App`/`Var` 表达式
    （proof `subst` 值同样按 round-trip 检查逐个降级），变量引用
    与生成 `Theory` 铸造规则结构相同。全语料仅 13/16,899 签名
    （0.08%）落入 fallback，全部注册且 elaborate 正确；回归测试
    以 monkeypatch 强制全 fallback 生成并全量 elaborate。
  - **GC 悬崖**：首次全语料尝试 16 分钟未完成生成，`sample` 显示
    ~85% 时间在 `_PyGC_Collect`/`mark_stacks`（约 3 GB 常驻对象图
    被分代 GC 反复全量标记）。数据库扫描后 `gc.freeze()` +
    `gc.disable()` 恢复线性行为。全语料工具链的固定作业要求。
  - **时间开销**（Apple M4，单进程单次）：扫描 1.78s；生成
    277.69s；惰性 import 7.96s；校验 0.03s；基准合计 287.46s。
    另测全量 16,542 证明经活 `Theory` 注册表 elaborate 50.70s
    （import 2.84s）。对照 07-18 四领域链式基线（生成 324.34s +
    急切重放 import 91.01s ≈ 415.36s），单包五领域含全量
    elaboration 约 336.4s（注意：本轮禁用 GC、渲染器已换代，
    非严格同条件）。
  - **SCC 模块负载表现**：1895 标签模块生成 3.84 MB Python 源，
    生成/导入/elaboration 均无异常——当前规模下它是可读性与边界
    卫生问题，不是性能热点。
  - 工件：`transpiler/benchmarks/benchmark_plan_v3.py`、
    `benchmarks/setmm-five-domains-plan-v3-20260719.{json,md}`；
    82 项测试、ruff、mypy strict 全绿。
  - 下一步：Phase 1 语句级拆分 SCC 巨模块与策展命名；
    metamath-combinatorics 建仓；发布包元数据消费端接线。
- 2026-07-20（第九轮）：**发布拓扑由 Project 028 取代**。十六个
  裸数学 Python 根冻结为十六个一一对应的数学发布单元；`numbers`
  改为 `number_systems`；Prelude 成为独立基础设施发布；公共
  ownership 改为本体主导，证明依赖保留为实现约束；mathbox/frontier
  分类移出 V1，等待独立治理裁决。历史 plan-v3 工件与测量继续
  保留，但新的实现工作面向 `knowledge-release-plan-v1`。
