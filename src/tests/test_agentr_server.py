import pytest
from agentr.server import AgentRServer
from loguru import logger

@pytest.mark.asyncio
@pytest.mark.skip(reason="This test is not completed yet")
async def test_load_agentr_server():
    # Test with invalid API key
    # Test with valid API key
    server = AgentRServer(
        name="Test Server", 
        description="Test Server", 
    )
    assert server.name == "Test Server"
    tools = await server.list_tools()
    logger.info(tools)
    assert len(tools) > 0
    result = await server.call_tool("star_repository", {"repo_full_name": "agentr-dev/agentr"})
    logger.info(result)
    assert result is not None
