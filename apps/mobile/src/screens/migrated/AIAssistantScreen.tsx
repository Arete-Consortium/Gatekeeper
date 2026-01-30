import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
} from "react-native";
import { useCharacters } from "../contexts/CharacterContext";
import AIService from "../services/AIService";

const AIAssistantScreen = () => {
  const { activeCharacter } = useCharacters();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const quickActions = [
    {
      title: "Route Planning",
      icon: "🗺️",
      description: "Plan safe routes with zkillboard data",
    },
    {
      title: "Asset Analysis",
      icon: "📊",
      description: "Analyze asset distribution and suggest consolidation",
    },
    {
      title: "Market Insights",
      icon: "💹",
      description: "Get market order recommendations",
    },
    {
      title: "Fitting Advisor",
      icon: "🚀",
      description: "Get optimal ship fitting suggestions",
    },
  ];

  const handleQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      // This is a placeholder for AI query processing
      // In production, this would call an AI service or backend
      let aiResponse = "";

      if (query.toLowerCase().includes("route")) {
        aiResponse =
          "To plan a route, go to the Map screen and select your origin and destination systems. I will analyze the route for danger and suggest alternatives.";
      } else if (query.toLowerCase().includes("asset")) {
        aiResponse =
          "Your assets are currently being tracked. Visit the Assets screen to see your inventory across all locations.";
      } else if (query.toLowerCase().includes("market")) {
        aiResponse =
          "Monitor your market orders in the Market Orders screen. I can help you analyze pricing and competition.";
      } else if (query.toLowerCase().includes("fit")) {
        aiResponse =
          "Visit the Ship Fittings screen to get AI-powered fitting suggestions based on your skills and intended use.";
      } else {
        aiResponse =
          "I can help you with route planning, asset management, market analysis, and ship fitting suggestions. What would you like to know more about?";
      }

      setResponse(aiResponse);
    } catch (error) {
      setResponse("Sorry, I encountered an error processing your request.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView>
        <View style={styles.header}>
          <Text style={styles.headerText}>🤖 AI Assistant</Text>
          <Text style={styles.headerSubtext}>
            Your intelligent companion for EVE Online
          </Text>
        </View>

        {activeCharacter && (
          <View style={styles.characterCard}>
            <Text style={styles.characterLabel}>Active Character:</Text>
            <Text style={styles.characterName}>
              {activeCharacter.character_name}
            </Text>
          </View>
        )}

        <View style={styles.querySection}>
          <Text style={styles.sectionTitle}>Ask me anything</Text>
          <TextInput
            style={styles.queryInput}
            placeholder="What would you like to know?"
            placeholderTextColor="#666"
            value={query}
            onChangeText={setQuery}
            multiline
            numberOfLines={3}
          />
          <TouchableOpacity
            style={styles.queryButton}
            onPress={handleQuery}
            disabled={loading}
          >
            <Text style={styles.queryButtonText}>
              {loading ? "Thinking..." : "Ask Assistant"}
            </Text>
          </TouchableOpacity>
        </View>

        {response && (
          <View style={styles.responseCard}>
            <Text style={styles.responseLabel}>Assistant Response:</Text>
            <Text style={styles.responseText}>{response}</Text>
          </View>
        )}

        <View style={styles.actionsSection}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          {quickActions.map((action, index) => (
            <View key={index} style={styles.actionCard}>
              <Text style={styles.actionIcon}>{action.icon}</Text>
              <View style={styles.actionContent}>
                <Text style={styles.actionTitle}>{action.title}</Text>
                <Text style={styles.actionDescription}>
                  {action.description}
                </Text>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.capabilitiesCard}>
          <Text style={styles.capabilitiesTitle}>AI Capabilities</Text>
          <Text style={styles.capabilityText}>
            ✓ Route planning with danger assessment
          </Text>
          <Text style={styles.capabilityText}>
            ✓ Asset distribution analysis
          </Text>
          <Text style={styles.capabilityText}>✓ Market order optimization</Text>
          <Text style={styles.capabilityText}>
            ✓ Ship fitting recommendations
          </Text>
          <Text style={styles.capabilityText}>
            ✓ Jump calculation for capital ships
          </Text>
          <Text style={styles.capabilityText}>
            ✓ zkillboard integration for threat detection
          </Text>
          <Text style={styles.capabilityText}>
            ✓ Alternative route suggestions
          </Text>
        </View>
      </ScrollView>
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
    fontSize: 24,
    fontWeight: "bold",
    color: "#00d4ff",
  },
  headerSubtext: {
    fontSize: 14,
    color: "#666",
    marginTop: 5,
  },
  characterCard: {
    margin: 15,
    backgroundColor: "#1a1a1a",
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#333",
  },
  characterLabel: {
    color: "#888",
    fontSize: 12,
    marginBottom: 5,
  },
  characterName: {
    color: "#00d4ff",
    fontSize: 18,
    fontWeight: "bold",
  },
  querySection: {
    padding: 15,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#fff",
    marginBottom: 15,
  },
  queryInput: {
    backgroundColor: "#1a1a1a",
    color: "#fff",
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#333",
    minHeight: 80,
    textAlignVertical: "top",
  },
  queryButton: {
    backgroundColor: "#00d4ff",
    padding: 15,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 10,
  },
  queryButtonText: {
    color: "#000",
    fontWeight: "bold",
    fontSize: 16,
  },
  responseCard: {
    margin: 15,
    backgroundColor: "#1a2a1a",
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#4CAF50",
  },
  responseLabel: {
    color: "#4CAF50",
    fontSize: 14,
    fontWeight: "bold",
    marginBottom: 10,
  },
  responseText: {
    color: "#fff",
    fontSize: 14,
    lineHeight: 22,
  },
  actionsSection: {
    padding: 15,
  },
  actionCard: {
    flexDirection: "row",
    backgroundColor: "#1a1a1a",
    padding: 15,
    borderRadius: 8,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#333",
    alignItems: "center",
  },
  actionIcon: {
    fontSize: 32,
    marginRight: 15,
  },
  actionContent: {
    flex: 1,
  },
  actionTitle: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "bold",
    marginBottom: 5,
  },
  actionDescription: {
    color: "#888",
    fontSize: 14,
  },
  capabilitiesCard: {
    margin: 15,
    backgroundColor: "#1a1a1a",
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#333",
  },
  capabilitiesTitle: {
    color: "#00d4ff",
    fontSize: 16,
    fontWeight: "bold",
    marginBottom: 10,
  },
  capabilityText: {
    color: "#ccc",
    fontSize: 14,
    marginBottom: 8,
  },
});

export default AIAssistantScreen;
