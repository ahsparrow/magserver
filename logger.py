import asyncio
import os

# End of touch timeout
READ_TIMEOUT = 5

# Number of archive log directories
MAX_ARCHIVES = 10

S_IFDIR = 0x4000


class Logger:
    def __init__(self, uart, root_dir):
        self.reader = asyncio.StreamReader(uart)
        self.root_dir = root_dir

        self.log_count = 0
        self.log_file = None

        self.vfs_size = self.get_vfs_size()

    # Main logging loop
    async def log(self):
        while True:
            try:
                data = await asyncio.wait_for(self.reader.readline(), READ_TIMEOUT)
            except asyncio.TimeoutError:
                print("timeout")
                data = ""

            if data:
                if not self.log_file:
                    self.start_log()

                self.log_file.write(data)

            else:
                if self.log_file:
                    self.log_file.close()
                    self.log_file = None

    # Start a new log file
    def start_log(self):
        if self.log_count == 0:
            self.rotate_logs()

        self.log_count += 1

        filename = self.log_path("log", "touch_{:02d}.txt".format(self.log_count))
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
                self.log_path("log.{:02d}".format(int(ind) + 1)),
            )

        # Archive current log dir and create a new one
        os.rename(self.log_path("log"), self.log_path("log.01"))
        os.mkdir(self.log_path("log"))

    # Make full path of log dirs and files
    def log_path(self, *args):
        return "/".join([self.root_dir, "/".join(args)])

    # Get free bytes on file system
    def get_vfs_free(self):
        stat = os.statvfs(self.root_dir)

        # f_bsize (block size) * f_bavail (free blocks for unprivilegded users)
        return stat[0] * stat[4]

    # File system size
    def get_vfs_size(self):
        stat = os.statvfs(self.root_dir)

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


# import machine
# uart = machine.UART(1, tx=4, rx=5)
# logger = Logger(uart, "/log")

# asyncio.run(logger.log())
