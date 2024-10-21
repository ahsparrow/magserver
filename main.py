import asyncio
import machine
import network

import secrets
import webserver
import logger


def connect():
    station = network.WLAN(network.STA_IF)
    if station.isconnected():
        print("Already connected")
        print(station.ifconfig())
        return

    station.active(True)
    station.connect(secrets.SSID, secrets.PASSWORD)

    while not station.isconnected():
        pass

    print("Connected")
    print(station.ifconfig())


async def start():
    uart = machine.UART(1, tx=4, rx=5)
    log = logger.Logger(uart, "log")

    app = webserver.create_app(log)

    ws = app.start_server(port=80)

    await asyncio.gather(ws, log.log())


def main():
    network.hostname("canbell")
    connect()

    asyncio.run(start())


main()
