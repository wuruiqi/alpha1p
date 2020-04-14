#!/sur/bin/python
#coding:utf-8

import serial
from math import ceil
from struct import unpack, pack

__all__ = [ 'packageCommand', 'usb_reformat_response', 'parsing_all_response', 'parsing_gen_resp', 
           'get_handshake_cmd', 'parsing_handshake',
           'get_aciton_list_cmd', 'parsing_get_action_list', 'get_execute_action_table_cmd',
           'parsing_execute_action_table', 'get_stop_cmd', 'get_sound_cmd', 'get_play_switch_cmd',
           'get_heart_beat_cmd', 'parsing_heart_beat', 'get_robot_status_cmd', 'parsing_get_robot_status', 
           'get_set_sound_cmd', 'get_power_down_cmd', 'get_light_cmd', 'get_set_time_cmd', 'get_read_alarm_cmd', 
           'parsing_read_alarm', 'get_set_alarm_cmd', 'get_soft_version_cmd', 'parsing_soft_version',
           'get_power_info_cmd', 'parsing_power_info', 'parsing_low_voltage_alarm','get_hard_version_cmd', 
           'parsing_hard_version', 'get_single_control_cmd', 'parsing_single_control', 'get_multi_control_cmd', 
           'parsing_multi_control', 'get_rb_single_cmd', 'parsing_rb_single', 'get_rb_all_cmd', 'parsing_rb_all', 
           'get_set_single_offset_cmd', 'parsing_set_single_offsset', 'get_set_all_offset_cmd', 
           'parsing_set_all_offsset', 'get_read_single_offset_cmd', 'parsing_read_single_offsset',
           'get_read_all_offset_cmd', 'parsing_read_all_offsset', 'get_single_geer_version_cmd',
        'parsing_single_geer_version','get_all_geer_version_cmd','parsing_all_geer_version','parsing_play_end', 
           'get_play_and_charge_cmd','get_sn_cmd', 'parsing_sn', 'get_udid_cmd', 'parsing_udid']


def packageCommand(parameters,cmdType):
    '''
    功能：打包机器人蓝牙通讯命令。
    输入：
    parameters:命令参数，数据是个list(int, int,...)
    cmdType:命令类型，数据格式string
    返回：机器人可识别的通讯命令，数据格式bytes
    '''          
    type2Number={'handShake':1, 'get_action_list':2, 'execute_action_table':3, 'stop_play':5,
                 'sound_switch':6, 'play_switch':7, 'heart_beat':8, 'robot_status':10, 'set_sound':11, 
                 'power_down':12, 'light_switch':13, 'set_time':14, 'read_alarm':15, 'set_alarm':16, 
                 'soft_version':17, 'power_info':24, 'hard_version':32, 'single_control':34, 'multi_Control':35, 
                 'read_back_single':36, 'read_back_all':37, 'set_single_offset':38, 'set_all_offset':39, 
                 'read_single_offset':40, 'read_all_offset':41, 'single_geer_version':42, 'all_geer_version':43,
                 'play_and_charge':50, 'get_sn':51, 'get_udid':52}
    cmd_list = [251,191]      # 先放入命令头 FB=251  BF=191
    cmd_list.append(len(parameters)+5)  # 放入长度 1字节 ,等于参数长度 +5 ，5个字节分别是（FB BF 长度 命令 check）
    cmd_list.append(type2Number[cmdType])   #放入命令代码
    for x in parameters:       # 放入参数数据
        cmd_list.append(x)
    checkSum = 0    
    for x in cmd_list[2:]:
        checkSum += x
    cmd_list.append(checkSum%256)   # 放入check码
    cmd_list.append(237)       # 放入结束标志ED = 237
    cmd = serial.to_bytes(cmd_list)
    return cmd

