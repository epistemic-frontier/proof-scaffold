# Project 029：目录编译器边界

> 状态：工具链边界规范性裁决（2026-07-21）。
>
> 裁决：规范 repository 名为 **`catalog-compiler`**，名字中不含
> `setmm`。Compiler core 对任何源码格式、基础系统、理论族、公共投影或
> backend 都保持零硬绑定。这些维度只能作为带版本的数据参数，或通过
> 注入的带版本能力协议进入。Set.mm 只是一个 adapter，不是编译器的定义。
>
> 迁移事实：GitHub repository ID `1299890868` 已于 2026-07-21 从
> `epistemic-frontier/partition` 改名为
> `epistemic-frontier/catalog-compiler`。旧名当前重定向到规范 repository；
> 此次改名没有重写 Git 历史。
>
> 规范依据：[Reference 017](../references/017-ontology-first-knowledge-organization.md)、
> [术语规范 000](../references/000-terminology.zh.md)、
> [Project 025](025-semantic-source-surface.zh.md)、
> [Project 026](026-package-evolution-standard.zh.md)、
> [Project 027](027-prelude-boundary-rfc.zh.md) 与
> [Project 028](028-top-level-knowledge-release-units.zh.md)。
>
> 本文中的“必须（MUST）”“不得（MUST NOT）”“应当（SHOULD）”
> 具有规范性含义。

---

## 0. 裁决

Repository 名为 `catalog-compiler`。这个名字表示“编译经治理知识目录的
引擎”，不指向某一个源码语料、某一种基础系统或某一个输出生态。

Compiler core 不得包含源码、基础、理论、投影或 backend 的专用政策。
尤其不得硬编码：

- Metamath 或 Set.mm 的语法、label、源码区域或断言种类；
- 经典、构造、集合论、类型论或其他基础系统；
- Project 028 的十六个 Set.mm 发布单元或任何其他本体；
- Python 模块路径、包名、发布拓扑或发布政策；
- 历史 Transpiler 实现或任何具体 emitter。

所有这类选择只能通过以下两个显式机制之一进入：

1. **带版本的数据参数**，其 schema、标识与摘要记录进编译结果；或
2. **注入的能力协议**，其实现标识、协议版本、声明能力与配置摘要记录进
   编译结果。

缺少版本或能力时必须拒绝。Core 不得猜测默认源码、基础、理论、投影或
backend。

---

## 1. 权威与数据流

通用流程为：

```text
源码字节 + source adapter
             |
             v
         带版本源码清单
             |
catalog + foundation 数据 + theory graph + projection 数据
             |
             v
        catalog-compiler core
          |             |
          |             `-- 注入的 analysis pass
          v
编译后 catalog / release lock / 分析结果
             |
             v
       注入的 backend 能力
             |
             v
