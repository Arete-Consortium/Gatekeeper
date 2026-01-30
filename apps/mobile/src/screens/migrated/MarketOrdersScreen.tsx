import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
} from "react-native";
import { useCharacters } from "../contexts/CharacterContext";
import ESIService from "../services/ESIService";
import { MarketOrder } from "../types";

const MarketOrdersScreen = () => {
  const { activeCharacter } = useCharacters();
  const [orders, setOrders] = useState<MarketOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeCharacter) {
      loadOrders();
    }
  }, [activeCharacter]);

  const loadOrders = async () => {
    if (!activeCharacter) return;

    setLoading(true);
    setError(null);

    try {
      if (activeCharacter.access_token) {
        ESIService.setAuthToken(activeCharacter.access_token);
      }
      const data = await ESIService.getCharacterOrders(
        activeCharacter.character_id,
      );

      // Fetch type names for orders
      const enrichedOrders = await Promise.all(
        data.map(async (order) => {
          try {
            const typeName = await ESIService.getTypeName(order.type_id);
            return { ...order, type_name: typeName };
          } catch {
            return order;
          }
        }),
      );

      setOrders(enrichedOrders);
    } catch (err) {
      setError(
        "Failed to load market orders. Please check your authentication.",
      );
      console.error("Error loading orders:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatISK = (value: number): string => {
    if (value >= 1000000000) {
      return `${(value / 1000000000).toFixed(2)}B ISK`;
    } else if (value >= 1000000) {
      return `${(value / 1000000).toFixed(2)}M ISK`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}K ISK`;
    }
    return `${value.toFixed(2)} ISK`;
  };

  const renderOrder = ({ item }: { item: MarketOrder }) => {
    const totalValue = item.price * item.volume_remain;
    const percentFilled =
      ((item.volume_total - item.volume_remain) / item.volume_total) * 100;

    return (
      <View style={styles.orderCard}>
        <View style={styles.orderHeader}>
          <Text style={styles.orderName}>
            {item.type_name || `Type ID: ${item.type_id}`}
          </Text>
          <View
            style={[
              styles.orderBadge,
              item.is_buy_order ? styles.buyBadge : styles.sellBadge,
            ]}
          >
            <Text style={styles.badgeText}>
              {item.is_buy_order ? "BUY" : "SELL"}
            </Text>
          </View>
        </View>
        <Text style={styles.orderPrice}>{formatISK(item.price)} per unit</Text>
        <Text style={styles.orderDetail}>
          Volume: {item.volume_remain} / {item.volume_total} (
          {percentFilled.toFixed(0)}% filled)
        </Text>
        <Text style={styles.orderDetail}>
          Total Value: {formatISK(totalValue)}
        </Text>
        <Text style={styles.orderDetail}>Duration: {item.duration} days</Text>
      </View>
    );
  };

  if (!activeCharacter) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>No active character selected</Text>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#00d4ff" />
        <Text style={styles.loadingText}>Loading market orders...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>
          {activeCharacter.character_name}'s Market Orders
        </Text>
        <Text style={styles.headerSubtext}>
          {orders.length} active order{orders.length !== 1 ? "s" : ""}
        </Text>
      </View>

      <FlatList
        data={orders}
        renderItem={renderOrder}
        keyExtractor={(item) => item.order_id.toString()}
        contentContainerStyle={styles.listContainer}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No active market orders</Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  centerContainer: {
    flex: 1,
    backgroundColor: "#0a0a0a",
    justifyContent: "center",
    alignItems: "center",
  },
  header: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#333",
  },
  headerText: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#00d4ff",
  },
  headerSubtext: {
    fontSize: 12,
    color: "#666",
    marginTop: 5,
  },
  listContainer: {
    padding: 15,
  },
  orderCard: {
    backgroundColor: "#1a1a1a",
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#333",
  },
  orderHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  orderName: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#fff",
    flex: 1,
  },
  orderBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  buyBadge: {
    backgroundColor: "#4CAF50",
  },
  sellBadge: {
    backgroundColor: "#f44336",
  },
  badgeText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 12,
  },
  orderPrice: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#00d4ff",
    marginBottom: 8,
  },
  orderDetail: {
    fontSize: 14,
    color: "#888",
    marginTop: 2,
  },
  loadingText: {
    color: "#888",
    marginTop: 10,
    fontSize: 16,
  },
  errorText: {
    color: "#ff4444",
    fontSize: 16,
    textAlign: "center",
    padding: 20,
  },
  emptyContainer: {
    paddingTop: 50,
    alignItems: "center",
  },
  emptyText: {
    fontSize: 16,
    color: "#666",
  },
});

export default MarketOrdersScreen;
