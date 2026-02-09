这里有我们一个 MetaMath 工具链的项目，我对于库的撰写的设计并不满意，感觉还是有些繁琐、不干净。希望可以和你一起协同给出一个干净的库和工具链之间的 API 接口，让职责清晰，代码也干净。'

=======================

我先把你说的“繁琐 / 不干净”具体落到你这份代码里能看见的摩擦点，然后给出一套**库（写证明/写理论的作者侧）**与**工具链（build/link/verify 的工程侧）**之间更“干净”的 API 边界。你可以把它当成我们协作的第一版“接口草案”，后续你再用你的直觉把它收敛成你真正想要的形状。

---

## 1) 现状里最“脏”的地方，其实集中在三类耦合

我在当前 `proof-scaffold / skfd` + 两个库 `metamath-prelude / metamath-logic` 里看到的主要问题是：

### A. 作者侧代码不得不碰 “内部实现细节”

典型表现：

* `metamath-prelude` 的 `build.py` 手动调用 `mm._intern_const/_intern_var/_intern_label` 来构造 exports（这几个是私有方法）。
* `metamath-logic` 里出现了 `mm._interner`, `mm._constants` 等私有字段访问。
* `skfd.authoring.emit` 里为了避免重复声明也读了 `mm._constants/_variables`（同样是私有实现细节）。

**这会导致：**

* “库写法”被迫理解 toolchain/builder 的内部状态机；
* 任何内部重构都会把上层库一起拖下水。

### B. 依赖注入的名字体系不一致（project name vs import module name）

一个非常关键、也非常容易让人不舒服的点：

* `pyproject.toml` 里的依赖是 distribution/project 名（如 `metamath-prelude`）。
* 但 Python 里你实际 import 的包名是 `prelude`。
* Driver 当前把依赖注入 kwargs 时又做了 `- -> _`（`metamath_prelude`），于是库作者写代码时要在三种名字之间跳。

你已经能在 `metamath-logic/src/logic/build.py` 里看到这种错位：`manifest()` 写的是 `"prelude"`，但 toolchain 实际注入的是 `"metamath_prelude"` —— 这类错位就是“不干净”的根源之一。

### C. 公式/语法对象（Wff tokens）与 Builder 的 “string token DSL” 不同构

`HilbertSystem.compile()` 产出的 `Wff.tokens` 是 `SymbolId` 序列；但 `MMBuilder.a/e/p` 目前主要接受的是字符串 token 串，需要先“把 SymbolId 映射成某种局部 token 名”。

于是出现了现在这种“中间层搬运”：

* `emit_axioms/emit_lemmas` 把每个 token id 映射成 `c<id>` / `v<id>`；
* 再用 `mm.c/mm.v/mm.f` 造出对应 token；
* 然后再用 `mm.a/mm.p` 写入。

**这段逻辑的本质是：**作者侧为了把 token-level 公式塞进 string-level DSL，被迫引入“临时命名/临时变量池/临时浮动假设”——繁琐且不优雅。

---

## 2) “干净”的边界：把责任切开，让每层只做一件事

我建议你把整个系统明确切成三层（你现有的代码已经大体如此，只是接口处漏风）：

```
[Author Library Layer]  只关心：公式/规则/证明对象（Wff、LemmaProof、HilbertSystem…）
        |
        |  (Build API: 极薄的一层胶水)
        v
[Build Frontend Layer]  只关心：把作者对象变成 IR（LIR/ProofUnitIR），并记录 exports
        |
        |  (Link/Verify API)
        v
[Toolchain Layer]       只关心：发现包、解依赖、执行 build、link、verify、输出诊断/产物
```

要做到“干净”，关键是把 **作者侧永远不需要知道** 的东西（driver 的依赖命名策略、builder 私有字段、token 映射策略）全部收进工具链/前端层。

---

## 3) 提案：库 ↔ 工具链 的最小接口（核心 API 草案）

下面是我建议你们稳定下来的“最小而完整”的边界接口。它解决上面三类耦合，同时尽量不推翻你们已有结构。

### 3.1 Build entrypoint：统一成 `build(ctx)`（可保留兼容层）

