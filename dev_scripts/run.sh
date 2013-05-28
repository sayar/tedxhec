#! /bin/sh

mkdir -p logs/
touch logs/input.log logs/server.log

sudo ./twinput.py > logs/input.log &
sudo ./serve.py -P 80 > logs/server.log &
