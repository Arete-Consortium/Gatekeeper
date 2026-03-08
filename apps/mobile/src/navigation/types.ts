/**
 * Navigation Types
 */

import type { RouteResponse } from '../types';

export type RootStackParamList = {
  Home: undefined;
  Map: { route?: RouteResponse; systemName?: string } | undefined;
  Route: { profile?: 'shortest' | 'safer' | 'paranoid'; from?: string; to?: string } | undefined;
  Settings: undefined;
  Fitting: undefined;
  Alerts: undefined;
};
