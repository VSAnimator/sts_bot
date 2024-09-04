import gymnasium as gym
import copy

env = gym.make("MountainCar-v0")#, render_mode="human")
observation, info = env.reset()

for _ in range(1000):
    print("Observation: ", observation)
    cart_position = observation[0]
    action = 1 if cart_position < 0 else 0
    action_options = [0, 1, 2]
    for action in action_options:
        action_env = copy.deepcopy(env)
        action_observation, _, _, _, _ = action_env.step(action)
        print("State option " + str(action) + ": ", action_observation)
    action = (int)(input("Action..."))
    observation, reward, terminated, truncated, info = env.step(action)
    print("Action: ", action)
    if terminated or truncated:
        break
        observation, info = env.reset()
env.close()