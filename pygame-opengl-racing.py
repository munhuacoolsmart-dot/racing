from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import math, random, numpy as np
import math, random

# --- 1. CONFIG & INITIALIZATION ---
# ----------------------------
# Initialize
# ----------------------------
pygame.init()
display = (1200, 700)
screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
pygame.display.set_caption("Cybertruck Racing: Pro Edition")
display = (1200,700)
screen = pygame.display.set_mode(display, DOUBLEBUF|OPENGL)
pygame.display.set_caption("AAA Mini 3D Racing Game - Cybertruck Edition")
clock = pygame.time.Clock()
pygame.mixer.init()

# OpenGL Flags
glEnable(GL_DEPTH_TEST)
glEnable(GL_TEXTURE_2D)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
glEnable(GL_LIGHT1)
glEnable(GL_COLOR_MATERIAL)
glEnable(GL_FOG)
glFogi(GL_FOG_MODE, GL_EXP2)
glLightf(GL_LIGHT1, GL_SPOT_CUTOFF, 25.0)

# --- 2. ASSET LOADERS ---
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
    try:
        surf = pygame.image.load(path)
        data = pygame.image.tostring(surf, "RGBA", 1)
        w, h = surf.get_size()
        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texid)
        gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGBA, w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)
        return texid
    except: return None
def load_obj(filename):
    verts, texs, final_data = [], [], []
    try:
        with open(filename) as f:
            for line in f:
                if line.startswith('v '): verts.append(list(map(float, line.split()[1:])))
                elif line.startswith('vt '): texs.append(list(map(float, line.split()[1:])))
                elif line.startswith('f '):
                    for v in line.split()[1:]:
                        w = v.split('/')
                        final_data.extend(verts[int(w[0])-1])
                        final_data.extend(texs[int(w[1])-1] if len(w)>1 and w[1] else [0,0])
        v_buf = np.array(final_data, dtype=np.float32)
        return vbo.VBO(v_buf), len(v_buf) // 5
    except: return None, 0
# --- 3. PROCEDURAL & GAME LOGIC ---
def generate_track():
    pts = []
    r, w, c, a = random.uniform(35, 50), 6.5, random.randint(3, 7), random.uniform(4, 8)
    for i in range(101):
        ang = 2 * math.pi * i / 100
        rd = r + a * math.sin(c * ang)
        pts.append((( (rd+w)*math.cos(ang), (rd+w)*math.sin(ang) ), 
                    ( (rd-w)*math.cos(ang), (rd-w)*math.sin(ang) )))
    return pts
# Difficulty Settings
DIFFICULTIES = {
    "ROOKIE": {"width": 9.0, "grip": 0.98, "ghost_speed": 0.95},
    "PRO":    {"width": 6.5, "grip": 0.96, "ghost_speed": 1.0},
    "CYBER":  {"width": 4.5, "grip": 0.93, "ghost_speed": 1.05}
}
# State Variables
STATE_MENU, STATE_RACING, STATE_SUMMARY = 0, 1, 2
game_state = STATE_MENU
cur_diff = "PRO"
cur_track_idx = 0
all_tracks = [generate_track() for _ in range(10)]
car = {"x": 0, "z": 50, "angle": 0, "speed": 0}
is_turbo, fov = False, 45.0
lap_count, start_tick, best_lap = 0, 0, float('inf')
ghost_data, cur_lap_rec = [], []
ghost_frame = 0
screen_drops = []
# --- 4. RENDERERS ---
def draw_scene():
    # Track
    glBindTexture(GL_TEXTURE_2D, track_tex)
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
    for out, inn in all_tracks[cur_track_idx]:
        glTexCoord2f(0,0); glVertex3f(out[0], 0, out[1])
        glTexCoord2f(1,1); glVertex3f(inn[0], 0, inn[1])
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
    # Ground
    glBindTexture(GL_TEXTURE_2D, grass_tex)
# ----------------------------
# Grass
# ----------------------------
def draw_grass():
    glBindTexture(GL_TEXTURE_2D,grass_texture)
    glBegin(GL_QUADS)
    glTexCoord2f(0,0); glVertex3f(-300, -0.1, -300)
    glTexCoord2f(20,0); glVertex3f(300, -0.1, -300)
    glTexCoord2f(20,20); glVertex3f(300, -0.1, 300)
    glTexCoord2f(0,20); glVertex3f(-300, -0.1, 300)
    glTexCoord2f(0,0)
    glVertex3f(-50,-0.2,-50)
    glTexCoord2f(1,0)
    glVertex3f(50,-0.2,-50)
    glTexCoord2f(1,1)
    glVertex3f(50,-0.2,50)
    glTexCoord2f(0,1)
    glVertex3f(-50,-0.2,50)
    glEnd()

