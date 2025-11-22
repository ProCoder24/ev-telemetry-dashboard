#include <SPI.h>
#include <mcp2515.h>

// CAN frame struct
struct can_frame canMsg;

// Create MCP2515 object, CS pin 10
MCP2515 mcp2515(10);

void setup() {
  Serial.begin(115200);

  // Initialize MCP2515
  mcp2515.reset();
  mcp2515.setBitrate(CAN_500KBPS);
  mcp2515.setNormalMode();

  Serial.println("------- CAN Send VESC RPM --------");
}

void loop() {
  uint8_t controller_id = 0; // VESC controller ID (usually 0)
  uint8_t packet_id = 3;     // CAN_PACKET_SET_RPM = 3

  int32_t rpm_value = 2500;  // RPM value to send

  // Construct extended CAN ID: packet_id in bits 8-15, controller_id bits 0-7
  uint32_t can_id = ((uint32_t)packet_id << 8) | controller_id;

  // Set the extended frame flag (bit 31)
  can_id |= 0x80000000UL;

  // Pack rpm_value into 4 bytes big-endian for CAN data
  canMsg.data[0] = (rpm_value >> 24) & 0xFF;
  canMsg.data[1] = (rpm_value >> 16) & 0xFF;
  canMsg.data[2] = (rpm_value >> 8) & 0xFF;
  canMsg.data[3] = rpm_value & 0xFF;

  canMsg.can_dlc = 4;      // Length of data
  canMsg.can_id = can_id;  // Extended CAN ID

  // Send CAN message
  if (mcp2515.sendMessage(&canMsg) == MCP2515::ERROR_OK) {
    Serial.print("Sent VESC RPM: ID=0x");
    Serial.print(canMsg.can_id, HEX);
    Serial.print(" Data=");
    for (int i = 0; i < canMsg.can_dlc; i++) {
      Serial.print(canMsg.data[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
  } else {
    Serial.println("Error sending CAN message");
  }

  delay(1000); // Send once per second
}
