#!/bin/bash
#   Linux chkconfig:
#   chkconfig: 2345 56 10
#   2345 56
#   2345 10
#   description: MPhoto start/stop/restart script
# Source function library.
SERVICE_NAME="MPhoto Web"
SERVICE_USER="compusky"
WORK_DIR="/home/compusky/mphoto-web"
export PYTHONPATH=${WORK_DIR}:${WORK_DIR}/mphoto:${WORK_DIR}/web

start() {
  if [[ `/usr/bin/whoami` == $SERVICE_USER ]]; then
    cd "${WORK_DIR}"
    conda activate mphoto
    export PYTHONPATH=$(pwd):$(pwd)/mphoto:$(pwd)/web
    gunicorn --workers=2 mphoto.wsgi
  else
    echo "You are not ${SERVICE_USER}."
}

stop() {
  cd $FOLDER
  kill -s TERM $( pidof /home/compusky/miniconda3/envs/mphoto/bin/python )
}

status() {
  echo "Running process: $( pidof /home/compusky/miniconda3/envs/mphoto/bin/python )"
}

#Body main
case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    echo "Restarting $SERVICE_NAME..."
    stop
    sleep 10
    start
    ;;
  state)
    echo "State "
  *)
    echo $"Usage: $0 {start|stop|restart}"
    exit 1
esac
exit 0