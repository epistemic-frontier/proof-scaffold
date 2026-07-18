# Reference 012：结构、公理与证明的语义化定义规范

> 状态：`api-proposal-0.1` 作者规范，2026-07-17。
>
> 本文中的“必须（MUST）”“不得（MUST NOT）”“应当（SHOULD）”和“可以（MAY）”具有规范性含义。

本文是 [Reference 011：将语言作为第一类元素](011-language-as-first-class.md) 的作者实践规范，
并以 [Project 024：First-Class Language Refactor](../projects/024-first-class-language-refactor.md)
当前已经实现的 semantic authoring API 为基准。代码片段为聚焦语义边界而省略了部分 imports。

## 0. 目的与总原则

本文回答包作者的三个问题：

1. 如何定义数学结构，即语言中的 sort、变量种类、constructor 与 binder；
2. 如何在该语言与 calculus 上给出公理或定义；
3. 如何只通过已登记 assertion 的应用给出证明。

核心纪律是：**数学对象先以 backend-neutral 的语义对象存在，再绑定到 Metamath。** Python
函数名、Unicode 字符、set.mm token、Metamath label 和运行时 `SymbolId` 都不是数学身份。

```text
LanguageSpec
  sorts + variable kinds + constructors + binders
            │
            ├── NotationSpec
            │     parse + render + aliases + precedence
            │
            └── MetamathLanguageBinding
                  typecodes + token templates + formation assertions

CalculusSpec
  judgment kinds + primitive inference rules
            │
            ├── AxiomDecl / DefinitionDecl
            │
            └── AssertionSignature + ElaboratedProof
```

一条公式是 `Term`；“该公式可证”是 `Judgment(PROVABLE, (term,))`。两者不得混淆。

---

## 1. 定义结构：先定义能写什么

### 1.1 使用稳定身份

每个 sort、variable kind 和 constructor 必须有稳定的 nominal ID：

```python
from skfd.authoring.ids import ConstructorId, LanguageId, SortId, VariableKindId

FOL_LANGUAGE_ID = LanguageId("example/fol#language:first-order")
SETVAR = SortId("example/fol#sort:setvar")
SETVAR_VARIABLE = VariableKindId("example/fol#variable-kind:setvar")

ALL = ConstructorId("example/fol#constructor:all")
EQ = ConstructorId("example/fol#constructor:equality")
```

ID 表示身份；`∀`、`A.`、`All` 只是不同层面的拼写。改变显示字符不得改变 `ALL`。

推荐的 ID 形式是：

```text
<package>/<domain>#sort:<name>
<package>/<domain>#variable-kind:<name>
<package>/<domain>#constructor:<name>
<package>/<domain>#axiom:<label>
<package>/<domain>#definition:<label>
<package>/<domain>#proof:<label>
```

### 1.2 声明 sort、变量种类、constructor 与 binder

```python
from skfd.authoring.language import (
    BinderDecl,
    ConstructorDecl,
    LanguageSpec,
    SortDecl,
    VariableKindDecl,
)

LANGUAGE_SPEC = LanguageSpec(
    id=FOL_LANGUAGE_ID,
    sorts=(SortDecl(id=SETVAR),),
    variable_kinds=(
        VariableKindDecl(id=SETVAR_VARIABLE, sort=SETVAR),
    ),
    constructors=(
        ConstructorDecl(id=ALL, inputs=(SETVAR, WFF), output=WFF),
        ConstructorDecl(id=EQ, inputs=(SETVAR, SETVAR), output=WFF),
    ),
    binders=(
        BinderDecl(
            constructor=ALL,
            variable_argument=0,
            scoped_arguments=(1,),
        ),
    ),
)
```

`ConstructorDecl` 只回答输入、输出与 binding behavior。它不得包含 Unicode、token layout、
Metamath label 或任意 Python callback。

`And : Wff × Wff → Wff` 属于语言；`df-an` 属于定义。新增 constructor 只扩大“能说什么”，
加入定义或公理才改变“能推出什么”。

### 1.3 显式解析语言扩展

```python
LANGUAGE_SPEC = LanguageSpec(
    id=FOL_LANGUAGE_ID,
    extends=(
        LanguageRequirement(
            id=PROP_LANGUAGE.id,
            semantic_digest=PROP_LANGUAGE.semantic_digest,
        ),
    ),
    # 本层新增声明……
)

LANGUAGE = resolve_language(
    LANGUAGE_SPEC,
    {PROP_LANGUAGE.id: PROP_LANGUAGE},
)
```

依赖 digest 必须参与解析。import 顺序不得决定语言内容；重复 ID 只有在声明完全相同时才可合并。

