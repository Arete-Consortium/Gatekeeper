/**
 * Cache Service for offline capabilities
 * Uses AsyncStorage to cache API responses with TTL
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

// Default TTL values in milliseconds
const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes
const ROUTE_TTL = 10 * 60 * 1000; // 10 minutes
const MAP_CONFIG_TTL = 60 * 60 * 1000; // 1 hour
const PROFILES_TTL = 24 * 60 * 60 * 1000; // 24 hours

// Cache key prefixes
const CACHE_PREFIX = '@gatekeeper_cache_';

class CacheService {
  /**
   * Get an item from cache
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const cacheKey = CACHE_PREFIX + key;
      const stored = await AsyncStorage.getItem(cacheKey);

      if (!stored) {
        return null;
      }

      const entry: CacheEntry<T> = JSON.parse(stored);
      const now = Date.now();

      // Check if cache has expired
      if (now - entry.timestamp > entry.ttl) {
        // Expired, remove from cache
        await AsyncStorage.removeItem(cacheKey);
        return null;
      }

      return entry.data;
    } catch (error) {
      console.warn(`[Cache] Error reading ${key}:`, error);
      return null;
    }
  }

  /**
   * Set an item in cache with TTL
   */
  async set<T>(key: string, data: T, ttl: number = DEFAULT_TTL): Promise<void> {
    try {
      const cacheKey = CACHE_PREFIX + key;
      const entry: CacheEntry<T> = {
        data,
        timestamp: Date.now(),
        ttl,
      };
      await AsyncStorage.setItem(cacheKey, JSON.stringify(entry));
    } catch (error) {
      console.warn(`[Cache] Error writing ${key}:`, error);
    }
  }

  /**
   * Remove an item from cache
   */
  async remove(key: string): Promise<void> {
    try {
      const cacheKey = CACHE_PREFIX + key;
      await AsyncStorage.removeItem(cacheKey);
    } catch (error) {
      console.warn(`[Cache] Error removing ${key}:`, error);
    }
  }

  /**
   * Clear all cached data
   */
  async clear(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter((k) => k.startsWith(CACHE_PREFIX));
      if (cacheKeys.length > 0) {
        await AsyncStorage.multiRemove(cacheKeys);
      }
    } catch (error) {
      console.warn('[Cache] Error clearing cache:', error);
    }
  }

  /**
   * Get cache statistics
   */
  async getStats(): Promise<{
    itemCount: number;
    keys: string[];
  }> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter((k) => k.startsWith(CACHE_PREFIX));
      return {
        itemCount: cacheKeys.length,
        keys: cacheKeys.map((k) => k.replace(CACHE_PREFIX, '')),
      };
    } catch (error) {
      console.warn('[Cache] Error getting stats:', error);
      return { itemCount: 0, keys: [] };
    }
  }

  // ==================== Convenience Methods ====================

  /**
   * Cache a route calculation
   */
  async cacheRoute(
    from: string,
    to: string,
    profile: string,
    options: { bridges?: boolean; thera?: boolean },
    data: unknown
  ): Promise<void> {
    const key = `route_${from}_${to}_${profile}_${options.bridges || false}_${options.thera || false}`;
    await this.set(key, data, ROUTE_TTL);
  }

  /**
   * Get cached route
   */
  async getCachedRoute(
    from: string,
    to: string,
    profile: string,
    options: { bridges?: boolean; thera?: boolean }
  ): Promise<unknown | null> {
    const key = `route_${from}_${to}_${profile}_${options.bridges || false}_${options.thera || false}`;
    return this.get(key);
  }

  /**
   * Cache map configuration
   */
  async cacheMapConfig(data: unknown): Promise<void> {
    await this.set('map_config', data, MAP_CONFIG_TTL);
  }

  /**
   * Get cached map configuration
   */
  async getCachedMapConfig(): Promise<unknown | null> {
    return this.get('map_config');
  }

  /**
   * Cache ship profiles
   */
  async cacheShipProfiles(data: unknown): Promise<void> {
    await this.set('ship_profiles', data, PROFILES_TTL);
  }

  /**
   * Get cached ship profiles
   */
  async getCachedShipProfiles(): Promise<unknown | null> {
    return this.get('ship_profiles');
  }

  /**
   * Cache system risk data
   */
  async cacheSystemRisk(systemName: string, data: unknown): Promise<void> {
    const key = `risk_${systemName}`;
    await this.set(key, data, DEFAULT_TTL);
  }

  /**
   * Get cached system risk
   */
  async getCachedSystemRisk(systemName: string): Promise<unknown | null> {
    const key = `risk_${systemName}`;
    return this.get(key);
  }

  /**
   * Cache route history
   */
  async cacheRouteHistory(data: unknown): Promise<void> {
    await this.set('route_history', data, DEFAULT_TTL);
  }

  /**
   * Get cached route history
   */
  async getCachedRouteHistory(): Promise<unknown | null> {
    return this.get('route_history');
  }

  /**
   * Cache hot systems
   */
  async cacheHotSystems(hours: number, data: unknown): Promise<void> {
    const key = `hot_systems_${hours}`;
    await this.set(key, data, DEFAULT_TTL);
  }

  /**
   * Get cached hot systems
   */
  async getCachedHotSystems(hours: number): Promise<unknown | null> {
    const key = `hot_systems_${hours}`;
    return this.get(key);
  }
}

// Export singleton instance
export const cacheService = new CacheService();
export default cacheService;

// Export TTL constants for custom usage
export { DEFAULT_TTL, ROUTE_TTL, MAP_CONFIG_TTL, PROFILES_TTL };
