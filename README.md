
## Repository Git pentru codul e pe Raspberry Pi:
https://github.com/Cosmina23/Blind-People--Raspberry_Pi_5-V2.git

## Repository Git pentru aplicație:
https://github.com/Cosmina23/VocaNav_1.git


## Descriere generală:

VocaNav este un sistem de asistență navigată destinat persoanelor cu probleme de vedere.
Acesta include o aplicație mobilă dezvoltată în React Native (Expo) cu backend în Flask (Python), conectată la o bază de date MySQL. Aplicația permite autentificarea utilizatorilor, salvarea traseelor parcurse, locațiilor vizitate.
Sistemul include ca și componentă principală Raspberry Pi 5 ce realizează principalele funcționalități în sistem: calculul traseelor, determinarea trecerilor de pietoni, procesarea imaginilor și generarea de indicații pentru orientare.

## Pașii de instalare și rulare:

### 1. Backend (Flask + MySQL)

#### a. Instalează Python 3.13+  
#### b. Creează un mediu virtual:
```bash
python -m venv venv_flask
```

#### c. Activează-l:
Windows PowerShell:
```bash
.
venv_flask\Scripts\activate
```

#### e. Creează baza de date `vocanav1` în MySQL  

#### f. Rulează serverul:
```bash
python ./backend/app.py
```

---

### 2. Frontend (React Native + Expo)

#### a. Instalează Node.js 
#### b. Instalează Expo CLI:
```bash
npm install -g expo-cli
```

#### c. Intră în folderul frontend:
```bash
cd BACAKDEV/VocaProject
```

#### d. Instalează dependențele:
```bash
npm install
```

#### e. Rulează aplicația:
```bash
npx expo start --tunnel
```

#### f. Deschide aplicația cu **Expo Go** pe telefon (QR code generat)

---

### 3. Raspberry Pi 5
#### Cerințe
- Python 3.8+
- [Ngrok](https://ngrok.com/)
- Microfon funcțional
- Sistem de operare: Linux (testat pe Ubuntu)

#### a. Instalarea bibliotecilor necesare
```bash
pip install -r requirements.txt
```

#### b. Creare mediu virtual 
```bash
python3 -m venv venv
source venv/bin/activate 
```

#### c. Pornire server WebSocket
```bash
python server.py
```

#### d. Pornire tunel Ngrok (pentru acces extern, dacă este cazul)
```bash
ngrok http 8765
```


#### e. Pornirea programului principal din mediul virtual
```bash
python ./FILES/main.py
```
