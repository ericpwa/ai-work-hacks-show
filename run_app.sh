#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/streamlit" ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi

LOCAL_HOSTNAME="$(scutil --get LocalHostName 2>/dev/null || hostname | sed 's/.local$//')"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"

echo ""
echo "AI Work Hacks 職場大絕 v0.2"
echo "========================================"
echo "老師自己開："
echo "  http://127.0.0.1:8501"
echo ""
echo "優先分享給學員的固定網址："
echo "  http://${LOCAL_HOSTNAME}.local:8501"
echo ""
if [ -n "${LAN_IP}" ]; then
  echo "若學員打不開 .local，再分享備用網址："
  echo "  http://${LAN_IP}:8501"
  echo ""
fi
echo "提示：.local 網址通常不會因換 Wi-Fi 改變；但部分學校網路會封鎖 Bonjour/mDNS，此時才需要用備用 IP。"
echo "========================================"
echo ""

.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
