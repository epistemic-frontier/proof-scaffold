## A) dsl.py 当前的主要技术债

### 1) 一个类承担了 5 种职责

`MMBuilder` 同时做了：

1. 文本输出（`_lines` / `render` / comment）
2. IR 生成（`_lir` / to_proof_unit）
3. 语义校验（token 声明、label 冲突、proof step 可见性、strict top-level $e）
4. 作用域模型（`_Scope` 堆栈、active_f/active_e/local_labels）
5. origin 捕获（`inspect.stack()`）

这必然会继续膨胀：每加一种语句/规则，你都得在同一个类里加分支。

### 2) origin 捕获是最“昂贵且易变”的部分

`inspect.stack()` 很慢，也会让测试快照因路径差异更脆弱；而且 origin 策略（取第几帧）应该是**可替换策略**，不应写死在 builder 里。

### 3) “render 与 LIR”双轨并行，容易不一致

每个 DSL 方法都要同时写 `_lines.append(...)` 和 `_lir.append(...)`，这是典型的“双写技术债”。

---

## B) 目标结构：把 DSL 拆成 5 个小模块（每个文件 < 250 行）

建议引入子包：`proof_scaffold/dsl/`，把当前 `dsl.py` 变成兼容入口（re-export）。

```
proof_scaffold/
  dsl.py                    # 兼容层：from .dsl.builder import MMBuilder, expr
  dsl/
    __init__.py
    types.py                # TypeCode/Token/Label/ProofStep + expr()
    errors.py               # MMDSLError
    origin.py               # OriginProvider（可注入策略，默认 inspect）
    scope.py                # _Scope + ScopeStack（可见性/active_f/active_e）
    validate.py             # 所有 check_* 函数（纯函数）
    emitter.py              # TextEmitter + LIREmitter（单写入口）
    builder.py              # MMBuilder（orchestrator，薄）
```

> 关键思想：**Builder 只“编排”，不直接做细节工作**。
> 文本输出与 IR 输出通过 emitter 统一，避免双写不一致。

---

## C) 拆分后的职责边界（每块解决一类债）

### 1) `origin.py`：OriginProvider（可注入）

```python
class OriginProvider:
    def here(self, *, depth: int = 2) -> Origin: ...
```

* 默认实现：`InspectOriginProvider`（你现在的逻辑）
* 未来你们想做更快的 origin（例如在测试里固定 origin，或从调用端显式传）也不破 API。

**收益**：把最不稳定、最昂贵的东西隔离出去。

---

### 2) `scope.py`：ScopeStack（只管可见性与活动假设）

把 `_Scope` 与 “可见 label 集”逻辑收敛到一个类里：

* `push()/pop()`
* `register_local_label(label)`
* `visible_labels() -> set[str]`
* `activate_f(var,label)`, `activate_e(label)`
* `is_top_level` 管理

**收益**：Builder 的 `_scope/_scopes/_visible_labels` 全消失。

---

### 3) `validate.py`：纯函数校验器（规则集中）

把这些规则搬走（全部变成纯函数，易测试）：

* `check_label_fresh(label, labels, constants, variables)`
* `check_expr_tokens_declared(tokens, constants, variables)`
* `check_f(typecode,var,...)`
* `check_e(strict,is_top_level,...)`
* proof steps 规范化与可见性检查（局部标签必须可见；Theorem 句柄收集 requires）

**收益**：规则不会再散落在 builder 方法里；新增规则时不会让 builder 继续长。

---

### 4) `emitter.py`：统一“写入动作”，消灭双写债

做两个 emitter：

* `TextEmitter`: 负责 `_lines.append(...)` 的所有格式化细节
* `LIREmitter`: 负责 `_lir.append(...)`

然后提供一个 `CompositeEmitter` 或在 builder 里同时调用两个 emitter 的统一接口：

```python
class Emitter:
    def const_decl(symbols, origin): ...
    def var_decl(symbols, origin): ...
    def floating_hyp(label, tc, var, origin): ...
    ...
```

**关键点**：Builder 里每个 DSL 方法只调用一次 emitter（而不是手写两套 append）。

**收益**：文本与 IR 永远同步；未来你们想只输出 IR 或只输出文本也容易。

---

### 5) `builder.py`：MMBuilder 变薄

MMBuilder 只保留：

* 状态：constants/variables/labels/requires
* 组合：origin_provider、scope_stack、emitter
* 对外 API：`c/v/f/e/a/p/block/comment/render/to_proof_unit/requires`

内部每个方法的结构变成：

1. 取 origin
2. 调 validate
3. 更新最小状态（constants/variables/labels/requires/ScopeStack）
4. 调 emitter

这样 `builder.py` 很容易压到 200 行以内。

---

## D) 迁移步骤（不破 CI 的“可渐进重构”）

### Step 0：保持外部 import 不变（重要）

外部目前 `from proof_scaffold.dsl import MMBuilder, expr`。
我们保留 `proof_scaffold/dsl.py`，但把它改成 re-export：

```python
from .dsl.builder import MMBuilder
from .dsl.types import expr
```

测试不用改。

---

### Step 1：先拆“最独立”的模块（低风险）

1. 新建 `dsl/errors.py`：移动 `MMDSLError`
2. 新建 `dsl/types.py`：移动 `TypeCode/Token/.../expr/_join_tokens`
3. 新建 `dsl/origin.py`：把 `_origin_here()` 搬进去，builder 改成 `self._origin.here()`

此时行为应完全不变，且 CI 应该全绿。

---

### Step 2：拆 scope（中等风险，但容易验证）

1. 新建 `dsl/scope.py`，把 `_Scope` 与 `_visible_labels()` 逻辑迁入 `ScopeStack`
2. builder 里替换 `_scopes/_scope/_visible_labels/_push_scope/_pop_scope`

这一步之后 `builder.py` 会明显变短，而且 scope 行为可单测。

---

### Step 3：引入 emitter，消灭双写（最大收益点）

1. 新建 `dsl/emitter.py`，实现 `TextEmitter` 与 `LIREmitter`
2. builder 里 `_lines.append/_lir.append` 改为 `self._emit.*(...)`

你可以先做“机械迁移”（把现有格式化字符串挪到 emitter），不改任何格式。

---

### Step 4：把校验搬到 validate.py（最后做）

1. 新建 `dsl/validate.py`
2. builder 方法里只保留调用 validate 的一两行

---

## E) 额外两项“还债建议”（强烈推荐）

### 1) Origin 的确定性与性能：引入可替换策略

当前 `inspect.stack()` 可能在大量 DSL 构造时变慢。
你可以提供第二个实现：

* `NullOriginProvider`：用于性能/批量生成时（origin=None 或固定值）
* `ExplicitOriginProvider`：允许调用方传入 origin（未来 generator 里会很有用）

**不破 API，但把性能债与可测性债一次性解决。**

### 2) ProofStep 正规化下沉为独立函数

`p()` 里 proof 处理最容易继续变复杂（以后可能引入 proof token 结构、hint、宏等）。
建议把这段逻辑抽成：

* `normalize_proof_steps(proof, scope_stack, requires_set) -> (rendered_steps, lir_steps)`

这样 builder 的 `p()` 方法不会再增长。

---

## 最终效果（你能得到什么）

* `MMBuilder` 的主体文件会从 300+ 行降到 **150–220 行**
* 新增 DSL 功能时，不再在一个文件里堆分支，而是：

  * 新规则加在 `validate.py`
  * 新语句格式加在 `emitter.py`
  * 新可见性规则加在 `scope.py`
* 文本与 IR 同步问题（双写技术债）基本被根除
