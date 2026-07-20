# Project 027：Prelude 边界 RFC（Prelude Boundary RFC）

> 状态：RFC 草案（2026-07-19，依据用户裁决起草）；
> prelude 维持极小 pre-logic 现状（三次裁决）；本文提出边界
> 问题、冻结判定框架与否定性裁决，候选边界待未来裁决（§12）。
>
> 发布拓扑更新（[Project 028](028-top-level-knowledge-release-units.zh.md)，
> 2026-07-20）：本 RFC 仍是 Prelude 内容与能力簇原则的权威规范，
> 但此前的包拓扑草图已被取代。`metamath-prelude` 是十六个数学 root
> 之外独立且显式锁定的基础设施 release。Mathbox 的知识、社群与治理
> 组织不在本项目范围内。
>
> 上游：[Project 026 §2.1](026-package-evolution-standard.zh.md)（prelude
> 内容标准立项）、[术语规范 000 §13](../references/000-terminology.zh.md)。
> 交接对象：metamath-prelude 仓（边界执行）、partition 仓（实证统计）。
>
> 本文中的"必须（MUST）""不得（MUST NOT）""应当（SHOULD）"具有规范性含义。

---

## 0. 裁决要点

**当前定位（2026-07-19 三次裁决）：prelude 维持现状的极小
pre-logic 状态，暂不扩展。** 本 RFC 的职能是把边界问题**提出**
并冻结判定框架，供未来裁决：

- **候选边界**（若未来扩展）：到集合/类基础、关系与函数为止
  （等价与商待裁决），贴近 set.mm 原生分层；实证基线 1370
  节点 / 18 公理（试点报告后记）；**是否以及何时扩展保留为
  开放问题**（§12 首项）；
- **否定性裁决保持冻结**：不得沿"逻辑—集合—数—线性代数—
  微积分"的学科阶梯向上吸收；自然数（含 ω 系）、有限性、
  归纳与有限递归不纳入（二次裁决，见 §4.1 后注）；线性代数
  归 `linear_algebra` root（经 `algebra`），微积分归 `analysis` root；
- Prelude 的边界判据是**通用理论构造能力**，不是"常用数学
  内容"；迁移单位是能力簇（§3）；
- 学习、程序验证等应用场景通过 **profile**（聚合入口）组装，
  不得反向压迫基础层；
- Prelude 是基础设施 release，而不是数学包 root。兼容符号可在对象理论
  表面隐式可见，但安装依赖、版本、内容摘要和验证锁必须显式；它不改变
  Project 028 冻结的十六个数学 root；
- 本 RFC 不分类、不发布、不晋升也不治理 mathbox 内容。

## 1. 目标修正："只依赖 prelude"不是好指标

"未来 Hoare 逻辑、分离逻辑只依赖 prelude"听起来干净，但若
prelude 不断膨胀，"只依赖 prelude"只是把复杂依赖隐藏进一个
大包。真正值得追求的指标：

- 传递依赖闭包小；
- 公理承诺明确；
- 验证与加载成本可控；
- 公共接口稳定；
- 不相关领域不被迫引入。

因此允许 `metamath-program-foundation` 这类中间底座，或
`metamath-program-profile` 聚合入口；不必把软件语义所需全部
塞进全局 prelude。Profile 是基础设施 release 的角色，而不是第三种
release kind；program foundation 的具体角色仍开放。两者都不得占用
Project 028 的十六个数学 root，也不得未经新裁决引入另一个数学 root。

## 2. 边界原则：构造工具箱，不是数学目录

> Prelude 提供定义新理论所需的**表示原语、组合机制和有限构造**；
> 不直接承载某个具体数学领域的主要对象与实质性理论。

## 3. 迁移单位：能力簇（capability slice）

对 Metamath 而言单独迁移一个 label 通常没有意义。一个构造至少
需要连同：

- 形成/良构性规则；
- 闭包规则；
- 相等性与替换规则；
- 引入、消去或求值规则；
- 必要的递归或归纳原则。

迁移单位必须是**能力簇**：最小可用的能力闭包。例："函数"不是
只有函数定义，还包括函数值、定义域、值域、限制、复合、像与
逆像，以及相应的相等性规则。

