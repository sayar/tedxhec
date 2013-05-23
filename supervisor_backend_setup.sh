sudo apt-get install supervisor
sudo echo_supervisord_conf > /etc/supervisord.conf
sudo echo "[program:tedxbackend]
command=/usr/bin/python /home/ubuntu/tedxhec/twinput.py
autorestart=true
directory=/home/ubuntu/tedxhec" >> /etc/supervisord.conf

sudo curl https://raw.github.com/gist/176149/88d0d68c4af22a7474ad1d011659ea2d27e35b8d/supervisord.sh > /etc/init.d/supervisord
sudo chmod +x /etc/init.d/supervisord
sudo update-rc.d supervisord defaults

sudo service supervisord start
