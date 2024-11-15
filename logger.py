import asyncio
import asyncio.stream
import os
import tarfile

from time import ticks_diff, time

# End of touch timeout
READ_TIMEOUT = 5

# Number of archive log directories
MAX_ARCHIVES = 5

# Minimum number of strikes to record
MIN_STRIKES = 60

S_IFDIR = 0x4000


class Logger:
    def __init__(self, uart, root_dir):
        self.uart_stream = asyncio.stream.Stream(uart)
        self.root_dir = root_dir

        self.strike_count = 0
        self.bell_set = set()

        self.touch_count = 0
        self.log_file = None

        self.touch_start_ticks = 0

        self.touch_end_time = time()

        self.vfs_size = self.get_vfs_size()

        self.event = asyncio.Event()

        self.catalog_file = self.log_path("log", "_logcat.csv")

    # Main logging loop
    async def log(self):
        while True:
            try:
                data = await asyncio.wait_for(self.uart_stream.readline(), READ_TIMEOUT)

                data = data.split(b",")
                if data[0] == b"B":
                    # Bell strike data
                    bell = data[1].decode()
                    strike_ticks = int(data[2].decode())

                    if not self.log_file:
                        # Rotate logs if > 12 hours since last touch
                        if (
                            self.touch_count == 0
                            or (time() - self.touch_end_time) > 3600 * 12
                        ):
                            self.rotate_logs()

                        # Start new log
                        self.start_log(strike_ticks)

                    delta_ticks = ticks_diff(strike_ticks, self.touch_start_ticks)
                    log = "{},{}\n".format(bell, delta_ticks)
                    self.log_file.write(log)

                    self.strike_count += 1
                    self.bell_set.add(bell)

                elif data[0] == b"D":
                    # Reply to delay query request
                    self.delays = [int(d) for d in data[1:]]
                    self.event.set()

            except asyncio.TimeoutError:
                if self.log_file:
                    self.touch_end_time = time()
                    self.stop_log()

    def get_status(self):
        return "idle" if self.log_file is None else "logging"

    # Start a new log file
    def start_log(self, start_ticks):
        if self.touch_count == 0:
            self.session_start_ticks = start_ticks

        self.touch_count += 1

        # Open new touch file and write header
        self.log_file = open(self.touch_file(), "wt")
        self.log_file.write("bell,ticks_ms\n")

        # Reset touch info variables
        self.strike_count = 0
        self.bell_set.clear()
        self.touch_start_ticks = ticks_diff(start_ticks, self.session_start_ticks)

    # Stop logging
    def stop_log(self):
        # Close touch file
        self.log_file.close()
        self.log_file = None

        if self.strike_count < MIN_STRIKES:
            # Discard very short touches
            os.remove(self.touch_file())
            self.touch_count -= 1
        else:
            # Update touch catalog
            with open(self.catalog_file, "at") as f:
                nrows = self.strike_count // len(self.bell_set)
                f.write(
                    "{},{},{}\n".format(self.touch_count, nrows, self.touch_start_ticks)
                )

    # Rotate (and delete) archive directories
    def rotate_logs(self):
        # Do nothing if current log directory has no entries
        entries = os.listdir(self.log_path("log"))
        if sum(1 for e in entries if e.startswith("touch")) == 0:
            return

        # Delete old archives if less than half the disk space is left or there
        # are more than MAX_ARCHIVES
        dirs = self.get_archive_dirs()
        dirs.sort(reverse=True)
        for dir in dirs:
            if (self.get_vfs_free() < self.vfs_size / 2) or (
                int(dir[-1:]) > MAX_ARCHIVES - 1
            ):
                self.delete_archive_dir(dir)

        # Rotate archive dirs
        dirs = self.get_archive_dirs()
        dirs.sort(reverse=True)
        for d in dirs:
            base, ind = d.split(".")
            os.rename(
                self.log_path(d),
                self.log_path("{}.{}".format(base, int(ind) + 1)),
            )

        # Archive current log dir and create a new one
        os.rename(self.log_path("log"), self.log_path("old-log.1"))
        os.mkdir(self.log_path("log"))

        # Create new catalog and write header
        with open(self.catalog_file, "wt") as f:
            f.write("touch,rows,start_ticks_ms\n")

        # Reset touch count
        self.touch_count = 0

    # Path of current touch log
    def touch_file(self):
        return self.log_path("log", "touch_{:02d}.csv".format(self.touch_count))

    # Make full path of log dirs and files
    def log_path(self, *args):
        return "/".join([self.root_dir, "/".join(args)])

    # Get free bytes on file system
    def get_vfs_free(self):
        stat = os.statvfs("/")

        # f_bsize (block size) * f_bavail (free blocks for unprivilegded users)
        return stat[0] * stat[4]

    # File system size
    def get_vfs_size(self):
        stat = os.statvfs("/")

        # f_bsize(block size) * f_blocks (number of blocks)
        return stat[0] * stat[2]

    # Get archive log directories (ending in single digit number)
    def get_archive_dirs(self):
        return [
            d[0]
            for d in os.ilistdir(self.root_dir)
            if d[1] & S_IFDIR and d[0][-1].isdigit()
        ]

    # Delete an archive directory
    def delete_archive_dir(self, dir):
        log_path = self.log_path(dir)
        for f in os.listdir(log_path):
            os.remove(self.log_path(dir, f))

        os.rmdir(log_path)

    # Get number of touches in each log dir
    def get_log_info(self):
        log_dirs = self.get_archive_dirs()
        log_dirs.sort()
        log_dirs.insert(0, "log")

        # Count touch logs
        touch_counts = [
            sum(1 for f in os.listdir(self.log_path(d)) if f.startswith("touch"))
            for d in log_dirs
        ]

        return zip(log_dirs, touch_counts)

    # Get current log catalog
    def get_catalog(self):
        with open(self.catalog_file, "rt") as catfile:
            return catfile.read()

    # Get touch data. Use generator to avoid memory issues
    async def get_touch_data(self, touch_num, chunksize=1024):
        if touch_num == 0:
            # Get newest touch from current log directory
            logs = [
                d for d in os.listdir(self.log_path("log")) if d.startswith("touch")
            ]
            filename = sorted(logs)[-1]
        else:
            filename = self.log_path("log", "touch_{:02d}.csv".format(touch_num))

        try:
            with open(filename) as f:
                while True:
                    data = f.read(chunksize)
                    if not data:
                        break
                    yield data
        except OSError:
            yield ""

    def make_tar(self, log_dir):
        tar_path = self.log_path("download.tar")
        with tarfile.TarFile(tar_path, "w") as tf:
            for log in os.listdir(self.log_path(log_dir)):
                filename = self.log_path(log_dir, log)
                stat = os.stat(filename)

                tarinfo = tarfile.TarInfo(log)
                tarinfo.uid = stat[4]
                tarinfo.gid = stat[5]
                tarinfo.size = stat[6]
                tarinfo.mtime = stat[8]
                with open(filename) as f:
                    tf.addfile(tarinfo, f)

        return tar_path

    # Get bell delays from CAN interface
    async def get_delays(self):
        self.event.clear()

        # Send request
        self.uart_stream.write(b"G\n")
        await self.uart_stream.drain()

        # Wait for response
        await self.event.wait()
        return self.delays

    # Send new bell delays to CAN interface
    async def set_delays(self, delays):
        self.delays = delays

        self.uart_stream.write(b"D,")
        self.uart_stream.write(b",".join(str(d).encode() for d in self.delays))
        self.uart_stream.write(b"\n")
        await self.uart_stream.drain()
