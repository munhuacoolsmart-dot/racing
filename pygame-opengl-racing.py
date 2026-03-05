import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math, random, time

# --- INITIALIZATION ---
pygame.init()
display = (1200, 700)
pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
pygame.display.set_caption("Cybertruck Pro: Final Edition")
clock = pygame.time.Clock()

# --- 1. EXTERNAL OBJ LOADER ---
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
                        # Supports v, v/vt, and v/vt/vn formats
                        face = [int(v.split('/')[0]) - 1 for v in line.split()[1:]]
                        # Triangulate if necessary (OpenGL GL_TRIANGLES needs 3 points)
                        if len(face) == 3:
                            self.faces.append(face)
                        elif len(face) == 4:
                            self.faces.append([face[0], face[1], face[2]])
                            self.faces.append([face[0], face[2], face[3]])
            
            # Compile into Display List for high FPS
            self.gl_list = glGenLists(1)
            glNewList(self.gl_list, GL_COMPILE)
            glBegin(GL_TRIANGLES)
            for face in self.faces:
                for vertex in face:
                    glVertex3fv(self.vertices[vertex])
            glEnd()
            glEndList()
        except Exception as e:
            print(f"Could not load {filename}: {e}")

    def render(self, color):
        glColor3f(*color)
        if hasattr(self, 'gl_list'):
            glCallList(self.gl_list)

# --- 2. PARTICLE SYSTEM (SMOKE) ---
smoke_particles = []

def create_smoke(x, z, angle):
    for _ in range(2):
        smoke_particles.append({
            "pos": [x - math.sin(math.radians(angle))*2, 0.1, z - math.cos(math.radians(angle))*2],
            "vel": [random.uniform(-0.04, 0.04), random.uniform(0.02, 0.08), random.uniform(-0.04, 0.04)],
            "life": 1.0
        })

def draw_smoke():
    glDisable(GL_LIGHTING)
    glBegin(GL_POINTS)
    for p in smoke_particles[:]:
        glColor4f(0.5, 0.5, 0.5, p["life"] * 0.4)
        glVertex3fv(p["pos"])
        p["pos"][0] += p["vel"][0]
        p["pos"][1] += p["vel"][1]
        p["pos"][2] += p["vel"][2]
        p["life"] -= 0.025
        if p["life"] <= 0: smoke_particles.remove(p)
    glEnd()
    glEnable(GL_LIGHTING)

# --- 3. HUD ---
def draw_hud(car, laps, finished):
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, display[0], 0, display[1])
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
    if finished:
        glColor4f(0,0,0,0.7); glRectf(0,0,display[0],display[1])
        glColor3f(1,1,1); glRectf(display[0]//2-100, display[1]//2-20, display[0]//2+100, display[1]//2+20)
    else:
        # Turbo Bar
        glColor3f(0.1, 0.1, 0.1); glRectf(50, 50, 300, 70)
        glColor3f(0, 0.8, 1) if car["turbo"] > 20 else glColor3f(1, 0, 0)
        glRectf(50, 50, 50 + (car["turbo"] * 2.5), 70)
        # Laps
        for i in range(laps):
            glColor3f(0, 1, 0); glRectf(50 + (i*35), 80, 75 + (i*35), 100)
    glEnable(GL_DEPTH_TEST); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix()

# --- 4. MAIN GAME ---
def main():
    # Load the model from your file
    truck_model = OBJ("cybertruck.obj")
    
    car = {"x": 55, "z": -5, "angle": 0, "speed": 0, "turbo": 100.0, "prev_z": -5}
    ai = {"angle": 15, "radius": 52, "speed": 0.9}
    laps = 0
    finished = False
    cur_fov = 45.0

    glEnable(GL_DEPTH_TEST); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_COLOR_MATERIAL)

    while True:
        for event in pygame.event.get():
            if event.type == QUIT: return
            if event.type == KEYDOWN and finished and event.key == K_r: return main()

        if not finished:
            keys = pygame.key.get_pressed()
            if keys[K_LEFT]: car["angle"] += 3.5
            if keys[K_RIGHT]: car["angle"] -= 3.5
            
            boosting = keys[K_SPACE] and car["turbo"] > 5
            if keys[K_UP]: 
                car["speed"] += 0.18 if boosting else 0.06
                if boosting or car["speed"] > 0.7: create_smoke(car["x"], car["z"], car["angle"])
            
            car["turbo"] = car["turbo"] - 0.8 if boosting else min(100, car["turbo"] + 0.2)
            cur_fov += ((75 if boosting else 45) - cur_fov) * 0.1
            car["speed"] *= 0.95
            
            car["prev_z"] = car["z"]
            car["x"] += math.sin(math.radians(car["angle"])) * car["speed"]
            car["z"] += math.cos(math.radians(car["angle"])) * car["speed"]

            # Lap logic
            if car["prev_z"] < 0 and car["z"] >= 0 and car["x"] > 0:
                laps += 1
                if laps >= 5: finished = True

            # AI Orbit
            ai["angle"] += ai["speed"]
            ai_x, ai_z = ai["radius"] * math.cos(math.radians(ai["angle"])), ai["radius"] * math.sin(math.radians(ai["angle"]))

        # Render
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(cur_fov, (display[0]/display[1]), 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        cx, cz = car["x"] - 16 * math.sin(math.radians(car["angle"])), car["z"] - 16 * math.cos(math.radians(car["angle"]))
        gluLookAt(cx, 8, cz, car["x"], 1, car["z"], 0, 1, 0)
        glLightfv(GL_LIGHT0, GL_POSITION, [car["x"], 10, car["z"], 1])

        # Floor (Grey Asphalt)
        glDisable(GL_LIGHTING); glColor3f(0.15, 0.15, 0.15)
        glBegin(GL_QUADS); glVertex3f(-300,0,-300); glVertex3f(300,0,-300); glVertex3f(300,0,300); glVertex3f(-300,0,300); glEnd()
        
        # Finish Line
        glColor3f(1, 1, 1)
        glBegin(GL_QUADS); glVertex3f(40,0.01,-1); glVertex3f(70,0.01,-1); glVertex3f(70,0.01,1); glVertex3f(40,0.01,1); glEnd()
        glEnable(GL_LIGHTING)

        draw_smoke()

        # Render Cars
        glPushMatrix(); glTranslatef(car["x"], 0.2, car["z"]); glRotatef(car["angle"], 0, 1, 0); glScalef(0.65, 0.65, 0.65)
        truck_model.render((0.8, 0.8, 0.85)); glPopMatrix()

        glPushMatrix(); glTranslatef(ai_x, 0.2, ai_z); glRotatef(-ai["angle"]+90, 0, 1, 0); glScalef(0.65, 0.65, 0.65)
        truck_model.render((0.3, 0.3, 0.35)); glPopMatrix()

        draw_hud(car, laps, finished)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
    pygame.quit()