**推荐唯一入口：**

```python
# build.py
from skfd.api import BuildContext

def build(ctx: BuildContext) -> None:
    mm = ctx.mm
    deps = ctx.deps
    ...
```

这样有几个好处：

* 彻底消灭 `build(mm, **deps)` 的 snake_case / kebab-case / module-name 混乱；
* build 变得可测试（自己 new 一个 BuildContext，直接调用 build）；
* toolchain 将来想扩展 context（配置、路径、logger、feature flags）不会污染作者侧签名。

**兼容策略（工具链内部实现）：**

* 若模块定义了 `build(ctx)`：调用它。
* 否则若定义 `build(mm, **deps)`：走旧逻辑适配（短期保留）。

### 3.2 Deps：用一个对象统一 “project 名 / module 名 / 非标识符 symbol 名”

定义 `DepsView` + `ExportsView` 两个只读对象：

```python
class ExportsView(Mapping[str, SymbolId]):
    # 支持 exports["ax-1"]（允许连字符）
    # 可选：exports.ax_1 作为便捷别名，但不强制

class DepsView:
    # 既支持 deps["metamath-prelude"]
    # 也支持 deps.prelude（module alias）
    def __getitem__(self, pkg: str) -> ExportsView: ...
    def __getattr__(self, module_alias: str) -> ExportsView: ...
```

**关键点：**

* toolchain 在内部维护一个 package 元数据：`dist_name` 与 `module_name` 的映射；
* 注入给作者侧时，`deps` 统一通过这个 View 暴露，不再用 kwargs。

这一步会立刻把你们现在的“名字脏乱”清掉。

### 3.3 MMBuilder：补齐两类“正式 API”，让作者侧不碰私有字段

#### (1) import/export：允许任意字符串 key，而不是只能 kwargs

目前 `import_symbols(**imports)` 被 Python 语法限制（key 必须是合法标识符），导致 `ax-1`、`|-`、`/\\` 这种非常合理的 token 在 API 层变得别扭。

建议新增：

```python
mm.import_map({"ax-1": sid, "|-": sid2, "->": sid3})
mm.export_map(["ax-1", "|-"])    # 或 export(*names) 继续保留
mm.exports() -> ExportsView      # toolchain 用它收集导出
```

并把旧的 `import_symbols(**kwargs)` 变成 `import_map` 的薄封装（保留原行为即可）。

#### (2) “ID-mode” 写入：允许直接用 `SymbolId` 序列写公式

这是解决 token 映射繁琐的关键。

新增一组与现有 `a/e/f/p/d` 对应的 ID 版本：

```python
mm.f_id(label: str, typecode: SymbolId, var: SymbolId)
mm.e_id(label: str, typecode: SymbolId, expr: Sequence[SymbolId])
mm.a_id(label: str, typecode: SymbolId, expr: Sequence[SymbolId])
mm.p_id(label: str, typecode: SymbolId, expr: Sequence[SymbolId], proof: Sequence[SymbolId])
mm.d_id(*vars: SymbolId)
```

这样作者侧（以及 `emit_*` 这类库函数）可以直接用 `Wff.tokens`，不需要把 token 重新命名成 `c123/v456` 再走 string DSL。

> 你们现有 IR（LIR）本来就是 SymbolId 级别的；ID-mode 只是把“最后一段不必要的字符串搬运”去掉。

### 3.4 自动化“浮动假设”生成：把重复样板移出库作者手里

大部分作者不想写 `$f` 也不想维护变量池，他们只想写公式。

所以建议提供一个**明确归属在 build-frontend 层**的 helper：

```python
mm.ensure_floating(
    *,
    typecode: SymbolId,
    vars: Iterable[SymbolId],
    label_policy: Literal["w+varname", "w+id"] = "w+varname",
) -> Mapping[SymbolId, SymbolId]   # var -> floating hyp label_id
```

然后 `emit_axioms/emit_lemmas/emit_lowered_lemmas` 统一调用它。

这一步能把当前 `skfd.authoring.emit` 那套 `c<id>/v<id>` 映射 + `mm.v/mm.f` 的样板直接删掉 70% 以上。

