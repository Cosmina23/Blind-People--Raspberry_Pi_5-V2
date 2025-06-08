#!/bin/bash

cd /home/cosmina/Documente/Proiect1 || exit

# Activează mediul virtual
source ./Project1/bin/activate

# Pornește ngrok (dacă ai fișier de config ~/.ngrok2/ngrok.yml cu `tunnels`)
ngrok start --all &

# Așteaptă câteva secunde ca ngrok să se conecteze
sleep 5

# Pornește aplicația principală (fără output în terminal)
python ./FILES/main.py 2>/dev/null
