/*
	finish_line.ino

	The finish line is responsible for monitoring for cars passing over each lane
  and reporting back to the Starting Gate via Bluetooth.

  TODO(tq): Finish write-up including commands accepted over BlueTooth and OTA
            updates

Author: Tom Quiggle
tquiggle@gmail.com

https://github.com/tquiggle/Diecast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for 
full license information.


*/

#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

#include <string>
#include <map>

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <WiFiClient.h>
#include <WiFi.h>
#include <FS.h>
#include <SPIFFS.h>

// Hard coded config
const char* FW_VERSION = "20120501";
                       // YYMMDDVV Last two digits of Year, Month, Day, Version
const char* fwVersionURLtemplate = "http://%s:%d/DRR/FL/version.txt";
const char* fwURLtemplate = "http://%s:%d/DRR/FL/finish-line-%0d.bin";
const char* configFilename = "/config.json";

// Adjust defaults as you see fit
#define URLLEN 80
#define DEFAULT_WIFI_SSID "<SSID>"
#define DEFAULT_WIFI_PASSWORD "<PASSWORD>"
#define DEFAULT_BT_ADVERTISEMENT "FinishLine"
#define DEFAULT_CONTROLLER_HOSTNAME "<CONTROLLER_HOST>"
#define DEFAULT_CONTROLLER_PORT 1968
#define MAX_CONFIG_SIZE 256

// Configuration stored in config.json
String wifiSSID(DEFAULT_WIFI_SSID);
String wifiPassword(DEFAULT_WIFI_PASSWORD);
String bluetoothAdvertisement(DEFAULT_BT_ADVERTISEMENT);
String controllerHostname(DEFAULT_CONTROLLER_HOSTNAME);
int    controllerPort = DEFAULT_CONTROLLER_PORT;

// Pin Assignments
const int LANE1_PIN = 16;
const int LANE2_PIN = 17;
const int LANE3_PIN = 18;
const int LANE4_PIN = 19;

const int numLanes = 4;
enum Lanes {
  LANE1 = 0,  // Lanes is used as an array index
  LANE2,
  LANE3,
  LANE4
};

enum Commands {
  HELLO,
  RESTART,
  UPDATE_FW,
  BEGIN_RACE,
  END_RACE,
  VERSION,
  GET_CONFIG,
  SET_CONFIG,
  DELETE_CONFIG,
  UNKNOWN
};

#define DEBOUNCE_MILLIS 100
unsigned long lastFinish[numLanes] = {0, 0, 0, 0};
const int finishMessageLength = 4;
const uint8_t* finishMessages[numLanes] = {
  (uint8_t*)"FIN1",
  (uint8_t*)"FIN2",
  (uint8_t*)"FIN3",
  (uint8_t*)"FIN4"
};

/* Mapping for command string received over Bluetooth to enum */
static const std::map<String, Commands> commandTable = {
  {"HELO", Commands::HELLO},
  {"RSRT", Commands::RESTART},
  {"UPFW", Commands::UPDATE_FW},
  {"BGIN", Commands::BEGIN_RACE},
  {"ENDR", Commands::END_RACE},
  {"FWVS", Commands::VERSION},
  {"GETC", Commands::GET_CONFIG},
  {"SETC", Commands::SET_CONFIG},
  {"DELC", Commands::DELETE_CONFIG}
};

Commands toCommand(String str) {
  std::map <String, Commands>::const_iterator iValue = commandTable.find(str);
  if (iValue  == commandTable.end())
    return Commands::UNKNOWN;
  return iValue->second;
}

BluetoothSerial SerialBT;
bool raceRunning = false;

