import cv2
import os
from djitellopy import Tello
import threading
import queue
import torch
from multiprocessing import Process, Value, Manager
import time
import ctypes
import socket

# Tello default IP (AP Mode). Change this if you are using Station Mode.
TELLO_IP = '192.168.10.1' 


# 创建一个TelloController类，用于控制Tello无人机
class TelloController:
    def __init__(self, tello, shared_dict):
        # 初始化Tello连接
        self.tello = tello
        self.tello.connect()
        self.tello.streamon()
        self.tello.get_height()
        self.frame_reader = self.tello.get_frame_read()
        time.sleep(2)  # 等视频流稳定


        # 创建一个共享整数值，用于控制飞行命令
        self.flight_control_command = Value(ctypes.c_int, -1)
        # 使用 maxsize=1 的队列，确保只保留最新命令
        self.command_queue = queue.Queue(maxsize=1)
        # 记录上一次执行的命令和时间，用于去重和防抖
        self.last_command = None
        self.last_command_time = 0
        self.command_cooldown = 0.5  # 同一命令的冷却时间（秒）

        # 创建两个事件，用于控制进程的执行
        self.process_frame_event = threading.Event()
        self.execute_command_event = threading.Event()
        self.execute_command_event.set()  # 设置执行命令的事件为True

    # 处理摄像头帧
    def process_frame(self, frame, model):
        frame = cv2.flip(frame, 1)  # 水平翻转帧
        frame_h, frame_w = frame.shape[:2]
        center_x = frame_w // 2
        center_y = frame_h // 2
        img_cvt = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # 将帧从RGB转换为BGR格式
        
        # 使用模型检测物体
        results = model(img_cvt)
        results_arr = results.pandas().xyxy[0].to_numpy()

        for item in results_arr:
            time.sleep(0.2)  # 每次检测之间等待一秒钟

            ret_label_text = item[-1]  # 检测到的物体标签
           
            # 清空队列中的旧命令，只保留最新命令
            try:
                while not self.command_queue.empty():
                    self.command_queue.get_nowait()
            except queue.Empty:
                pass
            
            # 将最新命令放入队列（非阻塞）
            try:
                self.command_queue.put_nowait(ret_label_text)
            except queue.Full:
                pass  # 队列满则跳过，保留之前的命令
            
            ret_conf = item[-3]  # 检测的置信度
            l, t, r, b = item[:4].astype('int')  # 检测框的坐标
            
            # 在帧上绘制检测框和标签
            cv2.rectangle(frame, (l, t), (r, b), (0, 255, 0), 2)
            cv2.putText(frame,'{} {}%'.format(ret_label_text, round(ret_conf*100,2)), (l, t-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        cv2.imshow("demo", frame)  # 在窗口中显示帧

    # 执行飞行命令
    def execute_command(self):
        while True:
            # 等待执行命令的事件为True，否则阻塞
            self.execute_command_event.wait()
            
            # 使用带超时的方式获取命令，避免永久阻塞
            try:
                command = self.command_queue.get(timeout=0.1)
            except queue.Empty:
                continue  # 没有命令则继续等待
            
            current_time = time.time()
            
            # 命令去重：如果是相同命令且在冷却时间内，跳过执行
            if command == self.last_command and (current_time - self.last_command_time) < self.command_cooldown:
                print(f'跳过重复命令: {command}')
                continue
            
            print('执行命令:', command)
            
            # 更新上一次命令记录
            self.last_command = command
            self.last_command_time = current_time
            
            # 根据检测到的物体和飞行高度执行不同的飞行命令
            if self.tello.get_height() < 5:
                if command == 'takeoff':
                    self.tello.takeoff()  # 起飞命令
                    print('起飞')#握拳，拳心向前#
            else :
                if command == "forward":
                    self.tello.move_forward(100)  # 前进命令
                    print('前进')#手比1#
                elif command == "back":
                    self.tello.move_back(60)
                    print('后退')#手比2#
                elif command == "left":
                    self.tello.move_left(60)
                    print('左移')#手比3#
                elif command == "right":
                    self.tello.move_right(60)
                    print('右移')#手比4#
                elif command == "up":
                    self.tello.move_up(60)
                    print('上升')##大拇哥##
                elif command == "down":
                    self.tello.move_down(60)
                    print('下降')#大拇哥向下#
                # 其他移动命令类似，例如后退、左移、右移、上升、下降
                # 这些命令根据检测到的物体标签执行不同的动作
                elif command == "landoff":
                    self.tello.land()  # 降落命令
                    print('降落')#平掌，掌心向前#

    # 运行视频流处理
    def run_video_stream(self):
        # 获取当前脚本所在目录的绝对路径
        base_path = os.path.dirname(os.path.abspath(__file__))
        # 拼接 yolov5 和 weights 的绝对路径
        yolo_path = os.path.join(base_path, 'yolov5')
        weights_path = os.path.join(base_path, 'weights', 'last_best.pt')

        # 加载YOLO模型
        model = torch.hub.load(yolo_path, 'custom', path=weights_path, source='local')
        model.conf = 0.7  # 设置检测置信度阈值
        
        # 启动飞行命令处理线程
        command_process = threading.Thread(target=self.execute_command)
        command_process.start()

        while True:
            # 设置执行命令的事件为False，防止同时执行
            self.execute_command_event.clear()
            frame = self.frame_reader.frame
              # 获取摄像头帧
            self.process_frame(frame, model)  # 处理帧
            
            if cv2.waitKey(10) & 0xFF == ord("q"):  # 如果按下键盘上的'q'键，退出循环
                break
            # 设置执行命令的事件为True，允许执行新的飞行命令
            self.execute_command_event.set()

if __name__ == '__main__':
    manager = Manager()
    shared_dict = manager.dict()
    
    # Init Tello with configurable IP
    print(f"Connecting to Tello at {TELLO_IP}...")
    tello = Tello(host=TELLO_IP)
    # shared_dict['tello'] = Tello()  # Removed
    
    controller = TelloController(tello, shared_dict)  # 创建TelloController实例
    video_process = threading.Thread(target=controller.run_video_stream)  # 创建视频流处理线程
    video_process.start()  # 启动视频流处理线程
    video_process.join()  # 等待视频流处理线程结束
