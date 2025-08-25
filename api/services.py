import json
import uuid
import asyncio
import logging
from typing import List, Dict, Any
from django.conf import settings
from openai import AsyncOpenAI
from core.models import ProcessNode, NodeDocument, NodeUsecaseCandidate, NodeEmbedding, AdminSettings

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        # Try admin settings first, fallback to environment variables
        api_key = AdminSettings.get_setting('openai_api_key') or settings.OPENAI_API_KEY
        self.model = AdminSettings.get_setting('openai_model') or settings.OPENAI_MODEL or 'gpt-4o'
        
        # Log configuration details
        api_key_source = "Admin Settings" if AdminSettings.get_setting('openai_api_key') else "Environment Variables"
        model_source = "Admin Settings" if AdminSettings.get_setting('openai_model') else "Default/Environment"
        
        logger.info(f"🔑 OpenAI API Key source: {api_key_source}")
        logger.info(f"🔑 API Key present: {'Yes' if api_key else 'No'}")
        if api_key:
            logger.info(f"🔑 API Key preview: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '****'}")
        
        logger.info(f"🎯 OpenAI Model source: {model_source}")
        logger.info(f"🎯 Model: {self.model}")
        
        if not api_key:
            logger.error("🔑 ❌ No OpenAI API key found!")
            raise ValueError("OpenAI API key not found. Please set it in Admin Settings or environment variables.")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("🤖 OpenAI AsyncClient initialized successfully")
    
    def generate_process_details(self, node: ProcessNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed process description with AI"""
        try:
            return asyncio.run(self._async_generate_process_details(node, context))
        except Exception as e:
            logger.error(f"🤖 ❌ Failed to run async generate_process_details: {str(e)}")
            raise
    
    async def _async_generate_process_details(self, node: ProcessNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of process details generation"""
        prompt = self._build_process_details_prompt(node, context)
        
        logger.info(f"🤖 [PROCESS_DETAILS] Starting OpenAI process details generation for node: {node.code}")
        logger.info(f"🤖 [PROCESS_DETAILS] Model: {self.model}")
        logger.info(f"🤖 [PROCESS_DETAILS] Prompt length: {len(prompt)} characters")
        logger.info(f"🤖 [PROCESS_DETAILS] Full prompt:\n{'-'*80}\n{prompt}\n{'-'*80}")
        
        system_message = "You are a business process expert. Generate detailed process information in JSON format."
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        logger.info(f"🤖 [PROCESS_DETAILS] System message: {system_message}")
        logger.info(f"🤖 [PROCESS_DETAILS] Messages structure: {len(messages)} messages")
        
        # Making OpenAI call with temperature for better, more creative results
        logger.info("🤖 [PROCESS_DETAILS] Making OpenAI call with temperature=0.7...")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7  # Balanced creativity vs consistency
            )
            
            logger.info("🤖 [PROCESS_DETAILS] ✅ OpenAI call successful")
            
        except Exception as api_error:
            logger.error(f"🤖 [PROCESS_DETAILS] ❌ OpenAI call failed: {str(api_error)}")
            logger.error(f"🤖 [PROCESS_DETAILS] Exception type: {type(api_error).__name__}")
            raise api_error
        
        # Log response details
        logger.info(f"🤖 [PROCESS_DETAILS] Response received:")
        logger.info(f"🤖 [PROCESS_DETAILS] - Model used: {response.model}")
        logger.info(f"🤖 [PROCESS_DETAILS] - Total tokens: {response.usage.total_tokens}")
        logger.info(f"🤖 [PROCESS_DETAILS] - Prompt tokens: {response.usage.prompt_tokens}")
        logger.info(f"🤖 [PROCESS_DETAILS] - Completion tokens: {response.usage.completion_tokens}")
        logger.info(f"🤖 [PROCESS_DETAILS] - Finish reason: {response.choices[0].finish_reason}")
        
        content = response.choices[0].message.content
        logger.info(f"🤖 [PROCESS_DETAILS] Response content length: {len(content)} characters")
        logger.info(f"🤖 [PROCESS_DETAILS] Full response content:\n{'-'*80}\n{content}\n{'-'*80}")
        
        try:
            parsed_result = json.loads(content)
            logger.info(f"🤖 [PROCESS_DETAILS] ✅ JSON parsing successful. Keys: {list(parsed_result.keys())}")
            return parsed_result
        except json.JSONDecodeError as e:
            logger.error(f"🤖 [PROCESS_DETAILS] ❌ JSON parsing failed: {str(e)}")
            logger.error(f"🤖 [PROCESS_DETAILS] Raw content that failed to parse: {content}")
            raise e
    
    def generate_usecase_candidates(self, node: ProcessNode, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate AI use case candidates for a process"""
        return asyncio.run(self._async_generate_usecase_candidates(node, context))
    
    async def _async_generate_usecase_candidates(self, node: ProcessNode, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Async implementation of usecase candidates generation"""
        prompt = self._build_usecase_prompt(node, context)
        
        logger.info(f"🤖 [USECASE_CANDIDATES] Starting OpenAI use case generation for node: {node.code}")
        logger.info(f"🤖 [USECASE_CANDIDATES] Model: {self.model}")
        logger.info(f"🤖 [USECASE_CANDIDATES] Prompt length: {len(prompt)} characters")
        logger.info(f"🤖 [USECASE_CANDIDATES] Full prompt:\n{'-'*80}\n{prompt}\n{'-'*80}")
        
        system_message = "You are an AI strategy consultant. Generate practical AI use case candidates in JSON format."
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        logger.info(f"🤖 [USECASE_CANDIDATES] System message: {system_message}")
        logger.info(f"🤖 [USECASE_CANDIDATES] Making OpenAI call with temperature=0.8...")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.8  # Higher for more creative use case ideas
            )
            
            logger.info(f"🤖 [USECASE_CANDIDATES] ✅ OpenAI call successful")
            logger.info(f"🤖 [USECASE_CANDIDATES] - Model used: {response.model}")
            logger.info(f"🤖 [USECASE_CANDIDATES] - Total tokens: {response.usage.total_tokens}")
            logger.info(f"🤖 [USECASE_CANDIDATES] - Prompt tokens: {response.usage.prompt_tokens}")
            logger.info(f"🤖 [USECASE_CANDIDATES] - Completion tokens: {response.usage.completion_tokens}")
            
            content = response.choices[0].message.content
            logger.info(f"🤖 [USECASE_CANDIDATES] Response content length: {len(content)} characters")
            logger.info(f"🤖 [USECASE_CANDIDATES] Full response:\n{'-'*80}\n{content}\n{'-'*80}")
            
            result = json.loads(content)
            logger.info(f"🤖 [USECASE_CANDIDATES] ✅ JSON parsing successful. Found {len(result.get('candidates', []))} candidates")
            return result.get('candidates', [])
            
        except Exception as e:
            logger.error(f"🤖 [USECASE_CANDIDATES] ❌ Failed: {str(e)}")
            raise
    
    def generate_usecase_specification(self, candidate: NodeUsecaseCandidate, context: Dict[str, Any]) -> str:
        """Generate detailed use case specification"""
        return asyncio.run(self._async_generate_usecase_specification(candidate, context))
    
    async def _async_generate_usecase_specification(self, candidate: NodeUsecaseCandidate, context: Dict[str, Any]) -> str:
        """Async implementation of usecase specification generation"""
        prompt = self._build_specification_prompt(candidate, context)
        
        logger.info(f"🤖 [USECASE_SPEC] Starting OpenAI specification generation for candidate: {candidate.title}")
        logger.info(f"🤖 [USECASE_SPEC] Model: {self.model}")
        logger.info(f"🤖 [USECASE_SPEC] Prompt length: {len(prompt)} characters")
        logger.info(f"🤖 [USECASE_SPEC] Full prompt:\n{'-'*80}\n{prompt}\n{'-'*80}")
        
        system_message = "You are a technical business analyst. Generate a comprehensive use case specification in markdown format."
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        logger.info(f"🤖 [USECASE_SPEC] System message: {system_message}")
        logger.info(f"🤖 [USECASE_SPEC] Making OpenAI call with temperature=0.6...")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.6  # Lower for more focused specifications
            )
            
            logger.info(f"🤖 [USECASE_SPEC] ✅ OpenAI call successful")
            logger.info(f"🤖 [USECASE_SPEC] - Model used: {response.model}")
            logger.info(f"🤖 [USECASE_SPEC] - Total tokens: {response.usage.total_tokens}")
            logger.info(f"🤖 [USECASE_SPEC] - Prompt tokens: {response.usage.prompt_tokens}")
            logger.info(f"🤖 [USECASE_SPEC] - Completion tokens: {response.usage.completion_tokens}")
            
            content = response.choices[0].message.content
            logger.info(f"🤖 [USECASE_SPEC] Response content length: {len(content)} characters")
            logger.info(f"🤖 [USECASE_SPEC] Full response:\n{'-'*80}\n{content}\n{'-'*80}")
            
            return content
            
        except Exception as e:
            logger.error(f"🤖 [USECASE_SPEC] ❌ Failed: {str(e)}")
            raise
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for similarity search"""
        return asyncio.run(self._async_generate_embeddings(texts))
    
    async def _async_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Async implementation of embeddings generation"""
        logger.info(f"🤖 [EMBEDDINGS] Starting OpenAI embeddings generation")
        logger.info(f"🤖 [EMBEDDINGS] Model: text-embedding-3-small")
        logger.info(f"🤖 [EMBEDDINGS] Number of texts: {len(texts)}")
        logger.info(f"🤖 [EMBEDDINGS] Total characters: {sum(len(t) for t in texts)}")
        
        for i, text in enumerate(texts[:3]):  # Log first 3 texts as sample
            preview = text[:200] + "..." if len(text) > 200 else text
            logger.info(f"🤖 [EMBEDDINGS] Sample text {i+1}: {preview}")
        
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            
            logger.info(f"🤖 [EMBEDDINGS] ✅ OpenAI embeddings call successful")
            logger.info(f"🤖 [EMBEDDINGS] - Model used: {response.model}")
            logger.info(f"🤖 [EMBEDDINGS] - Embeddings generated: {len(response.data)}")
            logger.info(f"🤖 [EMBEDDINGS] - Embedding dimensions: {len(response.data[0].embedding) if response.data else 0}")
            logger.info(f"🤖 [EMBEDDINGS] - Total tokens used: {response.usage.total_tokens}")
            
            return [embedding.embedding for embedding in response.data]
            
        except Exception as e:
            logger.error(f"🤖 [EMBEDDINGS] ❌ Failed: {str(e)}")
            raise
    
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