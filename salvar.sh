#!/bin/bash
cd ~/sistema-tutor
source venv/bin/activate
git add .
git commit -m "checkpoint: $(date '+%Y-%m-%d %H:%M')"
git push
echo "✅ Código salvo no GitHub!"
