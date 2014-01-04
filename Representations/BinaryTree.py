from Representations import Representation
import numpy as np
import warnings
from copy import deepcopy
import matplotlib.pyplot as plt

class Tree(Representation.Representation):

    def __init__(self, domain, logger, p_structure=.05, m=100, lam=2000, kappa=0.1,
                 learn_rate_coef=0.1, learn_rate_exp=-0.05, learn_rate_mode="boyan", grow_coef=25, grow_exp=1.1,
                 beta_coef=4, precuts=None, random_seed=0):
        self.random_state = np.random.RandomState(seed=random_seed)
        self.p_structure = p_structure
        self.m = m
        self.lam = lam
        self.kappa = kappa
        self.learn_rate_coef = learn_rate_coef
        self.learn_rate_exp = learn_rate_exp
        self.num_dim = domain.state_space_dims
        self.grow_coef = grow_coef
        self.grow_exp = grow_exp
        self.beta_coef = beta_coef
        self.gamma = domain.gamma
        self.learn_rate_mode = learn_rate_mode
        self.t = 0
        self.depth = 1
        self.root = Node(self, 1, leaf_id=1)
        self.num_nodes = 1
        self.num_leafs = 1
        self.nodelist = [self.root]
        self.domain = domain
        self.num_episodes = 0
        if precuts is not None:
            if precuts % 2 != 0:
                warnings.warn("precuts only possible in multiples of 2")
            stride = (domain.statespace_limits[:,1] - domain.statespace_limits[:,0]) / precuts
            cuts = np.outer(np.arange(1, precuts), stride).T.tolist()
            # add dimension ids
            cuts = list(enumerate(cuts))
            self.precutting(self.root, cuts)

    def precutting(self, node, cuts):
        #import ipdb
        #ipdb.set_trace()
        if len(cuts) < 1:
            return
        d, lst = cuts[0]
        mid = len(lst) / 2
        v = lst[mid]
        lst1 = lst[:mid]
        lst2 = lst[mid + 1:]
        if len(lst1):
            cuts1 = [(d,lst1)] + deepcopy(cuts[1:])
        else:
            cuts1 = deepcopy(cuts[1:])
        if len(lst2):
            cuts2 = [(d,lst2)] + deepcopy(cuts[1:])
        else:
            cuts2 = deepcopy(cuts[1:])
        node.split_node(d, v)
        self.precutting(node.left, cuts1)
        self.precutting(node.right, cuts2)

    def update_depth(self, depth):
        self.depth = max(depth, self.depth)

    def next_id(self):
        self.num_nodes += 1
        return self.num_nodes

    def add_node(self, node):
        self.nodelist.append(node)
        assert(len(self.nodelist) == self.num_nodes)
        self.num_leafs = sum([1 if n.leaf else 0 for n in self.nodelist])
        self.update_depth(node.depth)

    @property
    def features_num(self):
        return self.num_leafs

    def learn(self, s, r, ns, terminal):
        structure_point = self.random_state.rand() < self.p_structure
        if not structure_point:
            self.t += 1
        return self.root.descent(s).learn(s, r, ns, terminal=terminal, structure_point=structure_point)

    def predict(self, s, terminal=False):
        if terminal:
            return 0.
        return self.root.descent(s).value

    def predict_id(self, s, terminal=False):
        return self.root.descent(s).id

    def predict_leaf_id(self, s, terminal=False):
        return self.root.descent(s).leaf_id

    @property
    def theta(self):
        res = np.array([n.value for n in self.nodelist])
        return res

    def output(self):
        print "Nodes:", self.features_num
        print "Depth:", self.depth

    def plot_2d_cuts(self):
        if self.num_dim != 2:
            warnings.warn("Plotting the decision boundaries of tree only supported for 2d domains")
            return

        lim = self.domain.statespace_limits.copy()
        return self._plot_node_cuts(self.root, lim)

    def _plot_node_cuts(self, node, lim):
        if node.leaf:
            return
        if node.split_d == 0:
            plt.vlines(node.split_val, lim[1,0], lim[1,1])
            lim1 = lim.copy()
            lim1[0, 1] = min(lim[0,1], node.split_val)
            self._plot_node_cuts(node.left, lim1)
            lim2 = lim.copy()
            lim2[0, 0] = max(lim[0,0], node.split_val)
            self._plot_node_cuts(node.right, lim2)
        else:
            plt.hlines(node.split_val, lim[0,0], lim[0,1])
            lim1 = lim.copy()
            lim1[1, 1] = min(lim[1,1], node.split_val)
            self._plot_node_cuts(node.left, lim1)
            lim2 = lim.copy()
            lim2[1, 0] = max(lim[1,0], node.split_val)
            self._plot_node_cuts(node.right, lim2)

    def episodeTerminated(self):
        self.num_episodes += 1


