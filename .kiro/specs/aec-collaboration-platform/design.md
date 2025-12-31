# Design Document: AEC Collaboration Platform

## Overview

本设计文档描述了跨单位工程协同平台的技术架构和实现方案。系统采用"Meta-Data + Object Store"架构模式，模仿Git LFS的设计理念，将文件元数据与实际内容分离存储。核心技术栈包括：

- **Web Framework**: FastAPI (Python) - 高性能异步Web框架
- **ORM**: SQLAlchemy 2.0 - 数据库抽象层
- **Database**: PostgreSQL - 关系型数据库
- **Object Storage**: MinIO/Alibaba OSS - 对象存储后端
- **Task Queue**: Celery + Redis - 异步任务处理
- **File Conversion**: Autodesk Forge SDK, xeokit-sdk - CAD/BIM转换
- **Digital Signature**: PyMuPDF + cryptography - PDF电子签章

系统支持多租户隔离、大文件增量同步、版本控制、图纸预览、审批流程等核心功能。

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  (Desktop Client / Web Browser / Cloud PC)                   │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTPS/WebDAV
┌────────────────▼────────────────────────────────────────────┐
│                     API Gateway Layer                        │
│              FastAPI + Authentication Middleware             │
└────┬──────────────────────────────────────────────┬─────────┘
     │                                               │
┌────▼─────────────────────┐          ┌────────────▼──────────┐
│   Business Logic Layer   │          │   Task Queue Layer    │
│  - Tenant Management     │          │   Celery Workers      │
│  - File Operations       │          │  - File Conversion    │
│  - Version Control       │          │  - Preview Generation │
│  - Workflow Engine       │          │  - Async Processing   │
└────┬─────────────────────┘          └───────────────────────┘
     │                                               
┌────▼─────────────────────┐          ┌───────────────────────┐
│   Data Persistence Layer │          │  Object Storage Layer │
│   PostgreSQL + SQLAlchemy│          │   MinIO / OSS         │
│  - Metadata              │          │  - File Chunks (CAS)  │
│  - Version History       │          │  - Converted Previews │
│  - Workflow State        │          │                       │
└──────────────────────────┘          └───────────────────────┘
```

### Storage Architecture (Git LFS-like)

系统采用内容寻址存储(CAS)模式：

1. **Chunking**: 客户端将大文件分割为固定大小的块（如4MB）
2. **Hashing**: 对每个块计算SHA-256哈希值
3. **Deduplication**: 相同内容的块只存储一次
4. **Metadata**: 数据库记录文件结构和块引用关系
5. **Reconstruction**: 下载时根据元数据重组文件

```
FileVersion (Metadata)
├── file_id: UUID
├── version_number: int
├── commit_hash: str
└── chunks: List[ChunkReference]
    ├── ChunkReference
    │   ├── chunk_hash: str (SHA-256)
    │   ├── chunk_index: int
    │   └── chunk_size: int
    └── ...

Object Storage (Content)
├── objects/
│   ├── ab/cd/abcd1234... (chunk content)
│   ├── ef/gh/efgh5678... (chunk content)
│   └── ...
```

## Components and Interfaces

### 1. Tenant Management Module

**Responsibility**: 管理多租户隔离和组织结构

**Key Classes**:
- `TenantService`: 租户CRUD操作
- `TenantContext`: 请求上下文中的租户信息

**Interfaces**:
```python
class TenantService:
    def create_tenant(name: str, tenant_type: TenantType) -> Tenant
    def get_tenant(tenant_id: UUID) -> Tenant
    def list_tenants() -> List[Tenant]
    def delete_tenant(tenant_id: UUID) -> bool
