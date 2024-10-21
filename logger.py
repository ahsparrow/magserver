import asyncio
import asyncio.stream
import os
import tarfile
import time

# End of touch timeout
READ_TIMEOUT = 5

# Number of archive log directories
MAX_ARCHIVES = 5

S_IFDIR = 0x4000


class Logger:
    def __init__(self, uart, root_dir):
        self.uart_stream = asyncio.stream.Stream(uart)
        self.root_dir = root_dir

        self.log_count = 0
        self.log_file = None

        self.vfs_size = self.get_vfs_size()

        self.event = asyncio.Event()

    # Main logging loop
    async def log(self):
        while True:
            try:
                data = await asyncio.wait_for(self.uart_stream.readline(), READ_TIMEOUT)

                data = data.split(b",")
                if data[0] == b"B":
                    if not self.log_file:
                        self.start = int(data[2])
                        self.start_log()

                    self.log_file.write(
                        ",".join(
                            [
                                data[1].decode(),
                                str(time.ticks_diff(int(data[2]), self.start)),
                            ]
                        )
                    )
                    self.log_file.write("\n")

                elif data[0] == b"D":
                    self.delays = [int(d) for d in data[1:]]
                    self.event.set()

            except asyncio.TimeoutError:
                if self.log_file:
                    self.log_file.close()
                    self.log_file = None

    # Start a new log file
    def start_log(self):
        if self.log_count == 0:
            self.rotate_logs()

        self.log_count += 1

        filename = self.log_path("log", "touch_{:02d}.csv".format(self.log_count))
        self.log_file = open(filename, "wt")

    # Rotate (and delete) archive directories
    def rotate_logs(self):
        # Do nothing if current log directory has no entries
        if len(os.listdir(self.log_path("log"))) == 0:
            return

        # Delete old archives if less than half the disk space is left or there
        # are more than MAX_ARCHIVES
        for dir in sorted(self.get_archive_dirs(), reverse=True):
            if (self.get_vfs_free() < self.vfs_size / 2) or (
                int(dir[-2:]) > MAX_ARCHIVES - 1
            ):
                self.delete_archive_dir(dir)

        # Rotate archive dirs
        dirs = self.get_archive_dirs()
        dirs.sort(reverse=True)
        for d in dirs:
            base, ind = d.split(".")
            os.rename(
                self.log_path(d),
                self.log_path("old-log.{}".format(int(ind) + 1)),
            )

        # Archive current log dir and create a new one
        os.rename(self.log_path("log"), self.log_path("old-log.1"))
        os.mkdir(self.log_path("log"))

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

    # Get archive log directories (ending in two digit number)
    def get_archive_dirs(self):
        return list(
            filter(
                lambda x: (os.stat(self.log_path(x))[0] & S_IFDIR != 0)
                and x[-2:].isdigit(),
                os.listdir(self.root_dir),
            )
        )

    # Delete an archive directory
    def delete_archive_dir(self, dir):
        log_path = self.log_path(dir)
        for f in os.listdir(log_path):
            os.remove(self.log_path(dir, f))

        os.rmdir(log_path)

    def get_log_info(self):
        log_dirs = self.get_archive_dirs()
        log_dirs.sort()
        log_dirs.insert(0, "log")

        log_counts = [len(os.listdir(self.log_path(d))) for d in log_dirs]
        return zip(log_dirs, log_counts)

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
