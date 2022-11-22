import pygame
from config import *
from paddle_logic import RobotMovePaddleMara
import pygame.locals
from text_handling import write_something_sassy, text_box
pygame.init()

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
SCORE_FONT = pygame.font.SysFont("comicsans", 50)
SASS_FONT = pygame.font.SysFont("comicsans", 20)

stery_file = open('stery.txt', "r", encoding="utf-8")
LIST_OF_STERY_LINES = stery_file.readlines()


class Paddle:
    VEL = 2

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
    AIR_DRAG = 2
    no_of_updates = WIDTH//MAX_VEL

    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.x_vel = self.MAX_VEL
        self.y_vel = 0
        self.y_vel_from_rotation = 0.
        self.rotation = 0  # Every hit can increase by one

    def move(self):
        self.x += self.x_vel
        self.y += self.y_vel
        if self.rotation != 0:
            sign_of_rotation = self.rotation/abs(self.rotation)
            self.y_vel_from_rotation += float(self.AIR_DRAG*self.rotation)/self.no_of_updates * self.x_vel/abs(self.x_vel)
            sign_of_y_vel_from_rotation = self.y_vel_from_rotation/abs(self.y_vel_from_rotation)
            if abs(self.y_vel_from_rotation) > 1.:
                self.y_vel += 1 * int(sign_of_y_vel_from_rotation)
                self.y_vel_from_rotation += -sign_of_y_vel_from_rotation
                # print(self.y_vel_from_rotation, -sign_of_rotation)


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


def handle_paddle_movement(current_events, left_paddle, right_paddle, events):
    for event in current_events:
        if event == events['w']:
            left_paddle.move(up=True)
        if event == events['s']:
            left_paddle.move(up=False)

        if event == events['up']:
            right_paddle.move(up=True)
        if event == events['down']:
            right_paddle.move(up=False)

def ball_has_collided_with_paddle(ball, current_events, events):
    for event in current_events:
        if ball.x_vel < 0:
            if event == events['w']:
                ball.rotation += 1
            if event == events['s']:
                ball.rotation -= 1
        else:
            if event == events['up']:
                ball.rotation -= 1
            if event == events['down']:
                ball.rotation += 1
    ball.x_vel *= -1

def handle_collision(ball, left_paddle, right_paddle, current_events, events):
    if ball.y - ball.radius <= 0:
        ball.y_vel *= -1
    elif ball.y + ball.radius >= HEIGHT:
        ball.y_vel *= -1

    if ball.x_vel < 0:
        if ball.y >= left_paddle.y and ball.y <= left_paddle.y + left_paddle.height:
            if ball.x - ball.radius + ball.x_vel <= left_paddle.x + left_paddle.width <= ball.x - ball.radius:
                ball_has_collided_with_paddle(ball, current_events, events)
                middle_y = left_paddle.y + left_paddle.height/2
                difference_in_y = ball.y - middle_y
                relative_distance = difference_in_y / (left_paddle.height/2)
                ball.y_vel = relative_distance * ball.MAX_VEL

    else:
        if ball.y >= right_paddle.y and ball.y <= right_paddle.y + right_paddle.height:
            if ball.x + ball.radius + ball.x_vel >= right_paddle.x >= ball.x + ball.radius:
                ball_has_collided_with_paddle(ball, current_events, events)
                middle_y = right_paddle.y + right_paddle.height/2
                difference_in_y = ball.y - middle_y
                relative_distance = difference_in_y / (right_paddle.height/2)
                ball.y_vel = relative_distance * ball.MAX_VEL


def goal_check(ball, right_paddle, left_paddle, left_score, right_score):

    if ball.x - ball.radius > right_paddle.x + right_paddle.width and ball.x_vel > 0:
        write_something_sassy(pygame, LIST_OF_STERY_LINES, SASS_FONT, WIN)
        right_paddle.x = WIDTH - 10 - PADDLE_WIDTH
        right_paddle.y = HEIGHT//2 - PADDLE_HEIGHT//2
        left_paddle.x = 10
        left_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2

        ball.x = WIDTH//2
        ball.y = HEIGHT//2
        ball.y_vel = 0
        left_score += 1
        ball.rotation = 0

    elif ball.x + ball.radius < left_paddle.x and ball.x_vel < 0:
        write_something_sassy(pygame, LIST_OF_STERY_LINES, SASS_FONT, WIN)
        right_paddle.x = WIDTH - 10 - PADDLE_WIDTH
        right_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2
        left_paddle.x = 10
        left_paddle.y = HEIGHT//2 - PADDLE_HEIGHT//2

        ball.x = WIDTH // 2
        ball.y = HEIGHT // 2
        ball.y_vel = 0
        right_score += 1
        ball.rotation = 0

    return left_score, right_score


def main():
    run = True
    clock = pygame.time.Clock()
    left_paddle = Paddle(10, HEIGHT//2 - PADDLE_HEIGHT//2, PADDLE_WIDTH, PADDLE_HEIGHT, WHITE)
    right_paddle = Paddle(WIDTH - 10 - PADDLE_WIDTH, HEIGHT//2 - PADDLE_HEIGHT//2, PADDLE_WIDTH, PADDLE_HEIGHT, WHITE)

    event_w = pygame.event.Event(pygame.locals.KEYDOWN, unicode="w", key=pygame.locals.K_w,mod=pygame.locals.KMOD_NONE)
    event_s = pygame.event.Event(pygame.locals.KEYDOWN, unicode="s", key=pygame.locals.K_s,mod=pygame.locals.KMOD_NONE)
    event_up = pygame.event.Event(pygame.locals.KEYDOWN, unicode="up", key=pygame.locals.K_UP,mod=pygame.locals.KMOD_NONE)
    event_down = pygame.event.Event(pygame.locals.KEYDOWN, unicode="down", key=pygame.locals.K_DOWN,mod=pygame.locals.KMOD_NONE)

    events = {
        's': event_s,
        'w': event_w,
        'up': event_up,
        'down': event_down,
    }

    ball = Ball(WIDTH//2, HEIGHT//2, BALL_RADIUS)
    mara_logic = RobotMovePaddleMara(left=True, events=events)

    left_score = 0
    right_score = 0

    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

        draw(WIN, [left_paddle, right_paddle], ball, left_score, right_score)

        # Move with Robots
        mara_logic.make_a_move(ball, left_paddle, right_paddle, pygame)


        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            newevent = events['w']
            pygame.event.post(newevent)
        if keys[pygame.K_s]:
            newevent = events['s']
            pygame.event.post(newevent)
        if keys[pygame.K_UP]:
            newevent = events['up']
            pygame.event.post(newevent)
        if keys[pygame.K_DOWN]:
            newevent = events['down']
            pygame.event.post(newevent)

        current_events = pygame.event.get()
        handle_paddle_movement(current_events, left_paddle, right_paddle, events)
        ball.move()
        handle_collision(ball, left_paddle, right_paddle, current_events, events)
        left_score, right_score = goal_check(ball, right_paddle, left_paddle, left_score, right_score)

        won = False
        if left_score >= WINNING_SCORE:
            won = True
            win_text = "Left Player Won!"
        elif right_score >= WINNING_SCORE:
            won = True
            win_text = "Right Player Won!"

        if won:
            WIN.fill(BLACK)
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

