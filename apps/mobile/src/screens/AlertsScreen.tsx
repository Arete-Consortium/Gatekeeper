/**
 * Alerts Screen
 * Manage kill alert subscriptions
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  ActivityIndicator,
  RefreshControl,
  Switch,
  Alert,
} from 'react-native';
import { GatekeeperAPI } from '../services/GatekeeperAPI';
import { THEME } from '../config';

interface Subscription {
  id: string;
  name: string | null;
  webhook_type: string;
  systems: string[];
  regions: number[];
  min_value: number | null;
  include_pods: boolean;
  ship_types: string[];
  enabled: boolean;
}

export const AlertsScreen: React.FC = () => {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Create form state
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookType, setWebhookType] = useState<'discord' | 'slack'>('discord');
  const [subName, setSubName] = useState('');
  const [systems, setSystems] = useState('');
  const [minValue, setMinValue] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchSubscriptions();
  }, []);

  const fetchSubscriptions = async () => {
    try {
      const data = await GatekeeperAPI.listAlertSubscriptions();
      setSubscriptions(data.subscriptions);
    } catch (err) {
      console.error('Failed to fetch subscriptions:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchSubscriptions();
  }, []);

  const createSubscription = async () => {
    if (!webhookUrl.trim()) {
      Alert.alert('Error', 'Webhook URL is required');
      return;
    }

    setCreating(true);
    try {
      const systemsList = systems
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);

      await GatekeeperAPI.createAlertSubscription({
        webhook_url: webhookUrl.trim(),
        webhook_type: webhookType,
        name: subName.trim() || undefined,
        systems: systemsList.length > 0 ? systemsList : undefined,
        min_value: minValue ? parseFloat(minValue) : undefined,
      });

      // Reset form
      setWebhookUrl('');
      setSubName('');
      setSystems('');
      setMinValue('');
      setShowCreateForm(false);

      // Refresh list
      fetchSubscriptions();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Failed to create subscription');
    } finally {
      setCreating(false);
    }
  };

  const deleteSubscription = async (id: string) => {
    Alert.alert(
      'Delete Subscription',
      'Are you sure you want to delete this subscription?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await GatekeeperAPI.deleteAlertSubscription(id);
              fetchSubscriptions();
            } catch (err) {
              Alert.alert('Error', 'Failed to delete subscription');
            }
          },
        },
      ]
    );
  };

  const sendTestAlert = async (id: string) => {
    try {
      await GatekeeperAPI.sendTestAlert();
      Alert.alert('Success', 'Test alert sent');
    } catch (err) {
      Alert.alert('Error', 'Failed to send test alert');
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={THEME.colors.primary} />
      </View>
    );
  }

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
        <Text style={styles.title}>Kill Alerts</Text>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setShowCreateForm(!showCreateForm)}
        >
          <Text style={styles.addButtonText}>
            {showCreateForm ? 'Cancel' : '+ Add'}
          </Text>
        </TouchableOpacity>
      </View>

      {showCreateForm && (
        <View style={styles.createForm}>
          <Text style={styles.formTitle}>New Subscription</Text>

          <View style={styles.typeSelector}>
            <TouchableOpacity
              style={[
                styles.typeButton,
                webhookType === 'discord' && styles.typeButtonActive,
              ]}
              onPress={() => setWebhookType('discord')}
            >
              <Text
                style={[
                  styles.typeButtonText,
                  webhookType === 'discord' && styles.typeButtonTextActive,
                ]}
              >
                Discord
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.typeButton,
                webhookType === 'slack' && styles.typeButtonActive,
              ]}
              onPress={() => setWebhookType('slack')}
            >
              <Text
                style={[
                  styles.typeButtonText,
                  webhookType === 'slack' && styles.typeButtonTextActive,
                ]}
              >
                Slack
              </Text>
            </TouchableOpacity>
          </View>

          <TextInput
            style={styles.input}
            placeholder="Webhook URL *"
            placeholderTextColor={THEME.colors.textSecondary}
            value={webhookUrl}
            onChangeText={setWebhookUrl}
            autoCapitalize="none"
            autoCorrect={false}
          />

          <TextInput
            style={styles.input}
            placeholder="Name (optional)"
            placeholderTextColor={THEME.colors.textSecondary}
            value={subName}
            onChangeText={setSubName}
          />

          <TextInput
            style={styles.input}
            placeholder="Systems (comma-separated, empty = all)"
            placeholderTextColor={THEME.colors.textSecondary}
            value={systems}
            onChangeText={setSystems}
          />

          <TextInput
            style={styles.input}
            placeholder="Minimum ISK value (optional)"
            placeholderTextColor={THEME.colors.textSecondary}
            value={minValue}
            onChangeText={setMinValue}
            keyboardType="numeric"
          />

          <TouchableOpacity
            style={styles.createButton}
            onPress={createSubscription}
            disabled={creating}
          >
            {creating ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.createButtonText}>Create Subscription</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {subscriptions.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyText}>No subscriptions yet</Text>
          <Text style={styles.emptySubtext}>
            Add a Discord or Slack webhook to receive kill alerts
          </Text>
        </View>
      ) : (
        subscriptions.map(sub => (
          <View key={sub.id} style={styles.subscriptionCard}>
            <View style={styles.cardHeader}>
              <View style={styles.cardTitleRow}>
                <Text style={styles.cardTitle}>
                  {sub.name || `${sub.webhook_type} webhook`}
                </Text>
                <View
                  style={[
                    styles.typeBadge,
                    sub.webhook_type === 'discord'
                      ? styles.discordBadge
                      : styles.slackBadge,
                  ]}
                >
                  <Text style={styles.typeBadgeText}>
                    {sub.webhook_type.toUpperCase()}
                  </Text>
                </View>
              </View>
              <View
                style={[
                  styles.statusDot,
                  sub.enabled ? styles.statusEnabled : styles.statusDisabled,
                ]}
              />
            </View>

            <View style={styles.cardDetails}>
              <Text style={styles.detailText}>
                Systems: {sub.systems.length > 0 ? sub.systems.join(', ') : 'All'}
              </Text>
              {sub.min_value && (
                <Text style={styles.detailText}>
                  Min Value: {(sub.min_value / 1000000).toFixed(0)}M ISK
                </Text>
              )}
            </View>

            <View style={styles.cardActions}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => sendTestAlert(sub.id)}
              >
                <Text style={styles.actionButtonText}>Test</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionButton, styles.deleteButton]}
                onPress={() => deleteSubscription(sub.id)}
              >
                <Text style={styles.deleteButtonText}>Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  content: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: THEME.colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: THEME.colors.text,
  },
  addButton: {
    backgroundColor: THEME.colors.primary,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  createForm: {
    backgroundColor: THEME.colors.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  formTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: THEME.colors.text,
    marginBottom: 16,
  },
  typeSelector: {
    flexDirection: 'row',
    marginBottom: 16,
    gap: 12,
  },
  typeButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    alignItems: 'center',
  },
  typeButtonActive: {
    backgroundColor: THEME.colors.primary,
    borderColor: THEME.colors.primary,
  },
  typeButtonText: {
    color: THEME.colors.textSecondary,
    fontWeight: '500',
  },
  typeButtonTextActive: {
    color: '#fff',
  },
  input: {
    backgroundColor: THEME.colors.background,
    borderRadius: 8,
    padding: 12,
    color: THEME.colors.text,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  createButton: {
    backgroundColor: THEME.colors.primary,
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  createButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: THEME.colors.text,
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: THEME.colors.textSecondary,
    textAlign: 'center',
  },
  subscriptionCard: {
    backgroundColor: THEME.colors.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  cardTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: THEME.colors.text,
  },
  typeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  discordBadge: {
    backgroundColor: '#5865F2',
  },
  slackBadge: {
    backgroundColor: '#4A154B',
  },
  typeBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '600',
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  statusEnabled: {
    backgroundColor: '#4CAF50',
  },
  statusDisabled: {
    backgroundColor: '#9E9E9E',
  },
  cardDetails: {
    marginBottom: 12,
  },
  detailText: {
    fontSize: 14,
    color: THEME.colors.textSecondary,
    marginBottom: 4,
  },
  cardActions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 6,
    alignItems: 'center',
    backgroundColor: THEME.colors.background,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  actionButtonText: {
    color: THEME.colors.text,
    fontWeight: '500',
  },
  deleteButton: {
    borderColor: '#ff4444',
  },
  deleteButtonText: {
    color: '#ff4444',
    fontWeight: '500',
  },
});
