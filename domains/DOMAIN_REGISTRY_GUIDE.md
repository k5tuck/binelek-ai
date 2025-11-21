# Binelek Domain Registry - Structure Guide

**Last Updated:** November 19, 2025
**Version:** 2.0.0

---

## Overview

The Binelek platform uses a YAML-driven domain architecture where each industry vertical or use case is defined by three configuration files. This document explains the folder structure, the difference between domains and templates, and how to add new verticals.

---

## Folder Structure

```
config/domains/
├── [industry]/              # Enterprise industry verticals (20)
│   ├── domain.yaml          # Industry metadata, pricing, compliance
│   ├── ontology.yaml        # Entities, relationships, validation
│   └── ui-config.yaml       # Dashboard, navigation, forms
│
└── templates/               # SMB/Personal starter templates (5)
    └── [template]/
        ├── domain.yaml
        ├── ontology.yaml
        └── ui-config.yaml
```

---

## Domains vs Templates

### Enterprise Industry Verticals (`domains/[industry]/`)

**Purpose:** Full enterprise-grade industry solutions

**Characteristics:**
- Comprehensive entity models (10-30+ entities)
- Detailed compliance documentation (HIPAA, SOX, GDPR, etc.)
- Enterprise pricing tiers ($499 - $50,000+/month)
- Priority integrations with enterprise systems
- Full UI configurations with multiple dashboards
- Production-ready deployments

**Examples:** real-estate, healthcare, finance, legal, insurance, manufacturing

**Status Categories:**
- **Available** (5): Production-ready with full support
- **Coming Soon** (5): Active development, Q1-Q2 2026
- **Planned** (5): On roadmap, Q3-Q4 2026
- **Future** (5): 2027+ based on demand

---

### Starter Templates (`domains/templates/[template]/`)

**Purpose:** Quick-start templates for SMB and personal use

**Characteristics:**
- Simpler entity models (5-15 entities)
- Basic compliance (GDPR, PCI-DSS)
- Lower pricing tiers ($9 - $599/month)
- Common integrations (Google, Stripe, etc.)
- Streamlined UI configurations
- Customizable starting points
- Uses `category: "template"` in domain.yaml

**Examples:** personal, restaurant, retail, ecommerce, professional-services

**Target Users:**
- Small businesses
- Individuals
- Startups
- Quick evaluations

---

## Domain Index

### Available Now (Production-Ready)

| ID | Name | Entities | Status |
|----|------|----------|--------|
| `real-estate` | Real Estate & Property Management | 12 | ✅ Available |
| `healthcare` | Healthcare & Medical Practice | 12 | ✅ Available |
| `finance` | Finance & Wealth Management | 10 | ✅ Available |
| `smart-cities` | Smart Cities & Urban Planning | 10 | ✅ Available |
| `logistics` | Logistics & Supply Chain | 10 | ✅ Available |

### Coming Soon (Q1-Q2 2026)

| ID | Name | Entities | Status |
|----|------|----------|--------|
| `legal` | Legal & Law Practice | 12 | 🔶 Q1 2026 |
| `insurance` | Insurance | 10 | 🔶 Q1 2026 |
| `manufacturing` | Manufacturing & Industrial | 10 | 🔶 Q2 2026 |
| `retail` | Retail & E-commerce | 10 | 🔶 Q2 2026 |
| `education` | Education & Research | 11 | 🔶 Q2 2026 |

### Planned (Q3-Q4 2026)

| ID | Name | Entities | Status |
|----|------|----------|--------|
| `energy` | Energy & Utilities | 10 | 📅 Q3 2026 |
| `telecommunications` | Telecommunications | 10 | 📅 Q3 2026 |
| `pharmaceuticals` | Pharmaceuticals & Life Sciences | 11 | 📅 Q4 2026 |
| `media` | Media & Entertainment | 10 | 📅 Q4 2026 |
| `construction` | Construction & Engineering | 10 | 📅 Q4 2026 |

### Future Roadmap (2027+)

| ID | Name | Entities | Status |
|----|------|----------|--------|
| `agriculture` | Agriculture & Food | 10 | 🔮 2027 |
| `hospitality` | Hospitality & Travel | 10 | 🔮 2027 |
| `nonprofit` | Non-Profit & NGO | 10 | 🔮 2027 |
| `government` | Government & Public Sector | 10 | 🔮 2027+ |
| `professional-services` | Professional Services | 10 | 🔮 2027 |

### Starter Templates

| ID | Name | Entities | Target |
|----|------|----------|--------|
| `personal` | Personal Knowledge Base | 10 | Individuals |
| `restaurant` | Restaurant Management | 8 | Small restaurants |
| `retail` | Retail Store | 8 | Small retailers |
| `ecommerce` | E-commerce | 10 | Online stores |
| `professional-services` | Professional Services | 8 | Consultants/agencies |

---

## File Specifications

### domain.yaml

Required root key: `domain`

```yaml
domain:
  id: string              # Unique identifier (kebab-case)
  name: string            # Display name
  version: string         # Semantic version
  description: string     # Multi-line description
  icon: string            # Icon name or emoji
  color: string           # Hex color code
  category: string        # "industry" or "template"

  industry:
    sector: string
    subsectors: string[]
    primary_use_cases: string[]

  target_customers:
    - type: string
      size: string
      pain_points: string[]

  market_analysis:
    market_size: object
    key_trends: string[]
    competitive_landscape: object

  pricing_tiers:
    - tier: string
      price: string
      target: string
      included: string[]
      limitations: string[]
      overage_rates: string[]

  compliance_requirements:
    regulations:
      - name: string
        description: string
        impact: string

  integration_ecosystem:
    priority_integrations:
      - name: string
        providers: string[]
        use_case: string

  success_metrics:
    key_performance_indicators:
      - metric: string
        benchmark: string

  metadata:
    created_by: string
    created_at: date
    last_updated: date
    version_history: object[]
```

