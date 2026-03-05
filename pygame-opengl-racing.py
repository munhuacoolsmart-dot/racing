import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from OpenGL.GLU import *
import math, random, time

# ----------------------------
# Initialize
# ----------------------------
pygame.init()
display = (1200, 700)
screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
pygame.display.set_caption("AAA Mini 3D Racing Game - Weather + Puddles")
clock = pygame.time.Clock()

glEnable(GL_DEPTH_TEST)
glEnable(GL_TEXTURE_2D)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

# ----------------------------
# Shadow setup
# ----------------------------
SHADOW_WIDTH, SHADOW_HEIGHT = 2048, 2048
shadow_fbo = glGenFramebuffers(1)
shadow_tex = glGenTextures(1)
glBindTexture(GL_TEXTURE_2D, shadow_tex)
glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,SHADOW_WIDTH,SHADOW_HEIGHT,0,GL_DEPTH_COMPONENT,GL_FLOAT,None)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
border=[1.0,1.0,1.0,1.0]
glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, border)
glBindFramebuffer(GL_FRAMEBUFFER, shadow_fbo)
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, shadow_tex, 0)
glDrawBuffer(GL_NONE)
glReadBuffer(GL_NONE)
glBindFramebuffer(GL_FRAMEBUFFER,0)

# ----------------------------
# Shaders (simplified soft shadows)
# ----------------------------
vertex_shadow = """
#version 330 core
layout(location=0) in vec3 aPos;
uniform mat4 model;
uniform mat4 lightSpaceMatrix;
void main(){gl_Position = lightSpaceMatrix*model*vec4(aPos,1.0);}
"""
fragment_shadow = "#version 330 core\nvoid main(){}"
vertex_scene = """
#version 330 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal;
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat4 lightSpaceMatrix;
out vec4 FragPosLightSpace;
out vec3 Normal;
out vec3 FragPos;
void main(){
FragPos=vec3(model*vec4(aPos,1.0));
Normal=mat3(transpose(inverse(model)))*aNormal;
FragPosLightSpace=lightSpaceMatrix*vec4(FragPos,1.0);
gl_Position=projection*view*vec4(FragPos,1.0);}
"""
fragment_scene = """
#version 330 core
in vec4 FragPosLightSpace; in vec3 Normal; in vec3 FragPos;
uniform sampler2D shadowMap; uniform vec3 lightPos; uniform vec3 objectColor;
float ShadowCalculation(vec4 fragPosLightSpace){
vec3 projCoords=fragPosLightSpace.xyz/fragPosLightSpace.w;
projCoords=projCoords*0.5+0.5;
float shadow=0.0; float bias=max(0.005*(1.0-dot(Normal,normalize(lightPos-FragPos))),0.001);
int samples=3; float offset=1.0/2048.0;
for(int x=-samples;x<=samples;x++){for(int y=-samples;y<=samples;y++){
float pcfDepth=texture(shadowMap,projCoords.xy+vec2(x,y)*offset).r;
if(projCoords.z-bias>pcfDepth) shadow+=1.0;}}
shadow/=pow(2*samples+1,2); return shadow;}
void main(){
vec3 norm=normalize(Normal); vec3 lightDir=normalize(lightPos-FragPos);
float diff=max(dot(norm,lightDir),0.0);
float shadow=ShadowCalculation(FragPosLightSpace);
float ambient=max(0.1,min(1.0,lightPos.y/50.0));
vec3 color=(ambient+(1.0-shadow)*diff)*objectColor;
gl_FragColor=vec4(color,1.0);}
"""
shadow_shader = compileProgram(compileShader(vertex_shadow,GL_VERTEX_SHADER),
                               compileShader(fragment_shadow,GL_FRAGMENT_SHADER))
scene_shader = compileProgram(compileShader(vertex_scene,GL_VERTEX_SHADER),
                              compileShader(fragment_scene,GL_FRAGMENT_SHADER))

# ----------------------------
# Load textures
# ----------------------------
def load_texture(path):
    surf = pygame.image.load(path)
    texData = pygame.image.tostring(surf,"RGB",1)
    w,h=surf.get_width(),surf.get_height()
    texID=glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D,texID)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,w,h,0,GL_RGB,GL_UNSIGNED_BYTE,texData)
    return texID

track_texture = load_texture("track.jpg")
grass_texture = load_texture("grass.jpg")

# ----------------------------
# Cars, Tracks, Puddles
# ----------------------------
car={"x":0,"z":0,"angle":0,"speed":0,"color":(0,0,1)}
ai_cars=[]
for i in range(4): ai_cars.append({"angle":random.randint(0,360),"radius":20+random.randint(-3,3),"speed":random.uniform(0.5,1.0),"color":(1,0,0)})
tracks=[{"radius":20+i*2,"width":6+i%3} for i in range(10)]
current_track=0
puddles=[{"x":random.uniform(-20,20),"z":random.uniform(-20,20),"radius":random.uniform(2,4)} for _ in range(10)]

