from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math
import random

app = Ursina(title='Sandbox 3D', borderless=False)
window.color = color.rgb(120, 180, 255)

WORLD = 60

touch = {'f': False, 'b': False, 'l': False, 'r': False, 'gas': False, 'brake': False}

Sky()
ground = Entity(
    model='plane', scale=WORLD * 2, collider='box',
    texture='grass', texture_scale=(WORLD, WORLD), color=color.rgb(150, 200, 120)
)


def make_building(x, z):
    h = random.uniform(3, 9)
    return Entity(
        model='cube', position=(x, h / 2, z),
        scale=(random.uniform(3, 6), h, random.uniform(3, 6)),
        texture='brick', color=color.rgb(200, 200, 200), collider='box'
    )


def make_tree(x, z):
    trunk = Entity(model='cube', position=(x, 1, z), scale=(0.4, 2, 0.4),
                   color=color.rgb(90, 60, 30), collider='box')
    Entity(parent=trunk, model='sphere', position=(0, 1.4, 0), scale=2.4,
           color=color.rgb(40, 120, 40))
    return trunk


occupied = [(0, 0)]


def free_spot(r_min=8, r_max=WORLD - 6):
    for _ in range(60):
        x = random.uniform(-r_max, r_max)
        z = random.uniform(-r_max, r_max)
        if abs(x) < r_min and abs(z) < r_min:
            continue
        if all((x - ox) ** 2 + (z - oz) ** 2 > 25 for ox, oz in occupied):
            occupied.append((x, z))
            return x, z
    return random.uniform(-r_max, r_max), random.uniform(-r_max, r_max)


for _ in range(14):
    x, z = free_spot()
    make_building(x, z)
for _ in range(20):
    x, z = free_spot()
    make_tree(x, z)
for _ in range(6):
    x, z = free_spot()
    Entity(model='cube', position=(x, 0.4, z), scale=(1.2, 0.8, 1.2),
           texture='white_cube', color=color.rgb(200, 170, 60), collider='box')

player = FirstPersonController(position=(0, 2, 0), speed=6, jump_height=2.5)
player.cursor.color = color.rgba(255, 255, 255, 100)


class NPC(Entity):
    def __init__(self, position):
        super().__init__(position=position)
        self.body = Entity(parent=self, model='cube', scale=(0.6, 1.1, 0.4),
                           position=(0, 0.75, 0),
                           color=color.rgb(random.randint(80, 255), random.randint(80, 255), random.randint(80, 255)))
        self.head = Entity(parent=self, model='sphere', scale=0.45, position=(0, 1.55, 0),
                           color=color.rgb(240, 200, 160))
        self.speed = random.uniform(1.5, 3)
        self.target = self.new_target()
        self.timer = 0

    def new_target(self):
        return Vec3(random.uniform(-WORLD + 4, WORLD - 4), 0, random.uniform(-WORLD + 4, WORLD - 4))

    def update(self):
        to_target = self.target - self.position
        to_target.y = 0
        self.timer += time.dt
        if to_target.length() < 1 or self.timer > 12:
            self.target = self.new_target()
            self.timer = 0
            return
        direction = to_target.normalized()
        self.position += direction * self.speed * time.dt
        target_angle = math.degrees(math.atan2(direction.x, direction.z))
        self.rotation_y = lerp_angle(self.rotation_y, target_angle, 6 * time.dt)
        self.body.rotation_x = math.sin(time.time() * 8) * 8


for _ in range(10):
    NPC(position=(random.uniform(-30, 30), 0, random.uniform(-30, 30)))


