"""Knowledge Graph module for Neo4J integration."""

from .neo4j_client import Neo4JClient, neo4j_client, get_neo4j_client

__all__ = ["Neo4JClient", "neo4j_client", "get_neo4j_client"]
