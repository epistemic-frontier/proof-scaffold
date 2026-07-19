# Reference 012: Semantic Definition of Structures, Axioms, and Proofs

> Status: `api-proposal-0.1` author specification, 2026-07-17.
>
> The terms “MUST,” “MUST NOT,” “SHOULD,” and “MAY” in this document are to be interpreted as normative requirements.

This document is the authoring-practice specification for [Reference 011: Language as a First-Class Element](011-language-as-first-class.en.md),
and takes the semantic authoring API currently implemented by [Project 024: First-Class Language Refactor](../projects/024-first-class-language-refactor.en.md)
as its baseline. Some imports are omitted from code snippets in order to focus on semantic boundaries.

## 0. Purpose and General Principles

This document answers three questions for package authors:

1. How to define mathematical structures—that is, the sorts, variable kinds, constructors, and binders in a language;
2. How to state axioms or definitions over that language and calculus;
3. How to provide proofs solely by applying registered assertions.

The core discipline is: **mathematical objects exist first as backend-neutral semantic objects and are only then bound to Metamath.** Python
function names, Unicode characters, set.mm tokens, Metamath labels, and runtime `SymbolId` values are not content identifiers for mathematical objects.

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

A formula is a `Term`; “this formula is provable” is `Judgment(PROVABLE, (term,))`. The two MUST NOT be conflated.

---

## 1. Defining Structures: First Define What Can Be Written

### 1.1 Use stable identifiers

Every sort, variable kind, and constructor MUST have a stable nominal identifier:

```python
from skfd.authoring.ids import ConstructorId, LanguageId, SortId, VariableKindId

FOL_LANGUAGE_ID = LanguageId("example/fol#language:first-order")
SETVAR = SortId("example/fol#sort:setvar")
SETVAR_VARIABLE = VariableKindId("example/fol#variable-kind:setvar")

ALL = ConstructorId("example/fol#constructor:all")
EQ = ConstructorId("example/fol#constructor:equality")
```

An ID is an identifier; `∀`, `A.`, and `All` are merely spellings at different layers. Changing a display character MUST NOT change `ALL`.

The recommended ID forms are:

```text
<package>/<domain>#sort:<name>
<package>/<domain>#variable-kind:<name>
<package>/<domain>#constructor:<name>
<package>/<domain>#axiom:<label>
<package>/<domain>#definition:<label>
<package>/<domain>#proof:<label>
```

### 1.2 Declare sorts, variable kinds, constructors, and binders

```python
from skfd.authoring.language import (
    BinderDecl,
    BindingClause,
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
            bindings=(
                BindingClause(variable_argument=0, scoped_arguments=(1,)),
            ),
        ),
    ),
)
```

`ConstructorDecl` answers only questions about inputs, outputs, and binding behavior. It MUST NOT contain Unicode, token layouts,
Metamath labels, or arbitrary Python callbacks.

`And : Wff × Wff → Wff` belongs to the language; `df-an` is a definition. Adding a constructor only expands “what can be said”;
adding a definition or axiom changes “what can be derived.”

### 1.3 Resolve language extensions explicitly

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

Dependency digests MUST participate in resolution. Import order MUST NOT determine language content; duplicate IDs MAY be merged only when their declarations are exactly identical.

### 1.4 Provide direct, typed constructors

Ordinary mathematical code SHOULD NOT assemble formulas through string maps. Packages SHOULD provide thin callable façades:

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

These functions MUST NOT assemble tokens themselves or modify a global registry. Sort, arity, and binder checks MUST be performed by
`LanguageInterface.apply()`.

### 1.5 Separate notation from backend bindings

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

Accepted aliases, canonical rendering, and backend tokens are three distinct policies. Accepting `forall` does not mean that
the formatter or Metamath backend SHOULD output `forall`.

The Metamath realization is provided by a separate binding:

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

`wal` and `weq` are formation assertions, not inference rules. `ax-gen`, by contrast, is a primitive
inference rule of the calculus.

A coercion with no surface token MAY retain only its argument:

