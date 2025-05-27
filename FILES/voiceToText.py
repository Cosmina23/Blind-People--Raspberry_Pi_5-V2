import os
import sys

# Dezactivează mesajele ALSA și redirecționează erorile
os.environ["PULSE_SERVER"] = "unix:/run/user/1000/pulse/native"
os.environ["ALSA_LOG_LEVEL"] = "0"
os.environ["PYTHONWARNINGS"] = "ignore"
sys.stderr = open(os.devnull, "w")  # Trimite toate erorile către /dev/null

import speech_recognition as sr
import asyncio

async def recognize_speech():
    recognizer = sr.Recognizer()

    # Alege indexul corect din lista dispozitivelor
    device_index = None # Pune aici indexul corect

    def blocking_recognition():
        with sr.Microphone(device_index=device_index) as source:
            print("Înregistrează acum...")
            audio = recognizer.record(source, duration=5)
            print("Se procesează...")
            try:
                text = recognizer.recognize_google(audio, language="ro-RO")
                print(f"Textul recunoscut: {text}")
                return text
            except sr.UnknownValueError:
                print("Nu am înțeles ce ai spus.")
                return ""
            except sr.RequestError as e:
                print(f"Eroare la conectarea la Google Speech Recognition: {e}")
                return ""

    # Rulează recunoașterea vocală într-un thread separat
    text = await asyncio.to_thread(blocking_recognition)
    return text
