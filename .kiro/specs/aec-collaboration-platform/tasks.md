

# Implementation Plan: AEC Collaboration Platform

## Overview

本实施计划将跨单位工程协同平台分解为可执行的开发任务。系统采用FastAPI + SQLAlchemy + PostgreSQL + MinIO架构,支持多租户、大文件版本控制、BIM/CAD预览、审批流程等核心功能。

实施顺序遵循从基础设施到核心功能再到高级特性的原则,确保每个阶段都能产生可测试的增量价值。

## Tasks

- [x] 1. 项目骨架与基础设施搭建
  - 创建FastAPI项目结构
  - 配置PostgreSQL数据库连接
  - 配置环境变量管理(python-dotenv)
  - 设置日志系统
  - 创建Docker Compose配置(PostgreSQL + Redis + MinIO)
  - _Requirements: 14.3, 6.1_

- [ ]* 1.1 编写项目初始化单元测试
  - 测试数据库连接
  - 测试环境变量加载
  - _Requirements: 14.3_

- [ ] 2. 数据库模型与迁移
  - [ ] 2.1 定义SQLAlchemy基础模型
    - 创建Base类和数据库会话管理
    - 定义Tenant模型
    - 定义User模型
    - 定义Project模型
    - 定义ProjectMember模型
    - _Requirements: 14.2, 1.1, 2.1_

  - [ ] 2.2 定义文件系统相关模型
    - 定义Repository模型
    - 定义FileNode模型
    - 定义FileVersion模型
    - 定义Chunk模型
    - 添加必要的索引
    - _Requirements: 14.2, 3.1, 3.3, 4.4_

  - [ ] 2.3 定义工作流与签章模型
    - 定义Workflow模型
    - 定义WorkflowInstance模型
    - 定义DigitalSeal模型
    - 添加外键约束
    - _Requirements: 14.2, 10.1, 11.1, 14.5_

  - [ ] 2.4 配置Alembic数据库迁移
    - 初始化Alembic
    - 生成初始迁移脚本
    - 测试迁移执行
    - _Requirements: 14.4_

  - [ ]* 2.5 编写属性测试:外键约束强制执行
    - **Property 34: Foreign key constraint enforcement**
    - **Validates: Requirements 14.5**
    - 生成随机实体关系,尝试删除被引用的父实体,验证数据库拒绝操作
    - _Requirements: 14.5_

- [ ] 3. 认证与租户隔离
  - [ ] 3.1 实现JWT认证中间件
    - 创建JWT token生成和验证函数
    - 实现认证依赖注入
    - 创建用户注册和登录端点
    - _Requirements: 15.5_

  - [ ] 3.2 实现租户上下文中间件
    - 创建TenantContext类
    - 实现请求级租户注入
    - 配置SQLAlchemy查询过滤器
    - _Requirements: 1.2, 1.4_

  - [ ]* 3.3 编写属性测试:租户数据隔离
    - **Property 1: Tenant data isolation**
    - **Validates: Requirements 1.2, 1.3**
    - 生成两个随机租户,在T1中创建数据,在T2上下文查询,验证无法访问T1数据
    - _Requirements: 1.2, 1.3_

  - [ ]* 3.4 编写属性测试:租户-用户关联
    - **Property 2: Tenant-user association**
    - **Validates: Requirements 1.4**
    - 生成随机用户,认证后验证上下文包含正确的tenant_id
    - _Requirements: 1.4_

  - [ ]* 3.5 编写属性测试:认证要求强制执行
    - **Property 36: Authentication requirement enforcement**
    - **Validates: Requirements 15.5**
    - 对受保护端点发起无token请求,验证返回401
    - _Requirements: 15.5_

