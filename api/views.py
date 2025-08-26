import logging
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
logger = logging.getLogger(__name__)


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
    email = request.data.get('email')
    username = request.data.get('username')
    password = request.data.get('password')
    
    # Try to authenticate with email first, then username
    user = None
    if email:
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass
    
    if not user and username:
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

    @action(detail=True, methods=['post'])
    def generate_details(self, request, pk=None):
        """Generate process details using AI for a specific node"""
        node = self.get_object()
        
        # Only allow generation for leaf nodes (nodes with no children)
        if node.children.exists():
            return Response(
                {'error': 'Process details can only be generated for leaf nodes (nodes with no children)'}, 
                status=400
            )
        
        # Get parameters from request
        include_branch = request.data.get('include_branch', True)
        cross_category = request.data.get('cross_category', True)
        
        # Import the task here to avoid circular imports
        from .tasks import generate_process_details_task
        
        # Start the async task
        try:
            task = generate_process_details_task.delay(
                user_id=request.user.id,
                node_id=node.id,
                include_branch=include_branch,
                cross_category=cross_category
            )
            
            return Response({
                'message': 'Process details generation started. This will take a moment...',
                'task_id': task.id,
                'node_id': node.id,
                'node_code': node.code,
                'node_name': node.name,
                'status': 'PENDING'
            }, status=202)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to start process details generation: {str(e)}'}, 
                status=500
            )

    @action(detail=False, methods=['get'], url_path='task-status/(?P<task_id>[^/.]+)')
    def task_status(self, request, task_id=None):
        """Check the status of a background task"""
        try:
            from celery import Celery
            from django.conf import settings
            
            # Get celery app instance
            celery_app = Celery('caseforge')
            celery_app.config_from_object('django.conf:settings', namespace='CELERY')
            
            # Get task result
            task_result = celery_app.AsyncResult(task_id)
            
            response_data = {
                'task_id': task_id,
                'status': task_result.status,
                'ready': task_result.ready(),
            }
            
            # Add progress information if task is in progress
            if task_result.status == 'PROGRESS' and hasattr(task_result, 'info') and task_result.info:
                response_data['info'] = task_result.info
            
            if task_result.ready():
                if task_result.successful():
                    response_data['result'] = task_result.result
                    response_data['success'] = task_result.result.get('success', False) if isinstance(task_result.result, dict) else False
                else:
                    response_data['error'] = str(task_result.info)
                    response_data['success'] = False
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get task status: {str(e)}'}, 
                status=500
            )

    @action(detail=True, methods=['delete'])
    def delete_details(self, request, pk=None):
        """Delete process details document for a specific node"""
        node = self.get_object()
        
        try:
            # Find the process details document for this node
            document = NodeDocument.objects.get(
                node=node,
                user=request.user,
                document_type='process_details'
            )
            
            # Log the delete action before deletion
            logger.info(
                f"Process details deletion - User: {request.user.username} (ID: {request.user.id}), "
                f"Node: {node.code} - {node.name} (ID: {node.id}), "
                f"Document ID: {document.id}, "
                f"Document created: {document.created_at}, "
                f"IP: {request.META.get('REMOTE_ADDR', 'Unknown')}"
            )
            
            # Delete the document
            document.delete()
            
            logger.info(f"Process details successfully deleted for node {node.code} by user {request.user.username}")
            
            return Response({
                'message': 'Process details document deleted successfully',
                'node_id': node.id,
                'node_code': node.code,
                'node_name': node.name
            }, status=200)
            
        except NodeDocument.DoesNotExist:
            logger.warning(
                f"Process details deletion attempt failed - No document found for node {node.code} "
                f"by user {request.user.username} (ID: {request.user.id})"
            )
            return Response({
                'error': 'No process details document found for this node'
            }, status=404)
        
        except Exception as e:
            logger.error(
                f"Process details deletion failed for node {node.code} "
                f"by user {request.user.username} (ID: {request.user.id}): {str(e)}"
            )
            return Response({
                'error': f'Failed to delete process details: {str(e)}'
            }, status=500)


class NodeDocumentViewSet(ModelViewSet):
    serializer_class = NodeDocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = NodeDocument.objects.filter(user=self.request.user)
        
        # Filter by model_key if provided
        model_key = self.request.query_params.get('model_key')
        if model_key:
            queryset = queryset.filter(
                node__model_version__model__model_key=model_key,
                node__model_version__is_current=True
            )
        
        # Filter by document_type if provided
        document_type = self.request.query_params.get('document_type')
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        
        # Order by most recent first
        return queryset.select_related('node').order_by('-created_at')
    
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
    
    @action(detail=True, methods=['post'])
    def generate_specification(self, request, pk=None):
        """Generate detailed use case specification for a candidate"""
        candidate = self.get_object()
        
        # Import here to avoid circular imports
        from .tasks import generate_usecase_specification_task
        
        # Trigger async task
        task_result = generate_usecase_specification_task.delay(request.user.id, candidate.id)
        
        return Response({
            'success': True,
            'message': 'Specification generation started',
            'task_id': task_result.id
        })


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
