import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math, random, time

# --- INITIALIZATION ---
pygame.init()
display = (1200, 700)
pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
pygame.display.set_caption("Cybertruck Pro: Grand Prix Edition")
clock = pygame.time.Clock()

# --- OBJ LOADER ---
class OBJ:
    def __init__(self, filename):
        self.vertices = []
        self.faces = []
        try:
            with open(filename, "r") as f:
                for line in f:
                    if line.startswith('v '):
                        self.vertices.append(list(map(float, line.split()[1:4])))
                    elif line.startswith('f '):
                        face = [int(v.split('/')[0]) - 1 for v in line.split()[1:]]
                        self.faces.append(face)
            self.gl_list = glGenLists(1)
            glNewList(self.gl_list, GL_COMPILE)
            glBegin(GL_TRIANGLES)
            for face in self.faces:
                for vertex in face:
                    glVertex3fv(self.vertices[vertex])
            glEnd(); glEndList()
        except: print("OBJ Load Error")

    def render(self, color):
        glColor3f(*color); glCallList(self.gl_list)

# --- TEXTURE LOADER ---
def load_texture(path):
    try:
        surf = pygame.image.load(path)
        data = pygame.image.tostring(surf, "RGBA", 1)
        w, h = surf.get_size()
        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glGenerateMipmap(GL_TEXTURE_2D); return texid
    except: return None

# --- WORLD & HUD ---
def draw_hud(car, laps, finished):
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, display[0], 0, display[1])
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
    
    if not finished:
        # Turbo Bar
        glColor3f(0.1, 0.1, 0.1); glRectf(50, 50, 300, 70)
        glColor3f(0, 0.8, 1) if car["turbo"] > 20 else glColor3f(1, 0, 0)
        glRectf(50, 50, 50 + (car["turbo"] * 2.5), 70)
        # Lap Squares
        for i in range(laps):
            glColor3f(0, 1, 0); glRectf(50 + (i*35), 85, 80 + (i*35), 105)
    else:
        # End Screen Overlay
        glColor4f(0, 0, 0, 0.7); glRectf(0, 0, display[0], display[1])
        # Win/Loss Marker (Large Square)
        glColor3f(1, 1, 1); glRectf(display[0]//2 - 100, display[1]//2 - 20, display[0]//2 + 100, display[1]//2 + 20)
        
    glEnable(GL_DEPTH_TEST); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix()

# --- MAIN SETUP ---
truck_model = OBJ("cybertruck.obj")
grass_tex, sky_tex = load_texture("grass.jpg"), load_texture("sky.jpg")

def reset_game():
    return {
        "car": {"x": 55, "z": -5, "angle": 0, "speed": 0, "turbo": 100.0, "prev_z": -5},
        "ai": {"angle": 5, "radius": 52, "speed": 0.88, "laps": 0, "prev_z": -5},
        "laps": 0,
        "start_time": time.time(),
        "finished": False
    }

game = reset_game()
glEnable(GL_DEPTH_TEST); glEnable(GL_FOG); glFogi(GL_FOG_MODE, GL_EXP2)
glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_COLOR_MATERIAL); glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

running = True
while running:
    for event in pygame.event.get():
        if event.type == QUIT: running = False
        if event.type == KEYDOWN and game["finished"] and event.key == K_r:
            game = reset_game()

    if not game["finished"]:
        keys = pygame.key.get_pressed()
        car = game["car"]
        # Player Physics
        if keys[K_LEFT]: car["angle"] += 3.2
        if keys[K_RIGHT]: car["angle"] -= 3.2
        boosting = keys[K_SPACE] and car["turbo"] > 5
        if keys[K_UP]: car["speed"] += 0.18 if boosting else 0.06
        car["turbo"] = car["turbo"] - 0.8 if boosting else min(100, car["turbo"] + 0.2)
        car["speed"] *= 0.95
        car["prev_z"] = car["z"]
        car["x"] += math.sin(math.radians(car["angle"])) * car["speed"]
        car["z"] += math.cos(math.radians(car["angle"])) * car["speed"]

        # Lap Logic
        if car["prev_z"] < 0 and car["z"] >= 0 and car["x"] > 0:
            game["laps"] += 1
            if game["laps"] >= 5: game["finished"] = True

        # AI Physics
        ai = game["ai"]
        ai["angle"] += ai["speed"]
        ai_x, ai_z = ai["radius"] * math.cos(math.radians(ai["angle"])), ai["radius"] * math.sin(math.radians(ai["angle"]))

    # Render
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(45, (display[0]/display[1]), 0.1, 500.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    
    # Camera
    cx, cz = car["x"] - 16 * math.sin(math.radians(car["angle"])), car["z"] - 16 * math.cos(math.radians(car["angle"]))
    gluLookAt(cx, 8, cz, car["x"], 1, car["z"], 0, 1, 0)
    glLightfv(GL_LIGHT0, GL_POSITION, [car["x"], 10, car["z"], 1])

    # World
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, sky_tex); glBegin(GL_QUADS)
    for i in range(4):
        ang = (math.pi/2) * i
        glTexCoord2f(i/4, 0); glVertex3f(200*math.cos(ang), -10, 200*math.sin(ang))
        glTexCoord2f((i+1)/4, 1); glVertex3f(200*math.cos(ang+1.6), 100, 200*math.sin(ang+1.6))
    glEnd()
    glBindTexture(GL_TEXTURE_2D, grass_tex); glBegin(GL_QUADS); 
    glTexCoord2f(0,0); glVertex3f(-300,0,-300); glTexCoord2f(60,0); glVertex3f(300,0,-300); 
    glTexCoord2f(60,60); glVertex3f(300,0,300); glTexCoord2f(0,60); glVertex3f(-300,0,300); glEnd()
    
    # Finish Line
    glDisable(GL_TEXTURE_2D); glColor3f(1, 1, 1); glBegin(GL_QUADS)
    glVertex3f(40, 0.05, -1); glVertex3f(70, 0.05, -1); glVertex3f(70, 0.05, 1); glVertex3f(40, 0.05, 1); glEnd()

    # Draw Cars
    glPushMatrix(); glTranslatef(car["x"], 0.2, car["z"]); glRotatef(car["angle"], 0, 1, 0); glScalef(0.6, 0.6, 0.6); truck_model.render((0.8, 0.8, 0.85)); glPopMatrix()
    glPushMatrix(); glTranslatef(ai_x, 0.2, ai_z); glRotatef(-ai["angle"] + 90, 0, 1, 0); glScalef(0.6, 0.6, 0.6); truck_model.render((0.3, 0.3, 0.35)); glPopMatrix()

    draw_hud(car, game["laps"], game["finished"])
    pygame.display.flip(); clock.tick(60)
pygame.quit()
