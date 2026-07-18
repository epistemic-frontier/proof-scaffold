# ProofScaffold Terminology

> Status: Draft v0.1, 2026-07-18.  
> Chinese version: [ProofScaffold 术语规范](000-terminology.zh.md)  
> Scope: ProofScaffold design documents, public API documentation, code review, exchange-format specifications, and related bilingual material.  
> This document defines preferred project terminology but does not freeze Python class names, file-format names, or serialization protocols.

## 1. Purpose

ProofScaffold spans mathematical logic, proof assistants, compilers, data exchange, and search systems. The same English word may carry different meanings across these fields, and literal translation or unrestricted code jargon can collapse distinctions among:

- an object's name, content, and identity relation;
- a proof being complete and a proof being verified;
- author-facing shorthand, core semantic objects, and backend execution representations;
- an assertion being permitted and an assertion having a trusted implementation;
- in-memory objects, exchange archives, and verification certificates.

This terminology specification establishes a stable, natural, and auditable bilingual vocabulary so that one concept retains one meaning across documentation, APIs, and technical discussion.

## 2. Technical Background and Architecture

### 2.1 Mathematical semantic stack

```text
Formal language
  determines which expressions are well formed
        │
        v
Judgments and calculus
  determine which judgments exist and how new judgments are derived
        │
        v
Logic
  combines language, calculus, and logical axioms
        │
        v
Mathematical theory
  adds domain language, definitions, non-logical axioms, and theorems
        │
        v
Assertion interfaces and proof implementations
```

### 2.2 Three representation stages

```text
Specifications and declarations
  finite author-maintained source of truth
        │ resolution, conflict checking, inheritance expansion
        v
Semantic interfaces
  immutable, digestible, consumer-facing
        │ binding notation, backends, resolvers, and build context
        v
Runtime environments
  support actual authoring, verification, and output
```

These stages must not be collapsed. Runtime objects are not mathematical content identities, and notation or backend tokens do not belong to abstract-language semantics.

### 2.3 Proof lifecycle

```text
ProofAuthor ───────────────┐
                           v
                     Complete Proof ───> Semantic Verification ───> Proof Archive
                           │
ProofState <──refine/search┘
                           │
                           └───> Backend Conversion ───> Metamath and other backends
```

Linear proofs are written through `ProofAuthor`; interactive proving and search use immutable `ProofState`. Both produce the same kind of complete proof and share one assertion-application kernel and one final acceptance semantics.

### 2.4 Four concepts that must remain distinct

```text
Identifier
  how an object is referenced

Content digest
  whether canonical content is exactly equal

Verification result
  whether the object is valid under a theory environment and trust policy

Verification certificate
  persistable or transferable evidence of verification
```

A digest does not imply verification, and equal names do not imply equal content.

## 3. Terminology Policy

1. English code identifiers remain in backticks. Chinese documentation uses the preferred Chinese term followed by the code name on first occurrence.
2. Established mathematical terms take precedence where available.
3. One English word need not map to one Chinese word in every context. Terms such as artifact, identity, and projection must be translated by meaning.
4. `identifier`, `digest`, and identity relations are distinct.
5. Structural validation and semantic verification are distinct.
6. `elaboration` is translated as 详化 and `refinement` as 证明精化; the two terms must not be conflated.
7. A proof may be described as verified only after semantic replay under an exact theory environment.
8. Public terminology should describe responsibilities directly rather than preserve internal metaphors.
9. Translate `author` as 作者 or 证明作者 when it denotes a person and `proof authoring` as 证明写作 when it denotes the activity; only the explicit software component `ProofAuthor` is 证明编写器.
10. In scope, identifier, uniqueness, and object-identity contexts, translate `global` as 全局, never 全球 or 世界.

## 4. Provisional Terms Requiring Focused Review

All terms identified for focused review in this round have been settled and moved into the normative tables below. New ambiguities should be added here as they arise.

## 5. Layer 1: Architectural and Representation Stages

