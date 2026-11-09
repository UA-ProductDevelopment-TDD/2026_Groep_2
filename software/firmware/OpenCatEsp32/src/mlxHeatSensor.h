#ifndef MLX_HEAT_SENSOR_H
#define MLX_HEAT_SENSOR_H

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>

#if __has_include("../secrets.h")
#include "../secrets.h"
#elif __has_include("secrets.h")
#include "secrets.h"
#else
#define WIFI_SSID "MF’s iPhone"
#define WIFI_PASSWORD "manufortems"
#define SERVER_HOST "172.20.10.3"
#define SERVER_PORT 8000
#endif

extern SemaphoreHandle_t i2cBusMutex;

// MLX90614 constants
static const uint8_t MLX_I2C_ADDR = 0x5A;
static const uint8_t MLX_REG_TAMBIENT = 0x06;
static const uint8_t MLX_REG_TOBJECT1 = 0x07;
static const unsigned long MLX_SEND_INTERVAL_MS = 250;  // 4 readings/second
static const unsigned long MLX_WIFI_RETRY_MS = 10000;

static String mlxSensorUrl;
static unsigned long mlxLastSend = 0;
static unsigned long mlxLastWifiAttempt = 0;
static unsigned long mlxOkCount = 0;
static unsigned long mlxFailCount = 0;
static bool mlxInitialized = false;

// CRC-8 calculation for MLX90614 SMBus PEC validation
static inline uint8_t mlx_crc8(uint8_t crc, uint8_t data) {
  crc ^= data;
  for (int i = 0; i < 8; i++) {
    crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1;
  }
  return crc;
}

// Read 16-bit register with PEC check, 100 kHz SMBus clock, and thread-safe bus mutex
static bool mlxReadReg(uint8_t reg, uint16_t &value) {
  if (i2cBusMutex != NULL && xSemaphoreTake(i2cBusMutex, pdMS_TO_TICKS(50)) != pdTRUE) {
    return false;
  }

  // MLX90614 SMBus requires 100 kHz clock
  Wire.setClock(100000);

  Wire.beginTransmission(MLX_I2C_ADDR);
  Wire.write(reg);
  uint8_t err = Wire.endTransmission(false);  // repeated start
  if (err != 0) {
    Wire.setClock(400000);
    if (i2cBusMutex != NULL) xSemaphoreGive(i2cBusMutex);
    return false;
  }
  if (Wire.requestFrom(MLX_I2C_ADDR, (uint8_t)3) != 3) {
    Wire.setClock(400000);
    if (i2cBusMutex != NULL) xSemaphoreGive(i2cBusMutex);
    return false;
  }

  uint8_t lo = Wire.read();
  uint8_t hi = Wire.read();
  uint8_t pec = Wire.read();

  // Restore 400 kHz for fast gyro sampling
  Wire.setClock(400000);
  if (i2cBusMutex != NULL) xSemaphoreGive(i2cBusMutex);

  uint8_t crc = 0;
  crc = mlx_crc8(crc, MLX_I2C_ADDR << 1);
  crc = mlx_crc8(crc, reg);
  crc = mlx_crc8(crc, (MLX_I2C_ADDR << 1) | 1);
  crc = mlx_crc8(crc, lo);
  crc = mlx_crc8(crc, hi);
  if (crc != pec) return false;

  value = ((uint16_t)hi << 8) | lo;
  return !(value & 0x8000);  // bit 15 error flag
}

// Convert raw 0.02K to Celsius
static bool mlxReadCelsius(uint8_t reg, float &celsius) {
  uint16_t raw;
  if (!mlxReadReg(reg, raw)) return false;
  celsius = raw * 0.02f - 273.15f;
  return true;
}

