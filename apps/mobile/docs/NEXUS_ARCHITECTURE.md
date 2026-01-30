# Architecture Documentation

## Overview

Eve Nexus is built using React Native with Expo, following a modular architecture that separates concerns and enables easy maintenance and scalability.

## Core Architecture Principles

1. **Separation of Concerns**: Clear separation between UI, business logic, and data layers
2. **Reusability**: Component-based architecture for maximum reusability
3. **Type Safety**: TypeScript for compile-time type checking
4. **State Management**: Context API for global state management
5. **API Integration**: Service layer for all external API calls

## Directory Structure

```
Eve-Nexus-APP/
├── src/
│   ├── components/        # Reusable UI components
│   ├── contexts/          # React Context providers
│   ├── navigation/        # Navigation configuration
│   ├── screens/           # Screen components
│   ├── services/          # API and business logic services
│   ├── types/             # TypeScript type definitions
│   └── utils/             # Utility functions
├── assets/                # Static assets (images, fonts)
├── App.tsx                # Root application component
└── app.json               # Expo configuration
```

## Layer Architecture

### 1. Presentation Layer (UI)

**Components**: `src/screens/` and `src/components/`

- Responsible for rendering UI
- Handles user interactions
- Uses React hooks for local state
- Consumes context for global state
- Minimal business logic

**Key Screens**:
- `LoginScreen`: SSO authentication
- `HomeScreen`: Main dashboard
- `CharactersScreen`: Character management
- `AssetsScreen`: Asset tracking
- `MarketOrdersScreen`: Market order management
- `MapScreen`: Star map interface
- `RouteMapScreen`: Route planning and visualization
- `FittingsScreen`: Ship fitting suggestions
- `AIAssistantScreen`: AI-powered assistance

### 2. State Management Layer

**Contexts**: `src/contexts/`

#### AuthContext
- Manages authentication state
- Handles ESI SSO flow
- Token management and refresh
- User session management

```typescript
interface AuthContextType {
  isAuthenticated: boolean;
  currentCharacter: Character | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  loading: boolean;
}
```

#### CharacterContext
- Manages multiple characters (up to 100)
- Character switching
- Character CRUD operations
- Persistent storage integration

```typescript
interface CharacterContextType {
  characters: Character[];
  activeCharacter: Character | null;
  addCharacter: (character: Character) => Promise<void>;
  removeCharacter: (characterId: number) => Promise<void>;
  setActiveCharacter: (characterId: number) => void;
  getCharacter: (characterId: number) => Character | undefined;
  updateCharacter: (character: Character) => Promise<void>;
}
```

### 3. Service Layer

**Services**: `src/services/`

#### ESIService
Handles all interactions with EVE Online's ESI API:

- Character information retrieval
- Asset fetching
- Market order queries
- Solar system data
- Route calculation
- Universe search

**Methods**:
```typescript
- getCharacterInfo(characterId: number): Promise<Character>
- getCharacterAssets(characterId: number): Promise<Asset[]>
- getCharacterOrders(characterId: number): Promise<MarketOrder[]>
- getCharacterSkills(characterId: number): Promise<Skills>
- getSolarSystem(systemId: number): Promise<SolarSystem>
- getRoute(origin: number, destination: number): Promise<number[]>
```

#### ZKillboardService
Integrates with zkillboard API for threat assessment:

- System kill data retrieval
- Danger rating calculation
- Route danger assessment
- Character/corporation kill history

**Methods**:
```typescript
- getSystemKills(systemId: number, hoursBack: number): Promise<KillmailSummary[]>
- getSystemDangerRating(systemId: number): Promise<ZKillboardData>
- getRouteDangerAssessment(systemIds: number[]): Promise<Map<number, ZKillboardData>>
```

#### AIService
Provides AI-powered assistance:

- Route planning with danger assessment
- Alternative route suggestions
- Jump-capable ship calculations
- Asset distribution analysis
- Market order optimization
- Ship fitting recommendations

**Methods**:
```typescript
- calculateJumpRange(baseRange, jdcLevel, jfLevel): number
- calculateJumpRoute(origin, destination, range, fuel): Promise<Route>
- analyzeRouteSafety(systemIds: number[]): Promise<string>
- generateRouteSuggestions(origin, destination): Promise<AIRouteSuggestion>
- suggestShipFit(shipTypeId, purpose, skills): Promise<ShipFit[]>
```

### 4. Data Layer

**Types**: `src/types/`

Comprehensive TypeScript type definitions for:
- Character data structures
- Assets and items
- Market orders
- Solar systems and stargates
- Routes and navigation
- zkillboard data
- Skills and ship fittings

**Storage**:
- AsyncStorage for persistent data
- In-memory caching for API responses
- Secure token storage

