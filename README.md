# 项目模板

这是供人和 AI 共同维护的单项目仓库模板。当前还没有业务代码，也没有启用任何 GitHub 权限或分支保护设置。

**每个参与提交的 AI 都先读 [统一协作 Skill](.agents/skills/rayggxia-project-collab/SKILL.md)。** 开始任务、提交成果和修改状态时都使用这份规则；加载方式及可转发提示见 [AI 使用说明](docs/AI_SKILL.md)。

## 创建项目

1. 从这个模板建立一个独立仓库，建议先设为 **Private**。
2. 修改 `project.json`：填写稳定的 `project_id`、项目名称、负责人、真实仓库全名和默认分支；将 `lifecycle` 改为 `active`。项目 ID 一经采用尽量保持不变。
3. 填写 `docs/PROJECT_BRIEF.md`、`docs/ARCHITECTURE.md` 和 `docs/STATUS.md`。没有确定的信息写“待确认”。
4. 在 GitHub 中配置协作者、仓库权限、审查规则，并按 `config/labels.json` 创建标签；需要 CODEOWNERS 时填写 `.github/CODEOWNERS`。这些设置不会因复制文件而自动生效。
5. 确认标签已实际创建到 GitHub 仓库；Issue 表单只会引用已有标签，单独复制 `config/labels.json` 不会建立标签。可使用管理中心提供的初始化工具，或由管理员逐个创建。
6. 按统一 Skill 核验项目登记和目标看板配置；登记 PR 尚未合并时记为 `pending`。执行 `python scripts/check_project.py`，然后建立第一个 Issue，核验加卡、字段同步与实际读取结果；不能接入时留下持久交接。

## 日常使用

新成员先读 [成员协作与文件存放](docs/COLLABORATION.md)，用自己的 GitHub 账号连接自己的 AI。

每项工作建一个 Issue → 负责人确认范围和验收条件 → 建分支 → 提交 PR → 检查与审查 → 合并并关闭 Issue。

- 分支：`task/<Issue编号>-<简短英文描述>`，例如 `task/12-login-page`。
- PR 完整解决任务时用 `Closes #12`，部分交付用 `Refs #12`，避免提前关闭整个任务；跨仓库依赖使用完整 Issue 链接。
- 任务、负责人和任务状态以 **GitHub Issues** 为准；每个 Issue 只保留一个 `status:*` 标签。状态统一使用 `backlog / ready / in_progress / blocked / in_review / done`，与管理中心保持一致。
- Projects 用于汇总多个仓库；字段显示名与状态标签的精确对应见本仓库 [状态映射](config/status-mapping.json)。每次提交核验 Issue 已加入配置的看板，缺卡时在授权范围内加入；按映射同步字段并读回验证。在明确配置并验证自动同步之前，由操作者完成同步。如果两处不一致，按 Skill 先核对最新任务事实，再修正标签和字段。缺少配置、能力或权限时，在 Issue/PR 或交接记录中明确待处理事项。
- 文档只记录项目概况、当前里程碑、重要决策和交接，不另建一份完整任务清单。
- 每个项目的业务测试由项目自己补充。本模板的检查仅验证管理文件结构。

## 给 AI 的入口

先读 `AGENTS.md` 和 [统一协作 Skill](.agents/skills/rayggxia-project-collab/SKILL.md)，再读 `project.json`、`docs/COLLABORATION.md` 和 `docs/STATUS.md`，随后只加载当前 Issue 所需文件。提交或修改状态前重新核对 Skill；结束时按 PR 模板提交证据回执，更新个人进度并记录未完成事项。读取在线任务和更新看板还需要 AI 连接 GitHub Issues / Projects 并具有相应权限。

| 文件 | 用途 |
| --- | --- |
| `.agents/skills/rayggxia-project-collab/SKILL.md` | 所有 AI 共用的任务、上传、登记、看板和交付流程 |
| `project.json` | 机器可读的项目身份、负责人、流程和文档入口 |
| `config/status-mapping.json` | 六种任务状态、Issue 标签与 Projects 显示名的精确映射 |
| `docs/PROJECT_BRIEF.md` | 目标、边界和验收标准 |
| `docs/ARCHITECTURE.md` | 系统边界、目录约定和运行方式 |
| `docs/STATUS.md` | 当前阶段、里程碑和阻塞摘要 |
| `docs/COLLABORATION.md` | 成员与 AI 的协作入口、任务和文件存放规则 |
| `progress/<github-handle>/STATUS.md` | 个人进度摘要，关联 Issue/PR；格式见 [progress 说明](progress/README.md) |
| `work/<github-handle>/<issue-number>/` | 个人任务辅助资料；正式代码遵循项目正式目录，见 [work 说明](work/README.md) |
| `docs/decisions/` | 重要决策及理由 |
| `docs/handoffs/` | 下一位协作者可以接手的上下文 |

## 权限边界

**按仓库隔离需要保密的项目。** GitHub 的普通仓库协作权限不能把同一仓库的某个目录隐藏给指定协作者；CODEOWNERS 指定审查责任，不授予或撤销读取权限。集中管理仓库和 Projects 中只放参与者有权看到的信息，敏感细节保留在对应项目仓库。

协作者实际权限、邀请和分支保护由仓库或组织管理员在 GitHub 中配置。本模板不自动邀请任何人。
