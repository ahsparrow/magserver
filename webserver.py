import asyncio

from microdot import Microdot, Response, redirect, send_file
from microdot.utemplate import Template
from microdot.websocket import with_websocket

Response.default_content_type = "text/html"


def create_app(logger):
    app = Microdot()

    @app.route("/")
    async def index(request):
        log_info = logger.get_log_info()
        dirs, logcounts = list(zip(*log_info))

        return Template("index.tpl").render(
            dirs=dirs, logcounts=logcounts, free=logger.get_vfs_free()
        )

    @app.route("/static/<path:path>")
    async def static(request, path):
        if ".." in path:
            # directory traversal is not allowed
            return "Not found", 404
        return send_file("static/" + path, max_age=86400)

    @app.get("/delays")
    async def get_delays(request):
        try:
            delays = await asyncio.wait_for(logger.get_delays(), 1)
            return Template("delays.tpl").render(delays=delays)
        except asyncio.TimeoutError:
            return "Timeout waiting for delays from logger", 500

    @app.post("/delays")
    async def set_delays(request):
        if request.form["action"] == "ok":
            delays = [
                request.form.get("bell{}".format(i))
                for i in range(len(request.form) - 1)
            ]
            await logger.set_delays(delays)

        return redirect("/delays")

    @app.get("/download")
    async def download(request):
        log_dir = request.args.get("log")
        tarfile = logger.make_tar(log_dir)

        response = send_file(tarfile, content_type="application/x-tar")
        response.headers["Content-Disposition"] = 'attachment; filename="log.tar"'

        return response

    @app.get("/log")
    async def get_log_catalog(request):
        return logger.get_catalog(), 200, {"Content-Type": "text/plain"}

    @app.get("/log/<touch_num>")
    async def get_touch_data(request, touch_num):
        return (
            logger.get_touch_data(int(touch_num)),
            200,
            {"Content-Type": "text/plain"},
        )

    @app.get("/status")
    @with_websocket
    async def status(response, ws):
        log_status = logger.get_status()
        await ws.send(log_status)

        # Poll logger status
        while True:
            new_log_status = logger.get_status()
            if log_status != new_log_status:
                log_status = new_log_status

                await ws.send(log_status)

            # Do (dummy) receive to handle keep-alive pings
            try:
                await asyncio.wait_for(ws.receive(), 1)
            except asyncio.TimeoutError:
                pass

    return app
