/*
OLIMEX ESP32-POE DV10 Ventilation → MQTT → QuestDB
FIXED COMPILER ERRORS - PlatformIO READY

Commands:
0=Off 1=Reduced 2=Normal 3=Auto
r=Read a=AutoRead i=Interval m=Menu
*/

#include <ModbusMaster.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ======================== FILL YOUR CREDENTIALS HERE ========================
const char* ssid = "YOUR WIFI";
const char* password = "YOUR WIFI PASS";
const char* mqtt_server = "172.20.10.5"; //UPDATE TO HOST IP 
const int mqtt_port = 1883;
const char* mqtt_user = "edgeuser";
const char* mqtt_password = "Optilogic25";

const char* group_id = "Ventilation";
const char* edge_node_id = "OLIMEX_POE";
const char* device_id = "DV10";

unsigned long autoReadInterval = 10000;  // 10 seconds
// ============================================================================

WiFiClient espClient;
PubSubClient mqttClient(espClient);

#define RX_PIN 36
#define TX_PIN 4
#define MAX485_DE 5
#define MAX485_RE_NEG 14
#define BAUD_RATE 9600
#define MODBUS_SLAVE_ID 1

ModbusMaster modbus;
bool autoReadEnabled = true;
unsigned long lastAutoRead = 0;

struct SensorData {
  float heatExchangerEfficiency;
  uint16_t runMode;
  float outdoorTemp, supplyAirTemp, supplyAirSetpointTemp, exhaustAirTemp, extractAirTemp;
  float supplyAirPressure, extractAirPressure;
  float supplyAirFlow, extractAirFlow, extraSupplyAirFlow, extraExtractAirFlow;
  uint16_t supplyFanRuntime, extractFanRuntime;
  unsigned long timestamp;
  bool dataValid;
  int successfulReads;
};
SensorData currentData = {0};

void preTransmission() {
  digitalWrite(MAX485_RE_NEG, HIGH);
  digitalWrite(MAX485_DE, HIGH);
}

void postTransmission() {
  digitalWrite(MAX485_RE_NEG, LOW);
  digitalWrite(MAX485_DE, LOW);
}

void setupWiFi() {
  Serial.print("\nConnecting to WiFi: ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected");
    Serial.print("IP: "); Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ WiFi failed!");
  }
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Connecting MQTT ");
    
    String clientId = String(edge_node_id) + "_" + String(random(0xffff), HEX);
    
    // Create proper payloads as char arrays
    char nbirthPayload[256];
    snprintf(nbirthPayload, sizeof(nbirthPayload), 
      "{\"timestamp\":%lu,\"seq\":0,\"metrics\":[{\"name\":\"NodeControl/Rebirth\",\"value\":false}]}", 
      millis());
    
    if (mqttClient.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
      Serial.println("✓ MQTT connected");
      
      String nbirthTopic = "spBv1.0/" + String(group_id) + "/NBIRTH/" + edge_node_id;
      mqttClient.publish(nbirthTopic.c_str(), nbirthPayload);
      
      char dbirthPayload[1024];
      snprintf(dbirthPayload, sizeof(dbirthPayload),
        "{\"timestamp\":%lu,\"seq\":1,\"metrics\":["
        "{\"name\":\"HeatExchangerEfficiency\",\"type\":\"Float\"},"
        "{\"name\":\"RunMode\",\"type\":\"Int16\"},"
        "{\"name\":\"OutdoorTemp\",\"type\":\"Float\"},"
        "{\"name\":\"SupplyAirTemp\",\"type\":\"Float\"},"
        "{\"name\":\"SupplyAirSetpointTemp\",\"type\":\"Float\"},"
        "{\"name\":\"ExhaustAirTemp\",\"type\":\"Float\"},"
        "{\"name\":\"ExtractAirTemp\",\"type\":\"Float\"},"
        "{\"name\":\"SupplyAirPressure\",\"type\":\"Float\"},"
        "{\"name\":\"ExtractAirPressure\",\"type\":\"Float\"},"
        "{\"name\":\"SupplyAirFlow\",\"type\":\"Float\"},"
        "{\"name\":\"ExtractAirFlow\",\"type\":\"Float\"},"
        "{\"name\":\"ExtraSupplyAirFlow\",\"type\":\"Float\"},"
        "{\"name\":\"ExtraExtractAirFlow\",\"type\":\"Float\"},"
        "{\"name\":\"SupplyFanRuntime\",\"type\":\"Int16\"},"
        "{\"name\":\"ExtractFanRuntime\",\"type\":\"Int16\"}"
        "]}", millis());
      
      String dbirthTopic = "spBv1.0/" + String(group_id) + "/DBIRTH/" + edge_node_id + "/" + device_id;
      mqttClient.publish(dbirthTopic.c_str(), dbirthPayload);
      
    } else {
      Serial.print("✗ rc="); Serial.print(mqttClient.state()); Serial.println(" retry 5s");
      delay(5000);
    }
  }
}

