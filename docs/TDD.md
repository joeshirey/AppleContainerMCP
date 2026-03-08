# **Technical Design Document: Apple Container MCP Server**

## **1\. Architecture Overview**

The solution is built as a Python-based MCP server using the FastMCP framework. It communicates with the host macOS system via the container binary using the subprocess module.

### **Components**

1. **MCP Host (e.g., Claude Desktop):** The user interface.  
2. **MCP Server:** The Python process orchestrating tools and logic.  
3. **Apple Container CLI:** The container binary (installed via Apple’s open-source project).  
4. **XPC Interface:** The underlying communication channel between the CLI and the container-apiserver daemon.

## **2\. Technical Stack**

* **Language:** Python 3.11+  
* **Framework:** mcp / fastmcp  
* **Communication:** Standard I/O (stdio)  
* **Serialization:** JSON (native container output)

## **3\. Tool Implementation Details**

### **A. The Execution Wrapper**

To ensure consistency, all tools will use a shared private method \_run\_container\_cmd(args).

def _run_container_cmd(args: List[str]) -> Any:
    full_cmd = ["container"] + args
    FORMAT_JSON_COMMANDS = {"ls"}
    if "--format" not in full_cmd and (len(args) > 0 and args[0] in FORMAT_JSON_COMMANDS):
        full_cmd.extend(["--format", "json"])

    try:
        process = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
        stdout = process.stdout.strip()
        if not stdout:
            return {}
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            if args[0] in FORMAT_JSON_COMMANDS or args[0] == "inspect":
                return {"raw_output": stdout, "error": "Failed to parse JSON output"}
            return {"raw_output": stdout}
    except subprocess.CalledProcessError as e:
        # Check for daemon connection issues
        stderr_msg = e.stderr.strip().lower()
        if "connection refused" in stderr_msg:
             raise ContainerCLIError("Daemon not running", ...)
        raise ContainerCLIError(f"Command failed", ...)

### **B. Tool Mapping Strategy**

| MCP Tool Name | CLI Command Equivalent | Logic Notes |
| :---- | :---- | :---- |
| list_containers | container ls -a | Parse JSON array, return count and names. |
| run_container | container run ... | Map memory, cpus, ports, env, and volumes arguments to flags. |
| get_logs | container logs -n [limit] [id] | Use native `-n` flag instead of `--tail`. |
| system_status | container system status | Check if daemon is active. |

## **4\. Error Handling & Edge Cases**

1. **Daemon Not Running:** If a command fails with "connection refused," the server should return a specific error message suggesting the user run the start\_system tool.  
2. **Long-Running Builds:** container build blocks the process.  
   * *Solution:* Execute build in a separate thread. The tool returns a "Build Started" message immediately.  
   * *State Management:* Maintain an in-memory dictionary of active build IDs to track progress.  
3. **Large Log Files:** Avoid sending MBs of text back to the LLM.  
   * *Solution:* Implement a limit parameter (default 100 lines).

## **5\. Security Model**

* **Local Execution:** The MCP server only accepts requests from the local MCP Host.  
* **Path Validation:** For build commands, validate that the provided directory path exists and is within allowed user directories.  
* **Argument Sanitization:** Use subprocess.run with a list of arguments to prevent shell injection.

## **6\. Deployment Plan**

1. **Pre-requisite:** User must have the Apple container package installed.  
2. **Configuration:** Update claude\_desktop\_config.json:  
   {  
     "mcpServers": {  
       "apple\_container": {  
         "command": "python3",  
         "args": \["/path/to/server.py"\]  
       }  
     }  
   }

## **7\. Future Considerations**

* **Streamed Logs:** Support for MCP resources to provide real-time log updates.  
* **Virtualization Framework Integration:** Direct inspection of the Virtualization.framework state if the CLI is insufficient.