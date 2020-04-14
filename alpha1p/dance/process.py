# -*- coding: utf-8 -*-
"""
Created on Sun March 15 12:35:24 2020

@author: QQ
"""

import numpy as np
import pandas as pd
import numba
import os
import sys
import pkg_resources
from .conversion import interpolation
names = locals()

__all__ = ['norm', 'denorm', 'norm_trans','norm_01', 'denorm_01',
           'merge_csv', 'segment_csv', 'pos_interp',
           'resample', 'action_correction']

PACKAGE_NAME = 'alpha1p'

def norm(x):
    '''
    功能：将舵机参数归一化到[-1,1]
    输入:待归一化舞蹈动作矩阵。数据类型为numpy.array
    返回：归一化后的舞蹈动作矩阵
    '''
    x = x/180
    out = (x -0.5) *2
    return out.clip(-1, 1)

def denorm(x):
    '''
    功能：将舵机参数从[-1,1]反归一化到[0,180]
    输入:待反归一化舞蹈动作矩阵。数据类型为numpy.array
    返回：反归一化后的舞蹈动作矩阵
    '''
    out = (x + 1) / 2
    out = out.clip(0, 1)
    out = out * 180
    return out

def norm_trans(x, small2big=True):
    '''
    功能：将舵机参数从[-1,1]归一化到[0,1] 或者相反
    输入:待反归一化舞蹈动作矩阵。数据类型为numpy.array
    返回：反归一化后的舞蹈动作矩阵
    '''
    if small2big:
        out = (x + 1) / 2
        out = out.clip(0, 1)
    else:
        out = (x -0.5) *2
        out = out.clip(-1, 1)
    return out

def norm_01(x):
    '''
    功能：将舵机参数归一化到[0,1]
    输入:待归一化舞蹈动作矩阵。数据类型为numpy.array
    返回：归一化后的舞蹈动作矩阵
    '''
    out = x/180
    return out.clip(0, 1)

def denorm_01(x):
    '''
    功能：将舵机参数从[0,1]反归一化到[0,180]
    输入:待反归一化舞蹈动作矩阵。数据类型为numpy.array
    返回：反归一化后的舞蹈动作矩阵
    '''
    out = x.clip(0, 1)
    out = out * 180
    return out

def merge_csv(input_dir, output_dir, keep_last_actions=True): 
    '''
     功能：将53支舞蹈合并为一个csv文件。
     输入：
     input_dir:待合并舞蹈的路径
     output_dir:舞蹈合并后保存的位置
     keep_last_actions：是否保留最后4个动作。
     返回：空
    '''
    if keep_last_actions:
        end = 1
    else:
        end = 5
    files = os.listdir(input_dir)
    files.sort()
    csv_list,count = [],0
    for filename in files:
        basename,extname = os.path.splitext(filename)
        if extname == '.csv':#对csv文件读取，读取为pandas.dataframe格式
            df = pd.read_csv(os.path.join(input_dir,filename))
            df = df.loc[:len(df)-end]#因为df的slice是包括最后一个编号的元素的，因此删除4个动作需要-5
            csv_list.append(df)
            count+=1
    assert count == 53,'error,53 files not {}'.format(count)
    result = pd.concat(csv_list)
    result.to_csv('{}/all_actions.csv'.format(output_dir),encoding="utf_8_sig",index=False, header=True)
    print ('All actions have been saved in %s/all_actions.csv' %(output_dir))
    return

def segment_csv(csv_path=None, csv_folder=None, np_folder=None, keep_last_actions=True):
    '''
    功能：将包含53支舞蹈的csv文件分割保存。分别保存为以csv格式保存的舞姿式舞蹈和以npy格式保存的帧式舞蹈。
    输入：
    csv_path:待分隔csv文件的路径。
    csv_folder：分割后53个csv文件的保存路径
    np_folder：分割后53个npy文件的保存路径
    keep_last_actions：是否保留最后4个动作。
    返回：空
    '''
    if csv_path is None:
        relative_path = 'Datas/all_actions.csv'
        csv_path = pkg_resources.resource_filename(PACKAGE_NAME, relative_path)
    if csv_folder is None:
        relative_path = 'Datas/single_dance_csv/'
        csv_folder = pkg_resources.resource_filename(PACKAGE_NAME, relative_path)
    if np_folder is None:
        relative_path = '/Datas/single_dance/'
        np_folder = pkg_resources.resource_filename(PACKAGE_NAME, relative_path)

    if not os.path.exists(csv_folder):
        os.makedirs(csv_folder)
    if not os.path.exists(np_folder):
        os.makedirs(np_folder)
        
    if keep_last_actions:
        end = 0
    else:
        end = 4
    #53支舞蹈，初步分割
    all_actions = pd.read_csv(csv_path)
    end_index = 0
    data_num=0
    while end_index != len(all_actions):
        start_index = end_index
        end_index = start_index + all_actions['actionAmount'][end_index] - end
        data_num += 1
        names['data_'+str(data_num).rjust(2,'0')] = all_actions[start_index:end_index]
        names['data_'+str(data_num).rjust(2,'0')].to_csv(csv_folder+'dance_%s.csv' % (str(data_num).rjust(2,'0')))
        end_index += end
    print('The csv format of 53 dances has been saved in %s' %csv_folder)
    #对每支舞蹈转换为帧式格式保存
    for i in range(data_num):
        dance = interpolation(names['data_'+str(i+1).rjust(2,'0')])
        #dance = dance.transpose(1, 0)
        # print(dance.shape, 'max:%s' % (str(dance.max())), 'min:%s' % (str(dance.min())))
        np.save(np_folder+'dance_%s.npy' % (str(i+1).rjust(2,'0')), dance) 
    print('The npy format of 53 dances has been saved in %s' %np_folder)
    return