bool readScaledReg(uint16_t reg, float &value) {
  uint8_t result = modbus.readInputRegisters(reg, 1);
  if (result == modbus.ku8MBSuccess) {
    value = modbus.getResponseBuffer(0) / 10.0f;
    return true;
  }
  Serial.printf("Reg %d error: %d\n", reg, result);
  value = NAN;
  return false;
}

bool readRawReg(uint16_t reg, uint16_t &value) {
  uint8_t result = modbus.readInputRegisters(reg, 1);
  if (result == modbus.ku8MBSuccess) {
    value = modbus.getResponseBuffer(0);
    return true;
  }
  Serial.printf("Reg %d error: %d\n", reg, result);
  value = 0;
  return false;
}

void readAllSensors() {
  Serial.println("\n=== READING SENSORS ===");
  currentData.timestamp = millis();
  currentData.dataValid = false;
  int success = 0;
  
  if (readScaledReg(1, currentData.heatExchangerEfficiency)) success++;
  if (readRawReg(2, currentData.runMode)) success++;
  
  readScaledReg(0, currentData.outdoorTemp); if (!isnan(currentData.outdoorTemp)) success++;
  readScaledReg(6, currentData.supplyAirTemp); if (!isnan(currentData.supplyAirTemp)) success++;
  readScaledReg(7, currentData.supplyAirSetpointTemp); if (!isnan(currentData.supplyAirSetpointTemp)) success++;
  readScaledReg(8, currentData.exhaustAirTemp); if (!isnan(currentData.exhaustAirTemp)) success++;
  readScaledReg(19, currentData.extractAirTemp); if (!isnan(currentData.extractAirTemp)) success++;
  
  readScaledReg(12, currentData.supplyAirPressure); if (!isnan(currentData.supplyAirPressure)) success++;
  readScaledReg(13, currentData.extractAirPressure); if (!isnan(currentData.extractAirPressure)) success++;
  
  readScaledReg(14, currentData.supplyAirFlow); if (!isnan(currentData.supplyAirFlow)) success++;
  readScaledReg(15, currentData.extractAirFlow); if (!isnan(currentData.extractAirFlow)) success++;
  readScaledReg(292, currentData.extraSupplyAirFlow); if (!isnan(currentData.extraSupplyAirFlow)) success++;
  readScaledReg(293, currentData.extraExtractAirFlow); if (!isnan(currentData.extraExtractAirFlow)) success++;
  
  readRawReg(3, currentData.supplyFanRuntime); success++;
  readRawReg(4, currentData.extractFanRuntime); success++;
  
  currentData.successfulReads = success;
  currentData.dataValid = (success > 10);
  Serial.printf("✓ %d/%d sensors OK\n", success, 15);
}

