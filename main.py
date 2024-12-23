# CANBell - Bell sensor
#
# Copyright (C) 2024  Alan Sparrow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import machine

import webserver
import logger


async def start():
    uart = machine.UART(1, tx=4, rx=5)
    log = logger.Logger(uart, "log")

    app = webserver.create_app(log)
    ws = app.start_server(port=80)

    await asyncio.gather(ws, log.log())


asyncio.run(start())
