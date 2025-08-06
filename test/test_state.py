import os
import pytest
import yaml
import shutil
import asyncio
import tempfile
from filelock import Timeout
import sys

# Add parent directory to sys.path so huntbot module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from huntbot.State import State


@pytest.fixture
def temp_state_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "temp_state.yaml")
        yield state_file
        # No manual cleanup needed — tempfile handles it


@pytest.fixture
def state(temp_state_file):
    return State(state_file=temp_state_file)


# ---------------------------
# BASIC FUNCTIONALITY TESTS
# ---------------------------

@pytest.mark.asyncio
async def test_initial_load_creates_empty_state(state):
    await state.load_state()
    assert isinstance(state.state_data, dict)
    assert state.state_data == {"bot": {}, "cogs": {}}

@pytest.mark.asyncio
async def test_update_bot_section(state):
    await state.update_state(bot=True, team_one_name="Red")
    await state.load_state()
    assert "bot" in state.state_data
    assert state.state_data["bot"]["team_one_name"] == "Red"

@pytest.mark.asyncio
async def test_update_cog_section(state):
    await state.update_state(cog=True, score=100)
    await state.load_state()
    assert "cogs" in state.state_data
    assert state.state_data["cogs"]["score"] == 100

@pytest.mark.asyncio
async def test_update_both_bot_and_cog_separately(state):
    await state.update_state(bot=True, team_one_name="Red")
    await state.update_state(cog=True, dailies_enabled=True)
    await state.load_state()
    assert state.state_data["bot"]["team_one_name"] == "Red"
    assert state.state_data["cogs"]["dailies_enabled"] is True

# ---------------------------
# FILE LOCK TESTS
# ---------------------------

@pytest.mark.asyncio
async def test_file_lock_blocks_access(state):
    lock = state.lock_file
    from filelock import FileLock
    manual_lock = FileLock(lock)
    with manual_lock.acquire(timeout=1):
        with pytest.raises(Timeout):
            await asyncio.wait_for(state.update_state(bot=True, team_two_name="Blue"), timeout=2)

# ---------------------------
# EDGE CASES
# ---------------------------

@pytest.mark.asyncio
async def test_load_with_missing_file_logs_warning(temp_state_file, caplog):
    # Don't pre-create the file
    s = State(state_file=temp_state_file)
    await s.load_state()
    assert "No state file found" in caplog.text

@pytest.mark.asyncio
async def test_update_creates_new_file(temp_state_file):
    # Ensure the file doesn't exist before creating the State object
    assert not os.path.exists(temp_state_file)

    s = State(state_file=temp_state_file)

    # File should be created during initialization
    assert os.path.exists(temp_state_file)

    # Update state and verify contents
    await s.update_state(bot=True, x=1)

    with open(temp_state_file) as f:
        data = yaml.safe_load(f)

    assert data["bot"]["x"] == 1

@pytest.mark.asyncio
async def test_malformed_yaml_raises_error(temp_state_file):
    with open(temp_state_file, "w") as f:
        f.write("bot:\n - bad: [unclosed")

    s = State(state_file=temp_state_file)

    with pytest.raises(ValueError):
        await s.load_state()