```python
FormationBinding(
    constructor=CV,
    syntax_assertion=AssertionSemanticId("example/fol#formation:cv"),
    syntax_assertion_label="cv",
    template=(ArgumentPart(0),),
)
```

Thus, a semantic term MAY explicitly be written as `Elem(Cv(x), Cv(y))`, while the backend still outputs `x e. y`.

---

## 2. Stating an Axiom: Declare a Premise-Free Judgment

### 2.1 Schema variables MUST belong to an assertion

```python
AX5_ID = AssertionSemanticId("example/fol#axiom:ax-5")
AX5_OWNER = OwnerId(str(AX5_ID))

PHI_REF = VariableRef("schema", AX5_OWNER, "phi", WFF_VARIABLE)
X_REF = VariableRef("schema", AX5_OWNER, "x", SETVAR_VARIABLE)

phi = LANGUAGE.variable(PHI_REF)
x = SetVar(X_REF)
```

A variable's display name is not its identifier. Different assertions MUST NOT share variable identifiers merely because both use the string `"phi"`.

### 2.2 Construct a Term first, then wrap it in a Judgment

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

The layered meanings are:

```text
Imp(phi, All(x, phi))       a Wff Term
Judgment(PROVABLE, (...,))  “this Wff is provable”
AxiomDecl                   a primitive assertion with no premises
```

`resolve_axiom` MUST validate schema variables, sorts, the judgment kind, the constructor tree, and mandatory
DV endpoints, and MUST produce a deterministic digest.

### 2.3 The assertion contract and source scope of `$d`

`mandatory_distinct` is the public application contract of an assertion; `$d` in author source is a lexical-scope declaration. The two SHOULD be connected through
the `SourceBlock` elaboration process:

```python
signature = signature_from_axiom(AX5, canonical_label="ax-5")

source = SourceBuilder()
with source.block() as block:
    block.d(PHI_REF, X_REF)
    block.assertion(replace(signature, mandatory_distinct=()))

snapshot = elaborate_block(source.build()).assertions[0]
assert snapshot.declaration == signature
```

Source grouping and the semantic pair relation MUST remain separate. Multiple `$d` statements have identical assertion/proof semantic content
as long as they expand to the same canonicalized pair relation.

### 2.4 Definitions MUST NOT masquerade as theorems

Definitions and axioms have the same premise-free judgment shape, but belong to different semantic categories:

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

Constructors, definitions, axioms, and theorems MUST remain four distinct semantic categories. The fact that a backend uses `$a` for all of them
is not a reason to merge them in the author API.

### 2.5 Expose metadata and isolate legacy adapters

The public `AXIOMS` mapping SHOULD store semantic interfaces:

```python
AXIOMS: Mapping[str, AxiomInterface | DefinitionInterface] = MappingProxyType(
    {"ax-1": AX1, "df-an": DF_AN}
)
```

During migration, `LEGACY_AXIOMS` MAY be derived from semantic terms for use by the old `System.compile_axioms()`; the public semantic contract
MUST NOT instead be generated from legacy `Expr` values, and two copies of formulas MUST NOT be maintained by hand indefinitely.

---

## 3. Providing a Proof: Declare the Goal, Then Apply Assertions

### 3.1 The theorem signature MUST precede the proof body

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

The signature is the theorem's public contract; the proof body is one implementation of that contract. Replacing the proof body SHOULD NOT change
the signature's content identifier.

### 3.2 Every referenceable assertion MUST enter the catalog/assertion profile

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

The assertion profile (`AssertionProfile`) explicitly specifies which axioms, definitions, primitive rules, and existing theorems the current proof may use. A proof MUST NOT bypass the
catalog through an unregistered Python callable.

### 3.3 A proof body contains only mathematical actions

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

Authors SHOULD NOT redundantly supply:

- a step label;
- the assertion's internal legacy operation name;
- a substitution uniquely inferable from the assertion signature and premises;
- a result formula computable by the kernel;
- note/ref strings used only by the generator.

`proof.use()` MUST call the shared assertion-application kernel, which performs unification, substitution,
premise/result checks, and DV checks. `proof.qed()` MUST confirm that the root equals the theorem conclusion and generate an immutable
`ElaboratedProof` and semantic digest.

