#!/bin/bash

service_name="plasma-rtc"

#Require sudo
if [ $EUID != 0 ]; then
    sudo "$0" "$@"
    exit $?
fi

echo "adding service to /etc/systemd/system/..."
cp ${service_name}.service /etc/systemd/system/
chmod 644 /etc/systemd/system/$service_name.service
echo "done"

echo "starting and enabling $service_name service..."
systemctl daemon-reload
systemctl start $service_name
systemctl enable $service_name
echo "done"

echo "$service_name installed sucessfully!"