- [ ] 4. 租户与项目管理
  - [ ] 4.1 实现租户管理服务
    - 创建TenantService类
    - 实现CRUD操作
    - 创建租户管理API端点(/v1/tenants)
    - _Requirements: 1.1, 1.5_

  - [ ] 4.2 实现项目管理服务
    - 创建ProjectService类
    - 实现项目创建和查询
    - 创建项目API端点(/v1/projects)
    - _Requirements: 2.1, 2.2_

  - [ ] 4.3 实现权限管理服务
    - 创建PermissionService类
    - 实现RBAC权限检查
    - 实现成员管理功能
    - 创建权限API端点(/v1/projects/{id}/members)
    - _Requirements: 2.3, 2.4, 2.5_

  - [ ]* 4.4 编写属性测试:实体创建层级关系
    - **Property 3: Entity creation within hierarchy**
    - **Validates: Requirements 2.1, 3.1**
    - 生成随机父实体,创建子实体,验证parent_id正确关联
    - _Requirements: 2.1, 3.1_

  - [ ]* 4.5 编写属性测试:权限矩阵初始化
    - **Property 4: Permission matrix initialization**
    - **Validates: Requirements 2.2**
    - 创建随机项目,验证创建者被分配owner角色
    - _Requirements: 2.2_

  - [ ]* 4.6 编写属性测试:RBAC强制执行
    - **Property 5: Role-based access control enforcement**
    - **Validates: Requirements 2.3, 2.4, 2.5**
    - 生成随机用户和角色,尝试各种操作,验证权限检查正确
    - _Requirements: 2.3, 2.4, 2.5_

- [ ] 5. 对象存储适配器
  - [ ] 5.1 实现存储后端抽象接口
    - 创建StorageBackend抽象基类
    - 定义put_object, get_object, delete_object, object_exists方法
    - _Requirements: 6.1, 6.2_

  - [ ] 5.2 实现MinIO存储后端
    - 创建MinIOBackend类
    - 实现所有存储操作
    - 配置连接池和重试逻辑
    - _Requirements: 6.1, 6.3_

  - [ ] 5.3 实现OSS存储后端
    - 创建OSSBackend类
    - 实现所有存储操作
    - 配置阿里云SDK
    - _Requirements: 6.2, 6.3_

  - [ ]* 5.4 编写属性测试:内容寻址存储键
    - **Property 15: Content-addressable storage key**
    - **Validates: Requirements 6.3**
    - 生成随机chunk,存储后验证storage_key从chunk_hash派生
    - _Requirements: 6.3_

  - [ ]* 5.5 编写属性测试:存储后端故障处理
    - **Property 16: Storage backend failure handling**
    - **Validates: Requirements 6.4**
    - 模拟连接失败,验证返回503错误且不崩溃
    - _Requirements: 6.4_

- [ ] 6. 文件系统与仓库管理
  - [ ] 6.1 实现仓库管理服务
    - 创建RepositoryService类
    - 实现仓库CRUD操作
    - 创建仓库API端点(/v1/repositories)
    - _Requirements: 3.1, 3.2_

  - [ ] 6.2 实现文件系统服务
    - 创建FileSystemService类
    - 实现目录和文件节点创建
    - 实现路径解析和验证
    - 实现节点移动和删除
    - 创建文件系统API端点(/v1/files)
    - _Requirements: 3.3, 3.4_

  - [ ]* 6.3 编写属性测试:文件系统层级完整性
    - **Property 6: File system hierarchy integrity**
    - **Validates: Requirements 3.3**
    - 生成随机文件树,验证所有节点路径正确且可追溯到根
    - _Requirements: 3.3_

