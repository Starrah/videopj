import os
import threading
from os import path

from imagebkd.apiutils import RequestHandleFailException
from imagebkd.fileutils import determineDownload
from videopj.settings import MEDIA_ROOT


# 接入神经网络的适配器
NNList = [{"name": "Autoencoder", "param": "autoencoder", "isMultiInput": False},
          {"name": "Curvatures", "param": "curvature", "isMultiInput": False},
          {"name": "Colorization", "param": "colorization", "isMultiInput": False},
          {"name": "Denoising-Autoencoder", "param": "denoise", "isMultiInput": False},
          {"name": "Depth", "param": "rgb2depth", "isMultiInput": False},
          {"name": "Edge-2D", "param": "edge2d", "isMultiInput": False},
          {"name": "Edge-3D", "param": "edge3d", "isMultiInput": False},
          {"name": "Euclidean-Distance", "param": "rgb2mist", "isMultiInput": False},
          {"name": "Inpainting", "param": "inpainting_whole", "isMultiInput": False},
          {"name": "Jigsaw-Puzzle", "param": "jigsaw", "isMultiInput": False},
          {"name": "Keypoint-2D", "param": "keypoint2d", "isMultiInput": False},
          {"name": "Keypoint-3D", "param": "keypoint3d", "isMultiInput": False},
          {"name": "Object-Classification", "param": "class_1000", "isMultiInput": False},
          {"name": "Reshading", "param": "reshade", "isMultiInput": False},
          {"name": "Room-Layout", "param": "room_layout", "isMultiInput": False},
          {"name": "Scene-Classification", "param": "class_places", "isMultiInput": False},
          {"name": "Segmentation-2D", "param": "segment2d", "isMultiInput": False},
          {"name": "Segmentation-3D", "param": "segment25d", "isMultiInput": False},
          {"name": "Segmentation-Semantic", "param": "segmentsemantic", "isMultiInput": False},
          {"name": "Surface-Normal", "param": "rgb2sfnorm", "isMultiInput": False},
          {"name": "Vanishing-Point", "param": "vanishing_point", "isMultiInput": False},
          {"name": "Pairwise-Nonfixated-Camera-Pose", "param": "non_fixated_pose", "isMultiInput": True, "allowPicCount": [2,3]},
          {"name": "Pairwise-Fixated-Camera-Pose", "param": "fix_pose", "isMultiInput": True, "allowPicCount": [2,3]},
          {"name": "Triplet-Fixated-Camera-Pose", "param": "ego_motion", "isMultiInput": True, "allowPicCount": [3,4]},
          {"name": "Point-Matching", "param": "point_match", "isMultiInput": True, "allowPicCount": [2,3]}]


