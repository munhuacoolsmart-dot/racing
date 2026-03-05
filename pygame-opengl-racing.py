import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math, random

# ----------------------------
# Initialize
# ----------------------------
pygame.init()
display = (1200,700)
screen = pygame.display.set_mode(display, DOUBLEBUF|OPENGL)
pygame.display.set_caption("AAA Mini 3D Racing Game - Cybertruck Edition")

clock = pygame.time.Clock()

glEnable(GL_DEPTH_TEST)
glEnable(GL_TEXTURE_2D)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

# ----------------------------
# OBJ MODEL LOADER
# ----------------------------
class OBJ:
    def __init__(self, filename):
        self.vertices = []
        self.faces = []

        for line in open(filename,"r"):
            if line.startswith('#'):
                continue

            values = line.split()
            if not values:
                continue

            if values[0] == 'v':
                v = list(map(float, values[1:4]))
                self.vertices.append(v)

            if values[0] == 'f':
                face = []
                for v in values[1:]:
                    w = v.split('/')
                    face.append(int(w[0]) - 1)
                self.faces.append(face)

    def render(self):
        glBegin(GL_TRIANGLES)
        for face in self.faces:
            for vertex in face:
                glVertex3fv(self.vertices[vertex])
        glEnd()

# ----------------------------
# Load Cybertruck
# ----------------------------
cybertruck = OBJ("cybertruck.obj")

# ----------------------------
# Load textures
# ----------------------------
def load_texture(path):

    surf = pygame.image.load(path)
    texData = pygame.image.tostring(surf,"RGB",1)

    w = surf.get_width()
    h = surf.get_height()

    texID = glGenTextures(1)

    glBindTexture(GL_TEXTURE_2D, texID)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,w,h,0,GL_RGB,GL_UNSIGNED_BYTE,texData)

    return texID


track_texture = load_texture("track.jpg")
grass_texture = load_texture("grass.jpg")

# ----------------------------
# Cars
# ----------------------------
car={"x":0,"z":0,"angle":0,"speed":0,"color":(0.8,0.8,0.8)}

ai_cars=[]
for i in range(4):
    ai_cars.append({
        "angle":random.randint(0,360),
        "radius":20+random.randint(-3,3),
        "speed":random.uniform(0.5,1.0),
        "color":(1,0,0)
    })

# ----------------------------
# Track
# ----------------------------
tracks=[{"radius":20+i*2,"width":6+i%3} for i in range(10)]
current_track=0

# ----------------------------
# Puddles
# ----------------------------
puddles=[{
    "x":random.uniform(-20,20),
    "z":random.uniform(-20,20),
    "radius":random.uniform(2,4)
} for _ in range(10)]

# ----------------------------
# Rain
# ----------------------------
raining=True

rain_particles=[
{
"x":random.uniform(-50,50),
"y":random.uniform(5,50),
"z":random.uniform(-50,50)
} for _ in range(500)
]

# ----------------------------
# Fog
# ----------------------------
glEnable(GL_FOG)
glFogfv(GL_FOG_COLOR,[0.5,0.5,0.6,1])
glFogf(GL_FOG_DENSITY,0.02)
glFogi(GL_FOG_MODE,GL_EXP2)

# ----------------------------
# Draw Cybertruck
# ----------------------------
def draw_car(x,z,angle,color=(1,1,1)):

    glPushMatrix()

    glTranslatef(x,0,z)

    glRotatef(angle,0,1,0)

    glScalef(0.5,0.5,0.5)

    glColor3f(*color)

    cybertruck.render()

    glPopMatrix()


# ----------------------------
# Draw Track
# ----------------------------
def draw_track(track):

    radius=track["radius"]
    width=track["width"]

    glBindTexture(GL_TEXTURE_2D,track_texture)

    glBegin(GL_QUAD_STRIP)

    for i in range(101):

        angle=2*math.pi*i/100

        x_outer=(radius+width)*math.cos(angle)
        z_outer=(radius+width)*math.sin(angle)

        x_inner=(radius-width)*math.cos(angle)
        z_inner=(radius-width)*math.sin(angle)

        glTexCoord2f(0,0)
        glVertex3f(x_outer,-0.1,z_outer)

        glTexCoord2f(1,1)
        glVertex3f(x_inner,-0.1,z_inner)

    glEnd()


