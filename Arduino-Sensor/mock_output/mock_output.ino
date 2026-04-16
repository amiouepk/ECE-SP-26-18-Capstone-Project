#include <WiFi.h>
#include <WebSocketsServer.h>
#include <Arduino.h>

// WiFi AP settings (same as original)
const char *ssid = "Test Rpi Pico";
const char *password = "password";

// WebSocket server on port 81
WebSocketsServer webSocket(81);
bool clientConnected = false;
uint8_t connectedClient = 0;

// Timing
unsigned long lastSend = 0;
const unsigned long sendInterval = 500; // ms

// Mock data generation
float timeCounter = 0.0;          // increments each send

void setup_ap() {
  Serial.println("Configuring access point...");
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(myIP);
  Serial.println("Mock server started");
}

void onWebSocketEvent(uint8_t clientNum, WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[%u] Disconnected\n", clientNum);
      clientConnected = false;
      break;
    case WStype_CONNECTED:
      Serial.printf("[%u] Connected\n", clientNum);
      webSocket.sendTXT(clientNum, "Mock sensor server connected");
      clientConnected = true;
      connectedClient = clientNum;
      break;
    case WStype_TEXT:
      Serial.printf("[%u] Received: %s\n", clientNum, payload);
      // Echo back for testing
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
  delay(1000);

  setup_ap();
  setup_ws();

  Serial.println("Mock sensor data generator ready");
}

