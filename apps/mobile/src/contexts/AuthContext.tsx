import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as AuthSession from "expo-auth-session";
import * as WebBrowser from "expo-web-browser";
import { Character } from "../types";
import ESIService from "../services/ESIService";
import { ESI_CONFIG } from "../config";

WebBrowser.maybeCompleteAuthSession();

// ESI OAuth Configuration - loaded from environment variables
const ESI_CALLBACK_URL = AuthSession.makeRedirectUri({
  scheme: "evenexus",
});

interface AuthContextType {
  isAuthenticated: boolean;
  currentCharacter: Character | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentCharacter, setCurrentCharacter] = useState<Character | null>(
    null,
  );
  const [loading, setLoading] = useState(true);

  const discovery = {
    authorizationEndpoint: ESI_CONFIG.AUTHORIZE_URL,
    tokenEndpoint: ESI_CONFIG.TOKEN_URL,
  };

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: ESI_CONFIG.CLIENT_ID,
      scopes: [
        "esi-assets.read_assets.v1",
        "esi-characters.read_standings.v1",
        "esi-markets.read_character_orders.v1",
        "esi-universe.read_structures.v1",
        "esi-location.read_location.v1",
        "esi-location.read_ship_type.v1",
        "esi-skills.read_skills.v1",
        "esi-wallet.read_character_wallet.v1",
      ],
      redirectUri: ESI_CALLBACK_URL,
    },
    discovery,
  );

  useEffect(() => {
    loadStoredAuth();
  }, []);

  useEffect(() => {
    if (response?.type === "success") {
      const { code } = response.params;
      handleAuthCode(code);
    }
  }, [response]);

  const loadStoredAuth = async () => {
    try {
      const storedCharacter = await AsyncStorage.getItem("current_character");
      if (storedCharacter) {
        const character = JSON.parse(storedCharacter);

        // Check if token is still valid
        if (character.token_expiry && character.token_expiry > Date.now()) {
          setCurrentCharacter(character);
          setIsAuthenticated(true);
          ESIService.setAuthToken(character.access_token);
        } else if (character.refresh_token) {
          // Token expired, try to refresh
          await refreshTokenWithRefresh(character.refresh_token);
        }
      }
    } catch (error) {
      console.error("Error loading stored auth:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthCode = async (code: string) => {
    try {
      // Exchange code for tokens
      // In production, this should be done through a secure backend
      const tokenResponse = await AuthSession.exchangeCodeAsync(
        {
          clientId: ESI_CONFIG.CLIENT_ID,
          code,
          redirectUri: ESI_CALLBACK_URL,
          extraParams: {
            grant_type: "authorization_code",
          },
        },
        discovery,
      );

      const { accessToken, refreshToken, expiresIn } = tokenResponse;

      // Decode JWT to get character ID
      const characterId = decodeJWT(accessToken);

      // Fetch character info
      ESIService.setAuthToken(accessToken);
      const characterInfo = await ESIService.getCharacterInfo(characterId);

      const character: Character = {
        ...characterInfo,
        access_token: accessToken,
        refresh_token: refreshToken,
        token_expiry: Date.now() + expiresIn! * 1000,
      };

      await AsyncStorage.setItem(
        "current_character",
        JSON.stringify(character),
      );
      setCurrentCharacter(character);
      setIsAuthenticated(true);
    } catch (error) {
      console.error("Error handling auth code:", error);
    }
  };

  const refreshTokenWithRefresh = async (refreshToken: string) => {
    try {
      const tokenResponse = await AuthSession.refreshAsync(
        {
          clientId: ESI_CONFIG.CLIENT_ID,
          refreshToken,
        },
        discovery,
      );

      const {
        accessToken,
        refreshToken: newRefreshToken,
        expiresIn,
      } = tokenResponse;

      if (currentCharacter) {
        const updatedCharacter: Character = {
          ...currentCharacter,
          access_token: accessToken,
          refresh_token: newRefreshToken || refreshToken,
          token_expiry: Date.now() + expiresIn! * 1000,
        };

        await AsyncStorage.setItem(
          "current_character",
          JSON.stringify(updatedCharacter),
        );
        setCurrentCharacter(updatedCharacter);
        ESIService.setAuthToken(accessToken);
      }
    } catch (error) {
      console.error("Error refreshing token:", error);
      await logout();
    }
  };

  const decodeJWT = (token: string): number => {
    try {
      const parts = token.split(".");
      const payload = JSON.parse(atob(parts[1]));
      return parseInt(payload.sub.split(":")[2]);
    } catch (error) {
      console.error("Error decoding JWT:", error);
      return 0;
    }
  };

  const login = async () => {
    try {
      await promptAsync();
    } catch (error) {
      console.error("Error during login:", error);
    }
  };

  const logout = async () => {
    try {
      await AsyncStorage.removeItem("current_character");
      setCurrentCharacter(null);
      setIsAuthenticated(false);
    } catch (error) {
      console.error("Error during logout:", error);
    }
  };

  const refreshToken = async () => {
    if (currentCharacter?.refresh_token) {
      await refreshTokenWithRefresh(currentCharacter.refresh_token);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        currentCharacter,
        login,
        logout,
        refreshToken,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
