"""
Neo4J Knowledge Graph Client
Manages the manufacturing ecosystem knowledge graph for agent coordination.

As a Knowledge Graph Engineer:
- Nodes represent entities (Robots, Stages, Suppliers, Materials, Agents)
- Relationships capture dependencies and interactions
- Graph queries enable conflict detection and coordination analysis
"""

import asyncio
from typing import Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from config import settings

logger = structlog.get_logger(__name__)


class Neo4JClient:
    """
    Async Neo4J client for knowledge graph operations.
    
    Graph Schema:
    - (:Robot) - Mobile robots in warehouse
    - (:Stage) - Manufacturing stages
    - (:Supplier) - External suppliers
    - (:Material) - Raw materials and inventory
    - (:Agent) - Domain agents (Robotics, Manufacturing, SupplyChain)
    - (:Decision) - AI decisions made
    - (:Problem) - Detected coordination problems
    """
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self._driver: Optional[AsyncDriver] = None
        self._initialized = False
    
    async def connect(self) -> None:
        """Establish connection to Neo4J."""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connectivity
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            
            self._initialized = True
            logger.info("Neo4J connected", uri=self.uri)
            
            # Initialize schema
            await self._initialize_schema()
            
        except Exception as e:
            logger.error("Neo4J connection failed", error=str(e))
            self._initialized = False
            raise
    
    async def close(self) -> None:
        """Close Neo4J connection."""
        if self._driver:
            await self._driver.close()
            logger.info("Neo4J connection closed")
    
    @asynccontextmanager
    async def session(self):
        """Get a Neo4J session."""
        if not self._driver:
            raise RuntimeError("Neo4J not connected")
        async with self._driver.session() as session:
            yield session
    
    async def _initialize_schema(self) -> None:
        """Create indexes and constraints for optimal performance."""
        async with self.session() as session:
            # Create indexes
            indexes = [
                "CREATE INDEX robot_id IF NOT EXISTS FOR (r:Robot) ON (r.id)",
                "CREATE INDEX stage_id IF NOT EXISTS FOR (s:Stage) ON (s.id)",
                "CREATE INDEX supplier_id IF NOT EXISTS FOR (s:Supplier) ON (s.id)",
                "CREATE INDEX agent_domain IF NOT EXISTS FOR (a:Agent) ON (a.domain)",
                "CREATE INDEX decision_timestamp IF NOT EXISTS FOR (d:Decision) ON (d.timestamp)",
                "CREATE INDEX problem_type IF NOT EXISTS FOR (p:Problem) ON (p.type)"
            ]
            
            for index_query in indexes:
                try:
                    await session.run(index_query)
                except Exception as e:
                    logger.warning("Index creation skipped", query=index_query, error=str(e))
            
            logger.info("Neo4J schema initialized")
    
    # =========================================================================
    # ROBOT NODES
    # =========================================================================
    async def upsert_robot(self, robot_data: dict) -> None:
        """Create or update a robot node."""
        query = """
        MERGE (r:Robot {id: $id})
        SET r.position_x = $position_x,
            r.position_y = $position_y,
            r.battery = $battery,
            r.status = $status,
            r.task = $task,
            r.speed = $speed,
            r.last_update = datetime()
        """
        async with self.session() as session:
            await session.run(query, robot_data)
    
    async def get_robot(self, robot_id: int) -> Optional[dict]:
        """Get robot node by ID."""
        query = "MATCH (r:Robot {id: $id}) RETURN r"
        async with self.session() as session:
            result = await session.run(query, {"id": robot_id})
            record = await result.single()
            return dict(record["r"]) if record else None
    
    async def get_all_robots(self) -> list[dict]:
        """Get all robot nodes."""
        query = "MATCH (r:Robot) RETURN r ORDER BY r.id"
        async with self.session() as session:
            result = await session.run(query)
            records = await result.data()
            return [dict(r["r"]) for r in records]
    
    # =========================================================================
    # STAGE NODES
    # =========================================================================
    async def upsert_stage(self, stage_data: dict) -> None:
        """Create or update a manufacturing stage node."""
        query = """
        MERGE (s:Stage {id: $id})
        SET s.name = $name,
            s.queue_depth = $queue_depth,
            s.throughput = $throughput,
            s.status = $status,
            s.energy = $energy,
            s.defect_rate = $defect_rate,
            s.last_update = datetime()
        """
        async with self.session() as session:
            await session.run(query, stage_data)
    
    async def create_stage_pipeline(self, stage_order: list[int]) -> None:
        """Create FEEDS_INTO relationships between stages."""
        for i in range(len(stage_order) - 1):
            query = """
            MATCH (s1:Stage {id: $from_id}), (s2:Stage {id: $to_id})
            MERGE (s1)-[:FEEDS_INTO]->(s2)
            """
            async with self.session() as session:
                await session.run(query, {
                    "from_id": stage_order[i],
                    "to_id": stage_order[i + 1]
                })
    
    # =========================================================================
    # SUPPLIER NODES
    # =========================================================================
    async def upsert_supplier(self, supplier_data: dict) -> None:
        """Create or update a supplier node."""
        query = """
        MERGE (s:Supplier {id: $id})
        SET s.name = $name,
            s.status = $status,
            s.lead_time = $lead_time,
            s.reliability = $reliability,
            s.last_update = datetime()
        """
        async with self.session() as session:
            await session.run(query, supplier_data)
    
    # =========================================================================
    # AGENT NODES
    # =========================================================================
    async def upsert_agent(self, agent_data: dict) -> None:
        """Create or update a domain agent node."""
        query = """
        MERGE (a:Agent {domain: $domain})
        SET a.status = $status,
            a.current_action = $current_action,
            a.decisions_made = COALESCE(a.decisions_made, 0) + 1,
            a.last_update = datetime()
        """
        async with self.session() as session:
            await session.run(query, agent_data)
    
    async def record_agent_conflict(
        self,
        agent1_domain: str,
        agent2_domain: str,
        conflict_type: str,
        description: str
    ) -> None:
        """Record a conflict between two agents."""
        query = """
        MATCH (a1:Agent {domain: $domain1}), (a2:Agent {domain: $domain2})
        CREATE (a1)-[:CONFLICTS_WITH {
            type: $conflict_type,
            description: $description,
            timestamp: datetime(),
            resolved: false
        }]->(a2)
        """
        async with self.session() as session:
            await session.run(query, {
                "domain1": agent1_domain,
                "domain2": agent2_domain,
                "conflict_type": conflict_type,
                "description": description
            })
    
    # =========================================================================
    # PROBLEM DETECTION
    # =========================================================================
    async def detect_robot_collisions(self, collision_radius: float = 0.5) -> list[dict]:
        """Find robots that are too close to each other."""
        query = """
        MATCH (r1:Robot), (r2:Robot)
        WHERE r1.id < r2.id
          AND sqrt((r1.position_x - r2.position_x)^2 + (r1.position_y - r2.position_y)^2) < $radius
        RETURN r1.id AS robot1, r2.id AS robot2,
               sqrt((r1.position_x - r2.position_x)^2 + (r1.position_y - r2.position_y)^2) AS distance
        """
        async with self.session() as session:
            result = await session.run(query, {"radius": collision_radius})
            return await result.data()
    
    async def detect_bottlenecks(self, queue_threshold: int = 20) -> list[dict]:
        """Find bottleneck stages based on queue depth."""
        query = """
        MATCH (s:Stage)
        WHERE s.queue_depth > $threshold
        RETURN s.id AS stage_id, s.name AS stage_name, s.queue_depth AS queue_depth
        ORDER BY s.queue_depth DESC
        """
        async with self.session() as session:
            result = await session.run(query, {"threshold": queue_threshold})
            return await result.data()
    
    async def detect_supply_risks(self) -> list[dict]:
        """Find supply chain risks (low stock, delayed suppliers)."""
        query = """
        MATCH (s:Supplier)-[:SUPPLIES]->(m:Material)
        WHERE s.status = 'delayed' OR m.stock_level < m.reorder_point
        RETURN s.name AS supplier, m.name AS material, 
               s.status AS supplier_status, m.stock_level AS stock,
               m.reorder_point AS reorder_point
        """
        async with self.session() as session:
            result = await session.run(query)
            return await result.data()
    
    async def find_uncoordinated_decisions(self) -> list[dict]:
        """Find decisions made by different agents that conflict."""
        query = """
        MATCH (d1:Decision)<-[:MADE]-(a1:Agent),
              (d2:Decision)<-[:MADE]-(a2:Agent)
        WHERE a1.domain <> a2.domain
          AND abs(d1.timestamp.epochMillis - d2.timestamp.epochMillis) < 5000
          AND d1.affects_target = d2.affects_target
        RETURN a1.domain AS agent1, a2.domain AS agent2,
               d1.action AS action1, d2.action AS action2,
               d1.affects_target AS target
        """
        async with self.session() as session:
            result = await session.run(query)
            return await result.data()
    
    # =========================================================================
    # GRAPH VISUALIZATION DATA
    # =========================================================================
    async def get_full_graph(self) -> dict:
        """Get entire graph for visualization."""
        nodes_query = """
        MATCH (n)
        RETURN labels(n)[0] AS type, properties(n) AS props
        """
        edges_query = """
        MATCH (a)-[r]->(b)
        RETURN labels(a)[0] AS source_type, a.id AS source_id,
               type(r) AS relationship, properties(r) AS props,
               labels(b)[0] AS target_type, b.id AS target_id
        """
        
        async with self.session() as session:
            nodes_result = await session.run(nodes_query)
            nodes = await nodes_result.data()
            
            edges_result = await session.run(edges_query)
            edges = await edges_result.data()
        
        return {
            "nodes": nodes,
            "edges": edges,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # =========================================================================
    # CLEAR DATA
    # =========================================================================
    async def clear_all(self) -> None:
        """Clear all nodes and relationships (for reset)."""
        async with self.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("Neo4J graph cleared")


# Global client instance
neo4j_client = Neo4JClient()


async def get_neo4j_client() -> Neo4JClient:
    """Get the Neo4J client, connecting if needed."""
    if not neo4j_client._initialized:
        await neo4j_client.connect()
    return neo4j_client
