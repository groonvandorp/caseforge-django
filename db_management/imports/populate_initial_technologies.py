#!/usr/bin/env python3
"""
Populate Build Advisor with initial technology data from our landscape analysis
Based on the 37,000+ use case analysis results
"""

import os
import django
from django.utils.text import slugify

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from core.models import (
    TechnologyCategory, Vendor, Technology, TechnologyCapability, 
    TechnologyCapabilityMapping, UseCaseTechnologyRecommendation
)

def create_categories():
    """Create technology categories from our landscape analysis"""
    categories = [
        ("AI/ML Platforms", "Core artificial intelligence and machine learning platforms"),
        ("NLP & Language", "Natural language processing and text analytics"),
        ("Computer Vision", "Image and video processing technologies"),
        ("Process Automation", "Workflow orchestration and RPA tools"),
        ("Data Infrastructure", "Databases, streaming, and data processing"),
        ("Analytics & BI", "Predictive analytics and business intelligence"),
        ("Integration & API", "API management and system integration"),
        ("Cloud Platforms", "Cloud computing and infrastructure services"),
        ("Development Tools", "Development, deployment, and monitoring"),
    ]
    
    for name, description in categories:
        category, created = TechnologyCategory.objects.get_or_create(
            name=name,
            defaults={'description': description}
        )
        print(f"{'Created' if created else 'Found'} category: {name}")

def create_vendors():
    """Create major technology vendors"""
    vendors = [
        # Cloud Providers
        ("Microsoft", "cloud-provider", "https://microsoft.com", "strategic"),
        ("Amazon Web Services", "cloud-provider", "https://aws.amazon.com", "strategic"),
        ("Google", "cloud-provider", "https://cloud.google.com", "standard"),
        
        # AI/ML Leaders
        ("OpenAI", "startup", "https://openai.com", "standard"),
        ("Anthropic", "startup", "https://anthropic.com", "evaluating"),
        ("Hugging Face", "startup", "https://huggingface.co", "standard"),
        
        # Enterprise Software
        ("Databricks", "enterprise", "https://databricks.com", "preferred"),
        ("Snowflake", "enterprise", "https://snowflake.com", "standard"),
        ("Confluent", "enterprise", "https://confluent.io", "standard"),
        
        # Open Source
        ("Apache Software Foundation", "open-source", "https://apache.org", "none"),
        ("CNCF", "open-source", "https://cncf.io", "none"),
        ("Meta", "enterprise", "https://meta.com", "none"),
        
        # Automation/Integration
        ("UiPath", "enterprise", "https://uipath.com", "evaluating"),
        ("MuleSoft", "enterprise", "https://mulesoft.com", "standard"),
        ("Zapier", "software-vendor", "https://zapier.com", "standard"),
    ]
    
    for name, vendor_type, website, partnership in vendors:
        vendor, created = Vendor.objects.get_or_create(
            name=name,
            defaults={
                'vendor_type': vendor_type,
                'website': website,
                'partnership_status': partnership,
                'support_quality': 4 if partnership in ['strategic', 'preferred'] else 3,
                'market_position': 'leader' if name in ['Microsoft', 'Amazon Web Services', 'Google'] else 'challenger',
                'financial_stability': 5 if vendor_type == 'cloud-provider' else 4
            }
        )
        print(f"{'Created' if created else 'Found'} vendor: {name}")

