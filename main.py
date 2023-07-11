import machine
import network
import ntptime
import time
import umqtt.simple as simple
from pimoroni_i2c import PimoroniI2C
from pimoroni import PICO_EXPLORER_I2C_PINS
import breakout_scd41
import config
import gc
from LCDModule import draw_rect, write_text, refresh_screen, colours

# Wi-Fi configuration
WIFI_SSID = config.WIFI_SSID
WIFI_PASSWORD = config.WIFI_PASSWORD

# MQTT configuration
MQTT_SERVER = config.MQTT_SERVER
MQTT_SCREEN_ON_TOPIC = config.MQTT_SCREEN_ON_TOPIC
MQTT_RESET_TOPIC = config.MQTT_RESET_TOPIC

# LCD configuration
LCD_WIDTH = 240
LCD_HEIGHT = 240

LINE_HEIGHT = 18

# Retry configuration
MAX_RETRY = 10

# Print memory usage
def print_memory_usage():
    lineNumber = 12
    memory_usage = gc.mem_free()
    print("Memory usage:", memory_usage, "bytes free")
    draw_rect(x=0, y=LINE_HEIGHT * lineNumber, height=LINE_HEIGHT)
    write_text("Mem free: {} bytes".format(memory_usage), x=8, y=LINE_HEIGHT * lineNumber, colour=colours["WHITE"])
    refresh_screen()

wifi_status = "Disconnected..."
mqtt_status = "Disconnected..."
time_status = "Not Synced..."
scd41_status = "Initializing..."
mqtt_client = None

# Function to write setup status to the screen
def write_setup_status():
    draw_rect()
    # write_text(message="Setting up...", x=8, y=8)
    write_text(message="Wi-Fi: {}".format(wifi_status), x=8, y=LINE_HEIGHT, colour=colours["GREEN"] if wifi_status.endswith("Connected") else colours["WHITE"])
    write_text(message="MQTT: {}".format(mqtt_status), x=8, y=LINE_HEIGHT*2, colour=colours["GREEN"] if mqtt_status.endswith("Connected") else colours["WHITE"])
    write_text(message="Time: {}".format(time_status), x=8, y=LINE_HEIGHT*3, colour=colours["GREEN"] if time_status.endswith("Synced") else colours["WHITE"])
    write_text(message="SCD41: {}".format(scd41_status), x=8, y=LINE_HEIGHT*4, colour=colours["GREEN"] if scd41_status.endswith("Initialized") else colours["WHITE"])
    refresh_screen()
    print_memory_usage()

# Connect to Wi-Fi network
def connect_wifi():
    global wifi_status
    global MAX_RETRY

    print("Connecting to Wi-Fi...")
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    # wifi.disconnect()  # Disconnect from the Wi-Fi network

    retry_count = 0

    if wifi.status() == 3:
        wifi_status = "Connected"
        print("Already connected to Wi-Fi!")
        write_setup_status()
        # gc.collect()
        return
    
    if wifi.status() != 3:
        wifi_status = "Disconnected..."
        # print("Disconnected from Wi-Fi!")
        write_setup_status()
        if retry_count < MAX_RETRY:
            try:
                wifi.connect(WIFI_SSID, WIFI_PASSWORD)
            except Exception as e:
                print("Failed to connect to Wi-Fi:", e)
                retry_count += 1
                wifi_status = "Attempt {}/{}".format(retry_count, MAX_RETRY)
                print(wifi_status)
                write_setup_status()
                # gc.collect()
                time.sleep(1)

# Retry ntptime.settime()
def retry_ntptime_settime():
    global MAX_RETRY
    retry_count = 0
    global time_status
    ntptime.host = "time.cloudflare.com"
    ntptime.timeout = 2

    while retry_count < MAX_RETRY:
        try:
            ntptime.settime()
            time_status = "Synced"
            write_setup_status()
            return True
        except Exception as e:
            retry_count += 1
            print("Failed to synchronize time. Retrying ({}/{})...".format(retry_count, MAX_RETRY))
            time_status = "Syncing ({}/{})...".format(retry_count, MAX_RETRY)
            write_setup_status()
            time.sleep(2)

    print("Max retries exceeded. Time synchronization failed.")
    time_status = "Not Synced..."
    return False


