#include <Wire.h>
#define MUX_ADDR 0x70

void selectMuxChannel(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(MUX_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

void closeMux() {
  Wire.beginTransmission(MUX_ADDR);
  Wire.write(0x00);
  Wire.endTransmission();
}

void scanChannel(uint8_t channel) {
  selectMuxChannel(channel);
  delay(10);

  Serial.print("--- MUX Channel ");
  Serial.print(channel);
  Serial.println(" ---");

  int found = 0;
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("  Device at 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);

      // Annotate known addresses
      if (address == 0x68 || address == 0x69) Serial.print("  <-- MPU6050");
      if (address == 0x4A || address == 0x4B) Serial.print("  <-- BNO08x");
      if (address == 0x70)                    Serial.print("  <-- TCA9548A MUX");
      Serial.println();
      found++;
    }
  }

  if (found == 0) Serial.println("  (nothing found)");
}

void setup() {
  Serial.begin(115200);
  while (!Serial);
  delay(1000);

  Wire.setSDA(0);
  Wire.setSCL(1);
  Wire.begin();

  Serial.println("=============================");
  Serial.println(" Full MUX I2C Scanner");
  Serial.println("=============================");
}

void loop() {
  for (uint8_t ch = 0; ch < 8; ch++) {
    scanChannel(ch);
  }
  closeMux();

  Serial.println("\nScan complete. Waiting 5s...\n");
  delay(5000);
}