### ontology.yaml

Required root key: `ontology`

```yaml
ontology:
  version: string

  entities:
    - name: string
      label: string
      description: string
      icon: string
      color: string
      attributes:
        - name: string
          type: string           # string, number, boolean, date, enum, etc.
          required: boolean
          unique: boolean
          indexed: boolean
          default: any
          validators: object[]
      indexes: string[]

  relationships:
    - name: string
      from: string
      to: string
      type: string             # one-to-one, one-to-many, many-to-many
      required: boolean
      attributes: object[]

  common_queries:
    - name: string
      description: string
      cypher: string
```

### ui-config.yaml

Required root key: `ui`

```yaml
ui:
  theme:
    primary_color: string
    accent_color: string
    logo: string

  navigation:
    - id: string
      label: string
      icon: string
      route: string
      badge: string
      children: object[]

  dashboards:
    - id: string
      name: string
      default: boolean
      widgets: object[]

  entity_views:
    [entity_name]:
      list:
        columns: object[]
        filters: object[]
        actions: object[]
        default_sort: object
      detail:
        sections: object[]
        tabs: object[]
      form:
        layout: string
        fields: object[]

  search:
    global:
      placeholder: string
      entity_types: string[]
    entity_search:
      [entity_name]:
        searchable_fields: string[]
        result_template: string

  reports:
    - id: string
      name: string
      description: string
      entity_types: string[]
      parameters: object[]
      sections: object[]
```

---

## How DomainService Loads Domains

The `DomainService` (in `binah-domain-registry`) loads domains from the configured `DomainsDirectory`:

1. Scans immediate subdirectories of `DomainsDirectory`
2. For each subdirectory, looks for all 3 required files:
   - `domain.yaml`
   - `ontology.yaml`
   - `ui-config.yaml`
3. Parses YAML and validates structure
4. Caches in memory (5-minute TTL)
5. Optionally caches in Redis (24-hour TTL)

**Important:** The `templates/` subdirectory is NOT automatically loaded because it's nested. To load templates, configure a separate service or use the template-specific API.

---

## Adding a New Industry Vertical

1. **Create directory:**
   ```bash
   mkdir -p config/domains/[industry-name]
   ```

2. **Create domain.yaml:**
   - Copy from an existing domain as template
   - Update id, name, description
   - Define industry-specific sections

3. **Create ontology.yaml:**
   - Define entities with attributes
   - Define relationships
   - Add common Cypher queries

4. **Create ui-config.yaml:**
   - Configure dashboards
   - Configure entity views
   - Configure navigation

5. **Validate:**
   ```bash
   curl http://localhost:8100/api/domains/[industry-name]/validate
   ```

6. **Reload:**
   ```bash
   curl -X POST http://localhost:8100/api/domains/reload
   ```

---

## API Endpoints

### Get All Domains
```
GET /api/domains
```

### Get Domain by ID
```
GET /api/domains/{domainId}
```

### Get Domain Metadata
```
GET /api/domains/{domainId}/metadata
```

### Get Domain Ontology
```
GET /api/domains/{domainId}/ontology
```

### Get Domain UI Config
```
GET /api/domains/{domainId}/ui-config
```

### Get Domain Entities
```
GET /api/domains/{domainId}/entities
```

### Get Entity Definition
```
GET /api/domains/{domainId}/entities/{entityName}
```

### Validate Domain
```
GET /api/domains/{domainId}/validate
```

### Reload All Domains
```
POST /api/domains/reload
```

### Get Domain Stats
```
GET /api/domains/stats
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DomainsDirectory` | Path to domains folder | `/app/domains` |
| `ConnectionStrings__Redis` | Redis connection string | (optional) |

### appsettings.json

```json
{
  "DomainsDirectory": "/app/domains",
  "ConnectionStrings": {
    "Redis": "localhost:6379"
  }
}
```

### Docker Volume Mount

```yaml
services:
  binah-domain-registry:
    volumes:
      - ./config/domains:/app/domains:ro
```

---

## Best Practices

1. **Use kebab-case** for domain IDs (`real-estate`, not `realEstate`)
2. **Include all 3 files** - domains without all files are skipped
3. **Validate YAML syntax** before committing
4. **Test locally** with domain registry before deployment
5. **Document compliance** thoroughly for regulated industries
6. **Version your domains** using semantic versioning
7. **Keep templates simple** - they're starting points, not complete solutions

---

## Troubleshooting

### Domain not loading

1. Check all 3 files exist
2. Validate YAML syntax
3. Check file permissions
4. Check logs: `docker logs binah-domain-registry`

### Redis cache issues

1. Clear cache: `redis-cli FLUSHDB`
2. Restart service
3. Check Redis connection string

### Entity not found

1. Check entity name matches exactly (case-sensitive)
2. Reload domains: `POST /api/domains/reload`
3. Check ontology.yaml for typos

---

**Document Version:** 2.0.0
**Maintained By:** Binelek Platform Team
