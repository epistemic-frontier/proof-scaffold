# Project 027：Prelude 边界 RFC（Prelude Boundary RFC）

> 状态：RFC 草案（2026-07-19，依据用户裁决起草）；
> 定性边界已裁决，量化边界待实证（§10）。
>
> 上游：[Project 026 §2.1](026-package-evolution-standard.md)（prelude
> 内容标准立项）、[术语规范 000 §13](../references/000-terminology.zh.md)。
> 交接对象：metamath-prelude 仓（边界执行）、partition 仓（实证统计）。
>
> 本文中的"必须（MUST）""不得（MUST NOT）""应当（SHOULD）"具有规范性含义。

---

## 0. 裁决要点

**应当扩展 metamath-prelude，但不得沿"逻辑—集合—数—线性代数—
微积分"的学科阶梯向上吸收。** Prelude 的边界是**通用理论构造
能力**，不是"常用数学内容"：

- Prelude 到自然数、有限构造、关系函数和通用理论定义机制为止；
- 线性代数进入一级标准库（经 algebra），微积分进入分析库；
- 学习、程序验证等应用场景通过 **profile**（聚合入口）组装，
  不得反向压迫基础层。

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
塞进全局 prelude。

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
| 等价关系与商构造的基础设施 | 可纳入 |
| 有限元组、有限序列、索引族 | 纳入 |
| 自然数、有限性、归纳与有限递归 | 纳入 |
| 通用有限迭代或 fold | 纳入 |
| 不交、限制、局部更新等通用操作 | 纳入 |
| 定义代数结构所需的通用 vocabulary | 纳入，但不纳入完整代数理论 |

关键是**通用有限迭代**而非大量求和/求积定理：求和、矩阵乘法、
程序状态更新都可建立在有限索引族 + fold 之上。

自然数的特殊地位：它既是数学对象，又承担长度、索引、递归深度、
程序步数和有限性证明等**元语言职能**，故有充分理由进入 prelude；
整数与有理数没有同等的基础地位。

### 4.2 留在领域包

| 内容 | 位置 |
| --- | --- |
| 整数、负数运算 | `metamath-discrete` |
| 有理数与精确比例 | `metamath-discrete` 或 `metamath-algebra` |
| 整除、同余、素数、gcd | `metamath-number-theory` |
| 群、环、域、模的完整理论 | `metamath-algebra` |
| 格、偏序、固定点理论 | `metamath-order` |
| 有限图、组合对象 | `metamath-combinatorics` |

## 5. 线性代数与微积分

**线性代数**比微积分更接近基础设施，但仍带入一整套领域结构
（标量域、向量空间/模、线性映射、矩阵表示、基/维数/秩、内积
范数、有限/无限维分岔）。Prelude 应当提供使线性代数包**很薄**
的底层机制（有限索引族、函数、有限 fold、结构定义规范），
不得直接包含向量空间与矩阵理论。位置：
`prelude → algebra → linear-algebra`。

**微积分**更不适合：它不是轻量附加层，会迅速引入实数构造、
序列与极限、完备性、拓扑、连续性、导数积分，乃至度量空间、
测度与选择原则。一旦为"表达学习"纳入线性代数和微积分，很快
还需要概率、测度、优化、凸分析、张量和数值误差——prelude 就
从基础层变成数学课程目录。

学习相关能力组织为 profile：

```text
metamath-learning-profile
├── metamath-linear-algebra
├── metamath-analysis
├── metamath-probability
├── metamath-optimization
└── metamath-finite-computation
```

且存在不需要微积分的轻学习分支（符号学习、有限模型学习、
组合搜索）。

## 6. 形式化软件方法的真实底座

Hoare 逻辑、操作语义、分离逻辑不需要线性代数或微积分。共同
底座：语法树与有限序列；变量、环境和状态；函数、关系与关系
复合；自然数与归纳；偏函数/有限映射；不交并、局部更新；转移
系统与可达关系；（分离逻辑）部分交换幺半群 / separation algebra。

