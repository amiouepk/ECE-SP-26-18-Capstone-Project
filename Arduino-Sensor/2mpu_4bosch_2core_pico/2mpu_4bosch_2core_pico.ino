#include <WiFi.h>
#include <WebSocketsServer.h>
#include <Arduino.h>
#include "pico/mutex.h"
#include <queue>

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "SparkFun_BNO08x_Arduino_Library.h"
#include <Wire.h>

// ==========================================
// NETWORK SETTINGS & QUEUE
// ==========================================
const char *ssid = "Rpi Pico";
const char *password = "password";

WebSocketsServer webSocket(81);
volatile int activeClients = 0;
volatile bool systemReady = false;

mutex_t queueMutex;
std::queue<String> dataQueue;
const size_t MAX_QUEUE_SIZE = 50;

// ==========================================
// HARDWARE SETTINGS
// ==========================================
Adafruit_MPU6050 mpu1, mpu2;
BNO08x bno1, bno2, bno3, bno4;

#define TCAADDR     0x70
#define BNO08X_ADDR 0x4B   // default address (ADR high)
#define BNO08X_ADDR_ALT 0x4A // alternative address (ADR low)
#define BNO08X_INT  -1
#define BNO08X_RST  -1

// BNO data variables
float b1_x, b1_y, b1_z, b1_gx, b1_gy, b1_gz, b1_mx, b1_my, b1_mz;
float b2_x, b2_y, b2_z, b2_gx, b2_gy, b2_gz, b2_mx, b2_my, b2_mz;
float b3_x, b3_y, b3_z, b3_gx, b3_gy, b3_gz, b3_mx, b3_my, b3_mz;
float b4_x, b4_y, b4_z, b4_gx, b4_gy, b4_gz, b4_mx, b4_my, b4_mz;

sensors_event_t a1, g1, t1;
sensors_event_t a2, g2, t2;

// Timing Configuration
unsigned long lastQueueTime = 0;
unsigned long queueInterval = 40;  // Default 25 Hz
unsigned long lastBNOAcquisition = 0;

// ==========================================
// HARDWARE HELPER FUNCTIONS
// ==========================================
void tcaselect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
  delay(5);  // Increased from 500µs to 5ms for reliable switching
}

void tcaDisable() {
  Wire.beginTransmission(TCAADDR);
  Wire.write(0x00);
  Wire.endTransmission();
  delay(5);
}

// Check if a device responds at the given address on the current channel
bool probeAddress(uint8_t addr) {
  Wire.beginTransmission(addr);
  return (Wire.endTransmission() == 0);
}

// Scan a single channel, printing found devices
void scanChannel(uint8_t ch) {
  tcaselect(ch);
  delay(10);
  bool found = false;
  Serial.printf("  Channel %d: ", ch);
  for (uint8_t addr = 0x08; addr < 0x78; addr++) {
    if (probeAddress(addr)) {
      Serial.printf("0x%02X ", addr);
      found = true;
    }
  }
  if (!found) Serial.print("nothing found");
  Serial.println();
}

void scanI2CBus() {
  Serial.println("\n=== I2C Bus Scan ===");
  for (uint8_t ch = 0; ch < 6; ch++) {
    scanChannel(ch);
  }
  tcaDisable();
  Serial.println("=== Scan Complete ===\n");
}

// Read WHO_AM_I register of BNO08x (should return 0x19)
bool checkBNO08x(BNO08x &bno, uint8_t addr) {
  Wire.beginTransmission(addr);
  Wire.write(0x00);  // WHO_AM_I register
  if (Wire.endTransmission() != 0) return false;
  Wire.requestFrom(addr, (uint8_t)1);
  if (Wire.available()) {
    uint8_t whoami = Wire.read();
    Serial.printf("    WHO_AM_I = 0x%02X (expected 0x19)\n", whoami);
    return (whoami == 0x19);
  }
  return false;
}

void setReports(void) {
  tcaselect(2);
  bno1.enableAccelerometer(20);
  bno1.enableGyro(20);
  bno1.enableMagnetometer(20);

  tcaselect(3);
  bno2.enableAccelerometer(20);
  bno2.enableGyro(20);
  bno2.enableMagnetometer(20);

  tcaselect(4);
  bno3.enableAccelerometer(20);
  bno3.enableGyro(20);
  bno3.enableMagnetometer(20);

  tcaselect(5);
  bno4.enableAccelerometer(20);
  bno4.enableGyro(20);
  bno4.enableMagnetometer(20);

  Serial.println("BNO08x calibrated MEMS readings enabled at 50Hz");
}

void configureSensor(Adafruit_MPU6050 &mpu, int sensorNum) {
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);
  Serial.printf("MPU Sensor %d configured.\n", sensorNum);
}

// ==========================================
// CORE 1: NETWORKING & CONSUMER
// ==========================================
void setup_ap() {
  Serial.println("Configuring access point...");
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());
}

