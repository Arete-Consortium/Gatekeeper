/**
 * Bottom panel showing system details when a system is tapped.
 */
import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import type { MapNode } from './types';
import { THEME } from '../../config';

interface SystemInfoPanelProps {
  system: MapNode;
  onClose: () => void;
  onRouteFrom: (systemName: string) => void;
  onRouteTo: (systemName: string) => void;
}

function getSecurityColor(security: number): string {
  if (security >= 0.5) return THEME.colors.highSec;
  if (security > 0.0) return THEME.colors.lowSec;
  return THEME.colors.nullSec;
}

function getRiskLabel(score: number): { label: string; color: string } {
  if (score <= 2) return { label: 'Safe', color: THEME.colors.riskGreen };
  if (score <= 5) return { label: 'Caution', color: THEME.colors.riskYellow };
  if (score <= 8) return { label: 'Dangerous', color: THEME.colors.riskOrange };
  return { label: 'Deadly', color: THEME.colors.riskRed };
}

export function SystemInfoPanel({
  system,
  onClose,
  onRouteFrom,
  onRouteTo,
}: SystemInfoPanelProps) {
  const risk = getRiskLabel(system.riskScore);

  return (
    <View style={styles.container}>
      <View style={styles.handle} />

      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Text style={styles.systemName}>{system.name}</Text>
          <Text
            style={[
              styles.securityBadge,
              { backgroundColor: getSecurityColor(system.security) + '30' },
              { color: getSecurityColor(system.security) },
            ]}
          >
            {system.security.toFixed(1)}
          </Text>
        </View>
        <TouchableOpacity onPress={onClose} hitSlop={8}>
          <Text style={styles.closeButton}>Close</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.stats}>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Category</Text>
          <Text style={styles.statValue}>{system.category}</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Risk</Text>
          <Text style={[styles.statValue, { color: risk.color }]}>
            {system.riskScore.toFixed(1)} ({risk.label})
          </Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Region</Text>
          <Text style={styles.statValue}>{system.regionId}</Text>
        </View>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onRouteFrom(system.name)}
        >
          <Text style={styles.actionText}>Route from here</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.actionButtonPrimary]}
          onPress={() => onRouteTo(system.name)}
        >
          <Text style={[styles.actionText, styles.actionTextPrimary]}>
            Route to here
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: THEME.colors.card,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 16,
    paddingBottom: 32,
    borderTopWidth: 1,
    borderTopColor: THEME.colors.border,
  },
  handle: {
    width: 36,
    height: 4,
    backgroundColor: THEME.colors.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 12,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  systemName: {
    fontSize: 20,
    fontWeight: '700',
    color: THEME.colors.text,
  },
  securityBadge: {
    fontSize: 12,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    overflow: 'hidden',
  },
  closeButton: {
    color: THEME.colors.textSecondary,
    fontSize: 14,
  },
  stats: {
    flexDirection: 'row',
    gap: 24,
    marginBottom: 16,
  },
  statItem: {},
  statLabel: {
    fontSize: 11,
    color: THEME.colors.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  statValue: {
    fontSize: 14,
    fontWeight: '600',
    color: THEME.colors.text,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: THEME.colors.cardHover,
    alignItems: 'center',
  },
  actionButtonPrimary: {
    backgroundColor: THEME.colors.primary,
  },
  actionText: {
    fontSize: 14,
    fontWeight: '600',
    color: THEME.colors.text,
  },
  actionTextPrimary: {
    color: '#ffffff',
  },
});
