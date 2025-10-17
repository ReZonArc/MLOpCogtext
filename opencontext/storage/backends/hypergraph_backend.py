# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Hypergraph storage backend for OpenCog-inspired multi-layer context representation
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional
from pathlib import Path

from opencontext.interfaces.storage_interface import IContextStorage
from opencontext.models.context import ProcessedContext, Vectorize
from opencontext.models.hypergraph import HyperGraph, Atom, Node, Link, AtomType, TruthValue
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class HypergraphStorage(IContextStorage):
    """
    Hypergraph storage backend using SQLite for persistence and in-memory hypergraph for reasoning
    """
    
    def __init__(self):
        self.hypergraph: Optional[HyperGraph] = None
        self.db_path: Optional[Path] = None
        self.connection: Optional[sqlite3.Connection] = None
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the hypergraph storage backend"""
        try:
            # Get configuration
            storage_path = config.get("storage_path", "data/hypergraph.db")
            self.db_path = Path(storage_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            self._init_database()
            
            # Create or load hypergraph
            hypergraph_name = config.get("hypergraph_name", "MineContext_HyperGraph")
            self.hypergraph = self._load_or_create_hypergraph(hypergraph_name)
            
            logger.info(f"Hypergraph storage initialized at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hypergraph storage: {e}")
            return False
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS hypergraphs (
                graph_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                graph_data TEXT
            );
            
            CREATE TABLE IF NOT EXISTS atoms (
                uuid TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                atom_type TEXT NOT NULL,
                name TEXT,
                layer INTEGER DEFAULT 0,
                truth_strength REAL DEFAULT 0.5,
                truth_confidence REAL DEFAULT 0.5,
                attention_sti REAL DEFAULT 0.0,
                attention_lti REAL DEFAULT 0.0,
                attention_vlti BOOLEAN DEFAULT FALSE,
                context_id TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                properties TEXT,
                metadata TEXT,
                outgoing TEXT,
                FOREIGN KEY (graph_id) REFERENCES hypergraphs (graph_id)
            );
            
            CREATE TABLE IF NOT EXISTS processed_contexts (
                id TEXT PRIMARY KEY,
                context_data TEXT NOT NULL,
                hypergraph_atoms TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms (atom_type);
            CREATE INDEX IF NOT EXISTS idx_atoms_layer ON atoms (layer);
            CREATE INDEX IF NOT EXISTS idx_atoms_context ON atoms (context_id);
            CREATE INDEX IF NOT EXISTS idx_atoms_name ON atoms (name);
        """)
        
        self.connection.commit()
    
    def _load_or_create_hypergraph(self, name: str) -> HyperGraph:
        """Load existing hypergraph or create new one"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT graph_data FROM hypergraphs WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        if row:
            # Load existing hypergraph using JSON instead of pickle for security
            try:
                graph_data = json.loads(row[0])
                # Handle datetime parsing
                from datetime import datetime
                
                def parse_datetimes(obj):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if key.endswith('_at') or key == 'created_at' or key == 'updated_at':
                                if isinstance(value, str):
                                    try:
                                        obj[key] = datetime.fromisoformat(value)
                                    except (ValueError, TypeError):
                                        pass
                            elif key == 'atom_type' and isinstance(value, str):
                                # Convert atom_type string back to enum
                                from opencontext.models.hypergraph import AtomType
                                try:
                                    obj[key] = AtomType(value)
                                except ValueError:
                                    pass
                            elif isinstance(value, dict):
                                parse_datetimes(value)
                            elif isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict):
                                        parse_datetimes(item)
                    return obj
                
                graph_data = parse_datetimes(graph_data)
                hypergraph = HyperGraph.model_validate(graph_data)
                logger.info(f"Loaded existing hypergraph '{name}' with {len(hypergraph.atoms)} atoms")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to load hypergraph data: {e}")
                # Create new hypergraph if loading fails
                hypergraph = HyperGraph(name=name, description="MineContext Multi-layer Context HyperGraph")
                self._save_hypergraph(hypergraph)
        else:
            # Create new hypergraph
            hypergraph = HyperGraph(name=name, description="MineContext Multi-layer Context HyperGraph")
            self._save_hypergraph(hypergraph)
            logger.info(f"Created new hypergraph '{name}'")
        
        return hypergraph
    
    def _save_hypergraph(self, hypergraph: HyperGraph):
        """Save hypergraph to database using JSON serialization"""
        try:
            # Convert to JSON-safe format
            graph_dict = hypergraph.model_dump()
            # Handle datetime serialization
            import datetime
            
            def json_serializer(obj):
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                elif hasattr(obj, 'value'):  # Handle enums
                    return obj.value
                elif isinstance(obj, set):  # Handle sets
                    return list(obj)
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            graph_data = json.dumps(graph_dict, default=json_serializer)
            
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO hypergraphs 
                (graph_id, name, description, created_at, updated_at, graph_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                hypergraph.graph_id,
                hypergraph.name,
                hypergraph.description,
                hypergraph.created_at,
                hypergraph.updated_at,
                graph_data
            ))
            
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to save hypergraph: {e}")
            raise
    
    def _save_atom(self, atom: Atom):
        """Save individual atom to database"""
        cursor = self.connection.cursor()
        
        # Prepare data
        properties = json.dumps(getattr(atom, 'properties', {}))
        metadata = json.dumps(atom.metadata)
        outgoing = json.dumps(getattr(atom, 'outgoing', []))
        
        cursor.execute("""
            INSERT OR REPLACE INTO atoms 
            (uuid, graph_id, atom_type, name, layer, truth_strength, truth_confidence,
             attention_sti, attention_lti, attention_vlti, context_id, created_at, 
             updated_at, properties, metadata, outgoing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            atom.uuid,
            self.hypergraph.graph_id,
            atom.atom_type.value,
            atom.name,
            atom.layer,
            atom.truth_value.strength,
            atom.truth_value.confidence,
            atom.attention_value.sti,
            atom.attention_value.lti,
            atom.attention_value.vlti,
            atom.context_id,
            atom.created_at,
            atom.updated_at,
            properties,
            metadata,
            outgoing
        ))
        
        self.connection.commit()
    
    def get_name(self) -> str:
        """Get storage backend name"""
        return "HypergraphStorage"
    
    def get_description(self) -> str:
        """Get storage backend description"""
        return "OpenCog-inspired hypergraph storage for multi-layer context representation"
    
    def upsert_processed_context(self, context: ProcessedContext) -> str:
        """Store processed context and create hypergraph representation"""
        try:
            # Convert ProcessedContext to hypergraph atoms
            atoms_created = self._context_to_hypergraph(context)
            
            # Save context data
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO processed_contexts 
                (id, context_data, hypergraph_atoms, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                context.id,
                context.dump_json(),
                json.dumps(atoms_created),
                context.properties.create_time,
                context.properties.update_time
            ))
            
            # Save hypergraph
            self._save_hypergraph(self.hypergraph)
            
            logger.debug(f"Stored context {context.id} with {len(atoms_created)} hypergraph atoms")
            return context.id
            
        except Exception as e:
            logger.error(f"Failed to store processed context: {e}")
            raise
    
    def _context_to_hypergraph(self, context: ProcessedContext) -> List[str]:
        """Convert ProcessedContext to hypergraph atoms"""
        atoms_created = []
        
        # Create main context node
        context_node_uuid = self.hypergraph.create_context_node(
            context_id=context.id,
            name=context.extracted_data.title or f"Context_{context.id[:8]}",
            properties={
                "summary": context.extracted_data.summary,
                "keywords": context.extracted_data.keywords,
                "entities": context.extracted_data.entities,
                "tags": context.extracted_data.tags,
                "context_type": context.extracted_data.context_type.value,
                "confidence": context.extracted_data.confidence,
                "importance": context.extracted_data.importance,
                "create_time": context.properties.create_time.isoformat(),
                "event_time": context.properties.event_time.isoformat()
            },
            layer=0
        )
        atoms_created.append(context_node_uuid)
        
        # Create entity nodes and links
        for entity in context.extracted_data.entities:
            entity_uuid = self.hypergraph.create_entity_node(
                entity_name=entity,
                entity_type="Entity",
                layer=1
            )
            atoms_created.append(entity_uuid)
            
            # Link context to entity
            link_uuid = self.hypergraph.create_association_link(
                context_node_uuid,
                entity_uuid,
                strength=context.extracted_data.confidence / 100.0,
                layer=1
            )
            atoms_created.append(link_uuid)
        
        # Create keyword concept nodes
        for keyword in context.extracted_data.keywords:
            # Check if keyword concept already exists
            concept_atom = self.hypergraph.get_atom_by_name(f"Concept_{keyword}")
            if concept_atom is None:
                concept_uuid = self.hypergraph.add_atom(
                    Node(
                        atom_type=AtomType.CONCEPT_NODE,
                        name=f"Concept_{keyword}",
                        properties={"keyword": keyword}
                    ),
                    layer=2
                )
                atoms_created.append(concept_uuid)
            else:
                concept_uuid = concept_atom.uuid
            
            # Link context to concept
            link_uuid = self.hypergraph.create_association_link(
                context_node_uuid,
                concept_uuid,
                strength=0.7,
                layer=2
            )
            atoms_created.append(link_uuid)
        
        # Create temporal relationships if multiple contexts exist
        self._create_temporal_relationships(context, context_node_uuid)
        
        # Propagate attention based on importance (validate range)
        if context.extracted_data.importance is not None:
            attention_boost = max(0.0, min(1.0, context.extracted_data.importance / 100.0))
            self.hypergraph.propagate_attention(context_node_uuid, sti_boost=attention_boost)
        
        return atoms_created
    
    def _create_temporal_relationships(self, context: ProcessedContext, context_uuid: str):
        """Create temporal relationships with other contexts"""
        # Find contexts with similar event times
        similar_contexts = self._find_temporally_related_contexts(context)
        
        for related_context_uuid, time_delta in similar_contexts:
            if time_delta > 0:  # This context comes after
                link_uuid = self.hypergraph.create_temporal_link(
                    related_context_uuid,
                    context_uuid,
                    time_delta=time_delta,
                    layer=0
                )
            else:  # This context comes before
                link_uuid = self.hypergraph.create_temporal_link(
                    context_uuid,
                    related_context_uuid,
                    time_delta=abs(time_delta),
                    layer=0
                )
    
    def _find_temporally_related_contexts(self, context: ProcessedContext, max_delta_hours: float = 24.0) -> List[tuple]:
        """Find contexts that are temporally related"""
        related = []
        
        # Get all context nodes
        context_nodes = self.hypergraph.get_atoms_by_type(AtomType.CONTEXT_NODE)
        
        for node in context_nodes:
            if node.context_id == context.id:
                continue
                
            # Get the stored context to compare times
            try:
                cursor = self.connection.cursor()
                cursor.execute("SELECT context_data FROM processed_contexts WHERE id = ?", (node.context_id,))
                row = cursor.fetchone()
                if row:
                    stored_context = ProcessedContext.from_json(row[0])
                    time_delta = (context.properties.event_time - stored_context.properties.event_time).total_seconds() / 3600.0
                    
                    if abs(time_delta) <= max_delta_hours:
                        related.append((node.uuid, time_delta))
                        
            except Exception as e:
                logger.warning(f"Failed to compare temporal relationship: {e}")
                continue
        
        return related
    
    def batch_upsert_processed_context(self, contexts: List[ProcessedContext]) -> List[str]:
        """Batch store processed contexts"""
        results = []
        for context in contexts:
            try:
                result = self.upsert_processed_context(context)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to store context {context.id}: {e}")
                results.append(None)
        return results
    
    def query(self, query: Vectorize, top_k: int = 5) -> List[ProcessedContext]:
        """Query processed contexts using hypergraph reasoning"""
        try:
            # For now, implement a simple query based on text similarity
            # In a full implementation, this would use hypergraph reasoning
            query_text = query.get_vectorize_content().lower()
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT id, context_data FROM processed_contexts")
            
            results = []
            for row in cursor.fetchall():
                context_id, context_data = row
                context = ProcessedContext.from_json(context_data)
                
                # Simple text matching for demonstration
                context_text = f"{context.extracted_data.title or ''} {context.extracted_data.summary or ''} {' '.join(context.extracted_data.keywords)}"
                
                if any(word in context_text.lower() for word in query_text.split()):
                    # Boost attention for accessed context
                    context_node = self.hypergraph.get_atom_by_name(context.extracted_data.title or f"Context_{context.id[:8]}")
                    if context_node:
                        self.hypergraph.propagate_attention(context_node.uuid, sti_boost=0.1)
                    
                    results.append(context)
                    
                    if len(results) >= top_k:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query contexts: {e}")
            return []
    
    def delete_processed_context(self, doc_id: str) -> bool:
        """Delete processed context and associated hypergraph atoms"""
        try:
            # Get associated atoms
            cursor = self.connection.cursor()
            cursor.execute("SELECT hypergraph_atoms FROM processed_contexts WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            
            if row:
                atom_uuids = json.loads(row[0])
                
                # Remove atoms from hypergraph
                for atom_uuid in atom_uuids:
                    if atom_uuid in self.hypergraph.atoms:
                        del self.hypergraph.atoms[atom_uuid]
                
                # Delete from database using parameterized queries
                cursor.execute("DELETE FROM processed_contexts WHERE id = ?", (doc_id,))
                placeholders = ','.join(['?'] * len(atom_uuids))
                cursor.execute(f"DELETE FROM atoms WHERE uuid IN ({placeholders})", atom_uuids)
                
                self.connection.commit()
                self._save_hypergraph(self.hypergraph)
                
                logger.debug(f"Deleted context {doc_id} and {len(atom_uuids)} associated atoms")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete context {doc_id}: {e}")
            return False
    
    def get_all_processed_contexts(self, limit: int = 100, offset: int = 0, filter: Dict[str, Any] = {}) -> List[ProcessedContext]:
        """Get all processed contexts with pagination"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT context_data FROM processed_contexts 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            contexts = []
            for row in cursor.fetchall():
                context = ProcessedContext.from_json(row[0])
                contexts.append(context)
            
            return contexts
            
        except Exception as e:
            logger.error(f"Failed to get all contexts: {e}")
            return []
    
    def get_hypergraph_statistics(self) -> Dict[str, Any]:
        """Get hypergraph statistics"""
        if not self.hypergraph:
            return {}
        
        stats = self.hypergraph.get_statistics()
        stats["storage_backend"] = "HypergraphStorage"
        stats["database_path"] = str(self.db_path)
        
        return stats
    
    def get_most_important_contexts(self, limit: int = 10) -> List[ProcessedContext]:
        """Get contexts with highest attention values"""
        try:
            important_atoms = self.hypergraph.get_most_important_atoms(limit)
            context_atoms = [atom for atom in important_atoms if atom.atom_type == AtomType.CONTEXT_NODE]
            
            contexts = []
            cursor = self.connection.cursor()
            
            for atom in context_atoms:
                if atom.context_id:
                    cursor.execute("SELECT context_data FROM processed_contexts WHERE id = ?", (atom.context_id,))
                    row = cursor.fetchone()
                    if row:
                        context = ProcessedContext.from_json(row[0])
                        contexts.append(context)
            
            return contexts
            
        except Exception as e:
            logger.error(f"Failed to get important contexts: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()