from itertools import chain
from typing import Callable

import numpy as np
import pyglet
import random
import imageio.v2 as iio

LIGHT_GRAY = (225, 225, 225)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
RED = (255, 0, 0)
GREEN = (0, 150, 0)
BLUE = (0, 0, 255)
DARK_BLUE = (0, 0, 139)
BROWN = (165, 42, 42)
CYAN = (0, 255, 255)
PINK = (255, 192, 203)
WHITE = (255, 255, 255)

TOUCHING_COLORS = [BLACK, BLUE, GREEN, RED, DARK_BLUE, BROWN, CYAN, BLACK, PINK]
flag = pyglet.resource.image('flag.png')
bomb = pyglet.resource.image('bomb.png')
background = pyglet.graphics.Group(order=0)
foreground = pyglet.graphics.Group(order=1)

correct_tile_fitness = 2
win_bonus = 100
move_penalty = 0
move_interval = 1
move_limit = 20
bomb_penalty = -5
already_revealed_penalty = -2


class GameWindow(pyglet.window.Window):
    def __init__(self, rows, columns, index, net, size, bomb_list, on_game_over: Callable[[int, int], None]):
        super().__init__(width=size, height=size, caption=f"{index}")
        self.columns = columns
        self.tile_size = self.width / self.columns
        self.rows = rows
        self.game_over = False
        self.game_started = False
        self.bomb_list = bomb_list
        self.on_game_over = on_game_over
        self.fitness = 0
        self.index = index
        self.net = net
        self.tiles = []
        self.mouse_x = 0
        self.mouse_y = 0
        self.batch = pyglet.graphics.Batch()
        self.moves = 0
        self.writer = iio.get_writer("recording.mp4")

        self.create_grid()
        self.add_bombs()
        self.click_random()
        self.game_started = True

        pyglet.clock.schedule_interval(self.activate_net, move_interval)

    def click_random(self):
        for x, rows in enumerate(self.tiles):
            for y, tile in enumerate(rows):
                if tile.touching == 0:
                    self.reveal_from(x, y)
                    return

    def get_net_output(self):
        tiles_flat = list(chain.from_iterable(self.tiles))
        representations = list(map(lambda t: t.get_visible_representation(), tiles_flat))
        output = self.net.activate(representations)
        return output

    def activate_net(self, _):
        self.moves += 1
        self.fitness += move_penalty
        if self.moves > move_limit:
            self.game_over = True
            self.on_game_over(self.fitness, self.index)
            # self.close()
        if self.game_started:
            output = self.get_net_output()
            reshaped_output = [output[i:i+self.columns] for i in range(0, len(output), self.columns)]
            max_output = reshaped_output[0][0]
            max_x = 0
            max_y = 0
            for x, rows in enumerate(reshaped_output):
                for y, out in enumerate(rows):
                    if out > max_output:
                        max_output = out
                        max_x = x
                        max_y = y

            tile = self.tiles[max_x][max_y]
            self.handle_tile_click(tile, max_x, max_y)

    def create_grid(self):
        for rows in range(self.rows):
            row = []
            for col in range(self.columns):
                row.append(Tile())
            self.tiles.append(row)

    def add_bombs(self):
        for b in self.bomb_list:
            self.tiles[b[0]][b[1]].set_bomb()
        self.update_touching()

    def update_touching(self):
        for x, rows in enumerate(self.tiles):
            for y, tile in enumerate(rows):
                tile.update_touching(x, y, self.tiles, self.rows, self.columns)

    def draw_grid(self):
        rects = []
        for x, rows in enumerate(self.tiles):
            for y, tile in enumerate(rows):
                rects.append(tile.draw_tile(self.batch, x, y, self.width / self.columns, 4))

        self.batch.draw()

    def on_draw(self):
        self.clear()

        self.draw_grid()
        self.record_screen()

    def record_screen(self):
        # Capture frame
        color_buffer = pyglet.image.get_buffer_manager().get_color_buffer()
        image_data = color_buffer.get_image_data()
        buffer = image_data.get_data("RGBA", image_data.pitch)

        # 4 channels: RGBA
        frame = np.asarray(buffer).reshape((image_data.height, image_data.width, 4))
        # Make image correctly oriented
        frame = np.flipud(frame)
        self.writer.append_data(frame)

    def reveal_all(self):
        for x, rows in enumerate(self.tiles):
            for y, tile in enumerate(rows):
                tile.reveal()
        self.game_over = True
        self.on_game_over(self.fitness, self.index)
        # self.close()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        self.mouse_x = x
        self.mouse_y = y

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        tile = self.get_tile(x, y)
        tile_x = int(x / self.tile_size)
        tile_y = int(y / self.tile_size)
        self.handle_tile_click(tile, tile_x, tile_y)

    def handle_tile_click(self, tile, x, y):
        if tile.touching == 0:
            self.reveal_from(x, y)
        if not self.game_over:
            fitness_change = tile.click(self.reveal_all)
            self.fitness += fitness_change

            self.check_game_win()

    def on_key_release(self, symbol: int, modifiers: int):
        if symbol == pyglet.window.key.SPACE:
            tile = self.get_tile(self.mouse_x, self.mouse_y)
            tile.flag()
        if symbol == pyglet.window.key.A:
            self.activate_net(None)

    def reveal_from(self, x, y):
        for temp_x in range(-1, 2):
            for temp_y in range(-1, 2):
                final_x = x + temp_x
                final_y = y + temp_y
                if final_x < 0 or final_x >= self.rows:
                    continue
                if final_y < 0 or final_y >= self.columns:
                    continue
                if final_y == y and final_x == x:
                    continue
                tile_to_reveal = self.tiles[final_x][final_y]
                if not tile_to_reveal.is_revealed:
                    fitness_change = tile_to_reveal.click(lambda *args: None)
                    if self.game_started:
                        self.fitness += fitness_change
                    if tile_to_reveal.touching == 0:
                        self.reveal_from(final_x, final_y)

    def check_game_win(self):
        if self.game_over:
            return
        count = 0
        for x, rows in enumerate(self.tiles):
            for y, tile in enumerate(rows):
                if tile.is_revealed and not tile.is_bomb:
                    count += 1

        if count == self.columns * self.rows - len(self.bomb_list):
            print("winner winner chicken dinner")
            self.game_over = True
            self.fitness += win_bonus
            self.on_game_over(self.fitness, self.index)
            # self.close()

    def get_tile(self, x, y):
        tile_x = int(x / self.tile_size)
        tile_y = int(y / self.tile_size)
        return self.tiles[tile_x][tile_y]

    @staticmethod
    def check_bombs(i, list_):
        if i in list_:
            return True
        return False

    @staticmethod
    def get_random_bomb_list(rows, columns, num_bombs):
        bombs_list = []
        for _ in range(num_bombs):
            x = random.randint(0, rows - 1)
            y = random.randint(0, columns - 1)
            while GameWindow.check_bombs([x, y], bombs_list):
                x = random.randint(0, rows - 1)
                y = random.randint(0, columns - 1)
            bombs_list.append([x, y])
        return bombs_list


