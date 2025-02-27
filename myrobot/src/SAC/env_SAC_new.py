#!/usr/bin/env python3

import rospy
import numpy as np
import math
import os
import time
import random
from math import pi, sqrt, pow, exp
from gazebo_msgs.srv import SpawnModel, DeleteModel
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import Twist, Point, Pose
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Int64
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty
from tf.transformations import euler_from_quaternion, quaternion_from_euler
# from respawnGoal import Respawn


#class respawn_goal():#
#
#    def __init__(self):        
#        self.goal_modelPath = "/home/jm-kim/catkin_ws/src/myrobot/urdf/goal_box/model.sdf"
#        self.f = open(self.goal_modelPath, 'r')
#        self.goal_model = self.f.read()
#        self.modelName = 'goal'
#    
#        self.goal_position = Pose()
#        self.goal_position.position.x = 0
#        self.goal_position.position.y = 0
#        
#        self.sub_model = rospy.Subscriber('gazebo/model_states', ModelStates, self.checkModel)
#        self.check_model = False
#        
#    def checkModel(self, model):
#        self.check_model = False
#        for i in range(len(model.name)):
#            if model.name[i] == "goal":
#                self.check_model = True
#                
#    def respawnModel(self):
#        while True:
#            if not self.check_model:
#                rospy.wait_for_service('gazebo/spawn_sdf_model')
#                spawn_model_prox = rospy.ServiceProxy('gazebo/spawn_sdf_model', SpawnModel)
#                spawn_model_prox(self.modelName, self.goal_model, 'robotos_name_space', self.goal_position, "world")
#                #rospy.loginfo("Goal position : %.1f, %.1f", self.goal_position.position.x,
#                #              self.goal_position.position.y)
#                
#                break
#            else:
#                pass
#
#    def deleteModel(self):
#        while True:
#            if self.check_model:
#                rospy.wait_for_service('gazebo/delete_model')
#                del_model_prox = rospy.ServiceProxy('gazebo/delete_model', DeleteModel)
#                del_model_prox(self.modelName)
#                break
#            else:
#                pass
#                
#[3,3],[3,-3],[-3,3],[-3,-3],[6,6],[6,-6],[-6,6],[-6,-6],[6,0],[0,6],[-6,0],[0,-6] 
#
#    def goal_def(self, delete):
#       
#        obstacles = [[-6,6],[-3,6],[0,6],[3,6],[6,6],[-6,3],[-3,3],[0,3],[3,3],[6,3],[-6,0],[-3,0],[3,0],[6,0],[-6,-3],[-3,-3],[0,-3],[3,-3],[6,-3],[-6,-6],[-3,-6],[0,-6],[3,-6],[6,-6]]
#        while True:
#            distance = []
#            print("finding proper goal position...")
#            x, y = np.random.randint(-75,75)/10, np.random.randint(-75,75)/10
#            for i in range(len(obstacles)):
#                distance.append(sqrt(pow(obstacles[i][0]-x,2)+pow(obstacles[i][1]-y,2)))
#            if min(distance) > 1.5:
#                break
#        
#        self.goal_position.position.x = x
#        self.goal_position.position.y = y
#        
#        if delete:
#            self.deleteModel()
#            self.respawnModel()
#        
#        else:
#            self.respawnModel()
#            
#        return x, y       
        
         
         
#[[-6,6],[-3,6],[0,6],[3,6],[6,6],[-6,3],[-3,3],[0,3],[3,3],[6,3],[-6,0],[-3,0],[3,0],[6,0],[-6,-3],[-3,-3],[0,-3],[3,-3],[6,-3],[-6,-6],[-3,-6],[0,-6],[3,-6],[6,-6]]    

# [[3,0],[3,3],[0,3],[-3,3],[-3,0],[-3,-3],[0,-3],[3,-3]]

