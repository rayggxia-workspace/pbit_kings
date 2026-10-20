Recovery 复位瞬态诊断，20261020_recovery_diag_v1
=================================================

一、当前结论

基于 backend_functional_38215256 的原始报告，1,589 条 setuphold 都是真实的
标准单元时序检查。它们发生在 18,951.27--18,951.41 ns 的时钟事件附近，
处于 core_rst_n=0 的 18,948.87--36,108.26 ns 窗口内。
1,575 个不同寄存器受影响，事件中 1,095 条为 contrib_ff、494 条为 macsum_ff；
1,455 条检查 E，134 条检查 D。以上数量不是互不相同的寄存器数量。

对应 RTL 的 MAC 数据流水线使用无复位 dffe，控制器复位有效使能。
异步复位让 E/D 在时钟边沿附近变化，可能使无复位数据 Q 暂时变 X。
这不等同于有效计算已出错，也不能只因最终功能 PASS 就直接忽略。

另有 PLL 厂商行为模型的 STASKW_SDILTA64B/inf 延时警告。CKTST 振荡器
等待期间频率被清零可能涉及该警告，但未证实它是 MAC 违例的原因。
本包不改厂商模型功能行为，记录其警告并检查重启后的 core_clk/CKTST 周期。
沿用旧流程，仅在作业内的模型副本转换时间精度至 10 ps，原文件不改动，
转换记录和原始文件 SHA 保存在 precision.json。

二、本任务检查什么

仅 recovery，三个额外复位偏移 0 / 0.83 / 1.67 ns。一次编译，顺序执行。
均为 300 MHz、WC 最大 SDF、10 ps 精度。默认 4 CPU、8G，无自设 wall 上限。
VCS 普通串行模式，不要求 VT_FGP_Runtime，也不宣称 4 核并行加速。

1. 干净启动，配置一个节点和一条共享随机种子；实际多数表决=1，运行两轮。
2. 通过真实寄存器总线接口完整读取 10 页、100 个字、3,200 位 snapshot，
   保存随机数读回。不是仅读取少数期望位。
3. 运行中验证配置写入/重复启动拒绝，再通过实际 pad_rst_n 中途复位并重启 PLL。
4. 重新配置、运行，逐字比较 3,200 位 snapshot 和种子状态读回。
5. 对旧日志受影响的 1,575 个实际单元，只读观察 CK/E/D/Q，要求重启后
   完成至少一次已知数据写入且 Q 正确捕获。未知 E、启用时未知 D、捕获错误
   均保留为失败，不强制清零或忽略 X。新写入检查在复位后配置/计算阶段启用。
6. 记录复位边沿附近时钟，检查稳定重启阶段 core_clk 半周期 1.5--1.85 ns、
   CKTST 半周期 45--65 ns；保存复位期间短脉冲计数及模型警告。
7. 原始 timing 事件的参考边沿与数据边沿都必须处于同一已知低电平复位窗口，
   才分类为 reset_window_events。X/Z 复位不算确定的复位低电平。

保持现有仅两个已审核 UART RX 首级 notifier 的配置，不新增 MAC/复位豁免，
不关闭全局 timing checks，不 force 时钟、MAC 数据或阵列状态。
沿用已验证的 UART 请求边界快速总线适配器以及 PLL 供电连接；不是新的全程
pin UART 测试。已通过的 crossbank、boundaries 和独立 pin UART 不重跑。
不生成大波形、不做 PT/功耗、不等待长任务的 65,536 轮计算完成。

三、上传和提交

仅上传 backend_recovery_diag_20261020_scripts.zip 到原项目根目录。
已有 backend_inputs_261014 输入和已审核输入 checkpoint 继续使用，不重复上传。

BASE=/public3/home/t6s011227/pbit_chimera_pipeline_20260920
cd "$BASE"
unzip -o backend_recovery_diag_20261020_scripts.zip
cd backend_recovery_diag_20261020
grep -qx '20261020_recovery_diag_v1' VERSION.txt
python3 run.py verify .
bash submit.sh all

