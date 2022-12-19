import shutil
import tempfile
from math import ceil

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД

        small_image = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )

        cls.image = SimpleUploadedFile(
            name="test_img.png",
            content=small_image,
            content_type="image"
        )

        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='HasNoName')

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

        cls.comment = Comment.objects.create(
            text='Тестовый текст комментария',
            post=cls.post,
            author=cls.author,
        )

        cls.urls = [
            reverse('posts:index'),

            reverse('posts:group_list',
                    kwargs={'slug': cls.group.slug}),

            reverse('posts:profile',
                    kwargs={'username': cls.user.username}),

            reverse('posts:post_detail',
                    kwargs={'post_id': cls.post.id}),

            reverse('posts:post_edit',
                    kwargs={'post_id': cls.post.id}),

            reverse('posts:post_create'),

            '/unexisting_page/'  # Добавлено
        ]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        # Создаем гостя
        self.guest_client = Client()

        self.follower_user = User.objects.create_user(username='follower')
        self.creator_user = User.objects.create_user(username='creator')

        not_auth_client = User.objects.create(username="TestName")
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(not_auth_client)

        cache.clear()
    # Проверяем используемые шаблоны

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Использовал список чтобы избежать повторения ключей
        templates = [
            'posts/index.html',
            'posts/group_list.html',
            'posts/profile.html',
            'posts/post_detail.html',
            'posts/create_post.html',
            'posts/create_post.html',

            'core/404.html'  # Добавлено
        ]

        for url, template in dict(zip(self.urls, templates)).items():
            with self.subTest():
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_pages_show_correct_context(self):
        """Шаблоны для index, group_list, profile, post_detail
           сформированы с правильным контекстом:
           текст, группа, автор, картинка."""

        responses = [
            self.authorized_client.get(
                reverse('posts:index')
            ).context['page_obj'].object_list,  # index

            self.authorized_client.get(
                reverse('posts:group_list',
                        kwargs={'slug': self.group.slug})
            ).context['page_obj'].object_list,  # group_list

            self.authorized_client.get(
                reverse('posts:profile',
                        kwargs={'username': self.post.author.username})
            ).context['page_obj'].object_list,  # profile

            self.authorized_client.get(
                reverse('posts:post_detail',
                        kwargs={'post_id': self.post.id})
            ).context['post'],  # post_detail
        ]

        for res in responses:
            with self.subTest():
                first_object = res[0] if isinstance(res, list) else res

                post_text = first_object.text
                post_group = first_object.group
                post_author = first_object.author
                # Добавлено
                post_image = first_object.image

                self.assertEqual(post_text,
                                 self.post.text,
                                 msg=f'Проблема в {post_text}')
                self.assertEqual(post_group,
                                 self.post.group,
                                 msg=f'Проблема в {post_group}')
                self.assertEqual(post_author,
                                 self.post.author,
                                 msg=f'Проблема в {post_author}')
                # Добавлено
                self.assertEqual(post_image,
                                 self.post.image,
                                 msg=f'Проблема в {post_image}')

    def test_create_post_and_post_edit_pages_show_correct_context(self):
        """Шаблоны create_post и post_edit
           сформированы с правильным контекстом."""

        responses = [
            self.authorized_client.get(reverse('posts:post_create')),
            self.authorized_client.get(
                reverse('posts:post_edit',
                        kwargs={'post_id': self.post.id}
                        )
            )
        ]

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for response in responses:
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_pages_shows_correct_context(self):
        """Пост отображается в главной странице, странице группы и в профиле"""
        responses = [
            self.authorized_client.get(reverse('posts:index')),
            self.authorized_client.get(reverse('posts:group_list',
                                       kwargs={'slug': self.group.slug})),
            self.authorized_client.get(
                reverse('posts:profile',
                        kwargs={'username': self.post.author.username}
                        )
            )
        ]

        for response in responses:
            with self.subTest():
                first_object = response.context['page_obj'][0]
                post_text = first_object.text
                post_group = first_object.group.title
                self.assertEqual(post_text, self.post.text)
                self.assertEqual(post_group, self.group.title)

    def test_add_comment(self):
        """Тестируем добавление комментария зарегистрированным
           пользователем и незарегистрированным."""

        comment_form_auth = {
            'text': 'Текст комментария зарегистрированного пользователя',
        }
        comment_form_guest = {
            'text': 'Все равно его не увидят',
        }

        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=comment_form_auth,
        )
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=comment_form_guest,
        )

        self.assertEqual(comment_form_auth['text'],
                         Comment.objects.first().text,
                         msg=(f'Почему-то комментарий зарегистрированного '
                              f'пользователя < {comment_form_auth["text"]}'
                              f'> не доходит'))

        self.assertNotEqual(comment_form_guest['text'],
                            Comment.objects.first().text,
                            msg='Аноним оставил пост, надо исправить')

    def test_comment_apeears_on_post_page(self):
        """Комментарий появился на странице поста."""
        comments_count = Comment.objects.count()

        comment_form = {
            'text': 'Появившийся комментарий',
        }

        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=comment_form,
        )

        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Comment.objects.count(),
                         comments_count + 1,
                         msg='Комментариев больше не стало')

        self.assertEqual(response.context['comments'].first().text,
                         comment_form['text'],
                         msg='Комментарий не видно')

    def test_cache_works(self):
        # Первая проверка
        response = self.authorized_client.get(
            reverse('posts:index'))['cache-control']

        # Тут даже время можно проверить
        self.assertTrue(response == f'max-age={settings.CACHE_TIME}')

        # Вторая проверка
        # Создали пост
        new_post = Post.objects.create(
            text='Тестовый текст для кэша',
            author=self.author,
            group=self.group
        )
        # Сохранили контент страницы с новым постом
        page = self.authorized_client.get(reverse('posts:index')).content
        # Удалили новый пост
        new_post.delete()

        # Сохранили контент страницы с удаленным постом
        page_in_cache = self.authorized_client.get(
            reverse('posts:index')
        ).content

        # Эти два контента одинаковые
        self.assertEqual(page, page_in_cache)

        # Очистили кеш
        cache.clear()

        # Сохранили контент страницы с очищенным кешем
        page_with_delited_post = self.guest_client.get(
            reverse('posts:index')
        ).content

        # Первый контент и контент с очищенным кешем различаются
        self.assertNotEqual(page_in_cache, page_with_delited_post)

    def test_authorized_can_follow(self):
        """Подписка работает."""
        follow_count = Follow.objects.count()

        # Подписались
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.creator_user.username}
            )
        )

        # Подсчитали что подписка прошла
        self.assertEqual(Follow.objects.count(), follow_count + 1)

        # Получили объект подписки
        follow = Follow.objects.first()

        # Проверили поля
        self.assertEqual(follow.user.username,
                         self.user.username)
        self.assertEqual(follow.author.username,
                         self.creator_user.username)

    def test_authorized_can_unfollow(self):
        """Отписка работает."""
        follow_count = Follow.objects.count()

        # Подписались
        Follow.objects.create(
            user=self.follower_user,
            author=self.creator_user
        )

        # Подписка прошла
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        # Отписались
        Follow.objects.filter(
            user=self.follower_user,
            author=self.creator_user           
        ).delete()

        # Подсчитали что количество подписок уменьшилось
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_subscription_feed_for_authorized(self):
        """Запись появляется для подписчиков."""
        # Оформляем подписку
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post.author.username}
            )
        )

        # Создаем пост
        exclusive_post = Post.objects.create(
            text='Текст для подписчиков',
            author=self.post.author
        )

        # Заходим на страницу постов подписок
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )

        # Берем оттуда текст эксклюзивного поста и сравниваем
        exclusive_post_text = response.context['page_obj'][0].text
        self.assertEqual(exclusive_post_text, exclusive_post.text)

    def test_subscription_feed_for_guest(self):
        """Запись не появляется для неподписанных."""
        # Создаем пост
        exclusive_post = Post.objects.create(
            text='Текст для подписчиков',
            author=self.post.author
        )
        response = self.authorized_client_2.get(
            reverse('posts:follow_index')
        )
        # Поста там нет
        self.assertNotIn(exclusive_post, response.context["page_obj"])


