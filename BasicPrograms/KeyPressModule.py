import pygame


# Initialize a Pygame window required to capture keyboard input focus
def init():
    pygame.init()  # Initialize all imported Pygame modules
    win = pygame.display.set_mode((400, 400))  # Create a 400x400 pixel display window


# Detect whether a specific key is currently held down
def getKey(keyName):
    ans = False

    # CAUTION / BUG ALERT:
    # Pygame's event queue holds ALL pending user inputs (keypresses, mouse clicks, close events).
    # Calling `pygame.event.get()` empties this queue entirely. Because main() calls `getKey("LEFT")`
    # and then `getKey("RIGHT")`, the FIRST call consumes ALL pending events for that loop iteration.
    # The second call finds an EMPTY queue, breaking proper Pygame event state updating.
    for eve in pygame.event.get():
        pass  # Emptying event queue to keep Pygame responsive

    keyInput = pygame.key.get_pressed()  # Fetch current state of all keyboard keys (Boolean tuple)

    # Convert a string name (e.g., "LEFT") into Pygame's constant attribute (pygame.K_LEFT)
    myKey = getattr(pygame, "K_{}".format(keyName))

    if keyInput[myKey]:  # Check if target key is currently pressed
        ans = True

    pygame.display.update()  # Redraw display surface to the screen
    return ans


# Main logic function triggered every frame
def main():
    if getKey("LEFT"):
        print("Left key pressed")
    if getKey("RIGHT"):
        print("Right key pressed")


# Entry point execution guard
if __name__ == "__main__":
    init()  # Open game window once
    while True:  # Infinite game/teleop loop
        main()