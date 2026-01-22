import asyncio
import unittest
from app.utils.cache_manager import CacheManager

class TestCacheManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cache_manager = CacheManager(default_ttl=1, maxsize=10)

    async def test_caching(self):
        call_count = 0
        
        @self.cache_manager.cached(ttl=10)
        async def mock_api(x):
            nonlocal call_count
            call_count += 1
            return f"result_{x}"

        # First call: miss
        res1 = await mock_api(1)
        self.assertEqual(res1, "result_1")
        self.assertEqual(call_count, 1)

        # Second call: hit
        res2 = await mock_api(1)
        self.assertEqual(res2, "result_1")
        self.assertEqual(call_count, 1)

        # Different arg: miss
        res3 = await mock_api(2)
        self.assertEqual(res3, "result_2")
        self.assertEqual(call_count, 2)

    async def test_invalidation(self):
        call_count = 0
        
        @self.cache_manager.cached(tags=["test_tag"])
        async def mock_api():
            nonlocal call_count
            call_count += 1
            return "data"

        await mock_api() # miss
        self.assertEqual(call_count, 1)
        
        await mock_api() # hit
        self.assertEqual(call_count, 1)

        self.cache_manager.invalidate("test_tag")
        
        await mock_api() # miss (after invalidation)
        self.assertEqual(call_count, 2)

    async def test_ttl(self):
        call_count = 0
        
        @self.cache_manager.cached(ttl=0.1)
        async def mock_api():
            nonlocal call_count
            call_count += 1
            return "data"

        await mock_api() # miss
        self.assertEqual(call_count, 1)
        
        await asyncio.sleep(0.2)
        
        await mock_api() # miss (expired)
        self.assertEqual(call_count, 2)

if __name__ == "__main__":
    unittest.main()
