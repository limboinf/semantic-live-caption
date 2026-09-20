#!/usr/bin/env bash
# 一键拉起：ASR 流式识别服务(6006) + 网页/代理服务(6008)
#
# 前置条件见 README「快速开始」：Confucius4-R2T2 已 clone 并装好 conda 环境、
# 模型权重已下载到 $CONFUCIUS_DIR/checkpoints/。
#
# 可用环境变量：
#   CONFUCIUS_DIR  Confucius4-R2T2 仓库路径   默认 /root/autodl-tmp/Confucius4-R2T2
#   MODEL_PATH     ASR 权重目录                 默认 $CONFUCIUS_DIR/checkpoints/Confucius4-R2T2
#   ASR_PORT       ASR WebSocket 端口          默认 6006
#   WEB_PORT       网页/代理端口               默认 6008
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFUCIUS_DIR="${CONFUCIUS_DIR:-/root/autodl-tmp/Confucius4-R2T2}"
MODEL_PATH="${MODEL_PATH:-$CONFUCIUS_DIR/checkpoints/Confucius4-R2T2}"
ASR_PORT="${ASR_PORT:-6006}"
WEB_PORT="${WEB_PORT:-6008}"
CONDA_ENV="${CONDA_ENV:-confucius4-r2t2}"

source /root/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate "$CONDA_ENV"

# 1) ASR 服务（模型加载约 1~2 分钟，等待 Worker ready 由日志确认）
if [ -d "$CONFUCIUS_DIR" ]; then
  cd "$CONFUCIUS_DIR"
  export HF_HUB_OFFLINE=1   # 国内服务器直连 huggingface.co 不通，避免反复重试
  ./run_start_server.sh start --model_path "$MODEL_PATH" --port "$ASR_PORT" --gpu 0
else
  echo "!! 未找到 Confucius4-R2T2 仓库（$CONFUCIUS_DIR），跳过 ASR 服务"
fi

# 2) 网页 + API 代理服务（先杀掉占用端口的旧进程）
fuser -k "$WEB_PORT/tcp" 2>/dev/null || true
sleep 1
nohup python "$HERE/../server/server.py" --port "$WEB_PORT" --dir "$HERE/../web" \
  > /tmp/tingxiezhi_web.log 2>&1 &
sleep 1
echo "web  -> http://127.0.0.1:$WEB_PORT/  (log: /tmp/tingxiezhi_web.log)"
echo "asr  -> ws://127.0.0.1:$ASR_PORT/asr_stream_api_v1"
echo "done. 打开网页后，在「设置」里把识别服务地址指向 ASR 的可达地址。"
