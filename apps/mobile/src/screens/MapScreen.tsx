/**
 * Full-screen map of New Eden with pan/zoom, system tap, and route overlay.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useNavigation, useRoute as useNavRoute } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { SkiaMap, SystemInfoPanel } from '../components/map';
import type { MapNode, SkiaMapHandle } from '../components/map';
import type { ColorMode } from '../components/map/MapSystems';
import { useMapData } from '../hooks/useMapData';
import { useHotSystems } from '../hooks/useHotSystems';
import { THEME } from '../config';
import type { RootStackParamList } from '../navigation/types';
import type { RouteResponse } from '../types';

type MapScreenNavProp = StackNavigationProp<RootStackParamList, 'Map'>;

export default function MapScreen() {
  const navigation = useNavigation<MapScreenNavProp>();
  const navRoute = useNavRoute();
  const routeParam = (navRoute.params as { route?: RouteResponse })?.route;

  const mapRef = useRef<SkiaMapHandle>(null);

  const { nodes, edges, spatialIndex, regionCentroids, constellationCentroids, systemNameMap, isLoading, error } =
    useMapData();

  const hotSystems = useHotSystems();

  // Auto-fit viewport to route when arriving from RouteScreen
  const hasAutoFit = useRef(false);
  useEffect(() => {
    if (hasAutoFit.current || !routeParam?.path || !systemNameMap.size) return;
    hasAutoFit.current = true;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const hop of routeParam.path) {
      const node = systemNameMap.get(hop.system_name);
      if (!node) continue;
      minX = Math.min(minX, node.x);
      minY = Math.min(minY, node.y);
      maxX = Math.max(maxX, node.x);
      maxY = Math.max(maxY, node.y);
    }
    if (minX < Infinity) {
      // Delay slightly so SkiaMap has mounted
      setTimeout(() => mapRef.current?.fitBounds(minX, minY, maxX, maxY), 100);
    }
  }, [routeParam, systemNameMap]);

  const [selectedSystem, setSelectedSystem] = useState<MapNode | null>(null);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<MapNode[]>([]);
  const [showSearch, setShowSearch] = useState(false);
  const [colorMode, setColorMode] = useState<ColorMode>('security');

  const handleSystemTap = useCallback((system: MapNode) => {
    setSelectedSystem(system);
    setShowSearch(false);
  }, []);

  const handleSearch = useCallback(
    (text: string) => {
      setSearchText(text);
      if (text.length < 2) {
        setSearchResults([]);
        return;
      }
      const lower = text.toLowerCase();
      const results: MapNode[] = [];
      for (const [name, node] of systemNameMap) {
        if (name.toLowerCase().startsWith(lower)) {
          results.push(node);
          if (results.length >= 10) break;
        }
      }
      setSearchResults(results);
    },
    [systemNameMap]
  );

  const handleSearchSelect = useCallback((system: MapNode) => {
    setSelectedSystem(system);
    setSearchText('');
    setSearchResults([]);
    setShowSearch(false);
    mapRef.current?.focusSystem(system.x, system.y);
  }, []);

  const handleRouteFrom = useCallback(
    (systemName: string) => {
      setSelectedSystem(null);
      navigation.navigate('Route', { from: systemName });
    },
    [navigation]
  );

  const handleRouteTo = useCallback(
    (systemName: string) => {
      setSelectedSystem(null);
      navigation.navigate('Route', { to: systemName });
    },
    [navigation]
  );

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={THEME.colors.primary} />
        <Text style={styles.loadingText}>Loading New Eden...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity
          style={styles.retryButton}
          onPress={() => navigation.replace('Map')}
        >
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SkiaMap
        ref={mapRef}
        nodes={nodes}
        edges={edges}
        spatialIndex={spatialIndex}
        regionCentroids={regionCentroids}
        constellationCentroids={constellationCentroids}
        colorMode={colorMode}
        hotSystems={hotSystems}
        systemNameMap={systemNameMap}
        route={routeParam?.path}
        onSystemTap={handleSystemTap}
      />

      {/* Search bar overlay */}
      <View style={styles.searchContainer}>
        <View style={styles.topBar}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.backText}>Back</Text>
          </TouchableOpacity>

          <View style={styles.topBarRight}>
            <TouchableOpacity
              style={styles.colorToggle}
              onPress={() => setColorMode((m) => m === 'security' ? 'risk' : 'security')}
            >
              <Text style={styles.colorToggleText}>
                {colorMode === 'security' ? 'SEC' : 'RISK'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.searchToggle}
              onPress={() => setShowSearch(!showSearch)}
            >
              <Text style={styles.searchIcon}>Search</Text>
            </TouchableOpacity>
          </View>
        </View>

        {showSearch && (
          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          >
            <TextInput
              style={styles.searchInput}
              placeholder="Search system..."
              placeholderTextColor={THEME.colors.textSecondary}
              value={searchText}
              onChangeText={handleSearch}
              autoFocus
              autoCapitalize="characters"
              returnKeyType="search"
            />
            {searchResults.length > 0 && (
              <FlatList
                data={searchResults}
                keyExtractor={(item) => String(item.systemId)}
                style={styles.searchResults}
                keyboardShouldPersistTaps="handled"
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.searchResultItem}
                    onPress={() => handleSearchSelect(item)}
                  >
                    <Text style={styles.searchResultName}>{item.name}</Text>
                    <Text
                      style={[
                        styles.searchResultSecurity,
                        {
                          color:
                            item.security >= 0.5
                              ? THEME.colors.highSec
                              : item.security > 0
                              ? THEME.colors.lowSec
                              : THEME.colors.nullSec,
                        },
                      ]}
                    >
                      {item.security.toFixed(1)}
                    </Text>
                  </TouchableOpacity>
                )}
              />
            )}
          </KeyboardAvoidingView>
        )}
      </View>

      {/* Route stats overlay */}
      {routeParam && routeParam.path && (
        <View style={styles.routeStats}>
          <Text style={styles.routeStatsTitle}>Route</Text>
          <Text style={styles.routeStatsValue}>
            {routeParam.total_jumps} jumps
          </Text>
          <Text style={styles.routeStatsRisk}>
            Avg risk: {routeParam.avg_risk.toFixed(1)} | Max: {routeParam.max_risk.toFixed(1)}
          </Text>
        </View>
      )}

      {/* System count badge */}
      <View style={styles.countBadge}>
        <Text style={styles.countText}>
          {nodes.length.toLocaleString()} systems
          {hotSystems.size > 0 ? ` | ${hotSystems.size} active` : ''}
        </Text>
      </View>

      {/* System info panel */}
      {selectedSystem && (
        <SystemInfoPanel
          system={selectedSystem}
          onClose={() => setSelectedSystem(null)}
          onRouteFrom={handleRouteFrom}
          onRouteTo={handleRouteTo}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: THEME.colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  loadingText: {
    color: THEME.colors.textSecondary,
    fontSize: 16,
  },
  errorText: {
    color: THEME.colors.riskRed,
    fontSize: 16,
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 10,
    backgroundColor: THEME.colors.primary,
    borderRadius: 8,
  },
  retryText: {
    color: '#ffffff',
    fontWeight: '600',
  },
  searchContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingTop: 50,
    paddingHorizontal: 16,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  backButton: {
    backgroundColor: THEME.colors.card + 'DD',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  backText: {
    color: THEME.colors.text,
    fontWeight: '600',
    fontSize: 14,
  },
  searchToggle: {
    backgroundColor: THEME.colors.card + 'DD',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  searchIcon: {
    color: THEME.colors.primary,
    fontWeight: '600',
    fontSize: 14,
  },
  searchInput: {
    backgroundColor: THEME.colors.card,
    color: THEME.colors.text,
    fontSize: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  searchResults: {
    backgroundColor: THEME.colors.card,
    borderRadius: 10,
    marginTop: 4,
    maxHeight: 300,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  searchResultItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: THEME.colors.border,
  },
  searchResultName: {
    color: THEME.colors.text,
    fontSize: 15,
    fontWeight: '500',
  },
  searchResultSecurity: {
    fontSize: 13,
    fontWeight: '700',
  },
  topBarRight: {
    flexDirection: 'row',
    gap: 8,
  },
  colorToggle: {
    backgroundColor: THEME.colors.card + 'DD',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  colorToggleText: {
    color: THEME.colors.text,
    fontWeight: '700',
    fontSize: 12,
  },
  routeStats: {
    position: 'absolute',
    bottom: 16,
    right: 16,
    backgroundColor: THEME.colors.card + 'EE',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: THEME.colors.primary + '40',
  },
  routeStatsTitle: {
    color: THEME.colors.textSecondary,
    fontSize: 10,
    textTransform: 'uppercase',
    fontWeight: '600',
    marginBottom: 2,
  },
  routeStatsValue: {
    color: THEME.colors.text,
    fontSize: 16,
    fontWeight: '700',
  },
  routeStatsRisk: {
    color: THEME.colors.riskYellow,
    fontSize: 12,
    fontWeight: '600',
    marginTop: 2,
  },
  countBadge: {
    position: 'absolute',
    bottom: 16,
    left: 16,
    backgroundColor: THEME.colors.card + 'CC',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  countText: {
    color: THEME.colors.textSecondary,
    fontSize: 11,
    fontWeight: '500',
  },
});
