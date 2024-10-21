import asyncio
import os
import webserver


class TestLogger:
    def __init__(self):
        self.root_dir = "log"

    async def log(self):
        await asyncio.sleep(1)

    def get_log_info(self):
        log_dirs = self.get_archive_dirs()
        log_dirs.sort()
        log_dirs.insert(0, "log")

        log_counts = [len(os.listdir(self.log_path(d))) for d in log_dirs]
        return zip(log_dirs, log_counts)

    def log_path(self, *args):
        return "/".join([self.root_dir, "/".join(args)])

    def get_archive_dirs(self):
        return list(
            filter(
                lambda x: (os.path.isdir(os.path.join(self.root_dir, x)))
                and x[-1:].isdigit(),
                os.listdir(self.root_dir),
            )
        )

    def get_vfs_free(self):
        return 123456

    async def get_delays(self):
        await asyncio.sleep(0.5)
        return [100, 200, 300, 400, 500, 600]

    async def set_delays(self, delays):
        print(delays)


logger = TestLogger()

app = webserver.create_app(logger)
app.run()
