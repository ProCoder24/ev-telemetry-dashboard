#include <SPI.h>
#include <mcp2515.h>

struct can_frame canMsg;
MCP2515 mcp2515(10);

void setup() {
  Serial.begin(115200);
  mcp2515.reset();
  mcp2515.setBitrate(CAN_500KBPS);
  mcp2515.setNormalMode();
  Serial.println("CAN Sender Ready");
}

void loop() {
  canMsg.can_id  = 0x300 | 0x80000000UL; // Extended frame, VESC style
  canMsg.can_dlc = 4;
  canMsg.data[0] = 0x12;
  canMsg.data[1] = 0x34;
  canMsg.data[2] = 0x56;
  canMsg.data[3] = 0x78;

  if (mcp2515.sendMessage(&canMsg) == MCP2515::ERROR_OK) {
    Serial.println("Sent test CAN msg");
  } else {
    Serial.println("Send failed!");
  }
  delay(1000);
}

