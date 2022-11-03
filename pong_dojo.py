import pygame
pygame.init()

WIDTH, HEIGHT = 700, 500
WIN = pygame.display.set_mode((WIDTH, HEIGHT))

PADDLE_WIDTH, PADDLE_HEIGHT = 20, 100
BALL_RADIUS = 7
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


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


def draw(win, paddles, ball):
    win.fill(BLACK)
    for paddle in paddles:
        paddle.draw(win)
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


def ball_check(ball, right_paddle, left_paddle):

    if ball.x - ball.radius > right_paddle.x + right_paddle.width and ball.x_vel > 0:
        right_paddle.x = WIDTH - 10 - PADDLE_WIDTH
        right_paddle.y = HEIGHT//2 - PADDLE_HEIGHT//2
        left_paddle.x = 10
        left_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2

        ball.x = WIDTH//2
        ball.y = HEIGHT//2
        ball.y_vel = 0
        ball.x_vel *= -1


    elif ball.x + ball.radius < left_paddle.x and ball.x_vel < 0:
        right_paddle.x = WIDTH - 10 - PADDLE_WIDTH
        right_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2
        left_paddle.x = 10
        left_paddle.y = HEIGHT//2 - PADDLE_HEIGHT//2

        ball.x = WIDTH // 2
        ball.y = HEIGHT // 2
        ball.y_vel = 0
        ball.x_vel *= -1


def main():
    run = True
    clock = pygame.time.Clock()
    left_paddle = Paddle(10, HEIGHT//2 - PADDLE_HEIGHT//2, PADDLE_WIDTH, PADDLE_HEIGHT, WHITE)
    right_paddle = Paddle(WIDTH - 10 - PADDLE_WIDTH, HEIGHT//2 - PADDLE_HEIGHT//2, PADDLE_WIDTH, PADDLE_HEIGHT, WHITE)

    ball = Ball(WIDTH//2, HEIGHT//2, BALL_RADIUS)

    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

        draw(WIN, [left_paddle, right_paddle], ball)
        keys = pygame.key.get_pressed()
        handle_paddle_movement(keys, left_paddle, right_paddle)
        ball.move()
        handle_collision(ball, left_paddle, right_paddle)
        ball_check(ball, right_paddle, left_paddle)

    return


if __name__ == '__main__':
    main()


# BUG: ball can get stuck on the bottom edge of the screen, probably top too
