from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')

        help_texts = {
            'text': _('Текст нового поста'),
            'group': _('Группа к которой будет относится пост'),
            'image': _('Картинка поста')
        }
        labels = {
            'text': _('Текст Поста'),
            'group': _('Группа'),
            'image': _('Картинка'),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)

        help_texts = {
            'text': _('Текст нового комментария'),
        }
        labels = {
            'text': _('Комментарий'),
        }