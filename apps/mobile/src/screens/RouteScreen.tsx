/**
 * Route Screen
 * Route planning interface
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Switch,
} from 'react-native';
import { useRoute, useNavigation, RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { GatekeeperAPI } from '../services/GatekeeperAPI';
import { RouteResponse } from '../types';
import { RouteList } from '../components/RouteList';
import { THEME, ROUTE_PROFILES, SHIP_PROFILE_DISPLAY } from '../config';
import { RootStackParamList } from '../navigation/types';

type ShipProfileKey = keyof typeof SHIP_PROFILE_DISPLAY;

type RouteScreenRouteProp = RouteProp<RootStackParamList, 'Route'>;

type ProfileKey = 'shortest' | 'safer' | 'paranoid';

export const RouteScreen: React.FC = () => {
  const route = useRoute<RouteScreenRouteProp>();
  const navigation = useNavigation<StackNavigationProp<RootStackParamList>>();

  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [profile, setProfile] = useState<ProfileKey>(
    (route.params?.profile as ProfileKey) || 'safer'
  );
  const [shipProfile, setShipProfile] = useState<ShipProfileKey>('default');
  const [showShipProfiles, setShowShipProfiles] = useState(false);
  const [useBridges, setUseBridges] = useState(false);
  const [useThera, setUseThera] = useState(false);
  const [loading, setLoading] = useState(false);
  const [routeResult, setRouteResult] = useState<RouteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCalculateRoute = async () => {
    if (!origin.trim() || !destination.trim()) {
      Alert.alert('Error', 'Please enter both origin and destination systems');
      return;
    }

    setLoading(true);
    setError(null);
    setRouteResult(null);

    try {
      const result = await GatekeeperAPI.getRoute(
        origin.trim(),
        destination.trim(),
        profile,
        { bridges: useBridges, thera: useThera }
      );
      setRouteResult(result);
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to calculate route';
      setError(message);
      Alert.alert('Route Error', message);
    } finally {
      setLoading(false);
    }
  };

  const handleSwapSystems = () => {
    const temp = origin;
    setOrigin(destination);
    setDestination(temp);
  };

  const handleClear = () => {
    setOrigin('');
    setDestination('');
    setRouteResult(null);
    setError(null);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.inputSection}>
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Origin System</Text>
            <TextInput
              style={styles.input}
              value={origin}
              onChangeText={setOrigin}
              placeholder="e.g., Jita"
              placeholderTextColor={THEME.colors.textSecondary}
              autoCapitalize="words"
              autoCorrect={false}
            />
          </View>

          <TouchableOpacity style={styles.swapButton} onPress={handleSwapSystems}>
            <Text style={styles.swapButtonText}>Swap</Text>
          </TouchableOpacity>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Destination System</Text>
            <TextInput
              style={styles.input}
              value={destination}
              onChangeText={setDestination}
              placeholder="e.g., Amarr"
              placeholderTextColor={THEME.colors.textSecondary}
              autoCapitalize="words"
              autoCorrect={false}
            />
          </View>
        </View>

        <View style={styles.profileSection}>
          <Text style={styles.sectionTitle}>Route Profile</Text>
          <View style={styles.profileButtons}>
            {(Object.entries(ROUTE_PROFILES) as [ProfileKey, typeof ROUTE_PROFILES.shortest][]).map(
              ([key, config]) => (
                <TouchableOpacity
                  key={key}
                  style={[
                    styles.profileButton,
                    profile === key && {
                      backgroundColor: config.color,
                      borderColor: config.color,
                    },
                  ]}
                  onPress={() => setProfile(key)}
                >
                  <Text
                    style={[
                      styles.profileButtonText,
                      profile === key && styles.profileButtonTextActive,
                    ]}
                  >
                    {config.label}
                  </Text>
                </TouchableOpacity>
              )
            )}
          </View>
          <Text style={styles.profileDescription}>
            {ROUTE_PROFILES[profile].description}
          </Text>
        </View>

        <View style={styles.profileSection}>
          <TouchableOpacity
            style={styles.shipProfileHeader}
            onPress={() => setShowShipProfiles(!showShipProfiles)}
          >
            <Text style={styles.sectionTitle}>Ship Profile</Text>
            <View style={styles.shipProfileBadge}>
              <Text style={[styles.shipProfileBadgeText, { color: SHIP_PROFILE_DISPLAY[shipProfile].color }]}>
                {SHIP_PROFILE_DISPLAY[shipProfile].label}
              </Text>
            </View>
          </TouchableOpacity>
          {showShipProfiles && (
            <View style={styles.shipProfileGrid}>
              {(Object.entries(SHIP_PROFILE_DISPLAY) as [ShipProfileKey, typeof SHIP_PROFILE_DISPLAY.default][]).map(
                ([key, config]) => (
                  <TouchableOpacity
                    key={key}
                    style={[
                      styles.shipProfileCard,
                      shipProfile === key && {
                        borderColor: config.color,
                        backgroundColor: `${config.color}20`,
                      },
                    ]}
                    onPress={() => {
                      setShipProfile(key);
                      setShowShipProfiles(false);
                    }}
                  >
                    <Text
                      style={[
                        styles.shipProfileName,
                        { color: shipProfile === key ? config.color : THEME.colors.text },
                      ]}
                    >
                      {config.label}
                    </Text>
                    <Text style={styles.shipProfileDesc}>{config.description}</Text>
                  </TouchableOpacity>
                )
              )}
            </View>
          )}
        </View>

        <View style={styles.shortcutSection}>
          <Text style={styles.sectionTitle}>Shortcuts</Text>
          <View style={styles.toggleRow}>
            <View style={styles.toggleInfo}>
              <Text style={styles.toggleLabel}>Ansiblex Jump Bridges</Text>
              <Text style={styles.toggleDescription}>Use player-owned jump bridges</Text>
            </View>
            <Switch
              value={useBridges}
              onValueChange={setUseBridges}
              trackColor={{ false: THEME.colors.border, true: THEME.colors.primary }}
              thumbColor={THEME.colors.text}
            />
          </View>
          <View style={styles.toggleRow}>
            <View style={styles.toggleInfo}>
              <Text style={styles.toggleLabel}>Thera Shortcuts</Text>
              <Text style={styles.toggleDescription}>Route through Thera wormhole connections</Text>
            </View>
            <Switch
              value={useThera}
              onValueChange={setUseThera}
              trackColor={{ false: THEME.colors.border, true: THEME.colors.wormhole }}
              thumbColor={THEME.colors.text}
            />
          </View>
        </View>

        <View style={styles.actionSection}>
          <TouchableOpacity
            style={[styles.calculateButton, loading && styles.buttonDisabled]}
            onPress={handleCalculateRoute}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={THEME.colors.text} />
            ) : (
              <Text style={styles.calculateButtonText}>Calculate Route</Text>
            )}
          </TouchableOpacity>

          {routeResult && (
            <TouchableOpacity style={styles.clearButton} onPress={handleClear}>
              <Text style={styles.clearButtonText}>Clear</Text>
            </TouchableOpacity>
          )}
        </View>

        {error && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {routeResult && (
          <View style={styles.resultSection}>
            <Text style={styles.sectionTitle}>Route Result</Text>
            <RouteList route={routeResult} />
            <TouchableOpacity
              style={styles.showOnMapButton}
              onPress={() => navigation.navigate('Map', { route: routeResult })}
            >
              <Text style={styles.showOnMapText}>Show on Map</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  content: {
    padding: THEME.spacing.md,
  },
  inputSection: {
    marginBottom: THEME.spacing.md,
  },
  inputGroup: {
    marginBottom: THEME.spacing.sm,
  },
  inputLabel: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
    marginBottom: THEME.spacing.xs,
  },
  input: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    color: THEME.colors.text,
    fontSize: 16,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  swapButton: {
    alignSelf: 'center',
    paddingVertical: THEME.spacing.xs,
    paddingHorizontal: THEME.spacing.md,
    marginVertical: THEME.spacing.xs,
  },
  swapButtonText: {
    color: THEME.colors.primary,
    fontSize: 14,
    fontWeight: '600',
  },
  profileSection: {
    marginBottom: THEME.spacing.md,
  },
  sectionTitle: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
    textTransform: 'uppercase',
    fontWeight: '600',
    marginBottom: THEME.spacing.sm,
  },
  profileButtons: {
    flexDirection: 'row',
    gap: THEME.spacing.sm,
  },
  profileButton: {
    flex: 1,
    paddingVertical: THEME.spacing.sm,
    paddingHorizontal: THEME.spacing.md,
    borderRadius: THEME.borderRadius.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    alignItems: 'center',
  },
  profileButtonText: {
    color: THEME.colors.textSecondary,
    fontSize: 14,
    fontWeight: '600',
  },
  profileButtonTextActive: {
    color: '#000',
  },
  profileDescription: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
    marginTop: THEME.spacing.sm,
    textAlign: 'center',
  },
  shortcutSection: {
    marginBottom: THEME.spacing.md,
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    marginBottom: THEME.spacing.xs,
  },
  toggleInfo: {
    flex: 1,
    marginRight: THEME.spacing.md,
  },
  toggleLabel: {
    color: THEME.colors.text,
    fontSize: 14,
    fontWeight: '500',
  },
  toggleDescription: {
    color: THEME.colors.textSecondary,
    fontSize: 11,
    marginTop: 2,
  },
  actionSection: {
    flexDirection: 'row',
    gap: THEME.spacing.sm,
    marginBottom: THEME.spacing.md,
  },
  calculateButton: {
    flex: 1,
    backgroundColor: THEME.colors.primary,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  calculateButtonText: {
    color: THEME.colors.text,
    fontSize: 16,
    fontWeight: 'bold',
  },
  clearButton: {
    paddingHorizontal: THEME.spacing.md,
    paddingVertical: THEME.spacing.md,
    borderRadius: THEME.borderRadius.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  clearButtonText: {
    color: THEME.colors.textSecondary,
    fontSize: 16,
  },
  errorContainer: {
    backgroundColor: 'rgba(255, 69, 58, 0.2)',
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    marginBottom: THEME.spacing.md,
  },
  errorText: {
    color: THEME.colors.riskRed,
    fontSize: 14,
  },
  resultSection: {
    flex: 1,
  },
  showOnMapButton: {
    marginTop: THEME.spacing.md,
    backgroundColor: THEME.colors.primary,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    alignItems: 'center',
  },
  showOnMapText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  shipProfileHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: THEME.spacing.sm,
  },
  shipProfileBadge: {
    paddingHorizontal: THEME.spacing.sm,
    paddingVertical: THEME.spacing.xs,
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.sm,
  },
  shipProfileBadgeText: {
    fontSize: 12,
    fontWeight: '600',
  },
  shipProfileGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: THEME.spacing.sm,
  },
  shipProfileCard: {
    width: '48%',
    padding: THEME.spacing.sm,
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  shipProfileName: {
    fontSize: 14,
    fontWeight: '600',
  },
  shipProfileDesc: {
    fontSize: 10,
    color: THEME.colors.textSecondary,
    marginTop: 2,
  },
});

export default RouteScreen;
