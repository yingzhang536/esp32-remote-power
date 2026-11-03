#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程开机控制脚本(Python/paho 版, 替代 mosquitto_pub)
原因: Alibaba Cloud Linux 3 的源里没有 mosquitto-clients 包, 无 mosquitto_pub/sub 命令

用法(在 ECS 上):
    python3 send_power_cmd.py

行为: 向 MQTT 主题 device/pc_power 发布 trigger, 触发 ESP32 按电源键
日志: 触发时间 + 来源 追加到日志(默认 /var/log/pc_power_control.log, 无权限时落到脚本同目录)
"""
import datetime
import getpass
import os
import sys

import paho.mqtt.publish as publish

HOST = "127.0.0.1"              # Broker 地址(本机起 mosquitto)
PORT = 1883
TOPIC = "device/pc_power"
LOG_FILE = "/var/log/pc_power_control.log"


def main():
    # 发布 trigger(QoS 0, 丢了一拍再发一次即可; 10s 冷却会挡掉重复)
    publish.single(TOPIC, "trigger", hostname=HOST, port=PORT)

    # 日志: 时间 + 来源(SSH 客户端 IP / local) + 用户
    src = os.environ.get("SSH_CLIENT", "local").split()[0] if os.environ.get("SSH_CLIENT") else "local"
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] trigger 来源:{src} 用户:{getpass.getuser()}"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except PermissionError:
        fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pc_power_control.log")
        with open(fallback, "a") as f:
            f.write(line + "\n")
        line += f" (日志: {fallback})"
    print("✅ 已发送 trigger →", TOPIC)
    print(line)


if __name__ == "__main__":
    main()
