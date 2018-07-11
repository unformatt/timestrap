from django.contrib.auth.models import User, Permission

from rest_framework import viewsets, permissions, filters
from rest_framework.permissions import IsAuthenticated

import django_filters

from core.models import Client, Project, Entry, Task, ProjectUser
from .serializers import (UserSerializer, ClientSerializer,
                          PermissionSerializer, ProjectSerializer,
                          EntrySerializer, TaskSerializer)
from .pagination import LimitOffsetPaginationWithTotals


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = None

    def get_permissions(self):
        # Prevent rest_framework from checking for the "view" perm.
        return (permissions.IsAuthenticated(),)

    def get_queryset(self):
        if self.request.user.is_superuser:
            queryset = User.objects.all()
        else:
            queryset = User.objects.filter(id=self.request.user.id)
        return queryset


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    pagination_class = None

    def get_permissions(self):
        # Prevent rest_framework from checking for the "view" perm.
        return (permissions.IsAuthenticated(),)

    def get_queryset(self):
        if self.request.user.is_superuser:
            queryset = Permission.objects.all()
        else:
            queryset = Permission.objects.filter(user=self.request.user)
        return queryset


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.on_site.filter(archive=False)
    serializer_class = ClientSerializer
    pagination_class = None
    filter_fields = ('id',)

    def get_queryset(self):
        return Client.on_site.all()


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.filter(archive=False)
    serializer_class = ProjectSerializer
    pagination_class = None
    filter_fields = ('id', 'client',)

    def get_queryset(self):
        return super().get_queryset().filter(id__in=ProjectUser.objects.filter(user=self.request.user).values_list('project_id', flat=True))


class EntryFilter(django_filters.rest_framework.FilterSet):
    min_date = django_filters.DateFilter(name="date", lookup_expr="gte")
    max_date = django_filters.DateFilter(name="date", lookup_expr="lte")

    class Meta:
        model = Entry
        fields = ('id', 'date', 'user', 'task', 'project', 'project__client',)


class EntryViewSet(viewsets.ModelViewSet):
    queryset = Entry.objects.all()
    serializer_class = EntrySerializer
    pagination_class = LimitOffsetPaginationWithTotals
    filter_class = EntryFilter
    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
        filters.OrderingFilter
    )
    ordering_fields = ('date', 'user__username', 'task__name', 'project__name',
                       'project__client__name',)
    ordering = ('-date', '-id')
    search_fields = ('id', 'date', 'note', 'user__username', 'task__name',
                     'project__name', 'project__client__name',)

    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = Entry.on_site.all()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        return qs

    def create(self, request):
        # TODO Enforce user has permission to this project
        project_id = int(request.data['project'].split('/')[-2])
        if ProjectUser.objects.filter(project_id=project_id, user=request.user).exists():
            response = super(EntryViewSet, self).create(request)
            return response
        else:
            raise Exception('User does not have access to project %s' % project_id)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    pagination_class = None

    def get_queryset(self):
        return Task.on_site.all()