void publishData() {
  if (!currentData.dataValid || !mqttClient.connected()) return;
  
  JsonDocument doc;
  doc["device_id"] = device_id;
  doc["timestamp"] = currentData.timestamp;
  doc["heat_exchanger_efficiency"] = currentData.heatExchangerEfficiency;
  doc["run_mode"] = (int)currentData.runMode;
  doc["outdoor_temp"] = currentData.outdoorTemp;
  doc["supply_air_temp"] = currentData.supplyAirTemp;
  doc["supply_air_setpoint_temp"] = currentData.supplyAirSetpointTemp;
  doc["exhaust_air_temp"] = currentData.exhaustAirTemp;
  doc["extract_air_temp"] = currentData.extractAirTemp;
  doc["supply_air_pressure"] = currentData.supplyAirPressure;
  doc["extract_air_pressure"] = currentData.extractAirPressure;
  doc["supply_air_flow"] = currentData.supplyAirFlow;
  doc["extract_air_flow"] = currentData.extractAirFlow;
  doc["extra_supply_air_flow"] = currentData.extraSupplyAirFlow;
  doc["extra_extract_air_flow"] = currentData.extraExtractAirFlow;
  doc["supply_air_fan_runtime"] = (int)currentData.supplyFanRuntime;
  doc["extract_air_fan_runtime"] = (int)currentData.extractFanRuntime;
  
  String payload;
  serializeJson(doc, payload);
  
  if (mqttClient.publish("sensors/OLIMEX_POE", payload.c_str())) {
    Serial.println("✓ Data sent to QuestDB");
  } else {
    Serial.println("✗ Publish failed");
  }
}

void writeFanMode(uint16_t mode) {
  if (mode > 3) {
    Serial.println("ERROR: Mode 0-3 only");
    return;
  }
  uint8_t result = modbus.writeSingleRegister(367, mode);
  if (result == modbus.ku8MBSuccess) {
    Serial.printf("✓ Fan mode %d OK\n", mode);
  } else {
    Serial.printf("✗ Fan mode ERROR: %d\n", result);
  }
}

void printMenu() {
  Serial.println("\n=== DV10 CONTROLLER ===");
  Serial.println("0=Off 1=Reduced 2=Normal 3=Auto");
  Serial.println("r=Read a=AutoRead i=Interval m=Menu");
  Serial.printf("Auto: %s (%lus) | WiFi: %s | MQTT: %s\n",
    autoReadEnabled ? "ON" : "OFF", autoReadInterval/1000,
    WiFi.status() == WL_CONNECTED ? "OK" : "NO",
    mqttClient.connected() ? "OK" : "NO");
}

void handleSerial() {
  if (Serial.available()) {
    char cmd = Serial.read();
    while (Serial.available()) Serial.read();
    
    switch (cmd) {
      case '0'...'3': 
        writeFanMode(cmd - '0'); 
        break;
      case 'r': 
        readAllSensors(); 
        publishData(); 
        break;
      case 'a': 
        autoReadEnabled = !autoReadEnabled; 
        Serial.printf("Auto %s\n", autoReadEnabled ? "ON" : "OFF"); 
        break;
      case 'i': {
        Serial.print("Seconds (5-300): ");
        while(!Serial.available()) delay(10);
        long sec = Serial.parseInt();
        if (sec >= 5 && sec <= 300) {
          autoReadInterval = sec * 1000UL;
          Serial.printf("Interval: %ld sec\n", sec);
        }
        break;
      }
      case 'm': 
        printMenu(); 
        break;
      default: 
        Serial.println("Unknown. 'm' for menu"); 
        break;
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== OLIMEX ESP32-POE → MQTT → QuestDB ===");
  
  pinMode(MAX485_RE_NEG, OUTPUT);
  pinMode(MAX485_DE, OUTPUT);
  digitalWrite(MAX485_RE_NEG, LOW);
  digitalWrite(MAX485_DE, LOW);
  
  Serial2.begin(BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
  modbus.begin(MODBUS_SLAVE_ID, Serial2);
  modbus.preTransmission(preTransmission);
  modbus.postTransmission(postTransmission);
  
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setBufferSize(2048);
  
  setupWiFi();
  printMenu();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    setupWiFi();
  }
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
  
  handleSerial();
  
  if (autoReadEnabled) {
    unsigned long now = millis();
    if (now - lastAutoRead >= autoReadInterval) {
      lastAutoRead = now;
      readAllSensors();
      publishData();
    }
  }
  
  delay(10);
}