（这一标准**取代** 026 §2.1 最初"只放构造子、不放定理"的表述：
能力簇必然含有规则与原理层面的定理/公理；边界判据是**能力**
而非语句的句法类别。）

## 4. 纳入/排除边界表

### 4.1 适合进入 Prelude

| 能力 | 裁决 |
| --- | --- |
| 命题与一阶逻辑的基础形成和推理 | 纳入 |
| 相等、替换、变量约束与绑定机制 | 纳入 |
| 集合、类、成员关系的基础表达 | 纳入 |
| 有序对、笛卡尔积、关系、函数 | 纳入 |
| 函数复合、限制、像与逆像 | 纳入 |
| 等价关系与商构造的基础设施 | 可纳入（待裁决） |
| 不交、限制、局部更新等通用操作 | 纳入 |
| 定义代数结构所需的通用 vocabulary | 待实证（语料外，且 set.mm 结构槽为 ℕ 索引，见 §12） |

**后注（2026-07-19 二次裁决）**：初稿曾把"有限元组/序列/索引
族""自然数、有限性、归纳与有限递归""通用有限迭代 fold"三行
列为纳入，理由是自然数的元语言职能（长度、索引、递归深度、
有限性证明）。试点实证（partition 仓
`reports/corpus/prelude-naturals-pilot.md`）后用户裁决**回退**：

- ω 系虽技术上安全（闭包 19 公理、无 `ax-inf`），但 2479 节点
  / 14.4% 语料属过多进入；
- prelude 持 ω、`number_systems` root 持 ℕ 的"两个自然数"与数学传统
  不完全一致；
- set.mm 的实践基础设施（`seq`/`fz`/`word`）本就是 ℕ 基，
  ω 基 `seqom` 仅 95 个传递依赖者，薄版自建无语料可压测。

故三行全部移出 Prelude：ω、有限性、归纳、有限递归归
**`set_theory` root**。历史上的“B 路线”裁决冻结的是
“不进 Prelude”，而不是 Project 028 下由证明依赖决定的公共
ownership。有限序列与词的概念由 `combinatorics` 公开所有；
数值索引的 provider 实现可依赖 `number_systems`。`seq`/`fz`/`word`
的精确 label 分配仍需逐语句审查。求和、矩阵乘法与程序状态更新
经显式数学 release 依赖获得这些 provider，不经 Prelude。

### 4.2 留在数学 root

| 内容 | 位置 |
| --- | --- |
| ω、有限性、归纳、有限递归（`rdg`/`seqom`） | `set_theory` |
| 有限序列与词；索引族/fold 机制（`seq`/`fz`/`word`） | 公共主题归 `combinatorics`；数值 provider 可依赖 `number_systems`；精确 label 归属待审 |
| 自然数 ℕ 与算术（`df-nn`，含 `om2uz` 桥） | `number_systems` |
| 整数、负数运算 | `number_systems` |
| 有理数与精确比例 | `number_systems` 或 `algebra`（归属待裁决） |
| 整除、同余、素数、gcd | `number_theory` |
| 群、环、域、模的完整理论 | `algebra` |
| 格、偏序、固定点理论 | `order_theory` |
| 有限计数与组合对象 | `combinatorics` |
| 有限图与超图 | `graph_theory` |

## 5. 线性代数与微积分

**线性代数**比微积分更接近基础设施，但仍带入一整套领域结构
（标量域、向量空间/模、线性映射、矩阵表示、基/维数/秩、内积
范数、有限/无限维分岔）。使线性代数包**很薄**的机制分属多个
角色：Prelude 出函数与关系基础，`set_theory` 出集合层基础，
`number_systems` 出数值索引 provider，`combinatorics` 拥有有限序列/
fold facade。Prelude 不得直接包含向量空间与矩阵理论。一个示意
provider 次序是 `metamath-prelude → metamath-set-theory /
metamath-number-systems → metamath-combinatorics / metamath-algebra →
metamath-linear-algebra`；精确 release DAG 由所选快照验证，不由本 RFC
写死。

**微积分**更不适合：它不是轻量附加层，会迅速引入实数构造、
序列与极限、完备性、拓扑、连续性、导数积分，乃至度量空间、
测度与选择原则。一旦为"表达学习"纳入线性代数和微积分，很快
还需要概率、测度、优化、凸分析、张量和数值误差——prelude 就
从基础层变成数学课程目录。

