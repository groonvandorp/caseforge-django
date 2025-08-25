from celery import shared_task
from django.contrib.auth import get_user_model
from core.models import ProcessNode, NodeDocument, NodeUsecaseCandidate, NodeEmbedding
from .services import OpenAIService, ContextService, DocumentService
import uuid
import logging
from typing import List

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True)
def generate_process_details_task(self, user_id: int, node_id: int, include_branch: bool = False, 
                                cross_category: bool = False):
    """Async task to generate process details"""
    try:
        # Update status: Starting
        self.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 4, 'status': 'Loading process data...'}
        )
        
        user = User.objects.get(id=user_id)
        node = ProcessNode.objects.get(id=node_id)
        
        # Update status: Getting context
        self.update_state(
            state='PROGRESS',
            meta={'current': 2, 'total': 4, 'status': f'Analyzing process context for {node.code}...'}
        )
        
        # Get context
        context = ContextService.get_process_context(node, include_branch, cross_category)
        
        # Update status: Generating with AI
        self.update_state(
            state='PROGRESS',
            meta={'current': 3, 'total': 4, 'status': 'Generating detailed analysis with AI...'}
        )
        
        # Try to generate with AI, fall back to structured content if OpenAI fails
        try:
            ai_service = OpenAIService()
            details = ai_service.generate_process_details(node, context)
            logger.info(f"Generated AI-powered process details for {node.code}")
        except ValueError as config_error:
            logger.warning(f"OpenAI not configured for {node.code}: {str(config_error)}, using fallback")
            self.update_state(
                state='PROGRESS',
                meta={'current': 3, 'total': 4, 'status': 'OpenAI not configured, generating structured content...'}
            )
        except Exception as ai_error:
            logger.warning(f"OpenAI generation failed for {node.code}: {str(ai_error)}, using fallback")
            self.update_state(
                state='PROGRESS',
                meta={'current': 3, 'total': 4, 'status': 'AI service unavailable, generating structured content...'}
            )
            # Create structured fallback content
            details = {
                'summary': f"Process details for {node.name} (Code: {node.code})",
                'inputs': ['Input requirements to be defined based on process analysis'],
                'outputs': ['Output deliverables to be defined based on process requirements'],
                'kpis': ['Key performance indicators to be established'],
                'steps': [
                    'Step 1: Analyze current process state',
                    'Step 2: Identify improvement opportunities', 
                    'Step 3: Implement process enhancements',
                    'Step 4: Monitor and measure results'
                ],
                'upstream_processes': ['Upstream dependencies to be mapped'],
                'downstream_processes': ['Downstream impacts to be assessed'],
                'challenges': ['Process challenges to be identified through stakeholder analysis'],
                'best_practices': ['Industry best practices to be researched and applied']
            }
        
        # Create comprehensive markdown content
        markdown_content = f"""# Process Details: {node.name}

**Process Code:** {node.code}
**Process Level:** {node.level}
**Description:** {node.description or 'No description available'}

## Summary
{details.get('summary', 'Process summary to be developed')}

## Process Inputs
{chr(10).join(f"- {input_item}" for input_item in details.get('inputs', []))}

## Process Outputs  
{chr(10).join(f"- {output}" for output in details.get('outputs', []))}

## Key Performance Indicators
{chr(10).join(f"- {kpi}" for kpi in details.get('kpis', []))}

## Process Steps
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(details.get('steps', [])))}

## Upstream Processes
{chr(10).join(f"- {process}" for process in details.get('upstream_processes', []))}

## Downstream Processes
{chr(10).join(f"- {process}" for process in details.get('downstream_processes', []))}

## Common Challenges
{chr(10).join(f"- {challenge}" for challenge in details.get('challenges', []))}

## Best Practices
{chr(10).join(f"- {practice}" for practice in details.get('best_practices', []))}

---
*Generated on: {uuid.uuid4()}*
"""
        
        # Update status: Saving document
        self.update_state(
            state='PROGRESS',
            meta={'current': 4, 'total': 4, 'status': 'Saving document...'}
        )
        
        # Save document
        document = DocumentService.save_document(
            user=user,
            node=node,
            document_type='process_details',
            content=markdown_content,
            title=f"Process Details: {node.name}",
            meta_data=details
        )
        
        logger.info(f"Generated process details for {node.code} by user {user.username}")
        return {
            'document_id': document.id, 
            'success': True,
            'status': f'Process details generated successfully for {node.code}',
            'document_title': document.title
        }
        
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