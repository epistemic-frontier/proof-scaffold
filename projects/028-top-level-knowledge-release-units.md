# Project 028：以顶级知识包作为发布单元

> 状态：V1 包根规范性裁决（2026-07-20）。
>
> 裁决：set.mm V1 公共知识表面包含十六个无统一前缀的数学顶级
> Python 包。每个包恰好是一个数学领域的公共根，也是一个数学
> distribution 的发布单元。
>
> 规范依据：[Reference 017](../references/017-ontology-first-knowledge-organization.md)、
> [术语规范 000](../references/000-terminology.zh.md)、
> [Project 025](025-semantic-source-surface.zh.md)、
> [Project 026](026-package-evolution-standard.zh.md) 与
> [Project 027](027-prelude-boundary-rfc.zh.md)。
>
> 明确排除：本文不裁决 mathbox 的组织、所有权、审查、成熟度、
> 晋升与语句归属。Mathbox 不是第十七个数学包。
>
> 本文中的“必须（MUST）”“不得（MUST NOT）”“应当（SHOULD）”
> 具有规范性含义。

---

## 0. 裁决

V1 公共 import root 的封闭清单为：

```text
logic
set_theory
number_systems
order_theory
category_theory
algebra
linear_algebra
topology
geometry
analysis
measure_theory
probability
number_theory
combinatorics
graph_theory
computer_science
```

以上次序只用于展示，不表示依赖顺序。

V1 规定：

1. 每个名字都是无统一内容前缀的顶级 Python import root；
2. 每个根表示一个数学领域；
3. 每个根恰好由一个数学发布包所有；
4. 每个数学发布包恰好拥有一个根；
5. 公共 import 路径中不得出现 `metamath_knowledge` 或其他项目级
   内容总包；
6. 增加、删除或改名顶级根必须经过新的裁决并附带迁移方案。

这是 V1 的封闭清单，并非宣称未来只能存在这些数学学科。

---

## 1. 发布矩阵

此前容易混用的三个名字必须分开：

| 字段 | 示例 | 含义 |
|---|---|---|
| `release_unit_id` | `combinatorics` | 数学发布单元在生态中的稳定标识符 |
| `python_root` | `combinatorics` | 公共的裸顶级 Python import root |
| `distribution_name` | `metamath-combinatorics` | 安装与发布名称 |

V1 有意让 `release_unit_id` 与 `python_root` 文本相同，同时让
distribution 名继续带有独立命名空间。

每行是一个数学发布单元。V1 中以下四个角色构成双射：

```text
顶级数学领域
    ↔ 数学发布单元／发布包（`release_unit_id`）
    ↔ 裸公共 Python 根（`python_root`）
    ↔ 已发布 distribution（`distribution_name`）
```

即使其中两个字段拼写相同，它们标识的仍是不同架构角色。

`release_unit_id == python_root` 的文本相等只是 V1 初始赋值。
未来的 root 改名必须经过显式迁移，不会自动改名稳定的
`release_unit_id`。

| 发布单元 | Python 根 | Distribution | 数学范围的定义标准 |
|---|---|---|---|
| `logic` | `logic` | `metamath-logic` | 命题逻辑、谓词逻辑、等式、替代演算、自然演绎、模态与可证性逻辑、元数学和量子逻辑 |
| `set_theory` | `set_theory` | `metamath-set-theory` | 类、集合、关系、函数、ZF/ZFC/TG、序数、基数、选择、宇宙、集合递归和集合论模型 |
| `number_systems` | `number_systems` | `metamath-number-systems` | 自然数、整数、有理数、实数、复数、扩展实数、超现实数系统及其基本运算 |
| `order_theory` | `order_theory` | `metamath-order-theory` | 预序、偏序、全序、良序、链、格、有向集和闭包系统 |
| `category_theory` | `category_theory` | `metamath-category-theory` | 范畴、函子、自然变换、泛构造和 Kan 扩张 |
| `algebra` | `algebra` | `metamath-algebra` | 原群、幺半群、群、环、域、模、理想、多项式和域扩张 |
| `linear_algebra` | `linear_algebra` | `metamath-linear-algebra` | 向量空间、自由模、线性映射、矩阵、行列式、特征多项式和内积结构 |
| `topology` | `topology` | `metamath-topology` | 一般拓扑、滤子、一致空间、度量空间、紧致性、连通性和代数拓扑 |
| `geometry` | `geometry` | `metamath-geometry` | Tarski、Euclidean、affine、projective、平面与 Hilbert 空间几何 |
| `analysis` | `analysis` | `metamath-analysis` | 极限、连续、微分、级数、实分析、复分析、特殊函数、Fourier 分析和泛函分析 |
| `measure_theory` | `measure_theory` | `metamath-measure-theory` | σ-代数、测度、外测度、可测函数和测度论积分 |
| `probability` | `probability` | `metamath-probability` | 概率空间、随机变量、分布、期望、方差和离散概率 |
| `number_theory` | `number_theory` | `metamath-number-theory` | 整除、同余、素数、丢番图方程、代数数论和解析数论 |
| `combinatorics` | `combinatorics` | `metamath-combinatorics` | 有限计数、词、循环移位、排列、分拆、Ramsey 理论和 Van der Waerden 理论 |
| `graph_theory` | `graph_theory` | `metamath-graph-theory` | 图与超图、子图、游走、路径、圈、连通性、欧拉路和特殊图 |
| `computer_science` | `computer_science` | `metamath-computer-science` | 算法、数字与位表示、递归函数、可计算性和复杂性理论 |

