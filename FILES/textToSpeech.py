import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1" 

from gtts import gTTS
import pygame

def speak_text(text):
    tts = gTTS(text=text, lang='ro')
    tts.save("output.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("output.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue

