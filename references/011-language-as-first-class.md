# 将语言作为第一类元素

> 状态：规范性设计评注，提议稿。
>
> 范围：ProofScaffold 标准包栈中语言、逻辑、理论、Prelude 与证明基础设施的职责边界。
>
> 本文中的“必须（MUST）”“不得（MUST NOT）”“应当（SHOULD）”“不应当
> （SHOULD NOT）”和“可以（MAY）”具有规范性含义。

---

## 0. 核心裁决

一个形式数学系统必须被理解为以下层次的有序组合，而不是一个只有公理和定理的证明目录：

```text
语言（Language）
  决定哪些表达式有意义

逻辑（Logic）
  在该语言上给出公理和原始推理规则，决定什么叫作推出

具体数学理论（Mathematical Theory）
  扩展或复用底层语言，并加入本领域的非逻辑符号和公理

证明与定理（Proofs and Theorems）
  记录并命名在既定语言和推理关系下得到的结论
```

因此，语言必须是一等的、可命名的、可组合的、可检查的接口元素。一个对外公布
`AXIOMS`、`RULES` 和 `THEOREMS` 的理论，如果没有同时公布这些对象赖以成立的语言契约，
其接口在语义上是不完整的。

标准公共心智模型应当是：

```text
LANGUAGE  决定能说什么
AXIOMS    决定从哪里开始
RULES     决定怎样从已证明判断推出新的判断
THEOREMS  记录已经推出并获得名称的结论
```

---

## 1. “语言”的规范定义

形式语言是一个有限且可检查的表达式构造契约。一个 `LanguageSpec` 至少必须描述：

1. **Sort 或 typecode**：例如 `wff`、set variable、class、term；
2. **变量族**：每个变量属于哪个 sort，以及它是对象变量还是 schema/metavariable；
3. **构造子和符号**：每个构造子的稳定身份、输入 sorts、输出 sort 和 arity；
4. **抽象语法**：合法表达式由哪些构造子递归生成；
5. **绑定行为**：哪些参数位置引入 binder，binder 的作用域覆盖哪些参数；
6. **自由变量与代入语义**：自由出现、捕获规避和 alpha-renaming 的规则；
7. **具体记法**：可接受的 ASCII/Unicode aliases、优先级、结合性和 mixfix 形态；
8. **规范 lowering**：抽象项如何唯一地降为 Metamath token 序列；
9. **形成证明关联**：lowering 所需的 syntax assertion 或形成规则如何取得。

语言契约必须区分下列三个对象：

- `Term` 或 `Expr` 是抽象语法树，是作者操作的语义对象；
- ASCII、Unicode、LaTeX 和字符串是同一语义对象的输入或显示投影；
- `Wff`/token sequence 是面向 Metamath 后端的降低表示。

显示记法不得参与数学身份。`->`、`→` 与 `⇒` 可以解析为同一个构造子，但构造子的稳定身份、
参数和结果 sort 必须参与项的结构相等性。

语言只裁定表达式是否形成良好，不裁定表达式是否为真或可证。例如，若 `Imp` 的签名为
`Wff × Wff → Wff`，则 `Imp(φ, ψ)` 是合法公式；这件事本身既不是逻辑公理，也没有证明它。

---

## 2. 形成规则不是推理规则

Metamath 使用 `$a` 同时编码 syntax assertion 和逻辑公理，因此后端陈述种类不能直接充当
作者层的数学分类。实现必须区分：

### 2.1 语言形成规则

```text
φ : wff, ψ : wff
-----------------  wi
(φ → ψ) : wff
```

它说明如何形成一个合法公式，属于 `LANGUAGE` 的后端实现契约。

### 2.2 逻辑公理

```text
⊢ (φ → (ψ → φ))    ax-1
```

它在既定语言中直接授予一个可证判断，属于 `AXIOMS`。

### 2.3 推理规则

```text
⊢ φ    ⊢ (φ → ψ)
----------------  ax-mp
       ⊢ ψ
```

它消费已证明判断并产生新的已证明判断，属于 `RULES`。

因此，syntax assertion 可以在 `.mm` 中以 `$a` 发射，但在作者 API 中不得因此被误分类为逻辑
`AXIOMS`。同样，`mp` 不得与 `wi`、`wn` 等形成能力共同放入一个含义不明的“syntactic
rules”概念中。

---

## 3. 语言、逻辑与具体数学领域

### 3.1 语言先于逻辑

