import timesynth as ts
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import expit
from scipy.signal import butter, lfilter, freqz
import pickle as pkl
import os
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import random

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

# Filter requirements.
order = 3
fs = 30.0       # sample rate, Hz
cutoff = 2.6 # desired cutoff frequency of the filter, Hz

# Get the filter coefficients so we can check its frequency response.
b, a = butter_lowpass(cutoff, fs, order)

w, h = freqz(b, a, worN=8000)
plt.subplot(1, 1, 1)
plt.plot(0.5*fs*w/np.pi, np.abs(h), 'b')
plt.plot(cutoff, 0.5*np.sqrt(2), 'ko')
plt.axvline(cutoff, color='k')
plt.xlim(0, 0.5*fs)
plt.title("Lowpass Filter Frequency Response")
plt.xlabel('Frequency [Hz]')
plt.grid()


def main(n_samples, plot, Tt=48):
    signal_in = []
    thresholds = []
    trend_style=[]
    y_vec=[]
    for i in range(n_samples):
        if i%100==0:
            print(i)
        x,t,trend,y = generate_sample(plot, Tt=Tt)
        signal_in.append(x)
        thresholds.append(t)
        trend_style.append(trend)
        y_vec.append(y)

    print('samples done!')
    signal_in = np.array(signal_in)
    y_vec = np.array(y_vec)

    n_train = int(0.8*n_samples)
    x_train = signal_in[0:n_train,:,:]
    thresholds_train = thresholds[0:n_train]

    x_test = signal_in[n_train:,:,:]
    thresholds_test = thresholds[n_train:]
    
    y_train = y_vec[:n_train]
    y_test = y_vec[n_train:]

    scaler = StandardScaler()
    x_train_flat = scaler.fit_transform(np.reshape(x_train,[x_train.shape[0],-1]))
    x_train_n = np.reshape(x_train_flat,x_train.shape)
    x_test_flat = scaler.transform(np.reshape(x_test,[x_test.shape[0],-1]))
    x_test_n = np.reshape(x_test_flat,x_test.shape)

    #x_train_n = x_train
    #x_test_n = x_test
    x1_train_lpf = np.array([x[0,:] for x in x_train_n])
    x2_train_lpf = np.array([butter_lowpass_filter(x[1,:], cutoff, fs, order) if y_train[i] else x[1,:] for i,x in enumerate(x_train_n)])
    #x3_train_lpf = np.array([butter_lowpass_filter(x[2,:], cutoff, fs, order) for x in x_train_n])
    x_train_lpf = np.stack([x1_train_lpf, x2_train_lpf],axis=1)

    x1_test_lpf = np.array([x[0,:] for x in x_test_n])
    x2_test_lpf = np.array([butter_lowpass_filter(x[1,:], cutoff, fs, order) if y_test[i] else x[1,:] for i,x in enumerate(x_test_n)])
    #x3_test_lpf = np.array([butter_lowpass_filter(x[2,:], cutoff, fs, order) for x in x_test_n])
    x_test_lpf = np.stack([x1_test_lpf, x2_test_lpf],axis=1)
    
    x_train_n = x_train_lpf
    x_test_n = x_test_lpf

    ground_truth_importance_train=[]
    for n,x in enumerate(x_train_n):
        gt_t=np.zeros(x.shape[1])
        ground_truth_importance_train.append(np.array(gt_t))
   
    ground_truth_importance_train = np.array(ground_truth_importance_train)

    ground_truth_importance_test=[]
    for n,x in enumerate(x_test_n):
        gt_t=np.zeros(x.shape[1])
        ground_truth_importance_test.append(np.array(gt_t))

    ground_truth_importance_test = np.array(ground_truth_importance_test)
 
    if plot:
        for i in range(x_train_n.shape[0]):
            plt.plot(x_train_n[i,0,:], label='x1')
            plt.plot(x_train_n[i,1,:], label='x2')
            plt.plot(y_train[i])
            plt.title('Sample style: %s'%(trend_style[i]))

            if isinstance(thresholds[i],np.ndarray):
                for thresh in thresholds[i]:
                    plt.axvline(x=thresh, color='grey')
            else:
                plt.axvline(x=thresholds[i], color='grey')

            plt.legend()
            plt.show()

    return x_train_n[:,:,:],y_train,x_test_n[:,:,:],y_test,thresholds_train,thresholds_test, ground_truth_importance_train[:,:], ground_truth_importance_test[:,:]

