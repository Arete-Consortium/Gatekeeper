/**
 * Home Screen
 * Main dashboard with quick actions
 */
import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { GatekeeperAPI } from '../services/GatekeeperAPI';
import { RouteHistoryEntry, HotSystem } from '../types';
import { THEME, ROUTE_PROFILES } from '../config';
import { RootStackParamList } from '../navigation/types';

type HomeScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Home'>;

export const HomeScreen: React.FC = () => {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [routeHistory, setRouteHistory] = useState<RouteHistoryEntry[]>([]);
  const [hotSystems, setHotSystems] = useState<HotSystem[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    checkApiStatus();
  }, []);

  // Refresh data when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      if (apiStatus === 'online') {
        fetchData();
      }
    }, [apiStatus])
  );

  const checkApiStatus = async () => {
    setApiStatus('checking');
    const isOnline = await GatekeeperAPI.testConnection();
    setApiStatus(isOnline ? 'online' : 'offline');
    if (isOnline) {
      fetchData();
    }
  };

  const fetchData = async () => {
    try {
      const [historyRes, hotRes] = await Promise.all([
        GatekeeperAPI.getRouteHistory(5).catch(() => ({ history: [], total: 0 })),
        GatekeeperAPI.getHotSystems(24, 5).catch(() => []),
      ]);
      setRouteHistory(historyRes.history);
      setHotSystems(hotRes);
    } catch (err) {
      console.warn('Failed to fetch dashboard data:', err);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await checkApiStatus();
    setRefreshing(false);
  };

  const StatusIndicator = () => {
    let color: string;
    let text: string;

    switch (apiStatus) {
      case 'online':
        color = THEME.colors.riskGreen;
        text = 'API Online';
        break;
      case 'offline':
        color = THEME.colors.riskRed;
        text = 'API Offline';
        break;
      default:
        color = THEME.colors.textSecondary;
        text = 'Checking...';
    }

    return (
      <View style={styles.statusContainer}>
        <View style={[styles.statusDot, { backgroundColor: color }]} />
        <Text style={[styles.statusText, { color }]}>{text}</Text>
        {apiStatus === 'checking' && (
          <ActivityIndicator size="small" color={THEME.colors.textSecondary} />
        )}
      </View>
    );
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  const getSecurityColor = (security: number): string => {
    if (security >= 0.5) return THEME.colors.highSec;
    if (security > 0) return THEME.colors.lowSec;
    return THEME.colors.nullSec;
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={THEME.colors.primary}
        />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>EVE Gatekeeper</Text>
        <Text style={styles.subtitle}>Intel & Route Planning</Text>
        <StatusIndicator />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() => navigation.navigate('Map')}
        >
          <Text style={styles.primaryButtonText}>Open Map</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.primaryButton, styles.secondaryButton]}
          onPress={() => navigation.navigate('Route')}
        >
          <Text style={styles.primaryButtonText}>Plan Route</Text>
        </TouchableOpacity>
      </View>

      {hotSystems.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Hot Systems (24h)</Text>
          <View style={styles.hotSystemsGrid}>
            {hotSystems.map((system) => (
              <View key={system.system_id} style={styles.hotSystemCard}>
                <View style={styles.hotSystemHeader}>
                  <Text style={styles.hotSystemName}>{system.system_name}</Text>
                  <Text style={[styles.hotSystemSecurity, { color: getSecurityColor(system.security) }]}>
                    {system.security.toFixed(1)}
                  </Text>
                </View>
                <View style={styles.hotSystemStats}>
                  <Text style={styles.hotSystemKills}>{system.recent_kills} kills</Text>
                  {system.recent_pods > 0 && (
                    <Text style={styles.hotSystemPods}>{system.recent_pods} pods</Text>
                  )}
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {routeHistory.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Routes</Text>
          <View style={styles.historyGrid}>
            {routeHistory.map((entry, index) => (
              <TouchableOpacity
                key={`${entry.from_system}-${entry.to_system}-${index}`}
                style={styles.historyCard}
                onPress={() => navigation.navigate('Route')}
              >
                <View style={styles.historyRoute}>
                  <Text style={styles.historySystem}>{entry.from_system}</Text>
                  <Text style={styles.historyArrow}>→</Text>
                  <Text style={styles.historySystem}>{entry.to_system}</Text>
                </View>
                <View style={styles.historyMeta}>
                  <Text style={styles.historyJumps}>{entry.jumps} jumps</Text>
                  <Text style={styles.historyTime}>{formatTimestamp(entry.timestamp)}</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Route Profiles</Text>
        <View style={styles.profilesGrid}>
          {Object.entries(ROUTE_PROFILES).map(([key, profile]) => (
            <TouchableOpacity
              key={key}
              style={[styles.profileCard, { borderColor: profile.color }]}
              onPress={() => navigation.navigate('Route', { profile: key as any })}
            >
              <Text style={[styles.profileName, { color: profile.color }]}>
                {profile.label}
              </Text>
              <Text style={styles.profileDescription}>{profile.description}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Tools</Text>
        <View style={styles.toolsGrid}>
          <TouchableOpacity
            style={styles.toolCard}
            onPress={() => navigation.navigate('Fitting')}
          >
            <Text style={styles.toolName}>Fitting Analyzer</Text>
            <Text style={styles.toolDescription}>Parse EFT fittings for travel advice</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.toolCard}
            onPress={() => navigation.navigate('Alerts')}
          >
            <Text style={styles.toolName}>Kill Alerts</Text>
            <Text style={styles.toolDescription}>Discord & Slack notifications</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.toolCard}
            onPress={() => navigation.navigate('Settings')}
          >
            <Text style={styles.toolName}>Settings</Text>
            <Text style={styles.toolDescription}>Configure API & preferences</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
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
  header: {
    alignItems: 'center',
    paddingVertical: THEME.spacing.xl,
  },
  title: {
    color: THEME.colors.text,
    fontSize: 28,
    fontWeight: 'bold',
  },
  subtitle: {
    color: THEME.colors.textSecondary,
    fontSize: 16,
    marginTop: THEME.spacing.xs,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: THEME.spacing.md,
    gap: THEME.spacing.xs,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '500',
  },
  section: {
    marginBottom: THEME.spacing.lg,
  },
  sectionTitle: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
    textTransform: 'uppercase',
    fontWeight: '600',
    marginBottom: THEME.spacing.sm,
  },
  primaryButton: {
    backgroundColor: THEME.colors.primary,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.md,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: THEME.colors.text,
    fontSize: 18,
    fontWeight: 'bold',
  },
  secondaryButton: {
    backgroundColor: THEME.colors.card,
    marginTop: THEME.spacing.sm,
  },
  profilesGrid: {
    gap: THEME.spacing.sm,
  },
  profileCard: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.md,
    borderLeftWidth: 4,
  },
  profileName: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  profileDescription: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },
  toolsGrid: {
    gap: THEME.spacing.sm,
  },
  toolCard: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.md,
  },
  toolName: {
    color: THEME.colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  toolDescription: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },
  hotSystemsGrid: {
    gap: THEME.spacing.sm,
  },
  hotSystemCard: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.sm,
    borderLeftWidth: 3,
    borderLeftColor: THEME.colors.riskRed,
  },
  hotSystemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  hotSystemName: {
    color: THEME.colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  hotSystemSecurity: {
    fontSize: 12,
    fontWeight: '600',
  },
  hotSystemStats: {
    flexDirection: 'row',
    gap: THEME.spacing.sm,
    marginTop: 4,
  },
  hotSystemKills: {
    color: THEME.colors.riskRed,
    fontSize: 12,
  },
  hotSystemPods: {
    color: THEME.colors.riskOrange,
    fontSize: 12,
  },
  historyGrid: {
    gap: THEME.spacing.sm,
  },
  historyCard: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.sm,
  },
  historyRoute: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: THEME.spacing.xs,
  },
  historySystem: {
    color: THEME.colors.text,
    fontSize: 14,
    fontWeight: '500',
  },
  historyArrow: {
    color: THEME.colors.textSecondary,
    fontSize: 14,
  },
  historyMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  historyJumps: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
  },
  historyTime: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
  },
});

export default HomeScreen;