## Data Flow

### Authentication Flow

```
User Action → AuthContext.login()
           → Expo AuthSession (ESI SSO)
           → Token Exchange
           → ESIService.getCharacterInfo()
           → CharacterContext.addCharacter()
           → AsyncStorage (persist)
           → UI Update
```

### Asset Fetching Flow

```
AssetsScreen Mount → useEffect
                  → CharacterContext (get activeCharacter)
                  → ESIService.setAuthToken()
                  → ESIService.getCharacterAssets()
                  → Process and enrich data
                  → Update local state
                  → Render UI
```

### Route Planning Flow

```
User Input (Origin/Destination) → AIService.generateRouteSuggestions()
                                 → ESIService.getRoute() (shortest)
                                 → ZKillboardService.getRouteDangerAssessment()
                                 → Calculate alternative routes
                                 → Analyze risk
                                 → Return AIRouteSuggestion
                                 → RouteMapScreen displays results
```

## API Integration

### ESI API
- Base URL: `https://esi.evetech.net/latest`
- Authentication: OAuth 2.0 with JWT tokens
- Rate Limiting: Handled by service layer
- Error Handling: Try-catch with user-friendly messages

### zkillboard API
- Base URL: `https://zkillboard.com/api`
- Authentication: Not required (User-Agent header)
- Rate Limiting: Respectful delays between requests
- Caching: Recent data cached to reduce API calls

## Security Considerations

1. **Token Storage**: Tokens stored in AsyncStorage (consider SecureStore for production)
2. **Token Refresh**: Automatic refresh before expiration
3. **Scope Management**: Minimal required scopes for functionality
4. **No Password Storage**: Only OAuth tokens stored
5. **HTTPS Only**: All API calls over HTTPS

## Performance Optimizations

1. **Lazy Loading**: Components loaded on demand
2. **Memoization**: React.memo and useMemo for expensive computations
3. **Pagination**: Large lists paginated
4. **Caching**: API responses cached when appropriate
5. **Debouncing**: Search inputs debounced to reduce API calls

## Error Handling

### Strategy
1. **Try-Catch Blocks**: All async operations wrapped
2. **User Feedback**: Clear error messages shown to users
3. **Logging**: Console logging for debugging
4. **Graceful Degradation**: App remains functional even if some features fail

### Error Types
- **Network Errors**: API unavailable or timeout
- **Authentication Errors**: Invalid or expired tokens
- **Rate Limit Errors**: Too many requests
- **Data Errors**: Invalid or missing data

## Testing Strategy

### Unit Tests
- Service layer functions
- Utility functions
- Context providers

### Integration Tests
- API integration
- Authentication flow
- Data persistence

### E2E Tests
- Critical user flows
- Navigation
- Character management

## Scalability Considerations

1. **Character Limit**: Supports up to 100 characters with efficient storage
2. **API Optimization**: Batching requests where possible
3. **State Management**: Context API suitable for current scale
4. **Database**: Consider local database (SQLite) for large datasets

## Future Enhancements

1. **Offline Mode**: Cache data for offline access
2. **Push Notifications**: Market order and wallet notifications
3. **Real-time Updates**: WebSocket integration for live data
4. **Advanced Caching**: Redux with persistence middleware
5. **Background Tasks**: Periodic data sync
6. **Analytics**: User behavior tracking
7. **Crash Reporting**: Integration with Sentry or similar

## Development Workflow

1. **Feature Branch**: Create branch for new features
2. **Development**: Implement and test locally
3. **Code Review**: PR review before merge
4. **Testing**: Automated tests run on CI
5. **Deployment**: Build and publish through Expo

## Dependencies Management

### Core Dependencies
- `expo`: Platform framework
- `react-native`: Core framework
- `@react-navigation`: Navigation
- `axios`: HTTP client
- `@react-native-async-storage/async-storage`: Storage

### Version Strategy
- Expo SDK versions locked to compatible versions
- Regular security updates
- Careful testing before major version updates

## Build and Deployment

### Development Build
```bash
npm start
```

### Production Build
```bash
# iOS
expo build:ios

# Android
expo build:android
```

### OTA Updates
Expo supports over-the-air updates for quick fixes without app store review.

## Monitoring and Maintenance

1. **Error Tracking**: Implement error tracking service
2. **Analytics**: Track feature usage
3. **Performance Monitoring**: Monitor app performance metrics
4. **User Feedback**: In-app feedback mechanism
5. **Regular Updates**: Keep dependencies updated

## Documentation Standards

- **Code Comments**: Complex logic documented inline
- **README**: High-level overview and setup
- **SETUP.md**: Detailed setup instructions
- **ARCHITECTURE.md**: This document
- **API Docs**: Service layer methods documented
