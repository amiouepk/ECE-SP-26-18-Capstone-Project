

// setup for wifi AP
#include <WiFi.h>
#include <NetworkClient.h>
#include <WiFiAP.h>
const char *ssid = "yourAP";
const char *password = "yourPassword";
NetworkServer server(80);

void setup_ap(){
  Serial.println("Configuring access point...");
  if (!WiFi.softAP(ssid, password)) {
    log_e("Soft AP creation failed.");
    while (1);
  }
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(myIP);
  server.begin();

  Serial.println("Server started");
}


void setup() {
  Serial.begin(115200);
  Serial.println();

  setup_ap();

}

void loop() {
  // put your main code here, to run repeatedly:

}
