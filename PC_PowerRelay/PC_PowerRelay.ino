// PC_PowerRelay.ino — ESP32 远程开机控制器固件 v5
// 需求文档: projects/esp32/远程控制开机.txt V1.0
// 功能: 连 WiFi → 连 MQTT → 订阅 device/pc_power → 收到 "trigger" 驱动继电器 0.4s 模拟按电源键
// 硬件: ESP32 DevKitC + 5V 光耦继电器(低电平触发), 继电器 IN → GPIO4
//
// v7 (2026-09-15): GPIO4 改【开漏模式】——解决 3.3V 单片机驱动 5V 低电平触发模块的经典坑
//   实测: 模块 IN 悬空=断开, 碰 0V=吸合, 碰 3.3V=也吸合(5V 供电下 3.3V 仍算低电平)
//   方案: 开漏模式下 digitalWrite(HIGH)=高阻悬空(断开), digitalWrite(LOW)=0V(吸合)
//   逻辑: 默认 HIGH(悬空, 断开), trigger 时 LOW(0V, 吸合)0.4s, 再回 HIGH(悬空, 断开)

#include <WiFi.h>
#include <PubSubClient.h>

// ========== 配置项(烧录前必改) ==========
const char* ssid        = "YOUR_WIFI_NAME";        // 家庭 WiFi 名（烧录前填实际值）
const char* password    = "YOUR_WIFI_PASSWORD";
const char* mqttServer  = "YOUR_ECS_IP";   // 阿里云 ECS 公网 IP（烧录前填实际值）
const uint16_t mqttPort = 8081;             // 公网端口(安全组放行)
const char* mqttTopic   = "device/pc_power";// 订阅主题
#define RELAY_PIN 4                          // 继电器 IN(开漏驱动; 悬空=断开, 0V=吸合; 避开 strapping GPIO2)
const unsigned long COOL_DOWN_TIME = 10000; // 冷却 10s 防重复触发
const unsigned long PRESS_DURATION = 400;   // 吸合 0.4s = 按一下电源键
// ========================================

WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastTriggerTime = 0;  // 上次触发时刻(冷却用)

// 模拟按一次电源键: 继电器吸合 0.4s 后释放(和 MQTTTest 验证过的回调结构一致)
void pressPowerButton() {
  unsigned long now = millis();
  if (now - lastTriggerTime < COOL_DOWN_TIME) {
    Serial.print("[IGNORE] 冷却中, ");
    Serial.print((COOL_DOWN_TIME - (now - lastTriggerTime)) / 1000);
    Serial.println("s 后可再触发, 丢弃本次指令");
    return;
  }
  lastTriggerTime = now;
  Serial.println("[TRIGGER] 收到 trigger, 继电器吸合");
  digitalWrite(RELAY_PIN, LOW);   // 开漏拉低 0V: 光耦导通, 继电器吸合, COM-NO 导通 = 短接电源键
  delay(PRESS_DURATION);          // 0.4s(模拟按住电源键)
  digitalWrite(RELAY_PIN, HIGH);  // 开漏高=高阻悬空: 光耦截止, 继电器释放
  Serial.println("[TRIGGER] 继电器释放, 模拟按键松开");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.print("[MQTT] 主题: ");
  Serial.print(topic);
  Serial.print(" | payload: ");
  Serial.println(msg);
  if (msg == "trigger") {
    pressPowerButton();
  } else {
    Serial.println("[MQTT] 非 trigger, 忽略");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT_OPEN_DRAIN);  // 开漏: HIGH=高阻悬空(模块断开), LOW=0V(模块吸合)
  digitalWrite(RELAY_PIN, HIGH);          // 上电默认悬空 → 继电器断开(不误触发)
  Serial.println("===== ESP32 远程开机控制器 v7 =====");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  client.setServer(mqttServer, mqttPort);
  client.setCallback(mqttCallback);
}

void loop() {
  delay(10);   // 喂 IDLE 任务, 防任务看门狗(TG1WDT_SYS_RESET)

  // 非阻塞: WiFi 连上且 MQTT 断开时尝试重连(和 MQTTTest 验证过的写法一致)
  if (WiFi.status() == WL_CONNECTED && !client.connected()) {
    if (client.connect("ESP32-PCPower")) {
      client.subscribe(mqttTopic);
      Serial.print("[MQTT] 连接成功, 已订阅 ");
      Serial.println(mqttTopic);
    } else {
      Serial.printf("[MQTT] 连接失败 rc=%d\n", client.state());
    }
  }
  client.loop();  // 处理收包/回调
}
