#!/bin/bash
# ============================================================
# MQTT Broker 部署脚本(阿里云 ECS, AlmaLinux/RHEL 系 dnf)
# 项目: ESP32 远程开机控制器 (projects/esp32/远程控制开机.txt)
# 用法: sudo bash install_mosquitto.sh
# ============================================================
set -e

echo "=== 1/4 安装 mosquitto(Alibaba Cloud Linux 3 / EPEL 8 无 mosquitto-clients 包, 只装 broker) ==="
dnf install -y mosquitto

echo "=== 2/4 配置: 公网监听 1883(测试阶段明文) ==="
CONF=/etc/mosquitto/mosquitto.conf
if grep -q "^listener" "$CONF"; then
  echo "已有 listener 配置, 跳过追加"
else
  cat >> "$CONF" <<EOF

# --- ESP32 远程开机项目(2026-09-15) ---
# 测试阶段: 公网监听 1883, 允许匿名
# 生产建议: 加账号密码(mosquitto_passwd) + TLS 8883, 见 README
listener 1883 0.0.0.0
allow_anonymous true
EOF
  echo "已追加监听配置"
fi

echo "=== 3/4 启动 + 开机自启 ==="
systemctl enable --now mosquitto
systemctl is-active mosquitto

echo "=== 4/4 本机自测(订阅+发布) ==="
timeout 3 mosquitto_sub -h 127.0.0.1 -t device/pc_power -v &
sleep 1
mosquitto_pub -h 127.0.0.1 -t device/pc_power -m "trigger"
wait 2>/dev/null || true

echo ""
echo "✅ Broker 部署完成"
echo "下一步:"
echo "  1. 阿里云控制台安全组放行 TCP 1883(入方向, 0.0.0.0/0 或你的家宽 IP)"
echo "  2. 外部验证: mosquitto_pub -h <ECS公网IP> -t device/pc_power -m trigger"
echo "  3. ESP32 固件里 mqttServer 填 ECS 公网 IP, 烧录后看是否连上"
