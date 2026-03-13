#include <WiFi.h>
#include <Arduino.h>
#include <WebSocketsServer.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// WiFi AP settings
const char *ssid = "Rpi Pico";
const char *password = "password";

// WebSocket
WebSocketsServer webSocket(81);
bool clientConnected = false;
uint8_t connectedClient = 0;

// MPU6050 sensors
Adafruit_MPU6050 mpu1, mpu2, mpu3, mpu4, mpu5;

#define TCAADDR 0x70

void tcaselect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

void configureSensor(Adafruit_MPU6050 &mpu, int sensorNum) {
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);
  Serial.print("Sensor ");
  Serial.print(sensorNum);
  Serial.println(" configured.");
}

void setup_ap() {
  Serial.println("Configuring access point...");
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(myIP);
  Serial.println("Server started");
}

void onWebSocketEvent(uint8_t clientNum, WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[%u] Disconnected\n", clientNum);
      clientConnected = false;
      break;
    case WStype_CONNECTED:
      Serial.printf("[%u] Connected\n", clientNum);
      webSocket.sendTXT(clientNum, "Hello from Pico 2W!");
      clientConnected = true;
      connectedClient = clientNum;
      break;
    case WStype_TEXT:
      Serial.printf("[%u] Received: %s\n", clientNum, payload);
      webSocket.sendTXT(clientNum, payload, length);
      break;
  }
}

void setup_ws() {
  webSocket.begin();
  webSocket.onEvent(onWebSocketEvent);
  Serial.println("WebSocket server started on port 81");
}

void setup() {
  Serial.begin(115200);
  delay(5000);

  setup_ap();
  setup_ws();

  Wire.setSDA(4);
  Wire.setSCL(5);
  Wire.begin();

  tcaselect(0); delay(5);
  if (!mpu1.begin(0x68, &Wire)) { Serial.println("Failed MPU6050 #1"); while (0); }
  configureSensor(mpu1, 1);

  tcaselect(1);
  if (!mpu2.begin(0x68, &Wire)) { Serial.println("Failed MPU6050 #2"); while (0); }
  configureSensor(mpu2, 2);

  tcaselect(2);
  if (!mpu3.begin(0x68, &Wire)) { Serial.println("Failed MPU6050 #3"); while (0); }
  configureSensor(mpu3, 3);

  tcaselect(3);
  if (!mpu4.begin(0x68, &Wire)) { Serial.println("Failed MPU6050 #4"); while (0); }
  configureSensor(mpu4, 4);

  tcaselect(4);
  if (!mpu5.begin(0x68, &Wire)) { Serial.println("Failed MPU6050 #5"); while (0); }
  configureSensor(mpu5, 5);

  Serial.println("All sensors initialized!");
}

void loop() {
  webSocket.loop();

  static unsigned long lastSend = 0;
  if (millis() - lastSend > 500) {
    lastSend = millis();

    if (clientConnected) {
      sensors_event_t a, g, temp;
      String msg = "";

      tcaselect(0);
      mpu1.getEvent(&a, &g, &temp);
      msg += "|" + String(a.acceleration.x) + "/" + String(a.acceleration.y) + "/" + String(a.acceleration.z) + "/" +
             String(g.gyro.x) + "/" + String(g.gyro.y) + "/" + String(g.gyro.z);

      tcaselect(1);
      mpu2.getEvent(&a, &g, &temp);
      msg += "|" + String(a.acceleration.x) + "/" + String(a.acceleration.y) + "/" + String(a.acceleration.z) + "/" +
             String(g.gyro.x) + "/" + String(g.gyro.y) + "/" + String(g.gyro.z);

      tcaselect(2);
      mpu3.getEvent(&a, &g, &temp);
      msg += "|" + String(a.acceleration.x) + "/" + String(a.acceleration.y) + "/" + String(a.acceleration.z) + "/" +
             String(g.gyro.x) + "/" + String(g.gyro.y) + "/" + String(g.gyro.z);

      tcaselect(3);
      mpu4.getEvent(&a, &g, &temp);
      msg += "|S4:" + String(a.acceleration.x) + "/" + String(a.acceleration.y) + "/" + String(a.acceleration.z) + "/" +
             String(g.gyro.x) + "/" + String(g.gyro.y) + "/" + String(g.gyro.z);

      tcaselect(4);
      mpu5.getEvent(&a, &g, &temp);
      msg += "|S5:" + String(a.acceleration.x) + "/" + String(a.acceleration.y) + "/" + String(a.acceleration.z) + "/" +
             String(g.gyro.x) + "/" + String(g.gyro.y) + "/" + String(g.gyro.z);

      msg += "|";
      webSocket.sendTXT(connectedClient, msg);
    }
  }
}