```

**Data Isolation Strategy**: 
- 使用PostgreSQL的Row-Level Security (RLS)
- 每个查询自动添加tenant_id过滤条件
- 通过中间件注入租户上下文

### 2. Project & Permission Module

**Responsibility**: 项目管理和基于角色的访问控制(RBAC)

**Key Classes**:
- `ProjectService`: 项目生命周期管理
- `PermissionService`: 权限验证和授权
- `RoleManager`: 角色定义和分配

**Permission Matrix**:
```
Role      | Read | Write | Delete | Approve | Admin |
----------|------|-------|--------|---------|-------|
Owner     |  ✓   |   ✓   |   ✓    |    ✓    |   ✓   |
Editor    |  ✓   |   ✓   |   ✗    |    ✗    |   ✗   |
Viewer    |  ✓   |   ✗   |   ✗    |    ✗    |   ✗   |
Approver  |  ✓   |   ✗   |   ✗    |    ✓    |   ✗   |
```

**Interfaces**:
```python
class PermissionService:
    def check_permission(user_id: UUID, resource: Resource, action: Action) -> bool
    def grant_permission(user_id: UUID, project_id: UUID, role: Role) -> None
    def revoke_permission(user_id: UUID, project_id: UUID) -> None
```

### 3. File System Module

**Responsibility**: 文件和目录的逻辑组织

**Key Classes**:
- `FileSystemService`: 文件系统操作
- `FileNode`: 文件/目录节点
- `PathResolver`: 路径解析和验证

**Tree Structure**:
```python
class FileNode:
    id: UUID
    name: str
    path: str  # Full path from repository root
    node_type: Enum['file', 'directory']
    parent_id: Optional[UUID]
    repository_id: UUID
    current_version_id: Optional[UUID]  # For files only
    created_at: datetime
    updated_at: datetime
```

**Interfaces**:
```python
class FileSystemService:
    def create_directory(repository_id: UUID, path: str) -> FileNode
    def create_file(repository_id: UUID, path: str) -> FileNode
    def move_node(node_id: UUID, new_path: str) -> FileNode
    def delete_node(node_id: UUID) -> bool
    def list_children(node_id: UUID) -> List[FileNode]
```

### 4. Chunked Upload Module

**Responsibility**: 大文件分块上传和增量同步

**Key Classes**:
- `ChunkManager`: 块管理和去重
- `UploadSession`: 上传会话管理
- `DeltaCalculator`: 增量计算

**Upload Flow**:
```
Client                          Server
  │                               │
  ├─1. POST /upload/init─────────>│ Create UploadSession
  │<────────session_id────────────┤
  │                               │
  ├─2. POST /upload/check────────>│ Check existing chunks
  │    [chunk_hashes]             │ Query database
  │<────[missing_hashes]──────────┤
  │                               │
  ├─3. PUT /upload/chunk─────────>│ Upload missing chunks
  │    (chunk_data)               │ Store to object storage
  │<────200 OK─────────────────────┤
  │                               │
  ├─4. POST /upload/finalize────>│ Create FileVersion
  │                               │ Link chunks
  │<────file_version──────────────┤
```

**Interfaces**:
```python
class ChunkManager:
    def check_chunks_exist(chunk_hashes: List[str]) -> List[str]  # Returns missing
    def upload_chunk(chunk_hash: str, chunk_data: bytes) -> bool
    def get_chunk(chunk_hash: str) -> bytes
    def link_chunks_to_version(version_id: UUID, chunk_refs: List[ChunkReference]) -> None
```

### 5. Version Control Module

**Responsibility**: 文件版本历史和提交管理

**Key Classes**:
- `VersionService`: 版本CRUD操作
- `CommitManager`: 提交记录管理
- `MergeStrategy`: 合并策略实现

**Version Graph**:
```
FileNode
  └── versions: List[FileVersion]
      ├── v1 (commit: abc123)
      ├── v2 (commit: def456, parent: abc123)
      └── v3 (commit: ghi789, parent: def456)
```

**Interfaces**:
```python
class VersionService:
    def create_version(file_id: UUID, chunks: List[ChunkReference], 
                      commit_msg: str, author_id: UUID) -> FileVersion
    def get_version(version_id: UUID) -> FileVersion
    def list_versions(file_id: UUID) -> List[FileVersion]
    def checkout_version(file_id: UUID, version_id: UUID) -> None
    def merge_versions(base_version_id: UUID, target_version_id: UUID) -> FileVersion
```

### 6. Object Storage Adapter

**Responsibility**: 统一的对象存储接口，支持多种后端

**Key Classes**:
- `StorageBackend`: 抽象基类
- `MinIOBackend`: MinIO实现
- `OSSBackend`: Alibaba OSS实现

**Interfaces**:
```python
class StorageBackend(ABC):
    @abstractmethod
    def put_object(key: str, data: bytes) -> bool
    
    @abstractmethod
    def get_object(key: str) -> bytes
    
    @abstractmethod
    def delete_object(key: str) -> bool
    
    @abstractmethod
    def object_exists(key: str) -> bool
