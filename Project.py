
import pygame, sys
import time
import matplotlib.pyplot as plt
import numpy as np
import os
from win32 import win32gui
from ctypes import windll, Structure, c_long, byref

import winsound

from scipy.integrate import ode
import random
from random import randrange, uniform

# set up the colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
GRAY = (180, 180, 180)
LIGHT_GRAY = (240, 240, 240)

#os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (50,30)
	

win_width = 500
win_height = 674	

diff = 0.1
close = 0.9
close_dis = 40


goal_width = 200

drag = -0.1




def normalize(v):
	return v / np.linalg.norm(v)

class POINT(Structure):
		_fields_ = [("x", c_long), ("y", c_long)]
def queryMousePosition():
		pt = POINT()
		windll.user32.GetCursorPos(byref(pt))
		return [pt.x,pt.y]	   

class Disk(pygame.sprite.Sprite):
	
	def __init__(self, imgfile, radius, mass=1.0):
		pygame.sprite.Sprite.__init__(self)
		
		self.image = pygame.image.load(imgfile)

		self.image = pygame.transform.scale(self.image, (radius*2, radius*2))
		
		self.state = [0, 0, 0, 0]
		self.mass = mass
		self.t = 0
		self.radius = radius
		
		self.hit = False
		
		self.goalPlayer = False
		self.goalAI = False

		self.solver = ode(self.f)
		self.solver.set_integrator('dop853')
		self.solver.set_initial_value(self.state, self.t)

	def f(self, t, y):
		return [y[2], y[3], self.state[2]*drag, self.state[3]*drag]

	def set_pos(self, pos):
		self.state[0:2] = pos
		self.solver.set_initial_value(self.state, self.t)
		return self

	def set_vel(self, vel):
		self.state[2:] = vel
		self.solver.set_initial_value(self.state, self.t)
		return self
	
	def update(self, dt, disks):
		self.t += dt
		self.state = self.solver.integrate(self.t)		

			
	def updateMouse(self, dt, disks):
		self.t += dt
		pos = queryMousePosition()
		
		X, Y, r, b  = win32gui.GetWindowRect(pygame.display.get_wm_info()['window'])
		winx = 8 + X
		winy = 31 + Y

		
		#print(winx,winy)

		x_mouse = pos[0] - winx
		y_mouse = win_height - pos[1] + winy
		
		
		if ((x_mouse >= self.radius) & (x_mouse <= win_width - self.radius)):
			x = x_mouse
		else:
			x = self.state[0]
		if ((y_mouse >= self.radius) & (y_mouse <= win_height/2)):
			y = y_mouse
		else:
			y = self.state[1]
		
		vel_x = (x-self.state[0])/dt
		vel_y = (y-self.state[1])/dt
		
		self.state = [x,y,vel_x,vel_y]
		
	
	def updateAI(self, dt, disks, difficulty):
		self.t += dt
		
		x_puck = disks[1].state[0] 
		y_puck = disks[1].state[1]
		
		forsight = [0, 0]
		
		if (difficulty == "med"):
			forsight = [disks[1].state[2]/4, disks[1].state[3]/4]
		elif (difficulty == "hard"):
			forsight = [disks[1].state[2], disks[1].state[3]]
			
		if ((self.state[0] - x_puck)!=0):
			vel_x = -((self.state[0] - (x_puck + forsight[0])))*diff
		else:
			vel_x = 0
		
		if ((y_puck <= win_height/2) | (self.hit == True)):
			vel_y = -(self.state[1] - (win_height-self.radius))*diff
			if(self.state[1] >= (win_height-self.radius - 10)):
				self.hit = False
		elif ((self.state[1] - y_puck)!=0):
			vel_y = -((self.state[1] - (y_puck + forsight[1])))*diff
		else:
			vel_y = 0
			
		
		x = self.state[0] + vel_x
		
		y = self.state[1] + vel_y
		
		if ((x < self.radius) | (x > win_width - self.radius)):
			x = self.state[0]
		if ((y < win_height/2) | (y > win_height - self.radius)):
			y = self.state[1]
		
		
		self.state = [x,y,(x-self.state[0])/dt,(y-self.state[1])/dt]

		if (self.goalPlayer == True):
			x = win_width / 2
			y = win_height - self.radius - 30
			self.state = [x,y,0,0]
			disks[1].state = [win_width / 2,win_height / 4,0,0]
			self.goalPlayer = False
		elif (self.goalAI == True):
			x = win_width / 2
			y = win_height - self.radius - 30
			self.state = [x,y,0,0]
			disks[1].state = [win_width / 2,(3 * win_height) / 4,0,0]
			self.goalAI = False
			

	def move_by(self, delta):
		self.state[0:2] = np.add(self.pos, delta)
		return self

	def draw(self, surface):
		rect = self.image.get_rect()
		rect.center = (self.state[0], win_height-self.state[1]) # Flipping y
		surface.blit(self.image, rect)

	def pprint(self):
		print ('Disk', self.state)