bool saveConfig(const char* filename) {
  if (!SPIFFS.begin(true)) {
    Serial.println("saveConfig(): SPIFFS.begin() failed.");
    return false;
  }

  if (SPIFFS.exists(filename)) {
    Serial.printf("saveConfig(): %s exists, removing.\n", filename);
    SPIFFS.remove(filename);
  }

  File config = SPIFFS.open(filename, FILE_WRITE);
  if (!config) {
    Serial.printf("saveConfig(): Failed to create config file %s\n", filename);
    return false;
  }
  StaticJsonDocument<MAX_CONFIG_SIZE> doc;

  doc["wifiSSID"] = wifiSSID;
  doc["wifiPassword"] = wifiPassword;
  doc["bluetoothAdvertisement"] = bluetoothAdvertisement;
  doc["controllerHostname"] = controllerHostname;
  doc["controllerPort"] = controllerPort;

  String configJson;
  if (serializeJsonPretty(doc, configJson)) {
    Serial.printf("config = %s\n", configJson.c_str());
  }

  int bytesWritten = serializeJson(doc, config);
  Serial.printf("bytesWritten = %d\n", bytesWritten);

  if (bytesWritten <= 0)
    return false;

  config.close();
  SPIFFS.end();
  return true;
}

// Reads in the saved configuration from the SPIFFS file system on flash.
bool readConfig(const char* filename) {
  Serial.println("readConfig(): Compiled Defaults:");

  Serial.printf("  wifiSSID = %s\n", wifiSSID.c_str());
  Serial.printf("  wifiPassword = %s\n", wifiPassword.c_str());
  Serial.printf("  bluetoothAdvertisement = %s\n",
                bluetoothAdvertisement.c_str());
  Serial.printf("  controllerHostname = %s\n", controllerHostname.c_str());
  Serial.printf("  controllerPort = %d\n", controllerPort);

  if (!SPIFFS.begin(true)) {
    Serial.println("readConfig(): SPIFFS.begin() failed.");
    return false;
  }

  if (!SPIFFS.exists(filename)) {
    // Create config file with defaults
    Serial.printf("readConfig(): %s does not exist. Creating.\n", filename);
    saveConfig(filename);
    return true;
  }

  File config = SPIFFS.open(filename, FILE_READ);
  if (!config) {
    Serial.printf("readConfig(): unable to open %s\n", filename);
    return false;
  }

  StaticJsonDocument<MAX_CONFIG_SIZE> doc;
  DeserializationError error = deserializeJson(doc, config);
  if (error) {
    Serial.printf("  unable to deserialize %s. Deleting.\n", filename);
    SPIFFS.remove(filename);
    return false;
  }
  
  Serial.printf("readConfig(): Configuration read from %s:\n", filename);

  if (doc.containsKey("wifiSSID")) {
    wifiSSID = doc["wifiSSID"].as<String>();
    Serial.print("  wifiSSID = ");
    Serial.println(wifiSSID);
  }
  if (doc.containsKey("wifiPassword")) {
    wifiPassword = doc["wifiPassword"].as<String>();
    Serial.print("  wifiPassword = ");
    Serial.println(wifiPassword);
  }
  if (doc.containsKey("bluetoothAdvertisement")) {
    bluetoothAdvertisement = doc["bluetoothAdvertisement"].as<String>();
    Serial.print("  bluetoothAdvertisement = ");
    Serial.println(bluetoothAdvertisement);
  }
  if (doc.containsKey("controllerHostname")) {
    controllerHostname = doc["controllerHostname"].as<String>();
    Serial.print("  controllerHostname = ");
    Serial.println(controllerHostname);
  }
  if (doc.containsKey("controllerPort")) {
    controllerPort = doc["controllerPort"];
    Serial.print("  controllerPort = ");
    Serial.println(controllerPort);
  }
  config.close();
  SPIFFS.end();
}

