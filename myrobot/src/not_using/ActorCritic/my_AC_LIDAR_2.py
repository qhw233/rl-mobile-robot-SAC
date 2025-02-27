#!/usr/bin/env python3


import rospy
import os
import json
import numpy as np
import matplotlib.pyplot as plt
import random
import time
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from collections import deque
from collections import namedtuple
from std_msgs.msg import Float32MultiArray
from ActorCritic.env_AC_LIDAR import Env
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.autograd import Variable
from torch.distributions import Categorical
from torch.distributions import Normal

from torch.utils.tensorboard import SummaryWriter
writer = SummaryWriter('AC_log/0913/reduce_state_4')


USE_CUDA = torch.cuda.is_available()
device = torch.device('cuda:0' if USE_CUDA else 'cpu')
#device = torch.device("cpu")
print('DEVICE:',device)






class Actor(nn.Module):
    def __init__(self, state_size, action_size, action_bound, learning_rate):
        super(Actor, self).__init__()
        self.state_size = state_size
        self.action_size = action_size
        self.action_bound = action_bound
        self.learning_rate = learning_rate
        self.loss = 0.0

        self.std_bound = [1e-2, 0.99]
        
        self.fc1 = nn.Linear(self.state_size, 128)       
        self.bn1 = nn.BatchNorm1d(128)
        self.drp1 = nn.Dropout(0.2) 
        nn.init.kaiming_normal_(self.fc1.weight)
        #nn.init.xavier_uniform(self.fc1.weight)
        
        self.fc2 = nn.Linear(128, 64)       
        self.bn2 = nn.BatchNorm1d(64) 
        self.drp2 = nn.Dropout(0.2) 
        nn.init.kaiming_normal_(self.fc2.weight)
        #nn.init.xavier_uniform(self.fc2.weight)
        
        self.fc3 = nn.Linear(64, 32)       
        self.bn3 = nn.BatchNorm1d(32) 
        nn.init.kaiming_normal_(self.fc3.weight)
        #nn.init.xavier_uniform(self.fc3.weight)
             
        self.fc_mu = nn.Linear(32, self.action_size)
        #nn.init.kaiming_normal_(self.fc_mu.weight) 
        nn.init.xavier_uniform_(self.fc_mu.weight)
        
        self.fc_std = nn.Linear(32, self.action_size)
        #nn.init.kaiming_normal_(self.fc_std.weight)
        nn.init.xavier_uniform_(self.fc_std.weight)
        
        self.tanh = nn.Tanh()
        self.softplus = nn.Softplus()
        
        self.optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)

    def forward(self, state):
        x = F.leaky_relu(self.bn1(self.fc1(state)))
        x = self.drp1(x)
        
        x = F.leaky_relu(self.bn2(self.fc2(x)))
        x = self.drp2(x)
        
        x = F.leaky_relu(self.bn3(self.fc3(x)))
        
        mu = self.tanh(self.fc_mu(x))
        std = self.softplus(self.fc_std(x))    
        
        return mu * self.action_bound, std





class Critic(nn.Module):
    def __init__(self, state_size, action_size, learning_rate):
        super(Critic, self).__init__()

        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.loss = 0.0

        self.fc1 = nn.Linear(self.state_size, 128) #300dldjTdma       
        self.bn1 = nn.BatchNorm1d(128)
        self.drp1 = nn.Dropout(0.2) 
        nn.init.kaiming_normal_(self.fc1.weight)
        
        self.fc2 = nn.Linear(128, 128)       
        self.bn2 = nn.BatchNorm1d(128) 
        self.drp2 = nn.Dropout(0.2) 
        nn.init.kaiming_normal_(self.fc2.weight)
        
        self.fc3 = nn.Linear(128, 64)       
        self.bn3 = nn.BatchNorm1d(64) 
        self.drp3 = nn.Dropout(0.2) 
        nn.init.kaiming_normal_(self.fc3.weight)
             
        self.fc_out = nn.Linear(64, self.action_size)
        nn.init.kaiming_normal_(self.fc_out.weight)
        
        self.optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)

    def forward(self, state):
        x = F.leaky_relu(self.bn1(self.fc1(state)))
        x = self.drp1(x)
        
        x = F.leaky_relu(self.bn2(self.fc2(x)))
        x = self.drp2(x)
        
        x = F.leaky_relu(self.bn3(self.fc3(x)))
        x = self.drp3(x)
        
        v = F.leaky_relu(self.fc_out(x)) 

        return v



