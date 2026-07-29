# **Product Requirements Document: Apple Container MCP Server**

## **1\. Executive Summary**

The **Apple Container MCP Server** is a bridge between the Model Context Protocol (MCP) and Apple's open-source container CLI. It enables users to manage lightweight macOS-native containers using natural language via LLMs (like Claude, Cursor, or ChatGPT), abstracting away the complexity of specific CLI flags and system-level configurations.

The same package ships a second, independent deliverable: **`d2c`**, a Docker-to-Apple-Container command translator for the terminal. It serves users who want to keep their existing Docker habits and scripts rather than converse with an LLM. The two share a target CLI but no runtime code path.

## **2\. Problem Statement**

Apple's new container service is powerful but requires familiarity with a specific CLI syntax and a background daemon (container-apiserver). Users often struggle with:

* Remembering resource allocation flags (CPUs, memory).  
* Correctly formatting network and mount mappings.  
* Checking the status of the background service before running commands.  
* Interpreting raw terminal table outputs.

A second, distinct problem motivates `d2c`: users arriving from Docker have years of muscle memory and a drawer full of shell scripts. Apple Container renames commands (`docker rmi` is `container image delete`), drops others outright (`docker compose` has no counterpart), and rejects global flags that assume a remote daemon. Discovering each mismatch through a failed command is slow and, for the dropped commands, tells the user nothing about what to do instead.

## **3\. Goals & Objectives**

* **Accessibility:** Allow users to say "Run a Debian container with 4GB RAM" instead of typing container run \--memory 4g debian.  
* **Automation:** Enable LLMs to inspect the current state of containers and perform corrective actions (e.g., restarting a failed container).  
* **Safety:** Validate commands before execution to prevent system resource exhaustion.  
* **Transparency:** Provide structured JSON data to the LLM so it can provide meaningful status summaries to the user.

## **4\. User Personas**

* **The Developer:** Wants to quickly spin up testing environments without leaving their IDE.  
* **The System Admin:** Needs to audit running containers and system resource usage via a conversational interface.  
* **The AI Agent:** Needs a programmatic way to deploy and manage containerized services on macOS hardware.

## **5\. Functional Requirements (Tools)**

The MCP server must expose the following capabilities as "Tools":

### **FR1: System Management**

* Check if container-apiserver is running.  
* Start/Stop the system service.  
* Retrieve system-wide info (version, driver status).
* Retrieve detailed version information for the CLI and apiserver daemon (works without the daemon running; useful as a lightweight environment probe). Requires Apple Container 0.12+.
* Report disk usage across images, containers, and volumes, including how much is reclaimable, so cleanup decisions are informed rather than blind.
* Read logs from the `container` system services themselves, for diagnosing a daemon that will not start or containers that fail before producing any output of their own.

### **FR2: Container Lifecycle**

* **Run:** Start a container from an image with resource constraints, port forwarding, env variables, network, volume mounts, and initialization images.  
* **List:** View running and stopped containers.  
* **Start:** Start a stopped container.
* **Stop/Kill:** Gracefully or forcefully terminate containers.  
* **Remove:** Clean up container resources.
* **Export:** Export a container's filesystem as a tar archive (requires an output file path).
* **Prune:** Remove stopped containers to reclaim disk space.

### **FR3: Image Management**

* **Pull:** Download images from registries.  
* **Build:** Build images from local contexts (supports tags and secrets).  
* **List Images:** View available local images.
* **Remove Image:** Delete a single image from local storage.
* **Prune Images:** Remove unused or dangling images.
* **Tag:** Tag a local image with a new name/tag.
* **Push:** Push a local image to a container registry.

### **FR4: Network & Volume Management**

* **Networks:** Create (with optional subnet and MTU), list, inspect, remove, and prune networks.
* **Volumes:** Create (with optional size), list, inspect, remove, and prune volumes.

### **FR5: Inspection & Logs**

* **Logs:** Fetch recent stdout/stderr from a specific container.  
* **Inspect:** Get detailed low-level configuration of a container.
* **Exec:** Run a command inside a running container.
* **Stats:** Get a one-shot resource-usage snapshot for one or more containers (always non-streaming to fit the request/response model). Requires Apple Container 0.12+.

### **FR6: Registry & Builder Management**

* **Registry:** Login/Logout from container registries.
* **Builder:** Start, stop, and check status of the image builder.

### **FR7: Guided Workflows (Prompts)**

* **Troubleshoot:** Guided workflow for failing containers.
* **Build & Run:** Guided workflow for building and running local projects.
* **Cleanup:** Guided workflow for environment cleanup.
* **Registry Setup:** Guided workflow for private registry authentication.

## **5b\. Functional Requirements (`d2c` CLI)**

`d2c` is a separate console script (`d2c = "d2c.cli:main"`) with no dependency on the MCP server. Requirements are numbered separately because it is a separate deliverable.

### **DR1: Command Translation**

* Accept a Docker CLI invocation and run the Apple Container equivalent, forwarding the translated command's exit code so the tool composes in scripts and CI.
* Cover the commands that have a genuine counterpart: container lifecycle, image management, registry authentication, and the network / volume / system / image / builder management groups.
* Strip Docker's management namespace, so `docker container run` and `docker run` resolve identically.
* Attach an explanatory note where a mapping would otherwise surprise the user (for example `rmi` → `image delete`).

### **DR2: Preview Before Execution**

* A `--dry-run` flag must print the translation and exit without touching the system, so a user can check an unfamiliar command before trusting it.

### **DR3: Refuse Unsupported Commands With a Hint**

* Commands Apple Container does not implement must be rejected by `d2c` itself, before invoking the CLI, with a suggested alternative. Failing at the `container` binary would produce an error that neither names the real problem nor offers a path forward.
* Coverage includes the Docker Swarm family, orchestration (`compose`), image operations Apple Container lacks (`commit`, `import`, `history`, `manifest`, `search`), and lifecycle gaps (`pause`, `restart`, `rename`, `attach`, and others).

### **DR4: Handle Docker Global Flags Safely**

* Flags with a direct counterpart (`--debug` / `-D`) translate and are inserted ahead of the subcommand.
* Flags premised on capabilities Apple Container does not have — remote daemons, context switching, TLS configuration — must warn, explain why, and require explicit confirmation before proceeding.
* The confirmation must default to "no" and treat a closed stdin as "no", so a non-interactive script inheriting a stale flag halts rather than silently running against unintended settings.
* Only flags preceding the first positional argument count as global, so short flags reused by subcommands (`exec … bash -c "…"`) are left alone.

## **6\. Non-Functional Requirements**

* **Latency:** Tool execution should return within 2 seconds for standard CLI calls.  
* **Security:** The server must run with the user's permissions; it should not escalate to sudo unless explicitly configured by the user.  
* **Format:** Internal CLI communication should use \--format json where supported by the underlying Apple CLI to ensure data integrity, gracefully falling back to raw output parsing for commands that do not support it.

## **7\. Success Metrics**

* **Completion Rate:** Users successfully start a container on the first natural language attempt.  
* **Error Reduction:** Decrease in "Command Not Found" or "Invalid Argument" errors compared to manual CLI usage.
