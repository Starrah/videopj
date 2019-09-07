import os
import random
import time
import zipfile
from os import path
import filetype
import requests
from django.core.files import File
from django.db.models.fields.files import ImageFieldFile
from imagebkd.apiutils import RequestHandleFailException, subList
from imagebkd.models import Operation, InputFile, Output
from videopj.settings import MEDIA_ROOT


# 文件类型处理
def assertFileType(content_type=None, name = None):
    if content_type == "application/zip" or content_type == "application/x-zip-compressed":
        return "zip", ".zip"
    elif content_type and content_type.find("image") == 0:
        return "img", get_type_obj(content_type, getExtName(name)).extension
    else:
        try:
            if filetype.guess_mime(name) == "application/zip":
                return "zip", ".zip"
            elif filetype.image(name):
                return "img", get_type_obj(content_type, getExtName(name)).extension
        except FileNotFoundError:
            pass
        raise RequestHandleFailException(415, "输入的文件不是支持的图片或zip类型！")


def getExtName(fileName: str, withdot=True):
    a = path.splitext(fileName)
    return ("." if withdot else "") + (a[1].lstrip(".") if a[1] != "" else a[0].lstrip("."))


def get_type_obj(mime=None, ext=None):
    for kind in filetype.types:
        if kind.extension == ext.lstrip(".") or kind.mime == mime:
            return kind
    return None


# 目录与存储位置管理
def determineUpload(instance, fileName):
    saveDir = "upload"
    millis = int(round(time.time() * 1000))
    ran = random.randint(0, 9999999)
    extname = getExtName(fileName)
    name = str(millis) + "_" + str(ran) + extname
    toSave = path.join(saveDir, name)
    if path.exists(toSave):
        return determineUpload(instance, fileName)
    else:
        return toSave


def determineDownload(instance, fileName):
    saveDir = "download"
    millis = int(round(time.time() * 1000))
    ran = random.randint(0, 9999999)
    extname = getExtName(fileName) if fileName else ""
    name = str(millis) + "_" + str(ran) + extname
    toSave = path.join(saveDir, name)
    if path.exists(toSave):
        return determineUpload(instance, fileName)
    else:
        return toSave


def getForDownloadPath(p, most=0):
    if not p:
        return p
    if isinstance(p, list):
        l = list(map(lambda x:os.path.join("image/download", os.path.relpath(x, "image/download")), p))
        if most > 0:
            l = subList(l, most)
        return l
    else:
        p = os.path.join("image/download", os.path.relpath(p, "image/download"))
        return p


# 压缩文件处理
def unzipAllChooseImages(zipPath):
    exts = os.path.splitext(zipPath)
    foldername = exts[0]
    if len(exts) < 2 or exts[1] != ".zip":
        os.rename(zipPath, foldername+".zip")
        zipPath = foldername+".zip"
    with zipfile.ZipFile(zipPath, 'r') as zipf:
        zipf.extractall(path=foldername)
    res = []
    for root, dirs, files in os.walk(foldername):
        for file in files:
            realPath = os.path.join(root, file)
            kind = filetype.image(realPath)
            if kind:
                res.append(realPath)
    if len(res) <= 0:
        os.remove(zipPath)
        os.remove(foldername)
        raise RequestHandleFailException(415, "上传的压缩包中不含有任何的图片类型文件，因此无法处理")
    return res, foldername


def getFilesListOrZip(pathStr: str, otpObj: Output, enableZip: bool):
    if not (pathStr and pathStr != ""):
        return None, []
    if os.path.isdir(pathStr):
        zipFileName = None
        if enableZip:
            zipFileName = pathStr + ".zip"
            if not os.path.exists(zipFileName):
                with zipfile.ZipFile(zipFileName, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(pathStr):
                        for filename in files:
                            pathfile = os.path.join(root, filename)
                            relapath = os.path.relpath(pathfile, pathStr)
                            zipf.write(pathfile, relapath)
        res = []
        for filemodel in otpObj.moreoutputfile_set.all():
            res.append(filemodel.filePath)
        return zipFileName, res
    else:
        return pathStr, [pathStr]


# 从url下载并保存文件
def saveImageFieldFileFromUrl(url: str, oper: Operation):
    oper.save()
    r = requests.get(url, stream=True)
    r.raise_for_status()
    ftype, extname = assertFileType(r.headers["Content-Type"] if "Content-Type" in r.headers else None, url)
    toSave = os.path.join(MEDIA_ROOT, determineUpload(None, extname))
    with open(toSave, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    if ftype == "zip":
        pathList, dirname = unzipAllChooseImages(toSave)
        for p in pathList:
            saveImageFieldFile(p, InputFile(oper=oper).input, chosenName=os.path.relpath(p, MEDIA_ROOT))
    elif ftype == "img":
        saveImageFieldFile(toSave, InputFile(oper=oper).input, chosenName=os.path.relpath(toSave, MEDIA_ROOT))


# 向model中保存文件
def saveImageFieldFile(f, imageFieldFile: ImageFieldFile, chosenName=None):
    if isinstance(f, File):
        imageFieldFile.save(chosenName if chosenName else determineUpload(None, f.name), f, True)
    elif isinstance(f, str) or isinstance(f, bytes):
        with open(f, "rb") as ff:
            imageFieldFile.save(chosenName if chosenName else determineUpload(None, ff.name), File(ff), True)
    else:
        imageFieldFile.save(chosenName if chosenName else determineUpload(None, f.name), File(f), True)
