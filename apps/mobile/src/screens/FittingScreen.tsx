/**
 * Fitting Screen
 * Parse and analyze ship fittings for travel recommendations
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
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { GatekeeperAPI } from '../services/GatekeeperAPI';
import { THEME } from '../config';
import { FittingAnalysisResponse } from '../types';

export const FittingScreen: React.FC = () => {
  const [eftText, setEftText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FittingAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeFitting = async () => {
    if (!eftText.trim()) {
      setError('Please paste your EFT fitting');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await GatekeeperAPI.analyzeFitting(eftText);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze fitting');
    } finally {
      setLoading(false);
    }
  };

  const clearForm = () => {
    setEftText('');
    setResult(null);
    setError(null);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.inputSection}>
          <Text style={styles.sectionTitle}>Ship Fitting</Text>
          <Text style={styles.hint}>
            Paste your EFT format fitting from EVE Online
          </Text>
          <TextInput
            style={styles.textInput}
            multiline
            numberOfLines={10}
            placeholder="[Ship Name, Fit Name]&#10;Module 1&#10;Module 2&#10;..."
            placeholderTextColor={THEME.colors.textSecondary}
            value={eftText}
            onChangeText={setEftText}
            textAlignVertical="top"
          />

          <View style={styles.buttonRow}>
            <TouchableOpacity
              style={[styles.button, styles.clearButton]}
              onPress={clearForm}
            >
              <Text style={styles.buttonText}>Clear</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.analyzeButton]}
              onPress={analyzeFitting}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.buttonText}>Analyze</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>

        {error && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {result && (
          <View style={styles.resultSection}>
            <View style={styles.shipInfo}>
              <Text style={styles.shipName}>{result.fitting.ship_name}</Text>
              <View style={styles.badges}>
                <View style={[styles.badge, styles.categoryBadge]}>
                  <Text style={styles.badgeText}>
                    {result.fitting.ship_category.toUpperCase()}
                  </Text>
                </View>
                {result.fitting.jump_capability !== 'none' && (
                  <View style={[styles.badge, styles.jumpBadge]}>
                    <Text style={styles.badgeText}>JUMP CAPABLE</Text>
                  </View>
                )}
              </View>
            </View>

            <View style={styles.capabilitiesSection}>
              <Text style={styles.subTitle}>Travel Capabilities</Text>
              <View style={styles.capGrid}>
                <CapabilityItem
                  label="Covert Ops"
                  enabled={result.fitting.is_covert_capable}
                />
                <CapabilityItem
                  label="Cloak"
                  enabled={result.fitting.is_cloak_capable}
                />
                <CapabilityItem
                  label="Warp Stabs"
                  enabled={result.fitting.has_warp_stabs}
                />
                <CapabilityItem
                  label="Bubble Immune"
                  enabled={result.fitting.is_bubble_immune}
                />
                <CapabilityItem
                  label="Align Mods"
                  enabled={result.fitting.has_align_mods}
                />
                <CapabilityItem
                  label="Warp Speed"
                  enabled={result.fitting.has_warp_speed_mods}
                />
              </View>
            </View>

            <View style={styles.recommendationSection}>
              <Text style={styles.subTitle}>Travel Recommendation</Text>
              <View style={styles.recommendedProfile}>
                <Text style={styles.profileLabel}>Recommended Profile:</Text>
                <Text style={styles.profileValue}>
                  {result.travel.recommended_profile.toUpperCase()}
                </Text>
              </View>

              <View style={styles.travelMethods}>
                <TravelMethod
                  label="Gates"
                  enabled={result.travel.can_use_gates}
                />
                <TravelMethod
                  label="Jump Bridges"
                  enabled={result.travel.can_use_jump_bridges}
                />
                <TravelMethod
                  label="Jump Drive"
                  enabled={result.travel.can_jump}
                />
                <TravelMethod
                  label="Bridge Others"
                  enabled={result.travel.can_bridge_others}
                />
              </View>
            </View>

            {result.travel.warnings.length > 0 && (
              <View style={styles.warningsSection}>
                <Text style={styles.warningsTitle}>Warnings</Text>
                {result.travel.warnings.map((warning, index) => (
                  <View key={index} style={styles.warningItem}>
                    <Text style={styles.warningText}>! {warning}</Text>
                  </View>
                ))}
              </View>
            )}

            {result.travel.tips.length > 0 && (
              <View style={styles.tipsSection}>
                <Text style={styles.tipsTitle}>Tips</Text>
                {result.travel.tips.map((tip, index) => (
                  <View key={index} style={styles.tipItem}>
                    <Text style={styles.tipText}>* {tip}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const CapabilityItem: React.FC<{ label: string; enabled: boolean }> = ({ label, enabled }) => (
  <View style={[styles.capItem, enabled && styles.capItemEnabled]}>
    <Text style={[styles.capText, enabled && styles.capTextEnabled]}>{label}</Text>
  </View>
);

const TravelMethod: React.FC<{ label: string; enabled: boolean }> = ({ label, enabled }) => (
  <View style={styles.methodItem}>
    <Text style={[styles.methodIcon, enabled ? styles.methodEnabled : styles.methodDisabled]}>
      {enabled ? '✓' : '✕'}
    </Text>
    <Text style={styles.methodText}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  inputSection: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: THEME.colors.text,
    marginBottom: 8,
  },
  hint: {
    fontSize: 14,
    color: THEME.colors.textSecondary,
    marginBottom: 12,
  },
  textInput: {
    backgroundColor: THEME.colors.card,
    borderRadius: 8,
    padding: 12,
    color: THEME.colors.text,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontSize: 14,
    minHeight: 200,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  buttonRow: {
    flexDirection: 'row',
    marginTop: 12,
    gap: 12,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  clearButton: {
    backgroundColor: THEME.colors.card,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  analyzeButton: {
    backgroundColor: THEME.colors.primary,
  },
  buttonText: {
    color: THEME.colors.text,
    fontWeight: '600',
    fontSize: 16,
  },
  errorContainer: {
    backgroundColor: '#ff4444',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  errorText: {
    color: '#fff',
    fontSize: 14,
  },
  resultSection: {
    backgroundColor: THEME.colors.card,
    borderRadius: 12,
    padding: 16,
  },
  shipInfo: {
    marginBottom: 16,
  },
  shipName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: THEME.colors.text,
    marginBottom: 8,
  },
  badges: {
    flexDirection: 'row',
    gap: 8,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
  },
  categoryBadge: {
    backgroundColor: THEME.colors.primary,
  },
  jumpBadge: {
    backgroundColor: '#4CAF50',
  },
  badgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  capabilitiesSection: {
    marginBottom: 16,
  },
  subTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: THEME.colors.text,
    marginBottom: 12,
  },
  capGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  capItem: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: THEME.colors.background,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  capItemEnabled: {
    backgroundColor: 'rgba(76, 175, 80, 0.2)',
    borderColor: '#4CAF50',
  },
  capText: {
    fontSize: 12,
    color: THEME.colors.textSecondary,
  },
  capTextEnabled: {
    color: '#4CAF50',
    fontWeight: '500',
  },
  recommendationSection: {
    marginBottom: 16,
  },
  recommendedProfile: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  profileLabel: {
    fontSize: 14,
    color: THEME.colors.textSecondary,
    marginRight: 8,
  },
  profileValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: THEME.colors.primary,
  },
  travelMethods: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
  },
  methodItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  methodIcon: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  methodEnabled: {
    color: '#4CAF50',
  },
  methodDisabled: {
    color: '#ff4444',
  },
  methodText: {
    fontSize: 14,
    color: THEME.colors.text,
  },
  warningsSection: {
    marginTop: 16,
    padding: 12,
    backgroundColor: 'rgba(255, 152, 0, 0.1)',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#FF9800',
  },
  warningsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF9800',
    marginBottom: 8,
  },
  warningItem: {
    marginBottom: 4,
  },
  warningText: {
    fontSize: 14,
    color: '#FF9800',
  },
  tipsSection: {
    marginTop: 16,
    padding: 12,
    backgroundColor: 'rgba(33, 150, 243, 0.1)',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#2196F3',
  },
  tipsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2196F3',
    marginBottom: 8,
  },
  tipItem: {
    marginBottom: 4,
  },
  tipText: {
    fontSize: 14,
    color: '#2196F3',
  },
});
