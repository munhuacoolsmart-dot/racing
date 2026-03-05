import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math, random, time

# --- CONFIG & INITIALIZATION ---
pygame.init()
SCREEN_RES = (1200, 700)
pygame.display.set_mode(SCREEN_RES, DOUBLEBUF | OPENGL)
pygame.display.set_caption("Cybertruck Pro: Ultimate Edition")
clock = pygame.time.Clock()
font = pygame.font.SysFont('Monospace', 24, bold=True)
big_font = pygame.font.SysFont('Monospace', 48, bold=True)

# --- ASSET LOADERS ---
def load_texture(path):
    try:
        surf = pygame.image.load(path)
        data = pygame.image.tostring(surf, "RGBA", 1)
        w, h = surf.get_size()
        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glGenerateMipmap(GL_TEXTURE_2D)
        return texid
    except: return None

class OBJ:
    def __init__(self, filename):
        self.vertices, self.texcoords, self.faces = [], [], []
        try:
            with open(filename, "r") as f:
                for line in f:
                    if line.startswith('v '): self.vertices.append(list(map(float, line.split()[1:4])))
                    elif line.startswith('vt '): self.texcoords.append(list(map(float, line.split()[1:3])))
                    elif line.startswith('f '):
                        face = []
                        for v in line.split()[1:]:
                            w = v.split('/')
                            face.append((int(w[0])-1, int(w[1])-1 if len(w)>1 and w[1] else -1))
                        if len(face) >= 3:
                            self.faces.append(face[:3])
                            if len(face) == 4: self.faces.append([face[0], face[2], face[3]])
            self.gl_list = glGenLists(1)
            glNewList(self.gl_list, GL_COMPILE)
            glBegin(GL_TRIANGLES)
            for face in self.faces:
                for v_i, t_i in face:
                    if t_i >= 0: glTexCoord2fv(self.texcoords[t_i])
                    glVertex3fv(self.vertices[v_i])
            glEnd(); glEndList()
        except: pass
    def render(self): 
        if hasattr(self, 'gl_list'): glCallList(self.gl_list)

# --- PARTICLE CLASS ---
class Particle:
    def __init__(self, x, y, z, p_type="smoke"):
        self.x, self.y, self.z = x, y, z
        self.type = p_type
        self.life = 1.0
        self.vx = random.uniform(-0.05, 0.05)
        self.vy = random.uniform(0.01, 0.06)
        self.vz = random.uniform(-0.05, 0.05)

    def update(self):
        self.x += self.vx; self.y += self.vy; self.z += self.vz
        self.life -= 0.03 if self.type == "smoke" else 0.08
        return self.life > 0

    def draw(self):
        glPushMatrix(); glDisable(GL_LIGHTING); glDisable(GL_TEXTURE_2D)
        glTranslatef(self.x, self.y, self.z)
        if self.type == "smoke": glColor4f(0.6, 0.6, 0.6, self.life)
        else: glColor4f(1.0, random.uniform(0.2, 0.7), 0.0, self.life)
        s = 0.2 * self.life
        glBegin(GL_QUADS); glVertex3f(-s,s,0); glVertex3f(s,s,0); glVertex3f(s,-s,0); glVertex3f(-s,-s,0); glEnd()
        glEnable(GL_TEXTURE_2D); glEnable(GL_LIGHTING); glPopMatrix()

# --- HUD UTILS ---
def draw_ui_text(x, y, text, color=(255, 255, 255), center=False, big=False):
    f = big_font if big else font
    surf = f.render(text, True, color)
    data = pygame.image.tostring(surf, "RGBA", True)
    if center: x -= surf.get_width() // 2
    glWindowPos2d(x, y)
    glDrawPixels(surf.get_width(), surf.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, data)

