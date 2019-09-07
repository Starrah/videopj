from django import forms
from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
from imagebkd.modelutils import generateChoiceList


class User(AbstractUser):
    class Meta(AbstractUser.Meta):
        pass


class Operation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    process = models.PositiveSmallIntegerField(default=0)
    time = models.DateTimeField(auto_now_add=True)


class InputFile(models.Model):
    input = models.ImageField()
    oper = models.ForeignKey(Operation, on_delete=models.CASCADE)



class Output(models.Model):
    type = models.PositiveSmallIntegerField()
    outputStr = models.TextField(default="处理中...")
    outputFilePath = models.TextField()
    oper = models.ForeignKey(Operation, on_delete=models.CASCADE)
    process = models.PositiveSmallIntegerField(default=0)


class MoreOutputFile(models.Model):
    filePath = models.TextField()
    output = models.ForeignKey(Output, on_delete=models.CASCADE)


class OperationSubmitForm(forms.Form):
    input = forms.fields.FileField(required=False, label="选择文件", widget=forms.FileInput(attrs={'multiple': True, "accept": "image/*,application/zip"}))
    inputUrl = forms.fields.URLField(required=False, label="或输入图片的Url（多个url请以;隔开）")
    tocall = forms.fields.MultipleChoiceField(
        choices=generateChoiceList(),
        label="执行的算法",
        initial=[],
        widget=forms.widgets.CheckboxSelectMultiple()
    )


class TimeForm(forms.Form):
    page = forms.fields.IntegerField(required=False, label="页码", widget=forms.widgets.NumberInput(attrs={"class": "inl"}))
    begin = forms.fields.DateTimeField(required=False, label="从", widget=forms.widgets.DateTimeInput(attrs={"class": "inl"}))
    end = forms.fields.DateTimeField(required=False, label="到", widget=forms.widgets.DateTimeInput(attrs={"class": "inl"}))

    # def __init__(self, begin, end):
    #     self.begin = begin
    #     self.end = end

