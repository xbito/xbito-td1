import pygame
import sys

# Initialize Pygame
pygame.init()

# Set up the display
width, height = 640, 480
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pygame Test")

# Define colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Main game loop
clock = pygame.time.Clock()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Clear the screen
    screen.fill(BLACK)

    # Draw a white rectangle
    pygame.draw.rect(screen, WHITE, (50, 50, 100, 100))

    # Draw a red circle
    pygame.draw.circle(screen, RED, (320, 240), 50)

    # Update the display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(60)