def draw_truck(x, z, ang, is_ghost=False):
    glPushMatrix()
    glTranslatef(x, 0.2, z)
    glRotatef(ang, 0, 1, 0)
    if is_ghost:
        glDisable(GL_TEXTURE_2D); glColor4f(0, 1, 1, 0.3)
    else:
        glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, truck_tex); glColor4f(1,1,1,1)
    
    truck_vbo.bind()
    glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glVertexPointer(3, GL_FLOAT, 20, truck_vbo)
    glTexCoordPointer(2, GL_FLOAT, 20, truck_vbo + 12)
    glDrawArrays(GL_TRIANGLES, 0, truck_count)
    truck_vbo.unbind()
    glDisableClientState(GL_VERTEX_ARRAY); glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glPopMatrix()

def draw_hud_elements():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, display[0], 0, display[1])
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
    if game_state == STATE_MENU:
        # Simple Menu Overlay
        glColor4f(0,0,0,0.7); glRectf(0,0,display[0],display[1])
        # Preview Track
        glTranslatef(display[0]/2, display[1]/2, 0); glScalef(3, 3, 1)
        glColor3f(0, 1, 1); glBegin(GL_LINE_LOOP)
        for out, _ in all_tracks[cur_track_idx]: glVertex2f(out[0], out[1])
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
    
    elif game_state == STATE_RACING:
        # Speedometer
        s_val = min(abs(car["speed"])/2.2 * 200, 200)
        glColor3f(1, 1, 1); glRectf(display[0]-220, 20, display[0]-20, 40)
        glColor3f(0, 1, 1 if is_turbo else 0); glRectf(display[0]-220, 20, display[0]-220+s_val, 40)
    glEnable(GL_DEPTH_TEST); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix()
# --- 5. SYSTEM LOADING ---
truck_vbo, truck_count = load_obj("cybertruck.obj")
truck_tex = load_texture("cybertruck.jpg")
track_tex = load_texture("track.jpg")
grass_tex = load_texture("grass.jpg")
# --- 6. MAIN LOOP ---
running = True
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
    dt = clock.tick(60)
    clock.tick(60)
    t=pygame.time.get_ticks()/1000.0
    for event in pygame.event.get():
        if event.type == QUIT: running = False
        if event.type == KEYDOWN:
            if game_state == STATE_MENU:
                if event.key == K_RIGHT: cur_track_idx = (cur_track_idx + 1) % 10
                if event.key == K_TAB: cur_diff = "CYBER" if cur_diff == "PRO" else "PRO" if cur_diff == "ROOKIE" else "ROOKIE"
                if event.key == K_RETURN: 
                    game_state = STATE_RACING
                    car = {"x": 0, "z": 50, "angle": 0, "speed": 0}
                    start_tick = pygame.time.get_ticks()
            elif event.key == K_ESCAPE: game_state = STATE_MENU
    if game_state == STATE_RACING:
        # Physics
        keys = pygame.key.get_pressed()
        diff = DIFFICULTIES[cur_diff]
        if keys[K_LEFT]: car["angle"] += 3.5
        if keys[K_RIGHT]: car["angle"] -= 3.5
        is_turbo = keys[K_SPACE]
        accel = 0.12 if is_turbo else 0.05
        if keys[K_UP]: car["speed"] += accel
        car["speed"] *= diff["grip"]
        car["x"] += math.sin(math.radians(car["angle"])) * car["speed"]
        car["z"] += math.cos(math.radians(car["angle"])) * car["speed"]
        
        # Ghost Rec & FOV
        cur_lap_rec.append((car["x"], car["z"], car["angle"]))
        target_fov = 75 if is_turbo else 45
        fov += (target_fov - fov) * 0.1
    # Rendering
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    if game_state == STATE_RACING:
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(fov, display[0]/display[1], 0.1, 500)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        # Cam
        cx = car["x"] - 12 * math.sin(math.radians(car["angle"]))
        cz = car["z"] - 12 * math.cos(math.radians(car["angle"]))
        gluLookAt(cx, 5, cz, car["x"], 1, car["z"], 0, 1, 0)
        
        draw_scene()
        draw_truck(car["x"], car["z"], car["angle"])
        if ghost_data:
            g_idx = int(ghost_frame * diff["ghost_speed"]) % len(ghost_data)
            draw_truck(*ghost_data[g_idx], is_ghost=True)
            ghost_frame += 1
    draw_hud_elements()
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
