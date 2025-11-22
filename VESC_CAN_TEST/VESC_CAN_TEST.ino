#include <SPI.h>
#include <ACAN2515.h>

// MCP2515 SPI CS and INT pins
#define CS_PIN 53
#define INT_PIN 2

// CAN bit rate
const uint32_t CAN_BAUD = 500000;

// 8MHz crystal if 16MHz fails
ACAN2515Settings settings(CAN_BAUD, 8000000UL);


// Create CAN controller instance (CS pin, SPI instance, INT pin)
ACAN2515 can(CS_PIN, SPI, INT_PIN);

void setup() {
    Serial.begin(115200);
    while (!Serial);

    // Initialize CAN controller with settings, no interrupt handler
    uint16_t error = can.begin(settings, nullptr);
    if (error == 0) {
        Serial.println("CAN init OK!");
    } else {
        Serial.print("CAN init FAIL! Error code: ");
        Serial.println(error);
        while (true);
    }
}

void loop() {
    uint8_t controller_id = 0;  // VESC controller ID
    uint8_t packet_id = 3;      // CAN_PACKET_SET_RPM

    int32_t rpm_value = 2500;   // RPM to send

    // Build the extended CAN ID: controller_id + (packet_id << 8)
    // Then set highest bit (bit 31) to mark extended frame
    uint32_t can_id = ((uint32_t)packet_id << 8) | controller_id;
    can_id |= (1UL << 31);  // Set extended frame bit

    // Pack RPM as big-endian bytes
    uint8_t data[4];
    data[0] = (rpm_value >> 24) & 0xFF;
    data[1] = (rpm_value >> 16) & 0xFF;
    data[2] = (rpm_value >> 8) & 0xFF;
    data[3] = rpm_value & 0xFF;

    // Create CAN message
    CANMessage msg;
    msg.id = can_id;
    msg.len = 4;
    memcpy(msg.data, data, 4);

    // Send the CAN message via tryToSend()
    uint16_t sendError = can.tryToSend(msg);
    if (sendError == 0) {
        Serial.print("Sent VESC RPM packet: ID=0x");
        Serial.print(can_id, HEX);
        Serial.print(" Data=");
        for (int i = 0; i < 4; i++) {
            Serial.print(data[i], HEX);
            Serial.print(" ");
        }
        Serial.println();
    } else {
        Serial.print("CAN send error: ");
        Serial.println(sendError);
    }

    delay(1000); // Send every second
}