正常只提交一个 Slurm 作业，内部一次编译、依次执行三个复位相位。
仅需复查一个相位时：bash submit.sh phase0
若队列不允许 time=0，提交前指定其允许的 TIME_LIMIT；不要自行假定无限期获准。

默认输入校验 checkpoint：
  $BASE/backend_fast_20261018/results/38117744
默认输入目录：
  $BASE/backend_inputs_261014
如服务器已归档校验 checkpoint，可用全新检查，不改变网表：
  CHECK_JOB=fresh bash submit.sh all
如输入目录在别处，用 INPUT_DIR=/实际输入目录 指定。
只在工具明确需要全 debug 时设 DIAG_DEBUG=all；这会改变 build identity，
不允许静默复用不同 debug/source/input 的旧二进制。

四、结果位置与阅读

日志：logs/job-<JOBID>.out / .err
工作目录：results/<JOBID>/
自动下载包：backend_recovery_diag_<JOBID>.tar.gz

先读 diagnostic_summary.json；每相位读 cases/<phase>/diagnosis.json，
diagnostic_result.json、checks.jsonl、reset_clock_trace.csv 和 simulation.log。
包保留原始运行日志及 timing 事件，不附巨大网表/波形/二进制/厂商模型。
编译原始日志留在服务器 results/<JOBID>/build/compile.log；若编译失败，请另给
  tail -n 100 results/<JOBID>/build/compile.log
  cat results/<JOBID>/build/failure.txt
下载包中仍有 driver.log、注释门检查、原生覆盖率和输入/二进制身份摘要。

结果含义：
- FAILED_VALID_OPERATION_OR_FUNCTION：功能/X/时钟/非复位窗口时序等检查失败，
  必须继续定位。监视器在无效预热写入发现 X 时，也不能仅凭此宣称芯片功能坏，
  应结合首次有效消费时刻审查；本诊断采取保守报错。
- RESET_TRANSIENTS_FUNCTIONALLY_CONTAINED_REVIEW_REQUIRED：本测试的功能、
  新写入与稳定时钟检查通过，时序事件只在复位低电平期间；可作为复位无效数据
  瞬态的证据交后端审查，但没有把这些事件永久豁免。
- NO_UNEXPECTED_TIMING_IN_THIS_CASE_NOT_SIGNOFF：本用例未观察到额外时序事件。

DIAGNOSTICS_COMPLETE.txt 表示诊断执行结束，不是芯片时序 PASS；即使功能恢复，
复位时短脉冲、PLL 模型警告仍需保留审查，不能忽略。若警告继续存在或 CKTST
不恢复，需与厂商确认模型停钟/重启行为，不应自行给全模型禁用时序检查。

五、边界与可接受性判断

仅当违例位于复位无效窗口、恢复后流水线被新数据覆盖且未被提前消费、控制/输出
无 X、相同输入结果一致，并经后端核对复位释放 recovery/removal、最小脉宽和
有效工作 setup/hold 后，才适合将其列为复位窗口可解释事件。
本脚本的有限输入/三个相位提供定向证据，不是所有输入形式证明或 STA 签核。
未修改 RTL、SDC 或厂商 IP；不因软件检查完成就认为实体 PLL 模拟性能已验证。
若出现非复位窗口事件、结果差异、已知写入失败或重启时钟异常，则不是可以简单
忽略的问题，应按具体控制/数据/模型原因修复。

六、已有证据和本地验证

源结果 backend_functional_38215256.tar.gz SHA-256：
c43ad39669325ad3b5ceb15756a7a94605d5b1b4583e0910fd8da28208911b7e
旧输入包 backend_functional_20261019_v2_scripts.zip SHA-256：
28e340656a72f1afa148e6a7b57181db6c62790860d59dd557fec0fd2684c603
affected_registers.json 为自己设计的受影响实例名清单，不包含厂商模型。
具体已执行的本地检查见 LOCAL_VALIDATION.txt。这里没有运行全网表 VCS/STA，
必须提交远端诊断才能进一步下结论。
