# 架构与运行

基线为源库 pbit_chimera 分支 b2c0e774f03b5a7ec205f269e2170344df2139bd。

## 系统边界

UART 配置/读出连接阵列 bank、节点、MAC、LUT、LFSR、边/偏置比较、流水线与表决逻辑。PLL/IO/工艺模型是外部依赖，未随此次迁入发布。

## 目录

- `.github/`：Issue / PR 模板、审查负责人说明和结构检查。
- `config/labels.json`：与管理中心一致的任务类型、优先级、状态和 AI 协作标签。
- `docs/`：项目上下文、决策和交接。
- `scripts/`：不依赖第三方包的管理结构校验。
- `rtl/new_version/`、`rtl/common/`：Chimera RTL。
- `pipeline_tb/`：流水线、读写、3x3、边界、snapshot、逐轮 oracle。
- `gate_sim_500MHz*/`：门级/SDF 脚本；名称不代表签核通过。
- `top/`、`sim/`、`vivado_project/`：历史 FPGA/King 资料，需核实兼容性。

## 本地运行与验证

管理结构检查需要 Python 3.9 或更高版本，无第三方包：

```text
python scripts/check_project.py
python work/jieruiz/1/verify_import.py
```

业务测试按 [pipeline_tb/README.md](../pipeline_tb/README.md) 选择顶层/参数/数据。历史 `validation.txt` 不是本次重跑证据。VCS/DC/PT/Innovus 需要服务器、许可证和合法外部库；本次迁移未运行 EDA。旧脚本默认服务器路径需要按实际环境配置。

CI 仅申请仓库内容读取权限；checkout 固定到官方 [v7.0.1 发布提交](https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1)，不保留登录凭据。升级时核对官方发布记录再更新提交号。

## 配置与外部依赖

共享存储尚未统一；受限资料留在原授权位置，不进入公开仓库。实验须记录代码、配置、数据/库版本、PVT、工具、种子、成果位置及 SHA-256。忽略规则不能替代对已提交文件的检查。
