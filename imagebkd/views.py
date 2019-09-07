import os
from django.contrib import auth
from django.contrib.auth.hashers import make_password
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render_to_response, redirect

from imagebkd.apiutils import validateOutputStatus, generatePageInfo, RECORD_PER_PAGE
from imagebkd.modelutils import getInfoFromTimeForm
from videopj.settings import MEDIA_ROOT
from .apiutils import RequestHandleFailException, getKeyOrRaiseBlankRHFE, AlertResponse, assertRequestMethod, subList, \
    assertUser, assertSuperUser
from imagebkd.nnadapter import asyncNN
from .models import User, OperationSubmitForm, Operation, TimeForm, InputFile
from .fileutils import determineUpload, unzipAllChooseImages, assertFileType, saveImageFieldFileFromUrl, saveImageFieldFile

MOST_PIC_SHOW_INPUT = 5
MOST_PIC_SHOW_RES = 5


def logon(req: HttpRequest):
    assertRequestMethod(req, "POST")
    gUsername = getKeyOrRaiseBlankRHFE(req.POST, "username", "无效的用户名或密码！")
    gPassword = getKeyOrRaiseBlankRHFE(req.POST, "password", "无效的用户名或密码！")
    try:
        User.objects.get(username=gUsername)
        raise RequestHandleFailException(400, "该用户名已被占用，请更换！")
    except User.DoesNotExist:
        u = User.objects.create(username=gUsername, password=make_password(gPassword))  # 存在数据库中的密码已加密
        login(req)
        return AlertResponse("注册成功，并已为您自动登录", 200, redirect="uploadPage")


def login(req: HttpRequest):
    assertRequestMethod(req, "POST")
    gUsername = getKeyOrRaiseBlankRHFE(req.POST, "username", "用户名不存在！")
    gPassword = getKeyOrRaiseBlankRHFE(req.POST, "password", "密码错误！")
    try:
        user = User.objects.get(username=gUsername)  # 为了区分用户不存在和密码错误两种情况
        user = auth.authenticate(req, username=gUsername, password=gPassword)
        if user is None:
            raise RequestHandleFailException(400, "密码错误！")
        if user == req.user:
            raise RequestHandleFailException(400, "您已登录过，请勿重复登录！")
        auth.login(req, user)
        return AlertResponse("登录成功", 200, redirect="uploadPage")
    except User.DoesNotExist:
        raise RequestHandleFailException(400, "用户名不存在！")


def logout(req: HttpRequest):
    assertRequestMethod(req, "POST")
    user = req.user
    if not user.is_anonymous:
        auth.logout(req)
        return AlertResponse("登出成功", 200, "loginPage")
    else:
        raise RequestHandleFailException(400, "您当前没有登录，因此无法登出！")


def loginPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    user = req.user
    if user.is_anonymous:
        return render_to_response("loginPage.html")
    else:
        raise RequestHandleFailException(400, "您已登录。若要换号登录，请先登出此号！", redirect="uploadPage")


def uploadPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    assertUser(req)
    return render_to_response("uploadPage.html", {"form": OperationSubmitForm()})


def upload(req: HttpRequest):
    assertRequestMethod(req, "POST")
    assertUser(req)
    user = req.user
    form = OperationSubmitForm(req.POST, req.FILES)
    if form.is_valid():
        oper = Operation(user=user)
        oper.save()
        if not form.cleaned_data["input"]:
            if form.cleaned_data["inputUrl"] != "":
                urllist = form["inputUrl"].data.split(";")
                for url in urllist:
                    url = url.strip()
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
                                    ff.write(chunk)
                        pathList, dirname = unzipAllChooseImages(toSave)
                        for p in pathList:
                            saveImageFieldFile(p, InputFile(oper=oper).input, chosenName=os.path.relpath(p, MEDIA_ROOT))
                    elif ftype == "img":
                        saveImageFieldFile(f, InputFile(oper=oper).input)
            else:
                raise RequestHandleFailException(400, "不能同时上传文件和指定文件Url")
        oper.save()

        asyncNN(list(map(lambda x: x.input.path, oper.inputfile_set.all())), form.cleaned_data["tocall"], oper).start()
        return redirect("/resultPage?id=" + str(oper.id))
    else:
        raise RequestHandleFailException(400, "输入的文件或Url无效")


