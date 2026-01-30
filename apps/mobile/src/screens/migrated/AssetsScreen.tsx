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
import { Asset } from "../types";

const AssetsScreen = () => {
  const { activeCharacter } = useCharacters();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeCharacter) {
      loadAssets();
    }
  }, [activeCharacter]);

  const loadAssets = async () => {
    if (!activeCharacter) return;

    setLoading(true);
    setError(null);

    try {
      if (activeCharacter.access_token) {
        ESIService.setAuthToken(activeCharacter.access_token);
      }
      const data = await ESIService.getCharacterAssets(
        activeCharacter.character_id,
      );

      // Fetch type names for assets
      const enrichedAssets = await Promise.all(
        data.slice(0, 50).map(async (asset) => {
          try {
            const typeName = await ESIService.getTypeName(asset.type_id);
            return { ...asset, type_name: typeName };
          } catch {
            return asset;
          }
        }),
      );

      setAssets(enrichedAssets);
    } catch (err) {
      setError("Failed to load assets. Please check your authentication.");
      console.error("Error loading assets:", err);
    } finally {
      setLoading(false);
    }
  };

  const renderAsset = ({ item }: { item: Asset }) => (
    <View style={styles.assetCard}>
      <Text style={styles.assetName}>
        {item.type_name || `Type ID: ${item.type_id}`}
      </Text>
      <Text style={styles.assetDetail}>Quantity: {item.quantity}</Text>
      <Text style={styles.assetDetail}>Location ID: {item.location_id}</Text>
      <Text style={styles.assetDetail}>
        {item.is_singleton ? "Assembled" : "Packaged"}
      </Text>
    </View>
  );

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
        <Text style={styles.loadingText}>Loading assets...</Text>
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
          {activeCharacter.character_name}'s Assets
        </Text>
        <Text style={styles.headerSubtext}>
          {assets.length} items (showing first 50)
        </Text>
      </View>

      <FlatList
        data={assets}
        renderItem={renderAsset}
        keyExtractor={(item) => item.item_id.toString()}
        contentContainerStyle={styles.listContainer}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No assets found</Text>
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
  assetCard: {
    backgroundColor: "#1a1a1a",
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#333",
  },
  assetName: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#fff",
    marginBottom: 8,
  },
  assetDetail: {
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

export default AssetsScreen;
