# OpenCog Multi-Layer Context Hypergraph Implementation

This document describes the OpenCog-inspired multi-layer context hypergraph implementation in MineContext.

## Overview

The hypergraph implementation provides an advanced context representation system inspired by OpenCog's AtomSpace, enabling sophisticated relationship modeling and reasoning capabilities for context data.

## Key Features

### 1. Multi-Layer Architecture
- **Layer 0**: Raw context nodes (direct user interactions, screenshots, documents)
- **Layer 1**: Entity and concept extraction 
- **Layer 2**: Abstract concepts and high-level relationships
- **Layer N**: Higher-order abstractions and meta-relationships

### 2. OpenCog-Inspired Atom Types

#### Node Types
- `CONTEXT_NODE`: Represents individual context instances
- `ENTITY_NODE`: Represents extracted entities (people, places, concepts)
- `CONCEPT_NODE`: Represents abstract concepts and keywords
- `TEMPORAL_NODE`: Represents time-based information
- `SPATIAL_NODE`: Represents location-based information

#### Link Types
- `ASSOCIATION_LINK`: General associative relationships
- `INHERITANCE_LINK`: Hierarchical relationships (is-a)
- `SIMILARITY_LINK`: Similarity relationships
- `TEMPORAL_LINK`: Time-based sequence relationships
- `CAUSAL_LINK`: Cause-and-effect relationships
- `ABSTRACTION_LINK`: Concrete-to-abstract relationships
- `COMPOSITION_LINK`: Part-whole relationships

### 3. Truth Values and Attention
- **Truth Values**: Each atom has strength (0.0-1.0) and confidence (0.0-1.0) values
- **Attention Values**: Short-term importance (STI), long-term importance (LTI), and very long-term importance (VLTI)
- **Attention Propagation**: Automatically spreads importance through the network

## Architecture

```
MineContext HyperGraph
├── Storage Backend (SQLite + In-Memory)
├── Multi-Layer Structure
│   ├── Layer 0: Raw Contexts
│   ├── Layer 1: Entities & Concepts  
│   ├── Layer 2: Abstract Relationships
│   └── Layer N: Meta-Abstractions
├── Atom Management
│   ├── Node Creation & Indexing
│   ├── Link Creation & Tracking
│   └── Attention Propagation
└── Query & Reasoning
    ├── Pattern Matching
    ├── Similarity Search
    └── Temporal Reasoning
```

## Configuration

Add the hypergraph backend to your `config/config.yaml`:

```yaml
storage:
  enabled: true
  backends:
    - name: "hypergraph_vector"
      storage_type: "vector_db"
      backend: "hypergraph"
      config:
        storage_path: "${CONTEXT_PATH:.}/persist/hypergraph/hypergraph.db"
        hypergraph_name: "MineContext_HyperGraph"
```

## Usage Examples

### 1. Basic Hypergraph Operations

```python
from opencontext.models.hypergraph import HyperGraph, AtomType

# Create a hypergraph
hg = HyperGraph(name="MyGraph", description="Context hypergraph")

# Create context nodes
ctx1 = hg.create_context_node("ctx1", "User reading AI paper", layer=0)
ctx2 = hg.create_context_node("ctx2", "User writing code", layer=0)

# Create entity nodes
ai_entity = hg.create_entity_node("Artificial Intelligence", "Concept", layer=1)
coding_entity = hg.create_entity_node("Programming", "Activity", layer=1)

# Create relationships
hg.create_association_link(ctx1, ai_entity, strength=0.8, layer=1)
hg.create_temporal_link(ctx1, ctx2, time_delta=3600, layer=0)  # 1 hour later
```

### 2. Using the Storage Backend

```python
from opencontext.storage.backends.hypergraph_backend import HypergraphStorage
from opencontext.models.context import ProcessedContext

# Initialize storage
storage = HypergraphStorage()
config = {
    "storage_path": "data/hypergraph.db",
    "hypergraph_name": "MyHyperGraph"
}
storage.initialize(config)

# Store context (automatically creates hypergraph representation)
context_id = storage.upsert_processed_context(processed_context)

# Query contexts
results = storage.query(query_vectorize, top_k=5)

# Get hypergraph statistics
stats = storage.get_hypergraph_statistics()
print(f"Total atoms: {stats['total_atoms']}")
print(f"Layers: {stats['total_layers']}")
```

### 3. Attention-Based Importance

```python
# Propagate attention from important context
hg.propagate_attention(important_context_uuid, sti_boost=0.3)

# Get most important contexts
important_atoms = hg.get_most_important_atoms(limit=10)
important_contexts = storage.get_most_important_contexts(limit=5)
```

## Multi-Layer Context Representation

### Layer 0: Raw Context
- Direct user interactions (screenshots, documents, conversations)
- Temporal sequence of events
- Raw sensory data and observations

### Layer 1: Extracted Information
- Named entities (people, places, organizations)
- Keywords and concepts
- Basic relationships and associations

### Layer 2: Abstract Concepts
- High-level themes and patterns
- Conceptual relationships
- Domain-specific knowledge

### Layer N: Meta-Relationships
- Cross-domain connections
- Emergent patterns and insights
- Strategic-level understanding

## Benefits

1. **Rich Relationship Modeling**: Captures complex multi-way relationships between contexts
2. **Temporal Reasoning**: Understands sequence and causality in context streams
3. **Attention-Based Importance**: Automatically identifies and prioritizes important information
4. **Multi-Scale Abstraction**: Represents context at multiple levels of detail
5. **Reasoning Capabilities**: Enables inference and pattern discovery
6. **Scalable Architecture**: Efficient storage and retrieval of large context graphs

## Integration with MineContext

The hypergraph backend integrates seamlessly with the existing MineContext architecture:

- **Backwards Compatible**: Existing storage backends continue to work
- **Unified Interface**: Uses the same `IContextStorage` interface
- **Configurable**: Can be enabled/disabled via configuration
- **Performance Optimized**: Efficient indexing and caching for fast queries

## Future Enhancements

1. **Advanced Reasoning**: Implement PLN (Probabilistic Logic Networks) for inference
2. **Pattern Mining**: Discover recurring patterns in context streams
3. **Predictive Modeling**: Predict future contexts based on historical patterns
4. **Distributed Processing**: Scale across multiple nodes for large datasets
5. **Visualization**: Interactive hypergraph visualization tools

## Testing

Run the validation tests:

```bash
python test_hypergraph.py
```

This will validate:
- Hypergraph data models
- Storage backend functionality  
- Multi-layer context representation
- Attention propagation
- Temporal relationship creation

## Conclusion

The OpenCog-inspired hypergraph implementation provides MineContext with advanced context modeling capabilities, enabling sophisticated reasoning and relationship discovery in context data streams.