When disambiguation is required, `target=` or `subst=` MAY be supplied explicitly; they are information that constrains the kernel, not a second set of
proof semantics.

### 3.4 Families and combinators MUST expand before elaboration

Proof families and combinators MAY reduce repetition, but they MUST deterministically expand into ordinary `AssertionSignature` values and
`proof.use()` calls. An `ElaboratedProof` MUST NOT retain a second class of steps such as “family steps” or “combinator steps.”

### 3.5 Convert to legacy/Metamath backend representations only at the end

```text
ElaboratedProof
    ↓ build_semantic_replay_plan
SemanticReplayPlan
    ↓ ResolvedMetamathLanguageBinding + LegacyReplayBinding
legacy Proof / Step
    ↓ BuilderV2 / linker
.mm
```

A proof semantic digest MUST NOT contain `SymbolId`, temporary step labels, file paths, or token spellings. The backend
binding maps stable assertion IDs to Metamath labels and converts semantic terms into token-stream backend representations.

---

## 4. Recommended Package Layout

```text
logic/<domain>/
  language.py             semantic LanguageSpec and typed constructors
  notation.py             parse/render policy
  metamath_binding.py     typecodes, tokens, formation assertions
  calculus.py             judgment kinds and primitive inference rules
  axioms.py               AxiomDecl / DefinitionDecl and public AXIOMS
  rules.py                primitive-rule assertion views and catalog/assertion profile
  theorems.py             public prove_* and THEOREMS

  _builtins.py            legacy runtime/backend adapter
  _structures.py          legacy Expr compatibility façade
  _semantic_proofs.py     transitional location for handwritten semantic proofs or transpiler output
  _system.py              legacy System binding
```

Underscore-prefixed files MAY carry compatibility implementations, but semantic declarations SHOULD be the source of truth for mathematical facts. Public `prove_*` functions MAY continue
to be imported directly; `AXIOMS / RULES / THEOREMS` provide aggregate metadata for reflection, builds, and agents.

---

## 5. Review Checklist

### Defining structures

- [ ] Sorts, variable kinds, and constructors use stable IDs;
- [ ] Constructor signatures and binder contracts reside in `LanguageSpec`;
- [ ] Notation and Metamath token layouts do not reside in `LanguageSpec`;
- [ ] The typed façade calls only `LANGUAGE.apply()`;
- [ ] Formation assertions and primitive inference rules are correctly classified;
- [ ] Semantic, notation, and backend digests are mutually independent.

### Stating an axiom or definition

- [ ] Schema variables belong to the assertion ID;
- [ ] The conclusion is an explicit `Judgment`;
- [ ] Every variable is declared exactly once;
- [ ] Mandatory DV conditions use typed `DistinctPair` values;
- [ ] A definition uses `DefinitionDecl` and does not masquerade as a theorem;
- [ ] Public metadata is the source of truth, and legacy formulas are derived from it.

### Providing a proof

- [ ] The theorem signature is defined before the proof body;
- [ ] Every assertion dependency is in the catalog/assertion profile;
- [ ] The proof body uses only `proof.hypotheses`, `proof.use()`, and `proof.qed()`;
- [ ] No result formula, internal label, or inferable substitution is repeated;
- [ ] DV information comes from scoped source/replay context, not from a hidden side effect;
- [ ] After backend conversion, all three verifiers pass, and the `.mm` output of the migration slice remains unchanged as expected.

---

## 6. Explicitly Prohibited Forms

The following forms MUST NOT become new sources of truth:

```python
# 错误：用 token spelling 充当 constructor 标识符
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

During migration, a compatibility adapter MAY temporarily generate old objects, but it MUST preserve the one-way relationship:

```text
semantic declaration  ──generates──▶  legacy adapter

legacy global state   ──MUST NOT──▶  public semantic contract
```

This one-way relationship is the key to migrating structures, axioms, and proofs at scale while preserving existing `.mm` output and public `prove_*`
compatibility.