### 1.4 提供直接、typed 的构造函数

普通数学代码不应通过字符串 map 组装公式。包应提供薄的 callable facade：

```python
def SetVar(variable: VariableRef) -> Var:
    if variable.kind != SETVAR_VARIABLE:
        raise AuthoringSemanticError("expected a set variable")
    return LANGUAGE.variable(variable)


def All(variable: Term, body: Term) -> App:
    return LANGUAGE.apply(ALL, (variable, body))


def Eq(left: Term, right: Term) -> App:
    return LANGUAGE.apply(EQ, (left, right))
```

这些函数不得自己拼 token，也不得修改全局 registry。sort、arity 与 binder 检查必须由
`LanguageInterface.apply()` 完成。

### 1.5 分离 notation 与 backend binding

```python
NOTATION_SPEC = NotationSpec(
    id=NotationId("example/fol#notation:unicode"),
    language=LanguageRequirement(
        id=LANGUAGE.id,
        semantic_digest=LANGUAGE.semantic_digest,
    ),
    declarations=(
        NotationDecl(
            constructor=ALL,
            form=BinderForm(token="∀", precedence=0),
            aliases=("forall",),
        ),
        NotationDecl(
            constructor=EQ,
            form=InfixForm(token="=", precedence=30, associativity="left"),
        ),
    ),
)
```

accepted aliases、canonical rendering 与 backend token 是三项不同政策。接受 `forall` 不表示
formatter 或 Metamath backend 应输出 `forall`。

Metamath realization 由单独的 binding 给出：

```python
SETMM_BINDING_SPEC = MetamathLanguageBinding(
    id=BackendBindingId("example/fol#binding:setmm"),
    language=LanguageRequirement(
        id=LANGUAGE.id,
        semantic_digest=LANGUAGE.semantic_digest,
    ),
    foundation=FOUNDATION,
    formations=(
        FormationBinding(
            constructor=ALL,
            syntax_assertion=AssertionSemanticId("example/fol#formation:wal"),
            syntax_assertion_label="wal",
            template=(
                LiteralPart(SETMM_FORALL_TOKEN),
                ArgumentPart(0),
                ArgumentPart(1),
            ),
        ),
        FormationBinding(
            constructor=EQ,
            syntax_assertion=AssertionSemanticId("example/fol#formation:weq"),
            syntax_assertion_label="weq",
            template=(
                ArgumentPart(0),
                LiteralPart(SETMM_EQ_TOKEN),
                ArgumentPart(1),
            ),
        ),
    ),
)
```

`wal`、`weq` 是 formation assertions，不是推理规则。`ax-gen` 才是 calculus 的 primitive
inference rule。

无表面 token 的 coercion 可以只保留参数：

```python
FormationBinding(
    constructor=CV,
    syntax_assertion=AssertionSemanticId("example/fol#formation:cv"),
    syntax_assertion_label="cv",
    template=(ArgumentPart(0),),
)
```

于是 semantic Term 可以显式写 `Elem(Cv(x), Cv(y))`，backend 仍输出 `x e. y`。

---

## 2. 给出公理：声明一个无前提 judgment

### 2.1 schema variable 必须归属于 assertion

```python
AX5_ID = AssertionSemanticId("example/fol#axiom:ax-5")
AX5_OWNER = OwnerId(str(AX5_ID))

PHI_REF = VariableRef("schema", AX5_OWNER, "phi", WFF_VARIABLE)
X_REF = VariableRef("schema", AX5_OWNER, "x", SETVAR_VARIABLE)

phi = LANGUAGE.variable(PHI_REF)
x = SetVar(X_REF)
```

变量显示名不是身份。不同 assertion 不得因为都使用字符串 `"phi"` 而共享变量身份。

### 2.2 先构造 Term，再包装为 Judgment

```python
formula = Imp(phi, All(x, phi))

AX5 = resolve_axiom(
    AxiomDecl(
        id=AX5_ID,
        schema_variables=(PHI_REF, X_REF),
        conclusion=Judgment(PROVABLE, (formula,)),
        mandatory_distinct=(DistinctPair(PHI_REF, X_REF),),
    ),
    CALCULUS,
)
```

分层含义是：

```text
Imp(phi, All(x, phi))       一条 Wff Term
Judgment(PROVABLE, (...,))  “该 Wff 可证”
AxiomDecl                   一个没有 premises 的 primitive assertion
```

`resolve_axiom` 必须校验 schema variables、sort、judgment kind、constructor tree 和 mandatory
DV endpoints，并产生确定性的 digest。

### 2.3 `$d` 的 assertion 契约与 source scope