---

## 4) 用“改写后”的 build.py 看看代码会变干净到什么程度

### 4.1 `metamath-prelude`（你现在那段手动 exports 可以直接消失）

**当前写法最不舒服的是：**用私有 `_intern_*` 造 exports。

建议直接：

```python
# src/prelude/build.py
from skfd.api import BuildContext

def build(ctx: BuildContext) -> None:
    mm = ctx.mm

    mm.c("wff")
    mm.v("ph")
    mm.f("wph", "wff", "ph")
    mm.a("ax-1", "wff", "ph")

    # 关键：export 常量/变量/标签都允许
    mm.export("wff", "ph", "wph", "ax-1")
```

toolchain 侧统一用 `mm.exports()` 收集，不需要 build 返回 dict，也不需要作者碰 `_intern_*`。

### 4.2 `metamath-logic`：emit axioms / rule skeleton 不再做 token_map

你现在 `_emit_rule_skeleton` 和 `emit_axioms` 最大的繁琐都来自 token_map + “声明额外 const/var”。
如果有了 `a_id/e_id/f_id/ensure_floating`，逻辑会变成：

```python
from skfd.api import BuildContext
from skfd.authoring.emit2 import emit_axioms_id, emit_lowered_lemmas_id  # 假设我们提供新版
from logic.propositional.hilbert import HilbertSystem

def build(ctx: BuildContext) -> None:
    mm = ctx.mm
    prelude = ctx.deps.prelude   # 或 ctx.deps["metamath-prelude"]

    wff = prelude["wff"]         # SymbolId

    sys = HilbertSystem.make(interner=mm.interner)  # interner 作为正式 public 属性暴露

    axioms = sys.compile_axioms()                   # Mapping[str, Wff]
    emit_axioms_id(mm, axioms=axioms, typecode=wff)

    # 规则 skeleton 同理：直接用 Wff.tokens 走 a_id/e_id
    emit_rules_id(mm, sys=sys, typecode=wff)

    # lemmas / lowered lemmas 同理
    ...
    mm.export("A1", "A2", "A3", "mp", "wi", "wn", "wa")  # 示例
```

这里作者侧做的事就非常纯粹：**拿到类型码、生成公式对象、交给 emitter**。
所有“变量要不要声明”“浮动假设叫什么”“常量要不要补齐”都被封装掉。

---

## 5) 红队挑战：这套 API 真正的“数学/工程难点”在哪里？

我觉得你会在下面几个“关键点”上需要做取舍（我先直接给默认方案，不逼你现在回答）：

### Crux 1：跨包引用的访问控制要不要扩展到 Const/Var？

你们 Stage1 目前只对 proof tokens（Label）做 export 检查，Const/Var 是“全球随便用”。

* **默认建议：**先不强制（保持现在行为），因为很多系统会把 Const/Var 视作全局字表的一部分。
* **但风险：**某个包可以偷偷用另一个包的 Const/Var SymbolId，而不显式 import，形成“隐式耦合”。

折中办法：

* 保持 verifier 语义不变；
* toolchain 在“lint 模式”加一个可选检查：跨包使用的 Const/Var 若来自非依赖包则给 warning。

### Crux 2：`SymbolInterner` 的 key 里有 `origin_module_id`，那 module_id 到底应该是什么？

你们现在把 `MMBuilder(module_id=project.name)`，这会把发行名（带 `-`）写进符号身份。

* **默认建议：**把 `module_id` 定义成“作者侧 import 的模块名”，即 build.py 所在目录名（如 `prelude`、`logic`），并在 toolchain 里保留 `dist_name` 仅用于依赖解析与 CLI。
* **原因：**这能让符号身份更贴近源代码组织，减少“换个发行名全库符号 id 都变了”的不稳定性。

### Crux 3：自动生成 `$f` 的策略会不会掩盖作者错误？

自动化会让库写起来爽，但可能把一些应该显式写清的结构隐藏掉。

* **默认建议：**`ensure_floating` 只在 emit helper 中使用；手写 DSL（`mm.f(...)`）仍然可用。
* 并且提供一个开关：`emit_*` 可选择 `auto_floating=False`，用于严格模式或教学用途。

