#!/bin/bash
# ESP32 远程开机: 发送 MQTT trigger, 模拟按下电源键
# 用法: ./power-on.sh   或   power-on
# 原理: python3 调 paho 发 trigger 到 device/pc_power, ESP32 收到后继电器吸合 0.4s
exec python3 /home/shang/esp32-server/send_power_cmd.py