`mandatory_distinct` 是 assertion 的公开应用契约；作者源中的 `$d` 是词法作用域声明。两者应通过
SourceBlock elaboration 连接：

```python
signature = signature_from_axiom(AX5, canonical_label="ax-5")

source = SourceBuilder()
with source.block() as block:
    block.d(PHI_REF, X_REF)
    block.assertion(replace(signature, mandatory_distinct=()))

snapshot = elaborate_block(source.build()).assertions[0]
assert snapshot.declaration == signature
```

Source grouping 与 semantic pair relation 必须分离。多个 `$d` statement 只要展开成同一规范化 pair
relation，就具有同一 assertion/proof semantic identity。

### 2.4 定义不得伪装成 theorem

定义与公理具有相同的无前提 judgment 外形，但语义类别不同：

```python
DF_AN = resolve_definition(
    DefinitionDecl(
        id=AssertionSemanticId("example/prop#definition:df-an"),
        schema_variables=(PHI_REF, PSI_REF),
        conclusion=Judgment(
            PROVABLE,
            (Iff(And(phi, psi), Not(Imp(phi, Not(psi)))),),
        ),
    ),
    CALCULUS,
)

DF_AN_SIGNATURE = signature_from_definition(DF_AN, canonical_label="df-an")
assert DF_AN_SIGNATURE.kind == "definition"
```

constructor、definition、axiom 与 theorem 必须保持四种不同身份。后端都使用 `$a` 并不能成为在
author API 中合并它们的理由。

### 2.5 公开 metadata，隔离 legacy adapter

公开 `AXIOMS` 应保存 semantic interfaces：

```python
AXIOMS: Mapping[str, AxiomInterface | DefinitionInterface] = MappingProxyType(
    {"ax-1": AX1, "df-an": DF_AN}
)
```

迁移期可以由 semantic Term 派生 `LEGACY_AXIOMS`，供旧 `System.compile_axioms()` 使用；不得反过来
从 legacy `Expr` 生成公共 semantic contract，也不得长期手写两份公式。

---

## 3. 给出证明：声明目标，然后应用 assertion

### 3.1 theorem signature 必须先于 proof body

```python
MP2B_SIGNATURE = AssertionSignature(
    id=AssertionSemanticId("example/prop#assertion:mp2b"),
    canonical_label="mp2b",
    kind="theorem",
    schema_variables=(PHI_REF, PSI_REF, CHI_REF),
    premises=(
        Judgment(PROVABLE, (phi,)),
        Judgment(PROVABLE, (Imp(phi, psi),)),
        Judgment(PROVABLE, (Imp(psi, chi),)),
    ),
    conclusion=Judgment(PROVABLE, (chi,)),
)
```

signature 是 theorem 的公开契约；proof body 是该契约的一份实现。更换 proof body 不应改变
signature identity。

### 3.2 所有可引用 assertion 必须进入 catalog/profile

```python
MP_ASSERTION = signature_from_primitive_rule(
    MP,
    assertion_id=AssertionSemanticId("example/prop#assertion:ax-mp"),
    canonical_label="ax-mp",
)

ASSERTION_CATALOG = resolve_assertion_catalog(
    AssertionCatalogSpec(
        id=AssertionCatalogId("example/prop#catalog:semantic"),
        assertions=(MP_ASSERTION,),
        profiles=(
            AssertionProfileSpec(
                id=PROP_CORE_PROFILE,
                allowed=(MP_ASSERTION.id,),
            ),
        ),
    )
)
```

profile 明确规定当前证明允许使用哪些公理、定义、primitive rules 和既有定理。证明不得通过未登记
的 Python callable 绕过 catalog。

### 3.3 证明体只写数学动作

```python
def author_mp2b() -> ElaboratedProof:
    proof = ProofAuthor(
        MP2B_SIGNATURE,
        proof_id=ProofId("example/prop#proof:mp2b"),
        calculus=CALCULUS,
        catalog=ASSERTION_CATALOG,
        profile=PROP_CORE_PROFILE,
    )

    h_phi, h_phi_psi, h_psi_chi = proof.hypotheses
    psi = proof.use(MP_ASSERTION, h_phi, h_phi_psi)
    chi = proof.use(MP_ASSERTION, psi, h_psi_chi)
    return proof.qed(chi)
```

作者不应重复填写：

- step label；
- assertion 的内部 legacy operation 名；
- 可由 assertion signature 与 premises 唯一推断的 substitution；
- 可由 kernel 计算的 result formula；
- 只为生成器服务的 note/ref 字符串。

