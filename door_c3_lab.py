import network
import time
from machine import Pin, unique_id
import ubinascii
from umqtt.simple import MQTTClient
import urequests

# Wi-Fi credentials
SSID = "AAL_HOUSE"
PASSWORD = "Sm@rtTH0usE21"

# MQTT Broker details
MQTT_BROKER = "10.10.30.200"
MQTT_PORT = 1883
MQTT_TOPIC = "home/door_lab"
MQTT_CLIENT_ID = ubinascii.hexlify(unique_id()).decode()

# Telegram bot credentials
BOT_TOKEN = "7718187066:AAFNaTtwokEmNeP6V1WisLnPqh2ShWyz2y4"  # Replace with your Telegram Bot Token
CHAT_ID = "7427164267"  # Replace with your Telegram Chat ID
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# GPIO Pin for reed switch
REED_SWITCH_PIN = 5

# Initialize reed switch with internal pull-up resistor
reed_switch = Pin(REED_SWITCH_PIN, Pin.IN, Pin.PULL_UP)

# Connect to Wi-Fi
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Already connected to Wi-Fi")
        return wlan

    print(f"Connecting to Wi-Fi: {SSID}...")
    wlan.connect(SSID, PASSWORD)

    # Wait for connection
    for _ in range(20):  # 20 seconds timeout
        if wlan.isconnected():
            print("Wi-Fi connected")
            print("Network config:", wlan.ifconfig())
            return wlan
        time.sleep(1)

    # Fail if unable to connect
    raise RuntimeError("Failed to connect to Wi-Fi")

# Publish MQTT message
def send_mqtt_message(client, message):
    try:
        # Encode the message to UTF-8 before publishing
        client.publish(MQTT_TOPIC, message.encode('utf-8'))
        print(f"MQTT message sent: {message}")
    except Exception as e:
        print(f"Failed to send MQTT message: {e}")

# Send Telegram message
def send_telegram_message(message):
    try:
        url = f"{TELEGRAM_API}?chat_id={CHAT_ID}&text={message}"
        response = urequests.get(url)
        print("Telegram message sent:", response.text)
        response.close()
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

# Monitor door and send status if open for longer than 10 seconds
def monitor_door(client):
    prev_status = None
    open_time = None  # Time when the door was opened
    notification_sent = False  # Track if a message has been sent
    while True:
        # Check reed switch state
        status = reed_switch.value() == 1  # 1 = Open, 0 = Closed
        current_time = time.time()

        if status:  # Door is open
            if prev_status != status:  # Door just opened
                open_time = current_time  # Record the time the door was opened
                notification_sent = False  # Reset notification flag
                print("Door opened, timer started.")

            elif open_time and not notification_sent and (current_time - open_time > 10):
                # Door has been open for more than 10 seconds
                door_status = "Ανοιχτή"
                print(f"Door is {door_status} for longer than 10 seconds.")
                send_mqtt_message(client, door_status)
                send_telegram_message(f"Η πόρτα είναι {door_status}! Ελέγξτε μήπως δεν την κλείσατε!")
                notification_sent = True  # Mark that the notification was sent

        else:  # Door is closed
            if prev_status != status:  # Door just closed
                print("Door closed.")
            open_time = None  # Reset open time
            notification_sent = False  # Reset notification flag

        prev_status = status
        time.sleep(0.1)  # Polling delay

# Main execution
try:
    # Connect to Wi-Fi
    wlan = connect_to_wifi()

    # Connect to MQTT broker
    mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    mqtt_client.connect()
    print(f"Connected to MQTT broker at {MQTT_BROKER}")

    # Monitor door and send notifications
    monitor_door(mqtt_client)
except Exception as e:
    print(f"Error: {e}")