学习相关能力组织为 profile：

```text
metamath-learning-profile                 （基础设施 profile；无数学 root）
├── metamath-linear-algebra              → linear_algebra
├── metamath-analysis                    → analysis
├── metamath-probability                 → probability
└── 可选基础设施 provider/view           （基础设施角色；无数学 root）
```

优化与有限计算 view 可由未来的基础设施 provider 提供，但本示例不授权
`optimization` 或 `finite_computation` 成为额外数学 root。

且存在不需要微积分的轻学习分支（符号学习、有限模型学习、
组合搜索）。

## 6. 形式化软件方法的真实底座

Hoare 逻辑、操作语义、分离逻辑不需要线性代数或微积分。共同
底座：语法树与有限序列；变量、环境和状态；函数、关系与关系
复合；自然数与归纳；偏函数/有限映射；不交并、局部更新；转移
系统与可达关系；（分离逻辑）部分交换幺半群 / separation algebra。

分工：prelude 提供关系、函数、局部更新等**机制**；有限序列
主题来自 `combinatorics`，自然数、数值 provider 与归纳来自
`set_theory` 与 `number_systems`（显式 release 依赖，见 §1——
"只依赖 prelude"本就不是目标）；`metamath-program-foundation` 定义状态、
堆、转移系统和 separation algebra 等**本体**。依赖仍然浅，且
程序逻辑特有本体不固化进所有数学包。

**注意**：本节只界定"程序方法需要什么、不需要什么"；
program foundation 与 program profile **如何进入**发布生态
（program foundation 的 release 角色及其与 `set_theory`、`number_systems`、
`combinatorics`
的依赖形态，以及基础设施 profile 的成员和版本策略）保留为开放问题
（§12），不随本 RFC 定案。未来无论如何裁决，这些 release 都不得占用
或修改 Project 028 的十六个数学 root。

## 7. 候选生成与选择指标

set.mm 依赖频率**只能作候选生成机制，不得直接决定 prelude**。
高频有三种成因：

1. 真正的跨领域基础性；
2. set.mm 当前编码风格造成的枢纽；
3. 大统一结构承载许多小结构，频率被人为抬高（数系、类表达、
   统一算术结构尤其如此）。

每个候选能力簇必须计算五个指标：

| 指标 | 含义 | 方向 |
| --- | --- | --- |
| 使用频率 | 被多少证明直接/间接使用 | + |
| 领域分布熵 | 使用是否分散于多领域 | + |
| 闭包成本 | 迁入需连带迁入的前置规模 | − |
| 公理成本 | 是否引入无穷/选择/完备性等承诺 | − |
| 接口稳定性 | 未来出现更好表达方式的可能 | −（波动性） |

选择目标（示意）：

```text
PreludeValue = (frequency × cross-domain-breadth × reconstruction-cost)
             / (closure-size × axiom-cost × API-volatility)
```

**高频且领域分布广**才是强候选；高频但集中于单一领域的构造
留在其所属数学 root。迁移单位是依赖闭包后的能力簇，不是排行榜前 N 个
label（026 §2.1 的吸收率定标 prelude 由此正式降级为压力测试
基线，见 §11）。

## 8. 双层 prelude：语义基础与书写经济分离

ProofScaffold 有 Python 宿主语言，必须区分：

1. **对象理论 prelude**：本 RFC 的规范对象；
2. **Python API / elaboration 层 prelude**：书写便利设施。

矩阵字面量、张量索引语法、有界求和、record/structure 定义、
程序状态更新语法、有限列表与映射的便捷构造——这些由 Python 层
展开为较小的对象理论原语，不得通过扩充对象理论实现。

> Prelude 负责语义基础；Python 层负责书写经济性。

这显著减轻把线性代数、程序数据结构乃至机器学习符号塞进
Metamath prelude 的压力。

两层都不是第十七个数学 root。`metamath-prelude` 作为独立基础设施
release 安装和版本化；即使兼容的 Prelude 符号在对象理论内隐式可见，
其版本、内容摘要与验证环境仍必须显式锁定。

## 9. Project 028 下的发布拓扑

[Project 028](028-top-level-knowledge-release-units.zh.md) 取代本节此前的包结构草图。
生效的 V1 拓扑是：