This layer defines the basic vocabulary used to describe object lifecycles in the architecture.

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Specification | 规范 | Finite declarative data authored by a library author to state the contents and constraints of an object. | Acts as the source of truth; it should be checkable, digestible, and independent of arbitrary runtime callbacks. |
| Declaration | 声明 | A named semantic unit in a specification, such as a sort, constructor, inference rule, axiom, or theorem declaration. | Provides the smallest independently referenceable, checkable, and composable unit of definition. |
| Interface | 接口 | A read-only public view produced after dependency resolution, conflict checking, and inheritance expansion. | Serves as the consumer-facing contract; its content is fixed by an interface digest and is distinct from any particular implementation. |
| Implementation | 实现 | Concrete content satisfying an interface, such as a theorem proof body or a backend binding. | Allows the concrete realization to change without changing the interface. |
| Resolution | 解析与合成 | The process of checking declarations, resolving dependencies, expanding inheritance, and producing an immutable interface. | Transforms author-facing specifications into safe consumer interfaces; it should be distinguished from syntactic parsing. |
| Runtime environment | 运行时环境 | A runtime object that binds semantic interfaces to notation, backends, registries, resolvers, and build context. | Supports parsing, construction, verification, and backend output, but must not be treated as the content identity of a mathematical object. |
| Façade | 简化接口 | A narrow user-facing interface that hides internal objects users should not need to manage directly. | For example, `Theory` or `ProofAuthor` may act as simplified entry points; Chinese prose should avoid using the untranslated word façade. |
| Immutable | 不可变 | An object whose observable state does not change after construction; operations express change by returning new objects. | Provides a stable basis for proof branching, caching, concurrency, and content digests. |

## 6. Layer 2: Language and Expressions

This layer describes which expressions are well formed and how they are built; it does not determine which judgments are provable.

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Formal language | 形式语言 | A finite expression-building system consisting of sorts, variable kinds, constructors, and binding behavior. | Determines what can be written and forms the semantic basis of logics, theories, and proofs. |
| Sort | 类别 | A named component of a many-sorted language or algebraic signature that classifies terms; every variable and term has a sort, and constructor inputs and outputs are specified by sorts. | Corresponds to `SortId`; under an algebraic interpretation, each sort denotes a carrier set. It is close to a basic type but is not the same as `Type` in the general type-theoretic sense. |
| Variable kind | 变量种类 | A classification of variables that determines their sort and permitted binding behavior. | Structurally distinguishes object variables, formula variables, class variables, and similar families. |
| Term | 项 | A core semantic expression in a formal language, typically formed recursively from variables and constructor applications. | The common expression object used by authors, verifiers, and exchange formats; a rendered string is not the term itself. |
| Variable term / Application term | 变量项 / 应用项 | A variable term refers to a variable; an application term applies a constructor to an ordered list of arguments. | Corresponds to `Var` and `App`, which form the hole-free core `Term` union. |
| Constructor | 构造子 | An expression-forming operation with a stable identifier, argument sorts, and a result sort. | Defines abstract-syntax tree nodes; display symbols and backend tokens are not part of the constructor's semantic identity. |
| Binder | 绑定算子 | Constructor behavior that introduces variables at designated argument positions and specifies their scope over other arguments. | Supports quantifiers and similar forms and provides the basis for free-variable analysis, capture checks, and alpha-renaming. |
| Abstract syntax | 抽象语法 | A structured expression representation independent of concrete spelling, typography, and backend tokens. | Allows notations such as `→` and `->` to denote the same semantic constructor. |
| Token | 词元 | An indivisible lexical unit used in parsing or a backend representation. | Supports parsing and backend output; token spelling is not the semantic identifier of a constructor. |
| Notation | 记法 | Input and display conventions for expressions, including aliases, precedence, associativity, and canonical rendering. | Improves authoring ergonomics; notation changes must not change term or language semantic digests. |
| Parsing | 句法解析 | The process of transforming character or token sequences into syntax trees or semantic terms. | Belongs to notation and frontend processing and should not be confused with dependency resolution. |
| Rendering | 呈现 | The process of converting semantic terms into Unicode, ASCII, LaTeX, or another surface form. | Supports human-readable display; rendered output does not participate in mathematical content identity. |
| Backend binding | 后端绑定 | A mapping from abstract language objects to backend-specific typecodes, token templates, and syntax assertions. | Connects backend-neutral semantics to concrete systems such as Metamath without changing the abstract language. |
| Formation assertion | 语法形成断言 | A backend assertion showing that a token sequence forms a well-formed expression. | It serves backend well-formedness and is not a logical axiom or inference rule. |
| Free variable / Bound variable | 自由变量 / 约束变量 | A free-variable occurrence is not governed by a surrounding binder; a bound-variable occurrence lies within a binder's scope. | Used in substitution, distinct-variable checks, capture detection, and alpha-equivalence. |
| Capture-avoiding substitution | 避免变量捕获的代入 | Substitution that replaces variables with terms while preventing formerly free variables from becoming accidentally bound. | A fundamental semantic operation for languages with binders; it must be distinguished from purely structural assertion instantiation where appropriate. |
| Alpha-renaming | α-改名 | Systematic renaming of bound variables without changing binding structure. | Prevents capture and supports equivalence notions that ignore the spelling of bound variables. |
| Backend-neutral | 后端无关 | A property of an object whose semantics do not depend on a particular proof backend, token layout, or runtime symbol. | Allows the same language, theory, and proof to be reused by multiple verifiers and backends. |

