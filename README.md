# MCP Server for Apple Health Data with Elasticsearch - Starter Project

Welcome! This repository contains the complete and final source code for the blog post, "Unlock Your LLM's Potential: Building an MCP Server with Elasticsearch for Real Health Data".

This project provides a runnable implementation of a custom Model Context Protocol (MCP) server. Built with Python and the FastMCP framework, this server connects to an Elasticsearch index containing sample Apple HealthKit step data. This setup allows an LLM client like Claude to query personal health data using natural language.

## Prerequisites

Before you begin, ensure you have the following installed and running:

* **Python 3.10+**
* **Elasticsearch**: An instance of Elasticsearch 8.x running locally at `http://localhost:9200`.
* **Claude Desktop**: The MCP client we will use to interact with the server.
* **uv** : For managing Python packages.

## Getting Started

Follow these steps to set up your local environment and install the necessary dependencies.

### 1. Navigate to Your Project Directory

Open your terminal or command prompt and navigate to the project folder.
```shell
cd path/to/your/folder/apple-watch-health-mcp
```

### 2. Initialize the Python Project

This step creates the `pyproject.toml` file, which `uv` uses to manage your project's dependencies.
```shell
uv init
```

### 3. Create and Activate a Virtual Environment

```shell
# Create the virtual environment
uv venv

# Activate the environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 4. Install Dependencies

Install the necessary Python packages. Note that we are specifying a compatible version for the `elasticsearch` library to match the v8.x server used in this tutorial.
```shell
uv add "mcp[cli]" "elasticsearch>=8.0.0,<9.0.0" aiohttp pydantic

```

## Environment Configuration

### Setting up the API Key

After creating the API key in Elasticsearch, you need to configure it in your environment:

```bash
# Export the API key for the current session
export ES_API_KEY="your_encoded_api_key_here"
```

## Usage Instructions

With the environment set up, you can now run the solution.


### 1. Ingest the Sample Data

First, run the provided script to populate your Elasticsearch instance with the sample data. This script will create the index with the correct mapping and insert the 30 sample documents.
```shell
python ingest_data.py
```
You should see output confirming that the documents were ingested successfully.

### 2. Test the Server with MCP Inspector

Before installing in Claude, you can verify that the server is working correctly using the MCP Inspector tool.
```shell
mcp dev apple_watch_mcp.py
``` 

This will open a web interface where you can interactively test the server's resources, tools, and prompts.

### 3. Install and Use in Claude

This is the final step to connect your MCP server to the Claude Desktop client.

1.  **Install the server**: Run this command in your terminal.
    ```shell
    mcp install apple_watch_mcp.py --name "Apple Health Steps"
    ```
    This command registers the server in Claude Desktop's configuration file.

    Run the command below to view the contents of this file. 
    
    ```shell

        cat ~/Library/Application\ Support/Claude/claude_desktop_config.json  
    
    ```

You should see a structure similar to this inside the file, under the "mcpServers" key: 

 ```shell 

{
  "mcpServers": {
    "Apple Health Steps": {
      "command": "/full/path/to/your/uv",
      "args": [
        "--directory",
        "/path/to/repository/apple-watch-health-mcp",
        "run",
        "apple_watch_mcp.py"
        // Other arguments may appear depending on your setup
      ]
    }
    // ... other servers might be listed here
  }
}

 ``` 


2.  **Restart Claude Desktop**: You **must** close and reopen the Claude Desktop application for it to load the new server configuration.

3.  **Start Chatting**: Once restarted, Claude will automatically run your MCP server in the background. You can now ask it questions about your health data in natural language. Try these examples from the blog post:
    * "What was my most active day this week?" 
    * "Compare my activity between Apple Watch and iPhone"
    * Or use the built-in slash commands like `/daily_report` or `/trend_analysis`.

## File Descriptions

* `apple_watch_mcp.py`: The **complete and final script** for the MCP server, containing all implemented Resources, Tools, and Prompts.
* `ingest_data.py`: A helper script that populates your Elasticsearch instance with the sample data.
* `sample_data.json`: A JSON file containing fictitious Apple Health step count data for testing.
* `README.md`: This file, providing instructions to run the complete solution.