static void mlxConnectWifi() {
  mlxLastWifiAttempt = millis();
  Serial.printf("\n[MLX] Connecting to WiFi '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

// Setup hook called from setup()
inline void initMlxHeatSensor() {
  Serial.println("\n[MLX] Initializing MLX90614 Heat Sensor...");
  mlxSensorUrl = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/api/sensor";

  // Probe I2C bus for 0x5A with mutex at 100 kHz
  if (i2cBusMutex != NULL && xSemaphoreTake(i2cBusMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
    Wire.setClock(100000);
    Wire.beginTransmission(MLX_I2C_ADDR);
    if (Wire.endTransmission() == 0) {
      Serial.println("[MLX] MLX90614 detected at I2C address 0x5A!");
    } else {
      Serial.println("[MLX] WARNING: MLX90614 not detected at 0x5A.");
    }
    Wire.setClock(400000);
    xSemaphoreGive(i2cBusMutex);
  }

  Serial.printf("[MLX] Connecting to WiFi '%s' ", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(400);
    Serial.print('.');
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[MLX] WiFi connected! Dog IP: %s\n", WiFi.localIP().toString().c_str());
#ifdef WEB_SERVER
    extern bool webServerConnected;
    extern WebSocketsServer webSocket;
    extern void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length);
    webServerConnected = true;
    webSocket.begin();
    webSocket.onEvent(handleWebSocketEvent);
    Serial.printf("[MLX] OpenCat WebSocket server listening on ws://%s:81\n", WiFi.localIP().toString().c_str());
#endif
  } else {
    Serial.println("\n[MLX] WiFi connection taking time; loop will keep trying.");
  }

  mlxLastWifiAttempt = millis();
  mlxInitialized = true;
}

// Non-blocking loop hook called from loop()
inline void mlxLoop() {
  if (!mlxInitialized) return;
  unsigned long now = millis();

  // 1. Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    if (now - mlxLastWifiAttempt > MLX_WIFI_RETRY_MS) {
      mlxConnectWifi();
    }
    return;
  }

  // Activate OpenCat WebSocket server on first successful WiFi connection
#ifdef WEB_SERVER
  extern bool webServerConnected;
  extern WebSocketsServer webSocket;
  extern void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length);
  if (!webServerConnected) {
    webServerConnected = true;
    webSocket.begin();
    webSocket.onEvent(handleWebSocketEvent);
    Serial.printf("\n[MLX] WiFi connected! Dog IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("[MLX] OpenCat WebSocket server listening on ws://%s:81\n", WiFi.localIP().toString().c_str());
  }
#endif

  // 2. Telemetry interval (250 ms = 4 Hz)
  if (now - mlxLastSend < MLX_SEND_INTERVAL_MS) return;
  mlxLastSend = now;

  // 3. Read heat sensor
  float ambient = 0.0f;
  float object = 0.0f;
  if (!mlxReadCelsius(MLX_REG_TAMBIENT, ambient) || !mlxReadCelsius(MLX_REG_TOBJECT1, object)) {
    mlxFailCount++;
    if (mlxFailCount % 20 == 1) {
      Serial.println("[MLX] Sensor read retry...");
    }
    return;
  }

  // 4. POST to server using local HTTPClient
  char body[96];
  snprintf(body, sizeof(body), "{\"temperature\":%.2f,\"ambient\":%.2f}", object, ambient);

  HTTPClient http;
  http.setConnectTimeout(400);
  http.setTimeout(400);

  if (http.begin(mlxSensorUrl)) {
    http.addHeader("Content-Type", "application/json");
    int code = http.POST((uint8_t *)body, strlen(body));
    http.end();

    if (code == 200) {
      mlxOkCount++;
    } else {
      mlxFailCount++;
    }

    if ((mlxOkCount + mlxFailCount) % 8 == 0) {
      Serial.printf("[MLX] Object %.2f C | Ambient %.2f C -> Server HTTP %d (OK: %lu, Fail: %lu)\n",
                    object, ambient, code, mlxOkCount, mlxFailCount);
    }
  } else {
    mlxFailCount++;
  }
}

#endif  // MLX_HEAT_SENSOR_H
