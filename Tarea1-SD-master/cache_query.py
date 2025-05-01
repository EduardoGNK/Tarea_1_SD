#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import random
import logging
import os
from datetime import datetime
import numpy as np
import redis
import pymongo
from pymongo.collection import Collection
from bson.objectid import ObjectId
from typing import Dict, List, Any, Optional, Union
from collections import Counter, deque

# Setup logging
def setup_logger():
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    root_logger = logging.getLogger('cache_benchmark')
    root_logger.setLevel(logging.INFO)
    
    console = logging.StreamHandler()
    console.setFormatter(log_formatter)
    root_logger.addHandler(console)
    
    return root_logger

logger = setup_logger()

# Configuration
class Config:
    REDIS_SERVER = os.environ.get("REDIS_HOST", "cache")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    MONGODB_CONNECTION = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/")
    DB = "traffic_data"
    COLLECTION = "waze_incidents"
    QUERIES = 1000
    CACHE_SIZE = 200

# Access pattern generators
class AccessPatternFactory:
    @staticmethod
    def create(pattern_type: str, document_ids: List[str]):
        if pattern_type == "zipf":
            return ZipfAccessPattern(document_ids)
        return UniformAccessPattern(document_ids)

class BaseAccessPattern:
    def __init__(self, document_ids: List[str]):
        self.document_ids = document_ids
    
    def get_next_id(self) -> str:
        raise NotImplementedError()

class UniformAccessPattern(BaseAccessPattern):
    def get_next_id(self) -> str:
        return random.choice(self.document_ids)

class ZipfAccessPattern(BaseAccessPattern):
    def __init__(self, document_ids: List[str], alpha: float = 1.5):
        super().__init__(document_ids)
        self.alpha = alpha
        
        # Zipf distribution weights
        n = len(document_ids)
        weights = np.array([1/((i+1)**alpha) for i in range(n)])
        self.probabilities = weights / weights.sum()
    
    def get_next_id(self) -> str:
        return np.random.choice(self.document_ids, p=self.probabilities)

# Cache strategy implementations
class CacheStrategy:
    def __init__(self, redis_client: redis.Redis, capacity: int = Config.CACHE_SIZE, 
                 expiry: int = 3600):
        self.redis = redis_client
        self.capacity = capacity
        self.expiry = expiry
        self.strategy_name = "Base"
    
    def get(self, key: str) -> Optional[str]:
        return self.redis.get(key)
    
    def put(self, key: str, value: str) -> None:
        if self.redis.dbsize() >= self.capacity:
            self.evict_entry()
        self.redis.set(key, value, ex=self.expiry)
    
    def evict_entry(self) -> None:
        pass
    
    def reset(self) -> None:
        self.redis.flushall()

class BasicCacheStrategy(CacheStrategy):
    def __init__(self, redis_client: redis.Redis, capacity: int = Config.CACHE_SIZE, 
                 expiry: int = 3600):
        super().__init__(redis_client, capacity, expiry)
        self.strategy_name = "Simple"
    
    def evict_entry(self) -> None:
        # Relies on Redis TTL mechanism
        pass

class LRUCacheStrategy(CacheStrategy):
    def __init__(self, redis_client: redis.Redis, capacity: int = Config.CACHE_SIZE, 
                 expiry: int = 3600):
        super().__init__(redis_client, capacity, expiry)
        self.strategy_name = "LRU"
        self.access_queue = deque(maxlen=capacity)
    
    def get(self, key: str) -> Optional[str]:
        value = super().get(key)
        if value:
            # Move to end (most recently used)
            if key in self.access_queue:
                self.access_queue.remove(key)
            self.access_queue.append(key)
        return value
    
    def put(self, key: str, value: str) -> None:
        super().put(key, value)
        # Add to access history
        if key in self.access_queue:
            self.access_queue.remove(key)
        self.access_queue.append(key)
    
    def evict_entry(self) -> None:
        if self.access_queue:
            # Remove least recently used
            oldest = self.access_queue.popleft()
            self.redis.delete(oldest)

class LFUCacheStrategy(CacheStrategy):
    def __init__(self, redis_client: redis.Redis, capacity: int = Config.CACHE_SIZE, 
                 expiry: int = 3600):
        super().__init__(redis_client, capacity, expiry)
        self.strategy_name = "LFU"
        self.frequency = Counter()
    
    def get(self, key: str) -> Optional[str]:
        value = super().get(key)
        if value:
            self.frequency[key] += 1
        return value
    
    def put(self, key: str, value: str) -> None:
        super().put(key, value)
        self.frequency[key] = 1
    
    def evict_entry(self) -> None:
        if self.frequency:
            # Get least frequently used items
            least_used = self.frequency.most_common()[:-2:-1]
            if least_used:
                key = least_used[0][0]
                self.redis.delete(key)
                del self.frequency[key]

# Database connection helpers
def connect_services():
    logger.info("Connecting to services...")
    
    # Redis connection
    try:
        redis_client = redis.Redis(
            host=Config.REDIS_SERVER,
            port=Config.REDIS_PORT,
            decode_responses=True,
            socket_timeout=5
        )
        redis_client.ping()
        logger.info("✓ Redis connection successful")
    except redis.ConnectionError as e:
        logger.error(f"✗ Redis connection failed: {e}")
        sys.exit(1)
    
    # MongoDB connection
    try:
        mongo_client = pymongo.MongoClient(
            Config.MONGODB_CONNECTION,
            serverSelectionTimeoutMS=5000
        )
        mongo_client.admin.command('ping')
        db = mongo_client[Config.DB]
        collection = db[Config.COLLECTION]
        logger.info("✓ MongoDB connection successful")
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"✗ MongoDB connection failed: {e}")
        sys.exit(1)
    
    return redis_client, collection