class World:

	def __init__(self, difficulty):
		self.disks = []
		self.e = 1. # Coefficient of restitution
		
		self.playerScore = 0
		self.AIScore = 0
		self.winner = ""

		self.over = False
		self.count = 0

		self.difficulty = difficulty
		

		self.fontSmall = pygame.font.SysFont('Arial', 20)
		self.fontMed = pygame.font.SysFont('Arial', 80)
		self.font = pygame.font.SysFont('Arial', 200)

	def add(self, imgfile, radius, mass=1.0):
		disk = Disk(imgfile, radius, mass)
		self.disks.append(disk)
		return disk

	def pprint(self):
		print ('#disks', len(self.disks))
		for d in self.disks:
			d.pprint()

	def draw(self, screen):
		screen.blit(self.fontSmall.render(self.difficulty, True, GRAY), (20, 20))


		screen.blit(self.fontMed.render(str(self.winner), True, LIGHT_GRAY), (win_width/2-100, win_height/2-50))

		# AI Score
		screen.blit(self.font.render(str(self.AIScore), True, LIGHT_GRAY), (win_width/2-50, win_height/2 - 300))
		
		# Player Score
		screen.blit(self.font.render(str(self.playerScore), True, LIGHT_GRAY), (win_width/2-50, win_height/2 + 50))
		
		# Middle line
		pygame.draw.line(screen, GRAY, (0, win_height/2), (win_width, win_height/2), 1) 
		
		
		
		# Player Goal
		pygame.draw.lines(screen, GRAY, False, [(win_width/2 - goal_width/2, win_height), 
												(win_width/2 - goal_width/2, win_height - 20),
												(win_width/2 + goal_width/2, win_height - 20), 
												(win_width/2 + goal_width/2, win_height)], 1)
		
		# AI Goal
		pygame.draw.lines(screen, GRAY, False, [(win_width/2 - goal_width/2, 0), 
												(win_width/2 - goal_width/2, 20), 
												(win_width/2 + goal_width/2, 20), 
												(win_width/2 + goal_width/2, 0)], 1)

		for d in self.disks:			
			d.draw(screen)


	def reset(self):
		self.playerScore = 0
		self.AIScore = 0
		self.winner = ""

		self.over = False
		self.count = 0

		x_puck = win_width / 2
		y_puck = win_height / 2

		x_AI = win_width / 2
		y_AI = win_height - self.disks[1].radius - 30

		x_vel = 0
		y_vel = 0
		self.disks[1].state = [x_puck,y_puck,x_vel,y_vel]

		self.disks[2].state = [x_AI,y_AI,x_vel,y_vel]


	def update(self, dt):
		if(self.over == True):
			if(self.count == 5):
				time.sleep(3)
				self.reset()
			self.count += 1
		self.check_for_collision()
		self.disks[0].updateMouse(dt,self.disks)
		self.disks[1].update(dt,self.disks)
		self.disks[2].updateAI(dt,self.disks,self.difficulty)
			

	def compute_collision_response(self, i, j):
		pass

	def play_sound(self):
		pygame.mixer.music.load("hit_sound.mp3")
		pygame.mixer.music.play()

	def boundary_collison(self, pos_puck, radius_puck, vel_puck):
		vel_puck_aftercollision = vel_puck
		
		col = False

		if (pos_puck[0] == radius_puck):
			vel_puck_aftercollision = [-vel_puck[0], vel_puck[1]]
			col = True
		elif (pos_puck[0] < radius_puck):
			pos_puck[0] = radius_puck
			vel_puck_aftercollision = [-vel_puck[0], vel_puck[1]]
			col = True
		elif (pos_puck[0] == win_width - radius_puck):
			vel_puck_aftercollision = [-vel_puck[0], vel_puck[1]]
			col = True
		elif (pos_puck[0] > win_width - radius_puck):
			pos_puck[0] = win_width - radius_puck
			vel_puck_aftercollision = [-vel_puck[0], vel_puck[1]]
			col = True
		
		if((pos_puck[0] >= win_width/2 - goal_width/2) & (pos_puck[0] <= win_width/2 + goal_width/2)):
			if (pos_puck[1] <= 0):				   
				self.disks[2].goalAI = True
				self.AIScore += 1
				
				pygame.mixer.music.load("goal_sound.mp3")
				pygame.mixer.music.play()

				if (self.AIScore == 7):
					self.winner = "AI Wins!"
					self.over = True
				#time.sleep(0.3)
				return pos_puck, vel_puck_aftercollision
		elif (pos_puck[1] == radius_puck):
			vel_puck_aftercollision = [vel_puck[0], -vel_puck[1]]
			col = True
		elif (pos_puck[1] < radius_puck):
			pos_puck[1] = radius_puck
			vel_puck_aftercollision = [vel_puck[0], -vel_puck[1]]
			col = True
		
		if((pos_puck[0] >= win_width/2 - goal_width/2) & (pos_puck[0] <= win_width/2 + goal_width/2)):
			if (pos_puck[1] >= win_height):				   
				self.disks[2].goalPlayer = True
				self.playerScore += 1
				pygame.mixer.music.load("goal_sound.mp3")
				pygame.mixer.music.play()

				if (self.playerScore == 7):
					self.winner = "Player Wins!"
					self.over = True
				#time.sleep(0.3)
				return pos_puck, vel_puck_aftercollision
		elif (pos_puck[1] == win_height - radius_puck):
			vel_puck_aftercollision = [vel_puck[0], -vel_puck[1]]
			col = True
		elif (pos_puck[1] > win_height - radius_puck):
			pos_puck[1] = win_height - radius_puck
			vel_puck_aftercollision = [vel_puck[0], -vel_puck[1]]
			col = True

		if (col == True):
			self.play_sound()
		return pos_puck, vel_puck_aftercollision


	def check_for_collision(self):
		for i in range(0, len(self.disks)):
			if ((self.disks[2].goalPlayer == True) | (self.disks[2].goalAI == True)):
				break
			
			for j in range(i+1, len(self.disks)):
				
				pos_puck = np.array(self.disks[1].state[0:2])
				radius_puck = self.disks[1].radius
				vel_puck = np.array(self.disks[1].state[2:])
				
				pos_puck, vel_puck_aftercollision = self.boundary_collison(pos_puck, radius_puck, vel_puck)

				self.disks[1].state[0] = pos_puck[0]
				self.disks[1].state[1] = pos_puck[1]

				self.disks[1].set_vel(vel_puck_aftercollision)
				if ((self.disks[2].goalPlayer == True) | (self.disks[2].goalAI == True)):
					break
									
									
				pos_j = np.array(self.disks[j].state[0:2])
			
				vel_j = np.array(self.disks[j].state[2:])

				radius_j = self.disks[j].radius
				
				if i == j:
					continue
				pos_i = np.array(self.disks[i].state[0:2])
				pos_j = np.array(self.disks[j].state[0:2])
				dist_ij = np.sqrt(np.sum((pos_i - pos_j)**2))

				radius_i = self.disks[i].radius
				radius_j = self.disks[j].radius
				if dist_ij > radius_i + radius_j:
					continue

				# May be a collision
				vel_i = np.array(self.disks[i].state[2:])
				vel_j = np.array(self.disks[j].state[2:])
				relative_vel_ij = vel_i - vel_j
				n_ij = normalize(pos_i - pos_j)

				if np.dot(relative_vel_ij, n_ij) >= 0:
					continue
				
				
				if ((i == 2) | (j == 2)):
					self.disks[2].hit = True
				
				self.play_sound()
				mass_i = self.disks[i].mass
				mass_j = self.disks[j].mass

				J = -(1+self.e) * np.dot(relative_vel_ij, n_ij) / ((1./mass_i) + (1./mass_j))

				vel_i_aftercollision = vel_i + n_ij * J / mass_i
				vel_j_aftercollision = vel_j - n_ij * J / mass_j
				

				self.disks[i].set_vel(vel_i_aftercollision)
				self.disks[j].set_vel(vel_j_aftercollision)
				break




