from videopj.settings import MEDIA_ROOT
from django.contrib.auth.hashers import make_password
from django.http import HttpRequest, HttpResponse, JsonResponse
from .models import User, OperationSubmitForm, Operation, TimeForm, InputFile, Output
from django.contrib import auth
from .apiutils import RequestHandleFailException, getKeyOrRaiseBlankRHFE, AlertResponse, assertRequestMethod, asyncNN, subList
from django.shortcuts import render_to_response, redirect

import requests


# Create your views here.
def logon(req: HttpRequest):
    assertRequestMethod(req, "POST")
    gUsername = getKeyOrRaiseBlankRHFE(req.POST, "username", "invalid parameters")
    gPassword = getKeyOrRaiseBlankRHFE(req.POST, "password", "invalid parameters")
    try:
        User.objects.get(username=gUsername)
        raise RequestHandleFailException(200, "user exists")
    except User.DoesNotExist:
        u = User.objects.create(username=gUsername, password=make_password(gPassword))  # 存在数据库中的密码已加密
        login(req)
        return AlertResponse("注册成功，并已为您自动登录", 200, redirect="uploadPage")


def login(req: HttpRequest):
    assertRequestMethod(req, "POST")
    gUsername = getKeyOrRaiseBlankRHFE(req.POST, "username", "no such a user")
    gPassword = getKeyOrRaiseBlankRHFE(req.POST, "password", "password is wrong")
    try:
        user = User.objects.get(username=gUsername)  # 为了区分用户不存在和密码错误两种情况
        user = auth.authenticate(req, username=gUsername, password=gPassword)
        if user is None:
            raise RequestHandleFailException(200, "password is wrong")
        if user == req.user:
            raise RequestHandleFailException(200, "has logged in")
        auth.login(req, user)
        return AlertResponse("登录成功", 200, redirect="uploadPage")
    except User.DoesNotExist:
        raise RequestHandleFailException(200, "no such a user")