void loop() {
  webSocket.loop();

  if (millis() - lastSend > sendInterval) {
    lastSend = millis();
    timeCounter += 0.1; // advance simulation time

    if (clientConnected) {
      String msg = "";

      // Simulate 3 sensors (same order as original: mpu1, mpu2, mpu3)
      for (int sensor = 0; sensor < 5; sensor++) {
        // Use different frequencies and phases for each sensor to make data look independent
        float phase = sensor * 1.5; // offset per sensor

        float BNO1_ax = 2.0 * sin(timeCounter * 0.7 + phase);
        float BNO1_ay = 2.5 * cos(timeCounter * 0.5 + phase);
        float BNO1_az = 9.8 + 1.2 * sin(timeCounter * 0.3 + phase * 2);

        float BNO1_gx = 30.0 * sin(timeCounter * 1.2 + phase);
        float BNO1_gy = 25.0 * cos(timeCounter * 0.9 + phase);
        float BNO1_gz = 20.0 * sin(timeCounter * 0.8 + phase * 3);

        float BNO1_mx = 50.0 * sin(timeCounter * 1.2 + phase);
        float BNO1_my = 55.0 * cos(timeCounter * 0.9 + phase);
        float BNO1_mz = 60.0 * sin(timeCounter * 0.8 + phase * 3);

        float BNO2_ax = 2.0 * sin(timeCounter * 0.7 + phase);
        float BNO2_ay = 2.5 * cos(timeCounter * 0.5 + phase);
        float BNO2_az = 9.8 + 1.2 * sin(timeCounter * 0.3 + phase * 2);

        float BNO2_gx = 30.0 * sin(timeCounter * 1.2 + phase);
        float BNO2_gy = 25.0 * cos(timeCounter * 0.9 + phase);
        float BNO2_gz = 20.0 * sin(timeCounter * 0.8 + phase * 3);

        float BNO2_mx = 50.0 * sin(timeCounter * 1.2 + phase);
        float BNO2_my = 55.0 * cos(timeCounter * 0.9 + phase);
        float BNO2_mz = 60.0 * sin(timeCounter * 0.8 + phase * 3);

        float BNO3_ax = 2.0 * sin(timeCounter * 0.7 + phase);
        float BNO3_ay = 2.5 * cos(timeCounter * 0.5 + phase);
        float BNO3_az = 9.8 + 1.2 * sin(timeCounter * 0.3 + phase * 2);

        float BNO3_gx = 30.0 * sin(timeCounter * 1.2 + phase);
        float BNO3_gy = 25.0 * cos(timeCounter * 0.9 + phase);
        float BNO3_gz = 20.0 * sin(timeCounter * 0.8 + phase * 3);

        float BNO3_mx = 50.0 * sin(timeCounter * 1.2 + phase);
        float BNO3_my = 55.0 * cos(timeCounter * 0.9 + phase);
        float BNO3_mz = 60.0 * sin(timeCounter * 0.8 + phase * 3);

        float BNO4_ax = 2.0 * sin(timeCounter * 0.7 + phase);
        float BNO4_ay = 2.5 * cos(timeCounter * 0.5 + phase);
        float BNO4_az = 9.8 + 1.2 * sin(timeCounter * 0.3 + phase * 2);

        float BNO4_gx = 30.0 * sin(timeCounter * 1.2 + phase);
        float BNO4_gy = 25.0 * cos(timeCounter * 0.9 + phase);
        float BNO4_gz = 20.0 * sin(timeCounter * 0.8 + phase * 3);

        float BNO4_mx = 50.0 * sin(timeCounter * 1.2 + phase);
        float BNO4_my = 55.0 * cos(timeCounter * 0.9 + phase);
        float BNO4_mz = 60.0 * sin(timeCounter * 0.8 + phase * 3);

        // Accelerometer (m/s²) – typical range around -4..+4 for X/Y, Z near 9.8
        float MPU1_ax = 2.0 * sin(timeCounter * 0.7 + phase);
        float MPU1_ay = 2.5 * cos(timeCounter * 0.5 + phase);
        float MPU1_az = 9.8 + 1.2 * sin(timeCounter * 0.3 + phase * 2);

        // Gyroscope (deg/s) – typical range -50..+50
        float MPU1_gx = 30.0 * sin(timeCounter * 1.2 + phase);
        float MPU1_gy = 25.0 * cos(timeCounter * 0.9 + phase);
        float MPU1_gz = 20.0 * sin(timeCounter * 0.8 + phase * 3);

        float MPU2_ax = 2.0 * sin(timeCounter * 0.7 + phase);
        float MPU2_ay = 2.5 * cos(timeCounter * 0.5 + phase);
        float MPU2_az = 9.8 + 1.2 * sin(timeCounter * 0.3 + phase * 2);

        // Gyroscope (deg/s) – typical range -50..+50
        float MPU2_gx = 30.0 * sin(timeCounter * 1.2 + phase);
        float MPU2_gy = 25.0 * cos(timeCounter * 0.9 + phase);
        float MPU2_gz = 20.0 * sin(timeCounter * 0.8 + phase * 3);
      

        msg += String(BNO1_ax) + "," + String(BNO1_ay) + "," + String(BNO1_az) + "," +
               String(BNO1_gx) + "," + String(BNO1_gy) + "," + String(BNO1_gz) + "," +
               String(BNO1_mx) + "," + String(BNO1_my) + "," + String(BNO1_mz) + "," +
               String(BNO2_ax) + "," + String(BNO2_ay) + "," + String(BNO2_az) + "," +
               String(BNO2_gx) + "," + String(BNO2_gy) + "," + String(BNO2_gz) + "," +
               String(BNO2_mx) + "," + String(BNO2_my) + "," + String(BNO2_mz) + "," +
               String(BNO3_ax) + "," + String(BNO3_ay) + "," + String(BNO3_az) + "," +
               String(BNO3_gx) + "," + String(BNO3_gy) + "," + String(BNO3_gz) + "," +
               String(BNO3_mx) + "," + String(BNO3_my) + "," + String(BNO3_mz) + "," +
               String(BNO4_ax) + "," + String(BNO4_ay) + "," + String(BNO4_az) + "," +
               String(BNO4_gx) + "," + String(BNO4_gy) + "," + String(BNO4_gz) + "," +
               String(BNO4_mx) + "," + String(BNO4_my) + "," + String(BNO4_mz) + "," +
               String(MPU1_ax) + "," + String(MPU1_ay) + "," + String(MPU1_az) + "," +
               String(MPU1_gx) + "," + String(MPU1_gy) + "," + String(MPU1_gz) + "," +
               String(MPU2_ax) + "," + String(MPU2_ay) + "," + String(MPU2_az) + "," +
               String(MPU2_gx) + "," + String(MPU2_gy) + "," + String(MPU2_gz);
               
      }
      //msg += "|"; // trailing delimiter (optional but matches original style)

      webSocket.sendTXT(connectedClient, msg);
    }
  }
}