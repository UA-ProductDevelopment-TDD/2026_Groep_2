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

// MLX90614 constants
static const uint8_t MLX_I2C_ADDR = 0x5A;
static const uint8_t MLX_REG_TAMBIENT = 0x06;
static const uint8_t MLX_REG_TOBJECT1 = 0x07;
static const unsigned long MLX_SEND_INTERVAL_MS = 250;

static TaskHandle_t mlxTaskHandle = NULL;
static bool mlxSensorFound = false;

// CRC-8 calculation for MLX90614 SMBus PEC validation
static inline uint8_t mlx_crc8(uint8_t crc, uint8_t data) {
  crc ^= data;
  for (int i = 0; i < 8; i++) {
    crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1;
  }
  return crc;
}

// Read 16-bit register with PEC check
static bool mlxReadReg(uint8_t reg, uint16_t &value) {
  Wire.beginTransmission(MLX_I2C_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;  // repeated start
  if (Wire.requestFrom(MLX_I2C_ADDR, (uint8_t)3) != 3) return false;

  uint8_t lo = Wire.read();
  uint8_t hi = Wire.read();
  uint8_t pec = Wire.read();

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

// Dedicated FreeRTOS background task running on Core 0
// Reads MLX90614 and POSTs to main laptop server without disturbing gait motion on Core 1
static void mlxTaskLoop(void *pvParameters) {
  HTTPClient http;
  http.setReuse(true);
  http.setConnectTimeout(600);
  http.setTimeout(600);

  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/api/sensor";
  char jsonBody[128];
  unsigned long lastSend = 0;
  unsigned long lastWifiCheck = 0;
  unsigned long okCount = 0;
  unsigned long failCount = 0;

  for (;;) {
    unsigned long now = millis();

    // 1. WiFi connection management
    if (WiFi.status() != WL_CONNECTED) {
      if (now - lastWifiCheck > 5000) {
        lastWifiCheck = now;
        Serial.printf("[MLX] WiFi reconnecting to %s...\n", WIFI_SSID);
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      }
      vTaskDelay(pdMS_TO_TICKS(200));
      continue;
    }

    // 2. Rate limiting (4 times/sec = 250ms)
    if (now - lastSend < MLX_SEND_INTERVAL_MS) {
      vTaskDelay(pdMS_TO_TICKS(25));
      continue;
    }
    lastSend = now;

    // 3. Sensor reading
    float ambient = 0.0f;
    float object = 0.0f;
    if (!mlxReadCelsius(MLX_REG_TAMBIENT, ambient) || !mlxReadCelsius(MLX_REG_TOBJECT1, object)) {
      failCount++;
      if (failCount % 20 == 1) {
        Serial.println("[MLX] Sensor read failed - checking connection...");
      }
      vTaskDelay(pdMS_TO_TICKS(100));
      continue;
    }

    // 4. Send HTTP POST to laptop dashboard
    snprintf(jsonBody, sizeof(jsonBody), "{\"temperature\":%.2f,\"ambient\":%.2f}", object, ambient);
    if (http.begin(url)) {
      http.addHeader("Content-Type", "application/json");
      int code = http.POST((uint8_t *)jsonBody, strlen(jsonBody));
      http.end();

      if (code == 200) {
        okCount++;
      } else {
        failCount++;
      }

      if ((okCount + failCount) % 8 == 0) {
        Serial.printf("[MLX] Object %.2f C | Ambient %.2f C -> Server HTTP %d (OK: %lu, Fail: %lu)\n",
                      object, ambient, code, okCount, failCount);
      }
    } else {
      failCount++;
    }

    vTaskDelay(pdMS_TO_TICKS(50));
  }
}

// Initialize MLX90614 sensor and launch background WiFi reporter task
inline void initMlxHeatSensor() {
  Serial.println("\n[MLX] Initializing MLX90614 Heat Sensor & WiFi Streamer...");

  // Probe I2C bus for 0x5A
  Wire.beginTransmission(MLX_I2C_ADDR);
  if (Wire.endTransmission() == 0) {
    mlxSensorFound = true;
    Serial.println("[MLX] MLX90614 detected at I2C address 0x5A!");
  } else {
    Serial.println("[MLX] WARNING: MLX90614 not detected at 0x5A. Will still attempt reading.");
  }

  // Connect WiFi for telemetry and WebSockets
  Serial.printf("[MLX] Connecting to WiFi '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 8000) {
    delay(200);
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
    Serial.println("\n[MLX] WiFi connection taking longer; background task will continue retrying.");
  }

  // Launch sensor & telemetry task pinned to Core 0 (leaving Core 1 dedicated to servo gait PWM)
  xTaskCreatePinnedToCore(
    mlxTaskLoop,
    "MlxSensorTask",
    8192,
    NULL,
    1,
    &mlxTaskHandle,
    0
  );
  Serial.println("[MLX] Background sensor task started on Core 0.");
}

#endif  // MLX_HEAT_SENSOR_H