分工：prelude 提供关系、函数、有限序列、自然数、局部更新等
**机制**；`metamath-program-foundation` 定义状态、堆、转移系统
和 separation algebra 等**本体**。依赖仍然浅，且程序逻辑特有
本体不固化进所有数学包。

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
留在领域包。迁移单位是依赖闭包后的能力簇，不是排行榜前 N 个
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

## 9. 初始包结构（目标形态）

```text
metamath-prelude
├── logic-base
├── equality-and-substitution
├── set-and-class-base
├── relation-and-function
├── finite-family-and-sequence
└── nat-and-finite-recursion

metamath-logic          metamath-set          metamath-discrete
metamath-number-theory  metamath-algebra      metamath-linear-algebra
metamath-order          metamath-analysis     metamath-probability
metamath-program-foundation
metamath-hoare-logic    metamath-separation-logic

metamath-program-profile
metamath-learning-profile
```

**profile 只是稳定的聚合依赖，不得拥有底层定义。**既提供
开箱即用体验，又不破坏理论边界。

## 10. 实证计划（裁决量化边界前必须完成）

在 partition 仓的全语料图（及后续扩展语料）上：

1. **能力簇划定**：以 §4.1 表为纲，人工圈定每簇的种子 label
   集，机器计算规则闭包（形成/相等/引入消去/归纳）；
2. **五指标统计**：频率（直接+传递入度）、领域分布熵（跨五区
   归一化熵）、闭包成本（传递前置闭包大小）、公理成本（闭包内
   `ax-inf`/`ax-ac`/`ax-rep` 等出现情况）、接口稳定性（人工
   评级）；
3. 产出**候选簇排序表**，与 §4.1 的定性裁决互证：定性纳入但
   指标弱、或指标强但定性排除的项，逐项上报裁决；
4. 现有 215 标签实证 prelude 与能力簇边界的差集分析（哪些胶水
   引理属于某个能力簇、哪些是纯粹的高频定理应回落领域包）。

## 11. 与现有工作的关系

- **026 §2.1** 的悬置问题由本 RFC 裁决：prelude 角色 = 构造
  工具箱（能力簇粒度），非"构造子 only"亦非"高频基础层"；
  `--prelude-floor` 吸收率定标机制**保留但降级**为压力测试
  基线工具，不再是 prelude 内容的决定机制。
- **026 P7 / 000 §13** 术语直接适用：prelude 是发布包内的特殊
  层；profile 是只含聚合依赖的发布包；`metamath-program-foundation`
  这类中间底座是普通发布包。
- 当前五区 corpus 的 `prelude.core`（215 标签）继续作为压测
  基线使用，直至 §10 实证完成、能力簇 prelude 落地。

## 12. 待裁决

- 等价关系与商构造是否首批纳入（表中"可纳入"）；
- `metamath-discrete` 与 `metamath-algebra` 对有理数的归属；
- 接口稳定性评级的操作化定义；
- profile 的版本策略（锁定成员版本 vs 浮动）；
- **§4.1"自然数"行拆分**（试点实证上报，partition 仓
  `reports/corpus/prelude-naturals-pilot.md`）：ω 系（有限序数
  + 归纳 + `rdg` 有限递归，闭包公理 19 条、无 `ax-inf`、纯
  ch0–1）纳入；算术 ℕ（`df-nn`，闭包含全套 ℂ/ℝ 公理 21 条）
  留 numbers 领域，`om2uz` 桥归 numbers；
- **§4.1"有限序列/索引族"与"fold"行的归属**：set.mm 实践
  基础设施（`seq`/`fz`/`word`）是 ℕ 基（1847/1755/372 个传递
  依赖者），ω 基 `seqom` 仅 95 个——prelude 薄版自建（A）
  vs 下沉 numbers 领域（B）待裁决；
- "定义代数结构 vocabulary"簇（`df-struct` 族）在当前语料
  `[0, cstr)` 之外，实证待语料扩展。

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
