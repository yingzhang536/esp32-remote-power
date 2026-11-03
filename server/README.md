# ESP32 远程开机 · 服务端部署说明(阿里云 ECS)

> 项目: projects/esp32/远程控制开机.txt V1.0
> 本目录是**控制端**(服务端)交付物:Broker 部署脚本 + 控制指令脚本。
> 控制端与 Hermes Agent 无关,是 ECS 上的独立脚本/服务。

## 文件

| 文件 | 作用 |
|---|---|
| install_mosquitto.sh | 一键部署 MQTT Broker(mosquitto),含自测 |
| send_power_cmd.py | 触发开机的控制脚本(Python/paho,带日志)—— Alibaba Cloud Linux 3 无 mosquitto-clients 包,故用 paho 替代 mosquitto_pub |
| send_power_cmd.sh | (备用)mosquitto_pub 版,仅在有 mosquitto-clients 的发行版可用 |

## 部署步骤(在 ECS 上)

```bash
# 1. 部署 Broker(需要 root)
sudo bash install_mosquitto.sh

# 2. 安全组放行: 阿里云控制台 → 安全组 → 入方向 → 放行 TCP 1883
#    (来源建议写你的家宽 IP, 别 0.0.0.0/0 裸奔)

# 3. 验证外部可达(在你自己电脑上)
mosquitto_pub -h <ECS公网IP> -t device/pc_power -m trigger
# 另一终端订阅观察: mosquitto_sub -h <ECS公网IP> -t device/pc_power -v
```

## 触发开机(两种方式)

```bash
# 方式 A: 直接命令行
mosquitto_pub -h 127.0.0.1 -t device/pc_power -m trigger

# 方式 B: 用脚本(带日志记录时间/来源)
python3 send_power_cmd.py
# 日志: /var/log/pc_power_control.log
```

## 测试阶段 vs 生产安全

| | 测试阶段(现在) | 生产建议 |
|---|---|---|
| 监听 | 0.0.0.0:1883 明文 | 仅内网/加认证 |
| 认证 | allow_anonymous true | mosquitto_passwd 建账号 |
| 传输 | 明文 | TLS 8883 端口 |

当前固件未带账号密码,所以先明文测试;**上线前**把认证加上,固件里
`client.connect(clientId)` 改 `client.connect(clientId, user, pass)`。

## 常见排查

- Broker 没起来: `systemctl status mosquitto`, 看 `/var/log/mosquitto/mosquitto.log`
- ESP32 连不上: 先本机 mosquitto_sub/pub 自测 → 再外部 IP 测 → 再看 ESP32 串口日志(连上会打印 IP)
- 安全组改了不生效: 阿里云安全组是"白名单", 加规则后等 1-2 分钟
