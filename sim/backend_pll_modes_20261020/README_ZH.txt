PLL 旁路、变频与上板流程后仿
版本：20261020_pll_modes_v2
日期：2026-10-20；跟踪：rayggxia-workspace/pbit_kings Issue #5

一、用途与边界

使用已有 backend_261014 DRC/SI 网表、PLL_20260916 厂商行为模型和配套 SDF，
补充最新后端尚无完整通过证据的旁路/跨频率重配。不是重跑大 MaxCut 或功耗。
本地已执行的检查见 LOCAL_VALIDATION.txt；v1的真实网表任务38227554已检查，
v2尚待用户提交。旁路检查器由本项目testbench编写，不来自厂商或后端。
不修改芯片 RTL、不修补厂商 PLL 功能行为、不强制时钟或阵列状态、不生成大 VCD。
仅沿用已有窄范围同步首级 notifier profile，时序检查和所有原始事件仍保留。

二、三组完整流程与三项接管对照

v1任务38227554暴露的疑点分开验证：
  1. 25MHz旁路高/低电平20.20/19.80ns，但完整周期40ns。旧版强制对称检查过严。
     v2持续检查完整周期误差不超过40ps，高/低脉宽分别记录并限制在半周期±10%。
     旁路还逐沿比对真实dut.ref_clk的极性和0..2ns传播延迟。这些是诊断预算，
     不是工艺库WIDTH规格；SDF中的WIDTH/hold等检查仍全部启用。
  2. 地址寄存器req_addr[3]发生30ps的hold不足。它的Q有反馈，快速接口的force
     可能改变反馈D；其CK为CTS_8，原接口启动寄存器CK为CTS_5，不假定两者同相。
     bus_legacy保留原接管方式；bus_safe在该地址寄存器实际CK下降沿后0.30ns
     接管/释放，并重复8次；pin_only完全不接管总线，作无注入对照。
     三项只做启动和接口隔离，不宣称完成计算。CK/D/Q、注入变化都记录在trace。
     只有旧方式复现目标违例、新方式和无注入对照干净时才支持“测试台引入”判断。
  3. 独立model_probe在没有芯片网表/SDF的情况下，运行同一厂商PLL_20260916。
     比较厂商原始1ps模型和仅精度转换的10ps副本，五种EN关闭相位；保留原始警告
     和CKOUT/CKTST短脉冲。不修补厂商行为、不伪造锁定，也不据此宣布真实硅片有毛刺。
  4. 复位期间的MAC/RNG违例仍保留并按时刻/模块分类；各完整模式恢复计算后，
     额外读取10页共100字/3200位snapshot，任何X立即失败。该检查不等于所有内部
     寄存器都已刷新，也不能替代后端recovery/removal和复位树STA。

all包含以下六个case和独立model_probe，芯片网表只编译一次。quick只执行三项
接管对照和model_probe，不执行计算/完整切频流程。需要完整检查时使用all。

bypass：直接从上电/外部复位进入 25 MHz BP 旁路。
  PLL 正常配置通过真实 1 Mbaud UART 完成五笔写/读/APPLY/STATUS/ACTIVE。
  检查实际 BP/N/OD 引脚、core_clk 与 CKTST 稳定脉宽、启动等待和核心复位。
  用真实核心 UART 写/读全局配置，再用两节点 MaxCut 运行两轮、读 snapshot。

switch：300 -> 150 -> 25 MHz BP旁路 -> 300 -> 同频300 MHz重新APPLY。
  每档均执行上述五笔真实 PLL UART、两笔真实核心 UART和小问题计算/读出。
  SHADOW 写入时仍监视旧的工作时钟，正式 APPLY 才进入重配无效阶段。
  检查核心复位先于 PLL 关闭、足够启动等待，以及 APPLY 清除旧核心配置。
  同频 APPLY 也必须重新复位/配置，不能当成不改变状态的空操作。

