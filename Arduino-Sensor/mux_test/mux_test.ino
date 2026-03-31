#include <WiFi.h>
#include <WebSocketsServer.h>
#include <Arduino.h>
#include "pico/mutex.h"
#include <queue>

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
BNO08x bno1, bno2;

#define TCAADDR     0x70
#define BNO08X_ADDR 0x4B            // ADR high -> 0x4B
#define BNO08X_INT  -1

// If your BNO08x modules have a RST pin, connect both to a GPIO (e.g., 6)
// If not, leave BNO_RST_PIN undefined – the code will fall back to software retries
#define BNO_RST_PIN 6               // Connect both BNO RST pins to this GPIO

// BNO data variables
float b1_x, b1_y, b1_z, b1_gx, b1_gy, b1_gz, b1_mx, b1_my, b1_mz;
float b2_x, b2_y, b2_z, b2_gx, b2_gy, b2_gz, b2_mx, b2_my, b2_mz;

unsigned long lastQueueTime = 0;
unsigned long queueInterval = 40;   // 25 Hz default
unsigned long lastBNOAcquisition = 0;

// ==========================================
// HELPER FUNCTIONS
// ==========================================
void tcaselect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
  delayMicroseconds(500);
}

void tcaDisable() {
  Wire.beginTransmission(TCAADDR);
  Wire.write(0x00);
  Wire.endTransmission();
}

void scanI2CBus() {
  Serial.println("\n=== I2C Bus Scan ===");
  for (uint8_t ch = 0; ch < 8; ch++) {
    tcaselect(ch);
    delay(10);
    bool found = false;
    for (uint8_t addr = 0x08; addr < 0x78; addr++) {
      Wire.beginTransmission(addr);
      if (Wire.endTransmission() == 0) {
        Serial.printf("  Channel %d: device at 0x%02X\n", ch, addr);
        found = true;
      }
    }
    if (!found) Serial.printf("  Channel %d: nothing found\n", ch);
  }
  tcaDisable();
  Serial.println("=== Scan Complete ===\n");
}

#ifdef BNO_RST_PIN
void resetBNO() {
  pinMode(BNO_RST_PIN, OUTPUT);
  digitalWrite(BNO_RST_PIN, LOW);
  delay(10);
  digitalWrite(BNO_RST_PIN, HIGH);
  delay(100); // give sensor time to boot
}
#endif

void setReportsFor(BNO08x &bno) {
  bno.enableAccelerometer(20);
  bno.enableGyro(20);
  bno.enableMagnetometer(20);
}

// ==========================================
// CORE 1: NETWORKING
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
      if (activeClients > 0) activeClients--;
      break;
    case WStype_CONNECTED:
      webSocket.sendTXT(clientNum, "IMU Server Connected");
      activeClients++;
      break;
    case WStype_TEXT:
      webSocket.broadcastTXT(payload, length);
      break;
  }
}

// Drains stuck SHTP packets so the sensor can accept new commands
void flushBNO(uint8_t addr) {
  Wire.beginTransmission(addr);
  Wire.write(0x00); // Dummy write
  Wire.endTransmission();
  delay(10);
  
  // Clock out 4 bytes to clear any pending SHTP header
  Wire.requestFrom((uint8_t)addr, (size_t)4);
  while (Wire.available()) {
    Wire.read();
  }
  delay(50);
}

void setup1() {
  while (!systemReady) delay(10);
  setup_ap();
  webSocket.begin();
  webSocket.onEvent(onWebSocketEvent);
  Serial.println("Core 1: WiFi & WebSockets Ready");
}

void loop1() {
  webSocket.loop();
  if (activeClients > 0) {
    String msg = "";
    bool hasData = false;
    mutex_enter_blocking(&queueMutex);
    if (!dataQueue.empty()) {
      msg = dataQueue.front();
      dataQueue.pop();
      hasData = true;
    }
    mutex_exit(&queueMutex);
    if (hasData) webSocket.broadcastTXT(msg);
  } else {
    mutex_enter_blocking(&queueMutex);
    while (!dataQueue.empty()) dataQueue.pop();
    mutex_exit(&queueMutex);
  }
}