class Car(Entity):
    def __init__(self, position):
        super().__init__(position=position)
        self.body = Entity(parent=self, model='cube', scale=(2, 0.8, 4), position=(0, 0.8, 0),
                           color=color.rgb(200, 30, 30), collider='box')
        self.cabin = Entity(parent=self, model='cube', scale=(1.7, 0.7, 2), position=(0, 1.5, -0.2),
                            color=color.rgb(40, 60, 120))
        self.wheels = []
        for wx in (-0.9, 0.9):
            for wz in (-1.4, 1.4):
                self.wheels.append(Entity(parent=self, model='sphere', scale=(0.25, 0.6, 0.6),
                                          position=(wx, 0.4, wz), color=color.rgb(20, 20, 20)))
        self.speed = 0
        self.driven = False

    def update(self):
        if not self.driven:
            return
        gas = held_keys['w'] or held_keys['up arrow'] or touch['gas']
        brake = held_keys['s'] or held_keys['down arrow'] or touch['brake']
        steer = (held_keys['a'] or held_keys['left arrow'] or touch['l']) - \
                (held_keys['d'] or held_keys['right arrow'] or touch['r'])
        if gas:
            self.speed = lerp(self.speed, 18, 2 * time.dt)
        elif brake:
            self.speed = lerp(self.speed, -8, 2 * time.dt)
        else:
            self.speed = lerp(self.speed, 0, 1.5 * time.dt)

        hit = raycast(self.world_position + Vec3(0, 1, 0), self.forward, distance=3.5,
                      ignore=(self, self.body), debug=False)
        if hit.hit and self.speed > 0:
            self.speed = 0

        self.rotation_y += steer * 90 * time.dt * clamp(abs(self.speed) / 10, 0, 1) * \
            (1 if self.speed >= 0 else -1)
        self.position += self.forward * self.speed * time.dt
        self.position = Vec3(clamp(self.position.x, -WORLD + 2, WORLD - 2), self.position.y,
                             clamp(self.position.z, -WORLD + 2, WORLD - 2))
        for w in self.wheels:
            w.rotation_x += self.speed * time.dt * 60

        target = self.position + self.up * 4.5 - self.forward * 9
        camera.position = lerp(camera.position, target, 6 * time.dt)
        camera.look_at(self.body)
        camera.rotation_z = 0

    def toggle(self):
        if self.driven:
            self.driven = False
            player.enabled = True
            player.cursor.enabled = True
            player.position = self.position + self.right * 3 + Vec3(0, 1, 0)
        elif distance_2d(self.position, player.position) < 6:
            self.driven = True
            player.enabled = False
            player.cursor.enabled = False


car = Car(position=(6, 0, 6))


def update():
    if car.driven:
        return
    if touch['f']:
        player.position += player.forward * player.speed * time.dt
    if touch['b']:
        player.position -= player.forward * player.speed * time.dt
    if touch['l']:
        player.rotation_y -= 90 * time.dt
    if touch['r']:
        player.rotation_y += 90 * time.dt


def input(key):
    if key == 'e':
        car.toggle()


class TouchButton(Button):
    def __init__(self, label, action, toggle=False, **kwargs):
        btn_color = kwargs.pop('color', color.rgba(255, 255, 255, 60))
        super().__init__(text=label, scale=0.14, color=btn_color,
                         highlight_color=color.rgba(255, 255, 255, 120),
                         pressed_color=color.rgba(255, 255, 255, 160), **kwargs)
        self.text_entity.color = color.white
        self.text_entity.scale *= 0.8
        self.action = action
        self.toggle = toggle
        self.was_pressed = False

    def update(self):
        pressed = mouse.hovered_entity is self and mouse.left
        if self.toggle:
            if pressed and not self.was_pressed:
                car.toggle()
        else:
            touch[self.action] = pressed
        self.was_pressed = pressed


pad_y = -0.32
TouchButton('▲', 'f', position=(-0.42, pad_y + 0.16))
TouchButton('▼', 'b', position=(-0.42, pad_y - 0.16))
TouchButton('◀', 'l', position=(-0.60, pad_y))
TouchButton('▶', 'r', position=(-0.24, pad_y))
TouchButton('GAS', 'gas', position=(0.42, pad_y + 0.10), color=color.rgba(80, 200, 80, 70))
TouchButton('BRK', 'brake', position=(0.42, pad_y - 0.18), color=color.rgba(220, 80, 80, 70))
TouchButton('E', 'exit', toggle=True, position=(0.24, pad_y), color=color.rgba(80, 120, 220, 70))

Text('WASD — ходьба, Space — прыжок, E — сесть/выйти из машины. На телефоне — кнопки на экране.',
     position=(-0.85, 0.48), scale=0.7, color=color.black)

app.run()
