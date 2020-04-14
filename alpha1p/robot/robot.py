#coding:utf-8
from .control import *
from .bthandler import *
import serial
import time
import usb
import serial.tools.list_ports
import threading
import sys

__all__ = ['Alpha1S']

INIT_STAND = {
    'runTime': 1200,
    'totalTime':1200,
    'jointAngle': [90, 90, 90, 90, 90, 90, 90, 60, 76, 110, 90, 90, 120, 104, 70, 90]
}

#from 黑猫警长
LAST_SLAUTE = [[[90, 90, 90, 90, 90, 90, 90, 60, 76, 110, 90, 90, 120, 104, 70, 90, 90, 90, 90, 90],1500,1500],
[[120, 40, 59, 133, 133, 107, 90, 57, 140, 70, 90, 90, 125, 46, 108, 90, 90, 90, 90, 90],1500,1500],
[[120, 35, 39, 133, 163, 157, 90, 57, 140, 70, 90, 90, 125, 46, 108, 90, 90, 90, 90, 90],800,1500],
[[120, 40, 59, 133, 133, 107, 90, 57, 140, 70, 90, 90, 125, 48, 107, 90, 90, 90, 90, 90],800,800],
[[90, 35, 48, 90, 154, 130, 90, 60, 76, 110, 90, 90, 120, 104, 70, 90, 90, 90, 90, 90],800,800]]
        
    

def lock(func):
    def wrapper(self, *args, **kwargs):  # 指定宇宙无敌参数       
        self.lock.acquire()
#         print("[DEBUG]: enter {}()".format(func.__name__))
        resut = func(self, *args, **kwargs)
#         print("End {}()".format(func.__name__))
        self.lock.release()  

        return resut
    return wrapper  # 返回

def get_input(options=['y','n']):
    value = ''
    while value not in options:
        value = input()
    return value

class DaemonThread(threading.Thread):

    def __init__(self, robot, time):
        threading.Thread.__init__(self)
        self.robot = robot
        self.heat_time = time

    # 使用守护线程保证机器人在线
    def run(self):
        print('守护线程已经启动！')
        
        while self.robot.is_alive:
            time.sleep(self.heat_time)
            response = self.robot.get_response()
            if response!=b'':
                single_type =[1, 3, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 24, 25, 32, 34,
                                      35, 36, 37, 38, 39, 40, 41, 42, 43, 49, 50, 51, 52]
                while len(response)!=0:
                    success = True
                    try:
                        p_start = response.index(b'\xfb\xbf',0)
                        cmd_len = response[p_start+2]
                        cmd_type = response[p_start+3]
                        end = p_start+cmd_len

                        if cmd_type in single_type:
                            pass
                        elif cmd_type ==2:
                            while True:
                                try:
                                    tmp_start = response.index(b'\xfb\xbf\x06\x81', end)
                                    end = tmp_start+6
                                    break
                                except ValueError:
                                    response += self.robot.get_response()
                                    continue
                        elif cmd_type ==10:
                            while cmd_type ==10:
                                try:
                                    tmp_start = response.index(b'\xfb\xbf', end)
                                    cmd_len = response[tmp_start+2]
                                    cmd_type = response[tmp_start+3]
                                    if cmd_type==10:
                                        end = tmp_start+ßcmd_len
                                    else:
                                        break
                                except ValueError:
                                    break
                        else:
                            print('发现未知命令，命令内容为：%s',response[p_start:end+1])
                            success = False
                        if success:
                            parsing_all_response(response[p_start:end+1])
                        response = response[end+1:]
                    except ValueError:
                        end = len(response)
                        response = response[end+1:]
            else:
                flag = self.robot.heart_beat()
                if not flag:
                    self.robot.lock.acquire()
                    self.robot.is_alive = False
                    print('机器人连接已断开，正在尝试重新连接。。。')                
                    #自动重连
                    self.reconnect_robot_automatic()
                    #尝试手动连接
                    if not self.robot.is_alive:
                        print('机器人自动重连失败，请手动关闭机器人再次尝试连接!')
                        print('请选择是否手动重启？y/n')
                        confirm = get_input()
                        while confirm == 'y':
                            self.reconnect_robot_manually()
                            confirm = 'end'
                            if not self.robot.is_alive:
                                print('手动连接失败，是否再次尝试手动连接？y/n')
                                confirm = get_input()
                    self.robot.lock.release()
        return
                            
    def reconnect_robot_automatic(self, times=3):
        con_num = 1
        while con_num <=times:
            print('正在进行第%d次尝试连接。。。'%(con_num))
            time.sleep(2)
            self.robot.connect_to_PC(tips=False)
            if self.robot.dev!=0:
                self.robot.is_alive = True
                print('机器人已重新连接！')
                break
            else:
                con_num+=1
        return
    
    def reconnect_robot_manually(self, times=3):
        print('机器人是否已完成手动重启？y/n')
        confirm_2 = get_input()
        if confirm_2=='y':
            self.reconnect_robot_automatic()
        return

