# Multi-Tenant Gym Management Boilerplate Refactoring Plan

## Overview
This plan outlines the steps to refactor the existing gym management application into a reusable multi-tenant boilerplate. The chosen multi-tenancy strategy is **Shared Database, Shared Schema** with tenant identification via subdomain.

## Completed Steps

1. **Define Multi-Tenancy Strategy** ✓
   - Chosen approach: Shared Database, Shared Schema
   - Each tenant's data is isolated by a `tenant_id` (or similar) field in shared tables
   - Tenant identification via subdomain (e.g., `tenant1.yourgymapp.com`)

2. **Set Up Core Multi-Tenant Architecture** ✓
   - Implemented tenant identification middleware (`app/middleware.py`)
   - Middleware extracts tenant from subdomain and attaches to request state
   - Created tenant service (`app/services/tenants.py`) to fetch tenant by domain

3. **Implemented Middleware for Tenant Context Management** ✓
   - `TenantMiddleware` in `app/middleware.py` handles:
     - Tenant detection from request host
     - Attaching tenant object to `request.state.tenant`
     - Continuing request processing with tenant context

4. **Analyzed Existing Gym Application** ✓
   - Reviewed codebase for multi-tenancy readiness
   - Found existing tenant awareness in auth service and middleware
   - Identified areas needing enhancement for full multi-tenancy support

## Remaining Steps

### 5. Develop User Management with Multi-Tenancy Support
- [ ] **Authentication Service** (`app/services/auth.py`)
  - Verify all functions properly scope operations by tenant
  - Ensure `login_user` validates tenant membership
  - Ensure `create_user` associates new user with correct tenant
  - Review token handling to prevent cross-tenant token usage
- [ ] **User Service** (if exists or needs creation)
  - All user queries must include tenant filter
  - Functions: get user, update user, delete user, list users
- [ ] **User Routes** (`app/routes/auth.py`, `app/routes/user/`)
  - Ensure templates receive tenant context
  - Validate that users can only access their own tenant's data
  - Check that form submissions include tenant context where needed
- [ ] **Database Schema**
  - Verify `users` collection includes `tenant` field (references tenants collection)
  - Add index on `tenant` field for query performance
  - Ensure foreign key relationship between users and tenants collections
- [ ] **Password Reset & Email Flows**
  - Ensure password reset tokens are tenant-scoped
  - Email templates should include tenant-specific branding/links

### 6. Develop Membership Management with Multi-Tenancy Support
- [ ] **Plans/Subscriptions Service** (`app/services/plan.py`)
  - All plan queries must filter by tenant
  - Functions: create plan, get plan, update plan, delete plan, list plans
  - Plan validation to prevent cross-tenant assignment
- [ ] **Trainee/Membership Service**
  - Trainee records must include tenant reference
  - Membership payments and subscriptions tied to tenant
  - Functions for managing trainee lifecycle, membership status, payments
- [ ] **Membership Routes**
  - Protect routes to ensure tenants only manage their own members/plans
  - Validate tenant membership on all incoming requests
- [ ] **Database Schema**
  - Add `tenant` field to `plans`, `trainees`, `payments`, `subscriptions` collections
  - Indexes on tenant fields for performance
  - Consider soft delete patterns that respect tenant boundaries

### 7. Develop Class Scheduling with Multi-Tenancy Support
- [ ] **Class/Booking Service**
  - Classes, bookings, attendance records must be tenant-scoped
  - Prevent double-booking within same tenant
  - Allow cross-trainer viewing only within same tenant
- [ ] **Scheduling Routes**
  - Calendar views filtered by tenant
  - Booking creation validates trainer/trainee belong to same tenant
  - Instructor schedules isolated per tenant
- [ ] **Database Schema**
  - Add `tenant` field to `classes`, `bookings`, `attendance` collections
  - Indexes for efficient tenant-based queries
  - Consider recurring event patterns that respect tenant isolation

### 8. Develop Reporting & Analytics with Multi-Tenancy Support
- [ ] **Dashboard Service** (`app/services/dashboard.py`)
  - All analytics queries must filter by tenant
  - Existing `get_owner_dashboard_stats` already uses tenant filtering - verify consistency
  - Extend to other reports: revenue, attendance, class popularity, etc.
- [ ] **Reporting Routes**
  - Ensure reports only show data from the current tenant
  - Prevent data leakage between tenants in aggregated views
- [ ] **Database Considerations**
  - Materialized views or aggregate tables must include tenant partitioning
  - Index strategies for analytical queries on tenant-filtered data

### 9. Integrate Payment Processing with Multi-Tenancy Support
- [ ] **Payment Service**
  - Merchant credentials stored per tenant (encrypted)
  - Payment transactions linked to tenant and user
  - Webhook processing must verify tenant context
  - Refunds and disputes handled within tenant boundary