class Node(object):

    depth = 0
    right = None
    left = None
    value = 0.
    tree = None


    def __init__(self, tree, id=-1, value=0., depth=1, leaf_id=-2):
        self.value = value
        self.depth = depth
        if id == -1 and tree is not None:
            id = tree.next_id()
            if leaf_id is -1:
                leaf_id = tree.num_leafs
            tree.add_node(self)

        self.id = id
        self.leaf_id = leaf_id
        self.tree = tree
        m = self.tree.m
        d = min(1 + self.tree.random_state.poisson(self.tree.lam), self.tree.num_dim)
        self.structure_count = 0
        self.struct_st = 0.
        self.struct_stsq = 0.
        self.cand_split_dim = self.tree.random_state.permutation(np.arange(self.tree.num_dim))[:d]
        self.cand_split_st = np.zeros((d, m, 2))
        self.cand_split_val = np.zeros((d, m))
        self.cand_split_stsq = np.zeros((d, m, 2))
        self.cand_split_count = np.zeros((d, m, 2), dtype="int")

    @property
    def leaf(self):
        return self.right is None and self.left is None

    def output(self, recursive=True):
        print "Node ID", self.id
        print "\tLeaf", self.leaf
        print "\tValue", self.value
        if not self.leaf:
            print "\tSplit s[", self.split_d, "] <= ", self.split_val
            print "\tLeft: Node", self.left.id, ",\tRight: Node", self.right.id
        print "\tDepth", self.depth
        print "\tStructure points seen", self.structure_count
        print "\tCand split dim", self.cand_split_dim
        if recursive and not self.leaf:
            self.left.output(recursive)
            self.right.output(recursive)

    def descent(self, s):
        if self.leaf:
            return self
        if s[self.split_d] < self.split_val:
            return self.left.descent(s)
        else:
            return self.right.descent(s)

    def learn(self, s, r, ns, terminal, structure_point=False):
        if structure_point:
            # structure stream
            return self._learn_structure(s, r, ns, terminal)
        else:
            return self._learn_estimation(s, r, ns, terminal)

    def alpha(self):
        return self.tree.grow_coef * (self.tree.grow_exp)**self.depth

    def beta(self):
        return self.tree.beta_coef * self.alpha()

    def mu(self):
        """learning rate for updating the value estimate"""
        # boyan scheme
        if self.tree.learn_rate_mode is "boyan":
            return self.tree.learn_rate_coef * (self.tree.learn_rate_exp + 1.) / (self.tree.learn_rate_exp + (self.tree.num_episodes + 1) ** 1.1)
        else:
            return self.tree.learn_rate_coef * self.tree.t**self.tree.learn_rate_exp

    def _learn_estimation(self, s, r, ns, terminal):
        """improve estimation value based on this observation in this node
        only called in leafs"""
        delta = r + self.tree.gamma * self.tree.predict(ns, terminal=terminal) - self.value
        self.value += delta * self.mu()
        assert np.isfinite(self.value)

    def split_node_from_candidates(self, dimension_id, split_id):
        split_d = self.cand_split_dim[dimension_id]
        split_val = self.cand_split_val[dimension_id, split_id]
        return self.split_node(split_d, split_val)

    def split_node(self, split_d, split_val):
        self.split_d = split_d
        self.split_val = split_val
        # create children
        self.left = Node(self.tree, -1, self.value, self.depth + 1, self.leaf_id)
        self.right = Node(self.tree, -1, self.value, self.depth + 1, -1)
        self.leaf_id = -1
        del self.cand_split_count
        del self.cand_split_stsq
        del self.cand_split_st
        del self.cand_split_val
        del self.cand_split_dim

    def _learn_structure(self, s, r, ns, terminal):
        i = self.structure_count
        # add candidate splits if not enough available
        if i < self.tree.m:
            for j in xrange(self.cand_split_val.shape[0]):
                self.cand_split_val[j, i] = s[self.cand_split_dim[j]]
        if i == self.tree.m:
            pass
            # all splits are generated
            # update stats for splits based on previous data

        # update split status
        val = r + self.tree.gamma * self.tree.predict(ns)
        assert(not np.isnan(val))
        self.struct_st += val
        self.struct_stsq += val ** 2
        self.structure_count += 1

        decision = (s[self.cand_split_dim][:,None] > self.cand_split_val).astype("int")
        self.cand_split_st[:,:,0] += (1 - decision) * val
        self.cand_split_st[:,:,1] += decision * val
        self.cand_split_stsq[:,:,0] += (1 - decision) * val ** 2
        self.cand_split_stsq[:,:,1] += decision * val ** 2
        self.cand_split_count[:,:,0] += (1 - decision)
        self.cand_split_count[:,:,1] += decision

        # compute reduction in variance for each split
        exp = self.cand_split_st / self.cand_split_count
        var = self.cand_split_stsq / self.cand_split_count - exp ** 2
        wvar = self.cand_split_count * var
        ss = self.cand_split_count.sum(axis=2)
        wvar = wvar.sum(axis=2)
        wvar[ss > 0] /= ss[ss > 0]
        objective = self.struct_stsq / self.structure_count - (self.struct_st / self.structure_count) ** 2 - wvar
        objective[np.any(self.cand_split_count < self.alpha(), axis = 2)] = -np.inf
        assert(not np.any(np.isnan(objective)))
        # find biggest reduction
        a, b = np.unravel_index(np.nanargmax(objective), objective.shape)

        #for j in xrange(self.cand_split_val.shape[0]):
        #    for k in xrange(self.root.m):
        #        print self.cand_split_val[j, k], objective[j, k]

        if objective[a, b] > self.tree.kappa or (i > self.beta() and np.isfinite(objective[a, b])):
            # I've seen enough! Split, bitch!
            #import ipdb;ipdb.set_trace()
            self.split_node_from_candidates(a, b)

    def phi_nonTerminal(self, s):
        if self != self.root:
            return self.root.phi_nonTerminal(s)
        res = np.zeros(self.features_num)
        res[self.prediction_id(s)] = 1.
        return res

    def featureType(self):
        return bool