errors：从300 MHz启动，补充以下检查。
  - 真实 PLL UART 非法 COMMAND，应答、错误状态和清错。
  - 保留位非零、非法 N、输出600 MHz超限：拒绝 APPLY，ACTIVE和旧时钟不变。
  - 300 MHz核心UART主机位周期 -1% / +1% 的少量真实读回。
  - 运行中通过正常 PLL 控制器 APPLY 到150 MHz，验证旧运行被复位中止。
  - BUSY时写SHADOW/再次APPLY被拒绝，BUSY时CLEAR_ERROR允许且不取消重配。
  - 恢复后核心配置为复位值，重新配置并运行/读出小问题。

普通串口一帧的时间比约15 us的BUSY窗口还长，无法靠“收到APPLY应答后
再发一帧”保证打中BUSY。因此定向BUSY和部分非法配置通过已审核请求边界
注入，每笔标记 PLL_REQUEST_BOUNDARY；不是假称这些都经过真实引脚UART。
小问题配置与运行/读出使用已验证的快速核心寄存器接口；每档两个真实核心
UART探针独立进行，探针期间释放该接口的force。该混合任务不称全程pin UART。
完整正常pin UART路径已有任务38168732证据，不在这里逐节点串行配置3200位。

三、频率与波特率

参考时钟：25 MHz；PLL配置UART始终1 Mbaud。
当前后端核心UART固定500 core cycles/bit，不使用旧文档的400分频。

core clock    PLL配置值    核心UART      主机bit周期
300 MHz       0x0218       600 kbaud     1666.666667 ns
150 MHz       0x0418       300 kbaud     3333.333333 ns
25 MHz BP     0x0a18        50 kbaud    20000.000000 ns

N=24、SELECT=0，PLL模式VCO为600 MHz；150 MHz改变OD，旁路置BP。
配置还需符合厂商实际宏使用规范；仿真不证明模拟锁定、抖动或电源特性。
当前控制器BP=1时仍使能PLL；本任务不证明“PLL关闭/未锁定时旁路也可自救”。

每次成功APPLY会复位核心，所以步骤为：
  停止核心UART事务 -> 配置UART写SHADOW并APPLY -> 查STATUS/ACTIVE
  -> 按新频率更新核心UART位周期 -> 重配问题和种子 -> 运行 -> snapshot读出。
不支持把它理解为保留计算状态的无缝DVFS。

四、上传并运行

只上传 backend_pll_modes_20261020_v2_scripts.zip 到原服务器项目根目录。
网表/SDF/库沿用已有位置，无需重复上传。包里有全部新testbench及流程代码，
没有厂商模型/工艺库/芯片网表；它们需继续使用服务器已上传版本。

BASE=/public3/home/t6s011227/pbit_chimera_pipeline_20260920
cd "$BASE"
unzip -o backend_pll_modes_20261020_v2_scripts.zip
cd backend_pll_modes_20261020
grep -qx '20261020_pll_modes_v2' VERSION.txt
python3 run.py verify .
bash submit.sh all

默认一个Slurm任务：WC最大SDF，一次芯片编译，执行六项case和两个极小模型探针。
资源4 CPU、8G；普通串行VCS，无FGP要求。申请4核不代表获得四核仿真加速。
没有自设wall上限（Slurm --time=0、MAX_WALL_HOURS=0）；仍受集群策略限制。
有真实UART，运行时间不是纯总线任务的几分钟，不承诺具体完成时限。
每10秒记录墙钟/CPU进度，每10 us电路时间记录仿真心跳。

建议补充BC最小延时，独立提交：
  CORNER=BC bash submit.sh all
这会绑定BC文件并编译MINIMUM，运行+mindelays，不能复用WC二进制。
BC是已提供的FF/1.32V/-40C SDF场景，不是要求实物把电源调成1.32V。
VCS延时来自选定SDF；DB/SPEF只用于输入版本核验，没有运行PT/功耗/签核STA。