公理和推理规则都是在某个语言中写出的。若没有语言，就无法判定：

- 公理使用了哪些构造子；
- 推理规则的 premises 和 conclusion 是否类型正确；
- 代入是否跨越 binder 并捕获变量；
- 两个表面字符串是否表示同一个项；
- 一个理论扩展是否改变了旧表达式的意义。

所以逻辑系统必须显式引用一个语言，而不能依靠导入副作用和全局 registry 偶然获得语法。

### 3.2 逻辑定义“推出”

一个逻辑系统是在语言之上选择逻辑公理与原始推理规则。不同逻辑可以：

- 共享同一语言但采用不同公理；
- 共享同一语言和定理，却采用不同 primitive calculus；
- 使用 Hilbert、自然演绎或相继式等不同判断与推演组织；
- 对经典性、直觉主义、相关性或模态性作不同承诺。

所以 `RULES` 不是“整个数学只有一套的规则”，而是当前 calculus 的原始推演接口。派生规则如果
已经由底层系统证明，本质上仍是可复用定理，不应伪装成新的可信原语。

### 3.3 数学领域在逻辑之上形成理论

集合论、数论、代数等理论通常：

1. 继承底层逻辑语言与推理关系；
2. 增加本领域的非逻辑 sorts、函数、关系或 binder；
3. 增加领域公理或定义；
4. 在扩展后的理论中证明定理。

例如，普通一阶逻辑可以有变量、谓词、等号与量词；成员关系 `∈` 是集合论语言的非逻辑关系，
并非一阶逻辑这个概念天然包含的符号。某个兼容 `set.mm` 的包可以出于历史顺序同时提供二者，
但其接口必须标明这是包边界选择，而不是数学分类。

### 3.4 语言扩展不等于逻辑加强

加入一个新符号只扩大“可说的句子”，不自动增加“可证明的句子”。定义性扩展、保守扩展、增加
新公理和更换推理规则必须是可区分的操作：

- 增加记号或定义可能是保守的；
- 增加公理会加强理论；
- 增加 primitive rule 会改变 consequence relation 的可信基础；
- 证明一个派生规则不会扩大原理论的可证集合。

理论接口和接口摘要应当保留这些差异。

---

## 4. 标准包栈的职责

标准栈应当形成以下单向依赖：

```text
ProofScaffold language toolkit
              |
              v
metamath-prelude LANGUAGE
              |
              v
logic.prop LANGUAGE + LOGIC
              |
              v
logic.fol LANGUAGE + LOGIC
              |
              v
set / number-theory / other domain theories
```

### 4.1 ProofScaffold：构造语言的元工具

ProofScaffold 必须提供与具体数学内容无关的机制，例如：

- sort、variable、constructor 和 binder 的声明类型；
- immutable `Term`/`Expr`；
- registry 的显式构造与组合；
- parsing、formatting、matching 和 lowering 的通用算法；
- substitution、free-variable 与 capture 检查；
- `LanguageSpec`、`LanguageInterface` 及其稳定摘要。

ProofScaffold 不得硬编码 `→`、`∀` 或 `∈` 的数学含义。它是制造语言的工具，不是标准数学语言
本身。

### 4.2 metamath-prelude：最小具体语言基础

在标准构建闭包中，`metamath-prelude` 是唯一 Foundation Unit。它应当拥有后续标准包共享的
最小具体语言和 ambient Metamath frame，包括：

- 基础 typecodes，例如 `wff` 和 `|-`；
- 标准 foundation 变量及全局 floating hypotheses；
- 最小公共词汇，例如 `(`、`)`、`-.`、`->`；
- 对应的抽象构造子，例如 `Not`、`Imp`；
- 对应的 syntax assertions，例如 `wn`、`wi`；
- 这些对象组成的公开 `LANGUAGE` 契约。

Prelude 的“基础”是标准对象语言和 foundation scope 的基础，不是通用 DSL 的归宿。通用
`Var`、`Sort`、`Constructor`、parser framework 和 lowering framework 属于 ProofScaffold；
具体的 `Imp`、`Not` 及其规范 token layout 属于 Prelude。

Prelude 不应当拥有仅因当前下游逻辑恰好使用而存在的普通定理，也不应当吸收所有逻辑和数学
领域的符号。其内容变化是 foundation ABI 变化，必须比普通库扩展受到更严格的控制。

### 4.3 metamath-logic：逻辑语言和 consequence relation

