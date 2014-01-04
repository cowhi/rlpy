"""
Cart-pole balancing with independent discretization
"""
from Tools import Logger
from Domains import PuddleWorld
from Agents import Q_Learning
from Representations import *
from Experiments import Experiment
from hyperopt import hp
import numpy as np
from Domains import PuddleWorld
from Policies import BasicPuddlePolicy
from ValueEstimators.Forest import Forest
from Experiments.PolicyEvaluationExperiment import PolicyEvaluationExperiment

param_space = {"learn_rate_coef": hp.loguniform("learn_rate_coef", np.log(1e-2), np.log(1e0)),
               'm': hp.loguniform("m", np.log(1e0), np.log(1e2)),
               'grow_coef': hp.loguniform("grow_coef", np.log(1e1), np.log(1e2)),
               'learn_rate_exp': hp.uniform("learn_rate_exp", -0.1, -.01),
               'grow_exp': hp.loguniform("grow_exp", 1.00000001, 1.1)}


def make_experiment(id=1, path="./Results/Temp/{domain}/poleval/forest10_precut",
                    learn_rate_coef=0.1,
                    learn_rate_exp=-0.05, #13444,  #-0.04,
                    grow_coef=25,
                    grow_exp=1.05, #0001,
                    p_structure=0.05,
                    m=20):
    logger = Logger()
    max_steps = 2000000
    num_policy_checks = 20
    checks_per_policy = 100

    domain = PuddleWorld(logger=logger)
    pol = BasicPuddlePolicy(domain, None)
    forest = Forest(domain, None, num_trees=10, m=m, p_structure=p_structure,
                    grow_coef=grow_coef, grow_exp=grow_exp, learn_rate_mode="exp",
                    learn_rate_coef=learn_rate_coef, learn_rate_exp=learn_rate_exp, precuts=16)
    experiment = PolicyEvaluationExperiment(forest, domain, pol, max_steps=max_steps, num_checks=20, path=path, id=id, log_interval=10)

    return experiment

if __name__ == '__main__':
    experiment = make_experiment(1)
    experiment.run(visualize_learning=False)
    experiment.plot(y="rmse")