def logout(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        auth.logout(req)
        return AlertResponse("登出成功", 200, "loginPage")
    else:
        raise RequestHandleFailException(200, "no valid session")


def loginPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if user.is_anonymous:
        return render_to_response("loginPage.html")
    else:
        raise RequestHandleFailException(400, "您已登录，若要换号登录，请先登出此号！", redirect="uploadPage")


def uploadPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if not user.is_anonymous:
        return render_to_response("uploadPage.html", {"form": OperationSubmitForm()})
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


from PIL import Image

from django.db.models.fields.files import ImageFieldFile
from django.core.files import File
import random
import os
from .models import determineUpload
import zipfile
import filetype

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
        raise RequestHandleFailException(400, "上传的压缩包中不含有任何的图片类型文件，因此无法处理")
    return res, foldername


# def generateTempfileName(extname):
#     ran = random.randint(0, 9999999)
#     name = str(ran) + extname
#     toSave = os.path.join("image", "temp", name)
#     if os.path.exists(toSave):
#         return generateTempfileName(extname)
#     return toSave


def assertFileType(content_type=None, name = None):
    if content_type == "application/zip" or filetype.guess_mime(name) == "application/zip":
        return "zip", ".zip"
    elif (content_type and content_type.find("image") == 0) or filetype.image(name):
        return "img", filetype.get_type(content_type, os.path.splitext(name)[1]).extension
    else:
        raise RequestHandleFailException(400, "输入的文件不是支持的图片或zip类型！")


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


def saveImageFieldFile(f, imageFieldFile: ImageFieldFile, chosenName=None):
    if isinstance(f, File):
        imageFieldFile.save(chosenName if chosenName else determineUpload(None, f.name), f, False)
    elif isinstance(f, str) or isinstance(f, bytes):
        with open(f, "rb") as ff:
            imageFieldFile.save(chosenName if chosenName else determineUpload(None, ff.name), File(ff), False)
    else:
        imageFieldFile.save(chosenName if chosenName else determineUpload(None, f.name), File(f), False)




def upload(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        form = OperationSubmitForm(req.POST, req.FILES)
        if form.is_valid():
            oper = Operation(user=user)
            oper.save()
            if not form.cleaned_data["input"]:
                if form.cleaned_data["inputUrl"] != "":
                    urllist = form["inputUrl"].data.split(";")
                    for url in urllist:
                        saveImageFieldFileFromUrl(url, oper)
                else:
                    raise RequestHandleFailException(400, "必须上传文件或指定文件Url")
            else:
                if form.cleaned_data["inputUrl"] == "":
                    filelist = req.FILES.getlist("input")
                    for f in filelist:
                        ftype, extname = assertFileType(f.content_type, f.name)
                        if ftype == "zip":
                            toSave = os.path.join(MEDIA_ROOT, determineUpload(None, extname))
                            with open(toSave, "wb") as ff:
                                for chunk in f.chunks(chunk_size=1024*1024):
                                    if chunk:
                                        f.write(chunk)
                            pathList, dirname = unzipAllChooseImages(toSave)
                            for p in pathList:
                                saveImageFieldFile(p, InputFile(oper=oper).input, chosenName=os.path.relpath(p, MEDIA_ROOT))
                        elif ftype == "img":
                            saveImageFieldFile(f, InputFile(oper=oper).input)
                else:
                    raise RequestHandleFailException(400, "不能同时上传文件和指定文件Url")
            oper.save()
            asyncNN(list(map(lambda x: x.input.path, oper.inputfile_set.all())), form.cleaned_data["tocall"], oper).start()
            return redirect("/resultPage?id=" + str(form.instance.id))
        else:
            raise RequestHandleFailException(400, "输入的文件或Url无效")
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def test(req: HttpRequest):
    return AlertResponse("yyy", redirect="test2")


def test2(req: HttpRequest):
    return HttpResponse("qwq")


def getFilesListOrZip(pathStr: str, enableZip: bool):
    if not (pathStr and pathStr != ""):
        return None, []
    if os.path.isdir(pathStr):
        zipFileName = None
        if enableZip > 0:
            zipFileName = pathStr + ".zip"
            if not os.path.exists(zipFileName):
                with zipfile.ZipFile(zipFileName, 'wb', compression=zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(pathStr):
                        for filename in files:
                            pathfile = os.path.join(root, filename)
                            relapath = os.path.relpath(pathfile, pathStr)
                            zipf.write(pathfile, relapath)
        res = []
        for root, dirs, files in os.walk(pathStr):
            for file in files:
                realPath = os.path.join(root, file)
                kind = filetype.image(realPath)
                if kind:
                    res.append(realPath)
        return zipFileName, res
    else:
        return pathStr, [pathStr]


def getForDownloadPath(p, most=0):
    if isinstance(p, list):
        l = list(map(lambda x:os.path.join("image/download", os.path.relpath(x, "image/download")), p))
        if most > 0:
            l = subList(l, most)
        return l
    else:
        p = os.path.join("image/download", os.path.relpath(p, "image/download"))
        return p



MOST_PIC_SHOW_INPUT = 5
MOST_PIC_SHOW_RES = 5


def resultPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if not user.is_anonymous:
        id = int(req.GET["id"])
        try:
            model = Operation.objects.get(id=id)
        except Operation.DoesNotExist:
            raise RequestHandleFailException(404, "所访问的操作不存在！")
        if (not user.is_superuser) and model.user != user:
            raise RequestHandleFailException(403, "您无权访问此操作！")
        res = {
            "id": model.id,
            "status": model.process,
            "time": model.time,
            "inputs": list(map(lambda x: x.input, subList(model.inputfile_set.all(), MOST_PIC_SHOW_INPUT)))
        }
        otps = model.output_set.all()
        otpList = []
        for otp in otps:
            otpData = {
                "name": "hhh",
                "outputStr": otp.outputStr
            }
            otpRawDown, otpRawList = getFilesListOrZip(otp.outputFilePath, True if otp.process else False)
            otpData["outputFileUrls"] = getForDownloadPath(otpRawList, MOST_PIC_SHOW_RES)
            otpData["outputDownload"] = getForDownloadPath(otpRawDown)
            otpList.append(otpData)
        res["opers"] = otpList
        return render_to_response("resultPage.html", {"ope": res})
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def queryResult(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if not user.is_anonymous:
        id = int(req.GET["id"])
        try:
            model = Operation.objects.get(id=id)
        except Operation.DoesNotExist:
            raise RequestHandleFailException(404, "所访问的操作不存在！")
        if (not user.is_superuser) and model.user != user:
            raise RequestHandleFailException(403, "您无权访问此操作！")
        res = {
            "id": model.id,
            "status": model.process,
        }
        otps = model.output_set.all()
        otpList = []
        otpDict = {}
        for otp in otps:
            otpData = {
                "name": "hhh",
                "outputStr": otp.outputStr
            }
            otpRawDown, otpRawList = getFilesListOrZip(otp.outputFilePath, True if otp.process else False)
            otpData["outputFileUrls"] = getForDownloadPath(otpRawList, MOST_PIC_SHOW_RES)
            otpData["outputDownload"] = getForDownloadPath(otpRawDown)
            otpList.append(otpData)
        res["opers"] = otpList
        return JsonResponse(res)
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


RECORD_PER_PAGE = 10
import math

def assertKeyExist(key: str, form):
    d = form.__dict__["data"]
    return (key in d) and d[key] != ""


def history(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    if not form.is_valid():
        raise RequestHandleFailException(400, "输入的查询参数无效，请检查", "history")
    fd = form.__dict__["data"]
    curPage = int(fd["curPage"]) if assertKeyExist("curPage", form) else 1
    if assertKeyExist("lastPage", form):
        page = curPage - 1
    elif assertKeyExist("nextPage", form):
        page = curPage + 1
    else:
        page = form.cleaned_data["page"] if form.cleaned_data["page"] != None else curPage
    begin = form.cleaned_data["begin"]
    end = form.cleaned_data["end"]

    user = req.user
    if not user.is_anonymous:
        if begin and end:
            query = user.operation_set.filter(time__range=(begin, end))
        elif begin and (not end):
            query = user.operation_set.filter(time__gt=begin)
        elif (not begin) and end:
            query = user.operation_set.filter(time__lt=end)
        else:
            query = user.operation_set.all()

        total = len(query)
        resList = []
        totalPage = math.ceil(total / RECORD_PER_PAGE)
        resDict = {
            "total": total,
            "totalPage": totalPage,
            "curPage": page
        }
        if not 1<=page-1<=totalPage:
            resDict["noLast"] = 1
        if not 1<=page+1<=totalPage:
            resDict["noNext"] = 1

        if(totalPage > 0):
            if page<=0 or page>totalPage:
                raise RequestHandleFailException(400, "页码无效", "history")
            for i in range((page-1)*RECORD_PER_PAGE, min(page*RECORD_PER_PAGE, total)):
                resList.append({
                    "index": i+1,
                    "id": query[i].id,
                    "time": query[i].time,
                    "status": query[i].process
                })

        resDict["list"] = resList

        return render_to_response("historyPage.html", {"data": resDict, "timeForm": TimeForm(initial={
            "begin": begin,
            "end": end}
        )})
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def delete(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        for id in req.POST:
            try:
                oper = Operation.objects.select_for_update().get(id=int(id))
                if (not user.is_superuser) and oper.user != user:
                    raise RequestHandleFailException(403, "无权进行此操作")
                oper.delete()
            except Exception:
                raise RequestHandleFailException(400, "数据记录不存在或状态异常！")
        if req.headers["Referer"].find("adminHistory"):
            return redirect("/adminHistory")
        return redirect("/history")
    else:
        return AlertResponse("您还没有登录", 400, redirect="loginPage")


def adminHistory(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    if not form.is_valid():
        raise RequestHandleFailException(400, "输入的查询参数无效，请检查", "history")
    fd = form.__dict__["data"]
    curPage = int(fd["curPage"]) if assertKeyExist("curPage", form) else 1
    if assertKeyExist("lastPage", form):
        page = curPage - 1
    elif assertKeyExist("nextPage", form):
        page = curPage + 1
    else:
        page = form.cleaned_data["page"] if form.cleaned_data["page"] != None else curPage
    begin = form.cleaned_data["begin"]
    end = form.cleaned_data["end"]
    username = fd["username"] if assertKeyExist("username", form) else None

    if req.user.is_superuser:
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise RequestHandleFailException(400, "查无此用户", redirect="adminHistory")
            if begin and end:
                query = user.operation_set.filter(time__range=(begin, end))
            elif begin and (not end):
                query = user.operation_set.filter(time__gt=begin)
            elif (not begin) and end:
                query = user.operation_set.filter(time__lt=end)
            else:
                query = user.operation_set.all()
        else:
            if begin and end:
                query = Operation.objects.filter(time__range=(begin, end))
            elif begin and (not end):
                query = Operation.objects.filter(time__gt=begin)
            elif (not begin) and end:
                query = Operation.objects.filter(time__lt=end)
            else:
                query = Operation.objects.all()

        total = len(query)
        resList = []
        totalPage = math.ceil(total / RECORD_PER_PAGE)
        resDict = {
            "total": total,
            "totalPage": totalPage,
            "curPage": page
        }
        if not 1<=page-1<=totalPage:
            resDict["noLast"] = 1
        if not 1<=page+1<=totalPage:
            resDict["noNext"] = 1

        if(totalPage > 0):
            if page<=0 or page>totalPage:
                raise RequestHandleFailException(400, "页码无效", "history")
            for i in range((page-1)*RECORD_PER_PAGE, min(page*RECORD_PER_PAGE, total)):
                resList.append({
                    "index": i+1,
                    "id": query[i].id,
                    "time": query[i].time,
                    "status": query[i].process,
                    "username": query[i].user.username
                })

        resDict["list"] = resList

        return render_to_response("adminHistoryPage.html", {"data": resDict, "timeForm": TimeForm(initial={
            "begin": begin,
            "end": end}
        )})
    else:
        return AlertResponse("无权限", 403)


def adminUser(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    if not form.is_valid():
        raise RequestHandleFailException(400, "输入的查询参数无效，请检查", "history")
    fd = form.__dict__["data"]
    curPage = int(fd["curPage"]) if assertKeyExist("curPage", form) else 1
    if assertKeyExist("lastPage", form):
        page = curPage - 1
    elif assertKeyExist("nextPage", form):
        page = curPage + 1
    else:
        page = form.cleaned_data["page"] if form.cleaned_data["page"] != None else curPage
    begin = form.cleaned_data["begin"]
    end = form.cleaned_data["end"]

    if req.user.is_superuser:
        if begin and end:
            query = User.objects.filter(last_login__range=(begin, end))
        elif begin and (not end):
            query = User.objects.filter(last_login__gt=begin)
        elif (not begin) and end:
            query = User.objects.filter(last_login__lt=end)
        else:
            query = User.objects.all()

        total = len(query)
        resList = []
        totalPage = math.ceil(total / RECORD_PER_PAGE)
        resDict = {
            "total": total,
            "totalPage": totalPage,
            "curPage": page
        }
        if not 1<=page-1<=totalPage:
            resDict["noLast"] = 1
        if not 1<=page+1<=totalPage:
            resDict["noNext"] = 1

        if(totalPage > 0):
            if page<=0 or page>totalPage:
                raise RequestHandleFailException(400, "页码无效", "history")
            for i in range((page-1)*RECORD_PER_PAGE, min(page*RECORD_PER_PAGE, total)):
                resList.append({
                    "index": i+1,
                    "id": query[i].id,
                    "time": query[i].last_login,
                    "username": query[i].username,
                    "operCount": query[i].operation_set.count()
                })

        resDict["list"] = resList

        return render_to_response("adminUserPage.html", {"data": resDict, "timeForm": TimeForm(initial={
            "begin": begin,
            "end": end}
        )})
    else:
        return AlertResponse("无权限", 403)


def adminDeleteUser(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if user.is_superuser:
        for id in req.POST:
            try:
                oper = User.objects.select_for_update().get(id=int(id))
                if oper == user:
                    raise RequestHandleFailException(400, "您不能删除您自己")
                oper.delete()
            except Exception:
                raise RequestHandleFailException(400, "数据记录不存在或状态异常！")
        return redirect("/adminUser")
    else:
        raise RequestHandleFailException(403, "无权限！")