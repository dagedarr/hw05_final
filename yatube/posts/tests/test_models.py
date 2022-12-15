from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        fact_group_str = self.group.title
        fact_post_str = self.post.text[:settings.SYMBOLS_COUNT]

        expercation_group_str = str(self.group)
        expercation_post_str = str(self.post)

        self.assertEqual(fact_group_str, expercation_group_str,
                         msg='Название группы не выпадает в __str__')
        self.assertEqual(fact_post_str, expercation_post_str,
                         msg='Текст поста не выпадает в __str__')