def usb_reformat_response(raw_response):
    '''
    功能：将usb模拟串口通讯的回应内容格式化。
    输入：
    raw_response:机器人发回的原始内容，数据格式bytes
    返回：
    response:转换为串口通讯发回的内容格式，数据格式bytes
    '''      
    response = b''
    p_start = -1
    p_end = 0
    while p_end < len(raw_response)-1:
        try:
            p_start = raw_response.index(b'\xfb\xbf',p_start+1)
            cmd_len = raw_response[p_start+2]
            end = p_start+cmd_len
        except ValueError:
            p_start = len(raw_response)

        try:
            p_end = raw_response.index(b'\xed',p_start+1)
            while p_end != end and p_end<len(raw_response)-1:
                try:
                    p_end = raw_response.index(b'\xed',p_end+1)
                
                except ValueError:
                    print('命令解析错误，错误命令为：%s' %raw_response[p_start:p_end+1])
                    return 0
                if p_end > end:
                    print('命令解析错误，错误命令为：%s' %raw_response[p_start:p_end+1])
                    return 0
        except ValueError:
            p_end = len(raw_response)-1
        response += raw_response[p_start:p_end+1]
        
        if response!=b'' and response[-1] != 237:
            print(raw_response, p_start, p_end)
            print('命令解析错误，命令结尾不是\xed，错误命令为：%s' %raw_response[p_start:p_end+1])
            return 0
    return response
def parsing_all_response(response):
    '''
    功能：解析蓝牙协议中所有命令类型的回应内容。
    输入：
    response：符合蓝牙通讯协议的一条通讯。
    返回：
    cmd：空
    ''' 
    type2function = {1:(parsing_handshake), 2:(parsing_get_action_list), 3:(parsing_execute_action_table), 
                     5:(parsing_gen_resp), 6:(parsing_gen_resp), 7:(parsing_gen_resp), 8:(parsing_gen_resp),
                  10:(parsing_get_robot_status), 11:(parsing_gen_resp), 12:(parsing_gen_resp), 
                     13:(parsing_gen_resp), 14:(parsing_gen_resp), 15:(parsing_read_alarm), 
                     16:(parsing_gen_resp), 17:(parsing_soft_version), 24:(parsing_power_info), 
                     25:(parsing_low_voltage_alarm), 32:(parsing_hard_version), 34:(parsing_single_control), 
                     35:(parsing_multi_control), 36:(parsing_rb_single), 37:(parsing_rb_all), 
                     38:(parsing_set_single_offsset), 39:(parsing_set_all_offsset), 
                     40:(parsing_read_single_offsset), 41:(parsing_read_all_offsset), 
                     42:(parsing_single_geer_version), 43:(parsing_all_geer_version), 49:(parsing_play_end),
                50:(parsing_gen_resp), 51:(parsing_sn), 52:(parsing_udid)}
    
    cmd_type = response[3]

    parsing_function = type2function.get(cmd_type)
    parsing_function(response, tips=True)
    return

def parsing_gen_resp(response, tips=True):
    '''
    功能：解析停止命令回应内容。
    输入：
    response
    返回：
    cmd：机器人停止运动的命令。
    '''          
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    types=[5, 6, 7, 8, 10, 11, 12, 13, 14, 16, 50]
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type not in types:  
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return
    if tips:
        s ={5:'停止运行', 6:'声音开关', 7:'运动开关', 8:'心跳包', 10:'状态控制相关的',11:'设置音量', 12:'所有舵机掉电',
           13:'灯光控制', 14:'设置时间', 16:'设置闹钟', 50:'边玩边充电'}.get(cmd_type)
        
        print('已收到%s命令！'%(s))
    return

def get_handshake_cmd():
    '''
    功能：生成握手命令。
    输入：空
    返回：
    cmd：机器人握手命令。
    '''          
    cmd = packageCommand([0], 'handShake')
    return cmd

def parsing_handshake(response, tips=True):
    '''
    功能：解析握手包的返回内容，获取机器人的名字。
    输入：pc->dev 握手包之后，dev->pc的反应内容。
    返回：
    cmd：机器人的名字。
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    success = True
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 1: #0x01
        print(print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type))
        return 0
    robot_name = bytes.decode(response[4:(cmd_len-2)])
    if tips:
        print('Robot response:\n=======================\nRobot name:%s \n'%(robot_name))
    return robot_name

def get_aciton_list_cmd():
    '''
    功能：生成获取动作表命令。
    输入：空
    返回：
    cmd：获取动作表命令。
    '''          
    cmd = packageCommand([0], 'get_action_list')
    return cmd

def parsing_get_action_list(response, tips=False):
    '''
    功能：解析动作表的返回内容，获取动作表。
    输入：
    response：dev->pc的反应内容。
    返回：
    cmd：解析得到的动作表，数据格式为list。
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    poffset = 0
    total_len = (len(response))
    cmd_len = response[2]
    cmd_type = response[3]
    action_list = []
    if cmd_type != 2: #0x02
        print('命令类型错误，请检查命令内容！当前命令类型为%d' %(cmd_type))
        return 0
    poffset = response.index(b'\xfb\xbf', poffset+1)
    cmd_len = response[poffset+2]
    cmd_type = response[poffset+3]
    while cmd_type==128: #0x80
        action_name = bytes.decode(response[poffset+4:(poffset+cmd_len-1)],encoding= 'gbk')
        action_list.append(action_name)
        poffset = response.index(b'\xfb\xbf', poffset+1)
        cmd_len = response[poffset+2]
        cmd_type = response[poffset+3]

    if cmd_type!=129 or response[poffset+4] !=0: # 0x81
        print('获取动作表失败！请重新获取动作表，当前动作表数据最后一组命令类型为%d' %cmd_type)
        return 0
    if tips:
        print('获得动作表如下：\n%s'%(action_list))
    return action_list