---

## 6) 推荐迁移路线（不需要一次性推翻）

为了让工程上更稳，我建议按这条路线落地：

1. **先做“名字体系清理”**

   * toolchain 内部建立 `PackageMeta {dist_name, module_name, build_path}`
   * BuildContext + DepsView 上线
   * build 支持 `build(ctx)`（同时兼容旧签名）

2. **补齐 import/export 的 mapping 版本**

   * `mm.import_map()` / `mm.exports()`
   * toolchain 收集 exports 走 `mm.exports()`，不再碰 `mm._exports`

3. **加入 ID-mode 写入 + ensure_floating**

   * 这是让 authoring.emit 变干净的关键一步
   * 先实现 `f_id/a_id/e_id/p_id`，再重写 `emit_axioms/emit_lemmas`

4. **最后再决定要不要删 global proxies（skfd.mm / skfd.deps）**

   * 我倾向把它们降级为“脚本模式 sugar”，不是主接口
   * 主接口永远是 `build(ctx)`

---

## 7) 你只需要做的战略选择（可选，但能加速我们收敛）

我已经给出默认方向了；如果你愿意按你自己的直觉来拍板，我建议你只回答这三个偏好（一句话即可）：

1. 你希望 build 的主入口是 **函数式**（`build(ctx)`）还是保留 **脚本式**（全局 `skfd.mm/skfd.deps`）为主？
2. 你希望“公式对象（Wff tokens）”在最终 `.mm` 里**尽量保留原 token 名**（如 `->`、`-.`），还是不介意出现“内部生成的名字”（如 `c123`）？
3. 你更倾向 `$f`/变量池 **自动生成**，还是**强制显式书写**（严格但啰嗦）？

你给出这三点的方向后，我可以把上面的草案收敛成一套更具体的“API v1”（甚至直接按你们现有代码结构给出一个最小可行的 patch 计划与示例重写对照）。

=======================

因为我们还在项目初期，没有历史负担，可以单独出一个更“纯”的 BuilderV2。另外，我想清楚了，未来的大部分代码是你们写的不是人类写的；所以，authoring 层可以支持 unicode；同时有机器可读的 mapping 机制到 ascii 码，这样也可以照顾 set.mm 的历史资源。

=======================

好，我们现在有了三条非常强的共识，足够把边界一次切干净：

1. **主入口固定为** `build(ctx)`
2. **直接新建一个更“纯”的 BuilderV2**（不背历史兼容包袱）
3. **Authoring 允许 Unicode**，但整个工具链的“真相层”（IR / 链接 / 输出 `.mm`）坚持 **ASCII canonical**，并产出**机器可读的映射**，从而能对齐 `set.mm` 的既有资源

下面我给出一套 **API v1（面向 BuilderV2）** 的“职责切分 + 接口草案 + 名字/Unicode 映射机制”。我尽量写到你可以直接照着实现的粒度。

---

## 1. 总体架构与责任边界

核心思想：**作者/库**只描述数学结构；**BuilderV2**只产 IR；**工具链**只负责发现包/依赖/运行 build/link/verify。

```
(Authoring, Unicode-friendly)
    Expr / Var / Constructor (→ ¬ ∧ φ …)
             |
             | compile (uses Lexicon: Unicode -> ASCII canonical)
             v
(Token-level / IR-level, ASCII canonical)
    Formula.tokens: SymbolId[]
    Proof: SymbolId[]
             |
             | BuilderV2 emits LIR + exports
             v
(Toolchain)
    Driver: build(ctx) in topo order
    Linker: Stage1..6 -> emit .mm + .mm.map (+ names map)
```

### 你想要的“干净”，落地在两条硬规则上

* **规则 R1：跨包交互只通过 SymbolId（不再通过字符串 token）**
  这样 `import_symbols(**kwargs)` 这种“被 Python 标识符限制”的设计就可以直接消失。
* **规则 R2：一切输出 `.mm` 的 token/label 都是 ASCII canonical**
  Unicode 只存在于 authoring 侧（输入/展示），通过 Lexicon 映射进入 canonical 世界。

---