此表冻结的是主要公共所有权标准，并不否认附加的语义 facets。
一个定理可以从多个概念被发现，但只有一个规范发布所有者。

### 1.1 基础设施例外

`metamath-prelude` 是独立的基础设施 release 和 Foundation Unit，
不是第十七个数学根。其符号可以在兼容对象理论表面中隐式可见，
但安装依赖、版本、内容摘要与验证锁定必须保持显式。

不拥有定义的 profile 和实现提供者 release 同样属于基础设施。
它们不得占用十六个根，也不得隐式增加数学根。

---

## 2. 当前 set.mm 的证据

本次裁决采用的语料清单是上游 `metamath/set.mm` 的
`origin/develop` 提交 `4b2cea80`（2026-07-20）：

- 873,122 行源码；
- 3,000 条 `$a` 断言；
- 47,543 条 `$p` 断言；
- 合计 50,543 条形式断言；
- mathbox 区域 17,780 条，约占全语料 35.2%。

物理源码区段是重要证据，但不是包分类：

- `set-num.mm` 混合了数系、有限计数、词、极限、级数和三角学；
- `set-numth.mm` 混合了初等数论、词、项链、Ramsey 理论和
  Van der Waerden 理论；
- `set-numfunc.mm` 混合了分析、数论、概率例子和几何；
- `set-hilsp.mm` 混合了内积/Banach 空间、Hilbert 格和量子逻辑；
- extensible structures 是形式编码机制，不能据此建立名为
  `structures` 的公共杂项包。

因此 transpiler 不得通过改名源码区间来得到这十六个根。语句
所有权必须来自人工审定、允许非连续分布的分类计划。

### 2.1 显式源码范围

每个分类与发布计划必须声明精确源码快照和纳入区域。“完整覆盖”
只表示完整覆盖已声明目标，不得暗中等同于覆盖拼接后的整个 set.mm。

本项目冻结顶级根与发布单元，但尚不裁决 guides、humor、deprecated、
typesetting 或旧 Hilbert-space 区域的发布状态。这些区域在被发布计划
纳入或排除前，必须先有明确的生命周期裁决。

### 2.2 既有作者区段的 bootstrap 映射

下表只生成审查候选。混合区段需要语句级分类，不得作为不可分割的
整块迁移。

| 作者区段 | 候选数学根 |
|---|---|
| `set-pred.mm` | `logic` |
| `set-class.mm` | `set_theory`，残留逻辑接口需审查是否归 `logic` |
| `set-zf.mm` | `set_theory`；有限集、鸽笼原理与 Hall 类内容需审查是否归 `combinatorics` |
| `set-zfc.mm`、`set-tg.mm` | `set_theory` |
| `set-num.mm` | `number_systems`、`combinatorics`、`analysis` |
| `set-numth.mm` | `number_theory`、`combinatorics`、`computer_science` |
| `set-struct.mm` | 内部编码支撑加各主题所有的声明，含 `order_theory` 候选；不设 `structures` 根 |
| `set-cat.mm` | `category_theory` |
| `set-order.mm` | `order_theory` |
| `set-algstr.mm` | `algebra`；线性与赋范结构需审查是否归 `linear_algebra` 或 `analysis` |
| `set-linalg.mm` | `linear_algebra`；一般代数内容留在 `algebra` |
| `set-top.mm` | `topology`；赋范、Hilbert 与线性内容需审查是否归 `analysis` 或 `linear_algebra` |
| `set-numanal.mm` | `analysis`、`measure_theory` |
| `set-numfunc.mm` | `analysis`、`algebra`、`number_theory`、`probability`、`geometry` |
| `set-surreals.mm` | `number_systems` |
| `set-tarskigeom.mm` | `geometry` |
| `set-graphth.mm` | `graph_theory` |
| `set-hilsp.mm` | `linear_algebra`、`analysis`、`logic`，并保留其生命周期状态 |
| `set-guidesetc.mm`、`set-typeset.mm` | 展示或示例元数据，不是数学根 |
| `set-deprec.mm` | 主题所有者加 deprecated 状态；绝不建立 `deprecated` 根 |