先快速隔离可用：bash submit.sh quick。它不证明旁路/变频完整功能。
只跑一项可用：bash submit.sh bypass（或switch、errors、bus_legacy、bus_safe、pin_only）。
若同一脚本、同一corner已有成功编译，仅重跑剩余项可严格复用：
  BUILD_JOB="$BASE/backend_pll_modes_20261020/results/旧JOBID/build" bash submit.sh errors
源/设置/输入哈希或corner不一致会拒绝，不会静默用旧二进制。
不能把38227554的v1 build用于v2，必须重新编译。v2同版本的quick与all可复用。
保持旧build及其输入/符号链接目标，不要运行中删除。

默认输入：$BASE/backend_inputs_261014。
默认版本核验checkpoint：$BASE/backend_fast_20261018/results/38117744。
若已归档该checkpoint：CHECK_JOB=fresh bash submit.sh all（重新核验所有输入）。
其他路径用INPUT_DIR、PLL_ROOT、STD_ROOT、IO_ROOT等环境变量显式指定。
只在工具明确需要时设置DIAG_DEBUG=all，源码/构建身份会相应改变。

五、结果和判断

日志：logs/job-<JOBID>.out / .err
结果：results/<JOBID>/
自动打包：backend_pll_modes_<JOBID>.tar.gz

先读 suspect_diagnosis.json、diagnostic_summary.json，再读各cases/<名字>/audit.json。
model_probe/model_summary.json：独立厂商模型的双精度停启结果及原始trace/log。
clock_metrics.jsonl：完整周期、高低脉宽、旁路参考沿的传播延迟。
epochs.jsonl：每档配置、实际脉宽范围、串口笔数、复位/启动间隔及问题范围。
transactions.jsonl：真实PLL UART、真实核心UART和请求边界注入分别记载。
checks.jsonl：逐项断言清单；mode_trace.csv：复位与PLL引脚、短窗口时钟。
simulation.log：保留原始timing事件和PLL模型警告，不仅留下PASS标记。

功能错误、X/错误串口回复、频率/脉宽异常、缺覆盖、非复位窗口时序事件或短脉冲
会失败。复位窗口事件、已有同步首级事件和模型警告保留分类，不视为芯片签核。
唯一预期负对照是bus_legacy：若只复现目标地址hold且与注入变化相邻，原始失败仍
保留为negative_control_reproduced，汇总不把它当成新方式失败；其他新违例不豁免。
若旧方式未复现或safe/pin_only也有问题，因果判断明确保持未解决，不能自动归因。
FUNCTIONAL_PASS_REVIEW_REQUIRED表示定向功能完成但有事件待审，不是时序清零。
DIAGNOSTICS_COMPLETE.txt也仅表示全部选定case执行结束；需结合summary判断。

PLL旧模型停钟除零警告不会被修改/删除。若影响恢复、产生有效阶段异常脉冲或
结果不一致，会明确报错；仅复位期间的事件仍留给厂商/后端审查。
稳定窗口core_clk和CKTST由独立guard连续检查；过渡窗口短脉冲另从trace分类。

大网表、二进制、厂商模型、大波形和三份重复编译日志不放进下载包。
编译失败时原件仍在服务器，可另发：
  tail -n 100 results/<JOBID>/build/compile.log
  cat results/<JOBID>/build/failure.txt
下载包保留driver.log、回标审计、原生覆盖摘要和构建/输入身份。

六、不能由本任务证明的事项

不证明真实PLL锁定/抖动/电源/关断脉宽规格，不证明无LOCK输入的等待值在所有
PVT下足够，不证明实际参考时钟丢失后的硬件恢复能力，也不替代CDC/RDC或STA。
启动失锁等模拟故障需厂商模型支持、专门故障注入或实物测试，未伪造模拟LOCK。
真实PLL宏LEF/GDS与模型的一致性仍需后端核实。
