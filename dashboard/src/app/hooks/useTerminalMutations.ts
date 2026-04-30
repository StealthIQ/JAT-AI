export type PendingDeleteTerminal = {
  terminalId: string;
  tentacleName: string;
  workspaceMode: string;
  intent: "close-terminal" | "delete-terminal" | "cleanup-worktree";
};

export function useTerminalMutations(_opts: any) {
  return {
    editingTerminalId: null,
    terminalNameDraft: "",
    isCreatingTerminal: false,
    isDeletingTerminalId: null,
    pendingDeleteTerminal: null as PendingDeleteTerminal | null,
    setTerminalNameDraft: () => {},
    setEditingTerminalId: () => {},
    beginTerminalNameEdit: () => {},
    submitTerminalRename: async () => {},
    createTerminal: async () => undefined as string | undefined,
    createWorktreeTerminal: async () => undefined as string | undefined,
    requestDeleteTerminal: () => {},
    cancelDeleteTerminal: () => {},
    confirmDeleteTerminal: async () => {},
  };
}