```text
基础设施 release
└── metamath-prelude    （无数学 Python root；显式安装并锁定）

数学 release root
├── logic               ├── set_theory          ├── number_systems
├── order_theory        ├── category_theory     ├── algebra
├── linear_algebra      ├── topology            ├── geometry
├── analysis            ├── measure_theory      ├── probability
├── number_theory       ├── combinatorics       ├── graph_theory
└── computer_science

其他基础设施 release 角色
├── aggregation profile         （如 metamath-program-profile）
└── implementation provider
    （均为基础设施 release 的角色/子型，不拥有或增加数学 root）
```

每个数学 root 恰由一个数学 release 拥有，每个数学 release 恰拥有一个
root；不存在 `metamath_knowledge` 包裹层。distribution 名仍按 Project 028
另行保留命名空间。

**profile 只含稳定的聚合依赖，不得拥有底层定义或数学 root。**既提供
开箱即用体验，又不破坏理论边界。

程序方法一支（`program-foundation` / `hoare-logic` /
`separation-logic` / `program-profile`）的进入方式是开放问题（§12），
但不得改变冻结的十六 root allowlist，也不得隐式引入新 root。

Mathbox 组织不属于此拓扑。本 RFC 不分类、不发布、不晋升、不治理
mathbox 语句，也不把 mathbox 建模成通用 frontier 包。

## 10. 实证计划（裁决量化边界前必须完成）

在 partition 仓精确声明的非 mathbox 目标图（及后续显式定界的非
mathbox 扩展语料）上：

1. **能力簇划定**：以 §4.1 表为纲，人工圈定每簇的种子 label
   集，机器计算规则闭包（形成/相等/引入消去/归纳）；
2. **五指标统计**：频率（直接+传递入度）、领域分布熵（跨纳入的
   数学 root 计算归一化熵；历史试点使用五区）、闭包成本（传递前置闭包大小）、公理成本（闭包内
   `ax-inf`/`ax-ac`/`ax-rep` 等出现情况）、接口稳定性（人工
   评级）；
3. 产出**候选簇排序表**，与 §4.1 的定性裁决互证：定性纳入但
   指标弱、或指标强但定性排除的项，逐项上报裁决；
4. 现有 215 标签实证 prelude 与能力簇边界的差集分析（哪些胶水
   引理属于某个能力簇、哪些是纯粹的高频定理应回落所属数学 root）。

## 11. 与现有工作的关系

- **026 §2.1** 的悬置问题由本 RFC 裁决：prelude 角色 = 构造
  工具箱（能力簇粒度），非"构造子 only"亦非"高频基础层"；
  `--prelude-floor` 吸收率定标机制**保留但降级**为压力测试
  基线工具，不再是 prelude 内容的决定机制。
- [Project 028](028-top-level-knowledge-release-units.zh.md) 取代旧发布拓扑：
  Prelude 是十六个数学 root 之外独立的基础设施 release 与 Foundation Unit。
  对象理论符号只有在安装依赖、版本、内容摘要和验证锁均显式的前提下才可隐式可见。
- Profile 是只含聚合依赖、无定义的基础设施 release 角色。Program foundation
  与 profile 不得占用或修改十六个数学 root；program foundation 的 release
  角色以及 profile 的成员/版本策略仍留在 §12。
- 当前五区 corpus 的 `prelude.core`（215 标签）继续作为压测
  基线使用，直至 §10 实证完成、能力簇 prelude 落地。
- Mathbox 不在本 RFC 的语料范围和治理权限内；它既不是 Prelude 候选池，
  也不是自动 frontier。

## 12. 待裁决

- **prelude 是否以及何时从极小 pre-logic 扩展到候选边界**
  （集合/类基础 + 关系与函数，§0）——三次裁决维持现状，
  扩展需新的裁决触发；§4.1 表在此之前是候选清单而非生效边界；
- 等价关系与商构造是否首批纳入（表中"可纳入"）；
- `number_systems` 与 `algebra` 对有理数的归属；
- 接口稳定性评级的操作化定义；
- profile 的版本策略（锁定成员版本 vs 浮动）；
- "定义代数结构 vocabulary"簇（`df-struct` 族）在当前语料
  `[0, cstr)` 之外，实证待语料扩展；注意 set.mm 的可扩展结构
  以 ℕ 为槽索引（`df-ndx`/`df-slot`），该簇很可能同样依赖
  `number_systems` 而无法入 prelude，届时需连同结构定义机制的
  替代方案一并裁决；
