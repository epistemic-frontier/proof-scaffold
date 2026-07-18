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

判断与演算（Judgment / Calculus）
  决定可以对表达式作出哪些判断，以及判断如何原始地推出判断

逻辑（Logic）
  组合语言、演算和逻辑公理

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
LANGUAGE   决定能说什么
CALCULUS   决定能作出什么判断，以及怎样推出新的判断
AXIOMS     决定哪些判断被逻辑直接接受
THEORY     加入领域语言、定义与非逻辑公理
THEOREMS   记录已经推出并获得名称的结论
```

`|-`、modus ponens 和 generalization 不属于对象表达式语言。前者是 judgment 的一种
Metamath realization，后二者是 calculus 的 primitive inference rules。语言成为第一类元素，
不得被误解为语言对象包揽了整个逻辑系统。

---

## 1. “语言”的规范定义

形式语言是一个有限且可检查的抽象表达式构造契约。一个 `LanguageSpec` 至少必须描述：

1. **Sort**：例如 `wff`、object variable、class、term；
2. **变量种类**：每类变量属于哪个 sort，以及是否可以被 binder 绑定；
3. **构造子和符号**：每个构造子的稳定标识符、输入 sorts、输出 sort 和 arity；
4. **抽象语法**：合法表达式由哪些构造子递归生成；
5. **绑定行为**：哪些参数位置引入 binder，binder 的作用域覆盖哪些参数；
6. **自由变量与代入所需的结构信息**：使捕获规避和 alpha-renaming 可以由结构导出。

`LanguageSpec` 不得包含 Unicode/ASCII 拼写、parser callback、Metamath token layout、
`SymbolId` 或 syntax assertion label。这些内容分别属于 `NotationSpec` 和 backend binding。

语言声明变量的**种类**，不枚举所有实际变量名称。实际变量的标识符属于其声明上下文：

```text
DeclaredVariableId(owner=language_or_theory_id, local_key=...)
SchemaVariableId(owner=assertion_id, local_key=...)
LocalVariableId(owner=proof_id, local_key=...)
```

`φ/ψ/χ` 等偏好名称属于 notation/style；Prelude 中 `ph/ps/ch` 的固定 token pool 属于
Metamath foundation binding。二者都不得进入抽象 Term 的结构内容标识。

语言契约必须区分下列三个对象：

- `Term` 或 `Expr` 是抽象语法树，是作者操作的语义对象；
- ASCII、Unicode、LaTeX 和字符串是同一语义对象的输入或显示视图；
- `Wff`/token sequence 是面向 Metamath 的后端表示。

显示记法不得参与数学内容标识。`->`、`→` 与 `⇒` 可以解析为同一个构造子，但构造子的稳定标识符、
参数和结果 sort 必须参与项的结构相等性。

### 1.1 四个不得混合的契约

```text
LanguageSpec
  sorts + variable kinds + constructors + binders

NotationSpec
  parse/render + aliases + precedence + associativity

MetamathLanguageBinding
  typecodes + owned tokens + token templates + syntax assertions

CalculusSpec
  judgment kinds + primitive inference rules
```

同一个 `LanguageSpec` 可以配有多个 notation 和 backend binding。改变 Unicode 显示不得改变
Term 或语言语义摘要；改变 Metamath token layout 可以改变 backend 摘要而不改变抽象语言；改变
构造子的 sort signature 则必须改变语言语义摘要并使依赖接口失效。

核心声明必须使用有限、代数化的数据结构。任意 Python callback 不得进入声称可序列化、可摘要、
可跨进程复现的接口等级。

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

它说明 Metamath 后端如何证明一个转换得到的 token sequence 形成良好，属于
`MetamathLanguageBinding`，而不是抽象 `LanguageSpec`。

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

一个最小判断接口可以只有 `Provable : Wff -> Judgment`。即使第一版只支持 Hilbert 的
`⊢ φ`，公共 assertion signature 也应以 premises 和 conclusion judgments 表达，而不是把
judgment 隐藏为全局裸 `Wff` 假设。

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
logic.prop LANGUAGE + CALCULUS + LOGIC
              |
              v
logic.fol LANGUAGE + CALCULUS + LOGIC
              |
              v
set / number-theory / other domain theories
```

### 4.1 ProofScaffold：构造语言的元工具

ProofScaffold 必须提供与具体数学内容无关的机制，例如：

- sort、variable、constructor 和 binder 的声明类型；
- 具有结构相等性的 immutable `Term`，其变量和构造子使用稳定标识符；
- registry 的显式构造与组合；
- `NotationSpec` 驱动的 parsing/formatting；
- backend binding 驱动的符号后端转换；
- substitution、free-variable 与 capture 检查；
- `LanguageSpec`、`LanguageInterface`、`CalculusSpec` 及分层稳定摘要。

ProofScaffold 不得硬编码 `→`、`∀` 或 `∈` 的数学含义。它是制造语言的工具，不是标准数学语言
本身。

### 4.2 metamath-prelude：最小具体语言基础

在标准构建闭包中，`metamath-prelude` 是唯一 Foundation Unit。它应当拥有后续标准包共享的
最小具体语言和 ambient Metamath frame，包括：

- 基础语言 sort `wff`，以及 backend 中对应的 typecode；
- 标准 foundation 变量及全局 floating hypotheses；
- 最小公共词汇，例如 `(`、`)`、`-.`、`->`；
- 对应的抽象构造子，例如 `Not`、`Imp`；
- 对应的 syntax assertions，例如 `wn`、`wi`；
- 这些对象组成的公开 `LANGUAGE` 契约。