- [ ] 7. 分块上传与版本控制
  - [ ] 7.1 实现分块管理器
    - 创建ChunkManager类
    - 实现chunk存在性检查
    - 实现chunk上传和去重
    - 实现chunk检索
    - _Requirements: 4.2, 4.4_

  - [ ] 7.2 实现上传会话管理
    - 创建UploadSession模型
    - 实现上传初始化
    - 实现上传进度跟踪
    - 实现上传完成处理
    - _Requirements: 13.1, 13.3, 13.4_

  - [ ] 7.3 实现版本控制服务
    - 创建VersionService类
    - 实现版本创建和提交
    - 实现版本历史查询
    - 实现版本检出
    - 创建版本API端点(/v1/versions)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 7.4 创建分块上传API端点
    - POST /v1/upload/init - 初始化上传
    - POST /v1/upload/check - 检查chunk存在性
    - PUT /v1/upload/chunk - 上传单个chunk
    - POST /v1/upload/finalize - 完成上传
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 7.5 编写属性测试:文件修改创建新版本
    - **Property 7: File modification creates new version**
    - **Validates: Requirements 3.5, 5.2, 12.4**
    - 修改随机文件,验证创建新版本且version_number递增
    - _Requirements: 3.5, 5.2, 12.4_

  - [ ]* 7.6 编写属性测试:chunk去重
    - **Property 8: Chunk deduplication**
    - **Validates: Requirements 4.4**
    - 上传相同内容的chunk两次,验证只存储一份
    - _Requirements: 4.4_

  - [ ]* 7.7 编写属性测试:chunk存在性检查准确性
    - **Property 9: Chunk existence check accuracy**
    - **Validates: Requirements 4.2**
    - 提交随机chunk哈希集合,验证响应准确标识缺失的chunk
    - _Requirements: 4.2_

  - [ ]* 7.8 编写属性测试:FileVersion chunk链接完整性
    - **Property 10: FileVersion chunk linkage completeness**
    - **Validates: Requirements 4.5**
    - 完成上传后,验证chunk_refs包含所有chunk且大小总和正确
    - _Requirements: 4.5_

  - [ ]* 7.9 编写属性测试:版本历史完整性
    - **Property 11: Version history completeness**
    - **Validates: Requirements 5.1**
    - 对文件进行N次修改,验证版本列表包含N个记录
    - _Requirements: 5.1_

  - [ ]* 7.10 编写属性测试:提交哈希唯一性
    - **Property 12: Commit hash uniqueness**
    - **Validates: Requirements 5.2**
    - 创建多个版本,验证所有commit_hash互不相同
    - _Requirements: 5.2_

  - [ ]* 7.11 编写属性测试:版本元数据完整性
    - **Property 13: Version metadata completeness**
    - **Validates: Requirements 5.3**
    - 创建随机版本,验证author_id、created_at、commit_message非空
    - _Requirements: 5.3_

  - [ ]* 7.12 编写属性测试:历史版本检索
    - **Property 14: Historical version retrieval**
    - **Validates: Requirements 5.4**
    - 创建版本后通过ID查询,验证返回相同数据
    - _Requirements: 5.4_

- [ ] 8. Checkpoint - 核心功能验证
  - 确保所有测试通过
  - 验证文件上传和版本控制流程
  - 如有问题请咨询用户

- [ ] 9. Celery异步任务系统
  - [ ] 9.1 配置Celery应用
    - 创建Celery app配置
    - 配置Redis作为broker和backend
    - 配置任务路由和队列
    - _Requirements: 9.1, 9.2_

  - [ ] 9.2 实现任务状态管理
    - 创建TaskStatusService类
    - 实现任务状态查询
    - 实现任务重试逻辑
    - 创建任务状态API端点(/v1/tasks/{id})
    - _Requirements: 9.3, 9.4_

  - [ ]* 9.3 编写属性测试:异步任务排队
    - **Property 20: Asynchronous task queuing**
    - **Validates: Requirements 8.3, 9.2**
    - 触发异步操作,验证任务在1秒内出现在队列中
    - _Requirements: 8.3, 9.2_

  - [ ]* 9.4 编写属性测试:任务状态查询一致性
    - **Property 21: Task status query consistency**
    - **Validates: Requirements 8.4, 9.3, 10.2**
    - 创建任务并设置状态,查询验证状态一致
    - _Requirements: 8.4, 9.3, 10.2_

  - [ ]* 9.5 编写属性测试:任务失败重试能力
    - **Property 22: Task failure retry capability**
    - **Validates: Requirements 9.4**
    - 使任务失败,调用重试,验证创建新任务
    - _Requirements: 9.4_

