
# AWS Migration Documentation: SAT Decisions RAG System

## 1. Project Overview

The SAT Decisions RAG system analyzes State Administrative Tribunal legal decisions using AI and semantic search. This document outlines AWS infrastructure requirements.

## 2. Current Architecture Components

- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: React 19.0.0
- **Databases**:
  - PostgreSQL with pgvector extension (for vector embeddings)
  - Neo4j Aura (for case relationships/network visualization)
- **Data Pipeline**: Scrapy-based scraper, data processing scripts
- **AI Components**: LangChain 0.0.335, embedding models, LLMs

## 3. AWS Services Required

### 3.1 Compute Resources

- **Backend API**: 
  - AWS Elastic Container Service (ECS) with Fargate
  - 2 vCPU minimum, 4 GB RAM minimum per container
  - Auto-scaling based on CPU (target 70%)
  - Load balancer with HTTPS

- **Frontend**:
  - Amazon S3 for static hosting
  - CloudFront for content delivery
  - Route 53 for domain management

- **Scraper/Data Processing**:
  - AWS Lambda for scheduled scraping tasks
  - AWS Batch for larger processing jobs

### 3.2 Database Requirements

- **PostgreSQL**:
  - Amazon RDS for PostgreSQL (version 14+)
  - Instance class: db.r6g.large minimum (vector operations are memory-intensive)
  - Storage: 100GB minimum with auto-scaling
  - **Critical**: PostgreSQL must support pgvector extension
  - Multi-AZ deployment for high availability

- **Neo4j**:
  - Either:
    - Option 1: Neo4j Aura (existing cloud service) with VPC peering to AWS
    - Option 2: Self-hosted Neo4j on EC2 (t3.medium minimum)
    - Option 3: Amazon Neptune

### 3.3 Storage & Caching

- **Object Storage**:
  - S3 bucket for raw and processed case documents
  - S3 bucket for frontend assets

- **Caching**:
  - ElastiCache (Redis) for API responses and embedding lookups
  - 2GB cache minimum

### 3.4 Networking & Security

- **VPC Configuration**:
  - Private subnets for databases and application services
  - Public subnets for load balancers only
  - NAT Gateway for outbound traffic

- **Security Groups**:
  - Backend: Inbound 8000 from load balancer only
  - RDS: PostgreSQL port accessible only from backend services
  - Neo4j: Bolt/HTTP ports accessible only from backend services

### 3.5 Additional AWS Services

- **Authentication/Authorization**:
  - Amazon Cognito for user management

- **Monitoring & Logging**:
  - CloudWatch for logs and metrics
  - X-Ray for distributed tracing

- **CI/CD Pipeline**:
  - CodePipeline or GitHub Actions with deployment to ECS

## 4. Environment Variables & Configuration

The following environment variables must be set in ECS task definitions:

```
# Database
DATABASE_URL=postgresql://user:password@postgres-endpoint:5432/satdata

# Neo4j
NEO4J_URI=neo4j+s://[endpoint]
NEO4J_USER=[user]
NEO4J_PASSWORD=[password]

# Embedding Configuration
EMBEDDING_MODEL=e5-base-v2
ENABLE_STREAMING=true

# LLM API Keys (if applicable)
OPENAI_API_KEY=[key]
```

## 5. Deployment Strategy

1. **Database Migration**:
   - Create RDS instance with pgvector extension
   - Migrate data from existing PostgreSQL
   - Configure Neo4j Aura VPC peering or deploy EC2 Neo4j

2. **Backend Deployment**:
   - Create ECR repository
   - Build and push Docker images
   - Configure ECS service with appropriate environment variables

3. **Frontend Deployment**:
   - Build React application
   - Upload to S3
   - Configure CloudFront distribution

4. **Configure Scraper/Data Processing**:
   - Set up Lambda functions for scheduled scraping
   - Configure AWS Batch for data processing tasks

## 6. Cost Considerations

- **Estimated monthly cost**: $500-$1,500 depending on traffic
- **Highest cost components**:
  - RDS PostgreSQL instance (memory-optimized for vector operations)
  - ECS Fargate containers (especially with AI workloads)
  - Neo4j hosting (if self-hosted)

## 7. Security Requirements

- **Data Encryption**:
  - At-rest encryption for all databases and S3 buckets
  - In-transit encryption (TLS) for all connections

- **Access Control**:
  - IAM roles with least privilege principle
  - No direct access to databases from public internet

- **Compliance**:
  - Regular security scanning of deployed infrastructure
  - Backup retention policy according to data requirements

## 8. Migration Timeline Recommendation

- **Phase 1 (Week 1-2)**: Infrastructure setup and database migration
- **Phase 2 (Week 3)**: Backend deployment and testing
- **Phase 3 (Week 4)**: Frontend deployment and end-to-end testing
- **Phase 4 (Week 5)**: Scraper/data pipeline setup
- **Phase 5 (Week 6)**: Monitoring, optimization, and final cutover

## 9. Questions for Cloud Team

1. Do you have existing AWS infrastructure that this should integrate with?
2. Are there specific AWS regions required for compliance/performance?
3. Is there a preferred CI/CD pipeline already established?
4. Are there existing backup/restore procedures to follow?

Please review this document and provide any additional requirements before proceeding with infrastructure provisioning.