`proof.use()` 必须调用统一的 assertion-application kernel，由它完成 unification、substitution、
premise/result 检查与 DV 检查。`proof.qed()` 必须确认 root 等于 theorem conclusion，并生成 immutable
`ElaboratedProof` 与 semantic digest。

需要消除歧义时，可以显式提供 `target=` 或 `subst=`；它们是约束 kernel 的信息，不是第二套
proof semantics。

### 3.4 family 与 combinator 必须在 elaboration 前展开

proof family 和 combinator 可以减少重复，但必须确定性地展开为普通 `AssertionSignature` 与
`proof.use()` 调用。`ElaboratedProof` 中不得保留“family step”或“combinator step”这种第二类步骤。

### 3.5 最后才 lower 到 legacy/Metamath

```text
ElaboratedProof
    ↓ build_semantic_replay_plan
SemanticReplayPlan
    ↓ ResolvedMetamathLanguageBinding + LegacyReplayBinding
legacy Proof / Step
    ↓ BuilderV2 / linker
.mm
```

proof semantic digest 不得包含 `SymbolId`、临时 step label、文件路径或 token spelling。backend
binding 负责把 stable assertion ID 映射到 Metamath label，把 semantic Term lower 为 token stream。

---

## 4. 推荐的包布局

```text
logic/<domain>/
  language.py             semantic LanguageSpec 与 typed constructors
  notation.py             parse/render policy
  metamath_binding.py     typecodes、tokens、formation assertions
  calculus.py             judgment kinds 与 primitive inference rules
  axioms.py               AxiomDecl / DefinitionDecl 与公开 AXIOMS
  rules.py                primitive rule assertion view 与 catalog/profile
  theorems.py             公开 prove_* 与 THEOREMS

  _builtins.py            legacy runtime/backend adapter
  _structures.py          legacy Expr compatibility facade
  _semantic_proofs.py     手写 semantic proof 或 transpiler 输出的过渡位置
  _system.py              legacy System binding
```

下划线文件可以承载兼容实现，但数学事实源应在 semantic declarations 中。公开 `prove_*` 可以继续
直接导入；`AXIOMS / RULES / THEOREMS` 则提供反射、构建和 agent 使用的聚合 metadata。

---

## 5. 审查清单

### 定义结构

- [ ] sort、variable kind、constructor 使用稳定 ID；
- [ ] constructor signature 与 binder contract 位于 `LanguageSpec`；
- [ ] notation 与 Metamath token layout 不在 `LanguageSpec`；
- [ ] typed facade 只调用 `LANGUAGE.apply()`；
- [ ] formation assertion 与 primitive inference rule 已正确分类；
- [ ] semantic、notation 与 backend digest 相互独立。

### 给出公理或定义

- [ ] schema variables 归属于 assertion ID；
- [ ] conclusion 是明确的 `Judgment`；
- [ ] 所有变量恰好被声明；
- [ ] mandatory DV 使用 typed `DistinctPair`；
- [ ] definition 使用 `DefinitionDecl`，没有伪装成 theorem；
- [ ] 公开 metadata 是事实源，legacy formula 由其派生。

### 给出证明

- [ ] theorem signature 在 proof body 之前定义；
- [ ] 所有依赖 assertion 位于 catalog/profile；
- [ ] proof body 只使用 `proof.hypotheses`、`proof.use()` 与 `proof.qed()`；
- [ ] 没有重复 result formula、内部 label 或可推断 substitution；
- [ ] DV 来自 scoped source/replay context，而不是隐藏 side effect；
- [ ] lowering 后三套 verifier 通过，且迁移切片的 `.mm` 输出保持预期不变。

---

## 6. 明确禁止的形态

以下写法不得成为新的事实源：

```python
# 错误：用 token spelling 充当 constructor identity
Constructor("A.", 2)

# 错误：在数学 constructor 中拼接 backend token
def All(x, phi):
    return Wff("wff", (builtins.forall, *x.tokens, *phi.tokens))

# 错误：把 definition 冒充 theorem
AssertionSignature(kind="theorem", canonical_label="df-an", ...)

# 错误：证明步骤重复声明 kernel 可以推出的结果
proof.ref("step7", "psi", ref="ax-mp", ...)

# 错误：import 模块时修改全局 registry 来决定当前语言
DEFAULT_BUILDERS.register("A.", ...)
```

迁移期的 compatibility adapter 可以暂时生成旧对象，但必须保持单向关系：

```text
semantic declaration  ──生成──▶  legacy adapter

legacy global state   ──不得──▶  public semantic contract
```

这条单向关系是结构、公理与证明能够规模化迁移，同时保持现有 `.mm` 输出和公开 `prove_*` 兼容性的
关键。