# Connect to MQTT server
def connect_mqtt():
    global mqtt_status
    global MAX_RETRY

    print("Connecting to MQTT server...")
    client_id = "clientId-8XjjDaTnWG_sensor"
    mqtt_client = simple.MQTTClient(client_id, MQTT_SERVER, port=1883, user=None, password=None, keepalive=10, ssl=False, ssl_params={})
    retry_count = 0

    while retry_count < MAX_RETRY * 2:
        try:
            mqtt_client.set_callback(mqtt_callback)
            mqtt_client.connect()
            mqtt_status = "Connected"
            write_setup_status()
            print("Connected to MQTT server!")
            return mqtt_client
        except Exception as e:
            # # gc.collect()
            print("Failed to connect to MQTT server:", e)
            retry_count += 1
            mqtt_status = "Attempt {}/{}".format(retry_count, MAX_RETRY * 2)
            write_setup_status()
            print(mqtt_status)
            time.sleep(2)

    mqtt_status = "Max retries exceeded"
    write_setup_status()
    #print("Max retries exceeded. Resetting the device...")
    #time.sleep(2)
    #machine.reset()

# Callback for MQTT message
def mqtt_callback(topic, msg):
    print(topic, msg)
    if topic.decode() == MQTT_SCREEN_ON_TOPIC:
        if msg.decode() == "on":
            set_backlight(100)
            print("Display backlight turned on.")
        elif msg.decode() == "off":
            set_backlight(0)
            print("Display backlight turned off.")
    elif topic.decode() == MQTT_RESET_TOPIC:
        print("Resetting the device...")
        draw_rect()
        write_text("Received Reset Command", x=8, y=LINE_HEIGHT)
        write_text("Resetting...", x=8, y=LINE_HEIGHT*4)
        refresh_screen()
        time.sleep(2)
        machine.reset()

# Publish message to MQTT topic
def publish_to_mqtt(mqtt_client, topic, message):
    try:
        mqtt_client.publish(topic, message)
        print("Published to topic:", topic)
    except Exception as e:
        print("Failed to publish to topic:", topic, e)

def subscribe_topics(mqtt_client):
    topic_list = [MQTT_SCREEN_ON_TOPIC, MQTT_RESET_TOPIC]  # List of topics to subscribe to

    for topic in topic_list:
        try:
            mqtt_client.subscribe(topic)
            print("Subscribed to topic:", topic)
        except Exception as e:
            print("Failed to subscribe to topic:", topic, e)

# Initialize SCD41 sensor
def initialize_scd41():
    global scd41_status

    try:
        scd41_status = "Initializing"
        print("Initializing SCD41 sensor...")
        i2c = PimoroniI2C(**PICO_EXPLORER_I2C_PINS)
        breakout_scd41.init(i2c)
        breakout_scd41.start()
        scd41_status = "Initialized"
        write_setup_status()
        print("SCD41 sensor initialized.")
    except Exception as e:
        print("Failed to initialize SCD41 sensor:", e)
        draw_rect()
        write_text("[SCD41] Resetting...", x=8, y=LINE_HEIGHT)
        refresh_screen()
        time.sleep(2)
        machine.reset()

# Check SCD41 readiness
def is_scd41_ready():
    try:
        # gc.collect()
        return breakout_scd41.ready()
    except Exception as e:
        print("Error checking SCD41 readiness:", e)
        return False

# Measure using SCD41
def measure_scd41():
    try:
        return breakout_scd41.measure()
    except Exception as e:
        print("Error measuring with SCD41:", e)
        return None, None, None

# Set backlight intensity
def set_backlight(level):
    BL = 13  # GPIO pin for backlight control
    pwm = machine.PWM(machine.Pin(BL))
    pwm.freq(1000)
    one_percent = 65535 / 100
    brightness = round(one_percent * level)
    pwm.duty_u16(brightness)  # Set the backlight level