void onWebSocketEvent(uint8_t clientNum, WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[%u] Disconnected\n", clientNum);
      if (activeClients > 0) activeClients--;
      break;
    case WStype_CONNECTED:
      Serial.printf("[%u] Connected\n", clientNum);
      webSocket.sendTXT(clientNum, "IMU Server Connected");
      activeClients++;
      break;
    case WStype_TEXT:
      webSocket.broadcastTXT(payload, length);
      break;
  }
}

void setup1() {
  while (!systemReady) { delay(10); }
  setup_ap();
  webSocket.begin();
  webSocket.onEvent(onWebSocketEvent);
  Serial.println("Core 1: WiFi & WebSockets Ready");
}

void loop1() {
  webSocket.loop();

  if (activeClients > 0) {
    String msgToSend = "";
    bool hasData = false;

    mutex_enter_blocking(&queueMutex);
    if (!dataQueue.empty()) {
      msgToSend = dataQueue.front();
      dataQueue.pop();
      hasData = true;
    }
    mutex_exit(&queueMutex);

    if (hasData) {
      webSocket.broadcastTXT(msgToSend);
    }
  } else {
    mutex_enter_blocking(&queueMutex);
    while (!dataQueue.empty()) { dataQueue.pop(); }
    mutex_exit(&queueMutex);
  }
}

// ==========================================
// CORE 0: HARDWARE, MATH & PRODUCER
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(5000);

  mutex_init(&queueMutex);

  Wire.setSDA(4);
  Wire.setSCL(5);
  Wire.setClock(50000);  // 50kHz for reliable initialisation
  Wire.begin();
  Serial.println("I2C initialized at 50kHz for setup.");

  delay(2000);  // Extra power‑up time for all sensors

  scanI2CBus();

  // ---- Initialize MPUs (channels 0 and 1) ----
  tcaselect(0);
  delay(10);
  if (!mpu1.begin(0x68, &Wire)) {
    Serial.println("FATAL: Failed to find MPU1 on channel 0");
    while (1) { delay(10); }
  }
  configureSensor(mpu1, 1);

  tcaselect(1);
  delay(10);
  if (!mpu2.begin(0x68, &Wire)) {
    Serial.println("FATAL: Failed to find MPU2 on channel 1");
    while (1) { delay(10); }
  }
  configureSensor(mpu2, 2);

  // ---- Initialize BNOs (channels 2, 3, 4, 5) with retries & address fallback ----
  #define BNO_RETRIES 3
  #define BNO_RETRY_DELAY 100

  bool bno_ok[4] = {false, false, false, false};
  uint8_t channels[4] = {2, 3, 4, 5};
  BNO08x* bnoptr[4] = {&bno1, &bno2, &bno3, &bno4};
  uint8_t used_addr[4];

  for (int i = 0; i < 4; i++) {
    Serial.printf("\n--- Initializing BNO%d (channel %d) ---\n", i+1, channels[i]);
    bool ok = false;
    uint8_t addr_to_try[2] = {BNO08X_ADDR, BNO08X_ADDR_ALT};
    for (int a = 0; a < 2 && !ok; a++) {
      uint8_t try_addr = addr_to_try[a];
      for (int retry = 0; retry < BNO_RETRIES && !ok; retry++) {
        tcaselect(channels[i]);
        delay(50);  // Extra settling
        Serial.printf("  Attempt %d, address 0x%02X: ", retry+1, try_addr);
        if (bnoptr[i]->begin(try_addr, Wire, BNO08X_INT, BNO08X_RST)) {
          // Verify with WHO_AM_I
          if (checkBNO08x(*bnoptr[i], try_addr)) {
            ok = true;
            used_addr[i] = try_addr;
            Serial.printf("SUCCESS (addr 0x%02X)\n", try_addr);
          } else {
            Serial.println("WHO_AM_I mismatch");
          }
        } else {
          Serial.println("begin() failed");
        }
        delay(BNO_RETRY_DELAY);
      }
    }
    bno_ok[i] = ok;
    if (!ok) {
      Serial.printf("FATAL: BNO%d not detected on channel %d after all attempts.\n", i+1, channels[i]);
      while (1) { delay(10); }
    }
  }

  // After all BNOs are initialized, enable reports
  setReports();
  tcaDisable();

  // Bump I2C clock to 400kHz for faster data transfer
  Wire.setClock(400000);
  Serial.println("I2C bumped to 400kHz for runtime.");

  Serial.println("\nAll sensors initialized successfully!");
  Serial.printf("Used addresses: BNO1=0x%02X, BNO2=0x%02X, BNO3=0x%02X, BNO4=0x%02X\n",
                used_addr[0], used_addr[1], used_addr[2], used_addr[3]);
  Serial.println(">> Type target frequency (e.g., 25, 50) in Serial Monitor <<");

  systemReady = true;
}

