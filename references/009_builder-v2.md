# BuilderV2 v1 契约规范

> **状态**：冻结（v1）
>
> **目标**：在项目早期一次性钉死接口边界，使业务库只表达数学结构；BuilderV2 只产 IR；工具链只负责调度、链接、校验与产物输出。
>
> **后续解释**：全局 foundation scope 与 package/export 分类见
> [010-foundation-scope.md](010-foundation-scope.md)。

---

## 0. 设计公理（Invariants）

**I1. 单一入口**：所有业务库仅暴露 `build(ctx)`。

**I2. 单一事实层**：跨包交互只通过 `SymbolId`（不再通过字符串 token）。

**I3. 规范化输出**：`.mm` 输出与 IR **始终 ASCII canonical**。

**I4. Unicode 只在写作层**：通过 `NameResolver/Lexicon` 进入 ASCII 规范命名空间，并生成**机器可读映射**。

**I5. 自动 `$f`**：默认开启；作者侧不写 `$v/$f` 样板。

**I6. 冻结 API**：v1 内不破坏以下接口；演进只增不改。

---

## 1. 术语

* **SymbolId**：符号唯一标识（Const/Var/Label/Typecode）。
* **Canonical Name**：ASCII、Metamath 安全的 `local_name`。
* **Alias / Display**：Unicode 或其他别名，仅用于写作和展示。
* **IR（LIR/ProofUnitIR）**：工具链消费的中间表示。

---

## 2. BuildContextV2（工具链 → 库）

```python
@dataclass(frozen=True)
class BuildContextV2:
    mm: MMBuilderV2
    deps: DepsView
    unit: UnitMeta
    names: NameResolver
    cfg: BuildConfig
    log: Logger
```

**约束**：业务库不得绕过 `ctx` 访问任何全局或私有状态。

---

## 3. DepsView / ExportsView（依赖访问）

```python
ExportsView = Mapping[str, SymbolId]  # key 为 canonical ASCII 名

class DepsView:
    def __getitem__(self, key: str) -> ExportsView: ...   # dist 名
    def __getattr__(self, key: str) -> ExportsView: ...   # module 别名 / snake_case
```

**保证**：`ctx.deps[dist]`、`ctx.deps.module`、`ctx.deps.snake` 指向同一依赖。

---

## 4. NameResolver / Lexicon（Unicode → ASCII）

### 4.1 职责

* 将写作层的 Unicode/别名**规范化**为 ASCII 规范名称。
* 记录**本次 build 使用过的映射**，供工具链输出 `names.json`。

### 4.2 API

```python
class NameResolver:
    def canonicalize(self, kind: SymbolKind, name: str) -> str: ...
    def display(self, kind: SymbolKind, canonical: str) -> str | None: ...
    def record_use(self, kind: SymbolKind, alias: str, canonical: str) -> None: ...
    def used_mappings(self) -> dict: ...
```

### 4.3 Lexicon 合并顺序（从低到高）

1. 内置 set.mm 兼容表（默认）
2. 包内 `lexicon.toml/json`
3. CLI / 配置覆盖

**冲突策略**：冲突即报错（早失败）。

### 4.4 Label 规范化

* 若 `^[A-Za-z0-9._-]+$`：原样使用。
* 否则：`u_<stable_hash>`（确定性）。

---

## 5. MMBuilderV2（纯 IR Builder）

> **只吃 `SymbolId`，不吃字符串 token。**

### 5.1 符号生成（带规范化）

```python
class SymFacade:
    def const(self, name: str) -> SymbolId: ...
    def var(self, name: str) -> SymbolId: ...
    def label(self, name: str) -> SymbolId: ...

class MMBuilderV2:
    sym: SymFacade
    interner: SymbolInterner
```

### 5.2 语句发射（ID 级）

```python
mm.f(label: SymbolId, tc: SymbolId, var: SymbolId) -> SymbolId
mm.e(label: SymbolId, tc: SymbolId, expr: Sequence[SymbolId]) -> SymbolId
mm.a(label: SymbolId, tc: SymbolId, expr: Sequence[SymbolId]) -> SymbolId
mm.p(label: SymbolId, tc: SymbolId, expr: Sequence[SymbolId], proof: Sequence[SymbolId]) -> SymbolId
mm.d(*vars: SymbolId) -> None
```

