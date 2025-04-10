import pygame as pg
import numpy as np
import os
import time
import sys
from numba import njit, prange

WIN_RES = (800, 600)
WIDTH = WIN_RES[0]
HEIGHT = WIN_RES[1]
HALF_WIDTH = WIDTH // 2
HALF_HEIGHT = HEIGHT // 2
FOCAL_LEN = 250
SPEED = 0.008
SCALE = 100 

# 车头方向图片映射
vehicle_images = {
    (1,): pg.image.load("Mariocart/textures/Mario1.png"),  # 单独按下 W
    (2,): pg.image.load("Mariocart/textures/Mario7.png"),  # 单独按下 A
    (3,): pg.image.load("Mariocart/textures/Mario4.png"),  # 单独按下 S
    (4,): pg.image.load("Mariocart/textures/Mario8.png"),  # 单独按下 D
    (pg.K_RIGHT,): pg.image.load("Mariocart/textures/Mario3.png"),  # 按下右
    (pg.K_LEFT,): pg.image.load("Mariocart/textures/Mario2.png"),  # 同时左
    ('W', 'D'): pg.image.load("Mariocart/textures/Mario3.png"),  # 同时按下 W 和 D
    ('W', 'A'): pg.image.load("Mariocart/textures/Mario2.png"),  # 同时按下 W 和 A

    ('W', 'A',pg.K_LEFT,): pg.image.load("Mariocart/textures/Mario2.png"),  # 同时按下 W 和 A
    ('W', 'D',pg.K_RIGHT,): pg.image.load("Mariocart/textures/Mario3.png"),  # 同时按下 W 和 D
    ('W', pg.K_LEFT,): pg.image.load("Mariocart/textures/Mario2.png"),  # 同时按下 W 和 A
    ('W', pg.K_RIGHT,): pg.image.load("Mariocart/textures/Mario3.png"),  # 同时按下 W 和 D
    
    # ('S', 'D'): pg.image.load("Mariocart/textures/Mario6.png"),  # 同时按下 S 和 D
    # ('S', 'A'): pg.image.load("Mariocart/textures/Mario5.png"),  # 同时按下 S 和 A
    ('A',): pg.image.load("Mariocart/textures/Mario7.png"),  # 单独按下 A
    ('D',): pg.image.load("Mariocart/textures/Mario8.png"),  # 单独按下 D
}

