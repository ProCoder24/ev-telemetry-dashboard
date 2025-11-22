#include <SPI.h>
#include <mcp2515.h>

MCP2515 mcp2515(53);

struct can_frame CanMsg1;
struct can_frame CanMsg2;

void setup() {
  Serial.begin(115200);

  mcp2515.reset();
  mcp2515.setBitrate(CAN_500KBPS, MCP_8MHZ);
  mcp2515.setNormalMode();

  Serial.println("Example: Write to CAN");
}

void loop() {
  sendCANMessages();
  delay(100);
}

void sendCANMessages() {
  // Set up example CAN messages
  CanMsg1.can_id = 0x100;
  CanMsg1.can_dlc = 2;
  CanMsg1.data[0] = 0x11;
  CanMsg1.data[1] = 0x22;

  CanMsg2.can_id = 0x101;
  CanMsg2.can_dlc = 2;
  CanMsg2.data[0] = 0x33;
  CanMsg2.data[1] = 0x44;

  mcp2515.sendMessage(&CanMsg1);
  mcp2515.sendMessage(&CanMsg2);

  Serial.println("Messages sent");
}