# --- MAIN ENGINE ---
def main():
    # Load All Assets
    truck_model = OBJ("cybertruck.obj")
    tex = {
        "truck": load_texture("cybertruck.jpg"),
        "grass": load_texture("grass.jpg"),
        "sky": load_texture("sky.jpg"),
        "track": load_texture("track.jpg")
    }

    # State Variables
    game_state = "MENU" # MENU, RACING, FINISHED
    car = {"x": 55, "y": 0, "z": -5, "angle": 0, "speed": 0, "turbo": 100.0, "y_vel": 0, "on_ground": True}
    ai = {"x": 0, "z": 0, "angle": 15, "radius": 52, "speed": 0.96, "stun": 0}
    particles = []
    best_lap = float('inf')
    lap_start = 0
    laps = 0
    shake = 0
    was_boosting = False

    while True:
        for event in pygame.event.get():
            if event.type == QUIT: return
            if event.type == KEYDOWN:
                if game_state == "MENU" and event.key == K_RETURN:
                    game_state = "RACING"; lap_start = time.time()
                if game_state == "FINISHED" and event.key == K_r: return main()
                if game_state == "RACING" and event.key == K_SPACE and car["on_ground"]:
                    car["y_vel"] = 0.5; car["on_ground"] = False

        if game_state == "RACING":
            keys = pygame.key.get_pressed()
            if keys[K_LEFT]: car["angle"] += 3.5
            if keys[K_RIGHT]: car["angle"] -= 3.5
            
            # Physics & Jump
            if not car["on_ground"]:
                car["y"] += car["y_vel"]; car["y_vel"] -= 0.03
                if car["y"] <= 0:
                    car["y"] = 0; car["y_vel"] = 0; car["on_ground"] = True; shake = 12
            
            boosting = keys[K_SPACE] and car["turbo"] > 5 and car["on_ground"]
            car["speed"] += (0.18 if boosting else 0.06) if keys[K_UP] else 0
            car["turbo"] = max(0, car["turbo"] - 0.7) if boosting else min(100, car["turbo"] + 0.2)
            car["speed"] *= 0.95
            
            pz = car["z"]
            car["x"] += math.sin(math.radians(car["angle"])) * car["speed"]
            car["z"] += math.cos(math.radians(car["angle"])) * car["speed"]

            # Lap Logic
            if pz < 0 <= car["z"] and car["x"] > 0:
                if laps > 0: best_lap = min(best_lap, time.time() - lap_start)
                laps += 1; lap_start = time.time()

            # Particles
            rx, rz = car["x"] - math.sin(math.radians(car["angle"]))*2.5, car["z"] - math.cos(math.radians(car["angle"]))*2.5
            if boosting: particles.append(Particle(rx, 0.5, rz, "fire"))
            if was_boosting and not boosting: 
                for _ in range(10): particles.append(Particle(rx, 0.5, rz, "fire"))
            if car["speed"] > 0.6 and (keys[K_LEFT] or keys[K_RIGHT]):
                particles.append(Particle(rx, 0.1, rz, "smoke"))
            
            was_boosting = boosting
            particles = [p for p in particles if p.update()]

            # AI
            ai["angle"] += ai["speed"]; ai["x"] = ai["radius"]*math.cos(math.radians(ai["angle"])); ai["z"] = ai["radius"]*math.sin(math.radians(ai["angle"]))

        # --- RENDERING ---
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45, 1200/700, 0.1, 500.0); glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        sx = random.uniform(-0.1, 0.1) * shake if shake > 0 else 0
        if shake > 0: shake -= 1
        gluLookAt(car["x"]-16*math.sin(math.radians(car["angle"]))+sx, 8+car["y"], car["z"]-16*math.cos(math.radians(car["angle"])), car["x"], 1, car["z"], 0, 1, 0)
        
        # World
        glDisable(GL_LIGHTING); glBindTexture(GL_TEXTURE_2D, tex["sky"]); glBegin(GL_QUADS)
        for i in range(4): a=(math.pi/2)*i; glTexCoord2f(i/4,0); glVertex3f(250*math.cos(a),-20,250*math.sin(a)); glTexCoord2f((i+1)/4,1); glVertex3f(250*math.cos(a+1.6),120,250*math.sin(a+1.6)); glEnd()
        glBindTexture(GL_TEXTURE_2D, tex["grass"]); glBegin(GL_QUADS); glTexCoord2f(0,0); glVertex3f(-400,0,-400); glTexCoord2f(80,0); glVertex3f(400,0,-400); glTexCoord2f(80,80); glVertex3f(400,0,400); glTexCoord2f(0,80); glVertex3f(-400,0,400); glEnd()
        glBindTexture(GL_TEXTURE_2D, tex["track"]); glBegin(GL_QUAD_STRIP);
        for i in range(361): r=math.radians(i); glTexCoord2f(i/10,0); glVertex3f(46*math.cos(r),0.02,46*math.sin(r)); glTexCoord2f(i/10,1); glVertex3f(64*math.cos(r),0.02,64*math.sin(r)); glEnd()
        
        # Models & Particles
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE); [p.draw() for p in particles]; glDisable(GL_BLEND)
        glEnable(GL_LIGHTING); glEnable(GL_COLOR_MATERIAL); glBindTexture(GL_TEXTURE_2D, tex["truck"])
        glPushMatrix(); glTranslatef(car["x"], 0.2+car["y"], car["z"]); glRotatef(car["angle"], 0, 1, 0); glScalef(0.6,0.6,0.6); truck_model.render(); glPopMatrix()
        glPushMatrix(); glTranslatef(ai["x"], 0.2, ai["z"]); glRotatef(-ai["angle"]+90, 0, 1, 0); glScalef(0.6,0.6,0.6); glColor3f(0.3,0.3,0.4); truck_model.render(); glColor3f(1,1,1); glPopMatrix()

        # UI Overlay
        glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING)
        if game_state == "MENU":
            draw_ui_text(600, 400, "CYBERTRUCK PRO", (0, 255, 255), True, True)
            draw_ui_text(600, 340, "PRESS ENTER TO RACE", (255, 255, 255), True)
        else:
            draw_ui_text(30, 650, f"LAP: {laps}")
            draw_ui_text(30, 620, f"TURBO: {int(car['turbo'])}%")
            best_str = "---" if best_lap == float('inf') else f"{round(best_lap, 2)}s"
            draw_ui_text(1000, 650, f"BEST: {best_str}", (255, 215, 0))
        
        glEnable(GL_DEPTH_TEST); pygame.display.flip(); clock.tick(60)

if __name__ == "__main__": main()