def get_sample_documents(collection: Collection, sample_size: int = 500) -> List[str]:
    logger.info(f"Retrieving {sample_size} random documents...")
    
    try:
        # Sample random documents
        cursor = collection.aggregate([{"$sample": {"size": sample_size}}])
        doc_ids = [str(doc["_id"]) for doc in cursor]
        logger.info(f"✓ Retrieved {len(doc_ids)} document IDs")
        
        if len(doc_ids) < sample_size:
            logger.warning(f"⚠️ Only {len(doc_ids)} documents available")
        
        return doc_ids
    except Exception as e:
        logger.error(f"✗ Failed to get sample documents: {e}")
        sys.exit(1)

# Simulation runner
def run_benchmark(doc_ids: List[str], collection: Collection, 
                 access_pattern: str, cache_type: str) -> Dict[str, Any]:
    # Initialize components
    pattern_generator = AccessPatternFactory.create(access_pattern, doc_ids)
    redis_client, _ = connect_services()
    
    # Select cache strategy
    if cache_type == "lru":
        cache = LRUCacheStrategy(redis_client)
        strategy_name = "LRU"
    elif cache_type == "lfu":
        cache = LFUCacheStrategy(redis_client)
        strategy_name = "LFU"
    else:
        cache = BasicCacheStrategy(redis_client)
        strategy_name = "Simple"
    
    # Reset cache
    cache.reset()
    
    # Performance metrics
    cache_hits = 0
    cache_misses = 0
    response_times = []
    
    pattern_name = "Zipf" if access_pattern == "zipf" else "Uniform"
    logger.info(f"🔄 Starting benchmark: {pattern_name} pattern with {strategy_name} cache")
    
    # Run queries
    for i in range(Config.QUERIES):
        # Get next document to query
        doc_id = pattern_generator.get_next_id()
        start = time.time()
        
        # Try cache first
        cached_doc = cache.get(doc_id)
        
        if cached_doc:
            # Cache hit
            cache_hits += 1
            if i % 100 == 0:
                logger.info(f"[{i}] CACHE HIT ✓  -> {doc_id[:8]}...")
        else:
            # Cache miss
            cache_misses += 1
            if i % 100 == 0:
                logger.info(f"[{i}] CACHE MISS ✗ -> {doc_id[:8]}...")
            
            # Get from database
            document = collection.find_one({"_id": ObjectId(doc_id)})
            if document:
                # Convert ObjectId to string
                document["_id"] = str(document["_id"])
                cache.put(doc_id, json.dumps(document))
        
        # Calculate response time
        elapsed = time.time() - start
        response_times.append(elapsed)
        
        # Simulate processing delay
        time.sleep(0.01)
    
    # Calculate final metrics
    hit_rate = cache_hits / Config.QUERIES if Config.QUERIES > 0 else 0
    avg_latency = sum(response_times) / len(response_times) if response_times else 0
    
    # Prepare results
    benchmark_results = {
        "distribution": access_pattern,
        "cache_policy": cache_type,
        "cache_size": Config.CACHE_SIZE,
        "total_queries": Config.QUERIES,
        "hits": cache_hits,
        "misses": cache_misses,
        "hit_rate": hit_rate,
        "avg_latency": avg_latency,
        "timestamp": datetime.now().isoformat()
    }
    
    # Log summary
    logger.info(f"\n📊 Benchmark Results:")
    logger.info(f"   Access Pattern: {pattern_name}")
    logger.info(f"   Cache Strategy: {strategy_name}")
    logger.info(f"   Hit Rate: {hit_rate:.2%}")
    logger.info(f"   Average Latency: {avg_latency*1000:.2f} ms")
    logger.info(f"   Hits/Misses: {cache_hits}/{cache_misses}")
    
    # Save results
    filename = f"results_{access_pattern}_{cache_type}.json"
    with open(filename, "w") as f:
        json.dump(benchmark_results, f, indent=2)
    logger.info(f"✓ Results saved to {filename}")
    
    return benchmark_results

def main():
    logger.info("🚀 Starting cache simulation system")
    
    try:
        # Initialize connections
        redis_client, collection = connect_services()
        
        # Get sample documents
        doc_ids = get_sample_documents(collection)
        
        if not doc_ids:
            logger.error("✗ No document IDs available for benchmarking")
            return
        
        # Benchmark configurations
        access_patterns = ["uniform", "zipf"]
        cache_strategies = ["simple", "lru", "lfu"]
        
        # Log benchmark setup
        logger.info("\n📋 Benchmark Configuration:")
        logger.info(f"   Unique Documents: {len(doc_ids)}")
        logger.info(f"   Queries per Benchmark: {Config.QUERIES}")
        logger.info(f"   Cache Size: {Config.CACHE_SIZE} entries")
        
        # Show combinations
        logger.info("\n🔄 Running benchmark combinations:")
        for pattern in access_patterns:
            for strategy in cache_strategies:
                logger.info(f"   • {pattern.upper()} + {strategy.upper()}")
        
        # Run benchmarks
        all_results = []
        for pattern in access_patterns:
            for strategy in cache_strategies:
                logger.info(f"\n{'='*50}")
                logger.info(f"BENCHMARK: {pattern.upper()} + {strategy.upper()}")
                logger.info(f"{'='*50}")
                
                result = run_benchmark(doc_ids, collection, pattern, strategy)
                all_results.append(result)
                
                # Delay between benchmarks
                time.sleep(1)
        
        # Save consolidated results
        with open("all_simulation_results.json", "w") as f:
            json.dump(all_results, f, indent=2)
        logger.info("\n✅ All benchmarks completed and results consolidated")
        
    except Exception as e:
        logger.error(f"✗ Error during benchmark: {e}", exc_info=True)

if __name__ == "__main__":
    main()