#[[2,0],[4,0],[3,3],[0,2],[0,4],[-2,0],[-4,0],[-3,3],[0,-2],[0,-4],[3,-3],[-3,-3]]

    
def goal_def():

    obstacles = [[2,0],[4,0],[3,3],[0,2],[0,4],[-2,0],[-4,0],[-3,3],[0,-2],[0,-4],[3,-3],[-3,-3]]
    while True:
        distance = []
        #print("finding proper goal position...")
        x, y = np.random.randint(-47,47)/10, np.random.randint(-47,47)/10
        for i in range(len(obstacles)):
            distance.append(sqrt(pow(obstacles[i][0]-x,2)+pow(obstacles[i][1]-y,2)))
        if (min(distance) >= 1.0) and (not(x==0 and y==0)):
            break
              
    return x, y 


class Env():
    def __init__(self):
    
        #self.RespawnGoal = respawn_goal()
        self.delete = False
        self.goal_x, self.goal_y = 4.5, 4.5 # goal_def()
        #self.goal_x, self.goal_y = self.RespawnGoal.goal_def(self.delete)
        
        self.heading = 0
        #self.initGoal = True
        self.get_goalbox = False
        self.position = Pose()
        self.line_error = 0
        
        self.current_obstacle_angle = 0
        self.old_obstacle_angle = 0
        self.current_obstacle_min_range = 0
        self.old_obstacle_min_range = 0
        self.t = 0
        self.old_t = time.time()
        self.dt = 0
        
        self.time_step = 0
                
        self.reset_proxy = rospy.ServiceProxy('gazebo/reset_simulation', Empty)
        self.unpause_proxy = rospy.ServiceProxy('gazebo/unpause_physics', Empty)
        self.pause_proxy = rospy.ServiceProxy('gazebo/pause_physics', Empty)
        
        # 퍼블리셔
        self.pub_cmd_vel = rospy.Publisher('cmd_vel', Twist, queue_size=5)
        
        # 서브스크라이버
        self.sub_odom = rospy.Subscriber('odom', Odometry, self.getOdometry)
        self.sub_scan = rospy.Subscriber('scan', LaserScan, self.getScanData) # 내가 만든거
        self.scan = LaserScan()
        
    def getScanData(self, scan_msg): # 내가 만든거 
        self.scan = scan_msg        

    def getGoalDistace(self):
        goal_distance = round(math.hypot(self.goal_x - self.position.x, self.goal_y - self.position.y), 4)

        return goal_distance

    def getOdometry(self, odom):
        self.position = odom.pose.pose.position
        orientation = odom.pose.pose.orientation
        orientation_list = [orientation.x, orientation.y, orientation.z, orientation.w]
        _, _, yaw = euler_from_quaternion(orientation_list)

        goal_angle = math.atan2(self.goal_y - self.position.y, self.goal_x - self.position.x)

        heading = goal_angle - yaw
        if heading > pi:
            heading -= 2 * pi

        elif heading < -pi:
            heading += 2 * pi

        #self.heading = round(heading, 2)
        self.heading = heading

    def getState(self, scan, ep):
        scan_range = []        
        heading = self.heading
        min_range = 0.20
        done = False
        arrival = False
        #target_size = 1.0        
        
        if ep<30: target_size = 1.2
        elif (ep>=30 and ep<100): target_size = 0.7
        else: target_size = 0.5

        for i in range(len(scan.ranges)):
            if scan.ranges[i] == float('Inf'):
                scan_range.append(12)
            elif np.isnan(scan.ranges[i]):
                scan_range.append(0)
            else:
                scan_range.append(scan.ranges[i])
                
            
        obstacle_min_range = round(min(scan_range), 2)
        obstacle_angle = np.argmin(scan_range)
        
        if min_range > min(scan_range) > 0:
            done = True

        current_distance = round(math.hypot(self.goal_x - self.position.x, self.goal_y - self.position.y), 2)
        
        #print("obstacle_min_range", obstacle_min_range)
        #print("obstacle_angle", obstacle_angle)
        #print("current: %0.2f, %0.2f" %(self.position.x, self.position.y))
        
        #print("current_distance:",current_distance)
        if current_distance < target_size:
            self.get_goalbox = True
            arrival = True
            # done = True
            
        boundary = math.sqrt(pow(self.position.x,2) + pow(self.position.y,2))
        if boundary > 10:
            #done = False
            done = True
            
        #print("laser scan:",scan_range)

        #return scan_range + [heading, current_distance, obstacle_min_range, obstacle_angle], done
        state = [heading, current_distance, obstacle_min_range, obstacle_angle]
        #print("state", state)
        return state, done, arrival 

    def setReward(self, state, done, action):
    
        yaw_reward = []
        
        obstacle_angle = state[3]
        obstacle_min_range = state[2]
        current_distance = state[1]
        heading = state[0]      
        
        
        #angular_rate = abs(action[0])/1.5       
        #linear_rate  = action[1]/0.5
        
        #angular_reward = -2*angular_rate + 2
        #linear_reward  =  2*linear_rate
        #action_reward  = angular_reward + linear_reward
        
        if (obstacle_min_range < 0.6):
            obstacle_reward = -20/(obstacle_min_range+0.0001)
        else:
            obstacle_reward = 0.0
            
        lin_vel_rate = action[1]/0.5
        ang_vel_rate = abs(action[0])/1.5 
        lin_vel_reward = 3*lin_vel_rate
        ang_vel_reward = -2*ang_vel_rate+2
        action_reward = ang_vel_reward + lin_vel_reward
        
        distance_rate = (current_distance / (self.goal_distance+0.0000001))
        distance_reward = -10*distance_rate+10 if distance_rate<=1 else 1
        
        angle_rate = 2*abs(heading)/pi
        angle_reward = -10*angle_rate+10 if angle_rate<=1 else -5*angle_rate+5
        
        #time_reward = -self.time_step/20
        #time_reward = 1/(self.time_step +1)
        
        reward = distance_reward * angle_reward + obstacle_reward
        
        if done:
            #rospy.loginfo("Collision!")
            reward = -5000
            self.time_step = 0
            self.pub_cmd_vel.publish(Twist())

        if self.get_goalbox:
            rospy.loginfo("Goal!!")
            reward = 4000
            self.pub_cmd_vel.publish(Twist())
            self.delete = True
            #self.goal_x, self.goal_y = self.RespawnGoal.goal_def(self.delete)
            self.goal_x, self.goal_y = goal_def() #4.5, 4.5 # goal_def()
            print("NEXT GOAL : ", self.goal_x, self.goal_y )
            self.goal_distance = self.getGoalDistace()
            self.get_goalbox = False
            self.time_step = 0
            time.sleep(0.2)
            
        #print("total Reward:%0.3f"%reward, "\n")
        #print("Reward : ", reward)
        
        return reward

    def step(self, action, ep):
        
        self.time_step += 1
        
        vel_cmd = Twist()
        vel_cmd.linear.x  =  action[1] #0.5
        vel_cmd.angular.z = action[0]  # action
        self.pub_cmd_vel.publish(vel_cmd)
        
        #print("EP:", ep, " Step:", t, " Goal_x:",self.goal_x, "  Goal_y:",self.goal_y)
        
        state, done, arrival = self.getState(self.scan, ep)
        reward = self.setReward(state, done, action)
        
        return np.asarray(state), reward, done, arrival 

    def reset(self, ep):
    
        self.time_step = 0
        
        rospy.wait_for_service('gazebo/reset_simulation')
        time.sleep(0.1)
        try:
            self.reset_proxy()
            time.sleep(0.2)
        except (rospy.ServiceException) as e:
            print("gazebo/reset_simulation service call failed")
            
        while True:
            if (len(self.scan.ranges) > 0):
                break
        #error_data = self.line_error
        self.goal_distance = self.getGoalDistace()
        state, done, _ = self.getState(self.scan, ep)
             
        

        return np.asarray(state)
        
        
        
        
     