`logic.prop` 应当显式扩展 Prelude 语言，增加命题构造子；`logic.fol` 应当显式扩展命题语言，
增加一阶变量、量词、等号、代入与 binder 行为。每层应当公开：

```text
LANGUAGE
AXIOMS
RULES
THEOREMS
```

具体构造函数和 `prove_*` 仍可以是便于直接复用的公共 Python API；四个聚合对象是机器可读的
理论元数据，不能取代这些函数。

### 4.4 领域包：扩展语言并增加非逻辑公理

领域包必须明确声明继承的语言和理论 profile，并只在自身 `LANGUAGE` 中加入本领域词汇。它
可以复用底层 `RULES`，而不必机械复制一份映射；如果更换 calculus，则必须形成不同的逻辑或
theory profile。

---

## 5. 语言组合与身份不变量

**L1. 声明显式。** 每个可构建理论必须显式指定语言；不得仅靠模块导入副作用得到构造子。

**L2. 单一事实源。** 构造子的 sort、arity、binder、aliases、显示和 token layout 必须由同一
声明派生，或由稳定语义身份关联；不得维护数份可独立漂移的 registry。

**L3. 扩展单调。** 普通语言扩展不得改变继承构造子的身份、sort、arity、binder 或 lowering。
改变这些事实必须被视为不兼容的语言 ABI 变化。

**L4. Sort 精确。** 对象变量、class 和 wff 不得仅为降低实现方便而统一伪装成 `Wff`。若后端
桥接暂时需要兼容表示，作者层接口仍必须保留真实 sort。

**L5. Binder 完整。** 含 binder 的语言必须提供自由变量、代入和捕获规避契约。只声明量词的
打印形状不足以构成完整语言定义。

**L6. 表示分离。** 抽象项、显示字符串和 Metamath token sequence 必须是不同阶段的对象。

**L7. 形成与推出分离。** Syntax assertions 属于语言 lowering 契约；逻辑公理属于
`AXIOMS`；primitive inference rules 属于 `RULES`。

**L8. 接口可摘要。** 语言接口摘要必须覆盖公开 sorts、构造子签名、binder 和规范 lowering；
不得覆盖文件布局、Python 私有类名或显示偏好之外的临时实现细节。

**L9. 后端仍为权威。** `LanguageSpec` 是作者层 parsing、typing 与 display 的事实源，但不能绕过
BuilderV2、linker 和最终 Metamath verifier。

**L10. 基础唯一。** 标准构建闭包继续遵守一个 Foundation Unit 的约束；语言组合不得成为隐式
加载第二套 foundation symbols 或 ambient hypotheses 的通道。

---

## 6. 一个最小接口形状

本文不冻结 Python 拼写，但语义上至少需要：

```python
LanguageSpec(
    id=...,
    extends=(...,),
    sorts=(...),
    variables=(...),
    constructors=(...),
    binders=(...),
    lowering=(...),
)

TheorySpec(
    language=...,
    axioms=...,
    rules=...,
    theorems=...,
)
```

`LANGUAGE` 可以先是现有声明的不可变投影，而不必立即引入一个覆盖所有未来场景的大类。首要
目标是建立唯一事实源和清楚边界，而不是增加抽象数量。

---

## 7. 审查问题

任何语言、逻辑或领域包的设计都应回答：

1. 它继承哪一种语言？
2. 它新增哪些 sorts、variables、constructors 或 binders？
3. 新增内容只是记法、定义性扩展，还是带来新公理？
4. 它采用哪套 primitive inference rules？
5. 哪些规则只是已证明的 derived rules？
6. 它如何计算自由变量并执行无捕获代入？
7. 一个作者层项如何确定性降低到 `.mm`？
8. 语言 ABI 改变时，哪些下游接口摘要会失效？

如果一个包无法回答这些问题，它还没有形成完整的理论接口。

---

## 8. 结论

语言不是公理之前的一段实现准备，也不是 parser 的附属配置。它是公理、规则、证明和定理共同
引用的语义空间。把语言提升为第一类元素后，Prelude 才能被准确理解为标准语言基础，逻辑才能
被准确理解为在语言上的 consequence relation，集合论和数论等领域也才能被准确理解为逻辑之上
的词汇与公理扩展。

这一区分同时降低数学心智负担和工程维护成本：作者看到的是语言、假设和推演；后端继续负责
符号身份、lowering、链接与验证，但不再反过来决定作者 API 的分类。
