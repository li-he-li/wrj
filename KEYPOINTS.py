import mediapipe as mp
import cv2


class Mpkeypoints:
    '''
    获取人体Poss·
    '''
    def __init__(self):

        #实例化
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,min_tracking_confidence=0.5)
        
    def getFramePost(self,image):
        '''
        获取每一帧画面的关键点
        '''
        #推理
        results = self.pose.process(image)

        return results.pose_landmarks