```

**Configuration**:
```python
# Environment variables
STORAGE_BACKEND = "minio"  # or "oss"
STORAGE_ENDPOINT = "localhost:9000"
STORAGE_ACCESS_KEY = "..."
STORAGE_SECRET_KEY = "..."
STORAGE_BUCKET = "aec-platform"
```

### 7. File Conversion Module

**Responsibility**: CAD/BIM文件转换为Web可预览格式

**Key Classes**:
- `ConversionService`: 转换任务调度
- `CADConverter`: 2D CAD转换器
- `BIMConverter`: 3D BIM转换器
- `PreviewCache`: 预览结果缓存

**Conversion Pipeline**:
```
Original File (.dwg/.rvt/.ifc)
    │
    ├─> Celery Task Queue
    │
    ├─> Worker picks up task
    │
    ├─> Call conversion library
    │   ├─ CAD: Autodesk Forge API / ODA File Converter
    │   └─ BIM: xeokit / IfcOpenShell
    │
    ├─> Generate web format
    │   ├─ CAD: SVF / PDF
    │   └─ BIM: glTF / 3D Tiles
    │
    └─> Store to object storage
        └─> Update conversion status in database
```

**Interfaces**:
```python
class ConversionService:
    def request_conversion(file_version_id: UUID, 
                          output_format: str) -> str  # Returns task_id
    def get_conversion_status(task_id: str) -> ConversionStatus
    def get_preview_url(file_version_id: UUID) -> str

# Celery tasks
@celery_app.task
def convert_cad_file(file_version_id: UUID, output_format: str) -> None
    
@celery_app.task
def convert_bim_file(file_version_id: UUID, output_format: str) -> None
```

### 8. Workflow Engine Module

**Responsibility**: 审批流程定义和执行

**Key Classes**:
- `WorkflowService`: 流程管理
- `WorkflowInstance`: 流程实例
- `ApprovalNode`: 审批节点
- `WorkflowExecutor`: 流程执行引擎

**Workflow State Machine**:
```
[Draft] ──submit──> [Pending]
                       │
                       ├─approve─> [Node1_Approved]
                       │              │
                       │              ├─approve─> [Node2_Approved]
                       │              │              │
                       │              │              └─approve─> [Completed]
                       │              │
                       │              └─reject──> [Rejected]
                       │
                       └─reject──> [Rejected]
```

**Interfaces**:
```python
class WorkflowService:
    def create_workflow(name: str, nodes: List[ApprovalNodeConfig]) -> Workflow
    def start_workflow(workflow_id: UUID, file_version_id: UUID) -> WorkflowInstance
    def approve_node(instance_id: UUID, node_id: UUID, 
                    approver_id: UUID, comment: str) -> WorkflowInstance
    def reject_node(instance_id: UUID, node_id: UUID, 
                   approver_id: UUID, reason: str) -> WorkflowInstance
    def get_pending_approvals(user_id: UUID) -> List[WorkflowInstance]
```

### 9. Digital Seal Module

**Responsibility**: PDF电子签章和数字签名

**Key Classes**:
- `DigitalSealService`: 签章管理
- `PDFSigner`: PDF签名实现
- `CertificateManager`: 证书管理

**Signing Process**:
```
1. Load PDF file from storage
2. Load approver's digital seal image
3. Insert seal image at specified coordinates
4. Generate cryptographic signature using CA certificate
5. Embed signature in PDF
6. Calculate and store certificate hash for legal evidence
7. Save signed PDF back to storage
8. Mark FileVersion as signed and read-only
```

**Interfaces**:
```python
class DigitalSealService:
    def create_seal(user_id: UUID, seal_image: bytes, 
                   certificate: bytes) -> DigitalSeal
    def apply_seal_to_pdf(file_version_id: UUID, seal_id: UUID, 
                         position: Tuple[int, int]) -> bytes  # Returns signed PDF
    def verify_signature(file_version_id: UUID) -> bool
    def get_signature_info(file_version_id: UUID) -> SignatureInfo