生成源码、包、验证工件或其他投影
```

编译器负责计算与校验投影；它不会因此取得发明数学内容的权威。

- Source adapter 负责忠实解码源码并绑定快照。
- Catalog 数据负责已接受的身份、本体、归属、生命周期与投影裁决。
- Foundation 与 theory 数据负责声明解释所依赖的形式假设及其关系。
- Analysis pass 从同一次编译状态导出证据。
- Backend 能力实现编译后的输出，但不得改变 catalog 或 theory 的含义。

规范数据仓与 compiler repository 保持分离。编译器实现本身不是裁决权威。

---

## 2. Core 边界与能力注入

Core 可以提供 schema dispatch、规范编码、摘要校验、图遍历、约束求解、
确定性调度、诊断与 provenance 记录等通用设施。这些设施必须由数据或协议
参数化，不得按名字识别某个语料或输出。

注入的能力协议至少必须声明：

- 稳定能力标识与协议版本；
- 接受的输入 contract 版本和发出的输出 contract 版本；
- 确定性配置及其摘要；
- 所需伴随能力；
- 失败与诊断行为；
- 它属于观察、校验、转换还是发射能力。

Core 必须在执行前校验兼容性。能力发现不得退化为环境中的隐式插件加载：
完整、选定且有序的能力集合是显式编译输入，并出现在结果 provenance 中。

Foundation、theory 与 projection specification 即使有带类型构造器辅助，
本质仍是数据。便利 API 不得把这些值变成进程级全局政策。

---

## 3. Set.mm 只是 Adapter

Set.mm 支持由带版本 adapter 实现。该 adapter 可以了解：

- Metamath scanner、scope、frame、压缩证明与 replay 语义；
- 精确 Set.mm 快照以及包含/排除的源码区域；
- Set.mm 专用 section 提取与 source-inventory 编码；
- Set.mm 声明到稳定 catalog 身份的映射。

这些事实不得泄漏进通用 core 分支或默认值。Set.mm adapter 产生通用
compiler 输入，并在必要时产生带版本的 Set.mm 专用伴随记录。

Project 028 的十六个数学发布单元、Project 027 的 Prelude 边界与 Set.mm
V1 范围都是 adapter/catalog 数据，不是 core 常量。既有
`setmm-catalog-compiler-v1` contract 仍是 Set.mm 专用交换 contract；
它的名字不会把 `catalog-compiler` repository 或 core 改名或专用化。

Mono 可以继续担任 Set.mm source fact 的生产者与校验者。通用 core 依赖
source-adapter contract，不依赖作为具体进程或 Rust crate 的 Mono。

---

## 4. Theory Graph 与逆向数学分析

一次编译可以携带带版本的 theory graph：节点标识 foundation 或 theory，
带类型的边记录扩展、解释、翻译、保守投影或选定实现支持等关系。精确边词汇
属于图的数据 contract；除非由该 contract 提供，否则不得成为硬编码 core
枚举。

逆向数学（reverse mathematics）支持必须是作用于 theory graph 和同一份
规范编译状态的 analysis pass。它不得要求第二个编译器、分叉 catalog 或
源码专用代码路径。因此一次编译可以同时：

1. 校验声明及其选定实现；
2. 为锁定输入构造 theory graph；
3. 在该图上运行逆向数学或证明强度分析；
4. 发出编译后投影以及绑定 provenance 的分析结果。

分析结果是派生证据，不会静默修改 ownership 或 foundation。它必须标识输入
摘要、theory-graph 版本、分析能力/版本、所用假设，以及未解决或不可比较的
情形。分析失败不得伪装成否定的数学结论。

---

## 5. Transpiler 成为 Backend

当前 Transpiler 实现以注入 backend 能力迁入 `catalog-compiler`。其既有
repository 历史是该 backend provenance 的一部分，必须完整保留。

迁移必须保留每一个原始 commit SHA。因此不得使用：

- squash merge；
- 以 rebase 或 cherry-pick 替代原始历史导入；
- `git filter-repo`、`filter-branch` 或其他重写历史的目录迁移；
- 丢弃 ancestry、只提交当前快照的新仓导入。

可以使用 unrelated-history merge 或其他不重写 Git 对象的构造，让原始历史
在目标仓中可达，再以之后的新 commit 完成 backend 集成。历史可达之后移动
文件属于新的普通 commit；这不授权重写早期对象。

Backend 通过能力协议消费显式编译输入。它不得回读 catalog 内部细节、根据
证明次序推断公共 ownership，或让 backend 默认值变成 compiler-core 政策。
既有 `mm-transpiler` distribution、import、CLI、manifest 与 policy 名都作为
兼容 contract 保留，直到另行版本化迁移取代它们。

---

## 6. Partition 工件是历史兼容层

原 partition repository 建立了有价值的实证证据、proof-graph 格式、plan-v3
压力测试、生成器、报告与 API。这些工件作为可复现历史和兼容输入继续存在，
但它们不再命名新 compiler 的规范抽象。

在 `catalog-compiler` 中：

- 历史报告与生成工件保留原名；
- `proof-partition-*`、`mm-partition-domain-v1`、`mm_partition` 与
  `mm-partition` CLI 不作机械改名；
- 下游迁移期间可以保留兼容命令；
- partition 指标可以服务 analysis pass 或诊断；
- partition 输出不得决定公共数学 ownership，也不得成为隐式 core 默认值。

未来若移除兼容表面，必须先有显式 consumer inventory、替代路径、弃用周期与
可复现方案。

---

## 7. 名字与 Repository 映射

冻结的 repository/component 映射为：

| 名字 | 角色 |
| --- | --- |
| `catalog-compiler` | 通用 compiler repository 与组件；对源码、基础、理论、投影、backend 零硬绑定 |
| `setmm-catalog` | Set.mm 规范 catalog 数据与 schema |
| `setmm-review` | Set.mm 非规范 review campaign 与裁决工作区 |
| Mono | Set.mm source-plane 实现及 source-adapter 生产/校验者 |
| Transpiler backend | 完整历史迁入 `catalog-compiler` 的 backend 能力 |
| partition 兼容层 | 历史研究、工件、schema 与临时下游兼容 API |

Repository 名、软件 distribution 名、Python import root、CLI entry point 与
machine contract 标识是五类不同名字。Repository 改名不会自动改名其余四类。
迁移期间文档必须显式说明映射。

GitHub repository ID `1299890868` 现在的规范名字是
`epistemic-frontier/catalog-compiler`。原
`epistemic-frontier/partition` 名是 redirect，不是规范 URL。活跃文档必须
使用规范 URL；历史证据链接应指向规范 repository 并固定原始 commit SHA，
不得长期依赖 redirect。

---

## 8. 最后归档迁移门

旧 Transpiler repository 必须最后归档。在以下所有门通过前，它保持可用且
不归档：

1. **Ref 清单：**记录旧仓所有 branch、tag、默认分支 HEAD 及其 SHA。
2. **对象保全：**清单中的每个原始 commit SHA 都在 `catalog-compiler` 中
   可达，完整对象一致性检查通过。
3. **文件树映射：**旧默认分支源码树到导入 backend 树有显式、可评审映射，
   不存在无法解释的文件丢失。
4. **构建与测试等价：**导入 backend 在目标仓通过原有完整 test、lint、type
   与 build 门。
5. **行为等价：**锁定 fixture 产生等价的生成源码、manifest、摘要与验证结果；
   仅允许显式裁决的路径/provenance 变化。
6. **能力集成：**通用 core 只通过声明协议调用 backend；负例证明缺失或不兼容
   能力会被拒绝。
7. **运行切换：**CI、issue/PR 引用、发布说明、安全 ownership 与规范文档均
   指向目标仓，同时保留已记录的回滚路径。
8. **独立审计：**由独立评审者确认 ref manifest、可达性、验收门与目标 URL。

只有 G1–G8 全部通过，旧仓才能改为只读并归档。归档绝不是迁移前提，也不得用来
强迫切换。归档仓 notice 必须指向目标仓并说明历史保全边界。

已完成的 partition→`catalog-compiler` 改名不等于归档。以后若退休其历史
兼容表面，同样适用最后归档原则：先完成兼容迁移，再做退休，历史证据通过
原始 commit SHA 保持可达。

---

## 9. 验收门

Project 029 只有满足以下条件才算完成：

| 门 | 要求 |
| --- | --- |
| C1 | Core 测试证明通用编译中不存在 Set.mm/源码、foundation、theory、projection 或 backend 默认值 |
| C2 | 每个选定数据 contract 和 capability/version 都进入确定性 provenance |
| C3 | Set.mm 垂直切片只通过 adapter 边界运行，并复现冻结的 inventory/catalog lock contract |
| C4 | 同一次编译构造 theory graph，并运行绑定 provenance 的逆向数学 analysis pass |
| C5 | Transpiler 历史通过全部最后归档门，每个原始 commit SHA 均被保留 |
| C6 | 导入的 Transpiler backend 在锁定 fixture 上行为等价，并隔离在能力协议之后 |
| C7 | 旧 partition 工件保持可复现，但不能决定公共 ownership 或通用默认值 |
| C8 | 活跃中英文档对 repository、component、contract、兼容与归档状态表述一致 |

功能测试通过但丢失 Git 历史，C5 仍失败。保留 Git 对象但绕过 backend 协议，
C6 仍失败。只是在表面套一层通用 API 的 Set.mm-only core，C1 仍失败。

---

## 10. 实施顺序

1. 在 Project 029 与术语规范 000 中冻结本术语和边界。
2. 清点 partition 与 Transpiler repository、distribution、import、CLI、schema
   和 URL 的活跃消费者。
3. 记录并验证已完成、未重写历史的 GitHub 改名：repository ID
   `1299890868` 对应 `epistemic-frontier/catalog-compiler`，旧名保持 redirect，
   partition 兼容表面继续可用。
4. 引入通用带版本输入与能力协议，把 Set.mm 专用行为移到 adapter 之后。
5. 增加 theory-graph 构造与 analysis-pass 接口，在同一次编译中演示一个
   逆向数学 pass。
6. 清点并导入完整 Transpiler Git 历史；不得 squash、rebase、filter 或替换 SHA。
7. 把 Transpiler 集成为 backend，并通过等价性、能力与 provenance 门。
8. 在旧仓仍未归档时，把活跃文档与 CI 切换到目标仓。
9. 完成独立的最后归档审计。
10. 只有全部门通过后才归档旧 Transpiler repository。

每一步都必须留下可运行、可恢复状态。后续步骤不能追溯授权前面步骤重写历史。

---

## 11. 与 Projects 025–028 的关系

- Project 025 继续规范生成语义源码表面、惰性详化、frame equivalence 与
  backend 发射行为。Project 029 取代“单个 partition 结果有权决定公共模块
  ownership”的解释，并把 Transpiler 实现迁到 backend 协议之后。
- Project 026 继续规范 definingness、稳定迁移、依赖完备性、可复现性，并保留
  已记录的 partition 实验。它此前的 repository 交接是历史记录。
- Project 027 继续规范 Prelude 内容边界与 capability-slice 迁移原则。该边界是
  Set.mm foundation/catalog 数据，不是 compiler-core 常量。
- Project 028 继续规范十六个 Set.mm 数学发布单元及一根一发布拓扑。该拓扑是
  带版本 Set.mm projection 输入，不是通用 core allowlist。

Project 029 改变工具边界与迁移机制，不重开 Projects 027–028 的数学裁决。

---

## 12. 非目标与延后事项

本项目不：

- 选择一个普适本体或基础；
- 声称每个源码系统已经能提供全部可选能力；
- 在带版本 contract 之外冻结普适 theory-graph 边词汇；
- 定义逆向数学分析应得出的具体数学结论；
- 改名冻结的历史 schema、CLI、package 或生成工件；
- 授权删除任一旧 repository；
- 裁决 mathbox ownership、成熟度或晋升。

未来协议版本可以增加能力，但不得削弱零硬绑定规则、provenance 要求、保留 SHA
的迁移或最后归档门。

---

## 13. Provider Layout V1 边界（2026-07-21）

迁移后的第一个 semantic-package contract 是 `provider-layout-v1`。其规范
schema 与 validator 位于 `catalog-compiler`，但 `CompilerSpec` 与通用 core
都不 import 或构造它。Semantic-package backend 只能把它作为显式、绑定摘要
的参数接收。

该 contract 把五类事实正规化并保持分离：

1. 带版本的 compiled subject contract 与摘要；
2. 公共表面，以及各自不透明的公共 owner 与目标产物；
3. 物理 provider shard，以及各自不透明的 provider、目标产物与精确直接
   shard requirements；
4. 选定实现身份、实现摘要与带类型目标入口；
5. 每个声明到一个公共表面和一个选定实现的精确 binding。

通用 contract 把 owner、provider、artifact、declaration、implementation、
shard 与 entrypoint 标识全部视为不透明值。目标专用入口只能由显式选定、
带版本的 companion validator 解释。基础 schema 不得出现 source label、
assertion kind、source ordinal、Python path、distribution name、固定 release
registry、Prelude 默认值或 proof-format 词汇。

只通过 schema 仍不充分。Consumer 必须注入 authority context，提供精确的
subject 摘要、公共表面、选定实现与摘要、声明 binding、provider/artifact
权威与直接实现依赖关系。Endpoint validator 是独立显式 mapping，其 key 集
必须与 layout 实际使用的 contract 集完全相等。Layout 本身把实现指派给物理
shard。Validator 把 authority 提供的实现图折叠到 shard 后，声明边与所得直接
边必须完全相等；缺边和多余边都拒绝。Shard、provider quotient 与目标
artifact quotient 图都必须无环。

Authority facts 有自己的带版本 contract 与规范 content digest，并与 authority
producer 的 capability ID、protocol version 和 configuration digest 分开记录。
Endpoint validator 同样暴露带版本、绑定配置的 descriptor。成功结果对 layout、
authority descriptor 与精确 endpoint descriptor 集计算 validation-provenance
digest；它只是 cache／provenance key，不是 Manifest V3 或 verification certificate。

`provider-layout-v1` 不选择 provider、不优化 shard 边界，也不从 proof order
推断公共 ownership。发现环时必须先裁决 shard 合并或分阶段，或抽取真正接口；
不得借此把公共声明移给另一个 owner。V1 只验证给定 shard projection，不证明
某个合并或分阶段选择已经过裁决；production producer 必须在 provenance 中显式
记录 shard-projection capability 与 configuration digest。

对于 Set.mm V1，compiled lock 的 `provider` 仍只是 release 级选择，`module`
仍是公共 facade。Physical shard、generated path 与 implementation entrypoint
不得进入 `knowledge-release-lock-v1` 或 declaration-placement attestation。
后续 Set.mm authority companion 以声明 UUID 连接 snapshot-matched Mono graph
与精确 proof/replay facts，再把物理裁决作为显式数据提供。

本节不冻结 production Set.mm provider layout。当前 catalog 只是四声明的
partial governance sample，这些证明依赖 partial lock 之外的声明，而已有 corpus
graph 与 catalog pin 的 snapshot 不匹配。因此禁止虚构 shard ID，也禁止把历史
public-module plan 当成实现位置。

本阶段验收门为：

| 门 | 要求 |
| --- | --- |
| PL1 | 通用 schema 与 validator 不含 Set.mm、固定 release、Python、foundation 或 backend 默认值。 |
| PL2 | RFC 8785 摘要、规范顺序、唯一性与全部引用均 fail-closed 校验。 |
| PL3 | Authority join 要求声明、owner、选定 provider／implementation、artifact、entrypoint 与实现摘要精确一致；authority facts 还必须独立内容寻址。 |
| PL4 | 声明 shard requirements 与直接跨 shard 实现 quotient 完全相等；缺边和多余边都失败。 |
| PL5 | Shard、provider 与目标 artifact quotient 均无环。 |
| PL6 | 未知或不带版本的 endpoint contract 不得 ambient discovery；精确 authority 与 endpoint capability descriptor 必须绑定进 validation provenance。 |
| PL7 | Set.mm catalog、placement 与 knowledge-release lock schema 保持不变，并显式记录 physical-layout 边界。 |
| PL8 | 测试使用 synthetic 非 Set.mm authority context；规范数据中不出现虚构 production shard。 |

Generated-tree ownership、manifest V3、trust/foundation closure、原子发布与独立
verification receipt 仍是后续相邻 contract。有效 provider layout 是发布 semantic
package 的必要但不充分条件。
