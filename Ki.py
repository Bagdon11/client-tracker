import keyboard
import time

try:
    while True:
        keyboard.press('c')
        time.sleep(8)
        keyboard.release('c')
        
        keyboard.press('q')
        time.sleep(25)
        keyboard.release('q')
        
except KeyboardInterrupt:
    print("\nScript stopped by user")