/*
  finish_line.ino

  The finish line is responsible for monitoring for cars passing over each lane
  and reporting back to the Starting Gate via Bluetooth.

  TODO(tq): Finish write-up including commands accepted over BlueTooth and OTA updates

Author: Tom Quiggle
tquiggle@gmail.com

https://github.com/tquiggle/Diecast-Remote-Raceway

Copyright (c) Thomas Quiggle. All rights reserved.

Licensed under the MIT license. See LICENSE file in the project root for 
full license information.


*/

#include <stddef.h>
#include <string>
#include <map>
#include <Base64.h>

#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <WiFiClient.h>
#include <WiFi.h>
#include <FS.h>
#include <SPIFFS.h>

#include "rsa_routines.h"


// Hard coded config
const char* FW_VERSION = "26081900";
// YYMMDDVV Last two digits of Year, Month, Day, Version
const char* configFilename = "/config.json";

// Adjust defaults as you see fit
#define URLLEN 100
#define DEFAULT_BT_ADVERTISEMENT "FinishLine"
#define MAX_CONFIG_SIZE 512
#define MAX_LANES 4
#define WIFI_CONNECT_MAX_TRYS 10

bool rsaInitialized = false;

// Configuration stored in config.json
String bluetoothAdvertisement(DEFAULT_BT_ADVERTISEMENT);

// Pin Assignments
const int LANE1_PIN = 16;
const int LANE2_PIN = 17;
const int LANE3_PIN = 18;
const int LANE4_PIN = 19;

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
  GET_PUBLIC_KEY,
  GET_CONFIG,
  SET_CONFIG,
  DELETE_CONFIG,
  UNKNOWN
};

#define DEBOUNCE_MILLIS 100
unsigned long lastFinish[MAX_LANES] = { 0, 0, 0, 0 };
const int finishMessageLength = 4;
const uint8_t* finishMessages[MAX_LANES] = {
  (uint8_t*)"FIN1",
  (uint8_t*)"FIN2",
  (uint8_t*)"FIN3",
  (uint8_t*)"FIN4"
};

/* Mapping for command string received over Bluetooth to enum */
static const std::map<String, Commands> commandTable = {
  { "HELO", Commands::HELLO },
  { "RSRT", Commands::RESTART },
  { "UPFW", Commands::UPDATE_FW },
  { "BGIN", Commands::BEGIN_RACE },
  { "ENDR", Commands::END_RACE },
  { "FLVS", Commands::VERSION },
  { "GKEY", Commands::GET_PUBLIC_KEY },
  { "GETC", Commands::GET_CONFIG },
  { "SETC", Commands::SET_CONFIG },
  { "DELC", Commands::DELETE_CONFIG }
};

Commands toCommand(String str) {
  std::map<String, Commands>::const_iterator iValue = commandTable.find(str);
  if (iValue == commandTable.end())
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

  JsonDocument doc;

  doc["bluetoothAdvertisement"] = bluetoothAdvertisement;

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

  Serial.printf("  bluetoothAdvertisement = %s\n",
                bluetoothAdvertisement.c_str());

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

  JsonDocument doc;

  Serial.printf("readConfig(): calling deserializeJson\n");
  DeserializationError error = deserializeJson(doc, config);

  if (error) {
    Serial.printf("deserializeJson failed with code");
    Serial.println(error.f_str());
    Serial.printf("  unable to deserialize %s. Deleting.\n", filename);
    SPIFFS.remove(filename);
    return false;
  }

  Serial.printf("readConfig(): Configuration read from %s:\n", filename);
  serializeJson(doc, Serial);
  Serial.println("");

  if (doc["bluetoothAdvertisement"].is<String>()) {
    bluetoothAdvertisement = doc["bluetoothAdvertisement"].as<String>();
    Serial.print("  bluetoothAdvertisement = ");
    Serial.println(bluetoothAdvertisement);
  }

  Serial.printf("readConfig(): returning\n");
  config.close();
  SPIFFS.end();
  return true;
}

void deleteConfig(const char* filename) {
  Serial.println("deleteConfig():");

  if (!SPIFFS.begin(true)) {
    Serial.println("deleteConfig(): SPIFFS.begin() failed.");
    return;
  }
  SPIFFS.remove(filename);
  SPIFFS.end();
}

// Process a GETC command received via Bluetooth to update
bool getConfig(String configStr) {
  Serial.printf("getConfig(): configStr=%s\n", configStr);
  //StaticJsonDocument<MAX_CONFIG_SIZE> doc;
  JsonDocument doc;

  if (configStr.length() > 5) {
    String config = configStr.substring(5);
    Serial.printf("getConfig(): getting %s\n", config);
    if (configStr == "bluetoothAdvertisement") {
      doc["bluetoothAdvertisement"] = bluetoothAdvertisement;
    }
  } else {
    doc["bluetoothAdvertisement"] = bluetoothAdvertisement;
  }

  String configJson;
  if (serializeJsonPretty(doc, configJson)) {
    Serial.printf("config = %s\n", configJson.c_str());
  }
  SerialBT.write((const uint8_t*)configJson.c_str(), configJson.length());
  return true;
}

// Process a SETC command received via Bluetooth to update
bool setConfig(String configStr) {
  Serial.printf("setConfig(): configStr=%s\n", configStr.c_str());
  String key;
  String value;

  size_t pos = configStr.indexOf('=');
  if (pos > 0) {
    key = configStr.substring(0, pos);
    value = configStr.substring(pos + 1);
  } else {
    Serial.println("Invalid config string");
    return false;
  }

  Serial.printf("setConfig(): key=%s, value=%s\n", key.c_str(), value.c_str());
  if (key == "bluetoothAdvertisement") {
    bluetoothAdvertisement = value;
  } else {
    Serial.println("setConfig(): Invalid config name. Ignoring.");
    return false;
  }
  return saveConfig(configFilename);
}

void printHexArray(byte *buffer, int bufferSize) {
  for (int i = 0; i < bufferSize; i++) {
    if (buffer[i] < 0x10) Serial.print("0");
    Serial.print(buffer[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}

String decrypt_wifi_string(String encrypted_base64) {
  unsigned char encrypted[MBEDTLS_MPI_MAX_SIZE];
  unsigned char decrypted[MBEDTLS_MPI_MAX_SIZE];

  size_t enc_len;  // Size of encrypted string stored in encrypted buffer
  size_t dec_len;  // Size of decrypted string stored in decrypted buffer

  Serial.printf("decrypt_wifi_string(): base64 string is '%s'\n", encrypted_base64.c_str());

  enc_len = Base64.decode((char*)encrypted, (char*)encrypted_base64.c_str(), encrypted_base64.length());

  Serial.printf("decrypt_wifi_string(): base64 decoded: len=%d, encrypted=", enc_len);
  printHexArray((byte*)encrypted, enc_len);

  Serial.printf("Calling rsa_priv_dec\n");
  rsa_priv_dec(encrypted, enc_len, decrypted, sizeof(decrypted), &dec_len);
  decrypted[dec_len] = 0;

  Serial.printf("Decrypted password is '%s'\n", decrypted);
  return String((char*)decrypted);
}

int updateFirmware(String updateParametersJson) {
  /*
   * The updateParamsJson document contains the following:
   *
   * {"SSID":    "<WiFi SSID>",
   *  "encryptedPSK":  "<encrypted WiFi PSK>",
   *  "URL":     "<url of updated firmware"}
   */

  JsonDocument doc;
  String wifiSSID;
  String encryptedPSK;
  String wifiPSK;
  String fwImageURL;

  Serial.printf("updateFirmware(): calling deserializeJson\n");
  DeserializationError error = deserializeJson(doc, updateParametersJson);

  if (error) {
    Serial.printf("  deserializeJson failed with code %s\n", error.f_str());
    return false;
  }

  if (doc["SSID"].is<String>()) {
    wifiSSID = doc["SSID"].as<String>();
    Serial.print("  wifiSSID = ");
    Serial.println(wifiSSID);
  }

  if (doc["encryptedPSK"].is<String>()) {
    encryptedPSK = doc["encryptedPSK"].as<String>();
    Serial.print("  encryptedPSK = ");
    Serial.println(encryptedPSK);
  }

  if (doc["URL"].is<String>()) {
    fwImageURL = doc["URL"].as<String>();
    Serial.print("  fwImageURL = ");
    Serial.println(fwImageURL);
  }

  wifiPSK = decrypt_wifi_string(encryptedPSK);

  // Connect to the network
  WiFi.begin((const char*)wifiSSID.c_str(), (const char*)wifiPSK.c_str());

  int trys = 0;
  while (WiFi.status() != WL_CONNECTED && trys < WIFI_CONNECT_MAX_TRYS) {  // Wait for the Wi-Fi to connect
    delay(1000);
    Serial.printf("Waiting for wifi %d\n", trys++);
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("Unable to connect to wifi in %d trys\n", trys++);
    return false;
  }

  Serial.println("Connection established!");
  Serial.print("IP address:\t");
  Serial.println(WiFi.localIP());

  Serial.printf("Preparing to update to %s\n", fwImageURL.c_str());

  WiFiClient client;
  t_httpUpdate_return ret = httpUpdate.update(client, fwImageURL, FW_VERSION);

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

void get_public_key() {
  const uint8_t* public_key;
  size_t bytes = 0;
  size_t written = 0;

  Serial.println("get_public_key()");
  if (!rsaInitialized) {
    Serial.println("  calling rsa_init");
    rsa_init();
    rsaInitialized = true;
  }

  public_key = public_key_pem();
  size_t len = strlen((const char*)public_key);

  Serial.printf("  public_key=%s\n", (const char*)public_key);
  Serial.printf("  len=%zu\n", len);

  while (written < len) {
    Serial.printf("  Writing to BT %zu bytes (%zu already written)\n", len, written);
    bytes = SerialBT.write(&public_key[written], len - written);
    written += bytes;
    Serial.printf("GET_PUBLIC_KEY wrote %zu bytes of key with size %zu\n", written, len);
    if (bytes == 0)
      break;
  }
}

void processMessage() {
  String data = SerialBT.readString();
  Serial.println("Received '" + data + "' from Starting Line");
  if (data.length() < 3) {
    Serial.println("Command too short");
    return;
  }

  String command = data.substring(0, 4);
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
      updateFirmware(argument);
      break;
    case VERSION:
      SerialBT.write((const uint8_t*)FW_VERSION, strlen(FW_VERSION));
      break;
    case GET_PUBLIC_KEY:
      get_public_key();
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
      deleteConfig(configFilename);
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
  /*
   * Unlike the starting gate, there is no need to configure the number of connected lanes.
   * By pulling up all four of the pins, disconnected lanes will just never report state change.
   */
  Serial.begin(115200);
  readConfig(configFilename);
  Serial.println("setup(): back from readConfig()\n");

  pinMode(LANE1_PIN, INPUT_PULLUP);
  pinMode(LANE2_PIN, INPUT_PULLUP);
  pinMode(LANE3_PIN, INPUT_PULLUP);
  pinMode(LANE4_PIN, INPUT_PULLUP);

  Serial.printf("setup(): Initializing SerialBT with advertisement '%s'\n",
                bluetoothAdvertisement.c_str());
  SerialBT.begin(bluetoothAdvertisement, false);
  Serial.printf("Back from SerialBT.begin()");
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