class asyncNN(threading.Thread):
    def __init__(self, images: list, operTypes: list, operObj, allowParallel=True):
        super().__init__()
        from .models import Output
        self.images = images
        self.imageLen = len(self.images)
        if(self.imageLen <= 0):
            raise RequestHandleFailException(400, "您没有提供任何一个有效的图片，因此无法完成操作。请重新选择。")
        if (len(operTypes) <= 0):
            raise RequestHandleFailException(400, "您没有选择任何一个要执行的算法，因此无法完成操作。请重新选择。")
        self.operTypes = operTypes
        self.operObj = operObj
        self.otpList = []
        self.allowParallel = allowParallel
        self.childThreads = []
        self.lock = threading.RLock()
        self.asyncMessages = []
        self.done = []
        self.randomDownloadDirname = path.relpath(determineDownload(None, None), "download")
        for one in NNList:
            self.asyncMessages.append([])
            self.done.append(0)
        for oneOper in self.operTypes:
            output = Output(type=int(oneOper), oper=self.operObj)
            output.save()
            self.otpList.append(output)

    def parallelCallback(self, otp, message, filePath, instance):
        from .models import Output, MoreOutputFile
        with self.lock:
            self.done[otp.type] = self.done[otp.type] + 1
            if message:
                self.asyncMessages[otp.type].append(message)
            otpObj = Output.objects.select_for_update().get(id=otp.id)
            if NNList[otp.type]["isMultiInput"] or self.imageLen == 1:
                otpObj.outputStr = message if message else "已完成"
                otpObj.process = 1
                if filePath and filePath != "":
                    otpObj.outputFilePath = filePath
            elif self.imageLen >= 2:
                otpObj.outputStr = "运行中%d/%d%s" % (self.done[otp.type], self.imageLen, (", " + str(self.asyncMessages[otp.type])) if len(self.asyncMessages[otp.type]) > 0 else "")
                if filePath and filePath != "":
                    MoreOutputFile(filePath=filePath, output=otp).save()
                if self.done[otp.type] >= self.imageLen:
                    otpObj.process = 1
                    otpObj.outputStr = "已完成%s" % ((", " + str(self.asyncMessages[otp.type])) if len(self.asyncMessages[otp.type]) > 0 else "")
            otpObj.save()

    def run(self):
        from .models import Operation, Output
        for otp in self.otpList:
            if NNList[otp.type]["isMultiInput"]:
                outputpath = path.join(MEDIA_ROOT, "download", str(otp.type),
                                       path.relpath(self.images[0], path.join(MEDIA_ROOT, "upload")))
                interfaceObj = NNInterface(self.images, outputpath, otp, self.parallelCallback)
                if self.allowParallel:
                    self.childThreads.append(interfaceObj)
                    interfaceObj.start()
                else:
                    interfaceObj.run()
            else:
                le = len(self.images)
                if le == 1:
                    image = self.images[0]
                    outputpath = path.join(MEDIA_ROOT, "download", str(otp.type), path.relpath(image, path.join(MEDIA_ROOT, "upload")))
                    interfaceObj = NNInterface(image, outputpath, otp, self.parallelCallback)
                    if self.allowParallel:
                        self.childThreads.append(interfaceObj)
                        interfaceObj.start()
                    else:
                        interfaceObj.run()
                elif le >= 2:
                    outputFolder = path.join(MEDIA_ROOT, "download", str(otp.type), self.randomDownloadDirname)
                    if not path.exists(outputFolder):
                        os.makedirs(outputFolder)
                    otpObj = Output.objects.select_for_update().get(id=otp.id)
                    otpObj.outputStr = "运行中%d/%d" % (0, le)
                    otpObj.outputFilePath = outputFolder
                    otpObj.save()
                    for image in self.images:
                        outputpath = path.join(outputFolder, path.relpath(image, path.join(MEDIA_ROOT, "upload")))
                        if not path.exists(path.dirname(outputpath)):
                            os.makedirs(path.dirname(outputpath))
                        interfaceObj = NNInterface(image, outputpath, otp, self.parallelCallback)
                        if self.allowParallel:
                            self.childThreads.append(interfaceObj)
                            interfaceObj.start()
                        else:
                            interfaceObj.run()
                else:
                    raise RequestHandleFailException(400, "没有有效的可操作文件！")
        if self.allowParallel:
            flag = True
            while flag:
                flag = False
                for th in self.childThreads:
                    if th.is_alive():
                        flag = True
                        break
        self.operObj = Operation.objects.select_for_update().get(id=self.operObj.id)
        self.operObj.process = 1
        self.operObj.save()


class NNInterface(threading.Thread):
    def __init__(self, inputPath, outputPath, otpObj, messageCallback=None):
        super().__init__()
        self.inputPath = inputPath
        self.outputPath = outputPath
        self.otpObj = otpObj
        self.messageCallback = messageCallback


    def run(self):
        res, filePath = self.NNCall()
        if self.messageCallback:
            self.messageCallback(self.otpObj, res, filePath, self)
        return res


    # 网络的核心方法：根据给定的输入输出路径和操作类型调用work函数。
    # 返回值为要显示在屏幕上的echo字符串，或None
    def NNCall(self):
        if NNList[self.otpObj.type]["isMultiInput"]:
            ran = NNList[self.otpObj.type]["allowPicCount"]
            if not(isinstance(self.inputPath, list) and len(self.inputPath) >= ran[0] and len(self.inputPath) < ran[1]):
                return "错误：%s方法需要的输入图片数量必须大于等于%d个且小于%d个。"%(NNList[self.otpObj.type]["name"], ran[0], ran[1]), None
        if isinstance(self.inputPath, list):
            inStr = ",".join(list(map(lambda x: path.abspath(x), self.inputPath)))
        else:
            inStr = path.abspath(self.inputPath)
        if isinstance(self.outputPath, list):
            outStr = ",".join(list(map(lambda x: path.abspath(x), self.outputPath)))
        else:
            outStr = path.abspath(self.outputPath)

        # 以下是连通神经网络的API的代码
        # 正式接入神经网络时请取消这部分的注释
        from taskbank.tools.controller import work
        work(NNList[self.otpObj.type]["param"], inStr, outStr, is_multi_task=NNList[self.otpObj.type]["isMultiInput"])
        return None, outStr


        # 以下是本机单元测试用代码，没有接入神经网络，作用是5s后返回固定图片作为处理结果
        # 正式接入神经网络时请把这部分注释掉
        # import time
        # import shutil
        # import random
        # time.sleep(random.uniform(5,30))
        # shutil.copyfile("image/download/示例.png", outStr)
        # return "测试", outStr