class Mode7:
    def __init__(self, app):
        self.app = app
        
        self.start_ticks = pg.time.get_ticks()  # 記錄開始的時間（毫秒）
        self.font = pg.font.SysFont('Arial', 30)  # 設定字型與大小

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        
        self.floor_tex = pg.image.load(os.path.join(BASE_DIR, 'textures', 'floor_2.png')).convert()
        self.tex_size = self.floor_tex.get_size()
        self.floor_array = pg.surfarray.array3d(self.floor_tex)

        self.ceil_tex = pg.image.load(os.path.join(BASE_DIR, 'textures', 'ceil_2.png')).convert()
        self.ceil_tex = pg.transform.scale(self.ceil_tex, self.tex_size)
        self.ceil_array = pg.surfarray.array3d(self.ceil_tex)

        self.screen_array = pg.surfarray.array3d(pg.Surface(WIN_RES))

        self.alt = 0.  # 初始高度設為更低
        self.angle = 0.0
        self.pos = np.array([4.48614806, -1.48735932])  # 假設起點線在 floor_2.png 的中間

        # 车头方向初始化
        self.current_direction = (1,)  # 默认车头方向是 (1,) 即 Mario1.png
    
    def draw_timer(self):
    # 計算經過的秒數
        seconds = (pg.time.get_ticks() - self.start_ticks) // 1000
        timer_surface = self.font.render(f"Time: {seconds}s", True, (255, 255, 255))  # 白色文字
        self.app.screen.blit(timer_surface, (WIDTH - 150, 10))  # 顯示在右上角

    def update(self):
        self.movement()
        self.screen_array = self.render_frame(self.floor_array, self.ceil_array, self.screen_array,
                                              self.tex_size, self.angle, self.pos, self.alt)
        self.handle_input()  # 监听键盘输入

    def draw(self):
        pg.surfarray.blit_array(self.app.screen, self.screen_array)
        self.draw_vehicle()  # 绘制车头
        self.display_vehicle_color()  # 在畫面底部繪製車輛
        self.draw_timer()  # 顯示計時器

    def draw_vehicle(self):
        vehicle_width = 90
        vehicle_height = 90
        vehicle_x = HALF_WIDTH - vehicle_width // 2
        vehicle_y = HEIGHT - vehicle_height - 10  # 稍微抬高

        # 获取当前方向的图片
        current_image = self.get_direction_image()
        current_image = pg.transform.scale(current_image, (vehicle_width, vehicle_height))  # 调整图片大小

        # 将图片绘制到屏幕上
        self.app.screen.blit(current_image, (vehicle_x, vehicle_y))

    def get_direction_image(self):
        # 获取当前按下的键
        keys = pg.key.get_pressed()
        pressed_keys = []

        if keys[pg.K_w]:
            pressed_keys.append('W')
        if keys[pg.K_a]:
            pressed_keys.append('A')
        if keys[pg.K_s]:
            pressed_keys.append('S')
        if keys[pg.K_d]:
            pressed_keys.append('D')
        if keys[pg.K_LEFT]:
            pressed_keys.append(pg.K_LEFT)
        if keys[pg.K_RIGHT]:
            pressed_keys.append(pg.K_RIGHT)


        # 将按下的键组合成元组
        pressed_keys = tuple(pressed_keys)

        # 返回对应的图片，若没有匹配则默认返回 Mario1.png
        return vehicle_images.get(pressed_keys, vehicle_images[(1,)])

    def handle_input(self):
        # 监听按键输入，更新方向（已经由 get_direction_image 处理）
        pass
            

    def get_vehicle_color(self):
        # 檢測車輛正下方的地板顏色（假設車輛中心對應玩家位置）
        floor_x = int(self.pos[1] * SCALE % self.tex_size[0])  # self.pos[1] 是 x
        floor_y = int(self.pos[0] * SCALE % self.tex_size[1])  # self.pos[0] 是 y
        color = self.floor_array[floor_x, floor_y]  # RGB 值
        return color

    def display_vehicle_color(self):
        # 在螢幕上顯示車輛下方的顏色
        color = self.get_vehicle_color()
        font = pg.font.SysFont(None, 30)
        text = font.render(f"Color under vehicle: {color}", True, (255, 255, 255))
        self.app.screen.blit(text, (10, 10))

    @staticmethod
    @njit(fastmath=True, parallel=True)
    def render_frame(floor_array, ceil_array, screen_array, tex_size, angle, player_pos, alt):
        # 原有的 render_frame 函數保持不變
        sin, cos = np.sin(angle), np.cos(angle)
        for i in prange(WIDTH):
            new_alt = alt
            for j in range(HALF_HEIGHT, HEIGHT):
                x = HALF_WIDTH - i
                y = j + FOCAL_LEN
                z = j - HALF_HEIGHT + new_alt

                px = (x * cos - y * sin)
                py = (x * sin + y * cos)

                floor_x = px / z - player_pos[1]
                floor_y = py / z + player_pos[0]

                floor_pos = int(floor_x * SCALE % tex_size[0]), int(floor_y * SCALE % tex_size[1])
                floor_col = floor_array[floor_pos]

                ceil_x = alt * px / z - player_pos[1] * 0.3
                ceil_y = alt * py / z + player_pos[0] * 0.3

                ceil_pos = int(ceil_x * SCALE % tex_size[0]), int(ceil_y * SCALE % tex_size[1])
                ceil_col = ceil_array[ceil_pos]

                depth = min(max(2.5 * (abs(z) / HALF_HEIGHT), 0), 1)
                fog = (1 - depth) * 230

                floor_col = (floor_col[0] * depth + fog,
                             floor_col[1] * depth + fog,
                             floor_col[2] * depth + fog)

                ceil_col = (ceil_col[0] * depth + fog,
                            ceil_col[1] * depth + fog,
                            ceil_col[2] * depth + fog)

                screen_array[i, j] = floor_col
                screen_array[i, -j] = ceil_col

                new_alt += alt

        return screen_array

    def movement(self):
        sin_a = np.sin(self.angle)
        cos_a = np.cos(self.angle)
        dx, dy = 0, 0
        speed_sin = SPEED * sin_a
        speed_cos = SPEED * cos_a

        keys = pg.key.get_pressed()
        if keys[pg.K_w]:
            dx += speed_cos
            dy += speed_sin
        if keys[pg.K_s]:
            dx += -speed_cos
            dy += -speed_sin
        if keys[pg.K_a]:
            dx += speed_sin
            dy += -speed_cos
        if keys[pg.K_d]:
            dx += -speed_sin
            dy += speed_cos
        self.pos[0] += dx
        self.pos[1] += dy

        if keys[pg.K_LEFT]:
            self.angle -= SPEED
        if keys[pg.K_RIGHT]:
            self.angle += SPEED

        if keys[pg.K_q]:
            self.alt += SPEED
        if keys[pg.K_e]:
            self.alt -= SPEED
        self.alt = min(max(self.alt, 0.3), 4)  # 調整最小高度