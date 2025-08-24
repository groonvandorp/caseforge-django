from celery import shared_task
from django.contrib.auth import get_user_model
from core.models import ProcessNode, NodeDocument, NodeUsecaseCandidate
from .services import OpenAIService, ContextService, DocumentService
import uuid
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def generate_process_details_task(user_id: int, node_id: int, include_branch: bool = False, 
                                cross_category: bool = False):
    """Async task to generate process details"""
    try:
        user = User.objects.get(id=user_id)
        node = ProcessNode.objects.get(id=node_id)
        
        # Get context
        context = ContextService.get_process_context(node, include_branch, cross_category)
        
        # Generate with AI
        ai_service = OpenAIService()
        details = ai_service.generate_process_details(node, context)
        
        # Save document
        document = DocumentService.save_document(
            user=user,
            node=node,
            document_type='process_details',
            content=details.get('summary', ''),
            title=f"Process Details: {node.name}",
            meta_data=details
        )
        
        logger.info(f"Generated process details for {node.code} by user {user.username}")
        return {'document_id': document.id, 'success': True}
        
    except Exception as e:
        logger.error(f"Failed to generate process details: {str(e)}")
        return {'error': str(e), 'success': False}


@shared_task
def generate_usecase_candidates_task(user_id: int, node_id: int, include_branch: bool = False,
                                   cross_category: bool = False):
    """Async task to generate AI use case candidates"""
    try:
        user = User.objects.get(id=user_id)
        node = ProcessNode.objects.get(id=node_id)
        
        # Get context
        context = ContextService.get_process_context(node, include_branch, cross_category)
        
        # Generate with AI
        ai_service = OpenAIService()
        candidates = ai_service.generate_usecase_candidates(node, context)
        
        # Save candidates
        saved_candidates = []
        for candidate_data in candidates:
            candidate_uid = str(uuid.uuid4())
            candidate = NodeUsecaseCandidate.objects.create(
                user=user,
                node=node,
                candidate_uid=candidate_uid,
                title=candidate_data.get('title', 'Untitled'),
                description=candidate_data.get('description', ''),
                impact_assessment=candidate_data.get('impact_assessment', ''),
                complexity_score=candidate_data.get('complexity_score'),
                meta_json=candidate_data
            )
            saved_candidates.append(candidate.id)
        
        logger.info(f"Generated {len(candidates)} use case candidates for {node.code} by user {user.username}")
        return {'candidate_ids': saved_candidates, 'success': True}
        
    except Exception as e:
        logger.error(f"Failed to generate use case candidates: {str(e)}")
        return {'error': str(e), 'success': False}


@shared_task
def generate_usecase_specification_task(user_id: int, candidate_id: int):
    """Async task to generate detailed use case specification"""
    try:
        user = User.objects.get(id=user_id)
        candidate = NodeUsecaseCandidate.objects.get(id=candidate_id, user=user)
        
        # Get context
        context = ContextService.get_process_context(candidate.node)
        
        # Generate specification
        ai_service = OpenAIService()
        specification = ai_service.generate_usecase_specification(candidate, context)
        
        # Save document
        document = DocumentService.save_document(
            user=user,
            node=candidate.node,
            document_type='usecase_spec',
            content=specification,
            title=f"Use Case Specification: {candidate.title}",
            meta_data={'candidate_uid': candidate.candidate_uid}
        )
        
        logger.info(f"Generated specification for use case {candidate.title} by user {user.username}")
        return {'document_id': document.id, 'success': True}
        
    except Exception as e:
        logger.error(f"Failed to generate use case specification: {str(e)}")
        return {'error': str(e), 'success': False}


@shared_task
def generate_embeddings_task(node_ids: List[int]):
    """Async task to generate embeddings for process nodes"""
    try:
        nodes = ProcessNode.objects.filter(id__in=node_ids)
        ai_service = OpenAIService()
        
        # Prepare texts for embedding
        texts = []
        for node in nodes:
            text = f"{node.name}. {node.description or ''}"
            texts.append(text)
        
        # Generate embeddings
        embeddings = ai_service.generate_embeddings(texts)
        
        # Save embeddings
        for node, embedding in zip(nodes, embeddings):
            NodeEmbedding.objects.update_or_create(
                node=node,
                defaults={
                    'embedding_vector': embedding,
                    'embedding_model': 'text-embedding-3-small'
                }
            )
        
        logger.info(f"Generated embeddings for {len(node_ids)} nodes")
        return {'processed_count': len(node_ids), 'success': True}
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {str(e)}")
        return {'error': str(e), 'success': False}