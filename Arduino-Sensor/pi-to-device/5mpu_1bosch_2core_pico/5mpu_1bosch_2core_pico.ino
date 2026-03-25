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
Adafruit_MPU6050 mpu1, mpu2, mpu3, mpu4, mpu5;
BNO08x myIMU;

#define TCAADDR 0x70
#define BNO08X_ADDR 0x4B
#define BNO08X_INT  -1
#define BNO08X_RST  -1

// Calibrated BNO variables (Replace the int16_t ones)
float b_x = 0.0, b_y = 0.0, b_z = 0.0;
float b_gx = 0.0, b_gy = 0.0, b_gz = 0.0;
float b_mx = 0.0, b_my = 0.0, b_mz = 0.0;

sensors_event_t a1, g1, t1;
sensors_event_t a2, g2, t2;
sensors_event_t a3, g3, t3;
sensors_event_t a4, g4, t4;
sensors_event_t a5, g5, t5;

// Timing Configuration
unsigned long lastQueueTime = 0;
unsigned long queueInterval = 40;  // Default 25 Hz (Adjustable via Serial)
unsigned long lastBNOAcquisition = 0;

// ==========================================
// HARDWARE HELPER FUNCTIONS
// ==========================================
void tcaselect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

void setReports(void) {
  // Request calibrated data every 20ms (50 Hz)
  myIMU.enableAccelerometer(20);
  myIMU.enableGyro(20);
  myIMU.enableMagnetometer(20);
  Serial.println("BNO08x Calibrated MEMS readings enabled at 50Hz");
}

void configureSensor(Adafruit_MPU6050 &mpu, int sensorNum) {
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);
  Serial.printf("Sensor %d configured.\n", sensorNum);
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
  Wire.setClock(400000); // 400kHz fast mode 
  Wire.begin();
  Serial.println("I2C initialized at 100kHz.");

  // Initialize MPUs
  delay(10);
  tcaselect(0); delay(5);
  if (!mpu1.begin(0x68, &Wire)) { Serial.println("Failed MPU1"); while(1){delay(10);} }
  configureSensor(mpu1, 1);

  tcaselect(1);
  if (!mpu2.begin(0x68, &Wire)) { Serial.println("Failed MPU2"); while(1){delay(10);} }
  configureSensor(mpu2, 2);

  tcaselect(2);
  if (!mpu3.begin(0x68, &Wire)) { Serial.println("Failed MPU3"); while(1){delay(10);} }
  configureSensor(mpu3, 3);

  tcaselect(3);
  if (!mpu4.begin(0x68, &Wire)) { Serial.println("Failed MPU4"); while(1){delay(10);} }
  configureSensor(mpu4, 4);

  tcaselect(4);
  if (!mpu5.begin(0x68, &Wire)) { Serial.println("Failed MPU5"); while(1){delay(10);} }
  configureSensor(mpu5, 5);

  // Initialize BNO08x
  tcaselect(5);
  if (myIMU.begin(BNO08X_ADDR, Wire, BNO08X_INT, BNO08X_RST) == false) {
    Serial.println("BNO08x not detected. Freezing...");
    while(1){delay(10);}
  }
  setReports();

  Serial.println("\nAll sensors initialized!");
  Serial.println(">> Type target frequency (e.g., 25, 50) in Serial Monitor <<");
  
  systemReady = true; 
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
  // ACQUISITION LOOP: High-Speed Polling
  // ==========================================
  
  // --- 1. Poll BNO08x ---
  // We only check the BNO every 15ms (~66 Hz max) to keep the bus free
  if (now - lastBNOAcquisition >= 15) { 
    lastBNOAcquisition = now;
    
    tcaselect(5); 
    delayMicroseconds(250); // 0.25ms instead of 2.0ms! Much faster.

    if (myIMU.wasReset()) { 
      setReports(); 
    }

    // Drain cap reduced to 3 to prevent bus-hogging
    uint8_t drainCount = 0;
    while (myIMU.getSensorEvent() && drainCount < 3) {
      uint8_t reportID = myIMU.getSensorEventID();
      
      if (reportID == SENSOR_REPORTID_ACCELEROMETER) {
        b_x = myIMU.getAccelX(); b_y = myIMU.getAccelY(); b_z = myIMU.getAccelZ();
      } else if (reportID == SENSOR_REPORTID_GYROSCOPE_CALIBRATED) {
        b_gx = myIMU.getGyroX(); b_gy = myIMU.getGyroY(); b_gz = myIMU.getGyroZ();
      } else if (reportID == SENSOR_REPORTID_MAGNETIC_FIELD) {
        b_mx = myIMU.getMagX(); b_my = myIMU.getMagY(); b_mz = myIMU.getMagZ();
      }
      drainCount++;
    }
  }

  // --- 2. Poll MPUs ---
  tcaselect(0); mpu1.getEvent(&a1, &g1, &t1);
  tcaselect(1); mpu2.getEvent(&a2, &g2, &t2);
  tcaselect(2); mpu3.getEvent(&a3, &g3, &t3);
  tcaselect(3); mpu4.getEvent(&a4, &g4, &t4);
  tcaselect(4); mpu5.getEvent(&a5, &g5, &t5);

  // Close MUX
  Wire.beginTransmission(TCAADDR);
  Wire.write(0x00);
  Wire.endTransmission();

  // ==========================================
  // TRANSMISSION LOOP: Format and queue data at requested Hz
  // ==========================================
  if (now - lastQueueTime >= queueInterval) {
    lastQueueTime = now;

    if (activeClients > 0) {
      // Build one massive synchronized string from the global state
      String syncMsg = String(b_x) + "," + String(b_y) + "," + String(b_z) + "," +
                              String(b_gx) + "," + String(b_gy) + "," + String(b_gz) + "," +
                              String(b_mx) + "," + String(b_my) + "," + String(b_mz) + ",";

      syncMsg += String(a1.acceleration.x, 2) + "," + String(a1.acceleration.y, 2) + "," + String(a1.acceleration.z, 2) + "," + String(g1.gyro.x, 2) + "," + String(g1.gyro.y, 2) + "," + String(g1.gyro.z, 2) + ",";
      syncMsg += String(a2.acceleration.x, 2) + "," + String(a2.acceleration.y, 2) + "," + String(a2.acceleration.z, 2) + "," + String(g2.gyro.x, 2) + "," + String(g2.gyro.y, 2) + "," + String(g2.gyro.z, 2) + ",";
      syncMsg += String(a3.acceleration.x, 2) + "," + String(a3.acceleration.y, 2) + "," + String(a3.acceleration.z, 2) + "," + String(g3.gyro.x, 2) + "," + String(g3.gyro.y, 2) + "," + String(g3.gyro.z, 2) + ",";
      syncMsg += String(a4.acceleration.x, 2) + "," + String(a4.acceleration.y, 2) + "," + String(a4.acceleration.z, 2) + "," + String(g4.gyro.x, 2) + "," + String(g4.gyro.y, 2) + "," + String(g4.gyro.z, 2) + ",";
      syncMsg += String(a5.acceleration.x, 2) + "," + String(a5.acceleration.y, 2) + "," + String(a5.acceleration.z, 2) + "," + String(g5.gyro.x, 2) + "," + String(g5.gyro.y, 2) + "," + String(g5.gyro.z, 2);

      // Queue it up safely
      mutex_enter_blocking(&queueMutex);
      if (dataQueue.size() < MAX_QUEUE_SIZE) {
        dataQueue.push(syncMsg);
      }
      mutex_exit(&queueMutex);
    }
  }
}