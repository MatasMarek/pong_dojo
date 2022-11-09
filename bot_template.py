from config import *


class RobotMovePaddleMara:

    def __init__(self, left, events):
        self.left = left
        self.events = events
        return

    def make_a_move(self, ball, left_paddle, right_paddle, pygame):
        if self.left and ball.x_vel < 0:
            middle_of_paddle = left_paddle.y + PADDLE_HEIGHT//2
            difference_of_middles = middle_of_paddle - ball.y
            if difference_of_middles > 0:
                newevent = self.events['w']
                pygame.event.post(newevent)  # add the event to the queue
            else:
                newevent = self.events['s']
                pygame.event.post(newevent)  # add the event to the queue




