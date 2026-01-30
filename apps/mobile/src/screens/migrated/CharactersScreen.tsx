import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
} from "react-native";
import { useCharacters } from "../contexts/CharacterContext";
import { Character } from "../types";

const CharactersScreen = () => {
  const { characters, activeCharacter, setActiveCharacter, removeCharacter } =
    useCharacters();

  const handleSelectCharacter = (characterId: number) => {
    setActiveCharacter(characterId);
    Alert.alert("Success", "Active character changed");
  };

  const handleRemoveCharacter = (
    characterId: number,
    characterName: string,
  ) => {
    Alert.alert(
      "Remove Character",
      `Are you sure you want to remove ${characterName}?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Remove",
          style: "destructive",
          onPress: () => removeCharacter(characterId),
        },
      ],
    );
  };

  const renderCharacter = ({ item }: { item: Character }) => {
    const isActive = activeCharacter?.character_id === item.character_id;

    return (
      <TouchableOpacity
        style={[styles.characterCard, isActive && styles.activeCard]}
        onPress={() => handleSelectCharacter(item.character_id)}
        onLongPress={() =>
          handleRemoveCharacter(item.character_id, item.character_name)
        }
      >
        <View style={styles.characterInfo}>
          <Text style={styles.characterName}>{item.character_name}</Text>
          <Text style={styles.characterDetail}>
            Security: {item.security_status?.toFixed(2) || "N/A"}
          </Text>
          <Text style={styles.characterDetail}>
            Corp ID: {item.corporation_id}
          </Text>
          {item.alliance_id && (
            <Text style={styles.characterDetail}>
              Alliance ID: {item.alliance_id}
            </Text>
          )}
        </View>
        {isActive && (
          <View style={styles.activeBadge}>
            <Text style={styles.activeBadgeText}>ACTIVE</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>
          {characters.length} / 100 Characters
        </Text>
        <Text style={styles.headerSubtext}>
          Tap to select, long press to remove
        </Text>
      </View>

      <FlatList
        data={characters}
        renderItem={renderCharacter}
        keyExtractor={(item) => item.character_id.toString()}
        contentContainerStyle={styles.listContainer}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No characters added yet</Text>
            <Text style={styles.emptySubtext}>
              Use SSO login to add your first character
            </Text>
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
  characterCard: {
    backgroundColor: "#1a1a1a",
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#333",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  activeCard: {
    borderColor: "#00d4ff",
    borderWidth: 2,
  },
  characterInfo: {
    flex: 1,
  },
  characterName: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#fff",
    marginBottom: 5,
  },
  characterDetail: {
    fontSize: 14,
    color: "#888",
    marginTop: 2,
  },
  activeBadge: {
    backgroundColor: "#00d4ff",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 5,
  },
  activeBadgeText: {
    color: "#000",
    fontWeight: "bold",
    fontSize: 12,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 18,
    color: "#666",
    marginBottom: 10,
  },
  emptySubtext: {
    fontSize: 14,
    color: "#444",
    textAlign: "center",
  },
});

export default CharactersScreen;
