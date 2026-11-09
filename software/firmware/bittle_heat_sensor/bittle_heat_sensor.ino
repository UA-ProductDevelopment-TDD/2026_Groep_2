// MLX90614 heat sensor on the Bittle's BiBoard V1 (ESP32) -> WiFi -> dashboard.
//
// Reads the DFRobot MLX90614 (I2C address 0x5A) in the Grove I2C port and POSTs
// the readings to the main server (POST /api/sensor), which shows them live on the
// dashboard (fire detection meter) and in VR.
//
// This is a standalone TEST sketch. Uploading it replaces the OpenCat firmware on
// the BiBoard, so the dog will not walk until you flash OpenCat again
// (Petoi Desktop App, or the UA-ProductDevelopment-TDD OpenCatEsp32 fork).
//
// Wifi name/password and the server IP live in secrets.h (ignored by Git).
// Copy secrets.example.h to secrets.h and fill it in.
//
// Board: "ESP32 Dev Module" (esp32:esp32:esp32). Serial monitor: 115200 baud.

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>

#include "secrets.h"  // WIFI_SSID, WIFI_PASSWORD, SERVER_HOST, SERVER_PORT

// BiBoard V1: the Grove I2C port and the IMU share the ESP32 default I2C bus
// (SDA = GPIO21, SCL = GPIO22). OpenCat itself calls Wire.begin() with the defaults.
const int I2C_SDA = 21;
const int I2C_SCL = 22;

const uint8_t MLX_ADDR = 0x5A;  // default MLX90614 address
const uint8_t REG_TAMBIENT = 0x06;
const uint8_t REG_TOBJECT1 = 0x07;

const unsigned long SEND_INTERVAL_MS = 250;     // 4 readings per second
const unsigned long WIFI_RETRY_MS = 10000;

HTTPClient http;
String sensorUrl;
unsigned long lastSend = 0;
unsigned long lastWifiAttempt = 0;
unsigned long okCount = 0;
unsigned long failCount = 0;

// SMBus CRC-8 (polynomial x^8 + x^2 + x + 1), used for the PEC byte.
uint8_t crc8(uint8_t crc, uint8_t data) {
  crc ^= data;
  for (int i = 0; i < 8; i++) crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1;
  return crc;
}

// Reads a 16-bit RAM register. Returns false on bus error or PEC mismatch.
bool readReg(uint8_t reg, uint16_t &value) {
  Wire.beginTransmission(MLX_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;  // repeated start
  if (Wire.requestFrom(MLX_ADDR, (uint8_t)3) != 3) return false;
  uint8_t lo = Wire.read();
  uint8_t hi = Wire.read();
  uint8_t pec = Wire.read();

  uint8_t crc = 0;
  crc = crc8(crc, MLX_ADDR << 1);
  crc = crc8(crc, reg);
  crc = crc8(crc, (MLX_ADDR << 1) | 1);
  crc = crc8(crc, lo);
  crc = crc8(crc, hi);
  if (crc != pec) return false;

  value = ((uint16_t)hi << 8) | lo;
  return !(value & 0x8000);  // bit 15 set = error flag
}

// Raw value is in units of 0.02 K.
bool readCelsius(uint8_t reg, float &celsius) {
  uint16_t raw;
  if (!readReg(reg, raw)) return false;
  celsius = raw * 0.02f - 273.15f;
  return true;
}

void scanI2c() {
  Serial.println("Scanning I2C bus...");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  device at 0x%02X%s\n", addr, addr == MLX_ADDR ? "  <- MLX90614" : "");
      found++;
    }
  }
  if (found == 0) Serial.println("  nothing found - check the sensor cable and the Grove I2C port");
}

void connectWifi() {
  lastWifiAttempt = millis();
  Serial.printf("Connecting to WiFi '%s' ", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print('.');
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nConnected. Dog IP: %s, server: http://%s:%d\n", WiFi.localIP().toString().c_str(), SERVER_HOST, SERVER_PORT);
  } else {
    Serial.println("\nWiFi connection failed (2.4 GHz network needed). Will retry.");
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\nBittle MLX90614 -> WiFi dashboard test");

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);  // SMBus max 100 kHz
  Wire.setTimeOut(50);
  scanI2c();

  sensorUrl = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/api/sensor";
  connectWifi();

  http.setReuse(true);
  http.setConnectTimeout(800);
  http.setTimeout(800);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWifiAttempt > WIFI_RETRY_MS) connectWifi();
    delay(100);
    return;
  }

  if (millis() - lastSend < SEND_INTERVAL_MS) return;
  lastSend = millis();

  float ambient, object;
  if (!readCelsius(REG_TAMBIENT, ambient) || !readCelsius(REG_TOBJECT1, object)) {
    failCount++;
    Serial.println("Sensor read failed - check the sensor cable");
    return;
  }

  char body[96];
  snprintf(body, sizeof(body), "{\"temperature\":%.2f,\"ambient\":%.2f}", object, ambient);

  if (!http.begin(sensorUrl)) {
    Serial.println("HTTP begin failed");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  int code = http.POST((uint8_t *)body, strlen(body));
  http.end();

  if (code == 200) {
    okCount++;
  } else {
    failCount++;
  }
  // Print about once per second to keep the serial monitor readable.
  if ((okCount + failCount) % 4 == 0) {
    Serial.printf("Object %.2f C  Ambient %.2f C  -> server HTTP %d (ok %lu, failed %lu)\n", object, ambient, code, okCount, failCount);
  }
}