class A2CAgent:

    def __init__(self):    
    
        self.GAMMA = 0.99       
        self.ACTOR_LR  = 0.00005
        self.CRITIC_LR = 0.00025       
        self.EPISODE = 10000
        self.MAX_STEP_SIZE = 20000
        self.BATCH_SIZE = 100
        self.SAMPLING_RATE = 20        
        
        self.state_size = 4    # 109 # 
        self.action_size = 1   # (continuous)
        self.action_bound = 1.5
        
        self.data = []
        
        self.actor = Actor(self.state_size, self.action_size, self.action_bound, self.ACTOR_LR).to(device)
        self.critic = Critic(self.state_size, self.action_size, self.CRITIC_LR).to(device)
    
    def put_data(self, transition):
        self.data.append(transition)    
    
    def make_batch(self):
        s_lst, a_lst, r_lst, s_next_lst, done_lst = [], [], [], [], []
        for transition in self.data:
            s, a, r, s_next, done = transition
            s_lst.append(s)
            a_lst.append([a])
            r_lst.append([r])  # r_lst.append([r/100])
            s_next_lst.append(s_next)
            done_mask = 0.0 if done else 1.0
            done_lst.append([done_mask])

        s_batch       = torch.FloatTensor(    s_lst   ).to(device)
        a_batch       = torch.FloatTensor(    a_lst   ).to(device)
        r_batch       = torch.FloatTensor(    r_lst   ).to(device)
        s_next_batch  = torch.FloatTensor( s_next_lst ).to(device)
        done_batch    = torch.FloatTensor(  done_lst  ).to(device)
        self.data = []
        return s_batch, a_batch, r_batch, s_next_batch, done_batch


    def get_action(self, state):
        self.actor.eval()
        with torch.no_grad():
            mu, std = self.actor(state)
            mu, std = mu.item(), std.item()
        std = np.clip(std,self.actor.std_bound[0], self.actor.std_bound[1])
        action = np.random.normal(mu, std)
        action = np.clip(action,-self.actor.action_bound, self.actor.action_bound)
        # action = torch.FloatTensor([action]).to(device)
        return float(action)
        
        
    def get_TD_error_TD_target(self, state, next_state, reward, done):
        self.critic.eval()
        with torch.no_grad():
            v = self.critic(state)
            next_v = self.critic(next_state)
        TD_target = reward + self.GAMMA*next_v*done
        TD_error = TD_target - v
        
        return TD_error, TD_target
        
        
    def train_actor(self, state, action, TD_error):
        self.actor.train()
        
        mu, std = self.actor(state)
        dist = Normal(mu, std)
        log_prob = dist.log_prob(action)
        
        self.actor.loss = torch.mean(-log_prob*TD_error)
        
        self.actor.optimizer.zero_grad()
        self.actor.loss.backward()
        self.actor.optimizer.step()
        
        return self.actor.loss
        
        
    def train_critic(self, state, TD_target):
        self.critic.train()
        
        predict = self.critic(state)
        self.critic.loss = torch.mean((TD_target-predict)**2)
        #self.critic.loss = nn.MSELoss(TD_target, predict)
        
        self.critic.optimizer.zero_grad()
        self.critic.loss.backward()
        self.critic.optimizer.step()
        
        return self.critic.loss
            

if __name__ == "__main__":
    rospy.init_node('mobile_robot_AC')    
    
    agent = A2CAgent()
    env = Env(agent.action_size)
    time.sleep(2)
    
    actor_loss, critic_loss, score = 0.0, 0.0, 0.0
    for episode in range(agent.EPISODE):   
        
        done = False
        episode_score = 0.0
        s = env.reset(episode)
        #s = torch.FloatTensor([s]).to(device) #s=tensor([[2,3,4,100]])
        
        for step in range(agent.MAX_STEP_SIZE):
            
            #for i in range(agent.BATCH_SIZE):
            # if len(agent.data) < agent.BATCH_SIZE:
            a = agent.get_action(torch.FloatTensor([s]).to(device)) 
            s_next, r, done = env.step(a, episode, step)
            
            if step % agent.SAMPLING_RATE == 0:
                agent.put_data((s, a, r, s_next, done))
                
            s = s_next
            episode_score += r
            if done:
                s = env.reset(episode)
                #s = torch.FloatTensor([s]).to(device)
                    
            if len(agent.data) >= agent.BATCH_SIZE:
                s_batch, a_batch, r_batch, s_next_batch, done_batch = agent.make_batch()
                    
                td_error, td_target = agent.get_TD_error_TD_target(s_batch, s_next_batch, r_batch, done_batch)
                
                actor_loss = agent.train_actor(s_batch, a_batch, td_error)
                critic_loss = agent.train_critic(s_batch, td_target)
                
                print("EP:", episode, " Score:", episode_score, " actor_loss:", actor_loss.item(), " critic_loss:", critic_loss.item())
                
    
        print("EP:", episode, " Score:", episode_score, " actor_loss:", actor_loss.item(), " critic_loss:", critic_loss.item())

    print("종료")
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
     
    