## 7. Layer 3: Judgments, Calculi, Logics, and Theories

This layer describes which judgments may be made about expressions and how axioms, rules, and theorems derive them.

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Judgment | 判断 | A structured assertion made by a formal system about one or more terms, such as “formula φ is provable.” | Separates object-language expressions from meta-level claims such as provability or typing. |
| Judgment kind | 判断种类 | A declaration of a judgment's name, arity, and argument sorts. | Provides a finite, checkable judgment vocabulary for a calculus. |
| Calculus | 演算系统 | A deductive system consisting of judgment kinds and primitive inference rules. | Determines how judgments are derived from prior judgments and is distinct from the object language and theory-specific axioms. |
| Primitive inference rule | 原始推理规则 | An inference rule accepted directly by the calculus rather than proved within it. | Forms part of the trusted basis of the calculus; proved derived rules should remain reusable theorems. |
| Logic | 逻辑系统 | A combination of a formal language, a calculus, and logical axioms. | Defines a consequence relation that may be reused by multiple mathematical theories. |
| Theory | 理论 | An organized system that extends a logic with domain language, definitions, non-logical axioms, and theorems. | Acts as the primary semantic environment for proof construction, verification, search, and exchange. |
| Theory interface | 理论接口 | The language, calculus, assertion interfaces, import requirements, and content digests exposed by a theory. | Allows other theories and proofs to depend precisely on the theory without depending on its build process. |
| Verification environment lock (`VerificationEnvironmentLock`) | 验证环境锁定清单 | A read-only manifest recording the exact language, calculus, assertion interfaces, imports, assertion profile, trust policy, and verification-protocol version required to verify a proof. | Fixes the complete verification environment and prevents same-name substitutions or dependency and policy drift; it records content and policy requirements but neither provides referenced content nor states that verification succeeded. It is a value object that may be embedded in an archive, not necessarily a standalone file, and not a runtime mutex. |
| Axiom | 公理 | An assertion accepted directly in a logic or theory without proof premises. | Forms part of the theory's explicit assumption basis. |
| Definition | 定义 | A named assertion classified as a definition and used to introduce or specify an expression. | Is distinct from axioms and theorems; classification as a definition alone does not establish conservativity. |
| Theorem | 定理 | A named conclusion with a public assertion interface and a supporting proof implementation. | May be used by subsequent proofs; its interface and proof body should be identified separately. |
| Assertion | 断言 | The common term for an axiom, definition, primitive inference rule, or proved theorem when exposed through a uniform application interface. | Allows proof steps to reference and apply different sources of inference uniformly. |
| Assertion signature | 断言签名 | The public interface of an assertion, including schema variables, ordered premises, conclusion, and mandatory distinct-variable conditions. | Acts as the theorem-level calling contract shared by verification, construction, and search. |
| Premise / Conclusion | 前提 / 结论 | Premises are judgments required before an assertion may be applied; the conclusion is the judgment produced by a successful application. | Defines the inputs and output of assertion application. |
| Schema variable | 模式变量 | A variable owned by an assertion and instantiated with a concrete term when the assertion is applied. | Expresses reusable axiom, rule, and theorem patterns; its owner is part of its identifier. |
| Distinct-variable condition | 变量互异条件 | An application condition requiring variables occurring in two schema-variable substitutions to satisfy a specified distinctness relation. | Carries Metamath `$d` semantics and prevents invalid variable overlap. |
| Assertion catalog | 断言目录 | A read-only collection of resolvable assertion interfaces indexed by stable identifiers. | Provides a deterministic assertion lookup space for proof construction and verification. |
| Assertion profile (`AssertionProfile`) | 断言应用许可集（简称“断言许可集”） | A named subset selected from an assertion catalog whose members may be applied by proof steps in a particular construction and verification environment. | Proof authoring, proof search, and semantic replay should check the permission set before applying an assertion. It restricts inference capabilities but is not user access control and cannot make a theorem without a verifiable implementation trusted. |
| Conservative extension | 保守扩张 | An extension of a theory that proves no new statements expressible in the original language. | Evaluates whether a definition or language extension changes the proof-theoretic strength of the existing theory. |

## 8. Layer 4: Proof Authoring and Construction

