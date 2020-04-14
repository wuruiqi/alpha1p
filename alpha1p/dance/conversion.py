# -*- coding: utf-8 -*-
"""
Created on Sun March 15 12:35:24 2020

@author: QQ
"""
import struct
import math
import numpy as np
import pandas as pd

__all__ = ['pd2np', 'pd2aesx', 'np2aesx', 'save_bin', 'compression', 'interpolation', 'np2hts']

def __single2double(single):
    '''
    功能：将单字节表示的数值改为双字节表示
    输入：
    single：单字节表示序列
    返回：
    double：双字节表示序列
    '''
    double = bytes()
    for i in range(len(single)):
        double += struct.pack('h', single[i])
    return double

def __generate_nulls(num):
    '''
    功能：生成二进制的0
    输入：
    num：需生成0的数量
    返回：
    nulls：二进制表示的0序列
    '''
    num = int(num)
    nulls = bytes()
    for i in range(num):
        nulls += struct.pack('h', 0)
    return nulls

def pd2np(pd_dance):
    '''
    功能：将pd格式的舞蹈表示转换为三个以np矩阵表示的形式
    输入：
    pd_dance：从csv文件读入的舞蹈动作
    返回：
    all_actions：numpy.array格式表示的所有舞姿的舵机角度值
    exec_times：numpy.array格式表示的所有舞姿的运行时间
    total_times：numpy.array格式表示的所有舞姿的总时间
    '''
    all_actions = np.zeros([len(pd_dance), 16])
    exec_times = np.zeros(len(pd_dance))
    total_times = np.zeros(len(pd_dance))
    for i in range(len(pd_dance)):
        all_actions[i] = eval(pd_dance.jointAngle.iloc[i])[0:16]
        exec_times[i] = pd_dance.runTime.iloc[i]
        total_times[i] = pd_dance.totalTime[i]
    all_actions = all_actions.astype(np.int32)
    return all_actions, exec_times, total_times

def pd2aesx(pd_dance, **kwargs):
    '''
    功能：将由pd格式表示的整支舞蹈转换为模拟器可识别的aesx文件
    输入：
    pd_dance：从csv文件读入的舞蹈动作
    返回：
    aesx_file：aesx文件格式的二进制数据流，数据格式为bytes
    '''
    all_actions, exec_times, total_times = pd2np(pd_dance)
    aesx_file = np2aesx(all_actions, exec_times, total_times, **kwargs)
    return aesx_file