def pos_interp(start, end, step=3):
    '''
    功能：对两个舞姿进行插值操作。
    输入：
    start：起始舞姿
    end： 结束舞姿
    step：要插入舞姿的数量
    返回：
    interpolated_pose：插值操作后的所有插值舞姿+起始舞姿和结束舞姿。对象格式为：numpy.ndarray
    '''
    std = np.zeros([16])
    interp_step = step+1 #不包含上下界，也就是要在上下界之间插入的真实数量+1。
    interpolated_pose = np.zeros([interp_step+1, 16], dtype='float64')
    interpolated_pose[0] = start

    for i in range(len(std)):
        std[i]= (end[i]-start[i])/interp_step
    for i in range(interp_step):
        interpolated_pose[i+1] = interpolated_pose[i]+std
    return interpolated_pose

@numba.jit(nopython=True, nogil=True)
def resample_f(x, y, sample_ratio, interp_win, interp_delta, num_table):

    scale = min(1.0, sample_ratio)
    time_increment = 1./sample_ratio
    index_step = int(scale * num_table)
    time_register = 0.0

    n = 0
    frac = 0.0
    index_frac = 0.0
    offset = 0
    eta = 0.0
    weight = 0.0

    nwin = interp_win.shape[0]
    n_orig = x.shape[0]
    n_out = y.shape[0]
    n_channels = y.shape[1]

    for t in range(n_out):
        # Grab the top bits as an index to the input buffer
        n = int(time_register)

        # Grab the fractional component of the time index
        frac = scale * (time_register - n)

        # Offset into the filter
        index_frac = frac * num_table
        offset = int(index_frac)

        # Interpolation factor
        eta = index_frac - offset

        # Compute the left wing of the filter response
        i_max = min(n + 1, (nwin - offset) // index_step)
        for i in range(i_max):

            weight = (interp_win[offset + i * index_step] + eta * interp_delta[offset + i * index_step])
            for j in range(n_channels):
                y[t, j] += weight * x[n - i, j]

        # Invert P
        frac = scale - frac

        # Offset into the filter
        index_frac = frac * num_table
        offset = int(index_frac)

        # Interpolation factor
        eta = index_frac - offset

        # Compute the right wing of the filter response
        k_max = min(n_orig - n - 1, (nwin - offset)//index_step)
        for k in range(k_max):
            weight = (interp_win[offset + k * index_step] + eta * interp_delta[offset + k * index_step])
            for j in range(n_channels):
                y[t, j] += weight * x[n + k + 1, j]

        # Increment the time register
        time_register += time_increment

        
def resample(y, ratio, axis=0, res_type='kaiser_best', fix=True):
    """Resample a time series according to ratio. Note: dance must be normde in[-1, 1] 
    Parameters
    ----------
    y : np.ndarray time series.
    when y.ndim>=3, y.shape[1] must be the number of channels in y. 
    ratio: float > 0
        The resample rate of y
    axis : int 
    The target axis along which to resample `y`
    res_type : str
        resample type (see note)
        .. note::
            By default, this uses `resampy`'s high-quality mode ('kaiser_best').
            To use a faster method, set `res_type='kaiser_fast'`.
        .. note::
            When using `res_type='polyphase'`, only integer sampling rates are
            supported.
    fix : bool
        adjust the length of the resampled signal to be of size exactly
        `ceil(ratio * y.shape[axis]))`

    Returns
    -------
    y_hat : np.ndarray    `y` resampled from y

    See Also
    --------
    This function reference from these functions:
    librosa.core.resample
    librosa.util.fix_length
    resampy.resample

    Examples
    --------
    Downsample according to ratio 0.8.
    >>> y_8 = resample(y, 0.8)
    >>> y.shape, y_8.shape
    ((16, 4385), (16,3508))
    """

    # First, validate the audio buffer

    if ratio == 1.0:
        return y

    n_samples = int(np.ceil(y.shape[axis] * ratio))

    y_hat = kaiser_resample(y, ratio, filter_name=res_type, axis=axis)


    if fix:
        y_hat = fix_length(y_hat, n_samples, axis=axis)
        
    y_hat = np.asfortranarray(y_hat, dtype=y.dtype)

    return y_hat


def kaiser_resample(x, sample_ratio, axis=-1, filter_name='kaiser_best'):
    '''Resample a signal x according to resample_ratio along a given axis.

    Parameters
    ----------
    x : np.ndarray, dtype=np.float*
        The input signal(s) to resample.

    sample_ratio : float > 0
        The resample rate of x
        
    axis : int
        The target axis along which to resample `x`

    filter : optional, str or callable
        The resampling filter to use.

        By default, uses the `kaiser_best` (pre-computed filter).

    Returns
    -------
    y : np.ndarray

    Raises
    ------

    TypeError
        if the input signal `x` has an unsupported data type.
    '''

    # Set up the output shape
    shape = list(x.shape)
    shape[axis] = int(shape[axis] * sample_ratio)

    if shape[axis] < 1:
        raise ValueError('Input signal length={} is too small to '
                         'resample'.format(x.shape[axis]))

    # Preserve contiguity of input (if it exists)
    # If not, revert to C-contiguity by default
    if x.flags['F_CONTIGUOUS']:
        order = 'F'
    else:
        order = 'C'

    y = np.zeros(shape, dtype=x.dtype, order=order)
    
    fname = os.path.join('Datas/resample_filter', os.path.extsep.join([filter_name, 'npz']))
    file_path = pkg_resources.resource_filename(PACKAGE_NAME, fname)
    data = np.load(file_path)
    interp_win = data['half_window']
    precision = data['precision']

    if sample_ratio < 1:
        interp_win *= sample_ratio

    interp_delta = np.zeros_like(interp_win)
    interp_delta[:-1] = np.diff(interp_win)

    # Construct 2d views of the data with the resampling axis on the first dimension
    x_2d = x.swapaxes(0, axis).reshape((x.shape[axis], -1))
    y_2d = y.swapaxes(0, axis).reshape((y.shape[axis], -1))
    resample_f(x_2d, y_2d, sample_ratio, interp_win, interp_delta, precision)

    return y


def fix_length(data, size, axis=-1, mode_type='edge'):
    '''Fix the length an array `data` to exactly `size`.
    If `data.shape[axis] < n`, pad according to the provided mode type.
    By default, `data` is padded with edge mode.
    Examples
    --------
    >>> y = np.arange(7)
    >>> # Default: pad with zeros
    >>> fix_length(y, 10)
    array([0, 1, 2, 3, 4, 5, 6, 6, 6, 6])
    >>> # Trim to a desired length
    >>> fix_length(y, 5)
    array([0, 1, 2, 3, 4])
    >>> # Use zeros-padding instead of edge
    >>> librosa.util.fix_length(y, 10, mode='constant')
    array([0, 1, 2, 3, 4, 5, 6, 0, 0, 0])
    Parameters
    ----------
    data : np.ndarray
      array to be length-adjusted
    size : int >= 0 [scalar]
      desired length of the array
    axis : int, <= data.ndim
      axis along which to fix length
    kwargs : additional keyword arguments
        Parameters to `np.pad()`
    Returns
    -------
    data_fixed : np.ndarray [shape=data.shape]
        `data` either trimmed or padded to length `size`
        along the specified axis.
    See Also
    --------
    numpy.pad
    '''

    n = data.shape[axis]
    if n > size:
        slices = [slice(None)] * data.ndim
        slices[axis] = slice(0, size)
        return data[tuple(slices)]

    elif n < size:
        lengths = [(0, 0)] * data.ndim
        lengths[axis] = (0, size - n)
        return np.pad(data, lengths, mode= mode_type)

    return data

def action_correction(actions, policy='conservative'):
    '''
    功能：修正生成舞蹈中出现的舵机参数错误，7号舵机的角度必须要小于12号舵机的角度。
        注意，舵机角度值必须反归一化到[0, 180]
    输入：舞蹈动作矩阵，格式为numpy.array。
    返回：修正后的舞蹈动作矩阵。
    '''
    if policy == 'conservative':
        for i in range(actions.shape[0]):
            if actions[i][6]>actions[i][11]:
                if 180 - actions[i][6] < actions[i][11]:
                    actions[i][6] = actions[i][11] - 1
                else:
                    actions[i][11] = actions[i][6] + 1
    else:
        for i in range(actions.shape[0]):
            if actions[i][6]>actions[i][11]:
                if 180 - actions[i][6] < actions[i][11]:
                    actions[i][11] = actions[i][6] + 1
                else:
                    actions[i][6] = actions[i][11] - 1
    
    return actions.clip(0, 180)