```

### 10. VFS/WebDAV Module

**Responsibility**: 为云电脑提供文件系统挂载接口

**Key Classes**:
- `VFSProvider`: 虚拟文件系统提供者
- `WebDAVHandler`: WebDAV协议处理器
- `MountTokenManager`: 挂载凭证管理

**Mount Flow**:
```
Cloud PC                        Platform
   │                               │
   ├─1. GET /mount/credentials───>│ Generate time-limited token
   │<────token + endpoint──────────┤
   │                               │
   ├─2. PROPFIND /webdav/────────>│ List directory
   │<────file list─────────────────┤
   │                               │
   ├─3. GET /webdav/file.dwg─────>│ Download file
   │<────file content──────────────┤
   │                               │
   ├─4. PUT /webdav/file.dwg─────>│ Upload new version
   │<────201 Created───────────────┤ Create FileVersion
```

**Interfaces**:
```python
class VFSProvider:
    def generate_mount_token(user_id: UUID, project_id: UUID, 
                            ttl_seconds: int) -> str
    def validate_mount_token(token: str) -> Optional[MountContext]
    def get_webdav_endpoint() -> str

class WebDAVHandler:
    def handle_propfind(path: str, depth: int) -> WebDAVResponse
    def handle_get(path: str) -> bytes
    def handle_put(path: str, content: bytes) -> WebDAVResponse
    def handle_delete(path: str) -> WebDAVResponse
```

## Data Models

### Core Entities

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

class Tenant(Base):
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    tenant_type = Column(Enum('design', 'construction', 'owner', 'supervision', 
                             name='tenant_type_enum'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = relationship("Project", back_populates="tenant")
    users = relationship("User", back_populates="tenant")

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    repositories = relationship("Repository", back_populates="project")
    members = relationship("ProjectMember", back_populates="project")

class ProjectMember(Base):
    __tablename__ = 'project_members'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    role = Column(Enum('owner', 'editor', 'viewer', 'approver', 
                      name='project_role_enum'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")

class Repository(Base):
    __tablename__ = 'repositories'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    specialty = Column(String(100))  # e.g., 'architecture', 'structure', 'mep'
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="repositories")
    file_nodes = relationship("FileNode", back_populates="repository")

class FileNode(Base):
    __tablename__ = 'file_nodes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    path = Column(String(2000), nullable=False)  # Full path from repository root
    node_type = Column(Enum('file', 'directory', name='node_type_enum'), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('file_nodes.id'), nullable=True)
    repository_id = Column(UUID(as_uuid=True), ForeignKey('repositories.id'), nullable=False)
    current_version_id = Column(UUID(as_uuid=True), ForeignKey('file_versions.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    repository = relationship("Repository", back_populates="file_nodes")
    parent = relationship("FileNode", remote_side=[id], backref="children")
    versions = relationship("FileVersion", back_populates="file_node", 
                          foreign_keys="FileVersion.file_node_id")
    current_version = relationship("FileVersion", foreign_keys=[current_version_id])

class FileVersion(Base):
    __tablename__ = 'file_versions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_node_id = Column(UUID(as_uuid=True), ForeignKey('file_nodes.id'), nullable=False)
    version_number = Column(Integer, nullable=False)
    commit_hash = Column(String(64), nullable=False, unique=True)  # SHA-256
    commit_message = Column(String(1000))
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey('file_versions.id'), nullable=True)
    file_size = Column(Integer, nullable=False)  # Total size in bytes
    chunk_refs = Column(JSON, nullable=False)  # List of {chunk_hash, chunk_index, chunk_size}
    is_locked = Column(Boolean, default=False)  # Locked after approval
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    file_node = relationship("FileNode", back_populates="versions", 
                           foreign_keys=[file_node_id])
    author = relationship("User", back_populates="file_versions")
    parent_version = relationship("FileVersion", remote_side=[id])
    workflow_instances = relationship("WorkflowInstance", back_populates="file_version")

class Chunk(Base):
    __tablename__ = 'chunks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256
    chunk_size = Column(Integer, nullable=False)
    storage_key = Column(String(500), nullable=False)  # Object storage key
    ref_count = Column(Integer, default=1)  # Reference counting for GC
    created_at = Column(DateTime, default=datetime.utcnow)

class Workflow(Base):
    __tablename__ = 'workflows'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    nodes_config = Column(JSON, nullable=False)  # List of approval node configurations
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instances = relationship("WorkflowInstance", back_populates="workflow")

class WorkflowInstance(Base):
    __tablename__ = 'workflow_instances'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id'), nullable=False)
    file_version_id = Column(UUID(as_uuid=True), ForeignKey('file_versions.id'), nullable=False)
    status = Column(Enum('pending', 'approved', 'rejected', 'completed', 
                        name='workflow_status_enum'), nullable=False, default='pending')
    current_node_index = Column(Integer, default=0)
    approval_history = Column(JSON, default=list)  # List of approval records
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="instances")
    file_version = relationship("FileVersion", back_populates="workflow_instances")

class DigitalSeal(Base):
    __tablename__ = 'digital_seals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    seal_name = Column(String(255), nullable=False)
    seal_image_key = Column(String(500), nullable=False)  # Object storage key for seal image
    certificate_hash = Column(String(64), nullable=False)  # SHA-256 of CA certificate
    certificate_key = Column(String(500), nullable=False)  # Object storage key for certificate
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="digital_seals")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    project_memberships = relationship("ProjectMember", back_populates="user")
    file_versions = relationship("FileVersion", back_populates="author")
    digital_seals = relationship("DigitalSeal", back_populates="user")
```

