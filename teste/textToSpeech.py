import os
from gtts import gTTS
import pygame

# Ascunde mesajul de la Pygame
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

def speak_text(text):
    tts = gTTS(text=text, lang='ro')
    tts.save("output.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("output.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        continue  # Așteaptă până când termină de redat audio