def create_capabilities():
    """Create technology capabilities from use case analysis"""
    capabilities = [
        # NLP Capabilities
        ("Text Extraction", "NLP", ["ocr", "text extraction", "document parsing"]),
        ("Natural Language Processing", "NLP", ["nlp", "natural language", "text analysis"]),
        ("Sentiment Analysis", "NLP", ["sentiment", "emotion", "opinion mining"]),
        ("Large Language Models", "NLP", ["llm", "gpt", "large language model", "generative ai"]),
        
        # Analytics Capabilities  
        ("Predictive Analytics", "Analytics", ["predictive", "forecast", "prediction"]),
        ("Anomaly Detection", "Analytics", ["anomaly", "outlier", "unusual pattern"]),
        ("Optimization", "Analytics", ["optimization", "constraint", "linear programming"]),
        ("Clustering", "Analytics", ["clustering", "segmentation", "grouping"]),
        ("Graph Analytics", "Analytics", ["graph", "network analysis", "relationship"]),
        
        # Process Capabilities
        ("Workflow Orchestration", "Process", ["workflow", "orchestration", "pipeline"]),
        ("Process Automation", "Process", ["rpa", "robotic process", "automation"]),
        ("API Management", "Integration", ["api", "rest", "integration"]),
        ("Real-time Processing", "Data", ["real-time", "streaming", "event processing"]),
        
        # AI/ML Capabilities
        ("Computer Vision", "AI/ML", ["computer vision", "image recognition", "visual"]),
        ("Machine Learning", "AI/ML", ["machine learning", "ml", "model training"]),
        ("Deep Learning", "AI/ML", ["deep learning", "neural network", "tensorflow"]),
        ("Conversational AI", "AI/ML", ["chatbot", "conversational", "virtual assistant"]),
        
        # Data Capabilities
        ("Vector Search", "Data", ["vector", "embedding", "similarity search"]),
        ("Knowledge Graph", "Data", ["knowledge graph", "ontology", "semantic"]),
        ("Document Processing", "Data", ["document", "pdf", "ocr", "extraction"]),
    ]
    
    for name, category, keywords in capabilities:
        capability, created = TechnologyCapability.objects.get_or_create(
            name=name,
            defaults={
                'category': category,
                'keywords': keywords,
                'description': f"{name} capability for processing and analysis"
            }
        )
        print(f"{'Created' if created else 'Found'} capability: {name}")