- [ ] **Payment Routes**
  - Payment initiation validates tenant membership
  - Webhook endpoints validate tenant via request metadata or signed payload
  - Payment history restricted to tenant
- [ ] **Database Schema**
  - Store payment provider customer IDs with tenant reference
  - Transactions table includes `tenant_id`, `user_id`, `plan_id`
  - Encrypt sensitive payment data at rest

### 10. Configure Environment Variables and Logging for Multi-Tenancy
- [ ] **Environment Configuration**
  - Document required environment variables (PB_URL, etc.)
  - Add tenant-specific config overrides (if needed)
  - Separate configs for development, staging, production per tenant
- [ ] **Logging Enhancement**
  - Include tenant ID in all log entries for traceability
  - Structured logging to facilitate tenant-based log filtering
  - Audit logs for cross-tenant access attempts (should be blocked)
- [ ] **Error Handling**
  - Tenant-not-found errors should return appropriate HTTP status
  - Log unauthorized access attempts with tenant context

### 11. Establish Testing Strategy for Multi-Tenant Scenarios
- [ ] **Unit Tests**
  - Mock tenant context in service tests
  - Verify tenant isolation in data access methods
  - Test authentication flows with valid/invalid tenants
- [ ] **Integration Tests**
  - Test API endpoints with different tenant contexts
  - Verify cross-tenant access is blocked
  - Test tenant provisioning and deprovisioning flows
- [ ] **End-to-End Tests**
  - Simulate multiple tenants using the system simultaneously
  - Test data isolation between tenant contexts
  - Performance testing with multiple tenants
- [ ] **Test Data Management**
  - Strategies for generating isolated test data per tenant
  - Test database setup/teardown for parallel test execution

### 12. Develop Tenant Onboarding Process
- [ ] **Tenant Provisioning API**
  - Endpoint to create new tenant (subdomain, initial admin user)
  - Automatic schema migrations (if needed) for new tenant
  - Initial data setup (default plans, roles, etc.)
- [ ] **Self-Service Signup Flow**
  - Landing page for new tenant registration
  - Validation of subdomain availability
  - Provision of trial period or payment setup
- [ ] **Tenant Management Dashboard**
  - Super admin view to manage all tenants
  - Ability to suspend/reactivate tenants
  - View tenant usage metrics and billing info
- [ ] **Data Migration Tooling** (for existing single-tenant to multi-tenant)
  - Scripts to migrate existing data to multi-tenant schema
  - Tenant assignment strategies for legacy data
  - Validation checks post-migration

### 13. Test and Deploy the Refactored Multi-Tenant Application
- [ ] **Testing Phases**
  - Unit test coverage >80% for core services
  - Integration tests for all tenant-boundary scenarios
  - Performance baseline testing
  - Security audit for tenant isolation vulnerabilities
- [ ] **Deployment Strategy**
  - Blueprint for deploying multiple tenant instances
  - Database migration procedures for schema updates
  - Backup and disaster recovery per tenant
  - Monitoring and alerting setup for multi-tenant metrics
- [ ] **Documentation**
  - API documentation highlighting tenant context requirements
  - Developer guide for extending the boilerplate
  - Runbook for tenant operations (backup, restore, migrate)

## Detailed Modification Areas

### Middleware Enhancements
- Ensure tenant middleware handles missing/invalid subdomains gracefully
- Add tenant validation to prevent access to non-existent tenants
- Consider caching tenant lookups for performance

### Service Layer Patterns
- All service functions should accept tenant ID/context as parameter
- Repository pattern considerations for tenant-scoped queries
- Centralized tenant validation decorator/middleware

### Route Protection
- Middleware to verify user belongs to current tenant after authentication
- Role-based access control (RBAC) that respects tenant boundaries
- Audit logging for sensitive operations

### Database Considerations
- Consistent tenant field naming (`tenant_id` or `tenant`)
- Index strategy: composite indexes including tenant column for common queries
- Consider partitioning strategies for large-scale deployments
- Backup/restore procedures that maintain tenant isolation

### API Design
- All API endpoints should implicitly operate within tenant context
- Consider explicit tenant ID in URL for clarity (alternative to subdomain)
- Versioning strategy that maintains tenant contracts

## Boilerplate Reusability Features
- Extract multi-tenancy concerns into reusable modules/plugins
- Configuration-driven tenant identification (subdomain, header, JWT claim)
- Base controller/service classes that enforce tenant scoping
- Template for tenant-specific overrides (branding, features)

This plan provides a comprehensive roadmap for transforming the existing gym application into a multi-tenant SaaS boilerplate. Each section should be implemented and tested incrementally to ensure stability throughout the refactoring process.