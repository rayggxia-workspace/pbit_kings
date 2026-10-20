# 当前状态

公开仓库已创建，业务代码通过任务 PR 待审后合入；原库保留。

- 当前阶段：Issue #1 代码已推送，[PR #2](https://github.com/rayggxia-workspace/pbit_kings/pull/2) 待审，未合并
- 更新日期：2026-10-17（Asia/Shanghai）
- 当前里程碑：Chimera 已提交源码及历史接入工作区
- 当前重点：源版本 b2c0e774f03b5a7ec205f269e2170344df2139bd；不修改 RTL
- 关键阻塞：登记校验器仅接受 private，本项目按用户要求 public，管理 Issue #3 待处理；看板凭据缺 read:project；审查人待指定
- 下一个动作：审查 task/1-import-chimera，确认公开项目登记方式及补同步看板
- 任务入口：https://github.com/rayggxia-workspace/pbit_kings/issues/1
- Projects：查询返回 INSUFFICIENT_SCOPES，状态未核实、同步待处理；未新增授权/保护设置

个人进度：[jieruiz](../progress/jieruiz/STATUS.md)。交接：[HANDOFF](../work/jieruiz/1/HANDOFF.md)。

2026-10-20 增量：[Issue #3](https://github.com/rayggxia-workspace/pbit_kings/issues/3)
定向检查后仿中途复位的 1,589 条时序事件。已有事件均处于 core reset 低电平窗口，
最新远端任务38219776的三个相位功能恢复通过，事件均在复位期间，PLL模型停钟
警告仍保留；后端签核审查待执行，不能据此直接忽略全部事件。
已通过草稿 [PR #4](https://github.com/rayggxia-workspace/pbit_kings/pull/4) 交付，未合并。
不宣称问题已修复、时序已清零或 PR #2 已合并。

2026-10-20 新增：[Issue #5](https://github.com/rayggxia-workspace/pbit_kings/issues/5)
补充PLL旁路/变频后仿脚本，继承PR #4框架，未修改RTL或厂商模型功能行为。
本地15项检查通过；新模式的远端VCS仍待提交，不用旧版理想PLL测试冒充后端验证。

只维护影响整个项目的摘要，不复制完整任务清单。阶段或关键阻塞变化时更新；普通任务进度保留在 Issue/PR 中。