void pollBNO(BNO08x &bno, float &ax, float &ay, float &az,
                           float &gx, float &gy, float &gz,
                           float &mx, float &my, float &mz) {
  if (bno.wasReset()) setReports();
  uint8_t drain = 0;
  while (bno.getSensorEvent() && drain < 3) {
    uint8_t id = bno.getSensorEventID();
    if      (id == SENSOR_REPORTID_ACCELEROMETER)        { ax = bno.getAccelX(); ay = bno.getAccelY(); az = bno.getAccelZ(); }
    else if (id == SENSOR_REPORTID_GYROSCOPE_CALIBRATED) { gx = bno.getGyroX();  gy = bno.getGyroY();  gz = bno.getGyroZ(); }
    else if (id == SENSOR_REPORTID_MAGNETIC_FIELD)       { mx = bno.getMagX();   my = bno.getMagY();   mz = bno.getMagZ(); }
    drain++;
  }
}

void loop() {
  unsigned long now = millis();

  // --- Dynamic Frequency Update via Serial ---
  if (Serial.available() > 0) {
    long inputHz = Serial.parseInt();
    while (Serial.available() > 0) { Serial.read(); }
    if (inputHz > 0) {
      queueInterval = 1000 / inputHz;
      Serial.printf("\n[UPDATED] Output Frequency: %ld Hz (Interval: %lu ms)\n", inputHz, queueInterval);
    }
  }

  // ==========================================
  // ACQUISITION LOOP
  // ==========================================

  // --- Poll BNO08x sensors (~66 Hz max) ---
  if (now - lastBNOAcquisition >= 15) {
    lastBNOAcquisition = now;

    tcaselect(2);
    pollBNO(bno1, b1_x, b1_y, b1_z, b1_gx, b1_gy, b1_gz, b1_mx, b1_my, b1_mz);

    tcaselect(3);
    pollBNO(bno2, b2_x, b2_y, b2_z, b2_gx, b2_gy, b2_gz, b2_mx, b2_my, b2_mz);

    tcaselect(4);
    pollBNO(bno3, b3_x, b3_y, b3_z, b3_gx, b3_gy, b3_gz, b3_mx, b3_my, b3_mz);

    tcaselect(5);
    pollBNO(bno4, b4_x, b4_y, b4_z, b4_gx, b4_gy, b4_gz, b4_mx, b4_my, b4_mz);
  }

  // --- Poll MPU6050 sensors ---
  tcaselect(0); mpu1.getEvent(&a1, &g1, &t1);
  tcaselect(1); mpu2.getEvent(&a2, &g2, &t2);

  tcaDisable();

  // ==========================================
  // TRANSMISSION LOOP
  // ==========================================
  if (now - lastQueueTime >= queueInterval) {
    lastQueueTime = now;

    if (activeClients > 0) {
      String syncMsg = "";

      // BNO1–4 (9 fields each: ax,ay,az,gx,gy,gz,mx,my,mz)
      syncMsg += String(b1_x)+","+String(b1_y)+","+String(b1_z)+","+String(b1_gx)+","+String(b1_gy)+","+String(b1_gz)+","+String(b1_mx)+","+String(b1_my)+","+String(b1_mz)+",";
      syncMsg += String(b2_x)+","+String(b2_y)+","+String(b2_z)+","+String(b2_gx)+","+String(b2_gy)+","+String(b2_gz)+","+String(b2_mx)+","+String(b2_my)+","+String(b2_mz)+",";
      syncMsg += String(b3_x)+","+String(b3_y)+","+String(b3_z)+","+String(b3_gx)+","+String(b3_gy)+","+String(b3_gz)+","+String(b3_mx)+","+String(b3_my)+","+String(b3_mz)+",";
      syncMsg += String(b4_x)+","+String(b4_y)+","+String(b4_z)+","+String(b4_gx)+","+String(b4_gy)+","+String(b4_gz)+","+String(b4_mx)+","+String(b4_my)+","+String(b4_mz)+",";

      // MPU1–2 (6 fields each: ax,ay,az,gx,gy,gz)
      syncMsg += String(a1.acceleration.x,2)+","+String(a1.acceleration.y,2)+","+String(a1.acceleration.z,2)+","+String(g1.gyro.x,2)+","+String(g1.gyro.y,2)+","+String(g1.gyro.z,2)+",";
      syncMsg += String(a2.acceleration.x,2)+","+String(a2.acceleration.y,2)+","+String(a2.acceleration.z,2)+","+String(g2.gyro.x,2)+","+String(g2.gyro.y,2)+","+String(g2.gyro.z,2);

      mutex_enter_blocking(&queueMutex);
      if (dataQueue.size() < MAX_QUEUE_SIZE) {
        dataQueue.push(syncMsg);
      }
      mutex_exit(&queueMutex);
    }
  }
}