def generate_sample(plot, Tt=48):
    seed = np.random.randint(1,100)
    noise = ts.noise.GaussianNoise(std=0.01)
    trend_style = {0:'increase', 1:'decrease', 2:'hill', 3:'valley'}
    trend = np.random.randint(4)
    trend = 2
    y = np.random.choice([0,1],1,replace=False,p=[2/3,1/3])[0]

    x1 = ts.signals.NARMA(order=2,coefficients=[.5,.5,1.5,.5],seed=random.seed())
    x1_ts = ts.TimeSeries(x1, noise_generator=noise)
    x1_sample, signals, errors = x1_ts.sample(np.array(range(Tt)))

    
    seed = np.random.randint(1,1000)
    x2 = ts.signals.NARMA(order=2,coefficients=[.5,.5,1.5,.5],seed=random.seed())
    noise = ts.noise.GaussianNoise(std=0.01)
    x2_ts = ts.TimeSeries(x2,noise_generator=None)
    x2_sample,signals,errors = x2_ts.sample(np.array(range(Tt)))
    #x2_sample += 0.04*np.log(coeff[0]*x1_sample + coeff[1]*x1_sample*x1_sample + coeff[2]*x1_sample*x1_sample*x1_sample+0.5
    
    if 0:
        if trend==0 or trend==1:
            t = np.random.randint(20,38)
            x2_sample[t:] = x2_sample[t:] + (1 if trend==0 else -1) * np.log(1.5*np.asarray(range(Tt-t))+1.) 
        elif trend==2 or trend==3:
            t=[]
            t_st = np.random.choice(np.arange(15,30),1)[0]
            t.append(t_st)
            t.append(t_st+2)
            t_end = np.random.choice(np.arange(t_st+6,t_st+6+6),1)[0]
            t_env = t_end-2
            t.append(t_env)
            t.append(t_end)
            t = np.array(t)

            s = +1 if trend==2 else -1
            x2_sample[t[0]:t[1]] = x2_sample[t[0]:t[1]] + s*np.log(0.3*np.asarray(range(t[1]-t[0]))+1.)
            x2_sample[t[1]:t[2]] = x2_sample[t[1]:t[2]] + s * np.log(0.3 * np.full(x2_sample[t[1]:t[2]].shape, (t[1]-t[0])) + 1.)
            x2_sample[t[2]:t[3]] = x2_sample[t[2]:t[3]] - s*np.log(0.3*np.asarray(range(t[3]-t[2]))+1.)
    
    
    noise = ts.noise.GaussianNoise(std=0.01)
    x3 = ts.signals.NARMA(order=2,seed=random.seed())
    x3_ts = ts.TimeSeries(x3, noise_generator=noise)
    x3_sample, signals, errors = x3_ts.sample(np.array(range(Tt)))
    t = np.array(np.zeros(4))
    
    return np.stack([x2_sample, x3_sample]), t, trend_style[trend], y

def save_data(path,array):
    with open(path,'wb') as f:
        pkl.dump(array, f)


def logistic(x):
    return 1./(1+np.exp(-1*x))


if __name__=='__main__':
 
    n_samples = 30000
    x_train_n,y_train,x_test_n,y_test,thresholds_train,thresholds_test, gt_importance_train, gt_importance_test = main(n_samples=n_samples, plot=False)
    print(x_train_n.shape)
    if not os.path.exists('./data_generator/data/simulated_data'):
        os.mkdir('./data_generator/data/simulated_data')
    save_data('./data_generator/data/simulated_data/x_train.pkl', x_train_n)
    save_data('./data_generator/data/simulated_data/y_train.pkl', y_train)
    save_data('./data_generator/data/simulated_data/x_test.pkl', x_test_n)
    save_data('./data_generator/data/simulated_data/y_test.pkl', y_test)
    save_data('./data_generator/data/simulated_data/thresholds_train.pkl', thresholds_train)
    save_data('./data_generator/data/simulated_data/thresholds_test.pkl', thresholds_test)
    save_data('./data_generator/data/simulated_data/gt_train.pkl', gt_importance_train)
    save_data('./data_generator/data/simulated_data/gt_test.pkl', gt_importance_test)
    print(gt_importance_train.shape)