`computer_science` 在 `set-numth.mm` 的位序列与算法区域中已有非
mathbox 候选，但首个版本仍可能较小。这些候选仍需逐语句
审查。不得为了让 distribution 非空而向任何根塞入错误分类的材料。

---

## 3. Mathbox 是独立的治理问题

Mathbox 区域至少同时包含四类问题：

1. 数学主题分类；
2. 贡献者与社群所有权；
3. 审查、成熟度与信任状态；
4. 晋升、迁移、档案历史与维护权限。

本项目不裁决其中任何一项。

所有 Project 028 V1 计划都必须满足：

- `mathbox` 是显式排除的源码范围；
- mathbox 语句不得计为未分类失败；
- 贡献者名字不得成为数学 Python 根；
- 不得把 mathbox 自动建模成通用 `frontier` 包；
- 本文不授权把 mathbox 内容自动晋升或分配进十六个发布单元。

未来治理项目可以裁决：经审查的 mathbox 内容如何与十六个根对齐或
晋升，社群命名空间如何与数学所有权共存，以及是否需要其他 release
种类。Reference 016 只是该工作的证据，不是 V1 的规范性 mathbox 政策。

---

## 4. 本体所有权与实现依赖

一个声明的公共发布所有者遵循数学本体：声明陈述什么，主要定义、
刻画、构造或变换哪个概念。

选定的证明实现另行记录：

- 直接断言需求；
- 传递定理闭包；
- 假设与信任闭包；
- 实现局部 import；
- 构建、验证和后端发射顺序。

证明依赖不会转移公共所有权。例如，一个由复分析证明的数论陈述
仍由 `number_theory` 公开所有；它的实现记录对 `analysis` 的需求。

数学发布单元之间的具体实现依赖图必须无环。本体关系和发现 facets
可以重叠、成环。如果按本体归属得到实现商图环，应分离 facade 与
provider、对实现分阶段，或抽取真正的公共接口。不得仅为打破环而
暗中重新分类公共声明。

每个被选中的实现 provider release 和物理 provider shard 都必须进入
完整实现 DAG 与验证锁定。把 provider 称为“基础设施”，不得使其
逃离依赖、无环性、摘要或信任闭包检查。

Project 025 尚未完整表达这种 facade/provider 分离。当前 schema 无法
诚实表达无环实现投影的地方，不得全面铺开非连续分类。

---

## 5. Python 表面与 lazy 加载

常规公共表面是：

```python
from logic.propositional import modus_ponens
from combinatorics.words import cyclic_shift
from number_theory.primes import fermat_little_theorem
```

而不是：

```python
from metamath_knowledge.combinatorics.words import cyclic_shift
```

每个数学 distribution 必须：

- 拥有一个普通顶级 Python 包；
- 暴露稳定、轻量的断言 Handle；
- 不得只为聚合而在顶级 `__init__.py` import 兄弟数学根；
- 在包或叶模块 import 时不得详化证明；
- 仅按需加载实现与验证闭包；
- 随包提供 manifest 与类型信息，使目录查询和 IDE 发现无需 import
  整个语料库。

跨领域搜索属于 catalog/runtime 服务，不得要求或重新制造项目级
内容总包。

---

## 6. Plan 合约

下一版 plan schema 必须显式表达发布所有权。最小记录为：

```json
{
  "schema": "knowledge-release-plan-v1",
  "source": {
    "repository": "https://github.com/metamath/set.mm.git",
    "commit": "4b2cea80cdab6cd1855d7da39d4f6e89ed3fc6f6",
    "scope": {
      "include_manifests": [{"region": "main", "digest": "..."}],
      "exclude_manifests": [
        {"region": "mathbox", "digest": "...", "reason": "governance-deferred"}
      ]
    }
  },
  "release_units": [
    {
      "release_unit_id": "logic",
      "python_root": "logic",
      "distribution_name": "metamath-logic",
      "kind": "mathematical",
      "prelude_lock": "...",
      "modules": []
    }
  ]
}
```

Schema 必须区分：

- 稳定声明/概念标识符；
- 公共根和规范公共所有者；
- 物理模块与 shard；
- 断言接口与证明实现；
- 实现需求与本体关系；
- 数学 release 与基础设施 release，以及基础设施 release 内的
  profile/provider 角色；
- 以快照为锚、经摘要验证、且穷举精确源码或语句边界的
  include/exclude manifests；仅写布尔标志
  `mathbox: excluded` 不足够。

Python 路径是带版本的公共引用，但不是稳定数学标识符。

---

## 7. 名字所有权与冲突安全

V1 使用普通 package，不采用多所有者 PEP 420 拼装。每个根由一个
distribution 排他所有。