class Alpha1S:

    def __init__(self, con_type, vendor=0x0483, product=0x5750, port = "/dev/cu.Alpha1_E983-SerialPort", baud_rate=9600, timeout=0.5):
        self.con_type = con_type
        self.vendor = vendor
        self.product = product
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.execute_action = self.multi_control
        self.lock = threading.RLock()
        self.sound_status=self.play_status=self.sound_size=self.light_status=self.tf_card = None

        if self.con_type == 'usb':
            self.get_response = self.__usb_get_response
        elif self.con_type == 'bt':
            self.get_response = self.__bt_get_response
        else:
            print('请选则正确的连接类型：\'usb\'或者\'bt\’，目前连接类型为：%s', self.con_type)
        self.connect_to_PC()
        if self.dev==0:
            sys.exit(0)
        self.handshake()
        self.get_robot_status()
        self.version = 'Soft Version:{}    Hard Version:{}'.format(self.__soft_version(), self.__hard_version())
        self.get_udid(tips=False)
        self.get_sn(tips=False)
        self.open_daemon_thread(20)
        
    def connect_to_PC(self, tips=True):
        if self.con_type == 'usb':

            try:
                self.dev, self.ep, self.r_ep, self.r_ps = establish_usb_connection(self.vendor, self.product)
                self.__clear_usb_output(tips=False)
                self.change_usb_type(usb_write=True)
                time.sleep(1)
            except TypeError as e:
                pass
            port_list = list(serial.tools.list_ports.comports())
            self.port = port_list[-1][0]