def main():
	os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (50,32)


	print("Turn on sound for more enjoyment!")

	while (True):	
		d = input('[e]asy, [m]edium, [h]ard? ')

		if ((d == "e") | (d == "E")):
			difficulty = "easy"
			break
		elif ((d == "m") | (d == "M")):
			difficulty = "med"
			break
		elif ((d == "h") | (d == "H")):
			difficulty = "hard"
			break
		else:
			print("Enter a valid choice")


   # initializing pygame
	pygame.init()

	clock = pygame.time.Clock()

	screen = pygame.display.set_mode((win_width, win_height))
	pygame.display.set_caption('AirHockey')
	
	X, Y, r, b  = win32gui.GetWindowRect(pygame.display.get_wm_info()['window'])
	winx = 8 + X
	winy = 31 + Y

	pos = queryMousePosition()

	
	world = World(difficulty)
	
	
	#MOUSE
	
	radius = 20
	mass = 1
	x_vel = 0
	y_vel = 0
	color = RED
	

	world.add('disk-red.png', radius, mass).set_pos([pos[0] - winx, win_width - pos[1] + winy]).set_vel([x_vel,y_vel])
	
	
	#PUCK
	
	radius = 20
	mass = 1
	x_puck = win_width / 2
	y_puck = win_height / 2
	x_vel = 0
	y_vel = 0
	color = BLACK
	world.add('disk-black.png', radius, mass).set_pos([x_puck,y_puck]).set_vel([x_vel,y_vel])
	
	
	#AI
	
	radius = 20
	mass = 40
	x_AI = win_width / 2
	y_AI = win_height - radius - 30
	x_vel = 0
	y_vel = 0
	color = BLUE
	world.add('disk-blue.png', radius, mass).set_pos([x_AI,y_AI]).set_vel([x_vel,y_vel])
	
	dt = 0.1

	
	while True:
		# 30 fps
		clock.tick(30)

		event = pygame.event.poll()
		if event.type == pygame.QUIT:
			pygame.quit()
			sys.exit(0)
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
			pygame.quit()
			sys.exit(0)
		else:
			pass

		# Clear the background, and draw the sprites
		screen.fill(WHITE)
		world.draw(screen)
		
		world.update(dt)

		pygame.display.update()

if __name__ == '__main__':
	main()





