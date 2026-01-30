import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Character } from "../types";

interface CharacterContextType {
  characters: Character[];
  activeCharacter: Character | null;
  addCharacter: (character: Character) => Promise<void>;
  removeCharacter: (characterId: number) => Promise<void>;
  setActiveCharacter: (characterId: number) => void;
  getCharacter: (characterId: number) => Character | undefined;
  updateCharacter: (character: Character) => Promise<void>;
}

const CharacterContext = createContext<CharacterContextType | undefined>(
  undefined,
);

export const useCharacters = () => {
  const context = useContext(CharacterContext);
  if (!context) {
    throw new Error("useCharacters must be used within CharacterProvider");
  }
  return context;
};

interface CharacterProviderProps {
  children: ReactNode;
}

const CHARACTERS_STORAGE_KEY = "eve_nexus_characters";
const ACTIVE_CHARACTER_KEY = "eve_nexus_active_character";
const MAX_CHARACTERS = 100;

export const CharacterProvider: React.FC<CharacterProviderProps> = ({
  children,
}) => {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [activeCharacter, setActiveCharacterState] = useState<Character | null>(
    null,
  );

  useEffect(() => {
    loadCharacters();
  }, []);

  const loadCharacters = async () => {
    try {
      const storedCharacters = await AsyncStorage.getItem(
        CHARACTERS_STORAGE_KEY,
      );
      const activeCharacterId =
        await AsyncStorage.getItem(ACTIVE_CHARACTER_KEY);

      if (storedCharacters) {
        const parsedCharacters = JSON.parse(storedCharacters);
        setCharacters(parsedCharacters);

        if (activeCharacterId) {
          const active = parsedCharacters.find(
            (char: Character) =>
              char.character_id === parseInt(activeCharacterId),
          );
          setActiveCharacterState(active || null);
        }
      }
    } catch (error) {
      console.error("Error loading characters:", error);
    }
  };

  const saveCharacters = async (updatedCharacters: Character[]) => {
    try {
      await AsyncStorage.setItem(
        CHARACTERS_STORAGE_KEY,
        JSON.stringify(updatedCharacters),
      );
      setCharacters(updatedCharacters);
    } catch (error) {
      console.error("Error saving characters:", error);
    }
  };

  const addCharacter = async (character: Character) => {
    try {
      // Check if we've reached the maximum
      if (characters.length >= MAX_CHARACTERS) {
        throw new Error(`Maximum of ${MAX_CHARACTERS} characters reached`);
      }

      // Check if character already exists
      const existingIndex = characters.findIndex(
        (char) => char.character_id === character.character_id,
      );

      let updatedCharacters: Character[];
      if (existingIndex >= 0) {
        // Update existing character
        updatedCharacters = [...characters];
        updatedCharacters[existingIndex] = character;
      } else {
        // Add new character
        updatedCharacters = [...characters, character];
      }

      await saveCharacters(updatedCharacters);

      // If this is the first character, make it active
      if (characters.length === 0) {
        await setActiveCharacter(character.character_id);
      }
    } catch (error) {
      console.error("Error adding character:", error);
      throw error;
    }
  };

  const removeCharacter = async (characterId: number) => {
    try {
      const updatedCharacters = characters.filter(
        (char) => char.character_id !== characterId,
      );
      await saveCharacters(updatedCharacters);

      // If we removed the active character, clear it or set a new one
      if (activeCharacter?.character_id === characterId) {
        if (updatedCharacters.length > 0) {
          await setActiveCharacter(updatedCharacters[0].character_id);
        } else {
          setActiveCharacterState(null);
          await AsyncStorage.removeItem(ACTIVE_CHARACTER_KEY);
        }
      }
    } catch (error) {
      console.error("Error removing character:", error);
    }
  };

  const setActiveCharacter = async (characterId: number) => {
    const character = characters.find(
      (char) => char.character_id === characterId,
    );
    if (character) {
      setActiveCharacterState(character);
      await AsyncStorage.setItem(ACTIVE_CHARACTER_KEY, characterId.toString());
    }
  };

  const getCharacter = (characterId: number): Character | undefined => {
    return characters.find((char) => char.character_id === characterId);
  };

  const updateCharacter = async (character: Character) => {
    const updatedCharacters = characters.map((char) =>
      char.character_id === character.character_id ? character : char,
    );
    await saveCharacters(updatedCharacters);

    if (activeCharacter?.character_id === character.character_id) {
      setActiveCharacterState(character);
    }
  };

  return (
    <CharacterContext.Provider
      value={{
        characters,
        activeCharacter,
        addCharacter,
        removeCharacter,
        setActiveCharacter,
        getCharacter,
        updateCharacter,
      }}
    >
      {children}
    </CharacterContext.Provider>
  );
};
