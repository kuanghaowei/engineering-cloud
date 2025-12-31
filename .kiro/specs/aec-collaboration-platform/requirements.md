# Requirements Document

## Introduction

本文档定义了跨单位工程协同平台的功能需求。该平台采用"Meta-Data + Object Store"架构，支持多租户、大文件版本控制、BIM/CAD图纸预览、数字印章审批等核心功能，为设计、施工、建设、监理等单位提供协同工作环境。

## Glossary

- **System**: 跨单位工程协同平台
- **Tenant**: 租户，代表一个独立的组织单位（设计院、施工单位、建设单位、监理单位等）
- **Project**: 项目，顶级容器，包含多个仓库和成员权限
- **Repository**: 仓库，对应一个专业领域（建筑、结构、机电等）
- **FileNode**: 文件节点，记录文件的元数据信息
- **FileVersion**: 文件版本，指向具体的内容哈希
- **Chunk**: 文件分块，用于大文件的增量传输
- **CAS**: Content-Addressable Storage，基于内容哈希的存储方式
- **Workflow**: 审批流程，管理文件版本的审批状态
- **DigitalSeal**: 数字印章，用于电子签章和法律存证
- **VFS**: Virtual File System，虚拟文件系统
- **Client**: 客户端应用程序
- **CloudPC**: 工一云电脑，云端工作环境

## Requirements

### Requirement 1: 多租户管理

**User Story:** 作为系统管理员，我希望能够管理多个租户组织，以便不同单位可以在同一平台上独立工作。

#### Acceptance Criteria

1. THE System SHALL support creating multiple Tenant entities with unique identifiers
2. WHEN a Tenant is created, THE System SHALL assign it an isolated data namespace
3. THE System SHALL prevent cross-Tenant data access unless explicitly authorized
4. WHEN a user authenticates, THE System SHALL associate the user with their Tenant context
5. THE System SHALL support Tenant types including design, construction, owner, and supervision units

### Requirement 2: 项目与权限管理

**User Story:** 作为项目管理员，我希望能够创建项目并管理成员权限，以便控制谁可以访问和修改项目资源。

#### Acceptance Criteria

1. THE System SHALL allow creating Project entities within a Tenant
2. WHEN a Project is created, THE System SHALL initialize a permission matrix for members
3. THE System SHALL support role-based access control with roles including owner, editor, and viewer
4. WHEN a user attempts to access a Project resource, THE System SHALL verify the user's permissions
5. THE System SHALL allow Project administrators to add, remove, and modify member permissions

### Requirement 3: 仓库与文件系统

**User Story:** 作为项目成员，我希望能够在专业仓库中组织文件，以便按照专业领域管理工程文档。

#### Acceptance Criteria

1. THE System SHALL allow creating Repository entities within a Project
2. WHEN a Repository is created, THE System SHALL initialize a file system structure
3. THE System SHALL maintain FileNode entities to represent file and folder hierarchy
4. THE System SHALL support standard file operations including create, read, update, and delete
5. WHEN a file is modified, THE System SHALL create a new FileVersion record

### Requirement 4: 大文件分块存储

**User Story:** 作为用户，我希望能够高效上传大型工程文件，以便节省带宽和时间。

#### Acceptance Criteria

1. WHEN a Client uploads a file, THE Client SHALL compute content hashes for file chunks
2. THE System SHALL provide an API endpoint to check which Chunks already exist on the server
3. WHEN the Client receives the check response, THE Client SHALL upload only missing Chunks
4. THE System SHALL store Chunks using CAS in the object storage backend
5. WHEN all Chunks are uploaded, THE System SHALL create a FileVersion record linking to the Chunks

### Requirement 5: 版本控制

**User Story:** 作为用户，我希望能够追踪文件的历史版本，以便查看变更记录和回退到之前的版本。

#### Acceptance Criteria

1. THE System SHALL maintain a version history for each FileNode
2. WHEN a file is modified, THE System SHALL create a new FileVersion with a unique commit identifier
3. THE System SHALL record metadata including author, timestamp, and commit message for each version
4. THE System SHALL support retrieving any historical FileVersion
5. THE System SHALL support fast-forward merge operations between versions

### Requirement 6: 对象存储集成

**User Story:** 作为系统架构师，我希望系统能够使用MinIO或OSS作为存储后端，以便实现可扩展的文件存储。

#### Acceptance Criteria

1. THE System SHALL support MinIO as an object storage backend
2. THE System SHALL support Alibaba Cloud OSS as an object storage backend
3. WHEN storing a Chunk, THE System SHALL use the content hash as the object key
4. THE System SHALL handle storage backend connection failures gracefully
5. THE System SHALL support configuring storage backend credentials through environment variables

### Requirement 7: 2D CAD图纸预览

**User Story:** 作为用户，我希望能够在浏览器中预览CAD图纸，以便无需安装专业软件即可查看设计文件。