构建或安装 release 前，工具必须拒绝：

- 已由其他安装 distribution 所有的根；
- 与 Python 标准库冲突的根；
- manifest 声明了不同根所有者的 distribution；
- 两份 release manifest 声明同一个根。

`numbers` 与 Python 标准库模块冲突，因而禁用，以 `number_systems`
替代。其他标准库名字，包括 `math`、`statistics`、`decimal`、
`fractions`、`operator`、`types`、`typing`、`collections` 和 `graphlib`，
均不得作为数学根。

---

## 8. 规范性不变量

| ID | 不变量 |
|---|---|
| R1 | 数学根封闭清单恰好是 §0 的十六个名字。 |
| R2 | 顶级数学领域、数学发布单元／发布包、公共根与 distribution 名构成四方双射；每个成员在其他三个角色中都恰好有一个对应物。 |
| R3 | 公共 import 从数学根开始；不得生成统一内容总包。 |
| R4 | 每个范围内声明恰好有一个规范公共所有者；语义 facets 可非排他。 |
| R5 | 公共所有权由数学含义人工审定，不从证明依赖或源码区间生成。 |
| R6 | 实现需求完整、显式，并与本体关系分离。 |
| R7 | 验证锁定下的模块、provider/shard 与数学 release 实现依赖图必须完备且无环；本体图不受此限。 |
| R8 | Import 不得详化证明；证明实现与验证闭包按需加载。 |
| R9 | 稳定标识符不从 Python 路径、文件位置或源码次序导出。 |
| R10 | Mathbox 明确位于 V1 目标覆盖之外，不表示成包或分类失败。 |
| R11 | `structures`、`miscellaneous`、贡献者名字、生命周期状态和源码布局名均不是数学根。 |
| R12 | Prelude 和 profile 是显式基础设施 release，不改变十六根清单。 |

---

## 9. 验收门

1. **G0 — 术语：**术语规范 000 与 Projects 026–027 同意一根一发布
   模型及 Prelude 例外。
2. **G1 — Schema：**validator 强制 R1–R12、源码范围、根所有权及
   distribution 名分离。
3. **G2 — 垂直切片：**词、循环移位、项链、素数及其证明依赖可以
   通过 `combinatorics` 与 `number_theory` 编译，不出现统一总包，
   也不 eager 加载证明。
4. **G3 — Release smoke test：**十六个 distribution 均可在隔离环境
   构建安装；每个根解析到声明的所有者，且不与标准库或其他 release
   冲突。
5. **G4 — 语义与后端验证：**所选证明在精确 release/Prelude 锁定下
   详化、确定性发射，并通过独立 Metamath verifier。
6. **G5 — 迁移：**现有带前缀的生成 import 有显式映射、兼容政策和
   诊断；不得引入静默别名。

完整 mathbox 分类不是 Project 028 的验收门。

---

## 10. 与 Projects 026、027 的关系

本项目取代 Project 026 的以下条款：

- 一个发布包可包含多个一级数学领域；
- path 首段表示统一生成总包内的领域；
- P7 只检查单个发布包内部的领域商图；
- mathbox 自动成为 V1 发布计划的机制化 frontier；
- 物理证明位置决定公共语句所有权。

Project 026 在 definingness、稳定迁移、module/import 完备性、确定性
生成及不依赖旧发布拓扑的演化操作方面继续有效。

Project 027 在极小 Prelude 内容边界和 capability-slice 原则方面继续
有效。Project 028 只改变其包装拓扑：Prelude 是独立、显式锁定的
基础设施 release，而不是在每个数学 release 内重新生成的一层。

---

## 11. 延后裁决

下列问题有意不在本文决定：

- mathbox 的社群与知识治理；
- 全语料逐语句分类；
- deprecated、guide、humor、typesetting 与 legacy 区域的发布状态；
- 一个具名 bridge topic 将来是否值得成为新的顶级 release；
- 多基础概念对齐与证明传输；
- 尚未实现的 distribution 的建仓、版本号与发布节奏。

在另行裁决前，算术组合学等 bridge topic 是拥有一个规范根和多个
发现 facets 的子领域，而不是隐含的第十七个根。

---

## 12. 实施顺序

1. 修订术语并标出 Projects 026/027 被取代的发布拓扑。
2. 增加 `knowledge-release-plan-v1` 及根/源码范围 validator。
3. 把现有生成根改成裸 import，并把 `numbers` 改为
   `number_systems`。
4. 验证 combinatorics/number-theory 垂直切片。
5. 增加其余数学 release manifest，并渐进分类选定的非 mathbox
   目标语料。
6. 在稳定标识符之上构建 catalog，不增加内容总包。
7. 只有在独立治理项目获得裁决后才启动 mathbox 工作。
