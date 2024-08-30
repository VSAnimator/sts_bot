# Things to install

```
pip install flask dataset
```

# How to launch the interface

```
python app.py
```

The interface will be available at http://127.0.0.1:5000/

# How to label

For each of 7 game playthroughs, you first load the playthrough by selecting from the seed dropdown and clicking "Load Trajectory". Then, click Display State to display the first step in the trajectory. The goal is to label one of the choices from "Choice List" for each step_id in the trajectory.

The interface will display the choices available at every nontrivial metagame decision. For each metagame decision, you can move between states with the previous/next buttons. Please click on the option from "Choice List" that is the best metagame decision for the state--but don't click anything if you are unsure! Clicking on a particular choice will both store the information to labeling.db and also write your labeling choice to labeled_states.log. This choice will be reflected via green highlight in the interface--and can be changed by clicking on a different choice.  

# When you're done

Please send me both labeling.db and labeled_states.log