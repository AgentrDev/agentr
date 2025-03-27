from agentr.server import AgentRServer

mcp = AgentRServer(name="AgentR Server", description="AgentR Server", port=8005)


if __name__ == "__main__":
    mcp.run(transport="sse")