def create_core_technologies():
    """Create core technologies from our landscape analysis"""
    
    # Get references to categories and vendors
    ai_ml = TechnologyCategory.objects.get(name="AI/ML Platforms")
    nlp = TechnologyCategory.objects.get(name="NLP & Language")
    process = TechnologyCategory.objects.get(name="Process Automation")
    data = TechnologyCategory.objects.get(name="Data Infrastructure")
    analytics = TechnologyCategory.objects.get(name="Analytics & BI")
    integration = TechnologyCategory.objects.get(name="Integration & API")
    cloud = TechnologyCategory.objects.get(name="Cloud Platforms")
    
    microsoft = Vendor.objects.get(name="Microsoft")
    aws = Vendor.objects.get(name="Amazon Web Services")
    google = Vendor.objects.get(name="Google")
    openai = Vendor.objects.get(name="OpenAI")
    databricks = Vendor.objects.get(name="Databricks")
    apache = Vendor.objects.get(name="Apache Software Foundation")
    
    technologies = [
        # LLMs and AI Platforms (Top priority from analysis)
        {
            'name': 'GPT-4 Turbo',
            'vendor': openai,
            'category': nlp,
            'description': 'Advanced large language model for text generation and analysis',
            'maturity_level': 'stable',
            'licensing_model': 'usage-based',
            'cost_range': 'high',
            'learning_curve': 'medium',
            'deployment_models': ['cloud'],
            'implementation_time': '1-2 weeks',
            'required_skills': ['Python', 'API integration', 'Prompt engineering'],
            'website': 'https://openai.com/gpt-4',
            'api_available': True,
            'capabilities': ['Large Language Models', 'Natural Language Processing', 'Text Extraction']
        },
        
        # Azure AI Services (Strategic partner)
        {
            'name': 'Azure OpenAI Service',
            'vendor': microsoft,
            'category': nlp,
            'description': 'Enterprise-grade OpenAI models with Azure security and compliance',
            'maturity_level': 'stable',
            'licensing_model': 'usage-based', 
            'cost_range': 'high',
            'learning_curve': 'medium',
            'deployment_models': ['cloud'],
            'implementation_time': '1-2 weeks',
            'required_skills': ['Azure', 'Python', 'API integration'],
            'website': 'https://azure.microsoft.com/en-us/products/ai-services/openai-service',
            'api_available': True,
            'capabilities': ['Large Language Models', 'Natural Language Processing']
        },
        
        {
            'name': 'Azure Form Recognizer',
            'vendor': microsoft,
            'category': nlp,
            'description': 'AI-powered document processing and OCR service',
            'maturity_level': 'stable',
            'licensing_model': 'usage-based',
            'cost_range': 'medium',
            'learning_curve': 'low',
            'deployment_models': ['cloud'],
            'implementation_time': '1-2 weeks', 
            'required_skills': ['Azure', 'REST API'],
            'website': 'https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence',
            'api_available': True,
            'capabilities': ['Text Extraction', 'Document Processing', 'OCR']
        },
        
        # Workflow Orchestration (Highest use case mentions: 1,792!)
        {
            'name': 'Apache Airflow',
            'vendor': apache,
            'category': process,
            'description': 'Open-source workflow orchestration platform',
            'maturity_level': 'mature',
            'licensing_model': 'open-source',
            'cost_range': 'free',
            'learning_curve': 'high',
            'deployment_models': ['cloud', 'on-premise', 'hybrid'],
            'implementation_time': '2-4 weeks',
            'required_skills': ['Python', 'Docker', 'Linux', 'DevOps'],
            'github_url': 'https://github.com/apache/airflow',
            'website': 'https://airflow.apache.org',
            'api_available': True,
            'capabilities': ['Workflow Orchestration', 'Process Automation']
        },
        
        # Machine Learning Platforms
        {
            'name': 'Azure Machine Learning',
            'vendor': microsoft,
            'category': ai_ml,
            'description': 'End-to-end machine learning lifecycle management',
            'maturity_level': 'stable',
            'licensing_model': 'usage-based',
            'cost_range': 'medium',
            'learning_curve': 'medium',
            'deployment_models': ['cloud'],
            'implementation_time': '2-4 weeks',
            'required_skills': ['Python', 'Machine Learning', 'Azure'],
            'website': 'https://azure.microsoft.com/en-us/products/machine-learning',
            'api_available': True,
            'capabilities': ['Machine Learning', 'Deep Learning', 'Predictive Analytics']
        },
        
        {
            'name': 'Databricks',
            'vendor': databricks,
            'category': ai_ml,
            'description': 'Unified analytics platform for big data and machine learning',
            'maturity_level': 'stable',
            'licensing_model': 'subscription',
            'cost_range': 'high',
            'learning_curve': 'medium',
            'deployment_models': ['cloud', 'hybrid'],
            'implementation_time': '3-6 weeks',
            'required_skills': ['Python', 'Spark', 'SQL', 'Machine Learning'],
            'website': 'https://databricks.com',
            'api_available': True,
            'capabilities': ['Machine Learning', 'Analytics', 'Real-time Processing']
        },
        
        # Vector Databases (Emerging but critical for RAG)
        {
            'name': 'Pinecone',
            'vendor': Vendor.objects.get_or_create(name='Pinecone', defaults={'vendor_type': 'startup', 'website': 'https://pinecone.io'})[0],
            'category': data,
            'description': 'Vector database for similarity search and AI applications',
            'maturity_level': 'stable',
            'licensing_model': 'freemium',
            'cost_range': 'medium',
            'learning_curve': 'low',
            'deployment_models': ['cloud'],
            'implementation_time': '1-2 weeks',
            'required_skills': ['Python', 'Vector embeddings', 'API integration'],
            'website': 'https://pinecone.io',
            'api_available': True,
            'capabilities': ['Vector Search', 'Machine Learning']
        },
    ]
    
    # Create technologies
    for tech_data in technologies:
        # Remove fields that need special handling
        capabilities = tech_data.pop('capabilities', [])
        cost_range = tech_data.pop('cost_range', 'medium')
        implementation_time = tech_data.pop('implementation_time', '2-4 weeks')
        
        technology, created = Technology.objects.get_or_create(
            name=tech_data['name'],
            vendor=tech_data['vendor'],
            defaults={
                **tech_data,
                'slug': slugify(tech_data['name']),
                'typical_cost_range': cost_range,
                'typical_implementation_time': implementation_time,
            }
        )
        
        # Add capabilities
        for cap_name in capabilities:
            try:
                capability = TechnologyCapability.objects.get(name=cap_name)
                TechnologyCapabilityMapping.objects.get_or_create(
                    technology=technology,
                    capability=capability,
                    defaults={'proficiency_level': 4}
                )
            except TechnologyCapability.DoesNotExist:
                print(f"Warning: Capability '{cap_name}' not found")
        
        print(f"{'Created' if created else 'Updated'} technology: {tech_data['name']}")

def main():
    """Run the full population script"""
    print("🚀 Populating Build Advisor with initial technology data...")
    
    print("\n1. Creating categories...")
    create_categories()
    
    print("\n2. Creating vendors...")
    create_vendors()
    
    print("\n3. Creating capabilities...")
    create_capabilities()
    
    print("\n4. Creating core technologies...")
    create_core_technologies()
    
    print(f"\n✅ Population complete!")
    print(f"Categories: {TechnologyCategory.objects.count()}")
    print(f"Vendors: {Vendor.objects.count()}")
    print(f"Technologies: {Technology.objects.count()}")
    print(f"Capabilities: {TechnologyCapability.objects.count()}")

if __name__ == '__main__':
    main()