#             self.port = "/dev/cu.usbmodem48E1717838361"
            

        self.dev = establish_bt_connection(self.port, self.baud_rate, self.timeout, tips=tips)
        return 
    
    def reset(self):

        self.__init__(self.con_type)
        if self.dev!=0:
            rec_con = True
            print('机器人已重新连接！')
        else:
            rec_con = False
        return rec_con

    def __usb_output(self):
        """
        读取机器人的输出
        """
        response = self.dev.read(self.r_ep, self.r_ps)
        return response

 
    def read(self):
        """
        读取机器人的输出
        """
        response = self.dev.read_all()
        return response
   
    def write(self, cmd):
        '''
        功能：以Bluetooth形式执行单个命令。
        输入：单个执行命令。
        '''
        self.dev.write(cmd)
        return

    def __usb_write(self, cmd):
        '''
        功能：以Bluetooth形式执行单个命令。
        输入：单个执行命令。
        '''
        self.dev.write(self.ep, cmd)
        return

    @lock
    def __usb_get_response(self, duration=0, timeout=1000):
        response = b''  
        i = 0
        if duration!=0:
            timeout = duration/100
        else:
            timeout = timeout/100     
            
        while True:
            tmp = self.dev.read(64)
            if tmp !=b'':
                response += usb_reformat_response(tmp)
            else:
                break
                
        while response == b'' or duration!=0:
            while True:
                tmp = self.dev.read(64)
                if tmp !=b'':
                    response += usb_reformat_response(tmp)
                else:
                    break
            if i>=timeout:
                break
            time.sleep(0.1)
            i += 1
        return response
    
    @lock
    def __bt_get_response(self, duration=0, timeout=1000):
        response = b''
        i = 0
        if duration!=0:
            timeout = duration/100
        else:
            timeout = timeout/100
        response = self.read()
        while response == b'' or duration!=0:
            while True: 
                tmp = self.read()
                if tmp !=b'':
                    response += tmp
                else:
                    break
            if i>=timeout:
                break
            time.sleep(0.1)
            i += 1
        return response
    
    def clear_output(self, tips=False, duration=0, timeout=100):
        self.__bt_get_response(duration, timeout)
        if tips:
            print('机器人输出管道已初始化！')
        return
    
    @lock
    def change_usb_type(self, c_type=2, usb_write=False):
        '''
        功能：更改机器人与pc的USB连接类型。
        输入：
        c_type：USB连接类型，数据格式为int。取值范围1~3，1：U盘模式；2：VCP模式：3：HID模式。
                pyusb默认连接为HID模式，因此本函数默认更改为VCP模式。
        返回：空
        '''
        cmd_list = [249,159]      # 先放入命令头 F9=249  9F=159
        parameters = [c_type, 0, 0, 0, 0, 0]
        for x in parameters:       # 放入参数数据
            cmd_list.append(x)
        checkSum = 0    
        for x in cmd_list[2:]:
            checkSum += x
        cmd_list.append(checkSum%256)   # 放入check码
        cmd_list.append(237)       # 放入结束标志ED = 237
        cmd = serial.to_bytes(cmd_list)
        if usb_write:
            self.__usb_write(cmd)
        else:
            self.write(cmd)
        return
        
    def open_daemon_thread(self, heart_time=20):
        '''
        功能：开启守护线程，防止机器人断线
        输入：
        heart_time:心跳包发送间隔时间，单位s。
        返回：空
        '''             
        self.heart_time = heart_time
        self.is_alive = True
        self.Daemon = DaemonThread(robot=self, time=heart_time)
        self.Daemon.start()
        return
    
    def close_daemon_thread(self):
        '''
        功能：关闭守护线程。
        输入：空
        返回：空
        '''             
        self.is_alive = False
        time.sleep(self.heart_time)
        return        
               
    @lock
    def execute_actions(self, list_actions):
        """
        list_actions:　必须是列表形式的动作序列，如以上的last_slaute
        """
        for item in list_actions:
            cmd = {'jointAngle':item[0],'runTime':item[1],'totalTime':item[2]}
            self.multi_control(cmd)
            time.sleep((item[2]-40)/1000.) 
        return
    
     
    def stand(self):
        self.execute_action(INIT_STAND)
        return
        
        
    def salute(self):
        self.execute_actions(LAST_SLAUTE)
        return
        
#     def _symmetric(self, act):
#         """
#         输入act应该是一个list,只包括每个关键的值(至少是16维)
#         函数返回一个和这个动作对称的动作，形式和act一样
#         """
#         sym_a = act[:]
#         sym_a[:3] = [180 - x for x in act[3:6]]
#         sym_a[3:6] = [180 - x for x in act[:3]]
#         sym_a[6:11] = [180 - x for x in act[11:16]]
#         sym_a[11:16] = [180 - x for x in act[6:11]]
#         return sym_a
    
    
#     def execute_symmetric(self, acts):
#         """
#         acts是一个动作序列列表，每行是动作关节值，runTime, totalTime
#         该函数执行这个动作序里的对称动作序列
#         """
#         sym_actions = []
#         for a in acts:
#             sym_actions.append([self._symmetric(list(a[0])),a[1],a[2]])
#         self.execute_actions(sym_actions)
        
#     def repeat_actions(self, acts):
#         """
#         这个函数重复执行acts中的动作
#         """
#         while 1:
#             self.execute_actions(acts)
            
