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
          {"name": "Pairwise-Nonfixated-Camera-Pose", "param": "non_fixated_pose", "isMultiInput": True},
          {"name": "Pairwise-Fixated-Camera-Pose", "param": "fix_pose", "isMultiInput": True},
          {"name": "Triplet-Fixated-Camera-Pose", "param": "ego_motion", "isMultiInput": True},
          {"name": "Point-Matching", "param": "point_match", "isMultiInput": True}]


class asyncNN(threading.Thread):
    def __init__(self, images: list, operTypes: list, operObj):
        from .models import Output
        super().__init__()
        self.images = images
        if (len(operTypes) <= 0):
            raise RequestHandleFailException(400, "您没有选择任何一个要执行的算法，因此无法完成操作。请重新选择。")
        self.operTypes = operTypes
        self.operObj = operObj
        self.otpList = []
        for oneOper in self.operTypes:
            output = Output(type=int(oneOper), oper=self.operObj)
            output.save()
            self.otpList.append(output)

    def run(self):
        from .models import Operation, Output
        for otp in self.otpList:
            if NNList[otp.type]["isMultiInput"]:
                inputpath = ",".join(self.images)
                outputpath = path.join(MEDIA_ROOT, "download",
                                       path.relpath(self.images[0], path.join(MEDIA_ROOT, "upload")))
                outputStr = asyncNN.NNInterface(inputpath, outputpath, otp.type)
                otpObj = Output.objects.select_for_update().get(id=otp.id)
                otpObj.outputStr = outputStr if outputStr else "已完成"
                otpObj.outputFilePath = outputpath
                otpObj.save()
            else:
                le = len(self.images)
                if le == 1:
                    image = self.images[0]
                    outputpath = path.join(MEDIA_ROOT, "download", path.relpath(image, path.join(MEDIA_ROOT, "upload")))
                    outputStr = asyncNN.NNInterface(image, outputpath, otp.type)
                    otpObj = Output.objects.select_for_update().get(id=otp.id)
                    otpObj.outputStr = ("已完成, " + outputStr) if outputStr else "已完成"
                    otpObj.outputFilePath = outputpath
                    otpObj.process = 1
                    otpObj.save()
                elif le >= 2:
                    outputFolder = path.join(MEDIA_ROOT, determineDownload(None, None))
                    if not path.exists(outputFolder):
                        os.makedirs(outputFolder)
                    otpObj = Output.objects.select_for_update().get(id=otp.id)
                    otpObj.outputStr = "运行中%d/%d" % (0, le)
                    otpObj.outputFilePath = outputFolder
                    otpObj.save()
                    outputStrs = []
                    done = 0
                    for image in self.images:
                        outputpath = path.join(outputFolder, path.relpath(image, path.join(MEDIA_ROOT, "upload")))
                        if not path.exists(path.dirname(outputpath)):
                            os.makedirs(path.dirname(outputpath))
                        oneStr = asyncNN.NNInterface(image, outputpath, otp.type)
                        done = done + 1
                        if oneStr:
                            outputStrs.append(oneStr)
                        otpObj = Output.objects.select_for_update().get(id=otp.id)
                        otpObj.outputStr = "运行中%d/%d%s" % (
                            done, le, ", " + str(outputStrs) if len(outputStrs) > 0 else "")
                        otpObj.save()
                    otpObj = Output.objects.select_for_update().get(id=otp.id)
                    otpObj.outputStr = "已完成" + (", " + str(outputStrs)) if len(outputStrs) > 0 else "已完成"
                    otpObj.process = 1
                    otpObj.save()
                else:
                    raise RequestHandleFailException(400, "没有有效的可操作文件！")
        self.operObj = Operation.objects.select_for_update().get(id=self.operObj.id)
        self.operObj.process = 1
        self.operObj.save()

    # 网络的核心方法：根据给定的输入输出路径和操作类型调用work函数。
    # 返回值为要显示在屏幕上的echo字符串，或None
    @staticmethod
    def NNInterface(inputPath, outputPath, operType):
        # 以下是连通神经网络的API的代码
        # 正式接入神经网络时请取消这部分的注释
        from taskbank.tools.controller import work
        work(NNList[operType]["param"], path.abspath(inputPath), path.abspath(outputPath), is_multi_task=NNList[operType]["isMultiInput"])

        # 以下是本机单元测试用代码，没有接入神经网络，作用是5s后返回固定图片作为处理结果
        # 正式接入神经网络时请把这部分注释掉
        # import time
        # import shutil
        # time.sleep(5)
        # shutil.copyfile("image/download/示例.png", outputPath)