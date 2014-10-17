# This is the main skeleton of the neural network - it really only needs the input size, 
# the output size, and the hidden nodes per layer to get set up - the activation functions, 
# cost functions, gradient (bprop) functions, etc should be set-up in the subclasses, because
# these are what give rise to the variations in neural network architectures. Sparse autoencoders, 
# RBMs, multilayer softmax nets, even logistic/softmax regression, are all essentially neural
# networks under the hood. 

import numpy as np
import matplotlib.pyplot as plt
import nnetutils as nu
import nnetoptim as nopt
import scipy.optimize
import cPickle

class Network(object):

	def __init__(self,d=None,k=None,n_hid=None):

		# network parameters
		self.n_nodes = [d]+n_hid+[k] # number of nodes in each layer
		self.act = (len(self.n_nodes)-1)*[None] # activations for each layer (except input)
		if all(node for node in self.n_nodes): # triggers only if all values in self.nodes are not of type NoneType
			self.set_weights(method='alt_random')


	def set_weights(self,method='alt_random',wts=None):
		'''Sets the weights of the neural network based on the specified method
		
		Parameters:
		-----------
		method: sets the weights based on a specified method
				string (optional, default = random)

		wts:	custom weights
				list of numpy ndarrays (optional, default = None)

		Returns:
		--------
		None

		Updates:
		--------
		self.wts_

		'''
		if not wts:
			self.wts_ = (len(self.n_nodes)-1)*[None]

			# standard random initialization for neural network weights
			if method=='random':
				for i,(n1,n2) in enumerate(zip(self.n_nodes[:-1],self.n_nodes[1:])):
					self.wts_[i] = 0.005*np.random.rand(n1+1,n2)

			# andrew ng's suggested method in the UFLDL tutorial
			elif method=='alt_random':
				for i,(n1,n2) in enumerate(zip(self.n_nodes[:-1],self.n_nodes[1:])):
					v = np.sqrt(6./(n1+n2+1))
					self.wts_[i] = 2.0*v*np.random.rand(n1+1,n2) - v
			
			# mainly useful for testing/debugging purposes
			elif method=='fixed':
				last_size=0
				for i,(n1,n2) in enumerate(zip(self.n_nodes[:-1],self.n_nodes[1:])):
					curr_size = (n1+1)*n2
					self.wts_[i] = (0.1*np.cos(np.arange(curr_size)+last_size)).reshape((n1+1,n2))
					last_size = curr_size
		else:
			self.wts_ = wts

	def fit(self,X=None,y=None,x_data=None,method='L-BFGS-B',n_iter=1000,learn_rate=0.75,alpha=0.9):
		'''Fits the weights of the neural network

		Parameters:
		-----------
		X:	data matrix
			numpy d x m ndarray, d = # of features, m = # of samples
		
		y:	targets (labels)
			numpy k x m ndarray, k = # of classes, m = # of samples

		x_data:	mini-batch data iterator
				generator

		methods:	

		Returns:
		--------
		None
	
		Updates:
		--------
		self.wts_	
		'''
		if not X:
			m = X.shape[1]
			X = np.vstack((np.ones([1,m]),X))

		w0 = nu.unroll(self.wts_)
		if method == 'CG':
			wf = scipy.optimize.minimize(self.compute_cost_grad,w0,args=(X,y),method='CG',jac=True,options={'maxiter':n_iter})
			self.wts_ = nu.reroll(wf.x,self.n_nodes)
		
		elif method == 'L-BFGS-B':
			wf = scipy.optimize.minimize(self.compute_cost_grad,w0,args=(X,y),method='L-BFGS-B',jac=True,options={'maxiter':n_iter})
			self.wts_ = nu.reroll(wf.x,self.n_nodes)
		
		elif method == 'gradient_descent':
			if not X and not y:
				self.wts_ = nopt.gradient_descent(self.wts_,self.update_network,X,y,n_iter=n_iter,learn_rate=learn_rate)
			elif x_data:
				self.wts_ = nopt.gradient_descent(self.wts_,self.update_network,x_data=x_data,n_iter=n_iter,learn_rate=learn_rate)

		elif method == 'momentum':
			if not X and not y:
				self.wts_ = nopt.momentum(self.wts_,self.update_network,X,y,n_iter=n_iter,learn_rate=learn_rate,alpha=alpha)
			
			elif x_data:
				self.wts_ = nopt.momentum(self.wts_,self.update_network,x_data=x_data,n_iter=n_iter,learn_rate=learn_rate,alpha=alpha)

		elif method == 'improved_momentum':
			if not X and not y:
				self.wts_ = nopt.improved_momentum(self.wts_,self.update_network,X,y,n_iter=n_iter,learn_rate=learn_rate,alpha=alpha)	
			elif x_data:
				self.wts_ = nopt.improved_momentum(self.wts_,self.update_network,x_data=x_data,n_iter=n_iter,learn_rate=learn_rate,alpha=alpha)
		else:
			print 'Method does not exist, check your code'

		return self
	
	def compute_activations(self,_X,wts=None):
		'''Performs forward propagation and computes and stores intermediate activation values'''
		
		if not wts:
			wts = self.wts_
		m = _X.shape[1] # number of training cases
		ones = np.ones([1,m]) # a row of ones gets appended often, make just once
		self.act[0] = self.activ[0](np.dot(wts[0].T,_X)) # use the first data matrix to compute the first activation
		if len(wts) > 1: # wts = 1 refers to softmax regression
			self.act[0] = np.vstack((ones,self.act[0]))
			for i,w in enumerate(wts[1:-1]):
				self.act[i+1] = np.vstack((ones,self.activ[i+1](np.dot(w.T,self.act[i])))) # sigmoid activations
			self.act[-1] = self.activ[-1](np.dot(wts[-1].T,self.act[-2]))

	# the following methods are 'conveninence' functions needed for various optimization methods that are called
	# by the fit method 

	def compute_cost_grad(self,w,_X,y):
		''' convenience function for scipy.optimize.minimize() '''
		wts = nu.reroll(w,self.n_nodes)
		self.compute_activations(_X,wts)
		cost = self.compute_cost(y,wts)
		grad = nu.unroll(self.compute_grad(_X,y,wts))

		return cost,grad
	
	def update_network(self,_X,y,wts=None):
		''' convenience function for mini-batch optimization methods, e.g., 
		gradient_descent, momentum, improved_momentum'''
		
		if not wts:
			wts = self.wts_
		self.compute_activations(_X,wts)
		dE = self.compute_grad(_X,y,wts)
		
		return self.compute_grad(_X,y,wts)

	def reset(self,method='alt_random'):
		''' resets the weights of the network - useful for re-use'''
		self.set_weights(method=method)

	def save_network(self,save_path):
		''' serializes the model '''

		f = open(save_path,'wb')
		cPickle.dump(self.__dict__,f,2)
		f.close()

	def load_network(self,load_path):
		''' loads a serialized neural network, given a path'''

		f = open(load_path,'r')
		tmp_dict = cPickle.load(f)
		f.close()
		self.__dict__.update(tmp_dict)
		
	# Plotting function
	# def plot_error_curve(self):
	# 	'''Plots the error at each iteration'''
		    
	# 	plt.figure()
	# 	iter_idx = range(len(self.cost_vector))
	# 	print 'Final Error: ',self.cost_vector[-1]
	# 	plt.plot(iter_idx,self.cost_vector)
	# 	plt.title('Error Curve')
	# 	plt.xlabel('Iter #')
	# 	plt.ylabel('Error')