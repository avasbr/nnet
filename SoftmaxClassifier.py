import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import fmin_cg,fmin_l_bfgs_b
import nnetutils as nu
import NeuralNetworkCore

class SoftmaxClassifier(NeuralNetworkCore.Network):
	
	def __init__(self,d=None,k=None,n_hid=[25],decay=0.0001):
		
		# softmax classifier has sigmoid activations for the intermediate
		# layers, and a final softmax layer
		activ = len(n_hid)*[nu.sigmoid]
		activ.append(nu.softmax)
		
		# set the parameters of the superclass
		NeuralNetworkCore.Network.__init__(self,d=d,k=k,n_hid=n_hid,activ=activ,
			cost=self.cost, bprop=self.bprop)

		# set hyperparameters
		self.decay = decay # regularization coefficient

	def cost(self,y,wts=None):
		''' Cross-entropy: mean(-1.0*y_true*log(y_pred))'''
		
		if not wts:
			wts = self.wts_

		#  E = 1/N*sum(-y*log(p)) - negative log probability of the right answer
		E = np.mean(np.sum(-1.0*y*np.log(self.act[-1]),axis=0)) + 0.5*self.decay*sum([np.sum(w**2) for w in wts])

		return E

	def bprop(self,_X,y,wts=None):
		'''Back-propagation for L2-regularized '''

		if not wts:
			wts = self.wts_

		# reversing the lists makes it easier to work with 					
		wts = wts[::-1]
		act = self.act[::-1]

		m = _X.shape[1]
		dE_dW = []
		
		# the final layer is a softmax, so calculate the derivative with respect to 
		# the inputs to the softmax first
		dE_dz = act[0]-y
		
		for i,a in enumerate(act[1:]):
			dE_dW.append(1.0/m*np.dot(a,dE_dz.T) + self.decay*wts[i])
			dE_da = np.dot(wts[i],dE_dz)
			dE_dz = (dE_da*a*(1-a))[1:] # no connection to the bias node
		
		dE_dW.append(1.0/m*np.dot(_X,dE_dz.T) + self.decay*wts[-1])

		# re-reverse and return
		return dE_dW[::-1]

	def predict(self,X,y=None):
		'''One-line description
		
		Parameters:
		-----------
		X:
		y:
		
		Returns:
		--------
		pred:
		mce:
		'''
		m = X.shape[1]
		X = np.append(np.ones([1,m]),X,axis=0)
		self.fprop(X)
		pred = np.argmax(self.act[-1],axis=0) # only the final activation contains the 
		
		if not y:
			return pred
		mce = 1.0-np.mean(1.0*(pred==np.argmax(y,axis=0)))
		
		return pred,mce