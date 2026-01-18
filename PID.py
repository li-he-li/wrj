import time



class simple_PID:
    def __init__(self,pid_paras_list):
        #初始化参数配置
        self.kp=pid_paras_list[0]
        self.ki=pid_paras_list[1]
        self.kd=pid_paras_list[2]
        #记录上一次误差
        self.previous_error=0
        #上一次记录时间，用来计算dt
        self.previous_record_time=time.time()
        #积分
        self.integral=0
    def setParas(self,which='p',add_val=0.01):
        #重新设置参数
        if which=='p':
            self.kp=round(self.kp+add_val,2)
        elif which=='i':
            self.ki=round(self.ki+add_val,2)
        elif which=='d':
            self.kd=round(self.kd+add_val,2)
        #重新初始化参数
        self.previous_error=0
        self.previous_record_time=time.time()
        self.integral=0
        #返回变更后的参数列表
        return [self.kp,self.ki,self.kd]
    def update(self,current_error,min_val=-100,max_val=100):
        #更新参数，得到输出值
        #误差 观测值 传过来的参数
        error=current_error
        #微分：速度=距离/dt
        now=time.time()
        dt=(now-self.previous_record_time)
        derivative=(error-self.previous_error) / dt
        #积分
        self.integral=self.integral+error*dt
        #更新状态
        self.previous_error=error
        self.previous_record_time=now
        #计算结果
        output=self.kp*error+self.ki*self.integral+self.kd*derivative
        #控制输出的最大值最小值
        if output>max_val:
            output=max_val
        if output<min_val:
            output=min_val
        return output
