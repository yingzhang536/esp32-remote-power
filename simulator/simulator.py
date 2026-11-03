#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 远程开机 · 本地模拟器(扮演 ESP32)

用途: 硬件还没上时, 用本脚本模拟 ESP32 固件行为, 先打通 MQTT 全链路:
      阿里 ECS 控制脚本 → mosquitto(Broker) → 本模拟器(扮演 ESP32)

用法:
    python3 simulator.py <ECS公网IP> [--port 1883]

行为与固件 PC_PowerRelay.ino 对齐(串口日志格式也一致):
  - 连接 MQTT, 订阅 device/pc_power
  - 收到 "trigger": 模拟继电器吸合 0.4s → 松开 → 打印"模拟开机成功"
  - 10s 冷却: 冷却期内收到指令直接丢弃(防网络抖动重复触发)
"""
import sys
import time
import paho.mqtt.client as mqtt

TOPIC = "device/pc_power"
COOL_DOWN_SEC = 10     # 冷却 10s, 和固件一致
PRESS_SEC = 0.4        # 吸合 0.4s, 和固件一致

_last_trigger = 0.0


def on_connect(client, userdata, flags, reason_code, properties=None):
    # paho 2.x CallbackAPIVersion.VERSION2: 第4参数是 reason_code(0=成功)
    print(f"[MQTT] 连接成功 rc={reason_code}, 订阅 {TOPIC}")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    global _last_trigger
    payload = msg.payload.decode()
    print(f"[MQTT] 收到主题 {msg.topic} | payload: {payload}")
    if payload != "trigger":
        print("[MQTT] 非 trigger, 忽略")
        return
    now = time.monotonic()
    if now - _last_trigger < COOL_DOWN_SEC:
        left = int(COOL_DOWN_SEC - (now - _last_trigger))
        print(f"[IGNORE] 冷却中({left}s 后可再触发), 丢弃本次指令")
        return
    _last_trigger = now
    print("[TRIGGER] 收到 trigger, 继电器吸合(低电平) ... 模拟按下电源键")
    time.sleep(PRESS_SEC)
    print("[TRIGGER] 继电器释放, 模拟按键松开")
    print("✅ 模拟开机成功! (真机阶段: 台式机此时启动)")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 simulator.py <ECS公网IP> [--port 1883]")
        sys.exit(1)
    host = sys.argv[1]
    port = 1883
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="PC-Simulator")
    client.on_connect = on_connect
    client.on_message = on_message
    print(f"[SIM] ESP32 开机模拟器启动, 连接 {host}:{port} ...")
    try:
        client.connect(host, port, keepalive=60)
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("   检查: ECS 上 mosquitto 是否运行 / 安全组是否放行 1883 / IP 是否正确")
        sys.exit(1)
    client.loop_forever()


if __name__ == "__main__":
    main()
