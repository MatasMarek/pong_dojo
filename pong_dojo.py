import pygame
pygame.init()
import random

WIDTH, HEIGHT = 700, 500
WIN = pygame.display.set_mode((WIDTH, HEIGHT))

PADDLE_WIDTH, PADDLE_HEIGHT = 20, 100
BALL_RADIUS = 7
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

SCORE_FONT = pygame.font.SysFont("comicsans", 50)
SASS_FONT = pygame.font.SysFont("comicsans", 20)
WINNING_SCORE = 10

stery_file = open('stery.txt', "r")
LIST_OF_STERY_LINES = stery_file.readlines()


class Paddle:
    VEL = 4

    def __init__(self, x, y, width, height, color):
        self.color = color
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def draw(self, win):
        pygame.draw.rect(win, self.color, (self.x, self.y, self.width, self.height))

    def move(self, up=True):
        if up:
            if self.y - self.VEL > 0:
                self.y -= self.VEL
            else:
                self.y = 0
        else:
            if self.y + PADDLE_HEIGHT + self.VEL < HEIGHT:
                self.y += self.VEL
            else:
                self.y = HEIGHT - PADDLE_HEIGHT

class Ball:
    MAX_VEL = 5
    COLOR = WHITE

    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.x_vel = self.MAX_VEL
        self.y_vel = 0

    def move(self):
        self.x += self.x_vel
        self.y += self.y_vel

    def draw(self, win):
        pygame.draw.circle(win, self.COLOR, (self.x, self.y), self.radius)


def draw(win, paddles, ball, left_score, right_score):
    win.fill(BLACK)
    left_score_text = SCORE_FONT.render(f"{left_score}", 1, WHITE)
    right_score_text = SCORE_FONT.render(f"{right_score}", 1, WHITE)
    win.blit(left_score_text, (WIDTH//4 - left_score_text.get_width()//2, 20))
    win.blit(right_score_text, (WIDTH * 3//4 - right_score_text.get_width()//2, 20))

    for paddle in paddles:
        paddle.draw(win)

    for i in range(10, HEIGHT, HEIGHT//20):
        if i % 2 == 1:
            continue
        pygame.draw.rect(win, WHITE, (WIDTH//2 - 5, i, 10, HEIGHT//20))

    ball.draw(win)
    pygame.display.update()


def handle_paddle_movement(keys, left_paddle, right_paddle):
    if keys[pygame.K_w]:
        left_paddle.move(up=True)
    if keys[pygame.K_s]:
        left_paddle.move(up=False)

    if keys[pygame.K_UP]:
        right_paddle.move(up=True)
    if keys[pygame.K_DOWN]:
        right_paddle.move(up=False)


def handle_collision(ball, left_paddle, right_paddle):
    if ball.y - ball.radius <= 0:
        ball.y_vel *= -1
    elif ball.y + ball.radius >= HEIGHT:
        ball.y_vel *= -1

    if ball.x_vel < 0:
        if ball.y >= left_paddle.y and ball.y <= left_paddle.y + left_paddle.height:
            if ball.x - ball.radius + ball.x_vel <= left_paddle.x + left_paddle.width:
                ball.x_vel *= -1

                middle_y = left_paddle.y + left_paddle.height/2
                difference_in_y = ball.y - middle_y
                relative_distance = difference_in_y / (left_paddle.height/2)
                ball.y_vel = relative_distance * ball.MAX_VEL

    else:
        if ball.y >= right_paddle.y and ball.y <= right_paddle.y + right_paddle.height:
            if ball.x + ball.radius + ball.x_vel >= right_paddle.x:
                ball.x_vel *= -1

                middle_y = right_paddle.y + right_paddle.height/2
                difference_in_y = ball.y - middle_y
                relative_distance = difference_in_y / (right_paddle.height/2)
                ball.y_vel = relative_distance * ball.MAX_VEL


def write_something_sassy():

    idx_of_stera = random.randint(0, len(LIST_OF_STERY_LINES) - 1)
    sassy_text = LIST_OF_STERY_LINES[idx_of_stera][:-1]

    text = SASS_FONT.render(sassy_text, 1, WHITE)
    WIN.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - text.get_height() // 2))

    pygame.display.update()
    pygame.time.delay(4000)


def goal_check(ball, right_paddle, left_paddle, left_score, right_score):

    if ball.x - ball.radius > right_paddle.x + right_paddle.width and ball.x_vel > 0:
        write_something_sassy()
        right_paddle.x = WIDTH - 10 - PADDLE_WIDTH
        right_paddle.y = HEIGHT//2 - PADDLE_HEIGHT//2
        left_paddle.x = 10
        left_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2

        ball.x = WIDTH//2
        ball.y = HEIGHT//2
        ball.y_vel = 0
        ball.x_vel *= -1
        left_score += 1

    elif ball.x + ball.radius < left_paddle.x and ball.x_vel < 0:
        write_something_sassy()
        right_paddle.x = WIDTH - 10 - PADDLE_WIDTH
        right_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2
        left_paddle.x = 10
        left_paddle.y = HEIGHT//2 - PADDLE_HEIGHT//2

        ball.x = WIDTH // 2
        ball.y = HEIGHT // 2
        ball.y_vel = 0
        ball.x_vel *= -1
        right_score += 1

    return left_score, right_score


def main():
    run = True
    clock = pygame.time.Clock()
    left_paddle = Paddle(10, HEIGHT//2 - PADDLE_HEIGHT//2, PADDLE_WIDTH, PADDLE_HEIGHT, WHITE)
    right_paddle = Paddle(WIDTH - 10 - PADDLE_WIDTH, HEIGHT//2 - PADDLE_HEIGHT//2, PADDLE_WIDTH, PADDLE_HEIGHT, WHITE)

    ball = Ball(WIDTH//2, HEIGHT//2, BALL_RADIUS)

    left_score = 0
    right_score = 0

    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

        draw(WIN, [left_paddle, right_paddle], ball, left_score, right_score)
        keys = pygame.key.get_pressed()
        handle_paddle_movement(keys, left_paddle, right_paddle)
        ball.move()
        handle_collision(ball, left_paddle, right_paddle)
        left_score, right_score = goal_check(ball, right_paddle, left_paddle, left_score, right_score)

        won = False
        if left_score >= WINNING_SCORE:
            won = True
            win_text = "Left Player Won!"
        elif right_score >= WINNING_SCORE:
            won = True
            win_text = "Right Player Won!"

        if won:
            text = SCORE_FONT.render(win_text, 1, WHITE)
            WIN.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
            pygame.display.update()
            pygame.time.delay(5000)
            left_score, right_score = 0, 0

    return


if __name__ == '__main__':
    main()


# BUG: ball can get stuck on the bottom edge of the screen, probably top too
# TODO: How to distribute paddle logic so that it can play but the code is not readable
# TODO: How can bots control key presses.
# TODO HW: Sassy text overfloats, break lines and put balck background below
# TODO: Start coding initial bots

"""
Blueprint pro paddle logic, zaroven pristup ke vsem globalnim promennym.

def robot_move_paddle(ball, left_paddle, right_paddle, whoami):
    :param ball: 
    :param left_paddle: 
    :param right_paddle: 
    :param whoami: string "left" or "right"
    :return: move, up
    move - Boolean, if paddle moves
    up - Boolean if paddle moves up
    return 
"""
