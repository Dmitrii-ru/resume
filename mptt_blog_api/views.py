from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from mptt.utils import get_cached_trees
from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404 as api404
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination

from mptt_blog.utils import random_posts
from django.db.models import Q, OuterRef, Exists
from rest_framework.viewsets import ReadOnlyModelViewSet
from .serializers import PostSerializer, CategoryPostsSerializer, CategorySerializer, CategoryCreateUpdateSerializer, \
    CategoriesSerializer
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from .models import CategoryBlog, PostBlog
from .permissions_custom import IsAuthor


class CategoryCreateViewAPI(generics.CreateAPIView):
    """
    Create new category with parent or orphan
    Permission : IsAuthenticated
    Authentication : JWT token

    """

    serializer_class = CategoryCreateUpdateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        parent_id = self.kwargs.get('id')
        parent = api404(CategoryBlog, id=parent_id) if parent_id else None
        serializer = self.serializer_class(
            data=request.data,
            context={'parent': parent}
        )

        if serializer.is_valid():
            category = CategoryBlog.objects.create(
                title=serializer.validated_data['title'].title(),
                author=request.user,
                parent=parent if parent else None
            )

            return Response(
                {
                    'massage': 'New category successfully created',
                    'id': category.id
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoriesAPIView(ReadOnlyModelViewSet):
    """
    Get categories all or by id

    """
    serializer_class = CategoriesSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return CategoryBlog.objects.all()

    def list(self, request, *args, **kwargs):
        if 'id' in self.kwargs:
            data = self.get_serializer(self.get_object()).data
        else:
            data = self.get_serializer(self.get_queryset(), many=True).data
        return Response(data, status=status.HTTP_200_OK)


class CategoryUpDelViewAPI(generics.RetrieveUpdateDestroyAPIView):
    """
    Update or delete category
    Permission : IsAuthor
    Authentication : JWT token

    """
    serializer_class = CategoryCreateUpdateSerializer
    permission_classes = [IsAuthor]
    queryset = CategoryBlog.objects.all()
    lookup_field = 'id'

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        message = {
            'message': 'Category successfully delete'
        }
        return Response(message, status=status.HTTP_204_NO_CONTENT)


def update_page_data_like_fav(request, page):
    if request.user.is_authenticated:
        post_ids = {x.id: i for i, x in enumerate(page)}

        for post_id in request.user.favourite_posts.filter(
                id__in=list(post_ids.keys())).values_list('id', flat=True):
            page[post_ids[post_id]].is_favour = True

        for post_id in request.user.like_posts.filter(
                id__in=list(post_ids.keys())).values_list('id', flat=True):
            page[post_ids[post_id]].is_like = True

    return page


class PaginatorCategoryPost(PageNumberPagination):
    page_size = 1
    page_size_query_param = 'page_size'
    max_page_size = 8


class CategoryPostAPIView(ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    serializer_class = CategoryPostsSerializer

    def get_queryset(self):
        category = api404(CategoryBlog, id=self.kwargs['id'])
        post_qs = PostBlog.objects.select_related('author').filter(Q(category=category))
        if self.request.user.is_authenticated:
            post_qs = post_qs.filter(Q(is_privat=False) | Q(author=self.request.user))
        else:
            post_qs = post_qs.filter(is_privat=False)
        queryset = {
            'post_qs': post_qs,
            'category': category
        }
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset['post_qs'])  # Применяем пагинацию
        if page is not None:
            # Здесь мы обновляем объекты на текущей странице
            page = update_page_data_like_fav(request, page)

            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        # Если нет пагинации, то просто сериализуем объекты
        return Response(serializer.data)