### Database Indexes

```python
# Performance optimization indexes
Index('idx_file_nodes_repository_path', FileNode.repository_id, FileNode.path)
Index('idx_file_versions_file_node', FileVersion.file_node_id, FileVersion.version_number)
Index('idx_chunks_hash', Chunk.chunk_hash)
Index('idx_workflow_instances_status', WorkflowInstance.status, WorkflowInstance.current_node_index)
Index('idx_project_members_user', ProjectMember.user_id, ProjectMember.project_id)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas where properties can be consolidated:

1. **Tenant isolation properties (1.2, 1.3)**: These both test data isolation and can be combined into a single comprehensive property
2. **CRUD properties (2.1, 3.1)**: Basic creation operations can be generalized into entity creation properties
3. **Permission verification (2.4, 2.5)**: Both test permission enforcement and can be combined
4. **Version creation properties (3.5, 5.2, 12.4)**: All test that modifications create new versions - can be unified
5. **Conversion triggering (7.1, 8.1)**: Both test conversion task creation - can be generalized
6. **Status tracking (8.4, 9.3, 10.2)**: All test status query functionality - can be unified
7. **API error handling (7.4, 13.5, 15.4)**: All test HTTP error responses - can be combined

### Core Properties

**Property 1: Tenant data isolation**
*For any* two distinct tenants T1 and T2, and any data entity E created within T1's namespace, queries executed in T2's context should never return entity E
**Validates: Requirements 1.2, 1.3**

**Property 2: Tenant-user association**
*For any* authenticated user, the system context should contain exactly one tenant ID that matches the user's tenant_id field
**Validates: Requirements 1.4**

**Property 3: Entity creation within hierarchy**
*For any* valid parent entity (Tenant, Project, Repository) and child entity type, creating a child entity should result in the child being associated with the correct parent ID
**Validates: Requirements 2.1, 3.1**

**Property 4: Permission matrix initialization**
*For any* newly created project, the permission matrix should exist and contain at least one owner role assigned to the creator
**Validates: Requirements 2.2**

**Property 5: Role-based access control enforcement**
*For any* user U with role R attempting action A on resource S, access should be granted if and only if role R has permission for action A according to the permission matrix
**Validates: Requirements 2.3, 2.4, 2.5**

**Property 6: File system hierarchy integrity**
*For any* file node N with parent P, the path of N should start with the path of P, and traversing parent references from N should eventually reach the repository root
**Validates: Requirements 3.3**

**Property 7: File modification creates new version**
*For any* file node F, when a modification operation is performed, the system should create a new FileVersion V with version_number equal to the previous maximum version_number plus one
**Validates: Requirements 3.5, 5.2, 12.4**

**Property 8: Chunk deduplication**
*For any* two chunks C1 and C2 with identical content hashes, only one physical chunk should exist in object storage, and both references should point to the same storage key
**Validates: Requirements 4.4**

**Property 9: Chunk existence check accuracy**
*For any* set of chunk hashes H submitted to the check endpoint, the response should contain exactly those hashes that do not exist in the chunks table
**Validates: Requirements 4.2**

**Property 10: FileVersion chunk linkage completeness**
*For any* finalized FileVersion V, the chunk_refs field should contain references to all chunks required to reconstruct the file, and the sum of chunk sizes should equal file_size
**Validates: Requirements 4.5**

**Property 11: Version history completeness**
*For any* file node F with N modifications, the versions list should contain exactly N FileVersion records, ordered by version_number
**Validates: Requirements 5.1**

**Property 12: Commit hash uniqueness**
*For any* two distinct FileVersion records V1 and V2, their commit_hash values should be different
**Validates: Requirements 5.2**

**Property 13: Version metadata completeness**
*For any* FileVersion V, the fields author_id, created_at, and commit_message should all be non-null
**Validates: Requirements 5.3**

**Property 14: Historical version retrieval**
*For any* FileVersion V that was successfully created, querying by V's ID should return a record with identical field values
**Validates: Requirements 5.4**

**Property 15: Content-addressable storage key**
*For any* chunk C stored in object storage, the storage_key should be derivable from the chunk_hash (e.g., "objects/{hash[:2]}/{hash[2:4]}/{hash}")
**Validates: Requirements 6.3**

**Property 16: Storage backend failure handling**
*For any* storage operation that encounters a connection failure, the system should return an error response with status code 503 and a descriptive error message, without crashing
**Validates: Requirements 6.4**

**Property 17: Preview conversion task creation**
*For any* file version V with a supported CAD/BIM file extension, requesting a preview should create a Celery task with task_id and status "pending"
**Validates: Requirements 7.1, 8.1**

**Property 18: Preview caching idempotence**
*For any* file version V, requesting preview conversion twice should result in the second request returning cached data without creating a new conversion task
**Validates: Requirements 7.5**

**Property 19: Conversion error reporting**
*For any* conversion task that fails, querying the task status should return an error object containing a descriptive message about the failure cause
**Validates: Requirements 7.4**

**Property 20: Asynchronous task queuing**
*For any* operation that triggers an asynchronous task, the task should appear in the Celery queue within 1 second and be assigned a unique task_id
**Validates: Requirements 8.3, 9.2**

**Property 21: Task status query consistency**
*For any* task T with current state S, querying the task status by task_id should return state S
**Validates: Requirements 8.4, 9.3, 10.2**

**Property 22: Task failure retry capability**
*For any* failed task T, calling the retry endpoint should create a new task T' with the same parameters and status "pending"
**Validates: Requirements 9.4**

**Property 23: Workflow state machine progression**
*For any* workflow instance W at node N, approving node N should advance W to node N+1 if N+1 exists, or set status to "completed" if N is the final node
**Validates: Requirements 10.4, 10.5**

**Property 24: Approver notification triggering**
*For any* workflow instance W advancing to node N, the system should create a notification record for each approver designated in node N's configuration
**Validates: Requirements 10.3**

**Property 25: Digital seal positioning**
*For any* PDF document D and seal application at coordinates (x, y), the resulting PDF should contain the seal image with its top-left corner at position (x, y)
**Validates: Requirements 11.1**

**Property 26: Automatic seal application on approval**
*For any* workflow node approval where the approver has an active DigitalSeal, the system should apply that seal to the associated PDF document
**Validates: Requirements 11.2**

**Property 27: Cryptographic signature embedding**
*For any* signed PDF document D, extracting the signature should yield a valid cryptographic signature that can be verified using the stored certificate
**Validates: Requirements 11.3**

**Property 28: Certificate hash recording**
*For any* document signing operation, the system should store the SHA-256 hash of the CA certificate in the DigitalSeal record
**Validates: Requirements 11.4**

**Property 29: Approved version immutability**
*For any* FileVersion V with is_locked=true, any attempt to modify V or its associated file node should be rejected with a 403 Forbidden error
**Validates: Requirements 11.5**

**Property 30: Mount token time-limited validity**
*For any* mount token T generated with TTL of N seconds, validating T after N+1 seconds should return null/invalid
**Validates: Requirements 12.2**

**Property 31: WebDAV operation parity**
*For any* file operation O (create, read, update, delete) performed through WebDAV, the resulting file system state should be identical to performing O through the REST API
**Validates: Requirements 12.3**

**Property 32: Real-time synchronization**
*For any* file modification M performed through the WebDAV mount, querying the file through the REST API within 1 second should reflect modification M
**Validates: Requirements 12.5**

**Property 33: HTTP error response format**
*For any* API request that results in an error, the response should have an appropriate HTTP status code (4xx for client errors, 5xx for server errors) and a JSON body containing an error message
**Validates: Requirements 7.4, 13.5, 15.4**

**Property 34: Foreign key constraint enforcement**
*For any* entity E with a foreign key reference to entity P, attempting to delete P while E exists should be rejected by the database with a foreign key violation error
**Validates: Requirements 14.5**

**Property 35: JSON payload format**
*For any* API request with a request body or any API response with a response body, the content should be valid JSON parseable by a standard JSON parser
**Validates: Requirements 15.3**

**Property 36: Authentication requirement enforcement**
*For any* protected API endpoint, making a request without a valid authentication token should return a 401 Unauthorized response
**Validates: Requirements 15.5**

## Error Handling

### Error Categories

1. **Client Errors (4xx)**
   - 400 Bad Request: Invalid input data, malformed JSON
   - 401 Unauthorized: Missing or invalid authentication token
   - 403 Forbidden: Insufficient permissions, locked resource
   - 404 Not Found: Resource does not exist
   - 409 Conflict: Resource already exists, version conflict

2. **Server Errors (5xx)**
   - 500 Internal Server Error: Unexpected application error
   - 503 Service Unavailable: Storage backend unavailable, task queue full

### Error Response Format

All error responses follow a consistent JSON structure:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "File node with ID 'abc-123' does not exist",
    "details": {
      "resource_type": "FileNode",
      "resource_id": "abc-123"
    }
  }
}
```

