"""
Optimized Scalable Bloom Filter Seen Store

Provides ultra-fast, in-memory probabilistic deduplication with minimal memory usage

Luckily there are many implementations online for this in python (could be faster with a pacakge written in C/C++)
"""

import hashlib
import math
import os
import pickle
import struct
import threading


class BloomSlice:
    """
    Single bitarray slice for a Bloom Filter.

    Fields:
        capacity: int = Maximum number of items the slice is sized to hold
        error_rate: float = Target false positive probability for this slice
        num_bits: int = Total number of bits allocated in the bitarray
        num_bytes: int = Total number of bytes allocated for the bytearray
        num_hashes: int = Number of hash functions generated per key
        bitarray: bytearray = Byte array storing the filter bit fields
        count: int = Current number of elements added to this slice
    """

    def __init__(self, capacity: int, error_rate: float):
        """
        Initializes the bloom slice with optimal bit array size and hash counts.

        Args:
            capacity: int = Maximum number of items slice is sized to hold
            error_rate: float = Desired false positive probability
        """
        self.capacity = max(1, capacity)
        self.error_rate = error_rate
        # Optimal number of bits m = - (n * ln(p)) / (ln(2)^2)
        self.num_bits = int(-(self.capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self.num_bytes = (self.num_bits + 7) // 8
        self.num_bits = self.num_bytes * 8
        # Optimal number of hash functions k = (m / n) * ln(2)
        self.num_hashes = max(1, int((self.num_bits / self.capacity) * math.log(2)))
        self.bitarray = bytearray(self.num_bytes)
        self.count = 0

    def _hashes(self, key: str):
        """
        Generates bit indices using double hashing (Kirsch-Mitzenmacher technique).
        Derives two 64-bit unsigned hashes from a single MD5 digest.

        Args:
            key: str = Element string to hash

        Yields:
            int: Bit index within the bitarray
        """
        d = hashlib.md5(key.encode("utf-8")).digest()
        h1, h2 = struct.unpack("<QQ", d)
        h2 |= 1  # ensure odd step for full cycle
        num_bits = self.num_bits
        for i in range(self.num_hashes):
            yield (h1 + i * h2) % num_bits

    def add(self, key: str) -> None:
        """
        Adds a key to the bloom slice bitarray.

        Args:
            key: str = Element string to record in the slice
        """
        arr = self.bitarray
        for bit in self._hashes(key):
            arr[bit >> 3] |= (1 << (bit & 7))
        self.count += 1

    def contains(self, key: str) -> bool:
        """
        Tests whether a key may be present in the bloom slice.

        Args:
            key: str = Element string to test

        Returns:
            bool: True if key might be present, False if definitely not
        """
        arr = self.bitarray
        for bit in self._hashes(key):
            if not (arr[bit >> 3] & (1 << (bit & 7))):
                return False
        return True

    def check_and_add(self, key: str) -> bool:
        """
        Single-pass test-and-set: tests presence and sets bits in one pass.

        Args:
            key: str = Element string to test and insert

        Returns:
            bool: True if the key was new and inserted, False if already present
        """
        d = hashlib.md5(key.encode("utf-8")).digest()
        h1, h2 = struct.unpack("<QQ", d)
        h2 |= 1
        num_bits = self.num_bits
        arr = self.bitarray
        num_hashes = self.num_hashes

        all_set = True
        bits = []
        for i in range(num_hashes):
            bit = (h1 + i * h2) % num_bits
            bits.append(bit)
            if not (arr[bit >> 3] & (1 << (bit & 7))):
                all_set = False

        if all_set:
            return False

        for bit in bits:
            arr[bit >> 3] |= (1 << (bit & 7))
        self.count += 1
        return True


class ScalableBloomFilter:
    """
    Auto-expanding Bloom Filter that maintains overall error rate as items grow.

    Fields:
        initial_capacity: int = Sizing capacity for the first bloom slice
        error_rate: float = Target overall false positive error rate
        scale_factor: int = Multiplier for capacity when allocating subsequent slices
        slices: list[BloomSlice] = List of active BloomSlice instances
    """

    def __init__(self, initial_capacity: int = 200_000, error_rate: float = 0.01, scale_factor: int = 2):
        """
        Initializes the scalable bloom filter with an initial slice.

        Args:
            initial_capacity: int = Initial capacity for the first bloom slice
            error_rate: float = Target overall false positive error rate
            scale_factor: int = Multiplier to scale capacity for subsequent slices
        """
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.scale_factor = scale_factor
        self.slices = [BloomSlice(initial_capacity, error_rate)]

    def add(self, key: str) -> None:
        """
        Adds a key to the filter, appending a new slice if the current one is full.

        Args:
            key: str = Element string to record in the filter
        """
        if self.contains(key):
            return
        current = self.slices[-1]
        if current.count >= current.capacity:
            new_capacity = current.capacity * self.scale_factor
            new_error_rate = current.error_rate * 0.85
            current = BloomSlice(new_capacity, new_error_rate)
            self.slices.append(current)
        current.add(key)

    def contains(self, key: str) -> bool:
        """
        Tests whether a key may be present in any active bloom slice.

        Args:
            key: str = Element string to query

        Returns:
            bool: True if key may have been added, False if definitely not
        """
        for s in self.slices:
            if s.contains(key):
                return True
        return False

    def check_and_add(self, key: str) -> bool:
        """
        Atomically checks if an element is in any slice; if not, inserts it into the active slice.

        Args:
            key: str = Element string to check and insert

        Returns:
            bool: True if the element was new and added, False if already present
        """
        for s in self.slices:
            if s.contains(key):
                return False
        current = self.slices[-1]
        if current.count >= current.capacity:
            new_capacity = current.capacity * self.scale_factor
            new_error_rate = current.error_rate * 0.85
            current = BloomSlice(new_capacity, new_error_rate)
            self.slices.append(current)
        current.add(key)
        return True


class SeenStore:
    """
    High-Performance In-Memory Seen Store backed by a Scalable Bloom Filter.
    Zero disk I/O and zero database locks during crawling.

    Fields:
        db_path: str | None = Optional persistence file path on disk
        lock: threading.Lock = Mutex protecting concurrent access
        bloom: ScalableBloomFilter = In-memory scalable bloom filter
    """

    def __init__(self, db_path: str | None = None, reset: bool = True, initial_capacity: int = 200_000, error_rate: float = 0.01):
        """
        Initializes the in-memory bloom filter seen store.

        Args:
            db_path: str | None = Optional file path for persistence across sessions (None for pure RAM)
            reset: bool = If True, starts with a fresh empty filter
            initial_capacity: int = Initial slice capacity
            error_rate: float = Target false positive rate
        """
        self.db_path = db_path
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.lock = threading.Lock()
        self.bloom = ScalableBloomFilter(initial_capacity=initial_capacity, error_rate=error_rate)

        if not reset and db_path and os.path.exists(db_path):
            try:
                with open(db_path, "rb") as f:
                    loaded = pickle.load(f)
                    if isinstance(loaded, ScalableBloomFilter):
                        self.bloom = loaded
            except Exception:
                pass
        elif reset and db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    def clear(self) -> None:
        """Clears the bloom filter in memory and removes any associated file on disk."""
        with self.lock:
            self.bloom = ScalableBloomFilter(initial_capacity=self.initial_capacity, error_rate=self.error_rate)
            if self.db_path and os.path.exists(self.db_path):
                try:
                    os.remove(self.db_path)
                except Exception:
                    pass

    def check_and_add(self, url: str) -> bool:
        """
        Atomically checks if a URL has been seen and records it if new.

        Args:
            url: str = The URL string to test and record

        Returns:
            bool: True if the URL was new and successfully added, False if already seen
        """
        if not url or not isinstance(url, str):
            return False
        with self.lock:
            return self.bloom.check_and_add(url)

    def add(self, url: str) -> None:
        """
        Unconditionally records a URL as seen.

        Args:
            url: str = The URL string to record
        """
        if not url or not isinstance(url, str):
            return
        with self.lock:
            self.bloom.add(url)

    def contains(self, url: str) -> bool:
        """
        Checks whether a URL has been seen.

        Args:
            url: str = The URL string to check

        Returns:
            bool: True if the URL has been recorded as seen, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        with self.lock:
            return self.bloom.contains(url)

    def __contains__(self, url: str) -> bool:
        return self.contains(url)

    def commit(self) -> None:
        """Compatibility no-op (no active database connection needed)."""
        pass

    def close(self) -> None:
        """
        Persists the in-memory bloom filter state to file on shutdown if configured.
        """
        with self.lock:
            if self.db_path:
                try:
                    with open(self.db_path, "wb") as f:
                        pickle.dump(self.bloom, f)
                except Exception:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
