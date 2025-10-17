# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenCog-inspired hypergraph models for multi-layer context representation
"""

import uuid
import datetime
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum
from pydantic import BaseModel, Field


class AtomType(Enum):
    """Types of atoms in the hypergraph, inspired by OpenCog AtomTypes"""
    # Basic structural atoms
    CONCEPT_NODE = "ConceptNode"
    PREDICATE_NODE = "PredicateNode"
    LINK = "Link"
    
    # Context-specific atoms
    CONTEXT_NODE = "ContextNode"
    ENTITY_NODE = "EntityNode"
    TEMPORAL_NODE = "TemporalNode"
    SPATIAL_NODE = "SpatialNode"
    
    # Relationship links
    INHERITANCE_LINK = "InheritanceLink"
    SIMILARITY_LINK = "SimilarityLink"
    ASSOCIATION_LINK = "AssociationLink"
    TEMPORAL_LINK = "TemporalLink"
    CAUSAL_LINK = "CausalLink"
    
    # Multi-layer links
    ABSTRACTION_LINK = "AbstractionLink"
    COMPOSITION_LINK = "CompositionLink"
    AGGREGATION_LINK = "AggregationLink"


class TruthValue(BaseModel):
    """Truth value representation for atoms"""
    strength: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    def __str__(self) -> str:
        return f"<{self.strength:.3f}, {self.confidence:.3f}>"


class AttentionValue(BaseModel):
    """Attention value for importance and resource allocation"""
    sti: float = Field(default=0.0, description="Short-term importance")
    lti: float = Field(default=0.0, description="Long-term importance") 
    vlti: bool = Field(default=False, description="Very long-term importance")


class Atom(BaseModel):
    """Base atom class representing nodes and links in the hypergraph"""
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    atom_type: AtomType
    name: Optional[str] = None
    truth_value: TruthValue = Field(default_factory=TruthValue)
    attention_value: AttentionValue = Field(default_factory=AttentionValue)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    
    # Context-specific metadata
    context_id: Optional[str] = None
    layer: int = Field(default=0, description="Abstraction layer in the hypergraph")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Node(Atom):
    """Node atom representing concepts, entities, or contexts"""
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.name is None:
            self.name = f"{self.atom_type.value}_{self.uuid[:8]}"


class Link(Atom):
    """Link atom representing relationships between other atoms"""
    outgoing: List[str] = Field(default_factory=list, description="UUIDs of connected atoms")
    arity: int = Field(default=2, description="Number of atoms this link connects")
    
    def __init__(self, **data):
        super().__init__(**data)
        self.arity = len(self.outgoing)
        if self.name is None:
            self.name = f"{self.atom_type.value}_{self.uuid[:8]}"


class ContextLayer(BaseModel):
    """Represents a layer in the multi-layer hypergraph"""
    layer_id: int
    name: str
    description: Optional[str] = None
    atoms: Set[str] = Field(default_factory=set, description="Atom UUIDs in this layer")
    parent_layers: Set[int] = Field(default_factory=set)
    child_layers: Set[int] = Field(default_factory=set)
    
    def add_atom(self, atom_uuid: str):
        """Add an atom to this layer"""
        self.atoms.add(atom_uuid)
    
    def remove_atom(self, atom_uuid: str):
        """Remove an atom from this layer"""
        self.atoms.discard(atom_uuid)


class HyperGraph(BaseModel):
    """Multi-layer hypergraph for context representation"""
    graph_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    
    # Storage for atoms
    atoms: Dict[str, Atom] = Field(default_factory=dict)
    
    # Layer management
    layers: Dict[int, ContextLayer] = Field(default_factory=dict)
    max_layer: int = 0
    
    # Indexing for fast lookups
    atoms_by_type: Dict[AtomType, Set[str]] = Field(default_factory=dict)
    atoms_by_name: Dict[str, str] = Field(default_factory=dict)
    links_by_outgoing: Dict[str, Set[str]] = Field(default_factory=dict)
    
    def add_atom(self, atom: Atom, layer: int = 0) -> str:
        """Add an atom to the hypergraph"""
        self.atoms[atom.uuid] = atom
        atom.layer = layer
        
        # Update indexes
        if atom.atom_type not in self.atoms_by_type:
            self.atoms_by_type[atom.atom_type] = set()
        self.atoms_by_type[atom.atom_type].add(atom.uuid)
        
        if atom.name:
            self.atoms_by_name[atom.name] = atom.uuid
        
        # Update layer
        if layer not in self.layers:
            self.layers[layer] = ContextLayer(layer_id=layer, name=f"Layer_{layer}")
        self.layers[layer].add_atom(atom.uuid)
        self.max_layer = max(self.max_layer, layer)
        
        # Handle links
        if isinstance(atom, Link):
            for outgoing_uuid in atom.outgoing:
                if outgoing_uuid not in self.links_by_outgoing:
                    self.links_by_outgoing[outgoing_uuid] = set()
                self.links_by_outgoing[outgoing_uuid].add(atom.uuid)
        
        self.updated_at = datetime.datetime.now()
        return atom.uuid
    
    def get_atom(self, atom_uuid: str) -> Optional[Atom]:
        """Get an atom by UUID"""
        return self.atoms.get(atom_uuid)
    
    def get_atom_by_name(self, name: str) -> Optional[Atom]:
        """Get an atom by name"""
        atom_uuid = self.atoms_by_name.get(name)
        if atom_uuid:
            return self.atoms.get(atom_uuid)
        return None
    
    def get_atoms_by_type(self, atom_type: AtomType) -> List[Atom]:
        """Get all atoms of a specific type"""
        atom_uuids = self.atoms_by_type.get(atom_type, set())
        return [self.atoms[uuid] for uuid in atom_uuids if uuid in self.atoms]
    
    def get_incoming_links(self, atom_uuid: str) -> List[Link]:
        """Get all links that point to this atom"""
        link_uuids = self.links_by_outgoing.get(atom_uuid, set())
        return [self.atoms[uuid] for uuid in link_uuids if uuid in self.atoms and isinstance(self.atoms[uuid], Link)]
    
    def get_layer_atoms(self, layer: int) -> List[Atom]:
        """Get all atoms in a specific layer"""
        if layer not in self.layers:
            return []
        atom_uuids = self.layers[layer].atoms
        return [self.atoms[uuid] for uuid in atom_uuids if uuid in self.atoms]
    
    def create_context_node(self, context_id: str, name: str, properties: Dict[str, Any] = None, layer: int = 0) -> str:
        """Create a context node"""
        node = Node(
            atom_type=AtomType.CONTEXT_NODE,
            name=name,
            context_id=context_id,
            properties=properties or {}
        )
        return self.add_atom(node, layer)
    
    def create_entity_node(self, entity_name: str, entity_type: str = "Entity", properties: Dict[str, Any] = None, layer: int = 0) -> str:
        """Create an entity node"""
        node = Node(
            atom_type=AtomType.ENTITY_NODE,
            name=entity_name,
            properties={
                "entity_type": entity_type,
                **(properties or {})
            }
        )
        return self.add_atom(node, layer)
    
    def create_association_link(self, atom1_uuid: str, atom2_uuid: str, strength: float = 0.5, layer: int = 0) -> str:
        """Create an association link between two atoms"""
        link = Link(
            atom_type=AtomType.ASSOCIATION_LINK,
            outgoing=[atom1_uuid, atom2_uuid],
            truth_value=TruthValue(strength=strength)
        )
        return self.add_atom(link, layer)
    
    def create_temporal_link(self, before_uuid: str, after_uuid: str, time_delta: Optional[float] = None, layer: int = 0) -> str:
        """Create a temporal link indicating sequence"""
        metadata = {}
        if time_delta is not None:
            metadata["time_delta"] = time_delta
            
        link = Link(
            atom_type=AtomType.TEMPORAL_LINK,
            outgoing=[before_uuid, after_uuid],
            metadata=metadata
        )
        return self.add_atom(link, layer)
    
    def create_abstraction_link(self, concrete_uuid: str, abstract_uuid: str, abstraction_level: int = 1, layer: int = 0) -> str:
        """Create an abstraction link from concrete to abstract concept"""
        link = Link(
            atom_type=AtomType.ABSTRACTION_LINK,
            outgoing=[concrete_uuid, abstract_uuid],
            metadata={"abstraction_level": abstraction_level}
        )
        return self.add_atom(link, layer)
    
    def propagate_attention(self, atom_uuid: str, sti_boost: float = 0.1, decay_factor: float = 0.9):
        """Propagate attention through the hypergraph"""
        atom = self.get_atom(atom_uuid)
        if not atom:
            return
            
        # Boost the target atom's attention
        atom.attention_value.sti += sti_boost
        
        # Propagate to connected atoms
        incoming_links = self.get_incoming_links(atom_uuid)
        for link in incoming_links:
            for connected_uuid in link.outgoing:
                if connected_uuid != atom_uuid:
                    connected_atom = self.get_atom(connected_uuid)
                    if connected_atom:
                        connected_atom.attention_value.sti += sti_boost * decay_factor
    
    def get_most_important_atoms(self, limit: int = 10) -> List[Atom]:
        """Get atoms with highest attention values"""
        all_atoms = list(self.atoms.values())
        all_atoms.sort(key=lambda a: a.attention_value.sti, reverse=True)
        return all_atoms[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hypergraph statistics"""
        stats = {
            "total_atoms": len(self.atoms),
            "total_layers": len(self.layers),
            "max_layer": self.max_layer,
            "atoms_by_type": {atom_type.value: len(uuids) for atom_type, uuids in self.atoms_by_type.items()},
            "atoms_by_layer": {layer_id: len(layer.atoms) for layer_id, layer in self.layers.items()}
        }
        return stats