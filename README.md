docker build -t thiagomag/rpi-monitor:latest .

docker push thiagomag/rpi-monitor:latest

docker stop rpi-monitor-app

docker run -d \
  --name rpi-monitor-app \
  --restart unless-stopped \
  --privileged \
  --net="host" \
  --pid="host" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket \
  thiagomag/rpi-monitor:latest