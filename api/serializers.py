from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import (
    ProcessModel, ProcessModelVersion, ProcessNode, NodeDocument,
    NodeUsecaseCandidate, NodeBookmark, Portfolio, PortfolioItem,
    UserSettings
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProcessModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessModel
        fields = ['id', 'model_key', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProcessModelVersionSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source='model.name', read_only=True)
    
    class Meta:
        model = ProcessModelVersion
        fields = ['id', 'model', 'model_name', 'version_label', 'external_reference', 
                 'notes', 'effective_date', 'is_current', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProcessNodeSerializer(serializers.ModelSerializer):
    is_leaf = serializers.ReadOnlyField()
    children_count = serializers.SerializerMethodField()
    pcf_id = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessNode
        fields = ['id', 'model_version', 'parent', 'code', 'name', 'description',
                 'level', 'display_order', 'materialized_path', 'is_leaf', 'children_count', 'pcf_id']
        read_only_fields = ['id']
    
    def get_children_count(self, obj):
        return obj.children.count()
    
    def get_pcf_id(self, obj):
        """Get PCF ID from node attributes"""
        try:
            pcf_attr = obj.attributes.filter(key='pcf_id').first()
            return pcf_attr.value if pcf_attr else None
        except:
            return None


class ProcessNodeTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    is_leaf = serializers.ReadOnlyField()
    pcf_id = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessNode
        fields = ['id', 'code', 'name', 'description', 'level', 'is_leaf', 'children', 'children_count', 'pcf_id']
        
    def get_children_count(self, obj):
        return obj.children.count()
    
    def get_pcf_id(self, obj):
        """Get PCF ID from node attributes"""
        try:
            pcf_attr = obj.attributes.filter(key='pcf_id').first()
            return pcf_attr.value if pcf_attr else None
        except:
            return None
    
    def get_children(self, obj):
        if obj.level >= 6:  # Allow up to level 5 nodes (6 would be children of level 5)
            return []
        children = obj.children.order_by('display_order', 'name')
        return ProcessNodeTreeSerializer(children, many=True).data


class NodeDocumentSerializer(serializers.ModelSerializer):
    node_code = serializers.CharField(source='node.code', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = NodeDocument
        fields = ['id', 'node', 'node_code', 'node_name', 'document_type', 
                 'title', 'content', 'meta_json', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NodeUsecaseCandidateSerializer(serializers.ModelSerializer):
    node_code = serializers.CharField(source='node.code', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = NodeUsecaseCandidate
        fields = ['id', 'node', 'node_code', 'node_name', 'candidate_uid', 
                 'title', 'description', 'impact_assessment', 'complexity_score',
                 'meta_json', 'created_at']
        read_only_fields = ['id', 'created_at']


class NodeBookmarkSerializer(serializers.ModelSerializer):
    node_code = serializers.CharField(source='node.code', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = NodeBookmark
        fields = ['id', 'node', 'node_code', 'node_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class PortfolioSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Portfolio
        fields = ['id', 'name', 'description', 'items_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_items_count(self, obj):
        return obj.items.count()


class PortfolioItemSerializer(serializers.ModelSerializer):
    usecase_title = serializers.CharField(source='usecase_candidate.title', read_only=True)
    node_code = serializers.CharField(source='usecase_candidate.node.code', read_only=True)
    candidate_uid = serializers.CharField(source='usecase_candidate.candidate_uid', read_only=True)
    
    class Meta:
        model = PortfolioItem
        fields = ['id', 'portfolio', 'usecase_candidate', 'usecase_title', 
                 'node_code', 'candidate_uid', 'added_at']
        read_only_fields = ['id', 'added_at']


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['preferred_model', 'theme', 'settings_json']