import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type WorkspaceProject = {
  assetId?: string;
  assetName?: string;
  assetPreview?: string;
  foregroundAssetId?: string;
  maskAssetId?: string;
  previewId?: string;
  baseImageVersionId?: string;
  patternId?: string;
  backgroundMode?: string;
};

type WorkspaceState = {
  projects: Record<string, WorkspaceProject>;
  updateProject: (id: string, patch: Partial<WorkspaceProject>) => void;
};

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      projects: {},
      updateProject: (id, patch) =>
        set((state) => ({
          projects: { ...state.projects, [id]: { ...state.projects[id], ...patch } },
        })),
    }),
    {
      name: 'pingdou_workspace',
      partialize: (state) => ({
        projects: Object.fromEntries(
          Object.entries(state.projects).map(([id, project]) => [
            id,
            { ...project, assetPreview: project.assetPreview?.startsWith('data:') ? undefined : project.assetPreview },
          ]),
        ),
      }),
    },
  ),
);