### 5.3 Scope / 注释 / 导出

```python
with mm.block(): ...
mm.comment(text: str)
mm.export(*symbols: SymbolId)
mm.exports() -> set[SymbolId]
mm.finish() -> ProofUnitIR
```

---

## 6. Auto-$f（默认开启）

### 6.1 API

```python
class Auto:
    def floating(self, var: SymbolId, *, tc: SymbolId) -> SymbolId
    def use_existing_floating(self, var: SymbolId, *, label: SymbolId) -> SymbolId
    def mandatory_f(self, expr: Sequence[SymbolId], *, tc: SymbolId) -> list[SymbolId]
    def vars_in(self, expr: Sequence[SymbolId]) -> list[SymbolId]
```

### 6.2 规则

* 在当前 scope 内，**同一 var 只生成一次 `$f`**。
* `$f` label：`w{var}`；冲突则 `w{var}0, w{var}1...`（确定性）。
* `mm.a/mm.p` 在写入前自动补齐缺失 `$f`，但默认推断只适用于
  typecode canonical name 为 `wff` 的 syntax assertion。
* `|-` theorem 的 wff mandatory variables 必须通过已有 foundation `$f`
  或 proof 后端转换的 `floating_by_var` 显式提供；BuilderV2 不会从 `|-`
  typecode 推断出 `wff` floating hypotheses。

### 6.3 与 foundation `$f` 的关系

Auto-`$f` 是普通作者侧的局部便利；foundation-owned `$f` 是全局
foundation frame 的一部分。普通包如果显式使用 `metamath-prelude` 提供的
schema variables 和 `$f` labels，应先调用
`mm.auto.use_existing_floating(var, label=...)` 注册已有 foundation `$f`，
避免生成第二套同义 floating hypotheses。访问控制和 scope emission 以
`010-foundation-scope.md` 为准。

---

## 7. 构建产物

* `*.mm`：ASCII canonical
* `*.mm.map`：source map
* `*.names.json`：Unicode ↔ ASCII 映射（机器可读）

```json
{
  "format": "skfd-names-v1",
  "used": [{"kind":"Const","alias":"→","canonical":"->"}],
  "display": [{"kind":"Const","canonical":"->","display":"→"}]
}
```

---

## 8. 业务库示例（新代码）

### 8.1 prelude/build.py

```python
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm

    wff = mm.sym.const("wff")
    ph  = mm.sym.var("φ")           # Unicode 写作输入

    mm.auto.floating(ph, tc=wff)
    ax1 = mm.a(mm.sym.label("ax-1"), tc=wff, expr=[ph])

    mm.export(wff, ph, ax1)
```

### 8.2 logic/build.py

```python
from skfd.api_v2 import BuildContextV2
from logic.propositional.hilbert import System

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    prelude = ctx.deps.prelude

    wff = prelude["wff"]
    system = System.make(interner=mm.interner, names=ctx.names)

    for name, w in system.compile_axioms().items():
        mm.a(mm.sym.label(name), tc=wff, expr=w.tokens)
```

---

## 9. 参考实现骨架（用于迁移）

> **目的**：给到“能跑”的最小实现，便于迁移；不是最终性能实现。

```python
class MMBuilderV2:
    def __init__(self, interner, names, cfg): ...
    def a(self, label, tc, expr): ...  # 内部调用 auto.mandatory_f
    ...

class NameResolver:
    def canonicalize(self, kind, name): ...
```

（完整骨架建议由工具链仓库提供，业务库仅依赖接口。）

---

## 10. 迁移清单（Checklist）

* [ ] 业务库改为 `build(ctx)`
* [ ] 移除 `import_symbols(**kwargs)` / `token_map`
* [ ] proof/expr 全部改用 `SymbolId`
* [ ] 启用 `Auto-$f`
* [ ] 接入 `NameResolver/Lexicon`
* [ ] 工具链输出 `names.json`

---

**结论**：以上即为 BuilderV2 + Unicode 写作层 + ASCII 规范表示的 v1 冻结契约。任何新功能必须在不破坏上述公理的前提下演进。
