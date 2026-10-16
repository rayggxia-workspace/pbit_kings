# p-bit circuit project rules

## 2026-10-17 工作区接入更新（优先于下文历史状态）

- 用户确认本人为 `jieruiz`；本机已保存凭据经 GitHub `/user` 核实为 id `169070146`，未使用其他 connector 身份写入。
- 用户明确授权新建公开仓库 `rayggxia-workspace/pbit_kings`，现已创建。原 `jieruiz/pbit_kings` 保留；禁止向 LLM 仓库混入电路。
- 迁入任务为 https://github.com/rayggxia-workspace/pbit_kings/issues/1 ，负责人 jieruiz；分支 `task/1-import-chimera`，独立目录 `pbit_kings_workspace`。
- 源基线 `pbit_chimera` / `b2c0e774f03b5a7ec205f269e2170344df2139bd`，迁入该分支已跟踪文件及祖先历史；其余分支保留源库。本目录未跟踪 EDA/PDK/大产物不自动上传。
- 本次已读取组织管理规范、通用协作 Skill 1.0.0、模板、状态及相关 Issue/PR。项目根 AGENTS 同时保留硬件专项规则；数据需记录版本、配置、位置、SHA-256。
- 个人状态在目标仓库 `progress/jieruiz/STATUS.md`，辅助资料在 `work/jieruiz/1/`。开始/恢复先读取最新 Issue、PR 和交接。
- 当前仅仓库和 Issue 已建立，代码迁入/PR/登记/看板以目标 STATUS 与远端实际状态为准；不得依据本历史文件宣称已合并或已签核。
- 下文 2026-10-16 的“未建立目标仓库”等属于历史记录，不再代表当前资源状态；原有技术、协作和安全规则继续有效。

本文件适用于本仓库中的 p-bit King/Chimera RTL、testbench、综合、门级/后仿、PrimeTime 功耗与时序、Innovus/APR、FPGA 及相关文档任务。子目录存在更具体的 `AGENTS.md` 时，同时遵守；冲突时以更深目录且不违反本文件安全与协作要求的规则为准。

当前工程入口沿用 `README.md`：可综合 RTL 位于 `rtl/`，板级顶层位于 `top/`，仿真位于 `sim/` 及任务专用测试目录，说明材料位于 `docs/`。`vivado_project/` 是历史工程参考，其中路径可能仍指向原始目录，不得仅凭 `.xpr` 存在就宣称当前源码已通过 Vivado 重建。

## 1. 项目、身份与迁移状态

- 当前有效本地 Git 根为 `pbit_chimera_pipeline_20260920/`。截至 2026-10-16，本地分支为 `pbit_chimera`，本地与远端分支头均为 `b2c0e774f03b5a7ec205f269e2170344df2139bd`。
- 当前 `origin` 为历史个人仓库 `jieruiz/pbit_kings`。计划协作空间为 GitHub 组织 `rayggxia-workspace`，但核实时该组织尚无 p-bit 电路目标仓库，只有 `rayggxia-workspace/pbit-llm-qwen-baselines`；不得把电路代码误推到该 LLM 仓库。
- 本人 GitHub 身份为 `jieruiz`（GitHub id `169070146`）。本机 `git config user.name`、提交作者、remote owner 或用于读取资料的 connector 账号均不能单独代替登录身份核实。
- workspace 仓库建立后，必须记录其准确 `owner/repository`，添加明确命名的 remote（建议 `workspace`），核对写权限、默认分支、保护规则及 Issue/Projects 权限，再开始迁移或发布。
- 本文件当前只是本地规则安装。没有对应的 workspace 电路仓库、Issue、任务分支或 PR，因此不得描述为已上传、已迁移、已合并或已同步看板。首个迁移 Issue 建立后，应把本文件纳入该 Issue 的任务分支和 PR。

## 2. 开工前检查