class PaginatorViewsTest(TestCase):
    """Проверка корректной работы пагинатора на index, group_list, profile."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        cls.author = User.objects.create_user(username='author')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )

        posts = []
        for i in range(1, 29):
            posts.append(
                Post(
                    text='Тестовый текст',
                    group=cls.group,
                    author=cls.author,
                )
            )

        cls.post = posts[0]
        Post.objects.bulk_create(posts)

        cls.pages_names_for_paginator_test = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.author.username}),
        ]

    def setUp(self):
        # Создаем авторизованный клиент
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        cache.clear()

    def test_first_page_containse_ten_records(self):
        """Количество постов на первой странице равно значению в настройках."""
        for name in self.pages_names_for_paginator_test:
            with self.subTest():
                response = self.authorized_client.get(name)
                self.assertEqual(len(
                    response.context.get('page_obj').object_list),
                    settings.POSTS_PER_PAGE)

    def test_last_page_containse_remaining_records(self):
        """Количество постов на последней
           странице корректно"""
        # Уже не гениальная формула подсчета последней страницы
        last_page = ceil(Post.objects.count() / settings.POSTS_PER_PAGE)

        for name in self.pages_names_for_paginator_test:
            with self.subTest():

                response = self.authorized_client.get(
                    name + f'?page={last_page}'
                )

                self.assertEqual(len(
                    response.context.get('page_obj').object_list),
                    (Post.objects.count() - settings.POSTS_PER_PAGE
                     * (last_page - 1)),
                )