### Error Handling Strategies

1. **Database Errors**: Wrap in try-except, rollback transaction, return 500
2. **Storage Backend Errors**: Retry with exponential backoff (3 attempts), return 503 if all fail
3. **Validation Errors**: Return 400 with specific field errors
4. **Permission Errors**: Return 403 with resource information
5. **Task Queue Errors**: Log error, return 500, allow manual retry

## Testing Strategy

### Dual Testing Approach

The system will be validated using both unit tests and property-based tests:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs
- Both approaches are complementary and necessary for comprehensive coverage

### Unit Testing Focus

Unit tests should focus on:
- Specific examples that demonstrate correct behavior (e.g., creating a tenant with specific data)
- Integration points between components (e.g., workflow engine triggering seal application)
- Edge cases and error conditions (e.g., empty file upload, invalid coordinates)
- Database constraint violations
- API endpoint contract validation

### Property-Based Testing Configuration

**Library**: Hypothesis (Python)

**Configuration**:
- Minimum 100 iterations per property test
- Each property test must reference its design document property
- Tag format: `# Feature: aec-collaboration-platform, Property {number}: {property_text}`

**Example Property Test Structure**:

```python
from hypothesis import given, strategies as st
import pytest

@given(
    tenant_name=st.text(min_size=1, max_size=255),
    tenant_type=st.sampled_from(['design', 'construction', 'owner', 'supervision'])
)
@pytest.mark.property_test
def test_property_1_tenant_data_isolation(tenant_name, tenant_type):
    """
    Feature: aec-collaboration-platform, Property 1: Tenant data isolation
    
    For any two distinct tenants T1 and T2, and any data entity E created 
    within T1's namespace, queries executed in T2's context should never 
    return entity E
    """
    # Test implementation
    pass
```

### Test Coverage Goals

- Unit test coverage: >80% of code lines
- Property test coverage: All 36 correctness properties implemented
- Integration test coverage: All API endpoints
- End-to-end test coverage: Critical user workflows (upload, preview, approval)

### Testing Infrastructure

- **Test Database**: Separate PostgreSQL instance for testing
- **Test Storage**: MinIO instance in Docker for local testing
- **Test Queue**: Redis + Celery workers for async task testing
- **Fixtures**: Factory pattern for generating test data
- **Mocking**: Minimal mocking - prefer real implementations where possible

