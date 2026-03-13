#include <Wire.h>

#define MUX_ADDR 0x70

void selectMuxChannel(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(MUX_ADDR);
  Wire.write(1 << channel);   // Open channel 0-7
  Wire.endTransmission();
}

void setup() {
  Serial.begin(115200);
  while (!Serial);
  
  Wire.setSDA(0);
  Wire.setSCL(1);
  Wire.begin();

  // Open whichever channel your MPU6050 is on
  selectMuxChannel(0);  // change 0 to match which mux port you wired SD0/SC0 to

  Serial.println("Scanning after mux channel select...");
}

void loop() {
  byte error, address;
  int nDevices = 0;

  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("Found at 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      nDevices++;
    }
  }

  if (nDevices == 0) Serial.println("No devices found.");
  else Serial.println("Done.");
  delay(5000);
}