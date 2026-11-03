# ESP32 远程开机 · 软件全链路测试(模拟器方案)

> 思路: 硬件还没焊之前, 先用 Python 模拟器扮演 ESP32, 把"阿里 ECS 脚本 → MQTT Broker → 设备端"整条链路打通验证。
> 模拟器行为与固件 PC_PowerRelay.ino 完全对齐(冷却 10s、吸合 0.4s、trigger 触发), 模拟器验证通过后换真固件即无缝衔接。

## 拓扑

```
[阿里云 ECS]                      [本地 WSL]
send_power_cmd.sh  →  mosquitto  →   simulator.py (扮演 ESP32)
   (发布 trigger)     (Broker)        (订阅, 模拟开机)
```

## 前置条件

1. ECS 上已部署 Broker(还没部署就在 ECS 上跑 `sudo bash server/install_mosquitto.sh` —— 需要先同步 server/ 目录到 ECS)
2. 阿里云安全组放行 TCP 8081（公网路径；1883 仅内网测试用）
3. 本地已装 paho-mqtt(`pip3 install --user paho-mqtt`, 已装过)

## 测试步骤

```bash
# 终端 1(本地): 起模拟器, 扮演 ESP32
cd simulator
python3 simulator.py <ECS公网IP>
# 看到 "[MQTT] 连接成功 rc=0, 订阅 device/pc_power" 即链路通

# 终端 2(ECS 上): 触发开机（脚本在 server/ 目录）
cd server && bash send_power_cmd.sh

# 回终端 1 看:
#   [MQTT] 收到主题 device/pc_power | payload: trigger
#   [TRIGGER] 收到 trigger, 继电器吸合(低电平) ... 模拟按下电源键
#   [TRIGGER] 继电器释放, 模拟按键松开
#   ✅ 模拟开机成功!
```

## 验证点(对应需求文档 4 测试规范)

| 验证点 | 操作 | 预期 |
|---|---|---|
| 上电不误触发 | 模拟器刚启动,不发指令 | 无任何触发日志 ✅ |
| 触发开机 | ECS 跑 send_power_cmd.sh | 模拟器收到 trigger,打印开机成功 ✅ |
| 10s 冷却 | 10s 内连发 2-3 次 | 只有第 1 次动作,后续打印 [IGNORE] 冷却中 ✅ |
| 断线重连(可选) | Ctrl+C 杀模拟器再起 / 重启 mosquitto | 模拟器重连成功继续订阅 |

全部通过 → 链路 OK, 把模拟器换成真实 ESP32 固件(填同一 ECS IP 烧录)即可。

## 测试结果(2026-09-15 实测通过 ✅)

ECS: Alibaba Cloud Linux 3, mosquitto(EPEL 8, 无 mosquitto-clients 包 → 控制端用 paho 版 send_power_cmd.py)

**公网方案(真机就是这个路径)**: 安全组只放行 22 和 8081 → mosquitto 加 listener 8081, 设备直连 `<ECS公网IP>:8081`。
```
# ECS 上加 8081 监听(只做一次)
sudo bash -c 'echo -e "\nlistener 8081 0.0.0.0" >> /etc/mosquitto/mosquitto.conf'
sudo systemctl restart mosquitto
```

实测日志(模拟器连公网 <ECS公网IP>:8081):
```
[MQTT] 连接成功 rc=Success, 订阅 device/pc_power
[MQTT] 收到主题 device/pc_power | payload: trigger
[TRIGGER] 收到 trigger, 继电器吸合(低电平) ... 模拟按下电源键
[TRIGGER] 继电器释放, 模拟按键松开
✅ 模拟开机成功!
```
冷却验证: 2s 内连发两次, 第二次打印 `[IGNORE] 冷却中(7s 后可再触发), 丢弃本次指令` ✅

**结论**: MQTT 全链路(发布 → Broker → 订阅 → 动作)在**公网直连 8081** 上验证通过。
真机 ESP32 固件填: mqttServer=<ECS公网IP>, mqttPort=8081 即可。

(中间还用 SSH 隧道 `-L 1883:127.0.0.1:1883` 测过一次内网 1883, 也已通; 隧道方案已弃用, 真机走公网 8081)

## 之后换真机

1. Arduino IDE 打开 `PC_PowerRelay/PC_PowerRelay.ino`
2. 改配置: ssid / password / mqttServer = ECS 公网 IP
3. 烧录, 串口监视器看日志(格式和模拟器一致)
4. 同样在 ECS 跑 `bash send_power_cmd.sh`, 继电器应吸合 0.4s
