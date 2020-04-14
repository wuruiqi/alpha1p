#!/sur/bin/python
#coding:utf-8

import usb
import pickle
import time
import pandas as pd
# from pygame import mixer
import multiprocessing
import serial

__all__ = ['establish_usb_connection', 'establish_bt_connection', 'execute_csv_only', 'conn_and_execute_csv',
           'play_mp3', 'dance_with_song']

def establish_usb_connection(Vendor=0x0483, Product=0x5750):
    """use pyusb module to establish usb communication between alpha1S and PC
    
    raise(handled): OSError : [Errno 16] Resource busy
    return: a device handler and ep
    """
    
    try:
        dev = usb.core.find(idVendor=Vendor, idProduct=Product)
        if dev is None:#判断是否识别到该设备
#             print("请确认alpha1S机器人已开机并且usb连接正常后重试")
            return
        if dev.is_kernel_driver_active(0):
            reattach = True
            dev.detach_kernel_driver(0)
        try:
            dev.set_configuration()
        except usb.core.USBError:
            dev.reset()
        ep = dev[0][(0,0)][1].bEndpointAddress
        r_ep = dev[0][(0,0)][0].bEndpointAddress
        r_ps = dev[0][(0,0)][0].wMaxPacketSize
    except usb.core.USBError:
        print("请将usb重新拔插，或者重启机器人后重试")
        return 
    return dev, ep, r_ep, r_ps

def establish_bt_connection(port = "/dev/cu.Alpha1_E983-SerialPort", Baud_rate=9600, timeout=0.5, tips=True):
    """use serial module to establish bluetooth communication between alpha1S and PC
    
    raise(handled): OSError: [Errno 16] Resource busy
    return: a device handler
    """
       
    try:
        dev = serial.Serial(port, Baud_rate, timeout=timeout)
        try:
            if dev.isOpen():
                if tips:
                    print('串口连接已经成功！')
        except Exception as e:  # 捕获异常输出并终止运行
            if tips:
                print('硬件连接失败:{}'.format(e))
            return 0
    except Exception as e:
        if tips:
            print('硬件调试连接操作出错:{}\n请确定机器人已与pc完成串口连接，或者重启机器人后重试!'.format(e))
        return 0
    return dev

        
def execute_csv_only(path, dev, ep, debug = False):
    """
    path:
    dev: device handler
    """
    df = pd.read_csv(path)
    for i in range(len(df)):
        _, _, _, action, runTime, totalTime = df.loc[i]
        cmd = {'jointAngle':tuple(eval(action)),'runTime':runTime,'totalTime':totalTime}
        if debug:
            print(cmd['jointAngle'][:16], runTime, totalTime)
        dev.write(ep, serial.to_bytes(TransCmd(cmd)))
        time.sleep(totalTime/1000.)
    
        
def conn_and_execute_csv(csv_path):
    """
    csv_path: file name end with .csv
    """
    dev,ep = establish_usb_connection()
    execute_csv_only(csv_path, dev, ep)
    
    
def play_mp3(mp3_path):
    mixer.init()
    mixer.music.load("../"+mp3_path)
    mixer.music.play()
    
    
def dance_with_song(mp3_path):#这部分之后再修改
    """
    this function searchs the mp3_path file and coreesponding .csv file in defalut directory (m2d/)
    then it will call establish_usb_connection function to establish communication between 
    alpha1S and PC.
    finally, it plays the mp3 file and execute the actions specified in .csv file
    
    mp3_path: relative path under m2d/ ,should be ending with .mp3 suffix
    """
    
    dev,ep = establish_usb_connection()
    csv_path = "{}.csv".format(path[:-4])
    play_csv = lambda csv_path: execute_csv_only(csv_path,dev, ep)
    
    p1 = multiprocessing.Process(target = play_mp3, args = (mp3_path,))
    p2 = multiprocessing.Process(target = play_csv, args = (csv_path,))
    try:
        p1.start()
        p2.start()
    except IOError:
        print("check directory name and file name")
        return 
    
    