- 每次开始、恢复、上传或交接前，确认实际 Git 根、当前分支、工作树改动、所有 remote URL、远端最新提交，以及实际 GitHub 登录用户名。
- 读取目标仓库最新的 `README.md`、根/子目录 `AGENTS.md`、`CONTRIBUTING*`、协作模板、项目状态索引和任务相关文档。默认分支不一定包含最新硬件版本，应确认任务指定分支和准确 commit。
- 查看最新 Issue、关联 PR、评审讨论、`progress/*/STATUS.md` 与 `work/*/*/HANDOFF.md`，确认负责人、文件范围、接口、依赖和其他成员进度，避免重复开工。
- 当前 checkout 含大量未跟踪的 DC、PT、APR、后仿和功耗资料。不得把这些资料视为待自动提交内容，不得使用无范围的 `git add .`，不得为“清理”而删除或覆盖它们。

## 3. 一项任务对应一个 Issue

- 一项可独立验收的任务对应一个 Issue。已有同范围 Issue 时接续原 Issue，不重复创建。
- Issue 必须明确负责人（GitHub username/assignee）、目标仓库和 base、范围、非目标、修改目录、依赖、风险及可检查的验收标准。
- RTL 功能、约束、综合、时序、功耗和物理实现若属于同一交付，可以在同一 Issue 下列独立清单；无共同验收边界的工作应拆分 Issue。
- 发现与其他成员范围重叠时，先在 Issue 中记录分工、接口和采用的基线提交，不覆盖他人文件或擅自接管任务。
- Issue/看板无权限时，完成其余可执行工作，并在 STATUS、PR 和交接中写清阻塞与待同步项；不得虚报 Issue 或看板已更新。

## 4. 独立分支与工作目录

- 每个 Issue 使用独立分支，例如 `task/<Issue编号>-<简短名称>`，并在 Issue/STATUS 中记录基线 SHA、目标 PR base 和工作目录。
- 并行成员或 Codex 必须使用独立 clone、checkout 或 Git worktree。不得在同一目录共享未提交状态、来回切换任务分支或覆盖其他任务生成物。
- 不重置、清理、强制推送、删除、搬移他人的工作树、分支、日志或结果。依赖未合入任务时，记录依赖分支和准确 commit。
- 该混合资料 checkout 很脏时，正式修改优先在从已核实基线创建的独立 worktree 中完成；现有未跟踪资料只读使用，并以 manifest 引用。

## 5. 个人进度与任务资料

- 个人进度维护在 `progress/<本人GitHub用户名>/STATUS.md`，当前用户名为 `jieruiz`。其他成员的 STATUS 默认只读。
- STATUS 至少记录更新时间、负责人、Issue、目标仓库、分支/PR/base、工作目录、当前阶段、修改范围、实际验证、成果位置、阻塞/待同步和下一步可执行动作。
- 明确区分“本地已完成”“已提交”“已推送”“PR 待审”“已合并”“远端作业已完成”；后一个状态不能由前一个状态推断。
- 任务辅助资料放在 `work/<本人GitHub用户名>/<Issue编号>/`，包括核实记录、命令、配置、manifest、验证和交接。
- 正式 RTL、testbench、约束、流程脚本、文档和小型结果遵循项目正式目录，不把最终实现藏在个人 `work/` 中。

## 6. 硬件修改与验证

- RTL 修改前确认顶层、参数、时钟/复位、跨时钟域、UART/配置协议、流水线延迟、随机种子、边/偏置比较语义和 snapshot/readout 协议。
- 改流水线或周期数时同步更新 testbench、软件/oracle 模型、接口文档和时序约束；不能只凭单个 PASS marker 宣称算法与 RTL 对齐。
- 功能验证按风险覆盖普通读写、边界地址/非整 bank、配置写入、运行/停止/恢复、snapshot 完整读出、固定种子逐轮对比、X/Z、复位和错误恢复。
- 门级/后仿必须记录网表、SDF/SPEF、标准单元/IP 模型、corner、时间精度、SDF annotation/coverage、timing check 设置和实际日志。`+notimingcheck` 通过只证明功能，不证明时序通过。
- DC/PT/Innovus 报告区分 setup/hold、理想/传播时钟、wire-load/RC、PVT、MMMC view、活动率来源和未约束路径；DC 通过不能代替布局后 STA。
- 功耗结果记录测量窗口、频率、电压、温度、活动来源、read/write/更新次数、内部/开关/漏电、PLL/PAD/CTS/SRAM 是否包含及归一化公式。估算、库表、门级活动功耗和硅片实测不得混称。
- APR/物理结果记录输入网表/SDC/库/LEF/RC corner、阶段数据库、DRC/connectivity/antenna、PG 连接、SDF/SPEF 版本和报告。初步 floorplan 或工具零 error 不等于签核完成。
- 只运行与改动相称的验证，但必须列明未运行项及原因；引用历史 PASS 时给出其提交、配置和日志，不写成本次重跑。