This layer describes the process of forming a complete proof from goals and available premises. Linear authoring and interactive or search-driven construction should share final acceptance semantics without necessarily sharing the same state representation.

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Proof author | 证明作者 | A person or agent engaged in writing a proof. | Must be distinguished from the software component `ProofAuthor`; unqualified `author` is translated as 作者 according to context. |
| Proof authoring | 证明写作 | The activity of writing proof steps through an interface centered on mathematical actions. | Emphasizes authoring ergonomics and code expression and is typically supported by `ProofAuthor`. |
| Proof construction | 证明构造 | The computational process of building a proof object by applying assertions, solving constraints, and closing goals. | Covers linear authoring, interactive proving, and automated search; the preferred Chinese term is 构造 rather than 建构. |
| Proof-authoring interface (`ProofAuthor`) | 证明编写器 | A simplified software interface for writing complete, forward, linear proofs. | Binds the theory environment and hides lower-level draft, checking, and finalization machinery behind `use()` and `qed()`; it is not the proof author. |
| Proof draft (`ProofDraft`) | 证明草稿 | A proof record that has not yet been finalized. The current `ProofDraft` implementation contains only fully reified, immediately checked steps. | Should be distinguished from a true state containing goals, holes, and metavariables; the current class is closer to a checked proof prefix. |
| Checked proof prefix | 已检查证明前缀 | A prefix consisting of ordered hypotheses and concrete proof steps that have passed local checks. | More accurately describes the semantics of the current `ProofDraft` and may serve as its future internal name. |
| Proof state (`ProofState`) | 证明状态 | An immutable construction snapshot containing open goals, local steps, metavariables, constraints, and an exact theory environment. | Serves as the common mathematical state for interactive proving and search; search scores and search-tree metadata do not belong in it. |
| Goal | 待证目标 | A judgment in a proof state that has not yet been closed. | Provides the target of a refinement action and should be referenced through a stable `GoalId` in public APIs. |
| Hole | 证明空缺 | A placeholder in a proof structure whose derivation has not yet been supplied. | Belongs only to the construction layer and must not appear in final proofs or the verifier's core `Term`. |
| Metavariable | 元变量 | An internal variable representing a term not yet determined during construction. | Carries underdetermined substitutions and is progressively resolved by unification and constraint solving. |
| Constraint | 约束 | A condition that must be satisfied during proof construction, such as term equality, sort compatibility, or variable distinctness. | Allows unresolved information to remain temporarily during backward application; all constraints must be solved before finalization. |
| Elaboration | 详化 | The process of parsing, completing, disambiguating, and generating constraints for author- or source-level objects that contain abbreviations, scopes, implicit information, or partial specifications, thereby transforming them into more explicit core representations. | Elaboration may produce metavariables and unresolved constraints and may include expansion; it is distinct from expansion alone, proof-goal refinement, finalization, and semantic verification. |
| Refinement | 证明精化 | Application of an assertion or construction action to a goal, producing a more specific state and possibly new subgoals. | The basic state transition for interactive proving and search, corresponding to `ProofState.refine()`. |
| Forward / Backward construction | 前向构造 / 反向构造 | Forward construction derives new conclusions from available premises; backward construction decomposes a goal into subgoals. | Correspond respectively to the primary paths of `ProofAuthor.use()` and `ProofState.refine()`. |
| Proof step / Step reference | 证明步骤 / 步骤引用 | A proof step is a concrete assertion application or hypothesis occurrence; a step reference is a value-based reference to that occurrence. | Connects premises and conclusions within a proof; references may remain proof-local or lineage-local rather than becoming global objects. |
| State transition | 状态转移 | A deterministic operation from an immutable proof state and a construction request to either a new state or a structured failure. | Provides the stable core operation used by search engines and possible batch APIs. |
| Branch | 分支 | One of several successor states obtained by applying different refinements to the same immutable state. | Represents the search space; retaining the original state provides undo without an explicit core-state undo operation. |
| Snapshot / Lineage | 状态快照 / 演化链 | A snapshot is a complete immutable state at a point in construction; a lineage is the ancestor–successor relation formed by successive transitions. | Defines the stability scope of `GoalId`, `MetaId`, and step references and supports state digests. |
| Unification | 合一 | The process of finding a substitution that makes two terms structurally equal. | Used in assertion application, goal matching, and metavariable resolution. |
| Instantiation | 实例化 | Replacement of schema variables in an assertion according to a complete substitution. | Computes concrete premises and conclusions from an assertion pattern and must be independently reproducible by the verifier. |
| Finalization | 完成检查 | The process of checking root conclusion, reachability, and other completeness conditions after all goals and constraints are closed, then producing a complete proof. | The sole exit from construction to complete proofs, corresponding to `qed()` or `finish()`. |

## 9. Layer 5: Complete Proofs, Verification, and Trust