`|-` 由 foundation frame 发射，但在抽象模型中必须绑定到 calculus 的 `Provable` judgment，
不得声明成对象语言 constructor 或普通 sort。

Prelude 的“基础”是标准对象语言和 foundation scope 的基础，不是通用 DSL 的归宿。通用
`Var`、`Sort`、`Constructor`、parser framework 和后端转换框架属于 ProofScaffold；
具体的 `Imp`、`Not` 属于 Prelude language；其规范 token layout 属于 Prelude 的
`MetamathLanguageBinding`。

Prelude 不应当拥有仅因当前下游逻辑恰好使用而存在的普通定理，也不应当吸收所有逻辑和数学
领域的符号。其内容变化是 foundation ABI 变化，必须比普通库扩展受到更严格的控制。

### 4.3 metamath-logic：逻辑语言和 consequence relation

`logic.prop` 应当显式扩展 Prelude 语言，增加命题构造子；`logic.fol` 应当显式扩展命题语言，
增加一阶变量、量词、等号、代入与 binder 行为。每层应当公开：

```text
LANGUAGE
CALCULUS
AXIOMS
RULES
THEOREMS
```

具体构造函数和 `prove_*` 仍可以是便于直接复用的公共 Python API；四个聚合对象是机器可读的
理论元数据，不能取代这些函数。

### 4.4 领域包：扩展语言并增加非逻辑公理

领域包必须明确声明继承的语言和理论配置，并只在自身 `LANGUAGE` 中加入本领域词汇。它
可以复用底层 `RULES`，而不必机械复制一份映射；如果更换 calculus，则必须形成不同的逻辑或
理论配置。

---

## 5. 语言组合与标识不变量

**L1. 声明显式。** 每个可构建理论必须显式指定语言；不得仅靠模块导入副作用得到构造子。

**L2. 单一语义事实源。** 构造子的 sort、arity 和 binder 必须由 `LanguageSpec` 唯一声明。
Notation 和 backend binding 必须通过稳定 `ConstructorId` 引用它；不得复制 signature 或维护
可独立漂移的 registry。

**L3. 扩展单调。** 普通语言扩展不得改变继承构造子的标识符、sort、arity 或 binder。改变这些
事实必须被视为不兼容的语义 ABI 变化；backend realization 的变化另由 backend 摘要表达。

**L4. Sort 精确。** 对象变量、class 和 wff 不得仅为后端转换方便而统一伪装成 `Wff`。若后端
桥接暂时需要兼容表示，作者层接口仍必须保留真实 sort。

**L5. Binder 完整。** 含 binder 的语言必须提供自由变量、代入和捕获规避契约。只声明量词的
打印形状不足以构成完整语言定义。

**L6. 表示分离。** 抽象项、显示字符串和 Metamath token sequence 必须是不同阶段的对象。

**L7. 形成与推出分离。** Syntax assertions 属于 `MetamathLanguageBinding`；judgment 和
primitive inference rules 属于 `CalculusSpec`；逻辑公理属于 `AXIOMS`。

**L8. 摘要分层。** `semantic_digest` 只覆盖 sorts、variable kinds、constructor signatures 和
binder；`notation_digest` 覆盖记法；`backend_digest` 覆盖 typecodes、token templates、formation
bindings 与 foundation requirement；`calculus_digest` 覆盖 judgments 和 primitive rules。

**L9. 后端仍为权威。** `LanguageSpec` 是抽象 Term typing 的事实源；`NotationSpec` 是
parsing/display 的事实源；二者都不能绕过 BuilderV2、linker 和最终 Metamath verifier。

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
    variable_kinds=(...),
    constructors=(...),
    binders=(...),
)

NotationSpec(language=..., entries=(...))
MetamathLanguageBinding(language=..., typecodes=(...), formations=(...))
CalculusSpec(language=..., judgments=(...), rules=(...))

LogicSpec(language=..., calculus=..., axioms=(...))
TheorySpec(
    base_logic=...,
    language_extension=...,
    definitions=...,
    axioms=...,
    theorems=...,
)
```

只读 legacy 视图可以用于迁移盘点，但在旧全局注册表、last-wins 和 import-order 仍然决定
语义时，不得把它宣称为稳定 `LANGUAGE`。迁移的最终方向必须反转为由声明生成兼容 registry，
而不是长期由 registry 生成第二份语言副本。

---

## 7. 审查问题

任何语言、逻辑或领域包的设计都应回答：

1. 它继承哪一种语言？
2. 它新增哪些 sorts、variables、constructors 或 binders？
3. 新增内容只是记法、定义性扩展，还是带来新公理？
4. 它采用哪套 primitive inference rules？
5. 哪些规则只是已证明的 derived rules？
6. 它如何计算自由变量并执行无捕获代入？
7. 一个作者层项如何确定性转换为 `.mm` 后端表示？
8. 语言 ABI 改变时，哪些下游接口摘要会失效？

如果一个包无法回答这些问题，它还没有形成完整的理论接口。

---

## 8. 结论

语言不是公理之前的一段实现准备，也不是 parser 的附属配置。它是公理、规则、证明和定理共同
引用的语义空间。把语言提升为第一类元素后，Prelude 才能被准确理解为标准语言基础，逻辑才能
被准确理解为在语言上的 consequence relation，集合论和数论等领域也才能被准确理解为逻辑之上
的词汇与公理扩展。

这一区分同时降低数学理解负担和工程维护成本：作者看到的是语言、假设和推演；后端继续负责
符号标识、后端转换、链接与验证，但不再反过来决定作者 API 的分类。