## 7. 数据、版本和受限资料

- 实验和 EDA 结果必须记录代码 commit（含未提交补丁，如有）、脚本/约束配置、RTL/网表/SDF/SPEF/库版本、PVT、工具版本、种子、完整命令、作业 ID、成果位置和 SHA-256。
- 对输入归档和关键输出按原始字节计算 SHA-256。已有校验和后不得为换行、格式或压缩方式重写文件而仍沿用旧散列。
- 大型网表、波形、数据库、工艺结果、权重和数据集使用项目约定的共享存储；Git 只提交允许公开的小型代码、配置、manifest、索引和汇总。
- 未确定共享存储时，保留在现有授权位置并记录待迁移，不擅自上传公共 GitHub。
- 不提交凭据、token、SSH 配置、许可证、完整 PDK/工艺库、受 NDA 限制的 IP、厂商模型或未获授权的论文/数据。公开仓库中的路径和报告也应避免泄露受限服务器结构或个人信息。

## 8. 上传与 PR 交付

- 上传前再次核对 GitHub 登录身份、目标仓库、remote、任务分支、PR base、Issue、提交差异和精确文件清单。
- 只暂存 Issue 范围内的文件；尤其不得把当前 checkout 中未跟踪的后端包、日志、库或大结果随手提交。
- 通过任务分支和 PR 交付，关联 Issue，写明问题、最终修改、实际验证命令及结果、未运行项、限制、数据/成果位置和 SHA-256。
- 推送分支、创建 PR、CI 通过、评审通过和 PR 合并是不同状态。仅在合并并满足验收后标记任务完成和关闭 Issue。
- 在已有授权范围内完成修改、验证、推送、PR、Issue 状态及有权限的看板同步；缺权限、环境、许可证或数据时明确阻塞，不把本地完成写成远端已完成。

## 9. 暂停、换人与交接

- 暂停或换人时，在 `work/<用户名>/<Issue编号>/HANDOFF.md` 和个人 STATUS 中记录已完成/未完成、远端与本地状态、准确分支/commit/PR、变更文件、执行命令、配置、输入/输出及 SHA-256、验证、运行中作业、阻塞和下一步。
- 交接必须可直接执行，说明哪些文件尚未提交/上传、哪些结果只在本地或远端、哪些受限资料不可传输、恢复所需环境和权限。
- 接手者先重读最新 Issue、PR、STATUS 和 HANDOFF，再核对远端提交；聊天记录不是正式交接来源。

## 10. 规则来源与当前阻塞

- 项目结构与电路用途来自本分支 `README.md`，远端 blob `cc7fe150a75e723ba881d69329345a09e7bcc759`。
- 通用协作规则参考 `rayggxia-workspace/pbit-llm-qwen-baselines` 的 `collab/issue-1-governance` 分支，提交 `8fb45388f51dcc4b6dcff2b25584da767ffd0575`，对应 Issue #1 和待审、未合并的 PR #2；这里只采用协作方法，不继承其 LLM 专属实验规则。
- 截至 2026-10-16，workspace 的治理 PR #2 仍待审，Projects v2 权限不足；该状态不能当作组织级规则已经合并。
- 当前电路迁移的阻塞是：`rayggxia-workspace` 下尚未建立或指定电路目标仓库，因此无法在正确仓库创建本任务 Issue、设置 workspace remote、推送任务分支、提交 PR 或同步对应看板。
- 解除阻塞后第一步是确定/创建目标仓库及可见性，再建立迁移 Issue，明确哪些历史分支、Git 历史和本地大型资料属于迁移范围；不要把整个混合工作目录原样上传。
