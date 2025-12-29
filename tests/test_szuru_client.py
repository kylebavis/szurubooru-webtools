import os
from unittest.mock import AsyncMock

import pytest

# Set environment variables before importing the module
os.environ['SZURU_BASE'] = 'http://test.local'
os.environ['SZURU_USER'] = 'testuser'
os.environ['SZURU_TOKEN'] = 'testtoken'

from app.services.szuru_client import SzuruClient


@pytest.fixture
def mock_client():
    """Create a mock SzuruClient with mocked _req method"""
    client = SzuruClient()
    client._req = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_get_unused_tags_empty(mock_client):
    """Test get_unused_tags when no unused tags exist"""
    mock_client._req.return_value = {'results': []}
    
    result = await mock_client.get_unused_tags()
    
    assert result == []
    mock_client._req.assert_called_once()


@pytest.mark.asyncio
async def test_get_unused_tags_single_page(mock_client):
    """Test get_unused_tags with results on a single page"""
    mock_tags = [
        {'names': ['unused_tag_1'], 'usages': 0, 'version': 1},
        {'names': ['used_tag'], 'usages': 5, 'version': 1},
        {'names': ['unused_tag_2'], 'usages': 0, 'version': 2},
    ]
    mock_client._req.return_value = {'results': mock_tags}
    
    result = await mock_client.get_unused_tags()
    
    assert len(result) == 2
    assert result[0]['names'][0] == 'unused_tag_1'
    assert result[1]['names'][0] == 'unused_tag_2'
    assert all(tag['usages'] == 0 for tag in result)


@pytest.mark.asyncio
async def test_get_unused_tags_pagination(mock_client):
    """Test get_unused_tags with pagination across multiple pages"""
    page_1 = [
        {'names': [f'unused_tag_{i}'], 'usages': 0, 'version': i}
        for i in range(100)
    ]
    page_2 = [
        {'names': ['unused_tag_100'], 'usages': 0, 'version': 100},
        {'names': ['used_tag'], 'usages': 10, 'version': 101},
    ]
    
    mock_client._req.side_effect = [
        {'results': page_1},
        {'results': page_2},
    ]
    
    result = await mock_client.get_unused_tags()
    
    assert len(result) == 101
    assert mock_client._req.call_count == 2


@pytest.mark.asyncio
async def test_delete_tag(mock_client):
    """Test delete_tag sends correct request"""
    mock_client._req.return_value = {'success': True}
    
    result = await mock_client.delete_tag('test_tag', 5)
    
    mock_client._req.assert_called_once_with('DELETE', 'api/tag/test_tag', json={'version': 5})
    assert result == {'success': True}
