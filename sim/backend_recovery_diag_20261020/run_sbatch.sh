#!/bin/bash
set -Ee -o pipefail
: "${DIAG_ROOT:?Use submit.sh}" "${DIAG_SNAPSHOT:?Use submit.sh}" "${SLURM_JOB_ID:?Use Slurm}"
WORK="$DIAG_ROOT/results/$SLURM_JOB_ID"
mkdir -p "$WORK"
cd "$WORK"
finish() {
  local rc=$?
  trap - EXIT
  echo "$rc" > exit_status.txt
  # Keep native coverage and identities, not three copies of huge compiler warnings.
  tar --exclude='analysis.vg' --exclude='simulation.sdf' --exclude='*.vcd' \
    --exclude='sdfAnnotateInfo*' --exclude='models' --exclude='csrc' \
    --exclude='simv*' --exclude='*.daidir' --exclude='*.vdb' --exclude='__pycache__' \
    --exclude='compile.log' --exclude='compile_console.log' --exclude='sdf_annotation.log' \
    -czf "$DIAG_ROOT/backend_recovery_diag_${SLURM_JOB_ID}.tar.gz" \
    -C "$DIAG_ROOT/results" "$SLURM_JOB_ID" || true
  echo "WORK=$WORK"
  echo "DOWNLOAD=$DIAG_ROOT/backend_recovery_diag_${SLURM_JOB_ID}.tar.gz"
  exit "$rc"
}
trap finish EXIT
trap 'echo "ERROR line=$LINENO command=$BASH_COMMAND" >&2' ERR
set +u
source "$HOME/.bashrc"
set -Eeu -o pipefail
export CORE_MHZ=300 MAJORITY=1 UART_DIVISOR=500 PRECISION=10ps SYNC_POLICY=profile CORNER=WC
export PARALLEL=serial VCS_FGP_THREADS=1 SDC_MODE=measurement FAST_ROOT="$DIAG_ROOT" SCALE_CELLS=1
export STD_ROOT="${STD_ROOT:-/public3/home/t6s011227/ICsprout_55LLULP1225_STD_0818/ICsprout55_SC9T_BASIC_SVT/0.1}"
export IO_ROOT="${IO_ROOT:-/public3/home/t6s011227/ICsprout_55LLULP1225_IO_0901/ICsprout_55LLULP1225_IO_0901/IC055L_GPIO3P3V_CDG_v1.1a}"
export PLL_ROOT="${PLL_ROOT:-/public3/home/t6s011227/PLL_new_ip/PLL_20260916}"
export STD_DB="${STD_DB:-$STD_ROOT/lib/ICsprout55_9TSVT_ss_v1p08_125c_basic_nldm.db}"
export IO_DB="${IO_DB:-$IO_ROOT/lib/ic055l_gpio3p3v_cdg_v1p1a/ic055l_gpio3p3v_cdg_ss_v1p08_v2p25_125c_nldm.db}"
export PLL_DB="${PLL_DB:-$PLL_ROOT/lib/PLL_TOP_max.db}"
export STD_MODEL="${STD_MODEL:-$STD_ROOT/verilog/ICsprout55_9TSVT_basic.v}"
export IO_MODEL="${IO_MODEL:-$IO_ROOT/verilog/ic055l_gpio3p3v_cdg_v1p1a/IC055L_GPIO3P3V_CDG.v}"
export PLL_MODEL="${PLL_MODEL:-$PLL_ROOT/verilog/PLL_TOP.v}"
export NETLIST="$INPUT_DIR/sdf_261014/pt_netlist/pbit_io_wrapper_pt.vg"
export SDF_WC="$INPUT_DIR/sdf_261014/WC/pbit_io_wrapper_WC.sdf" SDF_BC="$INPUT_DIR/sdf_261014/BC/pbit_io_wrapper_BC.sdf"
export SPEF="$INPUT_DIR/spef/pbit_cworst_T_125.spef.gz" SPEF_BC="$INPUT_DIR/spef/pbit_cbest_T_m40.spef.gz"
export INPUT_SLEW_NS=0.1 PLL_SLEW_NS=0.1 OUTPUT_LOAD_PF=0.01
command -v "$PYTHON_BIN"
command -v "${VCS_BIN:-vcs}"
"$PYTHON_BIN" -u "$DIAG_SNAPSHOT/run.py"
