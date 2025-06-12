#!/usr/bin/env python3
"""
Apple Watch Health Data MCP Server
A Model Context Protocol server for querying Apple HealthKit step data stored in Elasticsearch.

Author: Alex Salgado
"""

from typing import Any, Optional
import json
from datetime import datetime
from pydantic import BaseModel, field_validator, ValidationError
from mcp.server.fastmcp import FastMCP
from elasticsearch import AsyncElasticsearch
from contextlib import asynccontextmanager

# Initialize FastMCP server
mcp = FastMCP("apple-watch-steps")

# Constants
ES_HOST = "http://localhost:9200"
ES_INDEX = "apple-health-steps"


# Pydantic model for parameter validation
class QueryStepDataParams(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    aggregation: Optional[str] = None
    device: Optional[str] = None
    
    @field_validator('start_date', 'end_date')
    def validate_date_format(cls, value):
        if value is None:
            return value
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
    
    @field_validator('aggregation')
    def validate_aggregation(cls, value):
        valid_aggregations = ["hourly", "daily", "weekly", "monthly", None]
        if value not in valid_aggregations:
            raise ValueError(f"Invalid aggregation. Use one of: {valid_aggregations[:-1]}")
        return value

@asynccontextmanager
async def get_es_client():
    """Context manager for Elasticsearch client."""
    client = AsyncElasticsearch([ES_HOST])
    try:
        yield client
    finally:
        await client.close()

# Elasticsearch helper function
async def query_elasticsearch(query: dict) -> dict[str, Any] | None:
    """Makes a request to Elasticsearch with proper error handling."""
    print(f"Sending query to Elasticsearch: {json.dumps(query)}")
    
    # Use context manager
    async with get_es_client() as client:
        try:
            response = await client.search(
                index=ES_INDEX,
                body=query
            )
            return response
        except Exception as e:
            print(f"Error querying Elasticsearch: {e}")
            return None


# Resources
@mcp.resource("health://steps/types")
async def list_step_types() -> str:
    """List all available step types in the database"""
    query = {
        "size": 0,
        "aggs": {
            "step_types": {
                "terms": {
                    "field": "type",
                    "size": 100
                }
            }
        }
    }
    
    data = await query_elasticsearch(query)
    if not data:
        return json.dumps({"error": "Unable to query Elasticsearch"}, indent=2)
    
    step_types = [bucket["key"] for bucket in data["aggregations"]["step_types"]["buckets"]]
    
    return json.dumps({
        "available_types": step_types,
        "count": len(step_types)
    }, indent=2)

@mcp.resource("health://steps/latest")
async def get_latest_steps() -> str:
    """Gets the most recent step records"""
    query = {
        "query": {
            "match_all": {}
        },
        "sort": [
            {"endDate": {"order": "desc"}}
        ],
        "size": 10
    }
    
    data = await query_elasticsearch(query)
    if not data:
        return json.dumps({"error": "Unable to query Elasticsearch"}, indent=2)
    
    results = []
    for hit in data["hits"]["hits"]:
        source = hit["_source"]
        results.append({
            "startDate": source.get("startDate"),
            "endDate": source.get("endDate"),
            "value": source.get("value"),
            "device": source.get("device"),
            "sourceName": source.get("sourceName"),
            "dayOfWeek": source.get("dayOfWeek"),
            "hour": source.get("hour")
        })
    
    return json.dumps({
        "latest_steps": results
    }, indent=2)

@mcp.resource("health://steps/summary")
async def get_steps_summary() -> str:
    """Get summary statistics for step counts"""
    query = {
        "aggs": {
            "all_time": {
                "stats": {
                    "field": "value"
                }
            }
        },
        "size": 0
    }
    
    data = await query_elasticsearch(query)
    if not data:
        return json.dumps({"error": "Unable to query Elasticsearch"}, indent=2)
    
    return json.dumps(data["aggregations"], indent=2)

# Tools
@mcp.tool()
async def query_step_data(params: QueryStepDataParams) -> str:
    """
    Query step data with customizable parameters
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        aggregation: Aggregation interval (hourly, daily, weekly, monthly)
        device: Filter by specific device name
    """
    # Extract parameters from model
    start_date = params.start_date or ""
    end_date = params.end_date or ""
    aggregation = params.aggregation or ""
    device = params.device or ""
    
    query = {"query": {"match_all": {}}}
    filters = []
    
    # Date filters
    date_ranges = []
    if start_date:
        date_ranges.append({"gte": start_date})
    if end_date:
        date_ranges.append({"lte": end_date})
    
    if date_ranges:
        filters.append({
            "range": {
                "day": {**{k: v for d in date_ranges for k, v in d.items()}}
            }
        })
    
    # Device filter
    if device:
        filters.append({
            "wildcard": {
                "device": f"*{device}*"
            }
        })
    
    if filters:
        query["query"] = {"bool": {"must": filters}}
    
    # Aggregation handling
    if aggregation:
        interval_mapping = {
            "hourly": "1h",
            "daily": "1d", 
            "weekly": "1w",
            "monthly": "1M"
        }
        interval = interval_mapping.get(aggregation, "1d")
        date_field = "startDate" if aggregation == "hourly" else "day"
        
        query["aggs"] = {
            "time_series": {
                "date_histogram": {
                    "field": date_field,
                    "calendar_interval": interval,
                    "min_doc_count": 0
                },
                "aggs": {
                    "total_steps": {"sum": {"field": "value"}},
                    "avg_steps": {"avg": {"field": "value"}},
                    "max_steps": {"max": {"field": "value"}},
                    "min_steps": {"min": {"field": "value"}}
                }
            }
        }
        query["size"] = 0
    else:
        query.update({
            "sort": [{"startDate": "desc"}],
            "size": 10
        })
    
    data = await query_elasticsearch(query)
    if not data:
        return json.dumps({
            "error": "Unable to query Elasticsearch",
            "query": query
        }, indent=2)
    
    # Process results
    results = []
    if aggregation and "time_series" in data.get("aggregations", {}):
        for bucket in data["aggregations"]["time_series"]["buckets"]:
            results.append({
                "date": bucket["key_as_string"],
                "total_steps": bucket["total_steps"]["value"],
                "average_steps": bucket["avg_steps"]["value"],
                "max_steps": bucket["max_steps"]["value"],
                "min_steps": bucket["min_steps"]["value"],
                "records": bucket["doc_count"]
            })
    else:
        for hit in data["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "startDate": source.get("startDate"),
                "endDate": source.get("endDate"),
                "day": source.get("day"),
                "dayOfWeek": source.get("dayOfWeek"),
                "hour": source.get("hour"),
                "value": source.get("value"),
                "device": source.get("device"),
                "sourceName": source.get("sourceName")
            })
    
    return json.dumps({
        "aggregation": aggregation,
        "total_records": data["hits"]["total"]["value"],
        "data": results,
        "query": query
    }, indent=2)

