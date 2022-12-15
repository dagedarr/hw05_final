import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestCreateForm(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        small_image = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )

        cls.image = SimpleUploadedFile(
            name="test_img2.png",
            content=small_image,
            content_type="image2"
        )

        cls.author = User.objects.create_user(username='author')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.author,
            image=cls.image
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()

        self.user = TestCreateForm.author
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_form_create(self):
        post_count = Post.objects.count()

        form_data = {
            'text': 'Тестовый текст формы',
            'group': self.group.id,
            'author': self.author.username,
            'image': self.post.image  # Добавлено
        }

        response = self.authorized_client.post(reverse('posts:post_create'),
                                               data=form_data,
                                               follow=True)
        # Посты увеличились
        self.assertEqual(Post.objects.count(), post_count + 1)
        # Нас кинули в профиль
        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': self.user.username}))

        test_obj = Post.objects.first()

        # Текст в посте сошелся с тем что мы в него передали
        self.assertEqual(test_obj.text, form_data['text'],
                         f'Проблема в {test_obj.text}')

        self.assertEqual(test_obj.group.id, form_data['group'],
                         f'Проблема в {test_obj.group.id}')

        self.assertEqual(test_obj.author.username, form_data['author'],
                         f'Проблема в {test_obj.author.username}')

        # Добавлено
        self.assertTrue(test_obj.image,
                        msg='В созданный пост не передалась картинка')

    def test_post_edit(self):
        """Проверка что пост можно редактировать."""
        # Данные изначального поста
        text_before_editing = self.post.text
        group_before_editing = self.post.group.id
        author_before_editing = self.post.author

        form_data_edit = {
            'text': 'После изменения',
            'group': self.group.id,
            'author': self.post.author,
        }

        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data_edit,
            follow=True)

        # Нашли наш измененный пост и данные из него
        edited_post = Post.objects.filter(id=self.post.id).first()

        # Текст и правда поменялся
        self.assertNotEqual(text_before_editing, edited_post.text)
        self.assertEqual(group_before_editing, edited_post.group.id)
        self.assertEqual(author_before_editing, edited_post.author)

    def test_guest_cant_create_post(self):
        post_count = Post.objects.count()

        form_data = {
            'text': 'Текст который никто на сайте не увидит',
            'group': self.group.id,
        }

        response = self.guest_client.post(reverse('posts:post_create'),
                                          data=form_data,
                                          follow=True)

        # Проверка что постов не увеличилось после передачи формы
        self.assertEqual(Post.objects.count(), post_count)

        # Проверка что нам предложили войти на сайт
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse('posts:post_create')
        )