def get_execute_action_table_cmd(action_name):
    '''
    功能：生成执行动作表命令。
    输入：
    action_name:要执行的动作表名称。
    返回：
    cmd：获取执行动作表的命令。
    '''          
    cmd = packageCommand(action_name.encode(encoding= 'gbk'), 'execute_action_table')
    return cmd

def parsing_execute_action_table(response, tips=True):
    '''
    功能：解析执行动作表后的返回内容，并判断动作是否执行成功。
    输入：
    response：dev->pc的反应内容。
    返回：空
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    success = True
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 3: #0x03
        print(print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type))
        return 0
    feedback = response[4]
    if tips:
        if feedback ==0:
            print('动作执行成功！！')
        elif feedback == 1:
            print('动作表名称错误，动作执行失败！！')
        elif feedback == 2:
            print('机器人电量低，动作执行失败！！')
    return

def get_stop_cmd():
    '''
    功能：生成停止命令。
    输入：空
    返回：
    cmd：机器人停止运动的命令。
    '''  

    cmd = packageCommand([0], 'stop_play')
    return cmd

def get_sound_cmd(switch):
    '''
    功能：生成声音控制命令。
    输入：
    switch：根据switch内容控制机器人声音开关。switch数据类型为int，取值范围0或1，为0时关闭声音，当为1时打开声音。
    返回：
    cmd：机器人声音控制的命令。
    '''          
    cmd = packageCommand([switch], 'sound_switch')
    return cmd

def get_play_switch_cmd(switch):
    '''
    功能：生成运动控制命令。
    输入：
    switch：根据switch内容控制机器人运动或者暂停。switch数据类型为int，取值范围0或1，当为0时暂停播放，为1时继续播放。
    返回：
    cmd：机器人运动控制的命令。
    '''          
    cmd = packageCommand([switch], 'play_switch')
    return cmd

def get_heart_beat_cmd():
    '''
    功能：生成心跳包命令。
    输入：空
    返回：
    cmd：心跳包命令。
    '''          
    cmd = packageCommand([0], 'heart_beat')
    return cmd

def parsing_heart_beat(response):
    '''
    功能：解析心跳包返回内容：
    输入：
    response：机器人返回的回应信息。
    返回：
    cmd：确定心跳包是否得到回应。
    '''
    if response==b'':
        return False
    success = True
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 8:  #0x08
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return False
    feedback = response[4]
    if feedback !=0:
        success = False
    return success


def get_robot_status_cmd():
    '''
    功能：生成获取机器人状态命令。
    输入：空
    返回：
    cmd：获取机器人状态命令。
    '''          
    cmd = packageCommand([0], 'robot_status')
    return cmd

def parsing_get_robot_status(response, tips=False):
    '''
    功能：解析机器人当前状态命令。
    输入：
    response：dev->pc的反应内容。
    返回：空
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    if len(response) !=40:
        if len(response)==8:
            parsing_gen_resp(response)
        else:
            print('回应数据错误，数据长度不是40，当前回应数据为%s'%response)
        return 0
    s_response = response.split(b'\xfb\xbf\x07')
    for i in range(1,6):        
        cmd_type = s_response[i][0]
        if cmd_type != 10: #0x0A
            print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
            return 0
        try:
            sub_type = s_response[i][1]
            p = s_response[i][2]
        except IndexError:
            print(i, s_response[i], response)
            return 0
        if sub_type==0:
            if p==0:
                is_mute = False
            else:
                is_mute = True

        elif sub_type==1:
            if p==0:
                play_status = False
            else:
                play_status = True
        elif sub_type==2:
            sound_size = ceil(100*p/255)

        elif sub_type==3:
            if p==0:
                light_status = False
            else:
                light_status = True
        elif sub_type==4:
            if p==0:
                tf_card = False
            else:
                tf_card = True
    if tips:
        mute_s = '是' if is_mute else '否'
        play_s = '播放中' if play_status else '暂停中'
        light_s = '开' if light_status else '关'
        tf_s = '已插入' if tf_card else '已拔出'
        print('======机器人当前状态======\n静音: %s\n状态: %s\n音量: %d\n灯光: %s\n内存卡: %s' %
                  (mute_s, play_s, sound_size, light_s, tf_s))
    return  is_mute, play_status, sound_size, light_status, tf_card

