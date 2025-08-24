from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import json


class User(AbstractUser):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username


class ProcessModel(models.Model):
    model_key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'process_model'

    def __str__(self):
        return self.name


class ProcessModelVersion(models.Model):
    model = models.ForeignKey(ProcessModel, on_delete=models.CASCADE, related_name='versions')
    version_label = models.CharField(max_length=50)
    external_reference = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'process_model_version'
        unique_together = ['model', 'version_label']

    def __str__(self):
        return f"{self.model.name} v{self.version_label}"


class SourceDocument(models.Model):
    model_version = models.ForeignKey(ProcessModelVersion, on_delete=models.CASCADE, related_name='documents')
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)
    checksum = models.CharField(max_length=128, blank=True, null=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'source_document'

    def __str__(self):
        return self.file_name


class ProcessNode(models.Model):
    model_version = models.ForeignKey(ProcessModelVersion, on_delete=models.CASCADE, related_name='nodes')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    level = models.IntegerField()
    display_order = models.IntegerField(blank=True, null=True)
    materialized_path = models.CharField(max_length=1000, blank=True, null=True)

    class Meta:
        db_table = 'process_node'
        unique_together = ['model_version', 'code']
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['model_version']),
            models.Index(fields=['code']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"

    @property
    def is_leaf(self):
        return not self.children.exists()


class NodeAttribute(models.Model):
    node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='attributes')
    key = models.CharField(max_length=100)
    value = models.TextField(blank=True, null=True)
    data_type = models.CharField(max_length=20, default='text')

    class Meta:
        db_table = 'node_attribute'
        unique_together = ['node', 'key']

    def __str__(self):
        return f"{self.node.code}.{self.key}"


class NodeRelationship(models.Model):
    from_node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='outgoing_relationships')
    to_node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='incoming_relationships')
    relationship_type = models.CharField(max_length=50)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'node_relationship'
        unique_together = ['from_node', 'to_node', 'relationship_type']

    def __str__(self):
        return f"{self.from_node.code} -> {self.to_node.code} ({self.relationship_type})"


class NodeEmbedding(models.Model):
    node = models.OneToOneField(ProcessNode, on_delete=models.CASCADE, related_name='embedding')
    embedding_vector = models.JSONField()
    embedding_model = models.CharField(max_length=100, default='text-embedding-3-small')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'node_embedding'

    def __str__(self):
        return f"Embedding for {self.node.code}"


class NodeDocument(models.Model):
    DOCUMENT_TYPES = [
        ('process_details', 'Process Details'),
        ('usecase_spec', 'Use Case Specification'),
        ('research_summary', 'Research Summary'),
    ]

    node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='documents')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    meta_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'node_document'
        indexes = [
            models.Index(fields=['node', 'user']),
            models.Index(fields=['document_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.document_type}: {self.node.code}"


class NodeUsecaseCandidate(models.Model):
    node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='usecase_candidates')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usecase_candidates')
    candidate_uid = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    impact_assessment = models.TextField(blank=True, null=True)
    complexity_score = models.IntegerField(blank=True, null=True)
    meta_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'node_usecase_candidate'
        indexes = [
            models.Index(fields=['node', 'user']),
            models.Index(fields=['candidate_uid']),
        ]

    def __str__(self):
        return f"{self.title} ({self.node.code})"


class UsecaseResearch(models.Model):
    document = models.ForeignKey(NodeDocument, on_delete=models.CASCADE, related_name='research_runs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='research_runs')
    research_query = models.CharField(max_length=500, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    web_results = models.JSONField(blank=True, null=True)
    synthesis_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'usecase_research'

    def __str__(self):
        return f"Research for {self.document.title}"


class NodeBookmark(models.Model):
    node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'node_bookmark'
        unique_together = ['node', 'user']

    def __str__(self):
        return f"{self.user.username} -> {self.node.code}"


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'portfolio'

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class PortfolioItem(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='items')
    usecase_candidate = models.ForeignKey(NodeUsecaseCandidate, on_delete=models.CASCADE, related_name='portfolio_items')
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'portfolio_item'
        unique_together = ['portfolio', 'usecase_candidate']

    def __str__(self):
        return f"{self.portfolio.name} -> {self.usecase_candidate.title}"


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    preferred_model = models.ForeignKey(ProcessModel, on_delete=models.SET_NULL, blank=True, null=True)
    theme = models.CharField(max_length=20, default='light', choices=[('light', 'Light'), ('dark', 'Dark')])
    settings_json = models.JSONField(default=dict)

    class Meta:
        db_table = 'user_settings'

    def __str__(self):
        return f"Settings for {self.user.username}"


class ModelAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='model_access')
    model = models.ForeignKey(ProcessModel, on_delete=models.CASCADE, related_name='user_access')
    granted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'model_access'
        unique_together = ['user', 'model']

    def __str__(self):
        return f"{self.user.username} -> {self.model.name}"