- `df-map`（函数空间）是否随关系函数簇纳入：纳入则公理承诺
  +`ax-un`/`ax-pow`（闭包 1370→1632 节点、18→20 公理，见
  试点报告后记）；
- **program foundation / program profile 的进入方式**（用户指定保留为
  开放问题）：program foundation 的 release 角色及其对 `set_theory`、
  `number_systems`、`combinatorics` 的依赖形态，以及基础设施 profile
  `metamath-program-profile` 聚合哪些成员与采用何种版本策略。Profile
  始终是基础设施 release 的角色/子型，而不是第三种 release kind。两者
  都不得成为十六个数学 root 内的领域、占用或修改这些 root；§6/§9 中的
  相关条目仅为示意草图，不构成裁决。

Mathbox 的知识、社群与治理组织明确不是 Prelude 边界的待裁决问题，
不由本项目处理。

已裁决（2026-07-19 二次裁决，原§12 两项）：**自然数不入
prelude**——ω 系与算术 ℕ 均下沉（§4.1 后注）；有限序列/fold
走 B 路线（保持在 Prelude 之外；Project 028 将 `combinatorics` 的公共
ownership 与基于 `number_systems` 的数值 provider 分开；不做 ω 基薄版
自建）。

## 13. 实施进展

- 2026-07-19：RFC 依据用户裁决起草；定性边界（§0–§9）定案，
  实证计划（§10）排入 partition 仓下一轮。
- 2026-07-19：§10 首个试点完成（自然数能力簇，partition 仓
  `reports/corpus/prelude-naturals-pilot.md`）。回答用户裁决
  问题"能否安全把自然数放入 prelude 且编译结果与 set.mm 开头
  吻合"：**ω 系可以**（19 公理、无 `ax-inf`、发射为 set.mm
  开头的保序子序列，前缀密度 32.6%——吻合只在子序列意义下
  成立，与"mm 是 DAG 的线索化"判断一致）；**算术 ℕ 不可以**
  （闭包拖入全套 ℂ 公理化与 ch4 素材）。副产物：215 标签频率
  prelude 泄漏 28 个 ch4–5 标签（`cc`/`cr`/`cn`/`ax-1cn`…），
  公理成本指标一票否决频率定标，验证 §7 成因 2/3 预言。
  新增三项待裁决（§12）。
- 2026-07-19：**二次裁决（边界回退）**。鉴于 ω 系闭包 2479
  节点 / 14.4% 属过多进入，且"两个自然数"格局与数学传统不
  完全一致，用户裁决自然数（含 ω）不入 prelude，边界回退至
  集合/类基础 + 关系与函数，贴近 set.mm 原生分层；有限序列/
  fold 走 B 路线下沉。修订 §0/§4/§5/§6/§9/§12。回退后 prelude
  实证基线：1370 节点（8.0%）、18 公理（无 `ax-un`/`ax-pow`/
  `ax-inf`）；含 `df-map` 变体 1632 节点、20 公理（数据见
  partition 仓试点报告后记）。
- 2026-07-19：program foundation / program profile 的进入方式
  经用户指定**保留为开放问题**（§12）；§6/§9 相关条目降为
  示意草图。
- 2026-07-19：**三次裁决（定位收敛）**。prelude 维持现状极小
  pre-logic 状态，暂不扩展；"是否/何时扩展到候选边界（集合/
  类 + 关系函数）"升为 §12 首项开放问题。本 RFC 的定位由
  "边界定案"转为"提出问题 + 冻结判定框架 + 保存实证基线"；
  否定性裁决（学科阶梯禁令、自然数不入、频率否决、能力簇
  单位、profile 机制）保持冻结。
- 2026-07-20：[Project 028](028-top-level-knowledge-release-units.zh.md)
  取代本 RFC 的包拓扑草图，但不改变 Prelude 内容边界。Prelude 改为
  冻结十六个数学 root 之外独立且显式锁定的基础设施 release；示例映射到
  新 root，program release 被禁止改变 allowlist，并明确 mathbox 不在本项目范围内。
