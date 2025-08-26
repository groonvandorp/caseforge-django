import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { ProcessModel } from '../types';
import { apiService } from '../services/api';

interface AppState {
  selectedModelKey: string | null;
  models: ProcessModel[];
  modelsLoading: boolean;
}

interface AppStateContextType {
  state: AppState;
  setSelectedModel: (modelKey: string) => void;
  loadModels: () => Promise<void>;
}

const STORAGE_KEY = 'app_state';

const defaultState: AppState = {
  selectedModelKey: null,
  models: [],
  modelsLoading: false,
};

const AppStateContext = createContext<AppStateContextType | undefined>(undefined);

export const AppStateProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Initialize state from localStorage
  const [state, setState] = useState<AppState>(() => {
    try {
      const savedState = localStorage.getItem(STORAGE_KEY);
      if (savedState) {
        const parsed = JSON.parse(savedState);
        return {
          ...defaultState,
          selectedModelKey: parsed.selectedModelKey,
        };
      }
    } catch (error) {
      console.error('Error loading app state:', error);
    }
    return defaultState;
  });

  // Save to localStorage whenever selectedModelKey changes
  useEffect(() => {
    try {
      if (state.selectedModelKey) {
        const stateToSave = {
          selectedModelKey: state.selectedModelKey,
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
      }
    } catch (error) {
      console.error('Error saving app state:', error);
    }
  }, [state.selectedModelKey]);

  // Load models only once on mount
  useEffect(() => {
    let isMounted = true;

    const loadModels = async () => {
      // Prevent loading if already loading or models already exist
      setState(prev => {
        if (prev.modelsLoading || prev.models.length > 0) {
          return prev;
        }
        return { ...prev, modelsLoading: true };
      });

      try {
        const modelsData = await apiService.getModels();
        
        if (isMounted) {
          setState(prev => {
            // Double-check we still need to load (avoid race conditions)
            if (prev.models.length > 0) {
              return prev;
            }
            
            const newState = {
              ...prev,
              models: modelsData,
              modelsLoading: false,
            };
            
            // If no model is selected, default to the first one
            if (!prev.selectedModelKey && modelsData.length > 0) {
              newState.selectedModelKey = modelsData[0].model_key;
            }
            
            return newState;
          });
        }
      } catch (error) {
        console.error('Failed to load models:', error);
        if (isMounted) {
          setState(prev => ({ ...prev, modelsLoading: false }));
        }
      }
    };

    loadModels();

    return () => {
      isMounted = false;
    };
  }, []); // Run only once on mount

  const loadModels = useCallback(async () => {
    // This is just for external calls, actual loading happens in useEffect above
  }, []);

  const setSelectedModel = (modelKey: string) => {
    setState(prev => ({
      ...prev,
      selectedModelKey: modelKey,
    }));
  };

  return (
    <AppStateContext.Provider
      value={{
        state,
        setSelectedModel,
        loadModels,
      }}
    >
      {children}
    </AppStateContext.Provider>
  );
};

export const useAppState = () => {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error('useAppState must be used within an AppStateProvider');
  }
  return context;
};