class Tile:
    def __init__(self):
        self.is_bomb = False
        self.touching = 0
        self.is_revealed = False
        self.is_flagged = False

    def click(self, reveal_all):
        if not self.is_revealed:
            if self.is_flagged:
                return 0
            self.is_revealed = True
            if self.is_bomb:
                reveal_all()
                return bomb_penalty
            else:
                return correct_tile_fitness
        else:
            return already_revealed_penalty

    def get_visible_representation(self):
        if self.is_revealed:
            return self.touching
        else:
            return -1

    def flag(self):
        if not self.is_revealed:
            self.is_flagged = not self.is_flagged

    def reveal(self):
        self.is_revealed = True

    def set_bomb(self):
        self.is_bomb = True

    def update_touching(self, x, y, tiles, rows, columns):
        if not self.is_bomb:
            count = 0
            for temp_x in range(-1, 2):
                for temp_y in range(-1, 2):
                    final_x = x + temp_x
                    final_y = y + temp_y
                    if final_x < 0 or final_x >= rows:
                        continue
                    if final_y < 0 or final_y >= columns:
                        continue
                    if final_y == y and final_x == x:
                        continue
                    if tiles[final_x][final_y].is_bomb:
                        count += 1
            self.touching = count
        else:
            self.touching = -1

    def draw_tile(self, batch, x, y, size, offset):
        objects = []
        translated_x = x * size + offset
        translated_y = y * size + offset
        translated_size = size - offset * 2
        color = GRAY
        if self.is_flagged:
            sprite = pyglet.sprite.Sprite(flag, translated_x, translated_y, batch=batch, group=foreground)
            sprite.width = translated_size
            sprite.height = translated_size
            objects.append(sprite)
        elif self.is_revealed and self.is_bomb:
            sprite = pyglet.sprite.Sprite(bomb, translated_x, translated_y, batch=batch, group=foreground)
            sprite.width = translated_size
            sprite.height = translated_size
            color = RED
            objects.append(sprite)
        elif self.is_revealed and self.touching != 0:
            label = pyglet.text.Label(f"{self.touching}", translated_x, translated_y, translated_size, translated_size,
                                      align='center', font_size=translated_size / 2, batch=batch, group=foreground,
                                      color=TOUCHING_COLORS[self.touching])
            color = LIGHT_GRAY
            objects.append(label)
        elif self.is_revealed:
            color = LIGHT_GRAY

        objects.append(
            pyglet.shapes.Rectangle(translated_x, translated_y, translated_size, translated_size,
                                    color=color, batch=batch, group=background))

        return objects