// Process a GETC command received via Bluetooth to update
bool getConfig(String configStr) {
  Serial.printf("getConfig(): configStr=%s\n", configStr);
  StaticJsonDocument<MAX_CONFIG_SIZE> doc;

  if (configStr.length() > 5) {
    String config = configStr.substring(5);
    Serial.printf("getConfig(): getting %s\n", config);
    if (configStr == "wifiSSID") {
      doc["wifiSSID"] = wifiSSID;
    } else if (configStr == "wifiPassword") {
      doc["wifiPassword"] = wifiPassword;
    } else if (configStr == "bluetoothAdvertisement") {
      doc["bluetoothAdvertisement"] = bluetoothAdvertisement;
    } else if (configStr == "controllerHostname") {
      doc["controllerHostname"] = controllerHostname;
    } else if (configStr == "controllerPort") {
      doc["controllerPort"] = controllerPort;
    }
  } else {
    doc["wifiSSID"] = wifiSSID;
    doc["wifiPassword"] = wifiPassword;
    doc["bluetoothAdvertisement"] = bluetoothAdvertisement;
    doc["controllerHostname"] = controllerHostname;
    doc["controllerPort"] = controllerPort;
  }

  String configJson;
  if (serializeJsonPretty(doc, configJson)) {
    Serial.printf("config = %s\n", configJson.c_str());
  }
  SerialBT.write((const uint8_t*)configJson.c_str(), configJson.length());

}

// Process a SETC command received via Bluetooth to update
bool setConfig(String configStr) {
  Serial.printf("setConfig(): configStr=%s\n", configStr.c_str());
  String key;
  String value;

  size_t pos = configStr.indexOf('=');
  if (pos > 0) {
    key = configStr.substring(0, pos);
    value = configStr.substring(pos+1);
  } else {
    Serial.println("Invalid config string");
    return false;
  }

  Serial.printf("setConfig(): key=%s, value=%s\n", key.c_str(), value.c_str());
  if (key == "wifiSSID") {
    wifiSSID = value;
  } else if  (key == "wifiPassword") {
    wifiPassword = value;
  } else if  (key == "bluetoothAdvertisement") {
    bluetoothAdvertisement = value;
  } else if (key == "controllerHostname") {
    controllerHostname = value;
  } else if (key == "controllerPort") {
    controllerPort = value.toInt();
  } else {
    Serial.println("setConfig(): Invalud config name. Ignoring.");
    return false;
  }
  return saveConfig(configFilename);
}

void deleteConfig() {
  Serial.println("deleteConfig():");

  if (!SPIFFS.begin(true)) {
    Serial.println("deleteConfig(): SPIFFS.begin() failed.");
    return;
  }
  SPIFFS.remove(configFilename);
  SPIFFS.end();
}

void checkForUpdates() {
  Serial.printf("Running Finish Line version %s\n", FW_VERSION);
  Serial.println("Configuring WiFi");
  WiFi.mode(WIFI_STA);

// Connect to the network
  WiFi.begin(wifiSSID.c_str(), wifiPassword.c_str());

  int i = 0;
  while (WiFi.status() != WL_CONNECTED) {  // Wait for the Wi-Fi to connect
    delay(1000);
    Serial.printf("Waiting for wifi %d\n", i++);
  }

  // expand template for URL of current firmware version
  char fwVersionURL[URLLEN];
  snprintf(fwVersionURL, URLLEN, fwVersionURLtemplate,
           controllerHostname.c_str(), controllerPort);

  Serial.println("Connection established!");
  Serial.print("IP address:\t");
  Serial.println(WiFi.localIP());

  Serial.println("Checking for firmware updates.");
  Serial.printf("Firmware version URL: %s\n", fwVersionURL);

  WiFiClient client;
  HTTPClient httpClient;
  bool result = httpClient.begin(client, fwVersionURL);
  Serial.printf("httpClient.begin(client, %s) returned %d\n",
                fwVersionURL, result);

  int httpCode = httpClient.GET();
  Serial.printf("http.GET() returned %d\n", httpCode);

  if ( httpCode == 200 ) {
    String newFWVersion = httpClient.getString();
    int newVersion = newFWVersion.toInt();
    int curVersion = atoi(FW_VERSION);

    Serial.printf("Current firmware version: %d\n", curVersion);
    Serial.printf("Available firmware version: %d\n", newVersion);

    if ( newVersion <= curVersion ) {
      Serial.println("Firmware is up to date");
    } else {
      char fwImageURL[URLLEN];
      t_httpUpdate_return ret;
      
      snprintf(fwImageURL, URLLEN, fwURLtemplate, controllerHostname.c_str(),
               controllerPort, newVersion);
      Serial.printf("Preparing to update to %s\n", fwImageURL);

      ret = httpUpdate.update(client, fwImageURL, FW_VERSION);

      switch (ret) {
        case HTTP_UPDATE_OK:
          Serial.printf("HTTP_UPDATE_OK Rebooting to new image.");
          delay(1000);
          ESP.restart();
          break;  // Just because it's good form!

        case HTTP_UPDATE_FAILED:
          Serial.printf("HTTP_UPDATE_FAILD Error (%d): %s\n",
                        httpUpdate.getLastError(),
                        httpUpdate.getLastErrorString().c_str());
          break;

        case HTTP_UPDATE_NO_UPDATES:
          Serial.println("HTTP_UPDATE_NO_UPDATES");
          break;
      }
    }
  } else {
    Serial.print("Firmware version check failed, got HTTP response code ");
    Serial.println(httpCode);
  }
  httpClient.end();
}