This layer distinguishes a fully formed proof object from a proof verified under an exact theory environment. A content digest is not a verification result.

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Complete proof | 完整证明 | A proof object with no goals, holes, metavariables, or unresolved constraints, whose steps are concrete assertion applications. | Serves as the common core object for verification, exchange, backend conversion, and analysis. |
| Elaborated proof (`ElaboratedProof`) | 完整证明对象（现有代码名） | The current API class representing a structurally elaborated and finalized proof. | Chinese prose should normally call it a complete proof rather than coin a literal translation; it may evolve into the public `Proof` type. |
| Proof DAG | 证明有向无环图（证明图） | A directed acyclic graph whose nodes are hypotheses and assertion applications and whose edges represent premise dependencies. | Preserves shared dependencies and supports reachability, dependency, and replay analysis. |
| Root | 根结论 | The designated final conclusion node of a complete proof. | Determines the theorem conclusion implemented by the proof and bounds the relevant proof closure. |
| Direct dependency / Dependency closure | 直接依赖 / 依赖闭包 | Direct dependencies are assertions referenced explicitly by proof steps; the dependency closure recursively includes dependencies of referenced theorems. | Separates interfaces needed for local replay from transitive dependencies needed for theory verification, publication, and audit. |
| Structural validation | 结构检查 | Checking that the internal shape of a proof object is well formed, including step numbering, reference direction, root conclusion, and reachability. | Establishes structural consistency only; it does not prove that assertion applications are semantically valid in a theory. |
| Semantic verification | 语义验证 | Re-resolving and reapplying every assertion under an exact theory environment while recomputing substitutions, results, DV conditions, and dependencies. | Provides the authoritative validity judgment, corresponding to `Theory.verify()` or `verify_proof()`. |
| Assertion-application kernel | 断言应用内核 | The common core that performs unification, complete substitution, result computation, sort checks, and DV checks for a concrete assertion application. | Must be shared by proof authoring, semantic replay, and finalization to preserve a single acceptance semantics. |
| Replay | 语义重放 | Stepwise re-execution and checking of a proof from recorded assertion references, premise positions, and substitutions. | Transforms proof data from merely declared content into content confirmed by independent recomputation. |
| Replay context | 重放上下文 | Environmental information required when replaying a proof, such as active DV relations and exact assertion-interface requirements. | Ensures that proof steps retain their intended semantics during exchange, loading, and backend conversion. |
| Verification report | 验证报告 | A structured verifier result containing at least success status, stable error codes, locations, expected and actual values, and relevant evidence. | The primary public object for expressing verification results and audit information. |
| Diagnostic | 诊断信息 | A machine-readable classification and contextual explanation of a construction or verification failure. | Supports stable consumption by search, batch processing, repair, training data, and user interfaces; free-form exception text is insufficient. |
| Evidence / Witness | 证据 / 见证 | Supporting data recomputed by the verifier, such as variable pairs satisfying a DV condition or locations of conflicts. | Supports audit and diagnosis but must not become a second unchecked source of authority. |
| Trust policy | 信任策略 | An explicit policy specifying which primitive declarations, external dependencies, or exceptional unproved objects may serve as verification assumptions. | Separates a proof's mathematical implementation from the trust boundary under which it is accepted. |
| Trust root | 信任根 | A foundational declaration explicitly approved by the trust policy and not further proved within the current theory. | Forms the explicit trusted basis on which verification ultimately rests. |
| Oracle | 免证断言（代码中可称 `oracle`） | An external assertion explicitly permitted by an advanced trust policy despite lacking a verifiable implementation. | Must appear in verification reports and trust dependencies and must not become trusted merely by catalog or profile membership. |
| Trust closure | 信任依赖闭包 | The transitive set of all trust roots, oracles, and other explicit assumptions on which a proof ultimately depends. | Explains what the proof ultimately trusts; prose may describe it as the final trust basis. |
| Verification certificate | 验证证书 | A persistable or transferable evidence object stating that an implementation passed verification under a particular verification environment lock. | Distinct from a content digest and an ordinary report; its format and security semantics require separate specification. |
| Independent verifier | 独立验证器 | A verifier implemented independently and capable of checking a proof without executing producer code. | Reduces common-implementation risk and provides an important conformance check before freezing an exchange format. |

## 10. Layer 6: Identifiers, Identity, and Digests