- [ ] 10. 文件转换系统
  - [ ] 10.1 实现转换服务基础设施
    - 创建ConversionService类
    - 实现转换任务调度
    - 实现预览缓存管理
    - 创建转换API端点(/v1/preview/{file_id})
    - _Requirements: 7.3, 7.5_

  - [ ] 10.2 实现CAD文件转换任务
    - 创建convert_cad_file Celery任务
    - 集成Autodesk Forge SDK或ODA转换器
    - 实现DWG到SVF/PDF转换
    - 处理转换错误和超时
    - _Requirements: 7.1, 7.2, 7.4_

  - [ ] 10.3 实现BIM文件转换任务
    - 创建convert_bim_file Celery任务
    - 集成xeokit或IfcOpenShell
    - 实现RVT/IFC到glTF转换
    - 处理大模型分块
    - _Requirements: 8.1, 8.2, 8.5_

  - [ ]* 10.4 编写属性测试:预览转换任务创建
    - **Property 17: Preview conversion task creation**
    - **Validates: Requirements 7.1, 8.1**
    - 请求支持格式的预览,验证创建Celery任务
    - _Requirements: 7.1, 8.1_

  - [ ]* 10.5 编写属性测试:预览缓存幂等性
    - **Property 18: Preview caching idempotence**
    - **Validates: Requirements 7.5**
    - 请求预览两次,验证第二次使用缓存
    - _Requirements: 7.5_

  - [ ]* 10.6 编写属性测试:转换错误报告
    - **Property 19: Conversion error reporting**
    - **Validates: Requirements 7.4**
    - 触发转换失败,验证状态查询返回描述性错误
    - _Requirements: 7.4_

- [ ] 11. 工作流引擎
  - [ ] 11.1 实现工作流服务
    - 创建WorkflowService类
    - 实现工作流定义CRUD
    - 实现工作流实例管理
    - 创建工作流API端点(/v1/workflows)
    - _Requirements: 10.1, 10.2_

  - [ ] 11.2 实现工作流执行引擎
    - 创建WorkflowExecutor类
    - 实现状态机逻辑
    - 实现审批和拒绝操作
    - 实现通知触发
    - 创建审批API端点(/v1/workflows/{id}/approve)
    - _Requirements: 10.3, 10.4, 10.5_

  - [ ]* 11.3 编写属性测试:工作流状态机推进
    - **Property 23: Workflow state machine progression**
    - **Validates: Requirements 10.4, 10.5**
    - 创建工作流并逐节点审批,验证状态正确推进
    - _Requirements: 10.4, 10.5_

  - [ ]* 11.4 编写属性测试:审批人通知触发
    - **Property 24: Approver notification triggering**
    - **Validates: Requirements 10.3**
    - 推进工作流,验证为下一节点审批人创建通知
    - _Requirements: 10.3_

- [ ] 12. 数字签章系统
  - [ ] 12.1 实现签章管理服务
    - 创建DigitalSealService类
    - 实现签章CRUD操作
    - 实现证书管理
    - 创建签章API端点(/v1/seals)
    - _Requirements: 11.1, 11.4_

  - [ ] 12.2 实现PDF签名功能
    - 创建PDFSigner类
    - 集成PyMuPDF进行PDF操作
    - 实现签章图像插入
    - 实现加密签名嵌入
    - 实现签名验证
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ] 12.3 集成工作流与签章
    - 在审批操作中触发签章应用
    - 实现版本锁定逻辑
    - _Requirements: 11.2, 11.5_

  - [ ]* 12.4 编写属性测试:数字签章定位
    - **Property 25: Digital seal positioning**
    - **Validates: Requirements 11.1**
    - 在随机坐标应用签章,验证PDF中位置正确
    - _Requirements: 11.1_

  - [ ]* 12.5 编写属性测试:审批时自动应用签章
    - **Property 26: Automatic seal application on approval**
    - **Validates: Requirements 11.2**
    - 审批节点,验证审批人签章自动应用到文档
    - _Requirements: 11.2_

  - [ ]* 12.6 编写属性测试:加密签名嵌入
    - **Property 27: Cryptographic signature embedding**
    - **Validates: Requirements 11.3**
    - 签名PDF,提取并验证签名有效
    - _Requirements: 11.3_

  - [ ]* 12.7 编写属性测试:证书哈希记录
    - **Property 28: Certificate hash recording**
    - **Validates: Requirements 11.4**
    - 签名文档,验证证书哈希存储在DigitalSeal记录中
    - _Requirements: 11.4_

  - [ ]* 12.8 编写属性测试:已审批版本不可变性
    - **Property 29: Approved version immutability**
    - **Validates: Requirements 11.5**
    - 完全审批版本后,尝试修改,验证返回403
    - _Requirements: 11.5_

