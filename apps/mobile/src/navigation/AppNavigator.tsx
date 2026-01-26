/**
 * App Navigator
 * Main navigation stack
 */
import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import {
  HomeScreen,
  RouteScreen,
  SettingsScreen,
  FittingScreen,
  AlertsScreen,
} from '../screens';
import { RootStackParamList } from './types';
import { THEME } from '../config';

const Stack = createStackNavigator<RootStackParamList>();

export const AppNavigator: React.FC = () => {
  return (
    <Stack.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerStyle: {
          backgroundColor: THEME.colors.card,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: THEME.colors.border,
        },
        headerTintColor: THEME.colors.text,
        headerTitleStyle: {
          fontWeight: 'bold',
        },
        cardStyle: {
          backgroundColor: THEME.colors.background,
        },
      }}
    >
      <Stack.Screen
        name="Home"
        component={HomeScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="Route"
        component={RouteScreen}
        options={{ title: 'Route Planner' }}
      />
      <Stack.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ title: 'Settings' }}
      />
      <Stack.Screen
        name="Fitting"
        component={FittingScreen}
        options={{ title: 'Fitting Analyzer' }}
      />
      <Stack.Screen
        name="Alerts"
        component={AlertsScreen}
        options={{ title: 'Kill Alerts' }}
      />
    </Stack.Navigator>
  );
};

export default AppNavigator;