This layer contains distinctions that the current documentation most needs to preserve. An identifier, identity relation, digest, and verified status are different concepts, and the English word identity should not be translated mechanically.

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Identifier | 标识符 | A stable name or structured key used to reference an object. | Answers how to refer to an object, not what its content is or whether it is valid. |
| Nominal identifier | 名称标识符 | A stable identifier composed of a namespace and local name that identifies a declaration by name. | Preserves readable names across versions while content digests check compatibility; it should not be treated as a content identity. |
| Object identity | 对象同一性 | The relation of two references designating the same runtime object. | May support in-process ownership checks but cannot serve as a mathematical identity across processes or serialization. |
| Semantic identity | 语义同一性 | A relation, defined by an explicit specification, determining whether two semantic objects represent the same content. | Must state the normalization and equivalence relation used and cannot be inferred from names or Python object addresses alone. |
| Content equality | 内容一致 | Equality of two objects' canonical representations. | Usually checked efficiently through digests under the same version and digest domain; it is not the same as mathematical equivalence. |
| Canonical form | 规范形式 | A representation uniquely determined for a given content by an explicit specification. | Provides the basis for deterministic serialization, digests, and cross-implementation agreement. |
| Canonical projection | 规范表示映射 | A mapping from an in-memory object to the authoritative fields and ordering of its canonical representation. | Determines which fields enter content digests and which are merely caches, display data, or sidecars. |
| Digest | 摘要 | A fixed-length hash value computed over versioned, domain-specific canonical bytes. | Used for content-equality checks, caching, and content addressing; a digest is not a validity certificate. |
| Semantic digest | 语义摘要 | A digest covering semantic content while excluding notation, source locations, and provenance. | Checks equality of semantic interfaces or objects; legacy field names must not imply verified status. |
| Interface digest | 接口摘要 | A digest of the public interface content of a language, assertion, or theory. | Fixes the consumer-facing contract; changing a theorem proof body should not change the theorem interface digest. |
| Implementation digest | 实现摘要 | A digest of the concrete implementation of an interface, such as a theorem interface, proof graph, replay context, and exact dependency requirements. | Identifies a concrete proof implementation while remaining separate from verification policy and result. |
| Verification digest | 验证摘要 | A result identifier computed from an implementation digest and a verification environment lock digest; the latter already covers the assertion profile, trust policy, and verification-protocol version. | Serves as a verification-result cache key or report identifier; it does not replace verification, a digital signature, or a certificate. |
| Verification environment lock digest | 验证环境锁定摘要 | A digest of the canonical contents of a verification environment lock. | Precisely identifies the complete verification-environment requirements for caching, audit, and exchange; the corresponding field may be named `verification_environment_lock_digest`. |
| Domain separation | 摘要域分离 | Use of distinct digest prefixes or namespaces for different object kinds and protocol versions. | Prevents identical bytes in different semantic contexts from being mistaken for the same kind of content. |
| Content-addressed reference | 内容寻址引用 | A reference that locates an object by content digest rather than by mutable path or name alone. | Allows thin artifacts to retrieve exact dependencies and verify that resolved content matches. |
| Cache key | 缓存键 | A stable key used to locate reusable computation results. | May be derived from implementation or verification digests, but cache hits must not bypass required version and trust checks. |

## 11. Layer 7: Exchange, Serialization, and Provenance

This layer defines how proofs are saved, transferred, and reverified as pure data. The English word artifact must be translated by context and has no unconditional one-word Chinese equivalent. Exchange and persistence contexts use 档案, while build and generation contexts use 产物. Here 档案 does not imply that the object must be a file, compressed package, or traditional archive.

