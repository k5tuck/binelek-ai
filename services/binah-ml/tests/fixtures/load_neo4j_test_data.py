"""
Load test data into Neo4j with tenant isolation

This script creates test graph data for two tenants:
- Tenant A: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
- Tenant B: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb

All nodes include tenantId property for isolation testing.
"""

from neo4j import GraphDatabase
import sys

# Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"  # Change as needed

TENANT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def create_test_data(driver):
    """Create test data for both tenants"""

    with driver.session() as session:
        # Clean up existing test data
        print("Cleaning up existing test data...")
        session.run("""
            MATCH (n)
            WHERE n.tenantId IN [$tenantA, $tenantB]
            DETACH DELETE n
        """, tenantA=TENANT_A_ID, tenantB=TENANT_B_ID)

        # Create Tenant A data
        print(f"Creating test data for Tenant A ({TENANT_A_ID})...")

        # Create projects for Tenant A
        session.run("""
            CREATE (p1:Project {
                id: 'a-proj-001',
                tenantId: $tenantId,
                name: 'Downtown Office Complex',
                size_sqft: 50000,
                num_units: 50,
                location_tier: 1,
                property_type: 'commercial',
                status: 'active'
            })
            CREATE (p2:Project {
                id: 'a-proj-002',
                tenantId: $tenantId,
                name: 'Suburban Residential',
                size_sqft: 35000,
                num_units: 35,
                location_tier: 2,
                property_type: 'residential',
                status: 'planning'
            })
            CREATE (p3:Project {
                id: 'a-proj-003',
                tenantId: $tenantId,
                name: 'Mixed Use Development',
                size_sqft: 80000,
                num_units: 100,
                location_tier: 1,
                property_type: 'mixed',
                status: 'active'
            })
        """, tenantId=TENANT_A_ID)

        # Create training data entities for Tenant A
        session.run("""
            CREATE (t1:TrainingData {
                id: 'a-train-001',
                tenantId: $tenantId,
                model_type: 'cost_forecasting',
                project_size_sqft: 45000,
                num_units: 45,
                location_tier: 2,
                property_type: 'commercial',
                actual_cost: 11250000
            })
            CREATE (t2:TrainingData {
                id: 'a-train-002',
                tenantId: $tenantId,
                model_type: 'cost_forecasting',
                project_size_sqft: 60000,
                num_units: 75,
                location_tier: 1,
                property_type: 'residential',
                actual_cost: 15000000
            })
            CREATE (t3:TrainingData {
                id: 'a-train-003',
                tenantId: $tenantId,
                model_type: 'risk_assessment',
                leverage_ratio: 0.75,
                occupancy_rate: 0.92,
                market_volatility: 0.45,
                actual_risk: 0.55
            })
        """, tenantId=TENANT_A_ID)

        # Create model entities for Tenant A
        session.run("""
            CREATE (m1:MLModel {
                id: 'a1111111-1111-1111-1111-111111111112',
                tenantId: $tenantId,
                model_type: 'cost_forecasting',
                model_version: '2.0',
                status: 'ready',
                accuracy: 0.94
            })
            CREATE (m2:MLModel {
                id: 'a2222222-2222-2222-2222-222222222222',
                tenantId: $tenantId,
                model_type: 'risk_assessment',
                model_version: '1.0',
                status: 'ready',
                accuracy: 0.87
            })
        """, tenantId=TENANT_A_ID)

        # Create relationships for Tenant A
        session.run("""
            MATCH (p:Project {tenantId: $tenantId})
            MATCH (m:MLModel {tenantId: $tenantId, model_type: 'cost_forecasting'})
            CREATE (p)-[:PREDICTED_BY]->(m)
        """, tenantId=TENANT_A_ID)

        # Create Tenant B data
        print(f"Creating test data for Tenant B ({TENANT_B_ID})...")

        # Create projects for Tenant B
        session.run("""
            CREATE (p1:Project {
                id: 'b-proj-001',
                tenantId: $tenantId,
                name: 'Enterprise Tower',
                size_sqft: 120000,
                num_units: 150,
                location_tier: 1,
                property_type: 'commercial',
                status: 'active'
            })
            CREATE (p2:Project {
                id: 'b-proj-002',
                tenantId: $tenantId,
                name: 'Waterfront Condos',
                size_sqft: 65000,
                num_units: 80,
                location_tier: 1,
                property_type: 'residential',
                status: 'active'
            })
            CREATE (p3:Project {
                id: 'b-proj-003',
                tenantId: $tenantId,
                name: 'Industrial Park',
                size_sqft: 200000,
                num_units: 20,
                location_tier: 3,
                property_type: 'industrial',
                status: 'planning'
            })
        """, tenantId=TENANT_B_ID)

        # Create training data entities for Tenant B
        session.run("""
            CREATE (t1:TrainingData {
                id: 'b-train-001',
                tenantId: $tenantId,
                model_type: 'cost_forecasting',
                project_size_sqft: 100000,
                num_units: 120,
                location_tier: 1,
                property_type: 'commercial',
                actual_cost: 30000000
            })
            CREATE (t2:TrainingData {
                id: 'b-train-002',
                tenantId: $tenantId,
                model_type: 'cost_forecasting',
                project_size_sqft: 55000,
                num_units: 65,
                location_tier: 2,
                property_type: 'residential',
                actual_cost: 13750000
            })
            CREATE (t3:TrainingData {
                id: 'b-train-003',
                tenantId: $tenantId,
                model_type: 'risk_assessment',
                leverage_ratio: 0.68,
                occupancy_rate: 0.95,
                market_volatility: 0.35,
                actual_risk: 0.32
            })
        """, tenantId=TENANT_B_ID)

        # Create model entities for Tenant B
        session.run("""
            CREATE (m1:MLModel {
                id: 'b1111111-1111-1111-1111-111111111112',
                tenantId: $tenantId,
                model_type: 'cost_forecasting',
                model_version: '1.1',
                status: 'ready',
                accuracy: 0.91
            })
            CREATE (m2:MLModel {
                id: 'b2222222-2222-2222-2222-222222222222',
                tenantId: $tenantId,
                model_type: 'risk_assessment',
                model_version: '1.0',
                status: 'ready',
                accuracy: 0.85
            })
        """, tenantId=TENANT_B_ID)

        # Create relationships for Tenant B
        session.run("""
            MATCH (p:Project {tenantId: $tenantId})
            MATCH (m:MLModel {tenantId: $tenantId, model_type: 'cost_forecasting'})
            CREATE (p)-[:PREDICTED_BY]->(m)
        """, tenantId=TENANT_B_ID)

        # Verify data creation
        print("\nVerifying data creation...")

        # Count nodes per tenant
        result_a = session.run("""
            MATCH (n)
            WHERE n.tenantId = $tenantId
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY label
        """, tenantId=TENANT_A_ID)

        print(f"\nTenant A nodes:")
        for record in result_a:
            print(f"  {record['label']}: {record['count']}")

        result_b = session.run("""
            MATCH (n)
            WHERE n.tenantId = $tenantId
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY label
        """, tenantId=TENANT_B_ID)

        print(f"\nTenant B nodes:")
        for record in result_b:
            print(f"  {record['label']}: {record['count']}")

        # Count relationships
        rel_count_a = session.run("""
            MATCH (n)-[r]->(m)
            WHERE n.tenantId = $tenantId
            RETURN count(r) as count
        """, tenantId=TENANT_A_ID).single()['count']

        rel_count_b = session.run("""
            MATCH (n)-[r]->(m)
            WHERE n.tenantId = $tenantId
            RETURN count(r) as count
        """, tenantId=TENANT_B_ID).single()['count']

        print(f"\nTenant A relationships: {rel_count_a}")
        print(f"Tenant B relationships: {rel_count_b}")

        print("\n✓ Neo4j test data created successfully!")


def main():
    """Main function"""
    print("=" * 80)
    print("Neo4j Test Data Loader")
    print("=" * 80)
    print(f"\nConnecting to Neo4j at {NEO4J_URI}...")

    try:
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

        # Verify connection
        driver.verify_connectivity()
        print("✓ Connected to Neo4j successfully\n")

        # Create test data
        create_test_data(driver)

        driver.close()
        print("\n" + "=" * 80)
        print("COMPLETE - Neo4j test data loaded")
        print("=" * 80)
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure Neo4j is running and credentials are correct.")
        print(f"Connection: {NEO4J_URI}")
        print(f"Username: {NEO4J_USER}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