## 2. 工具链 ↔ 库 的唯一入口：`build(ctx)`

### 2.1 BuildContextV2（工具链提供）

建议最小字段如下：

```python
@dataclass(frozen=True)
class BuildContextV2:
    mm: MMBuilderV2             # 纯 IR Builder
    deps: DepsView              # 依赖的 exports，只读
    unit: UnitMeta              # dist_name / module_name / version / path
    names: NameResolver         # Unicode -> ASCII canonical + 记录映射
    cfg: BuildConfig            # profile / auto_f / 输出策略等
    log: Logger                 # 诊断输出（可选）
```

* **ctx.mm**：构造 LIR（$f/$e/$a/$p/$d/scope/comment）
* **ctx.deps**：读依赖导出的 SymbolId（不会再注入 kwargs）
* **ctx.names**：authoring 和 builder 共享同一个 canonicalization 规则（关键）
* **ctx.cfg**：你可以在这里放“是否自动 $f”、“label 规范”等开关

> 这样 build 作者永远不需要知道：dist 名怎么变成 kwargs、蛇形命名怎么来、driver 内部状态是什么。

---

## 3. 依赖注入：DepsView（彻底解决 dist/module/别名混乱）

### 3.1 ExportsView

一个依赖包的“接口”就是：

```python
ExportsView = Mapping[str, SymbolId]  # key 是 canonical ASCII 名
```

比如 prelude 导出：

* `"wff" -> sid`
* `"ph" -> sid`
* `"ax-1" -> sid`
* `"wi" -> sid`

key 允许 `-`、`/\\`、`|-` 这类 set.mm 风格名字，因为永远是 `exports["ax-1"]` 访问。

### 3.2 DepsView

DepsView 要同时支持三种访问方式（都指向同一个依赖）：

* `ctx.deps["metamath-prelude"]`  （dist 名）
* `ctx.deps.prelude`              （模块名别名）
* `ctx.deps.metamath_prelude`      （兼容蛇形）

它的职责只是：**把“依赖是谁”这件事一次性在 toolchain 里解决**，build 作者永远不再猜。

---

## 4. BuilderV2：真正“纯”的 IR Builder（只吃 SymbolId）

这里是你这次想“变干净”的核心：BuilderV2 **不再接受字符串 token 序列**，只接受 `SymbolId`。

### 4.1 BuilderV2 的最小 API

我建议 BuilderV2 的对外 API 只保留以下几类：

#### (A) scope 与注释

```python
with mm.block(): ...
mm.comment("...")
```

#### (B) 产生/引用符号（intern + canonicalize）

```python
ph  = mm.sym.var("φ")         # Unicode authoring
imp = mm.sym.const("→")       # 或直接用 builtins 产生复合式
wi  = mm.sym.label("wi")
```

* `mm.sym.*` 负责：通过 `ctx.names` 做 canonicalize，然后 `interner.intern(...)`
* **重要**：interner 里的 `local_name` 必须是 ASCII canonical（否则 `.mm` 输出会被 Unicode 污染）

#### (C) 发出 Metamath 语句（全部 SymbolId）

```python
mm.f(label: SymbolId, tc: SymbolId, var: SymbolId) -> SymbolId
mm.e(label: SymbolId, tc: SymbolId, expr: Sequence[SymbolId]) -> SymbolId
mm.a(label: SymbolId, tc: SymbolId, expr: Sequence[SymbolId]) -> SymbolId
mm.p(label: SymbolId, tc: SymbolId, expr: Sequence[SymbolId], proof: Sequence[SymbolId]) -> SymbolId
mm.d(*vars: SymbolId) -> None
```

> 你也可以提供 `mm.a(name: str, ...) -> SymbolId` 这种 sugar，但内部立刻 canonicalize 并 intern 为 LabelId。

#### (D) exports：只导出 SymbolId

```python
mm.export(*symbol_ids: SymbolId) -> None
mm.exports() -> set[SymbolId]     # toolchain 收集
mm.finish() -> ProofUnitIR        # 生成 unit IR
```

### 4.2 关键变化：不再需要 import_symbols