@mcp.tool()
async def get_all_steps() -> str:
    """Get all steps without any filtering"""
    query = {
        "query": {
            "match_all": {}
        },
        "size": 10,
        "sort": [{"startDate": "desc"}]
    }
    
    data = await query_elasticsearch(query)
    if not data:
        return json.dumps({"error": "Unable to query Elasticsearch"}, indent=2)
    
    results = []
    for hit in data["hits"]["hits"]:
        source = hit["_source"]
        results.append({
            "startDate": source.get("startDate"),
            "value": source.get("value"),
            "device": source.get("device")
        })
    
    return json.dumps({
        "total_records": data["hits"]["total"]["value"],
        "data": results
    })

# Prompts
@mcp.prompt()
def daily_report(date: str = None) -> str:
    """Create a daily step report for a specific date"""
    if date:
        return f"""Please analyze the step data for {date}. Provide:
1. Total steps
2. Average steps per active hour
3. Most active periods of the day
4. Comparison with weekly average
5. Graphical visualization of the data, if possible"""
    else:
        return """Please analyze the step data for today. Provide:
1. Total steps so far
2. Average steps per active hour
3. Most active periods of the day
4. Comparison with weekly average
5. Graphical visualization of the data, if possible"""

@mcp.prompt()
def trend_analysis(start_date: str, end_date: str) -> str:
    """Analyze step trends over a specific period"""
    return f"""Analyze step trends between {start_date} and {end_date}.
Please include:
1. Daily step trend graph
2. Identification of weekly patterns
3. Days with highest and lowest activity
4. Progression over time
5. Recommendations based on the data"""

@mcp.prompt()
def device_comparison() -> str:
    """Compare step data recorded by different devices"""
    return """Compare step data recorded by Apple Watch and iPhone:
1. Which device records more steps on average?
2. Are there notable differences in usage patterns?
3. Times when each device is used more
4. Apparent accuracy of each device
5. Recommendations on which device to prioritize for tracking"""

# Main function to run the server
if __name__ == "__main__":
    mcp.run()