# Print values on LCD and publish to MQTT
def print_values(co2, temperature, humidity):
    gc.collect()
    line_height = 8
    draw_rect()
    write_text(message="CO2", x=8, y=line_height, colour=colours["WHITE"])
    write_text(message="{} PPM".format(co2), x=8, y=line_height * 3, colour=colours["GREEN"])

    write_text(message="Humidity", x=8, y=line_height * 6, colour=colours["WHITE"])
    write_text(message="{}%".format(humidity), x=8, y=line_height * 8, colour=colours["GREEN"])

    write_text(message="Temperature", x=8, y=line_height * 11, colour=colours["WHITE"])
    write_text(message="{} C".format(temperature), x=8, y=line_height * 13, colour=colours["GREEN"])

    current_time = time.localtime()
    formatted_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        current_time[0], current_time[1], current_time[2], current_time[3], current_time[4], current_time[5]
    )
    print("CO2: {} PPM, Temperature: {} C, Humidity: {}%".format(co2, temperature, humidity))
    write_text(message=formatted_time, x=8, y=line_height * 18)
    print_memory_usage()
    refresh_screen()


# Main function
def main():
    global time_status
    mqtt_client = None  # Initialize MQTT client object

    print_memory_usage()
    write_setup_status()
    connect_wifi()
    print_memory_usage()
    write_setup_status()

    # try:
    #     connect_wifi()
    #     write_setup_status()  # Write Wi-Fi setup status
    #     # gc.collect()
    # except Exception as e:
    #     print("An error occurred while connecting to Wi-Fi:", e)

    print_memory_usage()  # Print memory usage after connecting to Wi-Fi
    time.sleep(2)

    try:
        mqtt_client = connect_mqtt()
        write_setup_status()  # Write MQTT setup status
        gc.collect()
    except Exception as e:
        print("An error occurred while connecting to MQTT server:", e)

    print_memory_usage()  # Print memory usage after connecting to MQTT server
    time.sleep(2)

    try:
        retry_ntptime_settime()
        write_setup_status()  # Write time sync setup status
        # gc.collect()
    except Exception as e:
        print("An error occurred while synchronizing time:", e)

    print_memory_usage()  # Print memory usage after synchronizing time
    time.sleep(2)

    


    try:
        initialize_scd41()
        write_setup_status()  # Write SCD41 setup status
        # gc.collect()
    except Exception as e:
        print("An error occurred while initializing SCD41 sensor:", e)

    print_memory_usage()  # Print memory usage after initializing SCD41 sensor

    if mqtt_client is not None:
        subscribe_topics(mqtt_client)  # Subscribe to MQTT topics

    while True:
        if mqtt_client is not None:
            mqtt_client.check_msg()
            time.sleep(5)
        try:
            if is_scd41_ready():
                co2, temperature, humidity = measure_scd41()
                print_values(co2, temperature, humidity)
                current_time = time.localtime()
                formatted_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                    current_time[0], current_time[1], current_time[2], current_time[3], current_time[4], current_time[5]
                )
                if mqtt_client is not None:
                    publish_to_mqtt(mqtt_client, "environment-monitor/carbondioxide", str(co2))  # Publish CO2 value to MQTT topic
                    publish_to_mqtt(mqtt_client, "environment-monitor/temperature", str(temperature))  # Publish temperature value to MQTT topic
                    publish_to_mqtt(mqtt_client, "environment-monitor/humidity", str(humidity))  # Publish humidity value to MQTT topic
                    publish_to_mqtt(mqtt_client, "environment-monitor/last_update", formatted_time)  # Publish last_update value to MQTT topic
        except Exception as e:
            print("An error occurred while measuring or printing values:", e)

        try:
            if mqtt_client is not None:
                mqtt_client.check_msg()
                time.sleep(5)
        except Exception as e:
            print("An error occurred while checking MQTT messages or sleeping:", e)

        # gc.collect()  # Perform garbage collection after each loop iteration



# Run the main function
if __name__ == "__main__":
    print("Starting application...")
    main()


