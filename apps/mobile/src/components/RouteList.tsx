/**
 * Route List Component
 * Displays a route with all hops and risk information
 */
import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { RouteResponse, RouteHop } from '../types';
import { formatSecurityStatus, formatJumps, estimateRouteTime, formatRiskScore } from '../utils/formatting';
import { RiskBadge } from './RiskBadge';
import { THEME } from '../config';

interface RouteListProps {
  route: RouteResponse;
  showSummary?: boolean;
}

interface RouteHopItemProps {
  hop: RouteHop;
  index: number;
  isFirst: boolean;
  isLast: boolean;
}

const RouteHopItem: React.FC<RouteHopItemProps> = ({
  hop,
  index,
  isFirst,
  isLast,
}) => {
  const security = formatSecurityStatus(hop.security_status);

  return (
    <View style={styles.hopContainer}>
      <View style={styles.hopLine}>
        <View style={[styles.hopDot, { backgroundColor: security.color }]} />
        {!isLast && <View style={styles.hopConnector} />}
      </View>
      <View style={styles.hopContent}>
        <View style={styles.hopHeader}>
          <Text style={styles.hopNumber}>{index + 1}</Text>
          <Text style={styles.hopName}>{hop.system_name}</Text>
          <Text style={[styles.hopSecurity, { color: security.color }]}>
            {security.text}
          </Text>
        </View>
        <View style={styles.hopDetails}>
          <RiskBadge riskScore={hop.risk_score} size="small" />
          {isFirst && (
            <Text style={styles.hopLabel}>Origin</Text>
          )}
          {isLast && (
            <Text style={styles.hopLabel}>Destination</Text>
          )}
        </View>
      </View>
    </View>
  );
};

export const RouteList: React.FC<RouteListProps> = ({
  route,
  showSummary = true,
}) => {
  const avgRisk = formatRiskScore(route.avg_risk);
  const maxRisk = formatRiskScore(route.max_risk);

  const renderHop = ({ item, index }: { item: RouteHop; index: number }) => (
    <RouteHopItem
      hop={item}
      index={index}
      isFirst={index === 0}
      isLast={index === route.path.length - 1}
    />
  );

  return (
    <View style={styles.container}>
      {showSummary && (
        <View style={styles.summary}>
          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryValue}>{formatJumps(route.total_jumps)}</Text>
              <Text style={styles.summaryLabel}>Distance</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryValue}>{estimateRouteTime(route.total_jumps)}</Text>
              <Text style={styles.summaryLabel}>Est. Time</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={[styles.summaryValue, { color: avgRisk.color }]}>
                {avgRisk.text}
              </Text>
              <Text style={styles.summaryLabel}>Avg Risk</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={[styles.summaryValue, { color: maxRisk.color }]}>
                {maxRisk.text}
              </Text>
              <Text style={styles.summaryLabel}>Max Risk</Text>
            </View>
          </View>
          <View style={styles.badgeRow}>
            <View style={styles.profileBadge}>
              <Text style={styles.profileText}>
                Profile: {route.profile.charAt(0).toUpperCase() + route.profile.slice(1)}
              </Text>
            </View>
            {route.bridges_used > 0 && (
              <View style={[styles.profileBadge, styles.bridgeBadge]}>
                <Text style={styles.profileText}>
                  {route.bridges_used} Bridge{route.bridges_used !== 1 ? 's' : ''}
                </Text>
              </View>
            )}
            {route.thera_used > 0 && (
              <View style={[styles.profileBadge, styles.theraBadge]}>
                <Text style={styles.profileText}>
                  {route.thera_used} Thera
                </Text>
              </View>
            )}
          </View>
        </View>
      )}

      <FlatList
        data={route.path}
        renderItem={renderHop}
        keyExtractor={(item, index) => `${item.system_name}-${index}`}
        scrollEnabled={false}
        style={styles.list}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  summary: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.md,
    marginBottom: THEME.spacing.md,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryValue: {
    color: THEME.colors.text,
    fontSize: 18,
    fontWeight: 'bold',
  },
  summaryLabel: {
    color: THEME.colors.textSecondary,
    fontSize: 10,
    textTransform: 'uppercase',
    marginTop: 2,
  },
  badgeRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    flexWrap: 'wrap',
    gap: THEME.spacing.xs,
    marginTop: THEME.spacing.sm,
  },
  profileBadge: {
    paddingHorizontal: THEME.spacing.md,
    paddingVertical: THEME.spacing.xs,
    backgroundColor: THEME.colors.primary,
    borderRadius: THEME.borderRadius.xl,
  },
  bridgeBadge: {
    backgroundColor: '#ff9f0a',
  },
  theraBadge: {
    backgroundColor: '#9900ff',
  },
  profileText: {
    color: THEME.colors.text,
    fontSize: 12,
    fontWeight: '600',
  },
  list: {
    flex: 1,
  },
  hopContainer: {
    flexDirection: 'row',
    paddingLeft: THEME.spacing.sm,
  },
  hopLine: {
    width: 24,
    alignItems: 'center',
  },
  hopDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  hopConnector: {
    width: 2,
    flex: 1,
    backgroundColor: THEME.colors.border,
    marginVertical: 2,
  },
  hopContent: {
    flex: 1,
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.sm,
    marginLeft: THEME.spacing.sm,
    marginBottom: THEME.spacing.xs,
  },
  hopHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: THEME.spacing.sm,
  },
  hopNumber: {
    color: THEME.colors.textSecondary,
    fontSize: 12,
    fontWeight: 'bold',
    width: 20,
  },
  hopName: {
    color: THEME.colors.text,
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  hopSecurity: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  hopDetails: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: THEME.spacing.xs,
    gap: THEME.spacing.sm,
  },
  hopLabel: {
    color: THEME.colors.primary,
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
});

export default RouteList;
