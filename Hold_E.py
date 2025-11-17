import keyboard
import time

try:
    print("Spamming 'E'... (Ctrl+C to stop)")
    while True:
        keyboard.press('e')
        time.sleep(0.05)  # Very short delay
        keyboard.release('e')
        time.sleep(0.05)  # Adjust speed as needed
except KeyboardInterrupt:
    print("Stopped")