# ----------------------------
# Grass
# ----------------------------
def draw_grass():

    glBindTexture(GL_TEXTURE_2D,grass_texture)

    glBegin(GL_QUADS)

    glTexCoord2f(0,0)
    glVertex3f(-50,-0.2,-50)

    glTexCoord2f(1,0)
    glVertex3f(50,-0.2,-50)

    glTexCoord2f(1,1)
    glVertex3f(50,-0.2,50)

    glTexCoord2f(0,1)
    glVertex3f(-50,-0.2,50)

    glEnd()


# ----------------------------
# Rain
# ----------------------------
def draw_rain():

    glColor3f(0.6,0.6,1)

    glBegin(GL_LINES)

    for drop in rain_particles:

        glVertex3f(drop["x"],drop["y"],drop["z"])
        glVertex3f(drop["x"],drop["y"]-0.5,drop["z"])

    glEnd()


def update_rain():

    for drop in rain_particles:

        drop["y"]-=0.5

        if drop["y"]<0:

            drop["y"]=random.uniform(10,50)
            drop["x"]=random.uniform(-50,50)
            drop["z"]=random.uniform(-50,50)


# ----------------------------
# Puddles
# ----------------------------
def draw_puddles(time):

    glColor4f(0.3,0.4,0.5,0.6)

    for puddle in puddles:

        x=puddle["x"]
        z=puddle["z"]
        r=puddle["radius"]

        glPushMatrix()

        glTranslatef(x,0.01,z)

        glBegin(GL_TRIANGLE_FAN)

        glVertex3f(0,0,0)

        for i in range(21):

            angle=2*math.pi*i/20
            ripple=0.1*math.sin(time*5+i)

            glVertex3f(
                (r+ripple)*math.cos(angle),
                0,
                (r+ripple)*math.sin(angle)
            )

        glEnd()

        glPopMatrix()


# ----------------------------
# Camera
# ----------------------------
def set_camera():

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    cam_x = car["x"]-8*math.sin(math.radians(car["angle"]))
    cam_y = 5
    cam_z = car["z"]-8*math.cos(math.radians(car["angle"]))

    gluLookAt(cam_x,cam_y,cam_z,
              car["x"],0,car["z"],
              0,1,0)


# ----------------------------
# Projection
# ----------------------------
glMatrixMode(GL_PROJECTION)
gluPerspective(60,(display[0]/display[1]),0.1,100.0)
glMatrixMode(GL_MODELVIEW)

# ----------------------------
# Main loop
# ----------------------------
running=True

while running:

    clock.tick(60)

    t=pygame.time.get_ticks()/1000.0

    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            running=False

    keys=pygame.key.get_pressed()

    if keys[K_LEFT]:
        car["angle"]+=2

    if keys[K_RIGHT]:
        car["angle"]-=2

    if keys[K_UP]:
        car["speed"]+=0.05

    if keys[K_DOWN]:
        car["speed"]-=0.05

    car["speed"]*=0.97

    car["x"]+=math.sin(math.radians(car["angle"]))*car["speed"]
    car["z"]+=math.cos(math.radians(car["angle"]))*car["speed"]

    ai_positions=[]

    for ai in ai_cars:

        ai["angle"]+=ai["speed"]

        x=ai["radius"]*math.cos(math.radians(ai["angle"]))
        z=ai["radius"]*math.sin(math.radians(ai["angle"]))

        ai_positions.append((x,z))

    update_rain()

    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

    set_camera()

    draw_grass()
    draw_track(tracks[current_track])

    draw_car(car["x"],car["z"],car["angle"],car["color"])

    for pos,ai_car in zip(ai_positions,ai_cars):

        draw_car(pos[0],pos[1],ai_car["angle"],ai_car["color"])

    if raining:

        draw_rain()
        draw_puddles(t)

    pygame.display.flip()

pygame.quit()