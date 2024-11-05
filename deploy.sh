#!/bin/sh

dirs="log log/log microdot static templates utemplate"

files="
  main.py
  logger.py
  webserver.py
  microdot/__init__.py
  microdot/helpers.py
  microdot/microdot.py 
  microdot/utemplate.py
  microdot/websocket.py
  static/pure-min.css
  static/style.css
  templates/delays.tpl
  templates/index.tpl
  utemplate/compiled.py
  utemplate/recompile.py
  utemplate/source.py"

usage() {
  echo "Usage: $0 device"
  exit 1
}

if [ $# -ne 1 ]; then
  usage
fi

# Create new file system (from micropython/ports/rp2/modules/_boot.py)
mpremote connect $1 exec "import rp2; import vfs; vfs.umount('/'); bdev=rp2.Flash(); vfs.VfsLfs2.mkfs(bdev, progsize=256); fs=vfs.VfsLfs2(bdev, progsize=254); vfs.mount(fs, '/')"

# Add libraries
mpremote connect $1 mip install tarfile
mpremote connect $1 mip install tarfile-write

# Create directories
for d in $dirs; do
  mpremote connect $1 mkdir :$d
done

# Copy files
for f in $files; do
  mpremote connect $1 cp $f :$f
done

# Set WiFi access point
mpremote connect $1 cp boot_ap.py :boot.py

# Reboot
mpremote connect $1 reset