void processMessage() {
  String data = SerialBT.readString();
  Serial.println("Received '" + data + "' from Starting Line");
  if (data.length() < 3) {
    Serial.println("Command too short");
    return;
  }
  
  String command = data.substring(0,4);
  Serial.println("command = '" + command + "'");

  String argument = data.substring(5);
  Serial.println("argument = '" + argument + "'");

  switch (toCommand(command)) {
    case HELLO:
      SerialBT.write((const uint8_t*)"HELLO", 5);
      break;
    case RESTART:
      ESP.restart();
      break;
    case UPDATE_FW:
      checkForUpdates();
      break;
    case VERSION:
      SerialBT.write((const uint8_t*)FW_VERSION, strlen(FW_VERSION));
      break;
    case BEGIN_RACE:
      raceRunning = true;
      break;
    case END_RACE:
      raceRunning = false;
      break;
    case GET_CONFIG:
      getConfig(argument);
      break;
    case SET_CONFIG:
      setConfig(argument);
      break;
    case DELETE_CONFIG:
      deleteConfig();
      break;
    case UNKNOWN:
      Serial.println("Received unknown command.");
      break;
  }
}

void sendResult(Lanes lane) {
  Serial.printf("LANE%0d finished.\n", lane + 1);
  SerialBT.write(finishMessages[lane], finishMessageLength);
  lastFinish[lane] = millis();
}

bool debounce(Lanes lane) {
  unsigned long now = millis();
  return (now - lastFinish[lane]) > DEBOUNCE_MILLIS;
}

void setup() {
  Serial.begin(115200);
  readConfig(configFilename);
  checkForUpdates();
  pinMode(LANE1_PIN, INPUT_PULLUP);
  pinMode(LANE2_PIN, INPUT_PULLUP);
  pinMode(LANE3_PIN, INPUT_PULLUP);
  pinMode(LANE4_PIN, INPUT_PULLUP);

  Serial.printf("setup(): Initializing SerialBT with advertisement '%s'\n",
                bluetoothAdvertisement.c_str());
  SerialBT.begin(bluetoothAdvertisement, false);
}

void loop() {
  if (SerialBT.available()) {
    processMessage();
  }
  if (raceRunning) {
    if ((digitalRead(LANE1_PIN) == 0) && debounce(LANE1)) {
      sendResult(LANE1);
    }
    if ((digitalRead(LANE2_PIN) == 0) && debounce(LANE2)) {
      sendResult(LANE2);
    }
    if ((digitalRead(LANE3_PIN) == 0) && debounce(LANE3)) {
      sendResult(LANE3);
    }
    if ((digitalRead(LANE4_PIN) == 0) && debounce(LANE4)) {
      sendResult(LANE4);
    }
  }
}

// vim: set expandtab ts=2