| English context | Preferred Chinese | Usage condition |
| --- | --- | --- |
| Unqualified `artifact` | Avoid in Chinese prose | State the object kind or lifecycle explicitly; the word alone does not determine whether an object is an exchange object or a build output. |
| `exchange artifact` / persistent artifact | 交换档案 / 档案 | A versioned pure-data object that can be persisted, transferred, and strictly decoded by another process or implementation. |
| `proof artifact` / `theory artifact` | 证明档案 / 理论档案 | Exchange archives carrying proof content, or theory interfaces, implementations, and dependency information, respectively. |
| self-contained / thin artifact | 自包含档案 / 轻量档案 | Distinguishes whether verification dependencies are embedded or externalized through content-addressed references. |
| `build artifact` | 构建产物 | A reproducible output of compilation, backend conversion, or packaging, such as `.mm`, a source map, or a build report. |
| `generated artifact` | 生成产物 | A generic output of a generation process; if it satisfies the exchange contract of a proof or theory archive, use the corresponding 档案 term instead. |
| artifact envelope / artifact codec | 档案封装 / 档案编解码规范（器） | Reserved for the envelope and codec boundary of exchange archives. |

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Artifact | 按语境使用“档案”或“产物” | A broad software-engineering term for a deliverable object created by people or produced by a development process; its exact meaning depends on lifecycle and consumption boundary. | Chinese prose must not mechanically use 制品 or 工件 and should avoid the unqualified term: exchange objects are 档案, while build outputs are 产物. |
| Proof artifact / Theory artifact | 证明档案 / 理论档案 | Versioned data objects storing a proof, or a theory's interfaces, implementations, and dependency information. | Support cross-process exchange, long-term archival, and independent verification. |
| Serialization | 序列化 | Encoding semantic objects into a byte representation suitable for storage or transfer. | Forms part of the exchange boundary and must not depend on Python `repr`, pickle, or producer-code execution. |
| Codec | 编解码规范 / 编解码器 | The specification and implementation governing encoding, decoding, version handling, fields, and errors. | Ensures that independent implementations produce the same canonical bytes and accept or reject the same inputs. |
| Schema | 数据模式 | A definition of the fields, types, structure, and versions permitted in a serialized object. | Constrains the external shape of an artifact and should not be confused with schema variables in assertions. |
| Wire format / Wire schema | 序列化格式 / 序列化格式规范 | The exact byte and data-structure conventions used across processes or implementations. | Chinese prose should use 序列化格式 rather than literal translations of wire. |
| Envelope / Payload | 外层封装 / 主体数据 | The envelope carries version, object kind, and optional sections; the payload is the enclosed proof or theory content. | Separates file-level metadata from the core mathematical object. |
| Strict decoder | 严格解码器 | A decoder that explicitly rejects unknown versions, missing or extra fields, duplicate keys, malformed identifiers, and over-limit inputs. | Forms the first security boundary when accepting untrusted input. |
| Unchecked packet | 未核验原始数据 | A short-lived internal object produced by strict decoding but not yet subjected to semantic replay or dependency verification. | May circulate only within the decoder pipeline and must never masquerade as a public complete proof. |
| Self-contained / Thin artifact | 自包含档案 / 轻量档案 | A self-contained artifact embeds all dependency content needed for verification; a thin artifact records exact content-addressed references only. | Supports offline verification or external dependency resolution; a thin artifact must be rejected if dependencies are missing or mismatched. |
| Resolver | 依赖解析器 | A component that retrieves exact interfaces or implementations from stable identifiers and content digests. | Supplies content for thin artifacts and theory imports, with returned content checked against the required digest. |
| Canonical JSON | 规范化 JSON | A JSON representation with unique rules for object fields, array ordering, numbers, and string encoding. | Can serve as a readable first exchange encoding and provide a basis for cross-implementation digest agreement. |
| Round trip | 编解码往返 | Encoding, decoding, and re-encoding an object while preserving semantics and, where required, producing byte-identical canonical output. | Tests determinism and losslessness of the codec. |
| Golden vectors | 标准测试向量 | A fixed set of accepted and rejected inputs with expected canonical bytes, digests, or error codes. | Enables independent implementations to reproduce format behavior and serves as a release gate before freezing the exchange specification. |
| Sidecar | 伴随数据 | Additional data associated with a proof or theory through its subject digest but excluded from core semantic content. | Carries source maps, narrative, search scores, timing, and provenance; Chinese prose should use 伴随数据. |
| Provenance | 溯源信息 | Information recording an object's authorship, origin, generation process, tool versions, and build chain. | Supports audit, citation, and reproducibility but normally does not change the proof implementation digest. |
| Source map / Build record | 源码映射 / 构建记录 | A source map links semantic objects to author-source locations; a build record captures build environment and process information. | Supports diagnosis and reproducibility and is normally stored as sidecar data. |
| Digital signature | 数字签名 | A cryptographic signature over deterministic bytes using a key. | Establishes a relation between signer and content and is distinct from an assertion signature, content digest, or verification certificate. |
| Fail closed | 出错即拒绝 | The policy of rejecting input by default on unknown, missing, conflicting, unresolved, or over-limit conditions. | A security principle for loading untrusted artifacts and resolving dependencies. |
| Resource limit | 资源限制 | A hard limit on total bytes, term depth, step count, string length, collection size, and similar resources. | Prevents malformed or malicious artifacts from exhausting memory, CPU, or recursion depth. |

## 12. Layer 8: Backend Execution and Proof Search

Execution representations are derived from complete proofs, while search algorithms are an external control layer over proof states. Neither should contaminate core mathematical objects.

