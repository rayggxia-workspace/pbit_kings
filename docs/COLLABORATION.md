# 成员协作与文件存放

每位成员和自己的 AI 使用自己的 GitHub 账号。先接受邀请并确认目标仓库权限，再操作；项目负责人或组织所有者的账号不是共享账号。仓库和 Projects 看板权限独立，AI 工具也需要分别支持 GitHub Issues 和 Projects。

所有 AI 在开始任务、提交成果和修改状态前读取 [统一协作 Skill v1.0.0](../.agents/skills/rayggxia-project-collab/SKILL.md)。本文说明文件存放位置，完整操作顺序及交付回执以 Skill 为准；加载方法见 [AI 使用说明](AI_SKILL.md)。

## 找到任务并存放成果

| 内容 | 位置 |
| --- | --- |
| 任务、负责人、验收条件和具体讨论 | 本仓库的 GitHub Issues，一项任务一个 Issue |
| 项目整体阶段、里程碑和关键阻塞 | `docs/STATUS.md` |
| 个人简短进度 | `progress/<github-handle>/STATUS.md`，格式见 [progress 说明](../progress/README.md) |
| 个人任务资料、调研和辅助文件 | `work/<github-handle>/<issue-number>/`，格式见 [work 说明](../work/README.md) |
| 正式代码、共同文档与正式交付物 | `docs/ARCHITECTURE.md` 约定的项目目录，通过 PR 合并 |
| 重要决策 | `docs/decisions/` |
| 换人或换 AI 的上下文 | `docs/handoffs/` |

用实际 GitHub 用户名替换 `<github-handle>`，用当前仓库的真实 Issue 编号替换 `<issue-number>`。尚无 Issue 时先创建任务；没有权限时说明情况，不编造编号。不要把所有代码都放进个人目录，也不要覆盖他人的资料。个人目录仍对所有有仓库读取权限的人可见。

具体业务资料只进入获授权的实际项目仓库，不放进管理中心或空白模板仓库；需要不同可见范围时使用独立私有仓库，文件夹不能隔离读取权限。

## 日常工作

1. 在 **Issues → New issue** 填写任务目标、范围、验收标准和相关资料，指定一位主要负责人。多人协作可以拆分关联子任务。
2. 读 `AGENTS.md`、统一 Skill、`project.json`、`docs/STATUS.md` 和任务 Issue，按 `task/<issue-number>-<short-slug>` 建分支。
3. 修改正式代码或上传任务资料，提交时关联 Issue；更新个人进度，写清下一步和阻塞。只有影响整个项目阶段或里程碑的变化才更新 `docs/STATUS.md`。
4. 提交前再次核对 Skill，提交 PR、实际检查结果和证据回执；完成要求的审查、合并与验收后才关闭 Issue。暂停或交接时补充 `docs/handoffs/`。

任务状态以 Issue 的唯一 `status:*` 标签为准。每次提交都核验 Issue 是否已加入配置的 Projects 看板；缺卡时在授权范围内加入，按 [状态映射](../config/status-mapping.json) 同步字段并读回验证。除非项目明确记录并验证了自动同步，否则需要人或 AI 同步这两处。缺少配置、能力或权限时，在 Issue/PR 或 `docs/handoffs/` 留下持久交接，写明待处理动作和处理人；文件已上传不等于登记和看板已接通。

## 给自己的 AI

把本仓库地址和具体 Issue 链接一起发给 AI：

> 请在这个仓库按 .agents/skills/rayggxia-project-collab/SKILL.md 工作；先读取它和 AGENTS.md，再读取项目资料及我给出的 Issue。使用我自己的 GitHub 身份，只操作获授权范围。开始、提交和改状态都核对这份 Skill；交付时给出 PR/进度、项目登记、看板加卡与同步的证据回执。无法接入的事项写入持久交接，不要只上传文件就报告全部完成。

AI 如果只接触本地代码，还需要连接 GitHub 才能读取在线 Issues、分配任务或更新 Projects。无法访问时应报告缺少的能力或权限，不声称操作成功，也不借用其他成员的凭据。
