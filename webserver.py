import os
import tarfile

from microdot import Microdot, Response, redirect, send_file
from microdot.utemplate import Template

S_IFDIR = 0x4000

delays = [100, 200, 300, 400, 500, 600]

app = Microdot()
Response.default_content_type = "text/html"


@app.route("/")
async def index(request):
    statvfs = os.statvfs(".")
    free = statvfs[0] * statvfs[4]

    dirs = list(filter(lambda d: os.stat("logs/" + d)[0] & S_IFDIR, os.listdir("logs")))
    dirs.sort()

    logcounts = [len(os.listdir("logs/" + d)) for d in dirs]

    return Template("index.tpl").render(dirs=dirs, logcounts=logcounts, free=free)


@app.route("/static/<path:path>")
async def static(request, path):
    if ".." in path:
        # directory traversal is not allowed
        return "Not found", 404
    return send_file("static/" + path, max_age=86400)


@app.get("/delays")
async def get_delays(request):
    return Template("delays.tpl").render(delays=delays)


@app.post("/delays")
async def set_delays(request):
    global delays
    if request.form["action"] == "ok":
        delays = [
            request.form.get("bell{}".format(i)) for i in range(len(request.form) - 1)
        ]
        print(delays)
    else:
        delays = [100, 200, 300, 400, 500, 600]

    return redirect("/delays")


@app.get("/download")
async def download(request):
    log_dir = request.args.get("log")
    with tarfile.TarFile("logs/log.tar", "w") as tf:
        for filename in os.listdir("logs/{}".format(log_dir)):
            tf.addfile(
                tarfile.TarInfo(filename), open("logs/{}/{}".format(log_dir, filename))
            )

    response = send_file("logs/log.tar", content_type="application/x-tar")
    response.headers["Content-Disposition"] = 'attachment; filename="log.tar"'

    return response


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.start_server(host="0.0.0.0", port=5000))