- [ ] 13. Checkpoint - 高级功能验证
  - 确保所有测试通过
  - 验证完整的审批流程
  - 测试文件转换和签章功能
  - 如有问题请咨询用户

- [ ] 14. WebDAV/VFS挂载接口
  - [ ] 14.1 实现挂载凭证管理
    - 创建MountTokenManager类
    - 实现时间限制token生成
    - 实现token验证
    - 创建挂载凭证API端点(/v1/mount/credentials)
    - _Requirements: 12.2_

  - [ ] 14.2 实现WebDAV协议处理器
    - 创建WebDAVHandler类
    - 实现PROPFIND方法(列出目录)
    - 实现GET方法(下载文件)
    - 实现PUT方法(上传文件)
    - 实现DELETE方法(删除文件)
    - 配置WebDAV路由(/webdav/*)
    - _Requirements: 12.1, 12.3_

  - [ ] 14.3 集成WebDAV与版本控制
    - 在PUT操作中创建新版本
    - 实现实时同步逻辑
    - _Requirements: 12.4, 12.5_

  - [ ]* 14.4 编写属性测试:挂载token时间限制有效性
    - **Property 30: Mount token time-limited validity**
    - **Validates: Requirements 12.2**
    - 生成TTL为N秒的token,N+1秒后验证,确认无效
    - _Requirements: 12.2_

  - [ ]* 14.5 编写属性测试:WebDAV操作一致性
    - **Property 31: WebDAV operation parity**
    - **Validates: Requirements 12.3**
    - 通过WebDAV执行操作,验证与REST API结果一致
    - _Requirements: 12.3_

  - [ ]* 14.6 编写属性测试:实时同步
    - **Property 32: Real-time synchronization**
    - **Validates: Requirements 12.5**
    - 通过WebDAV修改文件,1秒内通过REST API查询,验证变更可见
    - _Requirements: 12.5_

- [ ] 15. API文档与错误处理
  - [ ] 15.1 配置OpenAPI文档生成
    - 配置FastAPI自动文档
    - 添加API描述和示例
    - 配置Swagger UI和ReDoc
    - _Requirements: 15.2_

  - [ ] 15.2 实现统一错误处理
    - 创建全局异常处理器
    - 实现标准错误响应格式
    - 配置HTTP状态码映射
    - _Requirements: 13.5, 15.4_

  - [ ]* 15.3 编写属性测试:HTTP错误响应格式
    - **Property 33: HTTP error response format**
    - **Validates: Requirements 7.4, 13.5, 15.4**
    - 触发各种错误,验证状态码和JSON格式正确
    - _Requirements: 7.4, 13.5, 15.4_

  - [ ]* 15.4 编写属性测试:JSON负载格式
    - **Property 35: JSON payload format**
    - **Validates: Requirements 15.3**
    - 对所有API端点发送请求,验证响应为有效JSON
    - _Requirements: 15.3_

- [ ] 16. 集成测试与文档
  - [ ]* 16.1 编写端到端集成测试
    - 测试完整的文件上传流程
    - 测试完整的审批流程
    - 测试WebDAV挂载流程
    - _Requirements: All_

  - [ ]* 16.2 编写API使用文档
    - 创建快速开始指南
    - 编写API调用示例
    - 文档化常见用例
    - _Requirements: 15.2_

- [ ] 17. 最终Checkpoint
  - 运行完整测试套件
  - 验证所有36个正确性属性
  - 检查代码覆盖率
  - 准备部署配置
  - 如有问题请咨询用户

## Notes

- 标记`*`的任务为可选任务,可跳过以加快MVP开发
- 每个任务都引用了具体的需求编号以便追溯
- Checkpoint任务确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
- 使用Hypothesis库进行属性测试,每个测试至少100次迭代