// ==========================================
// CORE 0: SENSORS & DATA PRODUCER
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(5000);
  mutex_init(&queueMutex);

  Wire.setSDA(4);
  Wire.setSCL(5);
  Wire.setClock(100000);
  Wire.begin();
  Serial.println("I2C initialized at 100kHz for setup.");
  delay(100);

  scanI2CBus();

  // ---- 1. PERFORM ONE GLOBAL HARDWARE RESET ----
#ifdef BNO_RST_PIN
  Serial.println("Performing one-time global hardware reset...");
  pinMode(BNO_RST_PIN, OUTPUT);
  digitalWrite(BNO_RST_PIN, LOW);
  delay(10);
  digitalWrite(BNO_RST_PIN, HIGH);
  delay(200); // Give both sensors generous time to boot
#endif

  // ---- 2. INITIALIZE BNO1 ON CHANNEL 0 ----
  tcaselect(0);
  delay(50);
  
  flushBNO(BNO08X_ADDR); // Un-jam BNO1 just in case
  if (!bno1.begin(BNO08X_ADDR, Wire, BNO08X_INT, -1)) {
    Serial.println("FATAL: BNO08x #1 not detected on channel 0");
    while (1) delay(10);
  }
  setReportsFor(bno1); 
  Serial.println("BNO1 OK & Configured");

  tcaDisable();
  delay(10);

  // ---- 3. INITIALIZE BNO2 ON CHANNEL 1 ----
  tcaselect(1);
  delay(50);
  
  bool bno2_ok = false;
  for (int attempt = 0; attempt < 5; attempt++) {
    // CRITICAL: Un-jam BNO2's stuck boot packet before sending the soft reset!
    flushBNO(BNO08X_ADDR); 
    
    if (bno2.begin(BNO08X_ADDR, Wire, BNO08X_INT, -1)) {
      bno2_ok = true;
      break;
    }
    Serial.printf("BNO2 begin attempt %d failed, retrying...\n", attempt + 1);
    delay(500);
  }

  if (!bno2_ok) {
    Serial.println("FATAL: BNO08x #2 initialization failed after all attempts.");
    while (1) delay(10);
  }
  setReportsFor(bno2);
  Serial.println("BNO2 OK & Configured");

  tcaDisable();

  Wire.setClock(400000);
  Serial.println("I2C bumped to 400kHz for runtime.");
  Serial.println("\nAll sensors initialized successfully!");

  systemReady = true;
}

void pollBNO(BNO08x &bno, float &ax, float &ay, float &az,
                           float &gx, float &gy, float &gz,
                           float &mx, float &my, float &mz) {
  // If the sensor resets, re-apply reports. 
  // It is safe to call setReportsFor here because pollBNO is wrapped in a tcaselect() in loop()
  if (bno.wasReset()) {
    setReportsFor(bno);
  }
  
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

  if (Serial.available() > 0) {
    long hz = Serial.parseInt();
    while (Serial.available() > 0) Serial.read();
    if (hz > 0) {
      queueInterval = 1000 / hz;
      Serial.printf("\n[UPDATED] Output Frequency: %ld Hz\n", hz);
    }
  }

  if (now - lastBNOAcquisition >= 15) {
    lastBNOAcquisition = now;
    tcaselect(0);
    pollBNO(bno1, b1_x, b1_y, b1_z, b1_gx, b1_gy, b1_gz, b1_mx, b1_my, b1_mz);
    tcaselect(1);
    pollBNO(bno2, b2_x, b2_y, b2_z, b2_gx, b2_gy, b2_gz, b2_mx, b2_my, b2_mz);
  }
  tcaDisable();

  if (now - lastQueueTime >= queueInterval) {
    lastQueueTime = now;
    if (activeClients > 0) {
      String msg = String(b1_x) + "," + String(b1_y) + "," + String(b1_z) + "," +
                   String(b1_gx) + "," + String(b1_gy) + "," + String(b1_gz) + "," +
                   String(b1_mx) + "," + String(b1_my) + "," + String(b1_mz) + "," +
                   String(b2_x) + "," + String(b2_y) + "," + String(b2_z) + "," +
                   String(b2_gx) + "," + String(b2_gy) + "," + String(b2_gz) + "," +
                   String(b2_mx) + "," + String(b2_my) + "," + String(b2_mz);
      mutex_enter_blocking(&queueMutex);
      if (dataQueue.size() < MAX_QUEUE_SIZE) dataQueue.push(msg);
      mutex_exit(&queueMutex);
    }
  }
}