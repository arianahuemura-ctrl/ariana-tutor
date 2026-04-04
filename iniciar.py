import threading
import subprocess
import time

def rodar_tutor():
    subprocess.run(["python3", "tutor.py"])

def rodar_notificacoes():
    subprocess.run(["python3", "notificacoes.py"])

if __name__ == "__main__":
    print("Iniciando sistema completo...")
    
    t1 = threading.Thread(target=rodar_tutor)
    t2 = threading.Thread(target=rodar_notificacoes)
    
    t1.start()
    time.sleep(2)
    t2.start()
    
    print("Bot de respostas: ON")
    print("Notificacoes: ON")
    
    t1.join()
    t2.join()