def np2aesx(all_actions, exec_times, total_times, max_group_time=100000, prev_click_num = 0):
    '''
    功能：将由3个numpy.array格式表示的整支舞蹈转换为模拟器可识别的aesx文件
    输入：
    all_actions：numpy.array格式表示的所有舞姿的舵机角度值
    exec_times：numpy.array格式表示的所有舞姿的运行时间
    total_times：numpy.array格式表示的所有舞姿的总时间
    max_group_time：aesx文件中每个动作组的最长总时间，默认为（10万*10）微秒，超过此数值将再建立一个分组，以避免时间值溢出。
    prev_click_num：模拟在编辑aesx文件时点击选中每个舞姿的次数。此项只影响动作组和动作的编号。
                    这两个编号只要按照从大到小顺序即可，所以此项默认为0
    返回：
    aesx_file：aesx文件格式的二进制数据流，数据格式为bytes
    '''
    # 判断 单个舞姿的最长总时间小于最大时间的二分之一。
    assert total_times.max()< max_group_time * 5
    groups = bytes()    
    servo_num = 16
    end_size = 0
    prev_group_point = 1
    prev_action_num = 0
    start_time = 0.0
    p_action = 0
    group_num = 0

    while (p_action < (len(all_actions)-10)):
        action_num = 0
        end_time = 0.0
        prev_point = -2
        prev_action_click = 2
        group_actions = bytes()
        while end_time<max_group_time and p_action < len(all_actions):
            # add action_head
            fixed_head = struct.pack('2i', 212, 212)
            action_head = fixed_head
            action_point = prev_action_click*2 + prev_point + 3
            action_head += struct.pack('i', action_point)
            exec_time = exec_times[p_action] / 10
            total_time = total_times[p_action] / 10
            action_head += struct.pack('2f', exec_time, total_time)
            name = b'Action'
            fmt = str(len(name))+'s'
            name = struct.pack(fmt, name)
            action_head += __single2double(name)
            null_num = 60/2 - len(name)
            action_head += __generate_nulls(null_num)
            action_head += struct.pack('2i', 132, 132)
            group_actions += action_head

            # add joint_angles
            for j in range(servo_num):
                group_actions += struct.pack('2i', j+1, all_actions[p_action][j])

            action_num += 1
            p_action += 1
            end_time += total_time
            prev_point = action_point


        # add motion_head
        group_size = 80 + len(group_actions) + 10 #  80 + (128+88)*action_num + 10
        motion_head = struct.pack('2i', group_size, group_size)    
        start_point = (prev_action_num + prev_click_num)*2 + prev_group_point + 1
        motion_head +=  struct.pack('i', start_point)
        end_time += start_time
        times = struct.pack('2f', start_time, end_time)
        motion_head += times
        name = b'name %d' %(group_num)
        fmt = str(len(name))+'s'
        name = struct.pack(fmt, name)
        motion_head += __single2double(name)
        null_num = 60/2 - len(name)
        nulls = __generate_nulls(null_num)
        motion_head += nulls
        motion_head += struct.pack('i', action_num)


        # add motion_end
        motion_end = struct.pack('i6s', 6, b'motion')
        group = motion_head + group_actions + motion_end

        groups += group

        prev_group_point = start_point
        prev_action_num = action_num
        start_time = end_time
        group_num += 1

    # add file_head
    total_size = len(groups) + 69 # len(all_group) + 69 (the length of file_head)
    file_head = struct.pack('i', total_size)
    arr = [b'ubx-alpha',2,3,0,8,10]
    fmt = '='+str(len(arr[0]))+'s'+'5i'
    file_head += struct.pack(fmt,*arr)
    total_seconds = 5 + math.ceil(total_times.sum()/1000 - 0.01)
    file_head += struct.pack('i', total_seconds)
    arr = [4,8,8,0,1]
    file_head += struct.pack('5i',*arr)
    Remaining_size = len(groups) + 8
    Remaining_size = struct.pack('2i',Remaining_size, Remaining_size)
    file_head += Remaining_size
    file_head += struct.pack('i', group_num)

    aesx_file = file_head + groups
    return aesx_file

def save_bin(save_path, aesx_file):
    '''
    功能：将输入的二进制文件存盘保存，aesx和hts都是二进制文件。
    输入：
    aesx_file：aesx文件格式的二进制数据流，数据格式为bytes
    save_path：存盘路径
    返回：空
    '''
    with open(save_path, 'wb') as f:
        f.write(aesx_file)
    print("dance has been saved in %s" %(save_path))
    return

def is_zero(diff):
    '''
    功能：判定差值数组是否都为0
    输入：
    diff：一个长度为16的差值数组，数值类型为numpy.array
    返回：diff是否为0，数值类型为bool
    '''
    d = abs(diff)
    if d.sum() <= 0.02:
        return True
    else:
        return False
    
def compression(dance, intervals=20, have_start=True):
    '''
    功能：将帧式表示的舞蹈转换为舞姿形式表示的舞蹈。
        舞蹈帧式表示时，舞蹈以默认间隔时间一个舞姿的形式表示。
        舞蹈舞姿式表示时，舞蹈由舞姿+运行时间+总时间形式表示。
    输入：
    dance：以帧式表示的舞蹈动作。数据格式为numpy.array，形状为（n, 16）
    intervals：帧式表示舞蹈时的帧率，默认为20ms每帧。
    have_start:源舞蹈矩阵是否包含起始动作。若不包含，在首位置插入。
    返回：
    actions：numpy.array格式表示的所有舞姿的舵机角度值
    exec_times：numpy.array格式表示的所有舞姿的运行时间
    total_times：numpy.array格式表示的所有舞姿的总时间
    '''
    if not have_start:
        start_pose = np.array([90, 90, 90, 90, 90, 90, 90, 60, 76, 110, 90, 90, 120, 104, 70, 90])
        dance = np.insert(dance, 0, start_pose, axis=0)
    diff = np.diff(dance, axis=0)
    actions = np.zeros_like(dance)
    exec_times = np.zeros(dance.shape[0])
    total_times = np.zeros(dance.shape[0])
    pose_index = 0
    for i in range(diff.shape[0]):
        actions[pose_index] = dance[i+1]
        d_flag = is_zero(diff[i])    
        if d_flag:
            total_times[pose_index] += intervals
        else:
            exec_times[pose_index] += intervals
            total_times[pose_index] += intervals
        if  i < diff.shape[0] -1:
            dd = diff[i] - diff[i+1]
            dd_flag = is_zero(dd)
            d_1 = is_zero(diff[i+1])
            if not dd_flag and not d_1:
                pose_index += 1
    actions = actions[:pose_index+1].astype(np.int32)
    exec_times = exec_times[:pose_index+1]
    total_times = total_times[:pose_index+1]

    return actions, exec_times, total_times