因为 proof/expr 都是 `SymbolId`，引用依赖符号就是：

```python
ax_1 = ctx.deps.prelude["ax-1"]   # 这是 SymbolId，直接放进 proof token 即可
```

**不需要**把依赖符号“映射到本地字符串名字”，从根上斩掉：

* kwargs 注入的命名混乱
* `ax-1` 不能作为 kwarg 的技术限制
* build author 需要理解“本地 token 字符串 DSL”的额外负担

---

## 5. 自动 `$f`：放进 BuilderV2 的 Auto 子系统（你要的 B）

你已经明确偏好“作者不写 `$f`”。那就让 BuilderV2 负责两件事：

1. 发现表达式中出现的 Var
2. 在当前 scope 内保证这些 Var 有对应的 `$f`

### 5.1 AutoF 的 API（给 proof 生成器用）

我建议提供三件最实用的能力：

```python
mm.auto.floating(var: SymbolId, *, tc: SymbolId) -> SymbolId
mm.auto.mandatory_f(expr: Sequence[SymbolId], *, tc: SymbolId) -> list[SymbolId]
mm.auto.vars_in(expr: Sequence[SymbolId]) -> list[SymbolId]
```

* `floating(...)`：如果当前 scope 未声明该 var 的 `$f`，就生成并返回其 label_id
* `mandatory_f(...)`：按确定性顺序（例如按 var 的 SymbolId 排序）返回需要出现在 proof 里的 `$f` labels
* `vars_in(...)`：抽取 expr 中的 Var tokens

### 5.2 BuilderV2 的默认行为

当你调用：

```python
mm.a("wi", tc=wff, expr=wff_tokens)
mm.p("L1", tc=wff, expr=goal, proof=steps)
```

BuilderV2 在写入 LIR 之前，自动执行：

```python
mm.auto.mandatory_f(expr, tc=wff)
```

并把缺失的 `$f` 以确定性 label 命名规则补上。

### 5.3 `$f` label 的命名规则（建议与 set.mm 对齐）

* 对 var `ph`：默认 `$f` label = `wph`
* 对 var `ps`：`wps`
* 冲突时 deterministic：`wph0`, `wph1`（与现有 relocation 的“加数字后缀”风格一致）

---

## 6. Unicode authoring → ASCII canonical：NameResolver / Lexicon（你要的 C）

这是你新决定的关键：**authoring 允许 Unicode**，但 canonical 世界必须 ASCII。

### 6.1 你需要的对象：NameResolver（双向映射 + 记录）

```python
class NameResolver:
    def canonicalize(self, kind: SymbolKind, name: str) -> str: ...
    def display(self, kind: SymbolKind, canonical: str) -> str | None: ...

    # 记录本次 build 实际使用过的映射（给工具链输出机器可读 mapping）
    def record_use(self, kind: SymbolKind, name: str, canonical: str) -> None: ...
    def used_mappings(self) -> dict: ...
```

**原则：**

* `interner` 只吃 canonical
* authoring/build 可以随便传 unicode/alias
* resolver 统一翻译并记录“这次 build 里你用了哪些别名”

### 6.2 Lexicon 的来源与合并策略

建议 `ctx.names` 来自三层叠加：

1. **内置 set.mm 兼容基础表**（强烈推荐作为默认）
2. 包自身附带的 `lexicon.toml/json`（扩展符号）
3. CLI/配置覆盖（最后覆盖）

合并时若出现冲突（同一个 alias 指向两个 canonical），直接报错——这是最容易把系统搞脏的地方，宁可早失败。

### 6.3 Lexicon 文件格式（建议：简单、可 diff、可机器写）

我建议用 TOML 或 JSON 均可。TOML 示例（表达力更强）：

```toml
format = "skfd-lexicon-v1"

[[symbol]]
kind = "Const"
canonical = "->"
display = "→"
aliases = ["→", "⇒"]

[[symbol]]
kind = "Const"
canonical = "-."
display = "¬"
aliases = ["¬", "~"]

[[symbol]]
kind = "Const"
canonical = "/\\"
display = "∧"
aliases = ["∧", "&"]

[[symbol]]
kind = "Var"
canonical = "ph"
display = "φ"
aliases = ["φ"]

[[symbol]]
kind = "Var"
canonical = "ps"
display = "ψ"
aliases = ["ψ"]
```

