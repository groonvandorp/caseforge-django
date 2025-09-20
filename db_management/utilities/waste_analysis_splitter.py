#!/usr/bin/env python
"""
Waste Analysis Splitter - Parse combined waste analysis into separate documents by type.

This utility takes the comprehensive waste analysis markdown and splits it into
12 separate documents for better filtering and search capabilities.
"""

import re
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import ProcessNode, NodeDocument
from datetime import datetime

class WasteAnalysisSplitter:

    # Define the 12 waste types with their identifiers
    WASTE_TYPES = {
        'transportation': {
            'emoji': '🚛',
            'name': 'Transportation Waste',
            'document_type': 'waste_transportation',
            'pattern': r'🚛 Transportation Waste.*?(?=🏃|📦|⏳|⚙️|📈|❌|🧠|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'inventory': {
            'emoji': '📦',
            'name': 'Inventory Waste',
            'document_type': 'waste_inventory',
            'pattern': r'📦 Inventory Waste.*?(?=🚛|🏃|⏳|⚙️|📈|❌|🧠|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'motion': {
            'emoji': '🏃',
            'name': 'Motion Waste',
            'document_type': 'waste_motion',
            'pattern': r'🏃 Motion Waste.*?(?=🚛|📦|⏳|⚙️|📈|❌|🧠|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'waiting': {
            'emoji': '⏳',
            'name': 'Waiting Waste',
            'document_type': 'waste_waiting',
            'pattern': r'⏳ Waiting Waste.*?(?=🚛|📦|🏃|⚙️|📈|❌|🧠|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'overprocessing': {
            'emoji': '⚙️',
            'name': 'Overprocessing Waste',
            'document_type': 'waste_overprocessing',
            'pattern': r'⚙️ Overprocessing Waste.*?(?=🚛|📦|🏃|⏳|📈|❌|🧠|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'overproduction': {
            'emoji': '📈',
            'name': 'Overproduction Waste',
            'document_type': 'waste_overproduction',
            'pattern': r'📈 Overproduction Waste.*?(?=🚛|📦|🏃|⏳|⚙️|❌|🧠|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'defects': {
            'emoji': '❌',
            'name': 'Defects Waste',
            'document_type': 'waste_defects',
            'pattern': r'❌ Defects Waste.*?(?=🚛|📦|🏃|⏳|⚙️|📈|🧠|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'skills': {
            'emoji': '🧠',
            'name': 'Skills Underutilization',
            'document_type': 'waste_skills',
            'pattern': r'🧠 Skills Underutilization.*?(?=🚛|📦|🏃|⏳|⚙️|📈|❌|💻|📚|📋|💬|Cross-cutting|\Z)'
        },
        'digital': {
            'emoji': '💻',
            'name': 'Digital Waste',
            'document_type': 'waste_digital',
            'pattern': r'💻 Digital Waste.*?(?=🚛|📦|🏃|⏳|⚙️|📈|❌|🧠|📚|📋|💬|Cross-cutting|\Z)'
        },
        'knowledge': {
            'emoji': '📚',
            'name': 'Knowledge Waste',
            'document_type': 'waste_knowledge',
            'pattern': r'📚 Knowledge Waste.*?(?=🚛|📦|🏃|⏳|⚙️|📈|❌|🧠|💻|📋|💬|Cross-cutting|\Z)'
        },
        'compliance': {
            'emoji': '📋',
            'name': 'Compliance Waste',
            'document_type': 'waste_compliance',
            'pattern': r'📋 Compliance Waste.*?(?=🚛|📦|🏃|⏳|⚙️|📈|❌|🧠|💻|📚|💬|Cross-cutting|\Z)'
        },
        'communication': {
            'emoji': '💬',
            'name': 'Communication Waste',
            'document_type': 'waste_communication',
            'pattern': r'💬 Communication Waste.*?(?=🚛|📦|🏃|⏳|⚙️|📈|❌|🧠|💻|📚|📋|Cross-cutting|\Z)'
        }
    }

    def __init__(self):
        self.processed_count = 0
        self.error_count = 0

    def extract_overall_context(self, content):
        """Extract the overall context/summary from the beginning of the analysis."""
        lines = content.split('\n')
        context_lines = []

        for line in lines:
            # Stop when we hit the first waste type emoji
            if any(waste['emoji'] in line for waste in self.WASTE_TYPES.values()):
                break
            context_lines.append(line)

        return '\n'.join(context_lines).strip()

    def extract_waste_section(self, content, waste_type_key):
        """Extract a specific waste type section from the content."""
        waste_info = self.WASTE_TYPES[waste_type_key]
        pattern = waste_info['pattern']

        # Use DOTALL flag to match across newlines
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(0).strip()
        else:
            return None

    def split_waste_analysis(self, node_id, combined_content, batch_metadata=None):
        """
        Split a combined waste analysis into 12 separate NodeDocument records.

        Args:
            node_id: ProcessNode ID
            combined_content: Full waste analysis markdown
            batch_metadata: Original batch metadata to preserve

        Returns:
            Tuple of (success_count, error_count)
        """

        try:
            node = ProcessNode.objects.get(id=node_id)
        except ProcessNode.DoesNotExist:
            print(f"❌ ProcessNode {node_id} not found")
            return 0, 1

        # Extract overall context for each document
        overall_context = self.extract_overall_context(combined_content)

        success_count = 0
        error_count = 0

        # Process each waste type
        for waste_key, waste_info in self.WASTE_TYPES.items():
            try:
                # Extract the specific waste section
                waste_section = self.extract_waste_section(combined_content, waste_key)

                if not waste_section:
                    print(f"⚠️  Could not extract {waste_info['name']} for node {node.code}")
                    error_count += 1
                    continue

                # Create the document content
                document_content = f"""# {waste_info['name']} Analysis for [{node.code}] {node.name}

{overall_context}

---

{waste_section}
"""

                # Create the document title
                title = f"{waste_info['name']} - {node.name}"

                # Prepare metadata
                meta_data = {
                    'waste_type': waste_key,
                    'waste_category': waste_info['name'],
                    'split_from': 'combined_waste_analysis',
                    'split_timestamp': datetime.now().isoformat()
                }

                # Preserve original batch metadata if provided
                if batch_metadata:
                    meta_data.update(batch_metadata)

                # Check if document already exists
                existing_doc = NodeDocument.objects.filter(
                    node=node,
                    document_type=waste_info['document_type']
                ).first()

                if existing_doc:
                    # Update existing document
                    existing_doc.content = document_content
                    existing_doc.title = title
                    existing_doc.meta_json = meta_data
                    existing_doc.updated_at = datetime.now()
                    existing_doc.save()
                    print(f"📝 Updated {waste_info['name']} for {node.code}")
                else:
                    # Create new document
                    NodeDocument.objects.create(
                        node=node,
                        document_type=waste_info['document_type'],
                        title=title,
                        content=document_content,
                        meta_json=meta_data
                    )
                    print(f"✅ Created {waste_info['name']} for {node.code}")

                success_count += 1

            except Exception as e:
                print(f"❌ Error processing {waste_info['name']} for node {node.code}: {str(e)}")
                error_count += 1

        return success_count, error_count

    def split_existing_waste_documents(self, model_key='apqc_pcf'):
        """
        Split all existing 'process_waste' documents into separate waste type documents.
        """
        from core.models import ProcessModelVersion

        # Get the model version
        model_version = ProcessModelVersion.objects.filter(
            model__model_key=model_key,
            is_current=True
        ).first()

        if not model_version:
            print(f"❌ Model {model_key} not found")
            return

        # Get all existing process_waste documents
        waste_documents = NodeDocument.objects.filter(
            node__model_version=model_version,
            document_type='process_waste'
        )

        print(f"🔍 Found {waste_documents.count()} process waste documents to split")

        total_success = 0
        total_errors = 0

        for doc in waste_documents:
            print(f"\n📊 Splitting waste analysis for [{doc.node.code}] {doc.node.name}")

            success, errors = self.split_waste_analysis(
                doc.node.id,
                doc.content,
                doc.meta_json
            )

            total_success += success
            total_errors += errors

        print(f"\n📈 Split Summary:")
        print(f"  ✅ Successfully created: {total_success} waste type documents")
        print(f"  ❌ Errors: {total_errors}")
        print(f"  📋 Average per process: {total_success/waste_documents.count():.1f} waste types")

        return total_success, total_errors

def main():
    """Main entry point for splitting waste analyses."""
    import argparse

    parser = argparse.ArgumentParser(description='Split combined waste analyses into separate documents')
    parser.add_argument('--model', default='apqc_pcf', help='Model key (default: apqc_pcf)')
    parser.add_argument('--test-file', help='Test with a specific markdown file')

    args = parser.parse_args()

    splitter = WasteAnalysisSplitter()

    if args.test_file:
        # Test with a specific file
        if os.path.exists(args.test_file):
            with open(args.test_file, 'r') as f:
                content = f.read()

            print("🧪 Testing waste analysis splitting...")

            # Extract sections for testing
            for waste_key, waste_info in splitter.WASTE_TYPES.items():
                section = splitter.extract_waste_section(content, waste_key)
                if section:
                    print(f"✅ Found {waste_info['name']}: {len(section)} characters")
                else:
                    print(f"❌ Missing {waste_info['name']}")
        else:
            print(f"❌ File {args.test_file} not found")
    else:
        # Split existing documents
        splitter.split_existing_waste_documents(args.model)

if __name__ == '__main__':
    main()