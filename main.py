from machine import UART, I2C, Pin, WDT
from binascii import hexlify
import ssd1306
from sml_extr import extract_sml
from simple_mqtt import MQTTClient
import utime
import ntptime
#############################################################
#board configuration
i2c = I2C(scl=Pin(4), sda=Pin(5))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
onbled = Pin(2, Pin.OUT)  # onboard led (blue)
uart = UART(2, 9600)
uart.init(9600, bits=8, parity=None, stop=1, timeout=100, timeout_char=100, rx=13, tx=15)  # init with given parameters

timezone = 0
sumtime = 0

# wifi
ssid = 'Cookie'
password = 'An35fP89htDw'

publish_int = 60  # Sekunden
buf = bytearray(500)

# mqtt settings
mqtt_server = "myServer"
mqtt_port = 8883  # using SSL/TLS (non-SSL = 1883)
mqtt_user = "USER"
mqtt_pw = "PASSWORD"
mqtt_client_id = "myDevice"
mqtt_topic = "myMQTTtopic"

mqtt = MQTTClient(client_id=mqtt_client_id, server=mqtt_server, port=mqtt_port, user=mqtt_user, password=mqtt_pw,
                  ssl=True)

#################################################################################################


def read_meter_data_uart():
    global buf

    oled.fill(0)
    oled.text('meter read...', 0, 0)
    oled.show()

    while True:
        if uart.any():
            uart.readinto(buf)
            uart.readinto(buf)  # double read to occure a timeout and get the startsequence first
            raw_str = str(hexlify(buf))

            if raw_str.find("1b1b1b1b") == 2:  # SML start/end sequence
                break

    res = extract_sml(raw_str)

    oled.fill(0)
    oled.text(res["devid"], 0, 0)
    oled.framebuf.hline(0, 12, 128, 1)
    oled.text("A+", 0, 16)
    oled.text(res["1.8.0_Wh"], 35, 16)
    oled.text("Wh", 110, 16)
    oled.text("P:", 0, 31)
    oled.text(res["16.7.0_W"], 35, 32)
    oled.text("W", 110, 32)
    oled.framebuf.hline(0, 48, 128, 1)
    oled.show()

    return res

#############################################################


onbled.on()  # on

icon = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 0, 0, 1, 1, 0],
    [1, 1, 1, 1, 0, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0],
]

oled.fill(0)  # Clear the display
for y, row in enumerate(icon):
    for x, c in enumerate(row):
        oled.pixel(x + 93, y + 23, c)

oled.text('IoT with ', 20, 25)
oled.text('Smart Meter MQTT', 5, 50)
oled.show()

utime.sleep(2)  # 2 seconds
onbled.off()  # off


#################################################################################################
# wifi connect

def do_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

    try:
        ntptime.settime()  # sync RTC with NTP-Server
        print('calender time (year, month, mday, hour, minute, second, weekday, yearday):', utime.localtime())
    except Exception as e:
        print(e)


do_connect()

wdt = WDT(timeout=8000)  # enable it with a timeout of 8s
wdt.feed()

#################################################################################################


def timestamp():
    t = utime.localtime()
    ms = utime.ticks_ms() % 1000
    ts = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:03d}Z".format(t[0], t[1], t[2], t[3]+timezone, t[4], t[5], ms)
    return ts


def build_msg():
    global mqtt_client_id

    props = ''
    try:
        data = read_meter_data_uart()  # returns a kv-dictionary
        length = len(data)
        for k, v in data.items():
            length -= 1

            if k == "devid":
                v = '"' + v + '"'

            props = props + '{"name":"' + k + '","value":' + v + ',"last_changed":"' + timestamp() + '"}'

            if length > 0:
                props = props + ','

    except:
        props = '{"name":"error","unit":"error","value":0,"last_changed":"' + timestamp() + '"}'

    msg = '{"device_id":"' + mqtt_client_id + '","timestamp":"' + timestamp() + '","properties":[' + props + ']}'

    return msg


def pub_msg():
    mqtt_msg = build_msg()
    mqtt.connect()
    mqtt.publish(topic=mqtt_topic, msg=mqtt_msg)
    mqtt.disconnect()


i = 0
while True:
    utime.sleep_ms(1000)

    wdt.feed()

    if i == 60:
        i = 0
        pub_msg()
        oled.text("published", 0, 55)
        oled.show()

    i += 1
