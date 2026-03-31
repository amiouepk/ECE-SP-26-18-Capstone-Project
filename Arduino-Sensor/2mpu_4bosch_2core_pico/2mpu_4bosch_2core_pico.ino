#include <WiFi.h>
#include <WebSocketsServer.h>
#include <Arduino.h>
#include "pico/mutex.h"
#include <queue>

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// ==========================================
// NETWORK SETTINGS & QUEUE
// ==========================================
const char *ssid = "Rpi Pico";
const char *password = "password";

WebSocketsServer webSocket(81);
volatile int activeClients = 0; 
volatile bool systemReady = false; 

// Pico Mutex
mutex_t queueMutex;
std::queue<String> dataQueue;
const size_t MAX_QUEUE_SIZE = 50; 

// ==========================================
// HARDWARE SETTINGS (4x BNO, 2x MPU)
// ==========================================
#define BNOs        4           
#define MPUs        2           
#define BNO_MUX_OFFSET 2        // BNOs start at mux port 2
#define TCAADDR     0x70        // I2C address of TCA9548
#define BNO_ADDR    0x4B        // I2C address of BNO085

#define ACC_REPORT   0x01   
#define GYRO_REPORT  0x02   
#define MAG_REPORT   0x03   
#define TIME_REPORT  0xFB   

Adafruit_MPU6050 mpu[MPUs];

// Global Data Arrays (Updated by background loop)
int16_t iax[BNOs], iay[BNOs], iaz[BNOs]; 
int16_t igx[BNOs], igy[BNOs], igz[BNOs]; 
int16_t imx[BNOs], imy[BNOs], imz[BNOs]; 
sensors_event_t mpu_a[MPUs], mpu_g[MPUs], mpu_temp[MPUs];

// Timing Configuration
unsigned long lastQueueTime = 0;
unsigned long queueInterval = 19;  // Default ~50 Hz (Adjustable via Serial)

// Scaling Factors for BNO
const float kACC = 1.0/9.80665/256;
const float kGYR = 180.0/M_PI/512;
const float kMAG = 0.01/16;

// ==========================================
// HARDWARE HELPER FUNCTIONS
// ==========================================
void tcaselect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

static void request_reports(uint8_t bno) {
  tcaselect(bno + BNO_MUX_OFFSET);
  
  // Set BNO reporting rate to 10ms (100 Hz)
  long SENSOR_US = 10000L;

  static const uint8_t cmd_acc[]  = {21, 0, 2, 0, 0xFD, ACC_REPORT,  0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR); Wire.write(cmd_acc, sizeof(cmd_acc)); Wire.endTransmission();

  static const uint8_t cmd_gyro[] = {21, 0, 2, 0, 0xFD, GYRO_REPORT, 0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR); Wire.write(cmd_gyro, sizeof(cmd_gyro)); Wire.endTransmission();

  static const uint8_t cmd_mag[]  = {21, 0, 2, 0, 0xFD, MAG_REPORT,  0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR); Wire.write(cmd_mag, sizeof(cmd_mag)); Wire.endTransmission();
}

static void ensure_read_available(int16_t length) {
  if (!Wire.available()) {
    Wire.requestFrom((uint16_t)BNO_ADDR, (uint8_t)(4+length));
    Wire.read(); Wire.read(); Wire.read(); Wire.read();
  }
}

// Bare-metal SHTP parser (Fastest possible read)
static void check_report(uint8_t bno) {
  int16_t length;
  uint8_t channel, seqnum;

  tcaselect(bno + BNO_MUX_OFFSET);

  Wire.requestFrom((uint16_t)BNO_ADDR, (uint8_t)5);
  length  = Wire.read();
  length |= (Wire.read() & 0x7F) << 8;
  channel = Wire.read();
  seqnum  = Wire.read();
  length -= 4;

  if (length <= 0 || length > 1000) return;

  while (length) {
    uint8_t buf[20];
    uint16_t n = 0;

    ensure_read_available(length);
    buf[n++] = Wire.read();
    length--;

    if (channel==3 && buf[0]==TIME_REPORT && length >= 5-1) {
      for (uint8_t i=1; i<5; i++) { ensure_read_available(length); buf[i] = Wire.read(); length--; }
      continue;
    }
    if (channel==3 && buf[0]==ACC_REPORT && length >= 10-1) {
      for (uint8_t i=1; i<10; i++) { ensure_read_available(length); buf[i] = Wire.read(); length--; }
      iax[bno] = *(int16_t*)&buf[4]; iay[bno] = *(int16_t*)&buf[6]; iaz[bno] = *(int16_t*)&buf[8];
      continue;
    }
    if (channel==3 && buf[0]==GYRO_REPORT && length >= 10-1) {
      for (uint8_t i=1; i<10; i++) { ensure_read_available(length); buf[i] = Wire.read(); length--; }
      igx[bno] = *(int16_t*)&buf[4]; igy[bno] = *(int16_t*)&buf[6]; igz[bno] = *(int16_t*)&buf[8];
      continue;
    }
    if (channel==3 && buf[0]==MAG_REPORT && length >= 10-1) {
      for (uint8_t i=1; i<10; i++) { ensure_read_available(length); buf[i] = Wire.read(); length--; }
      imx[bno] = *(int16_t*)&buf[4]; imy[bno] = *(int16_t*)&buf[6]; imz[bno] = *(int16_t*)&buf[8];
      continue; 
    }

    // Drain unknown packets to keep buffer clean
    while (length) {
      ensure_read_available(length);
      Wire.read();
      length--;
    }
  }
}

