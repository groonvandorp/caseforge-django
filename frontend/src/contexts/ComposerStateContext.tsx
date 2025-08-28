import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ProcessNode } from '../types';

interface ComposerState {
  selectedModelKey: string | null;
  selectedNodeId: number | null;
  selectedNode: ProcessNode | null;
  expandedNodeIds: number[];
  scrollPosition: number;
}

interface ComposerStateContextType {
  state: ComposerState;
  setSelectedModel: (modelKey: string) => void;
  setSelectedNode: (node: ProcessNode | null) => void;
  setExpandedNodes: (nodeIds: number[]) => void;
  setScrollPosition: (position: number) => void;
  clearState: () => void;
}

const STORAGE_KEY = 'composer_state';

const defaultState: ComposerState = {
  selectedModelKey: null,
  selectedNodeId: null,
  selectedNode: null,
  expandedNodeIds: [],
  scrollPosition: 0,
};

const ComposerStateContext = createContext<ComposerStateContextType | undefined>(undefined);

export const ComposerStateProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Initialize state from localStorage
  const [state, setState] = useState<ComposerState>(() => {
    try {
      const savedState = localStorage.getItem(STORAGE_KEY);
      if (savedState) {
        const parsed = JSON.parse(savedState);
        // Don't restore the full node object, just the ID
        return {
          ...parsed,
          selectedNode: null, // Will be reloaded from API
        };
      }
    } catch (error) {
      console.error('Error loading composer state:', error);
    }
    return defaultState;
  });

  // Save to localStorage whenever state changes
  useEffect(() => {
    try {
      const stateToSave = {
        ...state,
        selectedNode: null, // Don't save the full node object
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
    } catch (error) {
      console.error('Error saving composer state:', error);
    }
  }, [state]);

  const setSelectedModel = (modelKey: string) => {
    setState(prev => ({
      ...prev,
      selectedModelKey: modelKey,
      // Clear selection when model changes
      selectedNodeId: null,
      selectedNode: null,
      expandedNodeIds: [],
    }));
  };

  const setSelectedNode = (node: ProcessNode | null) => {
    setState(prev => ({
      ...prev,
      selectedNodeId: node?.id || null,
      selectedNode: node,
    }));
  };

  const setExpandedNodes = (nodeIds: number[]) => {
    setState(prev => ({
      ...prev,
      expandedNodeIds: nodeIds,
    }));
  };

  const setScrollPosition = (position: number) => {
    setState(prev => ({
      ...prev,
      scrollPosition: position,
    }));
  };

  const clearState = () => {
    setState(defaultState);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <ComposerStateContext.Provider
      value={{
        state,
        setSelectedModel,
        setSelectedNode,
        setExpandedNodes,
        setScrollPosition,
        clearState,
      }}
    >
      {children}
    </ComposerStateContext.Provider>
  );
};

export const useComposerState = () => {
  const context = useContext(ComposerStateContext);
  if (!context) {
    throw new Error('useComposerState must be used within a ComposerStateProvider');
  }
  return context;
};