#     def execute_csv(self, path, debug = False):
#         execute_csv_only(path, self.dev, self.ep, debug)
        
    
    def power_on_single(self, joint_id):        
        '''
        功能：为单个舵机恢复加电状态。
        输入：
        joint_id：舵机ID
        返回：空
        '''
        angle = self.read_back_single(joint_id)
        cmd = {'joint_id':joint_id, 'jointAngle':angle, 'runTime':400, 'totalTime':400}
        self.single_control(cmd)
        return
    
    def power_on_all(self):        
        '''
        功能：为所有舵机恢复加电状态。
        输入：空
        返回：空
        '''
        angles = self.read_back_all()
        cmd = {'jointAngle':angles, 'runTime':400, 'totalTime':400}
        self.multi_control(cmd)
        return
    
    @lock        
    def handshake(self):
        '''
        功能：连接机器人之后与机器人进行握手操作，获取机器人的名字。
        输入：空
        返回：机器人的名字。
        '''
        action_name = b''
        cmd = packageCommand([0], 'handShake')
        self.clear_output()
        self.write(cmd)
        if self.con_type=='bt':
            timeout = 1500
        response = self.get_response(duration=timeout)
        if len(response)==17:
            self.name = parsing_handshake(response)
        elif len(response)>17:
            self.name = parsing_handshake(response[:17])
            action_name = parsing_play_end(response[17:])
        else:
            print(response)
            print('与机器人握手失败，请重试！')
        print('Action name:%s\n'%action_name)
        if self.con_type=='bt':
            print('当前通信方式为蓝牙串口通信！')
        else:
            print('当前通信方式为USB串口通信！')
        return

    @lock
    def get_action_list(self,recept_time=4):
        '''
        功能：获取机器人本机的动作表。
        输入：空
        返回：动作表，数据格式：list。
        '''
        cmd = packageCommand([0], 'get_action_list')
        self.clear_output()
        self.write(cmd)
        response =b''
        while True:
            response += self.get_response()
            try:
                action_list = parsing_get_action_list(response)
                break
            except ValueError:
                continue
        action_list = parsing_get_action_list(response)
        return action_list
    
    @lock
    def execute_action_table(self, action_name):
        '''
        功能：执行机器人上面的一个动作表。
        输入：
        action_name:动作表名称，数据类型为str
        返回：是否执行成功。
        '''
        self.is_runing = True
        cmd = packageCommand(action_name.encode(encoding= 'gbk'), 'execute_action_table')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        parsing_execute_action_table(response)
        return
    
    @lock    
    def stop(self, tips=True):
        '''
        功能：停止机器人正在执行的动作表。
        输入：空
        返回：空。
        '''