// ==========================================
// CORE 1: NETWORKING & CONSUMER
// ==========================================
void onWebSocketEvent(uint8_t clientNum, WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      if (activeClients > 0) activeClients--; 
      Serial.printf("[%u] Disconnected\n", clientNum);
      break;
    case WStype_CONNECTED:
      webSocket.sendTXT(clientNum, "IMU Server Connected");
      activeClients++; 
      Serial.printf("[%u] Connected\n", clientNum);
      break;
  }
}

void setup1() {
  while (!systemReady) { delay(10); } // Wait for Core 0 hardware setup
  
  Serial.println("Configuring access point...");
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());

  webSocket.begin();
  webSocket.onEvent(onWebSocketEvent);
  Serial.println("Core 1: WiFi & WebSockets Ready");
}

void loop1() {
  webSocket.loop();

  if (activeClients > 0) {
    String msgToSend = "";
    bool hasData = false;

    // Lock Mutex, read queue, unlock Mutex
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
    // Keep queue empty if no one is listening
    mutex_enter_blocking(&queueMutex);
    while (!dataQueue.empty()) { dataQueue.pop(); }
    mutex_exit(&queueMutex);
  }

  // for debuging
  // delay(1);
}

// ==========================================
// CORE 0: HARDWARE, MATH & PRODUCER
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(2000); 

  // Initialize Pico Mutex
  mutex_init(&queueMutex);

  // Initialize I2C
  Wire.setSDA(4);
  Wire.setSCL(5);
  Wire.setClock(400000); // 400kHz Fast Mode
  Wire.begin();
  Serial.println("I2C initialized at 400kHz.");

  // Initialize MPUs on ports 0 and 1
  for (uint8_t i=0; i<MPUs; i++) {
    tcaselect(i);
    if (!mpu[i].begin()) { Serial.printf("Failed MPU%d\n", i); while(1) delay(10); }
    mpu[i].setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu[i].setGyroRange(MPU6050_RANGE_500_DEG);
    mpu[i].setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.printf("MPU %d configured.\n", i);
  }

  // Initialize BNO085s on ports 2-5
  for (uint8_t bno=0; bno<BNOs; bno++) {
    request_reports(bno);
    Serial.printf("BNO %d configured.\n", bno);
  }

  // Signal Core 1 to start networking
  systemReady = true; 
  Serial.println("\nAll sensors initialized!");
  Serial.println(">> Type target frequency (e.g., 25, 50) in Serial Monitor <<");
}

void loop() {
  unsigned long now = millis();

  // --- Dynamic Frequency Update ---
  if (Serial.available() > 0) {
    long inputHz = Serial.parseInt(); 
    while(Serial.available() > 0) { Serial.read(); }

    if (inputHz > 0) {
      queueInterval = 1000 / inputHz; 
      Serial.printf("\n[UPDATED] Output Frequency: %ld Hz (Interval: %lu ms)\n", inputHz, queueInterval);
    }
  }

  // ==========================================
  // ACQUISITION LOOP (Runs as fast as physically possible)
  // ==========================================
  
  // 1. Poll BNOs manually via SHTP
  for (uint8_t bno=0; bno<BNOs; bno++) {
    check_report(bno);
  }

  // 2. Poll MPUs
  for (uint8_t i=0; i<MPUs; i++) {
    tcaselect(i);
    mpu[i].getEvent(&mpu_a[i], &mpu_g[i], &mpu_temp[i]);
  }

  // Close MUX to keep bus quiet during string assembly
  Wire.beginTransmission(TCAADDR); Wire.write(0x00); Wire.endTransmission();

  // ==========================================
  // TRANSMISSION LOOP
  // ==========================================
  if (now - lastQueueTime >= queueInterval) {
    lastQueueTime = now;

    if (activeClients > 0) {
      String syncMsg = "";

      // Format BNOs: Accel/Gyro/Mag
      for (uint8_t bno=0; bno<BNOs; bno++) {
        syncMsg += "B" + String(bno) + ":" + 
                   String(kACC*iax[bno], 3) + "/" + String(-kACC*iay[bno], 3) + "/" + String(-kACC*iaz[bno], 3) + "/" +
                   String(kGYR*igx[bno], 3) + "/" + String(-kGYR*igy[bno], 3) + "/" + String(-kGYR*igz[bno], 3) + "/" +
                   String(kMAG*imx[bno], 3) + "/" + String(-kMAG*imy[bno], 3) + "/" + String(-kMAG*imz[bno], 3) + "|";
      }

      // Format MPUs: Accel/Gyro
      for (uint8_t i=0; i<MPUs; i++) {
        syncMsg += "M" + String(i) + ":" + 
                   String(mpu_a[i].acceleration.x / 9.80665, 3) + "/" + String(mpu_a[i].acceleration.y / 9.80665, 3) + "/" + String(mpu_a[i].acceleration.z / 9.80665, 3) + "/" +
                   String(mpu_g[i].gyro.x * 180.0 / M_PI, 3) + "/" + String(mpu_g[i].gyro.y * 180.0 / M_PI, 3) + "/" + String(mpu_g[i].gyro.z * 180.0 / M_PI, 3) + "|";
      }

      // Queue it up securely
      mutex_enter_blocking(&queueMutex);
      if (dataQueue.size() < MAX_QUEUE_SIZE) {
        dataQueue.push(syncMsg);
      }
      mutex_exit(&queueMutex);
    }
  }
  //debug
  // delay(1);
}