| English term / code name | Preferred Chinese | Definition | Role in the system |
| --- | --- | --- | --- |
| Backend | 后端 | An implementation that consumes backend-neutral semantic objects and produces a system-specific proof, file, or executable representation. | Examples include Metamath output and verification paths; backend details should not enter abstract-language or proof content identity. |
| Lowering | 后端转换 | Transformation of a higher-level backend-neutral object into a more concrete executable or output-oriented backend representation. | Chinese prose should describe it as conversion to a backend representation rather than use a literal translation. |
| Execution representation | 执行表示 | A derived representation with resolved assertion references, linearized steps, and no remaining inference work. | Supports high-throughput verification, Metamath output, or a future VM and should not become a mandatory author-facing object. |
| Replay plan | 重放序列 | An ordered sequence derived from a complete proof for semantic replay or backend conversion. | The current `SemanticReplayPlan` may remain internal and should not be confused with verification itself. |
| Search engine | 证明搜索器 | An external component that selects candidate actions over `ProofState`, maintains branches, and chooses exploration order. | Reuses core transitions and final verification semantics while keeping search strategy outside the proof state. |
| Search frontier | 搜索前沿 | The set of search nodes or proof states awaiting expansion. | Belongs to search scheduling rather than mathematical proof state or final proof content. |
| Candidate action | 候选动作 | An assertion application, substitution, or other refinement request proposed for a goal by the search engine. | Serves as input to a state transition and may be generated by rule indexes, models, or heuristics. |
| Scoring / Ranking | 评分 / 排序 | External strategies assigning values and priorities to candidate actions or search nodes. | Model scores, beam scores, and visit counts must not enter proof semantic digests. |
| Batch transition | 批量状态转移 | An interface that processes multiple candidate actions over one or more proof states in a batch. | Improves search throughput; itemwise results must agree with scalar transitions. |
| State deduplication | 状态去重 | Recognition and merging of search states considered equivalent. | An initial snapshot digest guarantees equal digests for equal canonical bytes but does not automatically define mathematical state equivalence. |
| Alpha-equivalence / Proof equivalence | α-等价 / 证明等价 | Alpha-equivalence ignores renaming of bound variables; proof equivalence is a stronger relation requiring a separate definition. | May support advanced deduplication and analysis but should not enter v1 content identity without evidence of benefit. |
| Normalization | 规范化 | The process of transforming an object into a selected canonical form according to deterministic rules. | Supports comparison, compression, and caching and must state the semantics and version it preserves. |
| Proof repair | 证明修复 | The search for modifications that restore proof validity after dependencies, interfaces, or local steps change. | Builds on structured diagnostics, proof graphs, and search and is not part of the minimal verification kernel. |
| Semantic diff | 语义差异 | A comparison of changes in the canonical semantic content of two proof or theory objects. | Supports review, migration, and repair and is distinct from textual or formatting differences. |
| Dependency minimization | 依赖最小化 | Removal of unnecessary assertion or theory dependencies while preserving proof validity. | Supports audit, publication, slicing, and smaller self-contained artifacts. |

## 13. Expressions to Avoid or Rewrite

| Expression | Preferred wording | Reason |
| --- | --- | --- |
| proof protocol | Use proof object specification, or proof exchange format when serialization is meant. | Avoid using protocol as an undifferentiated umbrella. |
| content identity | State whether this means content equality, a content identifier, or a digest. | The underlying relation must be explicit. |
| nominal identity / nominal ID | 名称标识符 | Do not imply content equality. |
| mental model budget | Public concept limit; or a direct sentence about limiting concepts users must understand. | Prefer direct architectural language. |
| acceptance boundary | Unified validity decision / 统一合法性判定 | Avoid an opaque architectural calque. |
| execution projection | Execution representation / 执行表示 | States the object's role directly. |
| happy path | Default path or ordinary path / 默认流程、常规流程 | Avoid colloquial jargon in normative prose. |
| fail closed | Reject on error / 出错即拒绝 | State the required behavior directly. |
| sidecar | Companion data / 伴随数据 | Avoid a literal vehicle metaphor in Chinese. |
| thin artifact | Thin archive / 轻量档案 | Avoid a literal “thin product” translation. |
| artifact identity | State whether this means archive content equality or an archive digest. | The identity relation must be specified. |
| lowering | Conversion to a backend representation / 后端转换 | Avoid literal Chinese translations such as 降低 or 降级. |
| progressive disclosure | Expose complexity on demand / 按需呈现复杂性 | Prefer a direct statement. |
| low ceremony | Low user burden or concise invocation / 使用负担低、调用简洁 | Avoid translating the metaphor. |

## 14. Maintenance Rules

1. Before adding a new public type to a design document, check whether the concept already exists here.
2. Every new term must include an English name, preferred Chinese name, definition, and role in the system.
3. If a term changes meaning, update this document's version and identify affected APIs, fields, and documents.
4. Code names and natural-language names may differ, but their mapping must be explicit and stable.
5. Mark disputed terms as provisional until frozen. A post-freeze change is a documentation and API compatibility change.
6. This document is organized by conceptual layer. Alphabetical English and Chinese indexes may later be generated from the same terminology data.

## 15. Related Design Documents

- [Reference 011: Language as a First-Class Element](011-language-as-first-class.md)
- [Reference 012: Semantic Definition of Structures, Axioms, and Proofs](012-defining-structures-axioms-and-proofs.md)
- [Reference 013: Proof API for Verification, Construction, Search, and Exchange](013-proof-api-for-verification-construction-search-and-exchange.md)
- [Project 024: First-Class Language Refactor](../projects/024-first-class-language-refactor.md)