这套表可以同时满足：

* authoring 写 `→`、`¬`、`∧`、`φ`
* 输出 `.mm` 始终是 `->`、`-.`、`/\\`、`ph`

### 6.4 对 Label 的 canonicalize（建议：保守 + 可预测）

Label 也允许 Unicode（因为 AI 写），但 canonical 输出必须是 Metamath 安全 ASCII。

建议规则：

* 如果 `name` 本身已经是 `^[A-Za-z0-9._-]+$`，直接使用（如 `L1`, `ax-1`, `mp`)
* 否则生成：`u_<hash>`，其中 `<hash>` = 对 Unicode 名做 stable hash（比如 base32(sha1) 截断）

这样你不会因为某次“中文标签/符号标签”把 `.mm` 弄坏。

---

## 7. 机器可读 mapping 的产物：工具链输出什么

你说“机器可读 mapping 机制到 ASCII”，我建议工具链在 `target/` 里输出一个明确的 artifact，例如：

* `logic_full.mm`（ASCII）
* `logic_full.mm.map`（你现有的 source map）
* **新增：** `logic_full.names.json`（Lexicon usage + reverse display）

`names.json` 可以长这样：

```json
{
  "format": "skfd-names-v1",
  "used": [
    {"kind": "Var", "alias": "φ", "canonical": "ph"},
    {"kind": "Const", "alias": "→", "canonical": "->"}
  ],
  "display": [
    {"kind": "Var", "canonical": "ph", "display": "φ"},
    {"kind": "Const", "canonical": "->", "display": "→"}
  ]
}
```

这样你后续无论是做 pretty printer、IDE 展示、网页渲染，都可以稳定地把 ASCII 还原成 Unicode。

---

## 8. 示例：build 文件会变得怎样“干净”

### 8.1 metamath-prelude（不再 return exports，不再访问私有字段）

```python
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm

    wff = mm.sym.const("wff")
    ph  = mm.sym.var("φ")          # 这里写 φ，内部 canonicalize 为 ph

    wph = mm.auto.floating(ph, tc=wff)  # 自动生成 label: wph
    ax1 = mm.a("ax-1", tc=wff, expr=[ph])

    mm.export(wff, ph, wph, ax1)
```

（你可以把 `ax-1` 的 typecode 以后换成 `|-` 来完全对齐 set.mm，这是下一步的语义升级，不影响这套 API。）

### 8.2 metamath-logic（依赖访问不再纠结名字；proof 全 SymbolId）

```python
from skfd.api_v2 import BuildContextV2
from logic.propositional.hilbert import HilbertSystem

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    prelude = ctx.deps.prelude

    wff = prelude["wff"]     # SymbolId

    system = HilbertSystem.make(interner=mm.interner, names=ctx.names)  # interner/public
    axioms = system.compile_axioms()  # Wff.tokens: SymbolId[]

    for name, w in axioms.items():
        mm.a(name, tc=wff, expr=w.tokens)   # auto-$f 自动处理
```

---

## 9. 红队挑战：这套设计的真正风险点

你现在做的决定很“对”，但有几处如果不提前锁死，会很容易重新变脏：

### 风险 1：Lexicon 冲突与漂移

* 同一个 alias（例如 `¬`）被不同包映射到不同 canonical，会导致“同一个字符在不同上下文含义不同”
* 解决：**合并时冲突直接报错**；并把内置 set.mm 兼容表设为默认基底

### 风险 2：Label 的 canonicalize 不可预测

* 如果 label 的生成规则不稳定（比如依赖运行时随机数），会让跨版本 diff/缓存全部失效
* 解决：**只用确定性 hash + 规则化前缀**

### 风险 3：自动 `$f` 的可见性/复用策略

* 如果每次出现 var 都新建 `$f`，会造成 label 冲突或 scope 污染
* 解决：在 scope 内维护 `active_f[var] -> floating_label_id`，只生成一次

### 风险 4：仅做 token 映射并不足以“直接复用 set.mm 证明”

