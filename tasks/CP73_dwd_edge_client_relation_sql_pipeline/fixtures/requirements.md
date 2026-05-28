# Edge-PP Client to PP Client Relation Requirements

## Background

In our graph database, we model relationships between "edge-PP clients" (peripheral/upstream clients) and "PP clients" (core platform clients). The data warehouse needs a DWD-layer processing script to materialize these relationships from raw ODS data.

## Source Tables

### ods_gu_user_gdb_edge (ODS layer - raw edge data)
| Column | Type | Description |
|--------|------|-------------|
| edge_id | STRING | Unique edge identifier |
| source_node | STRING | Source client node ID |
| target_node | STRING | Target client node ID |
| edge_type | STRING | Relation type (e.g. 'supply', 'purchase', 'affiliate') |
| weight | DOUBLE | Relation strength (0-1) |
| create_time | STRING | Edge creation timestamp (yyyy-MM-dd HH:mm:ss) |
| update_time | STRING | Last update timestamp |
| ds | STRING | Partition date (yyyyMMdd) |

### ods_gu_user_gdb_node (ODS layer - raw node data)
| Column | Type | Description |
|--------|------|-------------|
| node_id | STRING | Unique node identifier |
| node_type | STRING | 'pp_client' or 'edge_pp_client' |
| client_name | STRING | Display name |
| client_code | STRING | Business code |
| status | INT | 1=active, 0=inactive |
| region | STRING | Geographic region |
| json_value | STRING | Extended attributes (JSON string) |
| unx_value | BIGINT | Unix timestamp of last activity |
| ds | STRING | Partition date |

## Target Table

### dwd_gu_user_gdb_edge_client_to_meta (DWD layer)
| Column | Type | Description |
|--------|------|-------------|
| edge_id | STRING | FK to edge |
| source_client_code | STRING | Source client business code |
| source_client_name | STRING | Source client name |
| target_client_code | STRING | Target client business code |
| target_client_name | STRING | Target client name |
| edge_type | STRING | Relation type |
| weight | DOUBLE | Relation strength |
| source_region | STRING | Source client region |
| target_region | STRING | Target client region |
| source_status | INT | Source client status |
| target_status | INT | Target client status |
| recent_time | TIMESTAMP | Most recent of (edge update_time, source unx_value, target unx_value) |
| json_value | STRING | Merged JSON from both source and target nodes |
| unx_value | BIGINT | MAX of source and target unx_value |
| create_time | TIMESTAMP | Edge creation time |
| ds | STRING | Partition date |

## Processing Rules

1. JOIN edges with nodes on source_node = node_id AND target_node = node_id
2. Only include edges where BOTH source and target nodes exist
3. Filter: only edges where source node_type = 'edge_pp_client' AND target node_type = 'pp_client'
4. recent_time = MAX(edge.update_time, FROM_UNIXTIME(source.unx_value), FROM_UNIXTIME(target.unx_value))
5. json_value = merge of source.json_value and target.json_value (CONCAT as JSON array if both non-null)
6. unx_value = MAX(source.unx_value, target.unx_value)
7. Partition by ds, INSERT OVERWRITE

## Notes
- Use the latest partition (ds = '${bizdate}') for both source tables
- Handle NULL values in json_value and unx_value gracefully
- The recentTime field must be a proper TIMESTAMP, not a string
