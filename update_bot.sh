#!/bin/bash

cd /home/ubuntu/ariana-tutor

git pull

sudo systemctl restart bot

echo "Atualizado!"
#!/bin/bash

cd /home/ubuntu/ariana-tutor

git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart bot

echo "Atualizado!"