def get_set_sound_cmd(size):
    '''
    功能：生成设置音量命令。
    输入：
    size：音量大小，取值范围为0~100。
    返回：
    cmd：设置音量命令。
    '''          
    if size>100:
        size=100
    elif size<0:
        size=0
    size = int(255*size/100)
    cmd = packageCommand([size], 'set_sound')
    return cmd

def get_power_down_cmd():
    '''
    功能：生成所有舵机掉电命令。
    输入：空
    返回：
    cmd：所有舵机掉电命令。
    '''          
    cmd = packageCommand([0], 'power_down')
    return cmd

def get_light_cmd(switch):
    '''
    功能：生成灯光控制命令。
    输入：
    switch：根据switch内容控制机器人的灯光。switch数据类型为int，取值范围0或1，当为0时打开灯光，为1时关闭灯光。
    返回：
    cmd：机器人灯光控制的命令。
    '''          
    cmd = packageCommand([switch], 'light_switch')
    return cmd

def get_set_time_cmd(local_time):
    '''
    功能：生成同步时钟命令。
    输入：
    local_time：当前地区的当前时间，格式为time.struct_time
    返回：
    cmd：同步时钟命令。
    '''   
    year = local_time.tm_year - (local_time.tm_year//100)*100
    parameters=[year, local_time.tm_mon, local_time.tm_mday, local_time.tm_hour,
                local_time.tm_min, local_time.tm_sec+1]
    
    cmd = packageCommand(parameters, 'set_time')
    return cmd

def get_read_alarm_cmd():
    '''
    功能：生成读取闹钟命令。
    输入：空
    返回：
    cmd：读取闹钟命令。
    '''       
    cmd = packageCommand([0], 'read_alarm')
    return cmd

def parsing_read_alarm(response, tips=False):
    '''
    功能：解析读取闹钟参数：
    输入：
    response：机器人返回的闹钟信息。
    返回：
    alarm：闹钟信息，数据格式：tuple
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    alarm={}
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 15:  #0x0F
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return
    alarm['switch'] = response[4]
    alarm['every_day'] = response[5]
    alarm['hour'] = response[6]
    alarm['min'] = response[7]
    alarm['sec'] = response[8]
    name_len = response[9]-1
    if name_len==0:
        alarm['action_name'] = 'null'
    else:
        alarm['action_name'] = bytes.decode(response[10:11+name_len], encoding= 'gbk')
    if tips:
        switch = '开' if alarm['switch'] else '关'
        every_day = '开' if alarm['every_day'] else '关'
        times = '{}:{}:{}'.format(str(alarm['hour']).rjust(2,'0'), 
                str(alarm['min']).rjust(2,'0'), str(alarm['sec']).rjust(2,'0'))
        print('======机器人闹钟======\n闹钟开关: %s\n每日重复: %s\n响铃时间: %s\n闹钟舞蹈: %s\n' %
                (switch,  every_day, times, alarm['action_name'])) 
    return alarm

def get_set_alarm_cmd(alarm):
    '''
    功能：生成设置闹钟命令。
    输入：
    alarm：闹钟参数，格式为tuple{'switch':闹铃开关, 'every_day':是否每日重复, 
    'hour':时, 'min':分, 'sec'秒:, 'action_name':舞蹈名称}
    minute：分 
    sec：秒
    返回：
    cmd：设置闹钟命令。
    '''   
    parameters=[int(alarm['switch']), int(alarm['every_day']), alarm['hour'], alarm['min'], 
                alarm['sec']]
    if alarm['action_name']=='null':
        parameters.append(0)
        parameters.append(0)
    else:
        action_name = alarm['action_name'].encode('gbk')
        parameters.append(len(action_name))
        for x in action_name:
            parameters.append(x)
    cmd = packageCommand(parameters, 'set_alarm')
    return cmd

def get_soft_version_cmd():
    '''
    功能：生成获取机器软件版本命令。
    输入：空
    返回：
    cmd：获取机器软件版本命令。
    '''       
    cmd = packageCommand([0], 'soft_version')
    return cmd

def parsing_soft_version(response, tips=False):
    '''
    功能：解析机器人软件版本
    输入：
    response：机器人返回的回应信息。
    返回：
    cmd：机器人软件版本。
    '''
    if response==b'':
        return
    cmd_type = response[3]
    if cmd_type != 17:  #0x11
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return
    feedback = response[4:14].decode('gbk')
    if tips:
        print('机器人软件版本：%s'%(feedback))
    return feedback

def get_power_info_cmd():
    '''
    功能：生成获取机器软件版本命令。
    输入：空
    返回：
    cmd：获取机器软件版本命令。
    '''       
    cmd = packageCommand([0], 'power_info')
    return cmd

def parsing_power_info(response, tips=False):
    '''
    功能：解析机器人电量信息。
    输入：
    response：机器人返回的回应信息。
    返回：
    cmd：机器人硬件版本。
    '''
    if response==b'':
        print('获取电量信息失败！')
        return None, None, None
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 24:  #0x18
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return
    voltage = (response[4]*256+response[5])/1000
    charging = response[6]
    power = response[7]
    if tips:
        if charging==0:
            charge_info = '当前未充电！'
        elif charging==1:
            charge_info = '正在充电中....'
        elif charging==3:
            charge_info = '机器人没有电池，当前电源供电！'
        else:
            charge_info = '获取电量信息失败！'
        print('电压：{}v\n电量：{}%\n{}'.format(voltage, power, charge_info))    
    return voltage, charging, power

def parsing_low_voltage_alarm(response, tips=False):
    '''
    功能：解析机器人发出的低电压报警内容：
    输入：
    response：机器人发出的低电压报警内容。
    返回：空
    '''
    if response==b'':
        return response
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 25: #0x19
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    print('警告：机器人电压低，请及时充电！！！')
    return

def get_hard_version_cmd():
    '''
    功能：生成获取机器硬件版本命令。
    输入：空
    返回：
    cmd：获取机器硬件版本命令。
    '''       
    cmd = packageCommand([0], 'hard_version')
    return cmd

def parsing_hard_version(response, tips=False):
    '''
    功能：解析机器人硬件版本
    输入：
    response：机器人返回的回应信息。
    返回：
    cmd：机器人硬件版本。
    '''
    if response==b'':
        return
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 32:  #0x20
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return
    feedback = response[4:cmd_len-1].decode('gbk')
    if tips:
        print('机器人硬件版本：%s'%(feedback))
    return feedback

def get_single_control_cmd(cmd):
    '''
    功能：生成单舵机运动命令。
    输入：    
    cmd：单个舵机运动的命令参数，包括：舵机ID，舵机角度，运行时间，和允许下帧数据时间。
        注意：舵机ID从1开始计算
    返回：
    cmd：单舵机运动命令。
    '''  
    joint_id = cmd['joint_id']
    if joint_id not in range(1, 17):
        print('舵机ID错误，舵机ID从1开始计数，必须为1~16中的一个。当前输入ID为：%d' % joint_id)
        return
    angle = cmd['jointAngle']
    runtime =  cmd['runTime']//20
    nextTime = cmd['totalTime']//20 - 2
    parameters_list = []
    parameters_list.append(joint_id)         #  放入舵机ID
    parameters_list.append(angle)            #  放入舵机角度
    parameters_list.append(runtime % 256)     # 放入运行时间
    parameters_list.append(nextTime//256)      # 放入允许下帧允许的高位
    parameters_list.append(nextTime%256)      # 放入允许下帧允许的低位
    cmd = packageCommand(parameters_list, 'single_control')
    return cmd

def parsing_single_control(response, tips=False):
    '''
    功能：解析设置单舵机角度值的回应信息
    输入：
    response：机器人返回的设置单舵机角度值的回应信息
    返回：
    success:判定是否设置成功。数据格式bool
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    success = True
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 34: #0x22
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    joint_id = response[4]
    feedback = response[5]

    if feedback !=0:
        success = False
        if feedback == 1:
            print('错误：%d号舵机的id值错误！'%(joint_id))
        elif feedback == 2:
            print('错误：%d号舵机的角度值超出允许！'%(joint_id))
        elif feedback == 3:
            print('错误：%d号舵机没有应答！'%(joint_id))
    if tips:
        ss = '成功' if success else '失败'
        print('单舵机运动命令执行%s！'%(ss))
    return success

def  get_multi_control_cmd(cmd):
    '''
    功能：生成多舵机运动命令。
    输入：    
    cmd：多舵机运动的命令参数，包括：所有舵机的角度值，运行时间，和允许下帧数据时间。
    注意：舵机ID从1开始计算
    返回：
    cmd：多舵机运动命令。
    '''  
    angle = cmd['jointAngle'][0:16]
    runtime =  cmd['runTime']//20
    nextTime = cmd['totalTime']//20 - 2
    #nextTime只是标志在接到当前动作指令的nex tTime时间后才能接收下一个指令，
    #为了弥补指令传输和执行的延迟，将这个值减小20ams(这个值很难设置，因为无论usb传输或者蓝牙都会有延迟，
    #而这些延迟是会累加的。)
    parameters_list = []
    for x in angle:   #  放入16个关节的角度值
        parameters_list.append(x)
    parameters_list.append(runtime % 256)     # 放入运行时间
    parameters_list.append(nextTime//256)      # 放入允许下帧允许的高位
    parameters_list.append(nextTime%256)      # 放入允许下帧允许的低位
    cmd = packageCommand(parameters_list, 'multi_Control')
    return cmd

def parsing_multi_control(response, tips=False):
    '''
    功能：解析设置所有舵机角度值的回应信息
    输入：
    response：机器人返回的设置所有舵机角度值的回应信息
    返回：
    success:判定是否设置成功。数据格式bool
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    success = True
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 35: #0x23
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    feedback = response[4:cmd_len-1]
    for i in range(len(feedback)):
        if feedback[i] !=0:
            success = False
            if feedback[i] == 1:
                print('错误：%d号舵机的id值错误！'%(i+1))
            elif feedback[i] == 2:
                print('错误：%d号舵机的角度值超出允许！'%(i+1))
            elif feedback[i] == 3:
                print('错误：%d号舵机没有应答！'%(i+1))
    if tips:
        ss = '成功' if success else '失败'
        print('多舵机运动命令执行%s！'%(ss))
    return success

def get_rb_single_cmd(joint_id):
    '''
    功能：生成回读单舵机角度的命令。
    输入：
    joint_id：舵机ID。
    返回：
    cmd：回读单舵机角度的命令。
    '''          
    cmd = packageCommand([joint_id], 'read_back_single')
    return cmd

def parsing_rb_single(response, tips=False):
    '''
    功能：解析回读单个舵机角度命令执行后机器人的回应信息。
    输入：空
    返回：
    angle：回读单个舵机角度的命令。
    ''' 
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 36:  #0x24
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    joint_id = response[4]
    angle = response[5]
    if tips:
        print('回读到%d号舵机的角度值为：%d'%(joint_id, angle))
    return angle

def get_rb_all_cmd():
    '''
    功能：生成回读所有舵机角度的命令。
    输入：空
    返回：
    cmd：回读所有舵机角度的命令。
    '''          
    cmd = packageCommand([0], 'read_back_all')
    return cmd

def parsing_rb_all(response, tips=False):
    '''
    功能：解析回读所有舵机角度命令执行后机器人的回应信息。
    输入：空
    返回：
    angles：回读所有舵机角度的命令。
    ''' 
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 37: #0x25
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    angles = []
    for i in range(16):
        angles.append(response[4+i])        
    if tips:
        print('回读到所有舵机的角度值为：{}'.format(angles))
    return angles

def get_set_single_offset_cmd(geer_id, offset_value):
    '''
    功能：生成设置单个舵机偏移值的命令。
    输入：
    geer_id:舵机ID
    offset_value:舵机的偏移值
    返回：
    cmd：设置单个舵机偏移值的命令。
    '''     
    parameters=[geer_id]
    value = pack('!h', offset_value)
    parameters.append(value[0])
    parameters.append(value[1])
    cmd = packageCommand(parameters, 'set_single_offset')
    return cmd

def parsing_set_single_offsset(response, tips=False):
    '''
    功能：解析设置单舵机偏移值的回应信息
    输入：
    response：机器人返回的设置单舵机偏移值的回应信息
    返回：
    success:判定是否设置成功。数据格式bool
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    success = True
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 38: #0x26
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    joint_id = response[4]
    feedback = response[5]

    if feedback !=0:
        success = False
        if feedback == 1:
            print('错误：%d号舵机的id值错误！'%(joint_id))
        elif feedback == 2:
            print('错误：%d号舵机没有应答！'%(joint_id))
    if tips:
        ss = '成功' if success else '失败'
        print('设置单舵机偏移值命令执行%s！'%(ss))
    return success


def get_set_all_offset_cmd(offset_values):
    '''
    功能：生成设置所有舵机偏移值的命令。
    输入：
    offset_values:所有舵机的偏移值，数据格式：list
    返回：
    cmd：设置所有舵机偏移值的命令。
    '''
    parameters = []
    for offset_value in offset_values:
        value = pack('!h', offset_value)
        parameters.append(value[0])
        parameters.append(value[1])
    cmd = packageCommand(parameters, 'set_all_offset')
    return cmd

def parsing_set_all_offsset(response, tips=False):
    '''
    功能：解析设置所有舵偏移值的回应信息
    输入：
    response：机器人返回的设置所有舵机偏移值的回应信息
    返回：
    success:判定是否设置成功。数据格式bool
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    success = True
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 39: #0x27
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    feedback = response[4:cmd_len-1]
    for i in range(len(feedback)):
        if feedback[i] !=0:
            success = False
            if feedback[i] == 1:
                print('错误：%d号舵机的id值错误！'%(i+1))
            elif feedback[i] == 2:
                print('错误：%d号舵机没有应答！'%(i+1))
    if tips:
        ss = '成功' if success else '失败'
        print('设置所有舵机偏移值命令执行%s！'%(ss))
    return success

def get_read_single_offset_cmd(geer_id):
    '''
    功能：生成读取单个舵机偏移值的命令。
    输入：
    geer_id:舵机ID
    返回：
    cmd：读取单个舵机偏移值的命令。
    '''          
    cmd = packageCommand([geer_id], 'read_single_offset')
    return cmd

def parsing_read_single_offsset(response, tips=False):
    '''
    功能：解析单舵机的偏移值信息
    输入：
    response：机器人返回的单个舵机的偏移值信息。
    返回：
    geer_id:舵机ID，数据格式：int
    value:舵机的偏移值，数据格式：int
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 40: #0x28
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    geer_id = response[4]
    value = response[5:7]

    if value[0]==0x88:
            print('错误：%d号舵机没有响应！'%(geer_id))
    else:
        value = unpack('!h', value)[0]
    if tips:
        print('%d号舵机的偏移值为：%d'%(geer_id, value))
    return geer_id, value

def get_read_all_offset_cmd():
    '''
    功能：生成读取所有舵机偏移值的命令。
    输入：空
    返回：
    cmd：获取所有舵机偏移值的命令。
    '''          
    cmd = packageCommand([0], 'read_all_offset')
    return cmd

def parsing_read_all_offsset(response, tips=False):
    '''
    功能：解析所有舵机的偏移值信息：
    输入：
    response：机器人返回的所有舵机的偏移值信息。
    返回：
    geer_nums:舵机数量，数据格式：list
    values:所有舵机的偏移值，数据格式：list
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 41: #0x29
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    feedback = response[4:cmd_len-1]
    values =[]
    geer_nums = len(feedback)//2
    for i in range(geer_nums):
        value = feedback[i*2:(i+1)*2]
        if value[0]==0x88:
                print('错误：%d号舵机没有响应！'%(i+1))
        else:
            value = unpack('!h', value)[0]
        values.append(value)
    if tips:
        print('机器人共有{}个舵机，所有舵机的偏移值为：\n{}'.format(geer_nums, values))
    return geer_nums, values


def get_single_geer_version_cmd(geer_id):
    '''
    功能：生成读取单舵机版本命令。
    输入：
    geer_id：舵机ID。
    返回：
    cmd：读取单舵机版本命令。
    '''          
    cmd = packageCommand([geer_id], 'single_geer_version')
    return cmd

def parsing_single_geer_version(response, tips=False):
    '''
    功能：解析单舵机版本命令：
    输入：
    response：机器人返回的单个舵机的版本信息。
    返回：
    geer_id:舵机ID
    version:舵机版本号
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 42: #0x2A
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    geer_id = response[4]
    version = response[5:9]

    if version[0]==0x88:
            print('错误：%d号舵机没有响应！'%(geer_id))
    else:
        version = str(unpack('i', version)[0])
    if tips:
        print('%d号舵机的版本号为：%s'%(geer_id, version))
    return geer_id, version

def get_all_geer_version_cmd():
    '''
    功能：生成读取所有舵机版本命令。
    输入：空
    返回：
    cmd：读取所有舵机版本命令。
    '''          
    cmd = packageCommand([0], 'all_geer_version')
    return cmd

def parsing_all_geer_version(response, tips=False):
    '''
    功能：解析所有舵机版本信息：
    输入：
    response：机器人返回的所有舵机版本信息。
    返回：
    geer_nums:舵机数量
    versions:所有舵机的版本号
    '''
    if response==b'':
        print('回应内容为空，请重新获取回应！')
        return
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 43: #0x2B
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    feedback = response[4:cmd_len-1]
    versions =[]
    geer_nums = len(feedback)//4
    for i in range(geer_nums):
        version = feedback[i*4:(i+1)*4]
        if version[0]==0x88:
                print('错误：%d号舵机没有响应！'%(i+1))
        else:
            version = str(unpack('i', version)[0])
        versions.append(version)
    if tips:
        print('机器人共有{}个舵机，所有舵机的版本号为：\n{}'.format(geer_nums, versions))
    return geer_nums, versions


def parsing_play_end(response, tips=False):
    '''
    功能：解析停止播放命令的回应内容：
    输入：
    response：停止播放命令执行后机器人的回应内容。
    返回：
    action_name:机器人当前执行的动作表名称
    '''
    if response==b'':
        return response
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 49: #0x31
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return 0
    action_name = bytes.decode(response[4:(cmd_len-1)], encoding= 'gbk')
    if tips:
        print('动作“%s”已执行完毕！'%(action_name))
    return action_name


def get_play_and_charge_cmd(switch):
    '''
    功能：生成边玩边充控制命令。
    输入：
    switch：根据switch内容控制机器人是否允许边玩边充。switch数据类型为int，取值范围0或1，0表示不允许，1表示允许。
    返回：
    cmd：边玩边充控制命令。
    '''       
    cmd = packageCommand([switch], 'play_and_charge')
    return cmd

def get_sn_cmd():
    '''
    功能：生成获取机器SN号命令。
    输入：空
    返回：
    cmd：获取机器SN号命令。
    '''       
    cmd = packageCommand([0], 'get_sn')
    return cmd

def parsing_sn(response, tips=False):
    '''
    功能：解析机器人SN号。
    输入：
    response：机器人返回的sn号信息。
    返回：
    version:机器人SN号。
    '''
    if response==b'':
        return
    version = ''
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 51:  #0x33
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return
    feedback = response[4:cmd_len-1]
    if len(feedback)==1:
        version = 'null'
    else:
        num = len(feedback)//4
        feedback = unpack('%di'%(num), response[4:16])
        for v in feedback:
            version += str(v)
    if tips:
        print('机器人的SN号为：%s'%(version))
    return version

def get_udid_cmd():
    '''
    功能：生成获取主芯片UDID号命令。
    输入：空
    返回：
    cmd：获取主芯片UDID号命令。
    '''       
    cmd = packageCommand([0], 'get_udid')
    return cmd

def parsing_udid(response, tips=False):
    '''
    功能：解析主芯片UDID号。
    输入：
    response：机器人返回的udid信息。
    返回：
    version:机器人主芯片UDID号。
    '''
    if response==b'':
        return
    version = ''
    cmd_len = response[2]
    cmd_type = response[3]
    if cmd_type != 52:  #0x34
        print('解析类型错误，请检查回应内容，当前命令类型为%d'%cmd_type)
        return
    feedback = response[4:cmd_len-1]
    if len(feedback)==1:
        version = 'null'
    else:
        num = len(feedback)//4
        feedback = unpack('%di'%(num), response[4:16])
        for v in feedback:
            version += str(v)
    if tips:
        print('机器人的UDID号为：%s'%(version))
    return version