def resultPage(req: HttpRequest):
    assertRequestMethod(req, "GET")
    id = int(req.GET["id"])
    try:
        model = Operation.objects.get(id=id)
    except Operation.DoesNotExist:
        raise RequestHandleFailException(404, "所访问的操作不存在！")
    assertUser(req, model.user)
    res = {
        "id": model.id,
        "status": model.process,
        "time": model.time,
        "inputs": list(map(lambda x: x.input, subList(model.inputfile_set.all(), MOST_PIC_SHOW_INPUT))),
        "opers": validateOutputStatus(model),
        "toomany": model.inputfile_set.count() > MOST_PIC_SHOW_INPUT
    }
    return render_to_response("resultPage.html", {"ope": res})


def queryResult(req: HttpRequest):
    assertRequestMethod(req, "GET")
    id = int(req.GET["id"])
    try:
        model = Operation.objects.get(id=id)
    except Operation.DoesNotExist:
        raise RequestHandleFailException(404, "所访问的操作不存在！")
    assertUser(req, model.user)
    res = {
        "id": model.id,
        "status": model.process,
        "opers": validateOutputStatus(model)
    }
    return JsonResponse(res)


def history(req: HttpRequest):
    assertRequestMethod(req, "GET")
    assertUser(req)
    form = TimeForm(req.GET)
    curPage, page, begin, end, username = getInfoFromTimeForm(form)
    user = req.user
    if begin and end:
        query = user.operation_set.filter(time__range=(begin, end))
    elif begin and (not end):
        query = user.operation_set.filter(time__gt=begin)
    elif (not begin) and end:
        query = user.operation_set.filter(time__lt=end)
    else:
        query = user.operation_set.all()

    resDict, total, totalPage, pageRange = generatePageInfo(query, page)
    resList = []
    for i in pageRange:
        resList.append({
            "index": i + 1,
            "id": query[i].id,
            "time": query[i].time,
            "status": query[i].process
        })
    resDict["list"] = resList
    return render_to_response("historyPage.html", {"data": resDict, "timeForm": TimeForm(initial={"begin": begin,"end": end})})


def delete(req: HttpRequest):
    assertRequestMethod(req, "POST")
    for id in req.POST:
        try:
            oper = Operation.objects.select_for_update().get(id=int(id))
            assertUser(req, oper.user)
            oper.delete()
        except Exception:
            raise RequestHandleFailException(400, "数据记录不存在或状态异常！")
    if req.headers["Referer"].find("adminHistory") >= 0:
        return redirect("/adminHistory")
    return redirect("/history")


def adminHistory(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    curPage, page, begin, end, username = getInfoFromTimeForm(form)
    assertSuperUser(req)
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

    resDict, total, totalPage, pageRange = generatePageInfo(query, page)
    resList = []
    for i in pageRange:
        resList.append({
            "index": i+1,
            "id": query[i].id,
            "time": query[i].time,
            "status": query[i].process,
            "username": query[i].user.username
        })
    resDict["list"] = resList
    return render_to_response("adminHistoryPage.html", {"data": resDict, "timeForm": TimeForm(initial={"begin": begin,"end": end})})


def adminUser(req: HttpRequest):
    assertRequestMethod(req, "GET")
    form = TimeForm(req.GET)
    curPage, page, begin, end, username = getInfoFromTimeForm(form)
    assertSuperUser(req)
    if begin and end:
        query = User.objects.filter(last_login__range=(begin, end))
    elif begin and (not end):
        query = User.objects.filter(last_login__gt=begin)
    elif (not begin) and end:
        query = User.objects.filter(last_login__lt=end)
    else:
        query = User.objects.all()

    resDict, total, totalPage, pageRange = generatePageInfo(query, page)
    resList = []
    for i in pageRange:
        resList.append({
            "index": i+1,
            "id": query[i].id,
            "time": query[i].last_login,
            "username": query[i].username,
            "operCount": query[i].operation_set.count()
        })
    resDict["list"] = resList
    return render_to_response("adminUserPage.html", {"data": resDict, "timeForm": TimeForm(initial={"begin": begin,"end": end})})


def adminDeleteUser(req: HttpRequest):
    assertRequestMethod(req, "POST")
    assertSuperUser(req)
    for id in req.POST:
        try:
            oper = User.objects.select_for_update().get(id=int(id))
            if oper == req.user:
                raise RequestHandleFailException(400, "您不能删除您自己")
            oper.delete()
        except Exception:
            raise RequestHandleFailException(400, "数据记录不存在或状态异常！")
    return redirect("/adminUser")


def adminRedi(req: HttpRequest):
    assertRequestMethod(req, "GET")
    assertSuperUser(req)
    return redirect("/adminHistory")


def indexRedi(req: HttpRequest):
    if req.user.is_anonymous:
        return redirect("/loginPage")
    else:
        return redirect("/uploadPage")