import logging
import jwt as pyjwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Count, Q
from django.http import HttpResponse
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
from .search_service import search_service
from .enhanced_search_service import EnhancedSearchService

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
        )
        
        # Custom sorting for process codes - convert to list and sort in Python
        roots_list = list(roots)
        
        def sort_key(node):
            # Try to extract numeric part from code for proper sorting
            try:
                # For codes like "1.0", "10.0", "5.0" - extract the first number
                import re
                match = re.match(r'^(\d+(?:\.\d+)?)', node.code)
                if match:
                    return float(match.group(1))
                else:
                    # Fall back to string sorting for non-numeric codes
                    return float('inf')  # Put non-numeric codes at the end
            except (ValueError, AttributeError):
                return float('inf')  # Put problematic codes at the end
        
        roots_list.sort(key=sort_key)
        
        serializer = ProcessNodeTreeSerializer(roots_list, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        node = self.get_object()
        children = list(node.children.all())
        
        # Custom sorting for process codes
        def sort_key(node):
            try:
                import re
                match = re.match(r'^(\d+(?:\.\d+)?)', node.code)
                if match:
                    return float(match.group(1))
                else:
                    return float('inf')
            except (ValueError, AttributeError):
                return float('inf')
        
        children.sort(key=sort_key)
        
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

    @action(detail=True, methods=['post'])
    def generate_usecases(self, request, pk=None):
        """Generate AI usecase candidates for a specific node"""
        node = self.get_object()
        
        # Only allow generation for leaf nodes (nodes with no children)
        if node.children.exists():
            return Response(
                {'error': 'AI usecase candidates can only be generated for leaf nodes (nodes with no children)'}, 
                status=400
            )
        
        # Check if process details document exists for this node
        from core.models import NodeDocument
        process_details_exists = NodeDocument.objects.filter(
            node=node,
            user=request.user,
            document_type='process_details'
        ).exists()
        
        if not process_details_exists:
            return Response(
                {'error': 'Process details must be generated first before creating AI usecase candidates'}, 
                status=400
            )
        
        # Get parameters from request
        include_branch = request.data.get('include_branch', True)
        cross_category = request.data.get('cross_category', True)
        
        # Import the task here to avoid circular imports
        from .tasks import generate_usecase_candidates_task
        
        # Start the async task
        try:
            task = generate_usecase_candidates_task.delay(
                user_id=request.user.id,
                node_id=node.id,
                include_branch=include_branch,
                cross_category=cross_category
            )
            
            return Response({
                'message': 'AI usecase candidates generation started. This will take a moment...',
                'task_id': task.id,
                'node_id': node.id,
                'node_code': node.code,
                'node_name': node.name,
                'status': 'PENDING'
            }, status=202)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to start usecase candidates generation: {str(e)}'}, 
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
        queryset = NodeDocument.objects.all()
        
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
        serializer.save()
    
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
    
    @action(detail=True, methods=['get'])
    def download_docx(self, request, pk=None):
        """Download document as DOCX file"""
        try:
            document = self.get_object()
            
            # Generate DOCX content
            from .services import DocumentService
            docx_content = DocumentService.export_to_docx(document)
            
            # Create filename: PDD-<process-id>-<processname>.docx
            process_name = document.node.name.replace(' ', '-').replace('/', '-').replace('\\', '-')
            filename = f"PDD-{document.node.code}-{process_name}.docx"
            
            # Create response
            response = HttpResponse(
                docx_content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response({'error': f'Failed to generate DOCX: {str(e)}'}, status=500)


class NodeUsecaseCandidateViewSet(ModelViewSet):
    serializer_class = NodeUsecaseCandidateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NodeUsecaseCandidate.objects.all()
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def by_node(self, request):
        node_id = request.query_params.get('node_id')
        if not node_id:
            return Response({'error': 'node_id required'}, status=400)
        
        candidates = self.get_queryset().filter(node_id=node_id)
        serializer = self.get_serializer(candidates, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download_docx(self, request, pk=None):
        """Download use case candidate as DOCX file"""
        try:
            candidate = self.get_object()
            
            # Generate DOCX content
            from .services import DocumentService
            docx_content = DocumentService.export_usecase_candidate_to_docx(candidate)
            
            # Create filename: AUC-<process-id>-<candidate-uid>.docx
            filename = f"AUC-{candidate.node.code}-{candidate.candidate_uid}.docx"
            
            # Create response
            response = HttpResponse(
                docx_content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response({'error': f'Failed to generate DOCX: {str(e)}'}, status=500)
    
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
        try:
            portfolio = self.get_object()
            candidate_uid = request.data.get('candidate_uid')
            
            if not candidate_uid:
                return Response({'error': 'candidate_uid required'}, status=400)
            
            try:
                candidate = NodeUsecaseCandidate.objects.get(
                    candidate_uid=candidate_uid
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
                
        except Exception as e:
            logger.error(f"Error in add_item: {str(e)}")
            return Response({'error': f'Failed to add item to portfolio: {str(e)}'}, status=500)
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        try:
            portfolio = self.get_object()
            candidate_uid = request.data.get('candidate_uid')
            
            if not candidate_uid:
                return Response({'error': 'candidate_uid required'}, status=400)
            
            try:
                item = PortfolioItem.objects.get(
                    portfolio=portfolio,
                    usecase_candidate__candidate_uid=candidate_uid
                )
                item.delete()
                return Response({'message': 'Item removed from portfolio'})
            except PortfolioItem.DoesNotExist:
                return Response({'error': 'Item not found in portfolio'}, status=404)
                
        except Exception as e:
            logger.error(f"Error in remove_item: {str(e)}")
            return Response({'error': f'Failed to remove item from portfolio: {str(e)}'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_specs(request):
    model_key = request.query_params.get('model_key')
    if not model_key:
        return Response({'error': 'model_key required'}, status=400)
    
    specs = NodeDocument.objects.filter(
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def semantic_search(request):
    """
    Enhanced semantic search for processes and use cases with scope filtering.
    
    Request body:
    {
        "query": "find customer service processes",
        "model_version_id": 1,  // optional: filter by specific version ID
        "model_key": "apqc_pcf", // optional: filter by model key (alternative to model_version_id)
        "scope": "all",         // optional: "processes", "usecases", or "all" (default: "all")
        "search_type": "hybrid", // optional: "semantic", "text", or "hybrid" (default: "hybrid")
        "level_filter": [1, 2], // optional: filter by process levels (processes only)
        "limit": 20,            // optional: max results (default: 20)
        "min_similarity": 0.1   // optional: min similarity threshold (default: 0.1)
    }
    """
    try:
        # Get request parameters
        query = request.data.get('query', '').strip()
        if not query:
            return Response({'error': 'Query parameter is required'}, status=400)
        
        model_version_id = request.data.get('model_version_id')
        model_key = request.data.get('model_key')
        scope = request.data.get('scope', 'all')
        search_type = request.data.get('search_type', 'hybrid')
        level_filter = request.data.get('level_filter', [])
        limit = request.data.get('limit', 20)
        min_similarity = request.data.get('min_similarity', 0.1)
        
        # Validate scope parameter
        if scope not in ['processes', 'usecases', 'all']:
            return Response({'error': 'Invalid scope. Must be "processes", "usecases", or "all"'}, status=400)
            
        # Validate search_type parameter
        if search_type not in ['semantic', 'text', 'hybrid']:
            return Response({'error': 'Invalid search_type. Must be "semantic", "text", or "hybrid"'}, status=400)
        
        # Convert model_key to model_version_id if provided
        if model_key and not model_version_id:
            from core.models import ProcessModelVersion, ProcessModel
            try:
                # Get the current version for the model
                model = ProcessModel.objects.get(model_key=model_key)
                current_version = ProcessModelVersion.objects.filter(
                    model=model, 
                    is_current=True
                ).first()
                if current_version:
                    model_version_id = current_version.id
                    logger.info(f"Converted model_key '{model_key}' to model_version_id {model_version_id}")
                else:
                    logger.warning(f"No current version found for model_key '{model_key}'")
            except ProcessModel.DoesNotExist:
                logger.warning(f"Model with key '{model_key}' not found")
        
        # Validate parameters
        if limit > 100:
            limit = 100  # Prevent excessive results
        
        logger.info(f"Enhanced search request: query='{query}', scope='{scope}', search_type='{search_type}', "
                   f"limit={limit}, model_version_id={model_version_id}, level_filter={level_filter}")
        
        # Handle use case only search early
        if scope == 'usecases':
            try:
                enhanced_search = EnhancedSearchService()
                results = enhanced_search.search(
                    query=query,
                    model_version_id=model_version_id,
                    scope='usecases',
                    search_type=search_type,
                    limit=limit
                )
                logger.info(f"Use case search completed: {results.get('total_count', 0)} results found")
                return Response(results)
            except Exception as e:
                logger.error(f"Error in use case search: {str(e)}")
                return Response({
                    'query': query,
                    'scope': scope,
                    'search_type': 'error',
                    'processes': [],
                    'usecases': [],
                    'total_count': 0,
                    'error': 'Use case search temporarily unavailable'
                })
        
        # Check if query looks like a process code (e.g., "1.1.1.1", "6.0", "3.2.1") - only for process scopes
        import re
        code_pattern = r'^\d+(\.\d+)*$'
        is_code_query = re.match(code_pattern, query.strip())
        
        
        if is_code_query:
            logger.info(f"Detected code query: '{query}' - using exact code search")
            # For exact code queries, use direct database lookup
            from core.models import ProcessNode
            try:
                nodes_query = ProcessNode.objects.select_related(
                    'parent', 'model_version__model'
                )
                
                if model_version_id:
                    nodes_query = nodes_query.filter(model_version_id=model_version_id)
                
                # Look for exact code match
                exact_match = nodes_query.filter(code=query.strip()).first()
                if exact_match:
                    results = [{
                        'node_id': exact_match.id,
                        'code': exact_match.code,
                        'name': exact_match.name,
                        'description': exact_match.description,
                        'level': exact_match.level,
                        'similarity_score': 1.0,  # Exact match
                        'model_key': exact_match.model_version.model.model_key,
                        'parent_code': exact_match.parent.code if exact_match.parent else None,
                        'parent_name': exact_match.parent.name if exact_match.parent else None,
                        'search_type': 'exact_code'
                    }]
                    
                    if scope in ['processes', 'usecases', 'all']:
                        return Response({
                            'query': query,
                            'scope': scope,
                            'search_type': 'exact_code',
                            'processes': results if scope in ['processes', 'all'] else [],
                            'usecases': [],
                            'total_count': 1 if scope in ['processes', 'all'] else 0
                        })
                    else:
                        return Response({
                            'results': results,
                            'search_type': 'exact_code',
                            'query': query,
                            'total_results': 1
                        })
                else:
                    # No exact match found, fall back to text search for codes
                    results = search_service.text_search_fallback(
                        query=query,
                        model_version_id=model_version_id,
                        level_filter=level_filter,
                        limit=limit
                    )
                    
                    if scope in ['processes', 'usecases', 'all']:
                        return Response({
                            'query': query,
                            'scope': scope,
                            'search_type': 'code_text_search',
                            'processes': results if scope in ['processes', 'all'] else [],
                            'usecases': [],
                            'total_count': len(results) if scope in ['processes', 'all'] else 0
                        })
                    else:
                        return Response({
                            'results': results,
                            'search_type': 'code_text_search',
                            'query': query,
                            'total_results': len(results)
                        })
                    
            except Exception as e:
                logger.error(f"Error in code search: {e}")
                # Fall through to semantic search
        
        try:
            logger.info(f"Starting hybrid search for query: '{query}'")
            
            # Generate embedding for the search query
            query_embedding = search_service.generate_query_embedding_sync(query)
            
            if not query_embedding:
                # Fallback to text search if embedding generation fails
                logger.warning("Query embedding generation failed, falling back to text search")
                results = search_service.text_search_fallback(
                    query=query,
                    model_version_id=model_version_id,
                    level_filter=level_filter,
                    limit=limit
                )
                
                if scope in ['processes', 'usecases', 'all']:
                    return Response({
                        'query': query,
                        'scope': scope,
                        'search_type': 'text_fallback',
                        'processes': results if scope in ['processes', 'all'] else [],
                        'usecases': [],
                        'total_count': len(results) if scope in ['processes', 'all'] else 0
                    })
                else:
                    return Response({
                        'results': results,
                        'search_type': 'text_fallback',
                        'query': query,
                        'total_results': len(results)
                    })
            
            # Perform semantic search with half the limit to leave room for text results
            semantic_limit = max(1, limit // 2)
            semantic_results = search_service.search_nodes(
                query_embedding=query_embedding,
                model_version_id=model_version_id,
                level_filter=level_filter,
                limit=semantic_limit,
                min_similarity=min_similarity
            )
            
            # Also perform text search to catch exact word matches that semantic search might miss
            text_limit = limit - len(semantic_results)
            text_results = search_service.text_search_fallback(
                query=query,
                model_version_id=model_version_id,
                level_filter=level_filter,
                limit=text_limit
            )
            
            logger.info(f"Hybrid search: semantic_results={len(semantic_results)}, text_results={len(text_results)}")
            
            # Combine results, prioritizing semantic results but including text matches
            seen_node_ids = set()
            combined_results = []
            
            # Add semantic results first
            for result in semantic_results:
                node_id = result['node_id']
                if node_id not in seen_node_ids:
                    seen_node_ids.add(node_id)
                    combined_results.append(result)
            
            # Add text results that weren't already included
            text_added_count = 0
            for result in text_results:
                node_id = result['node_id']
                code = result.get('code')
                if node_id not in seen_node_ids and len(combined_results) < limit:
                    seen_node_ids.add(node_id)
                    # Mark as text match for transparency
                    result['search_type'] = 'text_match'
                    combined_results.append(result)
                    text_added_count += 1
                    if code == '1.1.5':
                        logger.info(f"✅ Added target node [1.1.5] from text search!")
                else:
                    if code == '1.1.5':
                        duplicate = 'duplicate' if node_id in seen_node_ids else 'limit reached'
                        logger.info(f"❌ Target node [1.1.5] not added: {duplicate}")
                        
            logger.info(f"Added {text_added_count} unique text results to {len(semantic_results)} semantic results")
            
            search_type_result = 'hybrid' if len(text_results) > 0 and any(r.get('search_type') == 'text_match' for r in combined_results) else 'semantic'
            
            # For scoped search, check if we need to also search use cases
            if scope == 'all' and search_type != 'text':
                try:
                    # Use enhanced search for use cases
                    enhanced_search = EnhancedSearchService()
                    usecase_results = enhanced_search.search(
                        query=query,
                        model_version_id=model_version_id,
                        scope='usecases',
                        search_type=search_type,
                        limit=limit
                    )
                    
                    return Response({
                        'query': query,
                        'scope': scope,
                        'search_type': search_type_result,
                        'processes': combined_results[:limit],
                        'usecases': usecase_results.get('usecases', []),
                        'total_count': len(combined_results[:limit]) + len(usecase_results.get('usecases', []))
                    })
                except Exception as e:
                    logger.error(f"Error searching use cases: {str(e)}")
                    # Fall back to processes only
                    return Response({
                        'query': query,
                        'scope': scope,
                        'search_type': search_type_result,
                        'processes': combined_results[:limit],
                        'usecases': [],
                        'total_count': len(combined_results[:limit])
                    })
            elif scope == 'processes':
                # Return in new format for processes scope
                return Response({
                    'query': query,
                    'scope': scope,
                    'search_type': search_type_result,
                    'processes': combined_results[:limit],
                    'usecases': [],
                    'total_count': len(combined_results[:limit])
                })
            else:
                # Default backward compatibility
                return Response({
                    'results': combined_results[:limit],
                    'search_type': search_type_result,
                    'query': query,
                    'total_results': len(combined_results[:limit]),
                    'min_similarity': min_similarity,
                    'semantic_count': len(semantic_results),
                    'text_count': len([r for r in combined_results if r.get('search_type') == 'text_match'])
                })
        
        except ValueError as ve:
            # OpenAI service not available, fallback to text search
            logger.warning(f"Semantic search unavailable: {ve}, falling back to text search")
            
            results = search_service.text_search_fallback(
                query=query,
                model_version_id=model_version_id,
                level_filter=level_filter,
                limit=limit
            )
            
            if scope in ['processes', 'usecases', 'all']:
                return Response({
                    'query': query,
                    'scope': scope,
                    'search_type': 'text_fallback',
                    'processes': results if scope in ['processes', 'all'] else [],
                    'usecases': [],
                    'total_count': len(results) if scope in ['processes', 'all'] else 0,
                    'reason': 'OpenAI service unavailable'
                })
            else:
                return Response({
                    'results': results,
                    'search_type': 'text_fallback',
                    'query': query,
                    'total_results': len(results),
                    'reason': 'OpenAI service unavailable'
                })
        
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return Response({
                'error': 'Search service temporarily unavailable',
                'details': str(e)
            }, status=500)
    
    except Exception as e:
        logger.error(f"Unexpected error in semantic search: {str(e)}")
        return Response({'error': 'Internal server error'}, status=500)
