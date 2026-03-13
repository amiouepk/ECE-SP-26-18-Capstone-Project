#include <WiFi.h>
#include <WebSocketsServer.h>
#include <Arduino.h>

// WiFi AP settings (same as original)
const char *ssid = "Rpi Pico";
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

        // Accelerometer (m/s²) – typical range around -4..+4 for X/Y, Z near 9.8
        float ax = 2.0 * sin(timeCounter * 0.7 + phase);
        float ay = 2.5 * cos(timeCounter * 0.5 + phase);
        float az = 9.8 + 1.2 * sin(timeCounter * 0.3 + phase * 2);

        // Gyroscope (deg/s) – typical range -50..+50
        float gx = 30.0 * sin(timeCounter * 1.2 + phase);
        float gy = 25.0 * cos(timeCounter * 0.9 + phase);
        float gz = 20.0 * sin(timeCounter * 0.8 + phase * 3);

        // Format exactly like original: "|ax/ay/az/gx/gy/gz"
        msg += "|" + String(ax, 2) + "/" + String(ay, 2) + "/" + String(az, 2) + "/" +
                     String(gx, 2) + "/" + String(gy, 2) + "/" + String(gz, 2);
      }
      msg += "|"; // trailing delimiter (optional but matches original style)

      webSocket.sendTXT(connectedClient, msg);
    }
  }
}