import jwt as pyjwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import (
    ProcessModel, ProcessModelVersion, ProcessNode, NodeDocument,
    NodeUsecaseCandidate, NodeBookmark, Portfolio, PortfolioItem,
    UserSettings, ModelAccess
)
from .serializers import (
    UserSerializer, ProcessModelSerializer, ProcessModelVersionSerializer,
    ProcessNodeSerializer, ProcessNodeTreeSerializer, NodeDocumentSerializer,
    NodeUsecaseCandidateSerializer, NodeBookmarkSerializer,
    PortfolioSerializer, PortfolioItemSerializer, UserSettingsSerializer
)

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)
    
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=400)
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )
    
    # Auto-provision access to all models for new users
    for model in ProcessModel.objects.all():
        ModelAccess.objects.create(user=user, model=model)
    
    return Response({'message': 'User created successfully'}, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def token(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Invalid credentials'}, status=401)
    
    if not user.is_active:
        return Response({'error': 'Account disabled'}, status=401)
    
    # Generate JWT token
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_DELTA)
    }
    
    token = pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return Response({
        'access_token': token,
        'token_type': 'bearer',
        'user': UserSerializer(user).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


class ProcessModelViewSet(ModelViewSet):
    serializer_class = ProcessModelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Filter by user access
        return ProcessModel.objects.filter(
            user_access__user=self.request.user
        ).distinct()


class ProcessModelVersionViewSet(ModelViewSet):
    serializer_class = ProcessModelVersionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        model_key = self.request.query_params.get('model_key')
        queryset = ProcessModelVersion.objects.filter(
            model__user_access__user=self.request.user
        ).select_related('model')
        
        if model_key:
            queryset = queryset.filter(model__model_key=model_key)
            
        return queryset.distinct()


class ProcessNodeViewSet(ModelViewSet):
    serializer_class = ProcessNodeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ProcessNode.objects.filter(
            model_version__model__user_access__user=self.request.user
        ).select_related('model_version', 'parent').distinct()
    
    @action(detail=False, methods=['get'])
    def roots(self, request):
        model_key = request.query_params.get('model_key')
        if not model_key:
            return Response({'error': 'model_key required'}, status=400)
        
        roots = self.get_queryset().filter(
            model_version__model__model_key=model_key,
            model_version__is_current=True,
            parent__isnull=True
        ).order_by('display_order', 'name')
        
        serializer = ProcessNodeTreeSerializer(roots, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        node = self.get_object()
        children = node.children.order_by('display_order', 'name')
        serializer = ProcessNodeSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def ancestors(self, request, pk=None):
        node = self.get_object()
        ancestors = []
        current = node.parent
        
        while current:
            ancestors.append(current)
            current = current.parent
            
        ancestors.reverse()
        serializer = ProcessNodeSerializer(ancestors, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-code/(?P<code>[^/.]+)')
    def by_code(self, request, code=None):
        model_key = request.query_params.get('model_key')
        if not model_key:
            return Response({'error': 'model_key required'}, status=400)
        
        try:
            node = self.get_queryset().get(
                code=code,
                model_version__model__model_key=model_key,
                model_version__is_current=True
            )
            serializer = ProcessNodeSerializer(node)
            return Response(serializer.data)
        except ProcessNode.DoesNotExist:
            return Response({'error': 'Node not found'}, status=404)


class NodeDocumentViewSet(ModelViewSet):
    serializer_class = NodeDocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NodeDocument.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_node(self, request):
        node_id = request.query_params.get('node_id')
        document_type = request.query_params.get('document_type')
        
        if not node_id:
            return Response({'error': 'node_id required'}, status=400)
        
        queryset = self.get_queryset().filter(node_id=node_id)
        
        if document_type:
            queryset = queryset.filter(document_type=document_type)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NodeUsecaseCandidateViewSet(ModelViewSet):
    serializer_class = NodeUsecaseCandidateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NodeUsecaseCandidate.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_node(self, request):
        node_id = request.query_params.get('node_id')
        if not node_id:
            return Response({'error': 'node_id required'}, status=400)
        
        candidates = self.get_queryset().filter(node_id=node_id)
        serializer = self.get_serializer(candidates, many=True)
        return Response(serializer.data)


class NodeBookmarkViewSet(ModelViewSet):
    serializer_class = NodeBookmarkSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NodeBookmark.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        node_id = request.data.get('node_id')
        if not node_id:
            return Response({'error': 'node_id required'}, status=400)
        
        bookmark, created = NodeBookmark.objects.get_or_create(
            user=request.user,
            node_id=node_id
        )
        
        if not created:
            bookmark.delete()
            return Response({'bookmarked': False})
        
        return Response({'bookmarked': True})
    
    @action(detail=False, methods=['get'])
    def counts(self, request):
        model_key = request.query_params.get('model_key')
        if not model_key:
            return Response({'error': 'model_key required'}, status=400)
        
        counts = NodeBookmark.objects.filter(
            user=request.user,
            node__model_version__model__model_key=model_key,
            node__model_version__is_current=True
        ).values('node__code').annotate(count=Count('id'))
        
        result = {item['node__code']: item['count'] for item in counts}
        return Response(result)


class PortfolioViewSet(ModelViewSet):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        portfolio = self.get_object()
        if portfolio.items.exists():
            return Response({'error': 'Cannot delete non-empty portfolio'}, status=400)
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        portfolio = self.get_object()
        items = portfolio.items.select_related('usecase_candidate__node')
        serializer = PortfolioItemSerializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        portfolio = self.get_object()
        candidate_uid = request.data.get('candidate_uid')
        
        if not candidate_uid:
            return Response({'error': 'candidate_uid required'}, status=400)
        
        try:
            candidate = NodeUsecaseCandidate.objects.get(
                candidate_uid=candidate_uid,
                user=request.user
            )
            
            item, created = PortfolioItem.objects.get_or_create(
                portfolio=portfolio,
                usecase_candidate=candidate
            )
            
            if created:
                return Response({'message': 'Item added to portfolio'}, status=201)
            else:
                return Response({'message': 'Item already in portfolio'}, status=200)
                
        except NodeUsecaseCandidate.DoesNotExist:
            return Response({'error': 'Use case candidate not found'}, status=404)
    
    @action(detail=True, methods=['delete'], url_path='items/(?P<candidate_uid>[^/.]+)')
    def remove_item(self, request, pk=None, candidate_uid=None):
        portfolio = self.get_object()
        
        try:
            item = PortfolioItem.objects.get(
                portfolio=portfolio,
                usecase_candidate__candidate_uid=candidate_uid
            )
            item.delete()
            return Response({'message': 'Item removed from portfolio'})
        except PortfolioItem.DoesNotExist:
            return Response({'error': 'Item not found in portfolio'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_specs(request):
    model_key = request.query_params.get('model_key')
    if not model_key:
        return Response({'error': 'model_key required'}, status=400)
    
    specs = NodeDocument.objects.filter(
        user=request.user,
        document_type='usecase_spec',
        node__model_version__model__model_key=model_key,
        node__model_version__is_current=True
    ).select_related('node').order_by('-created_at')
    
    serializer = NodeDocumentSerializer(specs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_settings_view(request):
    settings_obj, created = UserSettings.objects.get_or_create(user=request.user)
    serializer = UserSettingsSerializer(settings_obj)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_settings(request):
    settings_obj, created = UserSettings.objects.get_or_create(user=request.user)
    serializer = UserSettingsSerializer(settings_obj, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=400)
