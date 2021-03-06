import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import fmin_cg,fmin_l_bfgs_b
from nnet.common import nnetutils as nu
from nnet import NeuralNetworkCore
from nnet import SoftmaxClassifier as scl
from nnet import Autoencoder as ae

class DeepAutoencoderClassifier(NeuralNetworkCore.Network):

	def __init__(self,d=None,k=None,n_hid=None,sae_decay=None,scl_decay=None,rho=None,beta=None):
		
		# set up the stacked autoencoders
		self.stacked_ae = len(n_hid)*[None]
		self.stacked_ae[0] = ae.Autoencoder(d=d,n_hid=n_hid[0],decay=sae_decay[0],rho=rho[0],beta=beta[0])
		for i,(n1,n2) in enumerate(zip(n_hid[:-1],n_hid[1:])):
				self.stacked_ae[i+1] = ae.Autoencoder(d=n1,n_hid=n2,decay=sae_decay[i+1],rho=rho[i+1],beta=beta[i+1])

		# define the activation functions for the full network
		self.activ = len(n_hid)*[nu.sigmoid]+[nu.softmax]

		# sets up the full network architecture
		NeuralNetworkCore.Network.__init__(self,d=d,k=k,n_hid=n_hid)

		# define the hyper parameters for fine-tuning
		self.decay = scl_decay

	def pre_train(self,X=None,x_data=None,**optim_params):
		''' Greedy, layer-wise pre-training; currently, the method parameters apply to all layers'''
		
		if X is not None:
			
			# train the first autoencoder
			self.stacked_ae[0].fit(X,**optim_params)
			X_tf = self.stacked_ae[0].transform(X)
			self.wts_[0] = self.stacked_ae[0].wts_[0] # initialize the weights with the encoding weights

			# train the subsequent autoencoders
			for i,ae in enumerate(self.stacked_ae[1:]):
				ae.fit(X_tf,**optim_params)
				self.wts_[i+1] = ae.wts_[0]
				X_tf = ae.transform(X_tf)

	def cost_function(self,y,wts=None,bs=None):
		''' Cross-entropy: mean(-1.0*y_true*log(y_pred))'''
		
		if not wts:
			wts = self.wts_

		# same cost function as for the softmax classifier, but we don't regularize on the weights
		# learned during pre-training
		E = np.mean(np.sum(-1.0*y*np.log(self.act[-1]),axis=0)) + 0.5*self.decay*np.sum(wts[-1][1:]**2) 
		return E
				
	def bprop(self,X,y,wts=None,bs=None):
		'''Back-propagation for L2-regularized cross-entropy cost function'''

		if wts is None and bs is None:
			wts = self.wts_
			bs = self.bs_

		# reversing the lists makes it easier 					
		wts = wts[::-1]
		bs = bs[::-1]
		act = self.act[::-1]

		dE_dW = len(wts)*[None]
		dE_db = len(bs)*[None]

		# the final layer is a softmax, so calculate the derivative with respect to 
		# the inputs to the softmax first
		dE_dz = act[0]-y
		
		m = X.shape[1]
		if len(wts)>1: # wts = 1 means there's no hidden layer = softmax regression
			for i,a in enumerate(act[1:]):
				dE_dW[i] = 1./m*np.dot(dE_dz,a.T) + self.decay*wts[i]
				dE_db[i] = 1./m*np.sum(dE_dz,axis=1)[:,np.newaxis]
				dE_da = np.dot(wts[i].T,dE_dz)
				dE_dz = dE_da*a*(1-a) # no connection to the bias node
		dE_dW[-1] = 1./m*np.dot(dE_dz,X.T) + self.decay*wts[-1]
		dE_db[-1] = 1./m*np.sum(dE_dz,axis=1)[:,np.newaxis]

		return dE_dW[::-1],dE_db[::-1]

	def predict(self,X,y=None):
		'''Runs forward propagation through the network to predict labels, and computes 
		the misclassification rate if true labels are provided
		
		Parameters:
		-----------
		X: data matrix
		   numpy array, d x m
		y: labels
		   numpy array, k x m (optional)
		
		Returns:
		--------
		pred: predictions
			  numpy array, k x m
		mce: misclassification error, if labels were provided
			 float
		'''
		self.fprop(X)
		pred = np.argmax(self.act[-1],axis=0) # only the final activation contains the 
		
		if y is None:
			return pred
		mce = 1.0-np.mean(1.0*(pred==np.argmax(y,axis=0)))		
		return pred,mce