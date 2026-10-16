# 让 AI 按统一规则协作

统一规则正文是本仓库的 [rayggxia-project-collab / SKILL.md](../.agents/skills/rayggxia-project-collab/SKILL.md)，当前版本为 **1.0.0**。开始任务、提交成果和修改状态前都读取它；`AGENTS.md`、Claude 和 Copilot 入口只负责指向同一规则。

## 怎么加载

- **Codex：**在已检出的仓库中工作时，Codex 会从仓库 `.agents/skills/` 发现 Skill；开始任务时明确要求使用 `rayggxia-project-collab`。工具未发现时，直接按下方提示读取 `SKILL.md` 全文。[官方加载说明](https://learn.chatgpt.com/docs/build-skills)
- **其他支持 Skill 的 AI：**按其工具支持的方式加载整个 `rayggxia-project-collab` 目录，并确认实际读取版本；不要只复制名称或简介。
- **不支持 Skill 的 AI，或只通过 GitHub 连接工作的 AI：**显式打开上面的 `SKILL.md` 并读取全文，再读取目标仓库的 `AGENTS.md` 和指定 Issue。无需为了读规则安装新工具。

仓库内版本是当前项目的规则正文；个人副本如有不同，先比较版本和内容，不能静默覆盖仓库规则。Skill 通过文件被重复加载，不表示 AI 会永久记住或自动获得 GitHub 权限；每位成员仍使用自己的账号及已获授权的 Issues / Projects 能力。

## 可直接转发给对方 AI

> 请在这个仓库按 .agents/skills/rayggxia-project-collab/SKILL.md 工作；先读取它和 AGENTS.md，再读取项目资料及我给出的 Issue。使用我自己的 GitHub 身份，只操作获授权范围。开始、提交和改状态都核对这份 Skill；交付时给出 PR/进度、项目登记、看板加卡与同步的证据回执。无法接入的事项写入持久交接，不要只上传文件就报告全部完成。

转发时同时给出 **目标项目仓库地址 + Issue 链接**。登记或看板尚未完成时，回执要写清待处理事项；文件上传成功不等于整个协作流程已经接通。

新模板只影响之后创建的仓库，旧仓库不会自动升级。旧仓库缺少本文件时，在获授权的接入变更中复制完整 Skill 目录，让现有 `AGENTS.md` 和模型入口引用它，并保留原有项目规则。可从有权访问的 [team-workspace 同一路径](https://github.com/rayggxia-workspace/team-workspace/tree/main/.agents/skills/rayggxia-project-collab) 取得统一源；没有管理中心权限也可以直接使用已提供的 Markdown。
