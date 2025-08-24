import openai
import json
import uuid
from typing import List, Dict, Any
from django.conf import settings
from core.models import ProcessNode, NodeDocument, NodeUsecaseCandidate, NodeEmbedding


class OpenAIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
    
    def generate_process_details(self, node: ProcessNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed process description with AI"""
        prompt = self._build_process_details_prompt(node, context)
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a business process expert. Generate detailed process information in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        return json.loads(response.choices[0].message.content)
    
    def generate_usecase_candidates(self, node: ProcessNode, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate AI use case candidates for a process"""
        prompt = self._build_usecase_prompt(node, context)
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an AI strategy consultant. Generate practical AI use case candidates in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get('candidates', [])
    
    def generate_usecase_specification(self, candidate: NodeUsecaseCandidate, context: Dict[str, Any]) -> str:
        """Generate detailed use case specification"""
        prompt = self._build_specification_prompt(candidate, context)
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a technical business analyst. Generate a comprehensive use case specification in markdown format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        
        return response.choices[0].message.content
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for similarity search"""
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        
        return [embedding.embedding for embedding in response.data]
    
    def _build_process_details_prompt(self, node: ProcessNode, context: Dict[str, Any]) -> str:
        siblings = context.get('siblings', [])
        related = context.get('related', [])
        
        prompt = f"""
        Analyze this business process and provide detailed information:
        
        Process: {node.code} - {node.name}
        Description: {node.description or 'No description available'}
        Level: {node.level}
        
        Context:
        - Sibling processes: {', '.join([f"{s['code']}: {s['name']}" for s in siblings[:5]])}
        - Related processes: {', '.join([f"{r['code']}: {r['name']}" for r in related[:5]])}
        
        Generate a JSON response with:
        {{
            "summary": "Brief overview of the process",
            "inputs": ["list of typical inputs"],
            "outputs": ["list of typical outputs"],
            "kpis": ["key performance indicators"],
            "steps": ["detailed process steps"],
            "upstream_processes": ["processes that feed into this one"],
            "downstream_processes": ["processes that this feeds into"],
            "challenges": ["common challenges and pain points"],
            "best_practices": ["industry best practices"]
        }}
        """
        return prompt
    
    def _build_usecase_prompt(self, node: ProcessNode, context: Dict[str, Any]) -> str:
        prompt = f"""
        Generate AI use case candidates for this business process:
        
        Process: {node.code} - {node.name}
        Description: {node.description or 'No description available'}
        
        Generate 3-5 practical AI use case candidates in JSON format:
        {{
            "candidates": [
                {{
                    "title": "Clear, actionable title",
                    "description": "Detailed description of the AI solution",
                    "impact_assessment": "Expected business impact and benefits",
                    "complexity_score": 1-10,
                    "ai_technologies": ["list of relevant AI technologies"],
                    "implementation_effort": "Low/Medium/High",
                    "roi_potential": "Low/Medium/High"
                }}
            ]
        }}
        """
        return prompt
    
    def _build_specification_prompt(self, candidate: NodeUsecaseCandidate, context: Dict[str, Any]) -> str:
        prompt = f"""
        Create a comprehensive technical specification for this AI use case:
        
        Use Case: {candidate.title}
        Process: {candidate.node.code} - {candidate.node.name}
        Description: {candidate.description}
        Impact Assessment: {candidate.impact_assessment}
        
        Generate a detailed markdown specification including:
        - Executive Summary
        - Business Requirements
        - Technical Requirements
        - Implementation Plan
        - Success Metrics
        - Risk Assessment
        - Resource Requirements
        """
        return prompt


class ContextService:
    @staticmethod
    def get_process_context(node: ProcessNode, include_branch: bool = False, cross_category: bool = False) -> Dict[str, Any]:
        """Get contextual information for a process node"""
        context = {
            'siblings': [],
            'related': [],
            'nearest_neighbors': []
        }
        
        # Get siblings
        if node.parent:
            siblings = ProcessNode.objects.filter(
                parent=node.parent,
                model_version=node.model_version
            ).exclude(id=node.id).values('code', 'name', 'description')
            context['siblings'] = list(siblings)
        
        # Get related processes through embeddings
        if hasattr(node, 'embedding'):
            similar_nodes = ContextService._find_similar_nodes(node, limit=10)
            context['nearest_neighbors'] = similar_nodes
        
        # Branch context (L2 subtree)
        if include_branch and node.level >= 2:
            l2_ancestor = ContextService._get_l2_ancestor(node)
            if l2_ancestor:
                branch_nodes = ProcessNode.objects.filter(
                    model_version=node.model_version,
                    materialized_path__startswith=l2_ancestor.materialized_path
                ).exclude(id=node.id).values('code', 'name', 'description')
                context['branch_context'] = list(branch_nodes)
        
        return context
    
    @staticmethod
    def _find_similar_nodes(node: ProcessNode, limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar nodes using embedding similarity"""
        # This would implement cosine similarity search
        # For now, return related nodes by parent relationship
        if node.parent:
            related = ProcessNode.objects.filter(
                parent=node.parent,
                model_version=node.model_version
            ).exclude(id=node.id).values('code', 'name', 'description')[:limit]
            return list(related)
        return []
    
    @staticmethod
    def _get_l2_ancestor(node: ProcessNode) -> ProcessNode:
        """Get the level 2 ancestor of a node"""
        current = node
        while current and current.level > 2:
            current = current.parent
        return current if current and current.level == 2 else None


class DocumentService:
    @staticmethod
    def save_document(user, node: ProcessNode, document_type: str, content: str, 
                     title: str = None, meta_data: Dict = None) -> NodeDocument:
        """Save a document with proper user scoping"""
        document = NodeDocument.objects.create(
            user=user,
            node=node,
            document_type=document_type,
            title=title,
            content=content,
            meta_json=meta_data or {}
        )
        return document
    
    @staticmethod
    def find_document(user, node: ProcessNode, document_type: str) -> NodeDocument:
        """Find existing document for a node and user"""
        try:
            return NodeDocument.objects.get(
                user=user,
                node=node,
                document_type=document_type
            )
        except NodeDocument.DoesNotExist:
            return None
    
    @staticmethod
    def export_to_docx(document: NodeDocument) -> bytes:
        """Export document content to DOCX format"""
        from docx import Document
        from io import BytesIO
        
        doc = Document()
        doc.add_heading(document.title or f"{document.node.code} - {document.document_type}", 0)
        
        # Add content (assuming markdown)
        paragraphs = document.content.split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())
        
        # Save to bytes
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()