import random
from config import *


def text_box(surface, font, x_start, x_end, y_start, text, colour ):
    x = x_start
    y = y_start
    words = text.split(' ')

    for word in words:
        word_t = font.render(word, True, colour)
        if word_t.get_width() + x <= x_end:
            surface.blit(word_t, (x, y))
            x += word_t.get_width() + 6
        else:
            y += word_t.get_height() + 3
            x = x_start
            surface.blit(word_t, (x, y))
            x += word_t.get_width() + 6


def write_something_sassy(pygame, stery_lines, font, win):

    idx_of_stera = random.randint(0, len(stery_lines) - 1)
    sassy_text = stery_lines[idx_of_stera][:-1]

    pygame.draw.rect(win, BLACK, (WIDTH // 2 - 5, 0, 10, HEIGHT))
    text_box(win, font, WIDTH * 1/3, WIDTH * 5/7, HEIGHT * 2/5, sassy_text, WHITE)

    pygame.display.update()
    pygame.time.delay(4000)