# ----------------------------
# Rain + Fog
# ----------------------------
raining=True
rain_particles=[{"x":random.uniform(-50,50),"y":random.uniform(5,50),"z":random.uniform(-50,50)} for _ in range(500)]
glEnable(GL_FOG); glFogfv(GL_FOG_COLOR,[0.5,0.5,0.6,1]); glFogf(GL_FOG_DENSITY,0.02); glFogi(GL_FOG_MODE,GL_EXP2)

# ----------------------------
# Drawing functions
# ----------------------------
def draw_car(x,z,color=(0,0,1)):
    glPushMatrix(); glTranslatef(x,0,z); glColor3f(*color)
    glBegin(GL_QUADS)
    glVertex3f(-1,0,2); glVertex3f(1,0,2); glVertex3f(1,1,2); glVertex3f(-1,1,2)
    glVertex3f(-1,0,-2); glVertex3f(1,0,-2); glVertex3f(1,1,-2); glVertex3f(-1,1,-2)
    glEnd(); glPopMatrix()

def draw_track(track):
    radius,width=track["radius"],track["width"]; glBindTexture(GL_TEXTURE_2D,track_texture)
    glBegin(GL_QUAD_STRIP)
    for i in range(100+1):
        angle=2*math.pi*i/100
        x_outer=(radius+width)*math.cos(angle); z_outer=(radius+width)*math.sin(angle)
        x_inner=(radius-width)*math.cos(angle); z_inner=(radius-width)*math.sin(angle)
        glTexCoord2f(0,0); glVertex3f(x_outer,-0.1,z_outer); glTexCoord2f(1,1); glVertex3f(x_inner,-0.1,z_inner)
    glEnd()

def draw_grass(): glBindTexture(GL_TEXTURE_2D,grass_texture); glBegin(GL_QUADS); glTexCoord2f(0,0); glVertex3f(-50,-0.2,-50)
glTexCoord2f(1,0); glVertex3f(50,-0.2,-50); glTexCoord2f(1,1); glVertex3f(50,-0.2,50); glTexCoord2f(0,1); glVertex3f(-50,-0.2,50); glEnd()

def draw_rain():
    glColor3f(0.6,0.6,1); glBegin(GL_LINES)
    for drop in rain_particles: glVertex3f(drop["x"],drop["y"],drop["z"]); glVertex3f(drop["x"],drop["y"]-0.5,drop["z"])
    glEnd()

def update_rain():
    for drop in rain_particles:
        drop["y"]-=0.5
        if drop["y"]<0: drop.update({"y":random.uniform(10,50),"x":random.uniform(-50,50),"z":random.uniform(-50,50)})

def draw_puddles(time):
    glColor4f(0.3,0.4,0.5,0.6)
    for puddle in puddles:
        x,z,r=puddle["x"],puddle["z"],puddle["radius"]
        glPushMatrix(); glTranslatef(x,0.01,z); glBegin(GL_TRIANGLE_FAN); glVertex3f(0,0,0)
        for i in range(20+1):
            angle=2*math.pi*i/20; ripple=0.1*math.sin(time*5+i)
            glVertex3f((r+ripple)*math.cos(angle),0,(r+ripple)*math.sin(angle))
        glEnd(); glPopMatrix()

def set_camera():
    glLoadIdentity()
    cam_x = car["x"]-8*math.sin(math.radians(car["angle"]))
    cam_y = 5
    cam_z = car["z"]-8*math.cos(math.radians(car["angle"]))
    gluLookAt(cam_x,cam_y,cam_z,car["x"],0,car["z"],0,1,0)

# ----------------------------
# Main loop
# ----------------------------
sun_angle=0.0; sun_speed=0.05
running=True
while running:
    clock.tick(60)
    t = pygame.time.get_ticks()/1000.0
    for event in pygame.event.get(): 
        if event.type==pygame.QUIT: running=False

    keys=pygame.key.get_pressed()
    if keys[K_LEFT]: car["angle"]+=2
    if keys[K_RIGHT]: car["angle"]-=2
    if keys[K_UP]: car["speed"]+=0.05
    if keys[K_DOWN]: car["speed"]-=0.05
    car["speed"]*=0.97
    car["x"]+=math.sin(math.radians(car["angle"]))*car["speed"]
    car["z"]+=math.cos(math.radians(car["angle"]))*car["speed"]

    ai_positions=[]
    for ai in ai_cars: ai["angle"]+=ai["speed"]; ai_positions.append((ai["radius"]*math.cos(math.radians(ai["angle"])),ai["radius"]*math.sin(math.radians(ai["angle"]))))

    # Sun position
    sun_angle+=sun_speed; sun_angle%=360
    light_x,light_y,light_z=50*math.cos(math.radians(sun_angle)),50*math.sin(math.radians(sun_angle))+20,0
    light_pos=[light_x,light_y,light_z]

    update_rain()
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    set_camera()
    draw_grass(); draw_track(tracks[current_track])
    draw_car(car["x"],car["z"],car["color"])
    for pos,ai_car in zip(ai_positions,ai_cars): draw_car(pos[0],pos[1],ai_car["color"])
    if raining: draw_rain(); draw_puddles(t)
    pygame.display.flip()

pygame.quit()