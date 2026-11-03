// MLX90614 IR temperature sensor test on Arduino UNO R4 + Grove Base Shield.
// The sensor is on the hardware I2C bus (Grove I2C port), address 0x5A.
// Prints ambient and object temperature to Serial at 115200 baud.

#include <Wire.h>

const uint8_t MLX_ADDR = 0x5A;   // default MLX90614 address
const uint8_t REG_TAMBIENT = 0x06;
const uint8_t REG_TOBJECT1 = 0x07;

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
  uint8_t lo  = Wire.read();
  uint8_t hi  = Wire.read();
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

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}
  Wire.begin();
  Wire.setClock(100000);  // SMBus max 100 kHz
  Serial.println("MLX90614 test (hardware I2C)");
}

void loop() {
  float ambient, object;
  bool okA = readCelsius(REG_TAMBIENT, ambient);
  bool okO = readCelsius(REG_TOBJECT1, object);

  if (okA && okO) {
    Serial.print("Ambient: ");
    Serial.print(ambient, 2);
    Serial.print(" C   Object: ");
    Serial.print(object, 2);
    Serial.println(" C");
  } else {
    Serial.println("Read failed - check the sensor cable");
  }
  delay(500);
}
