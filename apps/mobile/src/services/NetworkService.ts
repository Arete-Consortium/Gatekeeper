/**
 * Network Service
 * Monitors network connectivity and provides offline detection
 */
import NetInfo, { NetInfoState, NetInfoSubscription } from '@react-native-community/netinfo';

type NetworkListener = (isConnected: boolean) => void;

class NetworkService {
  private isConnected: boolean = true;
  private listeners: Set<NetworkListener> = new Set();
  private subscription: NetInfoSubscription | null = null;

  constructor() {
    this.initialize();
  }

  /**
   * Initialize network monitoring
   */
  private async initialize(): Promise<void> {
    try {
      // Get initial state
      const state = await NetInfo.fetch();
      this.isConnected = state.isConnected ?? true;

      // Subscribe to network changes
      this.subscription = NetInfo.addEventListener((state: NetInfoState) => {
        const wasConnected = this.isConnected;
        this.isConnected = state.isConnected ?? true;

        // Notify listeners if connectivity changed
        if (wasConnected !== this.isConnected) {
          this.notifyListeners();
        }
      });
    } catch (error) {
      console.warn('[Network] Error initializing:', error);
      // Assume connected if we can't detect
      this.isConnected = true;
    }
  }

  /**
   * Get current connection status
   */
  getIsConnected(): boolean {
    return this.isConnected;
  }

  /**
   * Check if device is offline
   */
  isOffline(): boolean {
    return !this.isConnected;
  }

  /**
   * Add a listener for connectivity changes
   */
  addListener(listener: NetworkListener): () => void {
    this.listeners.add(listener);
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Notify all listeners of connectivity change
   */
  private notifyListeners(): void {
    this.listeners.forEach((listener) => {
      try {
        listener(this.isConnected);
      } catch (error) {
        console.warn('[Network] Listener error:', error);
      }
    });
  }

  /**
   * Manually refresh network state
   */
  async refresh(): Promise<boolean> {
    try {
      const state = await NetInfo.fetch();
      const wasConnected = this.isConnected;
      this.isConnected = state.isConnected ?? true;

      if (wasConnected !== this.isConnected) {
        this.notifyListeners();
      }

      return this.isConnected;
    } catch (error) {
      console.warn('[Network] Error refreshing:', error);
      return this.isConnected;
    }
  }

  /**
   * Clean up subscriptions
   */
  destroy(): void {
    if (this.subscription) {
      this.subscription();
      this.subscription = null;
    }
    this.listeners.clear();
  }
}

// Export singleton instance
export const networkService = new NetworkService();
export default networkService;
