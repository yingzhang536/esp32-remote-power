#!/bin/bash
# ============================================================
# 远程开机控制脚本(在阿里云 ECS 上执行)
# 项目: ESP32 远程开机控制器 (projects/esp32/远程控制开机.txt)
# 用法: ./send_power_cmd.sh
# 行为: 向 MQTT 主题 device/pc_power 发布 trigger, 触发 ESP32 按电源键
# 日志: 触发时间 + 来源 追加到 /var/log/pc_power_control.log
# ============================================================

MQTT_HOST="127.0.0.1"        # Broker 地址(本机起 mosquitto 就是 127.0.0.1)
MQTT_TOPIC="device/pc_power"
LOG_FILE="/var/log/pc_power_control.log"

# 记录触发: 时间 + 来源(SSH 客户端 IP / 本地) + 登录用户
{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] trigger 来源:${SSH_CLIENT:-local} 用户:${USER}"
} >> "$LOG_FILE" 2>/dev/null || {
  # 无权限写 /var/log 时退到当前目录
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] trigger 来源:${SSH_CLIENT:-local} 用户:${USER}" >> "$(dirname "$0")/pc_power_control.log"
}

# 发布指令(失败会退出码非 0, 可用于脚本联动)
if mosquitto_pub -h "$MQTT_HOST" -t "$MQTT_TOPIC" -m "trigger"; then
  echo "✅ 已发送 trigger → $MQTT_TOPIC ($(date '+%H:%M:%S'))"
else
  echo "❌ 发送失败, 检查 mosquitto 是否运行 / 1883 端口"
  exit 1
fi