#### Acceptance Criteria

1. WHEN a user requests preview for a DWG file, THE System SHALL convert it to a web-compatible format
2. THE System SHALL support converting DWG files to SVF or PDF format
3. THE System SHALL provide an API endpoint to retrieve the converted preview
4. WHEN conversion fails, THE System SHALL return a descriptive error message
5. THE System SHALL cache converted previews to avoid redundant processing

### Requirement 8: 3D BIM模型预览

**User Story:** 作为用户，我希望能够在浏览器中查看3D BIM模型，以便进行可视化审查和协同。

#### Acceptance Criteria

1. WHEN a user requests preview for a RVT or IFC file, THE System SHALL convert it to a web-compatible 3D format
2. THE System SHALL support converting BIM files to glTF or 3D Tiles format
3. THE System SHALL use asynchronous task processing for BIM conversion
4. THE System SHALL provide status updates for long-running conversion tasks
5. WHEN conversion completes, THE System SHALL store the converted model for streaming

### Requirement 9: 异步任务处理

**User Story:** 作为系统架构师，我希望使用任务队列处理耗时操作，以便保持API响应速度和系统可扩展性。

#### Acceptance Criteria

1. THE System SHALL use Celery for asynchronous task processing
2. THE System SHALL queue file conversion tasks to Celery workers
3. THE System SHALL support querying task status by task identifier
4. WHEN a task fails, THE System SHALL record the error and allow retry
5. THE System SHALL support configuring the number of concurrent workers

### Requirement 10: 审批流程引擎

**User Story:** 作为项目管理员，我希望能够定义审批流程，以便控制文件版本的发布和归档。

#### Acceptance Criteria

1. THE System SHALL allow creating Workflow entities with multiple approval nodes
2. WHEN a FileVersion enters a Workflow, THE System SHALL track its approval status
3. THE System SHALL notify designated approvers when their action is required
4. WHEN an approver approves a node, THE System SHALL advance the FileVersion to the next node
5. WHEN all nodes are approved, THE System SHALL mark the FileVersion as approved

### Requirement 11: 数字印章与电子签章

**User Story:** 作为审批人，我希望能够在PDF文档上添加电子签章，以便提供法律效力的审批证明。

#### Acceptance Criteria

1. THE System SHALL support inserting DigitalSeal images into PDF documents at specified coordinates
2. WHEN a Workflow node is approved, THE System SHALL apply the approver's DigitalSeal to the document
3. THE System SHALL embed cryptographic signatures in the PDF using CA certificates
4. THE System SHALL record the certificate hash for legal evidence
5. WHEN a FileVersion is fully approved, THE System SHALL lock it as read-only archived

### Requirement 12: 云电脑文件系统挂载

**User Story:** 作为用户，我希望能够在工一云电脑中直接访问平台文件，以便使用云端软件编辑文件。

#### Acceptance Criteria

1. THE System SHALL provide a VFS or WebDAV interface for file access
2. WHEN CloudPC requests mount credentials, THE System SHALL generate time-limited access tokens
3. THE System SHALL support standard file system operations through the mount interface
4. WHEN a file is modified through the mount, THE System SHALL create a new FileVersion
5. THE System SHALL synchronize changes between the mount and the platform in real-time

### Requirement 13: 增量同步协议

**User Story:** 作为客户端开发者，我希望有清晰的增量同步API，以便实现高效的文件上传和下载。

#### Acceptance Criteria

1. THE System SHALL provide a POST endpoint for initializing chunked uploads
2. THE System SHALL provide a GET endpoint for checking which Chunks exist on the server
3. THE System SHALL provide a POST endpoint for uploading individual Chunks
4. THE System SHALL provide a POST endpoint for finalizing uploads and creating FileVersion records
5. THE System SHALL return appropriate HTTP status codes and error messages for all operations

### Requirement 14: 数据库模型持久化

**User Story:** 作为系统架构师，我希望使用SQLAlchemy管理数据模型，以便实现可维护的数据访问层。

#### Acceptance Criteria

1. THE System SHALL use SQLAlchemy ORM for database operations
2. THE System SHALL define models for Tenant, Project, Repository, FileNode, FileVersion, Workflow, and DigitalSeal
3. THE System SHALL support PostgreSQL as the primary database backend
4. THE System SHALL use database migrations for schema changes
5. THE System SHALL enforce referential integrity through foreign key constraints

### Requirement 15: API接口规范

**User Story:** 作为API使用者，我希望有清晰的接口文档，以便正确调用平台功能。

#### Acceptance Criteria

1. THE System SHALL expose RESTful API endpoints with versioned paths (e.g., /v1/)
2. THE System SHALL provide OpenAPI/Swagger documentation for all endpoints
3. THE System SHALL use JSON for request and response payloads
4. THE System SHALL implement proper HTTP status codes for success and error cases
5. THE System SHALL require authentication tokens for protected endpoints
