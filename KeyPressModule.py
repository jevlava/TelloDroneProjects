import pygame

# To detect a window, it should be in a game window

# Initialize a window for a game
def init(): # Initialize pygame
    pygame.init()
    win = pygame.display.set_mode((400,400)) #Initialize window

# Getting the keypress
def getKey(keyName):
    ans = False
    for eve in pygame.event.get(): pass # getting events
    keyInput = pygame.key.get_pressed() # getting input
    myKey = getattr(pygame, 'K_{}' .format(keyName))
    if keyInput[myKey]:
        ans = True
    pygame.display.update()
    return ans

def main():
    if getKey("LEFT"):
        print("Left key pressed")
    if getKey("RIGHT"):
        print("Right key pressed")

if __name__ == '__main__':
    init()
    while True:
        main()
