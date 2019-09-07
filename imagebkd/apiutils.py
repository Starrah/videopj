from django.http import HttpResponse, HttpRequest
import threading
from PIL import Image
import time
import random
from os import path


def determineUpload(instance, fileName):
    saveDir = "upload"
    millis = int(round(time.time() * 1000))
    ran = random.randint(0, 9999999)
    extname = path.splitext(fileName)[1]
    name = str(millis) + "_" + str(ran) + extname
    toSave = path.join(saveDir, name)
    if path.exists(toSave):
        return determineUpload(instance, fileName)
    else:
        return toSave


class RequestHandleFailException(Exception):
    def __init__(self, to_statusCode=200, to_resp="", redirect = None):
        self.to_statusCode = to_statusCode
        self.to_resp = to_resp
        self.to_redi = redirect


def determineDownload(instance, fileName):
    saveDir = "download"
    millis = int(round(time.time() * 1000))
    ran = random.randint(0, 9999999)
    extname = path.splitext(fileName)[1] if fileName else ""
    name = str(millis) + "_" + str(ran) + extname
    toSave = path.join(saveDir, name)
    if path.exists(toSave):
        return determineUpload(instance, fileName)
    else:
        return toSave


def getKeyOrRaiseBlankRHFE(obj, key, errStr="invalid parameters"):
    if type(key) == list:
        resList = []
        for k in key:
            try:
                r = obj[k]
                if r == "" or r is None:
                    raise RequestHandleFailException(200, errStr)
                resList.append(r)
            except KeyError:
                raise RequestHandleFailException(200, errStr)
        return resList
    else:
        try:
            r = obj[key]
            if r == "" or r is None:
                raise RequestHandleFailException(200, errStr)
        except KeyError:
            raise RequestHandleFailException(200, errStr)
        return r


def assertRequestMethod(req: HttpRequest, method: str, errStr="错误的请求方法！"):
    if req.method != method:
        raise RequestHandleFailException(405, errStr)



def AlertResponse(text: str, status=200, redirect = None):
    toRes = "<script>alert(\""+ text +"\");"
    if redirect != None:
        if(redirect[0] != "\"" or redirect[-1] != "\""):
            redirect = "\"" + redirect + "\""
        toRes += ("window.location.href = " + redirect + ";")
    toRes += "</script>"
    return HttpResponse(toRes, status=status)
import os
NNList = [{"name": "Autoencoder", "param": "autoencoder", "isMultiInput": False}, {"name": "Curvatures", "param": "curvature", "isMultiInput": False}, {"name": "Colorization", "param": "colorization", "isMultiInput": False}, {"name": "Denoising-Autoencoder", "param": "denoise", "isMultiInput": False}, {"name": "Depth", "param": "rgb2depth", "isMultiInput": False}, {"name": "Edge-2D", "param": "edge2d", "isMultiInput": False}, {"name": "Edge-3D", "param": "edge3d", "isMultiInput": False}, {"name": "Euclidean-Distance", "param": "rgb2mist", "isMultiInput": False}, {"name": "Inpainting", "param": "inpainting_whole", "isMultiInput": False}, {"name": "Jigsaw-Puzzle", "param": "jigsaw", "isMultiInput": False}, {"name": "Keypoint-2D", "param": "keypoint2d", "isMultiInput": False}, {"name": "Keypoint-3D", "param": "keypoint3d", "isMultiInput": False}, {"name": "Object-Classification", "param": "class_1000", "isMultiInput": False}, {"name": "Reshading", "param": "reshade", "isMultiInput": False}, {"name": "Room-Layout", "param": "room_layout", "isMultiInput": False}, {"name": "Scene-Classification", "param": "class_places", "isMultiInput": False}, {"name": "Segmentation-2D", "param": "segment2d", "isMultiInput": False}, {"name": "Segmentation-3D", "param": "segment25d", "isMultiInput": False}, {"name": "Segmentation-Semantic", "param": "segmentsemantic", "isMultiInput": False}, {"name": "Surface-Normal", "param": "rgb2sfnorm", "isMultiInput": False}, {"name": "Vanishing-Point", "param": "vanishing_point", "isMultiInput": False}, {"name": "Pairwise-Nonfixated-Camera-Pose", "param": "non_fixated_pose", "isMultiInput": True}, {"name": "Pairwise-Fixated-Camera-Pose", "param": "fix_pose", "isMultiInput": True}, {"name": "Triplet-Fixated-Camera-Pose", "param": "ego_motion", "isMultiInput": True}, {"name": "Point-Matching", "param": "point_match", "isMultiInput": True}]
from videopj.settings import MEDIA_ROOT
class asyncNN(threading.Thread):
    def __init__(self, images: list, operTypes: list, operObj):
        from .models import Output
        super().__init__()
        self.images = images
        self.operTypes = operTypes
        self.operObj = operObj
        self.otpList = []
        for oneOper in self.operTypes:
            output = Output(type=oneOper, oper=self.operObj)
            output.save()
            self.otpList.append(output)

    def run(self):
        from .models import Operation, Output
        for otp in self.otpList:
            if NNList[otp.type]["isMultiInput"]:
                inputpath = ",".join(self.images)
                outputpath = path.join(MEDIA_ROOT, "download", path.relpath(self.images[0], path.join(MEDIA_ROOT, "upload")))
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
                    otpObj.outputStr = outputStr if "已完成, " + outputStr else "已完成"
                    otpObj.outputFilePath = outputpath
                    otpObj.process = 1
                    otpObj.save()
                elif le >= 2:
                    outputFolder = path.join(MEDIA_ROOT, determineDownload(None, None))
                    if not path.exists(outputFolder):
                        os.makedirs(outputFolder)
                    otpObj = Output.objects.select_for_update().get(id=otp.id)
                    otpObj.outputStr = "运行中%d/%d"%(0, le)
                    otpObj.outputFilePath = outputFolder
                    otpObj.save()
                    outputStrs = []
                    done = 0
                    for image in self.images:
                        outputpath = path.join(outputFolder, path.relpath(image, path.join(MEDIA_ROOT, "upload")))
                        oneStr = asyncNN.NNInterface(image, outputpath, otp.type)
                        done = done + 1
                        if oneStr:
                            outputStrs.append(oneStr)
                        otpObj = Output.objects.select_for_update().get(id=otp.id)
                        otpObj.outputStr = "运行中%d/%d%s" % (done, le, ", " + str(outputStrs) if len(outputStrs) > 0 else "")
                        otpObj.save()
                    otpObj = Output.objects.select_for_update().get(id=otp.id)
                    otpObj.outputStr = "已完成" + (", " + str(outputStrs)) if len(outputStrs) > 0 else ""
                    otpObj.process = 1
                    otpObj.save()
                else:
                    raise RequestHandleFailException(400, "没有有效的可操作文件！")
        self.operObj = Operation.objects.select_for_update().get(id=self.operObj.id)
        self.operObj.process = 1
        self.operObj.save()

    @staticmethod
    def NNInterface(inputPath, outputPath, operType):
        from taskbank.tools.controller import work
        work(NNList[operType]["param"], path.abspath(inputPath), path.abspath(outputPath), is_multi_task=NNList[operType]["isMultiInput"])

        # import time
        # import shutil
        # time.sleep(5)
        # shutil.copyfile("image/download/示例.png", outputPath)

def subList(l, len, begin=0):
    r = []
    c = 0
    for n in l:
        if c >= begin:
            r.append(n)
        c = c + 1
        if c >= len:
            break
    return r