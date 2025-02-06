# combat.py
import pygame
import sys
import random
import time

# Define colors.
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
GREEN   = (0, 255, 0)
ORANGE  = (255, 165, 0)
RED     = (255, 0, 0)
GRAY    = (200, 200, 200)

def compute_feedback(secret, guess):
    """
    Compute feedback for a guess against the secret.
    Returns a list of colors corresponding to each digit:
      - GREEN if digit and position are correct.
      - ORANGE if digit is in the secret but in a different position.
      - RED if digit is not in the secret.
    """
    feedback = [RED] * 4
    secret_copy = secret.copy()
    guess_copy = guess.copy()

    # First pass: correct position.
    for i in range(4):
        if guess[i] == secret[i]:
            feedback[i] = GREEN
            secret_copy[i] = None
            guess_copy[i] = None

    # Second pass: correct digit, wrong position.
    for i in range(4):
        if guess_copy[i] is not None and guess_copy[i] in secret_copy:
            feedback[i] = ORANGE
            index = secret_copy.index(guess_copy[i])
            secret_copy[index] = None

    return feedback

def animate_guess_row(screen, font, guess_str, feedback, final_x, y_pos, box_size, gap, frames=15):
    """
    Animate the guess row sliding in from the right.
    The row starts at an x offset (final_x + offset) and moves to final_x over a number of frames.
    """
    # Determine start offset (off-screen to the right).
    start_offset = 200
    for frame in range(frames):
        # Interpolate x position.
        offset = start_offset * (1 - frame / frames)
        current_x = final_x + offset
        # Clear row area.
        row_rect = pygame.Rect(0, y_pos, screen.get_width(), box_size)
        pygame.draw.rect(screen, BLACK, row_rect)
        # Draw each block with digit and its feedback color.
        for i in range(4):
            rect = pygame.Rect(current_x + i * (box_size + gap), y_pos, box_size, box_size)
            pygame.draw.rect(screen, feedback[i], rect)
            digit_surface = font.render(guess_str[i], True, WHITE)
            screen.blit(digit_surface, (rect.centerx - digit_surface.get_width()//2,
                                        rect.centery - digit_surface.get_height()//2))
        pygame.display.flip()
        pygame.time.delay(30)

def combat_minigame(enemy_hp=3, attempts_allowed=5):
    """
    A Pygame combat minigame.
    
    The player must guess a secret 4-digit number (each digit 1-9). After each guess, four boxes display
    the player's guess with colored feedback:
      - GREEN: digit correct and in correct position.
      - ORANGE: digit correct but in wrong position.
      - RED: digit not in the secret.
      
    The player gets a fixed number of attempts. Each guess is animated by sliding in from the right.
    If the player guesses correctly before the attempts run out, the combat is won.
    Otherwise, the combat is lost.
    
    Returns enemy_hp (full damage) if victory, or 0 if failed.
    """
    pygame.init()
    # Set up window.
    width, height = 500, 500
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Combat!")
    font = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()

    # Generate secret 4-digit number (each digit between 1 and 9).
    secret = [str(random.randint(1, 9)) for _ in range(4)]
    # Uncomment next line for debugging:
    # print("Secret:", ''.join(secret))
    
    # Layout parameters.
    box_size = 60
    gap = 10
    top_margin = 60  # space for instructions
    history_start_y = top_margin + 50  # start drawing guess history below instructions
    input_y = height - box_size - 50  # input row is near bottom
    attempts_text_y = top_margin  # Attempts text at top

    history = []  # Each element is a tuple: (guess_str, feedback)
    current_guess = ""
    attempt = 0
    victory = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    current_guess = current_guess[:-1]
                elif event.key == pygame.K_RETURN:
                    if len(current_guess) == 4:
                        attempt += 1
                        guess_list = list(current_guess)
                        feedback = compute_feedback(secret, guess_list)
                        # Animate the new guess row.
                        row_y = history_start_y + (attempt - 1) * (box_size + gap)
                        final_x = (width - (4 * box_size + 3 * gap)) // 2
                        animate_guess_row(screen, font, current_guess, feedback, final_x, row_y, box_size, gap)
                        history.append((current_guess, feedback))
                        if current_guess == ''.join(secret):
                            victory = True
                            running = False
                        elif attempt >= attempts_allowed:
                            running = False
                        current_guess = ""
                else:
                    if event.unicode and event.unicode in "123456789":
                        if len(current_guess) < 4:
                            current_guess += event.unicode

        # Draw background.
        screen.fill(BLACK)
        
        # Render instructions.
        instr_text = font.render("Guess the 4-digit number", True, WHITE)
        screen.blit(instr_text, (width//2 - instr_text.get_width()//2, 10))
        
        # Render attempts counter.
        attempts_text = font.render(f"Attempt {attempt+1}/{attempts_allowed}", True, WHITE)
        screen.blit(attempts_text, (20, attempts_text_y))
        
        # Render history.
        for idx, (guess_str, colors) in enumerate(history):
            x_start = (width - (4 * box_size + 3 * gap)) // 2
            y_pos = history_start_y + idx * (box_size + gap)
            for i in range(4):
                rect = pygame.Rect(x_start + i * (box_size + gap), y_pos, box_size, box_size)
                pygame.draw.rect(screen, colors[i], rect)
                digit_surface = font.render(guess_str[i], True, WHITE)
                screen.blit(digit_surface, (rect.centerx - digit_surface.get_width()//2,
                                            rect.centery - digit_surface.get_height()//2))
        
        # Render input row.
        x_start = (width - (4 * box_size + 3 * gap)) // 2
        y_pos = input_y
        for i in range(4):
            rect = pygame.Rect(x_start + i * (box_size + gap), y_pos, box_size, box_size)
            pygame.draw.rect(screen, GRAY, rect, 2)
            if i < len(current_guess):
                digit_surface = font.render(current_guess[i], True, WHITE)
                screen.blit(digit_surface, (rect.centerx - digit_surface.get_width()//2,
                                            rect.centery - digit_surface.get_height()//2))
        
        pygame.display.flip()
        clock.tick(30)
    
    # Final result screen.
    screen.fill(BLACK)
    if victory:
        result_text = font.render("Victory! Enemy defeated.", True, GREEN)
    else:
        result_text = font.render(f"Defeat. Answer: {''.join(secret)}", True, RED)
    screen.blit(result_text, (width//2 - result_text.get_width()//2, height//2 - result_text.get_height()//2))
    pygame.display.flip()
    time.sleep(2)
    pygame.quit()
    return enemy_hp if victory else 0