#         if not self.is_runing:
#             print('当前未执行动作表！')
#             return
        cmd = packageCommand([0], 'stop_play')
        self.clear_output()
        self.write(cmd)
        if tips:
            response = self.get_response()
            if len(response)==7:
                response += self.get_response()
            action_name = parsing_play_end(response[7:])
            if response[3] ==5 and response[4]==1:
                if action_name!=b'':
                    print('机器人已停止运动，动作表“%s”已结束执行！'%action_name)
                else:
                    print('停止指令执行成功，机器人已停止行动！')
            else:
                print('机器人停止指令执行失败！')
                return
        else:
            self.clear_output(timeout=1000)
        return
    
  
    def turn_on_sound(self, tips=False):
        self.__sound_switch(1, tips)
        return
       
    def turn_off_sound(self, tips=False):
        self.__sound_switch(0, tips)
        return
    
    @lock    
    def __sound_switch(self, switch, tips=False):
        '''
        功能：机器人声音开关。
        输入：
        switch:根据switch内容控制机器人声音开关。switch数据类型为int，取值范围0或1，为0时关闭声音，当为1时打开声音。
        返回：空。
        '''
        cmd = packageCommand([switch], 'sound_switch')
        self.write(cmd)
        self.clear_output(timeout=1000)
        return

    def play(self):
        self.__play_switch(1)
        return
    
    def pause(self):
        self.__play_switch(0)
        return
    
    @lock
    def __play_switch(self, switch):
        '''
        功能：机器人播放开关。
        输入：
        switch:根据switch内容控制机器人运动或者暂停。switch数据类型为int，取值范围0或1，当为0时暂停播放，为1时继续播放。
        返回：空。
        '''

        cmd = packageCommand([switch], 'play_switch')
        self.write(cmd)
        self.clear_output(timeout=1000)
        return
    
    @lock
    def heart_beat(self):
        '''
        功能：向机器人发送心跳包命令。
        输入：空
        返回：确定机器人在线。
        '''
        response = b''
        i = 0
        cmd = packageCommand([0], 'heart_beat')
        self.clear_output()
        try:
            self.write(cmd)
        except OSError:
            return False
        response = self.get_response()
        flag = parsing_heart_beat(response)
        return flag
    
    @lock
    def get_robot_status(self, tips=True):
        '''
        功能：获取机器人当前状态信息。
        输入：空
        返回：空
        '''
        response = b''
        i = 0
        cmd = packageCommand([0], 'robot_status')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        self.is_mute, self.play_status, self.sound_size, self.light_status, self.tf_card = parsing_get_robot_status(response)
        if tips:
            mute_s = '是' if self.is_mute else '否'
            play_s = '播放中' if self.play_status else '暂停中'
            light_s = '开' if self.light_status else '关'
            tf_s = '已插入' if self.tf_card else '已拔出'
            print('======机器人当前状态======\n静音: %s\n状态: %s\n音量: %d\n灯光: %s\n内存卡: %s' %
                  (mute_s, play_s, self.sound_size, light_s, tf_s))
        return
    
    @lock
    def set_sound(self, size):
        '''
        功能：设置机器人音量。
        输入：
        size：音量大小，取值范围为0~100。
        返回：空。
        '''
        response = b''
        if size>100:
            size=100
        elif size<0:
            size=0
        self.sound_size = size
        size = int(255*size/100)
        cmd = packageCommand([size], 'set_sound')
        self.write(cmd)
        self.clear_output(timeout=1000)
        return
    
    @lock    
    def power_down(self):
        '''
        功能：所有舵机进行掉电操作。
        输入：空
        返回：空。
        '''
        cmd = packageCommand([0], 'power_down')
        self.write(cmd)
        self.clear_output(timeout=1000)
        return
    
    def turn_on_light(self, tips=False):
        self.__light_switch(1, tips)
        return
    
    def turn_off_light(self, tips=False):
        self.__light_switch(0, tips)
        return    
    
    @lock
    def __light_switch(self, switch, tips=False):
        '''
        功能：机器人灯光开关。
        输入：
        switch:根据switch内容控制机器人的灯光。switch数据类型为int，取值范围0或1，当为0时打开灯光，为1时关闭灯光。
        返回：空。
        '''
        cmd = packageCommand([switch], 'light_switch')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        if len(response)==15 and response[3]==13:
            response = response[7:]
        elif len(response)==7 and response[3]==13:
            response = self.get_response()
        self.light_status = bool(response[5])
        if tips:
            if self.light_status:
                print('舵机灯已打开！')
            else:
                print('舵机灯已关闭！')
        return
    
    @lock    
    def sync_time(self):
        '''
        功能：同步机器人的时钟。
        输入：空
        返回：空。
        '''
        cmd = get_set_time_cmd(time.localtime())
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        if response==b'':
            print('机器人没有应答，时钟可能设置失败，请重试！')
        else:
            if response[4]==1:
                print('时钟设置失败，请重试！')        
        return
    
    @lock    
    def read_alarm(self, is_call=False, tips=True):
        '''
        功能：读取机器人的闹钟。
        输入：空
        返回：空。
        '''
        cmd = packageCommand([0], 'read_alarm')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        alarm = parsing_read_alarm(response)
        if is_call:
            return alarm
        if tips:
            switch = '开' if alarm['switch'] else '关'
            every_day = '开' if alarm['every_day'] else '关'
            times = '{}:{}:{}'.format(str(alarm['hour']).rjust(2,'0'), 
                                      str(alarm['min']).rjust(2,'0'), str(alarm['sec']).rjust(2,'0'))
            print('======机器人闹钟======\n闹钟开关: %s\n每日重复: %s\n响铃时间: %s\n闹钟舞蹈: %s\n' %
                  (switch,  every_day, times, alarm['action_name']))        
        return
    
    @lock    
    def set_alarm(self,switch=None, every_day=None, hour=None, 
                  minute=None, sec=None, action_name=None, tips=False):
        '''
        功能：设置机器人的闹钟。
        输入：
        switch:闹钟开关，数据格式bool。
        every_day:是否每天开启闹钟，数据格式bool。
        hour:时，数据格式int，取值范围0~23。
        minute:分，数据格式int，取值范围0~59。
        sec:秒，数据格式int，取值范围0~59。
        action_name:舞蹈名称，数据格式string。
        tips:是否验证设置成功，数据格式bool。
        返回：空。
        '''     
        alarm = self.read_alarm(is_call=True)
        if switch is not None:
            alarm['switch'] = switch
        if every_day is not None:
            alarm['every_day'] = every_day            
        if hour is not None:
            if hour<0:
                hour = 0
            elif hour>23:
                hour = 23
            alarm['hour'] = hour
        if minute is not None:
            if minute<0:
                minute = 0
            elif minute>59:
                minute = 59
            alarm['min'] = minute
        if sec is not None:
            if minute<0:
                minute = 0
            elif minute>59:
                minute = 59
            alarm['sec'] = sec           
        if action_name is not None:
            alarm['action_name'] = action_name   
        cmd = get_set_alarm_cmd(alarm)        
        self.write(cmd)
        if tips:
            alarm_new = self.read_alarm(is_call=True)
            if alarm== alarm_new:
                print('闹钟设置成功！')
            else:
                print(alarm, alarm_new)
                print('闹钟设置失败，请重试！')
        else:
            self.clear_output(timeout=1000)
        return

    def __soft_version(self):
        '''
        功能：获取机器人的软件版本。
        输入：空
        返回：
        version:机器人的软件版本，格式为string
        '''
        cmd = packageCommand([0], 'soft_version')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        version = response[4:14].decode('gbk')       
        return version

    def __hard_version(self):
        '''
        功能：获取机器人的硬件版本。
        输入：空
        返回：
        version:机器人的硬件版本，格式为string
        '''
        cmd = packageCommand([0], 'hard_version')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        cmd_len = response[2]
        version = response[4:cmd_len-1].decode('gbk')       
        return version
    
    @lock
    def power_info(self):
        '''
        功能：获取机器人的电量信息。
        输入：空
        返回：空
        '''
        cmd = packageCommand([0], 'power_info')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        voltage, charging, power = parsing_power_info(response)
        if charging==0:
            charge_info = '当前未充电！'
        elif charging==1:
            charge_info = '正在充电中....'
        elif charging==3:
            charge_info = '机器人没有电池，当前电源供电！'
        else:
            charge_info = '获取电量信息失败！'
        print('电压：{}v\n电量：{}%\n{}'.format(voltage, power, charge_info))    
        return
    
    @lock
    def single_control(self, cmd):
        '''
        功能：控制机器人的单个舵机运动。
        输入：
        cmd：单个舵机运动的命令参数，包括：舵机ID，舵机角度，运行时间，和允许下帧数据时间。
        注意：舵机ID从1开始计算
        返回：空
        '''
        response = b''
        cmd = get_single_control_cmd(cmd)
        self.clear_output()
        self.write(cmd)
        while response==b'':
            response = self.get_response()
        flag = parsing_single_control(response)
        if flag is False:
            print('命令执行失败，请重试！')
            return 0
        return
    
    @lock    
    def multi_control(self, cmd):
        '''
        功能：控制机器人的所有舵机运动。
        输入：
        cmd：多舵机运动的命令参数，包括：所有舵机的角度值，运行时间，和允许下帧数据时间。
        注意：舵机ID从1开始计算
        返回：空
        '''
        response = b''
        cmd = get_multi_control_cmd(cmd)
        self.clear_output()
        self.write(cmd)
        while response==b'':
            response = self.get_response()
        flag = parsing_multi_control(response)
        if flag is False:
            print('命令执行失败，请重试！')
            return 0
        return flag
    
    @lock
    def read_back_single(self, joint_id):
        '''
        功能：回读单个舵机的角度。
        输入：
        joint_id：舵机ID。
        返回：舵机当前的角度。
        '''

        if joint_id not in range(1, 17):
            print('舵机ID错误，舵机ID从1开始计数，必须为1~16中的一个。当前输入ID为：%d' % joint_id)
            return
        cmd = packageCommand([joint_id], 'read_back_single')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        angle = parsing_rb_single(response)
        return angle
    
    @lock    
    def read_back_all(self):
        '''
        功能：回读所有舵机的角度。
        输入：空
        返回：所有舵机的当前角度。
        '''
        cmd = packageCommand([0], 'read_back_all')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        angles = parsing_rb_all(response)
        return angles
    
    @lock
    def set_single_offset(self, geer_id, value):
        '''
        功能：设置单个舵机偏移值的命令。
        输入：
        geer_id:舵机ID， 数据格式：int
        注意：舵机ID从1开始计算
        value:舵机的偏移值， 数据格式：int
        返回：空
        '''
        response = b''
        cmd = get_set_single_offset_cmd(geer_id, value)
        self.clear_output()
        self.write(cmd)
        while response==b'':
            response = self.get_response()
        flag = parsing_set_single_offsset(response)
        if flag is False:
            print('命令执行失败，请重试！')
            return 0
        return
    
    @lock    
    def set_all_offset(self, offset_values):
        '''
        功能：设置所有舵机偏移值的命令。
        输入：
        offset_values:所有舵机的偏移值，数据格式：list
        返回：空
        '''
        response = b''
        cmd = get_set_all_offset_cmd(offset_values)
        self.clear_output()
        self.write(cmd)
        while response==b'':
            response = self.get_response()
        flag = parsing_set_all_offsset(response)
        if flag is False:
            print('命令执行失败，请重试！')
            return 0
        return
    
    @lock    
    def read_single_geer_offset(self, geer_id, tips=False):
        '''
        功能：读取单个舵机的偏移值
        输入：
        geer_id:舵机ID
        返回：
        value:舵机的偏移值。
        '''
        cmd = packageCommand([geer_id], 'read_single_offset')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        geer_id, value = parsing_read_single_offsset(response)
        if tips:
            print('%d号舵机的版本号为：%s'%(geer_id, value))
        return value
    
    @lock
    def read_all_geer_offset(self, tips=False):
        '''
        功能：读取所有舵机的偏移值
        输入：空
        返回：
        geer_nums:舵机数量
        versions:所有舵机的偏移值
        '''
        cmd = packageCommand([0], 'read_all_offset')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        geer_nums, values = parsing_read_all_offsset(response)
        if tips:
            print('===========机器人共有%d个舵机，各舵机的偏移值如下：==========='%(geer_nums))
            for i in range(geer_nums//2):
                print('{}号舵机：{}                  {}号舵机：{}'.format(str((i*2)+1).rjust(2,'0'),
                                                                  values[i*2], str((i*2)+2).rjust(2,'0'), 
                                                                  values[(i*2)+1]))
        return geer_nums, values
    
    @lock    
    def single_geer_version(self, geer_id, tips=False):
        '''
        功能：读取单个舵机的版本号
        输入：
        geer_id:舵机ID
        返回：
        version:舵机的版本号。
        '''
        cmd = packageCommand([geer_id], 'single_geer_version')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        geer_id, version = parsing_single_geer_version(response)
        if tips:
            print('%d号舵机的版本号为：%s'%(geer_id, version))
        return version
    
    @lock
    def all_geer_version(self, tips=False):
        '''
        功能：读取所有舵机的版本号
        输入：空
        返回：
        geer_nums:舵机数量
        versions:所有舵机的版本号
        '''
        cmd = packageCommand([0], 'all_geer_version')
        self.clear_output()
        self.write(cmd)
        response = self.get_response()
        geer_nums, versions = parsing_all_geer_version(response)
        if tips:
            print('===========机器人共有%d个舵机，各舵机的版本号如下：==========='%(geer_nums))
            for i in range(geer_nums//2):
                print('%s号舵机：%s                  %s号舵机：%s'
                      %(str((i*2)+1).rjust(2,'0'),versions[i*2], str((i*2)+2).rjust(2,'0'), versions[(i*2)+1]))
        return geer_nums, versions
    
    @lock    
    def play_and_charge(self, switch, tips=True):
        '''
        功能：控制机器人是否允许边玩边充。
        输入：
        switch:根据switch内容控制机器人边玩边充开关。switch数据类型为int，取值范围0或1，0表示不允许，1表示允许。
        返回：空。
        '''
        cmd = packageCommand([switch], 'play_and_charge')
        self.write(cmd)
        self.clear_output(timeout=1000)
        if tips:
            p_s = '已开启' if switch else '已关闭'
            print('边玩边充功能%s！'%p_s)
    
    @lock
    def get_sn(self, tips=True):
        '''
        功能：获取机器人的sn号。
        输入：空
        返回：空
        '''
        cmd = packageCommand([0], 'get_sn')
        self.write(cmd)
        response = self.get_response()
        self.SN = parsing_sn(response)
        if tips:
            print('机器人的SN号为：%s'%self.SN)
        return
    
    @lock        
    def get_udid(self, tips=True):
        '''
        功能：获取机器人的udid号。
        输入：空
        返回：空
        '''
        cmd = packageCommand([0], 'get_udid')
        self.write(cmd)
        response = self.get_response()
        self.UDID = parsing_udid(response)
        if tips:
            print('机器人的UDID号为：%s'%self.UDID)
        return
        
    

    
    

        