def interpolation(dance_df, start_pose=None):
    '''
    功能：将舞姿式表示的舞蹈转换为帧式表示的舞蹈，帧率默认为20ms每帧。
    输入：
    dance_df:舞姿式表示的舞蹈，数据格式为pandas.dataframe
    返回：
    all_pose：帧式表示的舞蹈。数据格式为nmupy.np
    '''
    data = dance_df.copy()
    # 时间预处理
    data['totalTime'] = data['totalTime']/20
    data['runTime'] = data['runTime']/20
    sum_time = data['totalTime'].sum() + 1  
    all_pose = np.zeros([int(sum_time), 16])
    start_pose = np.array([90, 90, 90, 90, 90, 90, 90, 60, 76, 110, 90, 90, 120, 104, 70, 90])
    all_pose[0] = start_pose
    pose_index = 1
    for i in range(len(data)):
        end_pose = np.array(eval(data.jointAngle.iloc[i])[0:16])
        run_time = int(data.runTime.iloc[i])
        total_time = int(data.totalTime.iloc[i])
        holding_time = total_time - run_time
        if run_time >1 :
            step = (end_pose-start_pose)/(run_time)
            for j in range(run_time-1):
                all_pose[pose_index+j] = all_pose[pose_index+j-1] + step
        elif run_time == 1:
            all_pose[pose_index] = end_pose
        else:
            print('run_time error, run_time is %d'%(run_time))
        pose_index += run_time
        all_pose[pose_index-1:pose_index+holding_time] = end_pose
        pose_index += holding_time
        start_pose = end_pose
    return all_pose

def np2hts(action, run_time, total_time):
    '''
    功能：将由3个numpy.array格式表示的整支舞蹈转换为机器人可执行的hts文件
    输入：
    action：numpy.array格式表示的所有舞姿的舵机角度值
    run_time：numpy.array格式表示的所有舞姿的运行时间
    total_time：numpy.array格式表示的所有舞姿的总时间
    返回：
    hts：hts文件格式的二进制数据流，数据格式为bytes
    '''
    if action.shape[1] == 16:
        ext = np.full( [action.shape[0], 4], 90,)
        action = np.insert(action, [16], ext, axis=1)
    hts = [0]*33
    t_sum = int(total_time.sum())
    r = run_time/20
    t = total_time/20 - 2
    action_amount = len(action)
    
    for i in range(action_amount):
        start = [251,191,1]
        end = [237]
        if i+1 == 1:#开始动作
            start.append(1)
        elif i+1 == action_amount:
            start.append(3)
        else:
            start.append(2)
        start.append(action_amount%256)#动作数的低位
        start.append(action_amount/256)#动作数的高位
        start.append((i+1)%256)#action_id的低位
        start.append((i+1)/256)#action_id的高位
        start.extend(action[i])#action转换为角度
        start.append(r[i]% 256)     # 放入运行时间
        start.append(t[i]/256)      # 放入允许下帧允许的高位
        start.append(t[i]%256)      # 放入允许下帧允许的低位
        check_sum = 0
        for x in start[2:]:
            check_sum += int(x)
        start.append(check_sum%256)  # 放入check码
        start.append(237)       # 放入结束标志ED = 237
        for j in start:
            if j>255:
                print(j)
        hts.extend(start)
    hts.extend([0]*29)
    hts = np.trunc(hts).astype(int).tolist()
    fmt = str(len(hts))+'B'
    hts = struct.pack(fmt, *hts)
    hts += struct.pack('I', t_sum) #末尾加入总时间之和作为校验,数据类型为unsigned int
    return hts