from django.db import models
from django.contrib.auth.models import AbstractUser
from django import forms
import time
import random
from os import path

# Create your models here.
class User(AbstractUser):

    class Meta(AbstractUser.Meta):
        pass


def determineUpload(instance, fileName):
    saveDir = "upload"
    millis = int(round(time.time() * 1000))
    ran = random.randint(0, 9999999)
    extname = path.splitext(fileName)[1]
    name = str(millis) + "_" + str(ran) + extname
    from videopj.settings import MEDIA_ROOT
    print(path.basename(MEDIA_ROOT))
    toSave = path.join(saveDir, name)
    if path.exists(toSave):
        return determineUpload(instance, fileName)
    else:
        return toSave


class Operation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    process = models.PositiveSmallIntegerField(default=0)
    time = models.DateTimeField(auto_now_add=True)
    input = models.ImageField(upload_to=determineUpload)


class Output(models.Model):
    type = models.PositiveSmallIntegerField()
    outputStr = models.TextField(default="处理中...")
    outputFile = models.FileField()
    oper = models.ForeignKey(Operation, on_delete=models.CASCADE)


class OperationSubmitForm(forms.ModelForm):
    tocall = forms.fields.MultipleChoiceField(
        choices=((0, "A"), (1, "B"), (2, "C"),),
        label="执行的算法",
        initial=[0,1,2],
        widget=forms.widgets.CheckboxSelectMultiple()
    )

    class Meta:
        model=Operation
        fields=["input"]
        labels={
            "input": "输入图片"
        }