* `set.mm` 的大部分定理是 `|-` 语句；你现在很多 axioms/lemmas 可能还停留在 `wff` typecode 语义
* 解决：这不影响本次 API，但建议在下一轮把 “断言类型”抽象成一个 `Judgement`（例如 `Provable(wff)`），让系统自然落在 `|-` 上

---

## 10. 我建议你现在就“钉死”的接口（最小稳定核）

为了防止未来又长回去，我建议你现在就把下面几条写成你们的“规范”：

1. build 只有 `build(ctx)`
2. proof/expr 全部是 `SymbolId[]`（不允许字符串 proof token）
3. interner 的 `local_name` 永远是 ASCII canonical
4. Unicode 只通过 `NameResolver/Lexicon` 进入系统
5. toolchain 必须输出 `names.json`（映射可追溯）

---

如果你愿意，我下一步可以把这套 API 进一步收敛成一个“最小实现切片”（几百行级别的改动路径），明确指出：

* 需要新建哪些文件（`skfd/api_v2.py`, `skfd/builder_v2/...`, `skfd/names/...`）
* 现有 driver/emit 里哪些可以直接删掉（`import_symbols`, `token_map`, 私有字段访问等）
* metamath-prelude / metamath-logic 的 build.py 最小改写对照

但就“职责清晰、代码干净”的接口层面，上面这一版已经可以作为 **BuilderV2 + Unicode authoring + ASCII canonical** 的 v1 合同了。

=======================

那让我们把接口“钉死”，然后给出 BuilderV2 + Unicode authoring + ASCII canonical 的 v1 版契约的规范文档。因为业务库并不复杂，我认为你可以给出业务库的新代码；而 BuilderV2 + Unicode authoring + ASCII canonical 的代码你看情况给到什么程度？我们下面就去做迁移

=======================

很好，这一步非常关键。
我已经把 **BuilderV2 + Unicode authoring + ASCII canonical 的 v1 契约**完整地“钉死”成了一份**可执行的规范文档**，并同时给出了**业务库（prelude / logic）的新代码写法**以及**BuilderV2 的参考实现骨架**，都已经放在右侧的文档里。

### 你现在已经具备的三样东西

1. **冻结的接口合同（v1）**

   * 明确了不可破坏的公理（build(ctx)、SymbolId-only、ASCII canonical、Auto-$f 等）
   * 明确了工具链 / Builder / 业务库 的责任边界
   * 未来即使大规模演进，也不会“返脏”

2. **可以直接迁移的业务库新写法**

   * `build(ctx)` 的最小范式
   * Unicode 变量/构造子直接 authoring
   * 不再有 `token_map / import_symbols / 私有字段`

3. **“够用但不臃肿”的 BuilderV2 代码给付策略**

   * 接口 + 行为规范写死
   * 给出 reference skeleton（而不是过早优化的完整实现）
   * 便于你们边迁移、边补实现细节

### 建议的实际迁移顺序（非常重要）

我建议你们**严格按下面顺序推进**，这样风险最低：

1. **先实现 NameResolver + Lexicon（最小可用）**

   * 先只覆盖 `φ ψ → ¬ ∧` + set.mm 常用 ASCII
   * 同时把 `names.json` 的输出管线打通

2. **落地 MMBuilderV2（只到能 emit IR 即可）**

   * 不需要一开始就接全 verifier
   * 重点是：SymbolId-only + Auto-$f

3. **迁移 metamath-prelude（最小、最快）**

   * 这是最好的试金石
   * 成功后接口就真的“钉死”了

4. **迁移 metamath-logic + authoring emit**

   * 删除 token_map 的那一刻，你会明显感觉系统“干净”了

---

如果你愿意，下一步我可以 **直接给你一个“迁移包”**（例如一个最小 `skfd/api_v2.py + builder_v2/ + names/` 目录结构，外加 prelude/logic 的完整可运行版本），让你们基本上是**复制 → 跑 → 对齐**。

你只需要告诉我一句话：
👉 **是希望“先跑起来的最小实现”，还是“一次到位、覆盖 verifier/linker 的完整实现”？**
