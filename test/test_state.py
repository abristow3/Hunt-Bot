import os
import pytest
import yaml
import shutil
import asyncio
from filelock import Timeout
import sys

# Add parent directory to sys.path so huntbot module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from huntbot.State import State

# Temp test directory
TEST_DIR = "test_conf"
TEST_FILE = os.path.join(TEST_DIR, "state.yaml")

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup: create test_conf dir
    os.makedirs(TEST_DIR, exist_ok=True)

    yield

    # Teardown: remove test_conf dir after each test
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

@pytest.fixture
def state():
    s = State()
    s.state_file = TEST_FILE
    s.lock_file = TEST_FILE + ".lock"
    return s


# ---------------------------
# BASIC FUNCTIONALITY TESTS
# ---------------------------

@pytest.mark.asyncio
async def test_initial_load_creates_empty_state(state):
    await state.load_state()
    assert isinstance(state.state_data, dict)
    assert state.state_data == {}

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
    assert "cog" in state.state_data
    assert state.state_data["cog"]["score"] == 100

@pytest.mark.asyncio
async def test_update_both_bot_and_cog_separately(state):
    await state.update_state(bot=True, team_one_name="Red")
    await state.update_state(cog=True, dailies_enabled=True)
    await state.load_state()
    assert state.state_data["bot"]["team_one_name"] == "Red"
    assert state.state_data["cog"]["dailies_enabled"] is True


# ---------------------------
# FILE LOCK TESTS
# ---------------------------

@pytest.mark.asyncio
async def test_file_lock_blocks_access(state):
    lock = state.lock_file

    # Manually acquire lock to simulate file being in use
    from filelock import FileLock
    manual_lock = FileLock(lock)
    with manual_lock.acquire(timeout=1):
        with pytest.raises(Timeout):
            # This should fail because lock is held
            await asyncio.wait_for(state.update_state(bot=True, team_two_name="Blue"), timeout=2)


# ---------------------------
# EDGE CASES
# ---------------------------

@pytest.mark.asyncio
async def test_load_with_missing_file_logs_warning(state, caplog):
    await state.load_state()
    assert "No state file found" in caplog.text

@pytest.mark.asyncio
async def test_update_creates_new_file(state):
    assert not os.path.exists(TEST_FILE)
    await state.update_state(bot=True, x=1)
    assert os.path.exists(TEST_FILE)
    with open(TEST_FILE) as f:
        data = yaml.safe_load(f)
    assert data["bot"]["x"] == 1

@pytest.mark.asyncio
async def test_malformed_yaml_raises_error(state):
    # Write bad YAML manually
    with open(TEST_FILE, "w") as f:
        f.write("bot:\n - bad: [unclosed")

    with pytest.raises(ValueError):
        await state.load_state()

